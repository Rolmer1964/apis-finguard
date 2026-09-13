# apis_finguard

O FinGuard — triagem automatizada de reclamações bancárias — dividido em **9
serviços independentes**: 7 folhas de domínio, um orquestrador e uma interface.

Cada serviço sobe sozinho, responde `GET /health` e tem seu próprio
`README.md`, `Dockerfile`, testes e `.env.example`. Nada de import entre
serviços — o código comum é copiado, não compartilhado.

## Arquitetura

```
                          ┌───────────── fin_web (8008) ─── SSR, fala só com ↓
                          │
                    fin_orchestrator (8000) ─── pipeline + proxies de leitura
                          │  (único que conhece o endereço das folhas)
        ┌─────────┬───────┼─────────┬─────────────┬───────────┬──────────┐
   fin_guardrail  fin_triage  fin_rag   fin_risk  fin_consolidate  fin_report_writer  fin_traces
      (8001)       (8002)    (8003)    (8004)       (8005)            (8006)            (8007)
      Bedrock      Haiku    Titan+FAISS Sonnet    determinístico     Jinja2/arquivos   memória
      Guardrails                                                                        + painel
```

Fluxo de uma reclamação (`POST /analyze` no orquestrador): guardrail de
entrada → triagem → RAG → risco → consolidação → guardrail de saída →
registro no log. Se o guardrail de entrada bloqueia, encerra ali. O `/batch`
processa um CSV com controle adaptativo de vazão (AIMD) e gera um relatório.

| Serviço | Porta | AWS | Função (resumo) |
|---|---|---|---|
| fin_guardrail | 8001 | sim | valida entrada / sanitiza saída (Bedrock Guardrails + PII + profanidade) |
| fin_triage | 8002 | sim | classifica categoria, produto, sentimento, urgência, resumo (Claude Haiku) |
| fin_rag | 8003 | sim | retrieval sobre a Política Interna (Titan Embeddings + FAISS) |
| fin_risk | 8004 | sim | nível de risco + ações imediatas (Claude Sonnet) |
| fin_consolidate | 8005 | não | regras POL-SAC-001: SLA, área responsável, overrides de canal |
| fin_report_writer | 8006 | não | relatório gerencial (JSON/CSV/MD/HTML) + agregações |
| fin_traces | 8007 | não | log de execução em memória + painel decisório |
| fin_orchestrator | 8000 | não | roda o pipeline por HTTP + proxies de leitura para a UI |
| fin_web | 8008 | não | interface HTML server-side (consome só o orquestrador) |

Explicação detalhada de cada API em [`docs/explicacoes_apis.md`](docs/explicacoes_apis.md).
Plano da divisão e histórico em [`docs/PLANO_DIVISAO.md`](docs/PLANO_DIVISAO.md).

## Rodar o stack (docker compose)

**Pré-requisitos:** Docker + credencial AWS com acesso ao Bedrock (modelos
Haiku, Sonnet e Titan habilitados na região) e um **Guardrail provisionado**.

```bash
cp .env.example .env
#   edite .env:
#   - GUARDRAIL_ID           (obrigatório — sem ele o fin_guardrail não sobe)
#   - AWS: AWS_PROFILE + HOST_AWS_DIR=~/.aws   (após 'aws sso login')
#          ou as 3 chaves estáticas AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN
docker compose up --build
```

Abra **http://localhost:8008**. Cada API tem `/<porta>/docs`.

Ordem de subida é automática: as 7 folhas primeiro (healthcheck), depois o
orquestrador, depois o `fin_web`. Volumes nomeados persistem o índice do RAG
(`rag_index`), os relatórios (`report_output`) e o log de execução
(`traces_data`).

### Sem AWS

Não há caminho 100% offline para o pipeline inteiro: o **fin_guardrail sempre
faz um probe real no Bedrock no startup** e não sobe sem ele. O que dá para
subir sem credencial: `fin_consolidate`, `fin_report_writer`, `fin_traces` e
`fin_web` (este último abre, mas as telas de dados dão 502). `fin_triage`,
`fin_rag` e `fin_risk` sobem com `PROBE_ON_STARTUP=false` e só falham (502)
quando chamados.

```bash
docker compose up fin_consolidate fin_report_writer fin_traces
```

## Verificar

```bash
# com o stack no ar:
python tools/smoke_e2e.py
```

Confere a saúde das folhas e o **shape** de `/analyze` e `/batch` contra o do
monólito finguard8. Ver [`tools/README.md`](tools/README.md).

## Deploy na AWS

O mesmo `docker-compose.yml` e as mesmas imagens rodam numa EC2 — a única
diferença é configuração: a instância usa uma **IAM role** (sem chaves no
`.env`) e o Security Group libera só a porta 8008. Passo a passo (IAM policy,
Security Group, EC2, `.env`, deploy manual) em
[`docs/DEPLOY_AWS.md`](docs/DEPLOY_AWS.md).

## Desenvolver um serviço isolado

```bash
cd fin_<serviço>
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port <porta>
pytest
```

`fin_rag` exige **Python 3.12** (o `faiss-cpu` não tem wheel para 3.14); os
demais rodam em 3.12+ (a suíte de testes roda em 3.14 nas máquinas de dev).

## Autenticação

`API_KEY` no `.env` raiz, se preenchida, é injetada em **todos** os serviços;
o orquestrador e o `fin_web` a repassam no header `X-API-Key`. Vazia = sem auth
(padrão em dev).

## Layout

```
fin_<serviço>/        um serviço FastAPI autocontido (app/, tests/, Dockerfile, README)
docker-compose.yml    o stack completo (9 serviços + rede + healthchecks + volumes)
.env.example          configuração compartilhada do compose
tools/                utilitários de dev (smoke E2E, geradores de CSV)
docs/                 plano da divisão, explicações das APIs, visão de negócio
```
