# Deploy na AWS — uma instância EC2 puxando as imagens do ECR

> **Objetivo:** subir o stack completo (9 serviços) numa única EC2, usando as
> **mesmas imagens** publicadas no ECR (`tools/publish_ecr.sh`, ver
> `docs/PLANO_DIVISAO.md`) — a instância não builda nada, só dá `pull`. A
> diferença para o local é toda em configuração:
>
> 1. **imagens** — local builda com `docker compose up --build`; na EC2 usa-se
>    `docker-compose.yml` + `docker-compose.prod.yml` (override que aponta
>    `image:` para o ECR) e `docker compose pull`;
> 2. **credencial** — local usa chaves no `.env`; na EC2 a instância tem uma
>    **IAM role** e o boto3 (e o próprio `docker login` no ECR) pegam a
>    credencial dela sozinhos;
> 3. **firewall** — o *Security Group* libera só a porta **8008** (o `fin_web`);
> 4. **`.env`** — sem as 3 linhas de chave AWS, com `API_KEY` preenchida.
>
> **Nada de código muda. Nenhum pipeline.** O deploy é manual: publicar as
> imagens (`tools/publish_ecr.sh`, local), copiar os arquivos de config pra
> instância e rodar `docker compose pull && up -d`.
>
> Alternativa cotada e **descartada por ora**: ECS Fargate. Decisão
> (2026-09-12): para 9 containers com tráfego modesto, EC2+ECR mantém a
> simplicidade (sem CI/CD, sem service discovery extra, sem EFS) já assumida
> neste runbook. Ver §12 se isso mudar no futuro.

Este runbook assume **Amazon Linux 2023**, região **us-east-1** (a mesma onde
os modelos Bedrock estão habilitados e onde os guardrails
os guardrails de entrada/saída existem — conta `<ACCOUNT_ID>`).

---

## 0. Pré-requisitos

- Acesso ao Console AWS da conta `<ACCOUNT_ID>` (ou CLI com um profile admin).
- Um **key pair** de EC2 para SSH (crie um em EC2 → Key Pairs se não tiver;
  baixe o `.pem`).
- No Bedrock, **Model access** já liberado para Claude Haiku 4.5, Claude
  Sonnet 4.5 e Titan Embed Text v2 em us-east-1 (Console → Bedrock → *Model
  access*). Isso é da conta, não da instância.
- Seu IP público (para liberar SSH só pra você): abra <https://checkip.amazonaws.com>.

Ao longo do doc, substitua os placeholders:

| Placeholder | Exemplo |
|---|---|
| `<ACCOUNT_ID>` | `123456789012` |
| `<REGION>` | `us-east-1` |
| `<SEU_IP>` | `203.0.113.7` |
| `<KEY_PAIR>` | `finguard-ec2` |
| `<EC2_IP>` | o IP público da instância, depois que ela subir |
| `<CHAVE.pem>` | caminho do seu key pair baixado |

---

## 1. IAM role para a instância

A instância precisa poder chamar o Bedrock **e** puxar as imagens do ECR. Em
vez de chaves, isso vem de uma **role anexada à EC2** (*instance profile*).

### 1.1 Política (Bedrock)

Console → **IAM → Policies → Create policy → aba JSON**. Cole:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FinGuardBedrock",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:ApplyGuardrail"
      ],
      "Resource": "*"
    }
  ]
}
```

> `Resource: "*"` mantém o primeiro deploy simples. Para apertar depois, veja
> **§11 (Endurecer a policy)**.

Nome: `FinGuardBedrockInvoke`. Create.

### 1.2 Role

Console → **IAM → Roles → Create role**:

- **Trusted entity type:** AWS service
- **Use case:** EC2
- **Permissions:** marque `FinGuardBedrockInvoke` (a policy acima) **e** a
  managed policy `AmazonEC2ContainerRegistryReadOnly` (dá `ecr:GetAuthorizationToken`
  + `ecr:BatchGetImage`/`GetDownloadUrlForLayer`/`BatchCheckLayerAvailability`
  — o suficiente para `docker login` + `pull`; não dá permissão de push)
- **Role name:** `FinGuardEC2Role`
- Create role.

*(O instance profile de mesmo nome é criado junto automaticamente.)*

### 1.3 (alternativa CLI)

```bash
cat > /tmp/trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
cat > /tmp/policy.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Sid":"FinGuardBedrock","Effect":"Allow","Action":["bedrock:InvokeModel","bedrock:ApplyGuardrail"],"Resource":"*"}]}
EOF
aws iam create-role --role-name FinGuardEC2Role --assume-role-policy-document file:///tmp/trust.json
aws iam put-role-policy --role-name FinGuardEC2Role --policy-name FinGuardBedrockInvoke --policy-document file:///tmp/policy.json
aws iam attach-role-policy --role-name FinGuardEC2Role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam create-instance-profile --instance-profile-name FinGuardEC2Role
aws iam add-role-to-instance-profile --instance-profile-name FinGuardEC2Role --role-name FinGuardEC2Role
```

---

## 2. Security Group

Console → **EC2 → Security Groups → Create security group**:

- **Name:** `finguard-sg`
- **VPC:** a default serve.
- **Inbound rules:**

| Type | Port | Source | Para quê |
|---|---|---|---|
| SSH | 22 | `<SEU_IP>/32` | você entrar na máquina |
| Custom TCP | 8008 | `<SEU_IP>/32` (ou `0.0.0.0/0` se for demo aberta) | o `fin_web` no navegador |

- **Outbound rules:** deixe o padrão (**All traffic → 0.0.0.0/0**). A
  instância precisa de saída para: endpoint do Bedrock, Docker Hub (imagem
  base `python:3.12-slim`) e o repositório de pacotes do SO.

> As portas **8000–8007 não entram na lista**. Elas existem dentro da
> instância (o `fin_web` fala com o orquestrador por elas na rede interna do
> compose), mas ninguém de fora alcança.

---

## 3. Lançar a instância EC2

> Faça isto **depois** dos §1 (role) e §2 (security group) — o assistente vai
> pedir os dois.

Console → **EC2 → Instances → Launch an instance**:

| Campo | Valor |
|---|---|
| **Name** | `finguard` |
| **AMI** | Amazon Linux 2023 (x86_64) |
| **Instance type** | `t3.large` (2 vCPU / 8 GB) — folgado. `t3.medium` (4 GB) roda para uso leve; abaixo disso o batch sofre. |
| **Key pair** | `<KEY_PAIR>` |
| **Network settings → Firewall (security groups)** | marque **"Select existing security group"** e escolha o `finguard-sg` (o que você criou no §2). A outra opção, "Create security group", criaria um novo aqui — não use. |
| **Storage** | 30 GiB gp3 (imagens ~2 GB + volumes de dados) |
| **Advanced details → IAM instance profile** | `FinGuardEC2Role` (criado no §1) |

Launch. Anote o **IPv4 público** (`<EC2_IP>`).

> **IP estável (recomendado):** EC2 → **Elastic IPs → Allocate**, depois
> **Associate** à instância. Sem isso, o IP muda toda vez que você
> **para/inicia** a instância (reiniciar pelo SO não muda).

---

## 4. Preparar a instância (instalar Docker)

```bash
ssh -i finguard.pem ec2-user@54.91.118.95

# Docker
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# plugin 'docker compose' (v2) — o pacote do AL2023 não traz
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
     -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# saia e entre de novo para o grupo 'docker' valer
exit
```

Reconecte e confirme:

```bash
ssh -i <CHAVE.pem> ec2-user@<EC2_IP>
docker version
docker compose version
# a role está visível?
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/
#   -> deve imprimir: FinGuardEC2Role
```

---

## 5. Levar a config para a instância e puxar as imagens

O código-fonte **não precisa mais ir para a EC2** — as 9 imagens já estão
buildadas e publicadas no ECR (`tools/publish_ecr.sh`, rodado local). A
instância só precisa dos arquivos de **configuração**:

- `docker-compose.yml` + `docker-compose.prod.yml`
- `.env.example` (para virar `.env` no §6)
- `fin_rag/assets/docs/` (o PDF seed da política interna — montado read-only)
- `tools/smoke_e2e.py` (opcional, só para o teste do §8)

### 5.a Pacote `.tar.gz` (bom para o primeiro deploy)

Na **sua máquina**, na pasta que contém `apis_finguard/`:

```bash
tar -czf apis_finguard_config.tgz \
    apis_finguard/docker-compose.yml \
    apis_finguard/docker-compose.prod.yml \
    apis_finguard/.env.example \
    apis_finguard/fin_rag/assets/docs \
    apis_finguard/tools/smoke_e2e.py

scp -i <CHAVE.pem> apis_finguard_config.tgz ec2-user@<EC2_IP>:~
```

Na **instância**:

```bash
tar -xzf apis_finguard_config.tgz
cd apis_finguard
```

### 5.b Melhor a médio prazo — git

Faça `git init` no `apis_finguard`, publique num repositório privado
(GitHub / CodeCommit) e na instância use `git clone` / `git pull` — mesmo
sendo só config, versionar com git facilita o histórico de mudanças no
compose/`.env.example`.

### 5.c Login no ECR e pull

Na **instância** (a role `FinGuardEC2Role` já dá a permissão — ver §1.2):

```bash
aws --version   # AL2023 normalmente já traz a AWS CLI v2; se faltar, instale
                # a partir da doc oficial da AWS CLI v2 para Linux

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

> O token do `docker login` dura ~12h. Só precisa logar de novo quando for
> dar `pull` de uma imagem nova depois desse prazo — containers já rodando
> não são afetados.

**Para atualizar depois:** local, rode `tools/publish_ecr.sh` (builda+push);
na instância, só repita o login se o token tiver expirado e vá direto para
`docker compose ... pull && up -d` (§7/§9) — não precisa re-copiar nada, a
menos que o `docker-compose.yml`/`.prod.yml` tenham mudado.

---

## 6. Configurar o `.env` na instância

```bash
cd ~/apis_finguard
cp .env.example .env
nano .env    # ou vi
```

Ajuste **estas linhas** (o resto pode ficar no default):

```ini
AWS_REGION=us-east-1

# NÃO preencher — a instância usa a IAM role (FinGuardEC2Role) via IMDS.
AWS_PROFILE=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=

# Registry de onde a instância puxa as imagens (docker-compose.prod.yml).
ECR_REGISTRY=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Guardrails reais da conta (input e output separados).
GUARDRAIL_ID=<GUARDRAIL_ID>
GUARDRAIL_VERSION=DRAFT
GUARDRAIL_ID_OUTPUT=<GUARDRAIL_ID_OUTPUT>
GUARDRAIL_VERSION_OUTPUT=DRAFT

# Em servidor, deixe true: triage/rag/risk também abortam cedo e com erro
# claro se a permissão da role estiver errada.
PROBE_ON_STARTUP=true
INGEST_ON_STARTUP=true

# Protege as APIs internas (orquestrador + folhas). Gere um valor:
#   openssl rand -hex 24
API_KEY=COLE_UM_VALOR_ALEATORIO_AQUI
```

Sobre o `API_KEY`:

- Com ele definido, **o orquestrador e as folhas exigem** o header
  `X-API-Key`. O `fin_web` injeta esse header automaticamente nas chamadas que
  faz — **o navegador não precisa mandar nada**.
- O `fin_web` em si (porta 8008) **não** fica protegido por essa chave — quem
  alcança a 8008 usa a interface. Por isso o Security Group libera a 8008 só
  pro seu IP. Proteção da própria interface (login) é assunto de um proxy na
  frente — ver **§12**.

---

## 7. Subir

```bash
cd ~/apis_finguard
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Acompanhe até tudo ficar `healthy`:

```bash
watch -n3 docker compose ps
# Ctrl-C quando os 9 estiverem "Up ... (healthy)"
```

Ordem automática: as 7 folhas → `fin_orchestrator` (espera as folhas) →
`fin_web` (espera o orquestrador).

Se algo não ficar healthy, pule para **§10 Troubleshooting**.

---

## 8. Testar

Na **instância**:

```bash
curl -s localhost:8000/health/downstream | python3 -m json.tool
#   -> "status": "ok" e as 7 folhas "ok": true
```

Da **sua máquina** (o smoke test aponta para o EC2):

```bash
python tools/smoke_e2e.py --orch http://<EC2_IP>:8000 --web http://<EC2_IP>:8008 --api-key <SEU_API_KEY>
```

> Isso só funciona se a 8000 também estiver liberada no Security Group. Se
> preferir não abrir a 8000, rode o smoke **dentro da instância**:
> `python3 tools/smoke_e2e.py --api-key <SEU_API_KEY>` (o AL2023 tem Python 3).

Navegador: **http://<EC2_IP>:8008**

---

## 9. Operação do dia a dia

```bash
cd ~/apis_finguard
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'

dc ps                     # estado
dc logs -f fin_risk       # logs de uma API
dc logs -f                # todas
dc restart fin_web        # reiniciar uma
dc down                   # PARAR tudo (mantém volumes)
dc down -v                # parar e APAGAR índice/relatórios/log
dc pull && dc up -d       # redeploy após publicar novas imagens no ECR
```

**Redeploy completo:** local, `tools/publish_ecr.sh` builda+push as imagens
que mudaram; na instância, `dc pull && dc up -d` (o compose recria só os
containers cuja imagem mudou). Se o `docker-compose.yml`/`.prod.yml` também
mudaram, refaça o §5.a/§5.b antes.

**Parar a instância para não pagar** quando não estiver usando: EC2 →
Instances → Stop. Ao iniciar de novo, se **não** houver Elastic IP, o IP
público muda. Os dados (volumes) sobrevivem ao stop/start.

**Custo aproximado (us-east-1, on-demand):** `t3.large` ≈ US$ 0,083/h
(≈ US$ 60/mês se ligada 24/7) + EBS 30 GB gp3 ≈ US$ 2,4/mês + Bedrock por
token (Haiku barato; Sonnet ~US$ 3 / US$ 15 por milhão de tokens in/out;
Titan embed ~US$ 0,02 / milhão). Instância **parada** = só o custo do EBS.

---

## 10. Troubleshooting

| Sintoma | Causa provável / o que checar |
|---|---|
| `fin_guardrail` reiniciando / `unhealthy` | `docker compose logs fin_guardrail`. Mensagem `BEDROCK_SEM_PERMISSAO` → a role não tem `bedrock:ApplyGuardrail` (rever §1.1). `BEDROCK_GUARDRAIL_NAO_ENCONTRADO` → `GUARDRAIL_ID` errado ou região diferente. `BEDROCK_SEM_CREDENCIAIS` → a instância subiu sem o instance profile (rever §3, campo IAM instance profile). |
| `/analyze` → 502 `BEDROCK_RECURSO_NAO_ENCONTRADO` | model id / região. Confirme *Model access* liberado em us-east-1 para os 3 modelos. |
| `/analyze` → 502 `BEDROCK_SEM_PERMISSAO` | policy da role sem `bedrock:InvokeModel` para aquele modelo. Se estiver com policy apertada (§11), volte para `Resource: "*"`. |
| Não abre `http://<EC2_IP>:8008` | Security Group não libera a 8008 do seu IP; a instância não tem IP público; `docker compose ps` mostra `fin_web` fora do ar. |
| Containers morrendo sem erro claro no log | Memória. `free -m` na instância; suba o tipo (`t3.large`+). O `/batch` é o que mais consome (chamadas concorrentes ao Bedrock). |
| `curl 169.254.169.254/.../iam/...` não retorna a role | Instance profile não anexado. EC2 → Instances → Actions → Security → Modify IAM role → `FinGuardEC2Role`. |
| `AWS_PROFILE ... não existe` / `ProfileNotFound` | O `.env` está com `AWS_PROFILE=` **e** o compose emitindo essa var. No `docker-compose.yml` a linha `AWS_PROFILE` da âncora `x-aws-env` deve estar **comentada** (já vem assim). |
| `pull access denied` / `no basic auth credentials` no `docker compose pull` | Token do `docker login` no ECR expirou (~12h) ou a role não tem `AmazonEC2ContainerRegistryReadOnly` (rever §1.2). Refaça o login do §5.c. |
| `pull` funciona mas puxa versão antiga | `tools/publish_ecr.sh` publicou como `:latest` mas você não rodou `dc pull` de novo na instância antes do `up -d`. Confira o digest: `docker image inspect --format '{{.RepoDigests}}' apis-finguard/fin_risk` (ou o nome completo do ECR). |

Logs no `docker compose logs` já saem em stdout — para mandar ao CloudWatch,
configure o *log driver* `awslogs` no `docker-compose.yml` (ou rode o
CloudWatch agent). Fora do escopo do primeiro deploy.

---

## 11. Endurecer a policy (depois que funcionar)

Troque o `Resource: "*"` por ARNs específicos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeModels",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:*:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:*:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      ]
    },
    {
      "Sid": "Guardrails",
      "Effect": "Allow",
      "Action": "bedrock:ApplyGuardrail",
      "Resource": [
        "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:guardrail/<GUARDRAIL_ID>",
        "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:guardrail/<GUARDRAIL_ID_OUTPUT>"
      ]
    }
  ]
}
```

> Os modelos com prefixo `us.` são *inference profiles* de cross-region — por
> isso `InvokeModel` precisa da permissão **no profile e nos foundation-models
> em qualquer região** (`arn:aws:bedrock:*::foundation-model/...`). Se der
> `AccessDenied` em algum modelo, volte ao `Resource: "*"` e investigue com
> calma.

---

## 12. Próximos passos (opcionais, não bloqueiam)

- **HTTPS + domínio:** hoje a 8008 é HTTP puro. Opções: (a) ALB + certificado
  ACM apontando para a instância na 8008; (b) um `caddy`/`nginx` na própria
  instância com Let's Encrypt, fazendo proxy para a 8008.
- **Login na interface:** o `fin_web` não tem autenticação própria. Um proxy
  reverso com Basic Auth (ou o ALB com autenticação OIDC/Cognito) resolve.
- **Persistência resiliente:** os volumes vivem no disco da instância. Para
  sobreviver a *terminate*, use snapshots do EBS ou um volume EFS montado nos
  paths dos volumes.
- **Deploy automático:** só se quiser. Pipeline publica no ECR (`tools/
  publish_ecr.sh` ou equivalente em CI) → webhook/runner na instância roda
  `dc pull && dc up -d`. É um add-on; nada do que está acima depende disso.
- **ECS Fargate:** se precisar de HA / autoscaling de verdade — cada serviço
  vira um ECS service, a role de task dá a credencial, Cloud Map faz o DNS
  interno, ALB → só o `fin_web`, EFS para os volumes. É trabalho de infra
  (Terraform/CloudFormation), não de código.

---

## Checklist local → AWS (o resumo)

- [x] **Mesmas imagens** — publicadas no ECR por `tools/publish_ecr.sh`,
      instância só dá `pull` (via `docker-compose.prod.yml`).
- [ ] `.env`: **apagar** `AWS_ACCESS_KEY_ID` / `SECRET` / `SESSION_TOKEN`;
      **setar** `API_KEY`; `PROBE_ON_STARTUP=true`; conferir `ECR_REGISTRY`.
- [ ] **IAM role** `FinGuardEC2Role` anexada à instância (§1) — Bedrock +
      `AmazonEC2ContainerRegistryReadOnly`, substitui as chaves.
- [ ] **Security Group**: inbound só 22 e 8008 (§2).
- [ ] **Model access** do Bedrock liberado na conta, em us-east-1.
- [ ] `docker login` no ECR feito na instância (§5.c) antes do primeiro `pull`.
- Código: **zero alteração** — só config viaja para a instância.
