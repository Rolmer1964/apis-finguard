# fin_triage

API standalone que implementa o **nó de triagem** do FinGuard (Nível 3 do
desafio Future Minds). Classifica uma reclamação bancária via **Amazon Bedrock
— Claude Haiku**:

- **categoria** — Cobrança Indevida · Atendimento · Fraude/Segurança · Produto/Serviço · Cancelamento · Outros
- **produto** — Cartão de Crédito · Conta Corrente · Empréstimo · Investimentos · Seguros · Não Identificado
- **sentimento** — Positivo · Neutro · Negativo · Crítico
- **urgência** — Baixa · Média · Alta · Crítica (com os gatilhos obrigatórios da POL-SAC-001 no prompt)
- **resumo** — 2-3 linhas, neutro, com palavrões mascarados por `***`

A API **chama o Amazon Bedrock de verdade** (`InvokeModel`) — não há fallback
local. Se a chamada falhar, o endpoint responde **HTTP 502** com
`detail = {codigo, mensagem, erro_aws}` (mesma taxonomia `BEDROCK_*` do
`fin_guardrail`). Se o modelo devolver um JSON inválido, a triagem cai em
valores neutros (`Outros` / `Não Identificado` / `Neutro` / `Baixa`).

Credenciais AWS: em dev local, `AWS_PROFILE` aponta para um profile de
`~/.aws/config` com acesso ao Bedrock (rode `aws sso login` antes). Na EC2,
deixe `AWS_PROFILE` vazio — vale a IAM role da instância (IMDS).

## Setup

```bash
cd fin_triage
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```

Edite o `.env` com o `AWS_PROFILE` (ou chaves) e, se quiser, o modelo.

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8002
```

Docs interativas: http://localhost:8002/docs

### Probe de conectividade no startup

Com `PROBE_ON_STARTUP=true` (padrão), a API faz **uma chamada real de 1 token**
ao Bedrock ao subir. Se o Bedrock não estiver acessível, o processo **não sobe**
e loga `RuntimeError: [CODIGO] mensagem`:

| Código | Significado |
|---|---|
| `BEDROCK_SEM_CREDENCIAIS` | Nenhuma credencial AWS resolvida. |
| `BEDROCK_PROFILE_INEXISTENTE` | `AWS_PROFILE` não existe em `~/.aws/config`. |
| `BEDROCK_SSO_EXPIRADO` | Sessão SSO / token expirado — rode `aws sso login`. |
| `BEDROCK_CREDENCIAL_INVALIDA` | Chave / segredo / token rejeitados. |
| `BEDROCK_SEM_PERMISSAO` | Falta `bedrock:InvokeModel` na policy IAM. |
| `BEDROCK_RECURSO_NAO_ENCONTRADO` | `BEDROCK_MODEL_TRIAGE` / `AWS_REGION` errados, ou modelo não habilitado. |
| `BEDROCK_REGIAO_AUSENTE` | Nenhuma `AWS_REGION` configurada. |
| `BEDROCK_SEM_CONECTIVIDADE` | Sem rota de rede até o `bedrock-runtime`. |
| `BEDROCK_THROTTLING` | Bedrock limitando as chamadas. |
| `BEDROCK_ERRO_DESCONHECIDO` | Outra falha — ver `erro_aws` no log. |

Defina `PROBE_ON_STARTUP=false` para pular (CI, ou subir sem AWS).

## Endpoints

### `GET /health`
Healthcheck → `{"status": "ok"}`.

### `POST /v1/triage`
Classifica a reclamação.

```json
// request
{ "text": "Já é a terceira vez que ligo pedindo o estorno de uma cobrança que não fiz no meu cartão.", "product_hint": "Cartão de Crédito" }

// response
{
  "category": "Cobrança Indevida",
  "product": "Cartão de Crédito",
  "sentiment": "Crítico",
  "urgency": "Alta",
  "summary": "Cliente relata cobrança não reconhecida no cartão de crédito e múltiplas tentativas de contato sem resolução."
}
```

`product_hint` é opcional — só uma pista. Se o modelo não devolver um produto
da lista, o resultado é `Não Identificado`.

Exemplo `curl`:

```bash
curl -X POST http://localhost:8002/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"text":"Fui cobrado duas vezes na fatura e ninguém resolve."}'
```

### Autenticação (opcional)
Se `API_KEY` estiver definida no `.env`, `POST /v1/triage` exige o header
`X-API-Key: <valor>`.

## Testes

```bash
pytest
```

Não tocam a AWS: `tests/conftest.py` substitui `TriageService._call_llm` por
um stub e desliga o probe de startup.

## Integração com o grafo do FinGuard

Corresponde ao nó `triage` da arquitetura do Nível 3. O orquestrador chama
`POST /v1/triage` **depois** do guardrail de entrada e **antes** do
`fin_rag` / `fin_risk` — o resultado da triagem alimenta a query do RAG e o
prompt de risco.

## Docker

```bash
docker build -t fin-triage .
docker run --env-file .env -p 8002:8002 fin-triage
```
