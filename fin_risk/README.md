# fin_risk

API standalone que implementa o **nó de avaliação de risco** do FinGuard
(Nível 3 do desafio Future Minds). Avalia uma reclamação bancária via **Amazon
Bedrock — Claude Sonnet**:

- **risk_level** — Baixo · Médio · Alto · Crítico
- **risk_justification** — 2-3 frases, tom profissional, citando a seção da POL-SAC-001 que embasa a decisão
- **acoes_recomendadas** — até 5 ações imediatas obrigatórias (§2/§3 da POL-SAC-001), concretas, com prazos e área responsável quando a política os define
- **rag_chunks_used** — quantos trechos da Política Interna compuseram o contexto

## O RAG não é chamado aqui

No monólito, o agente de risco chamava o RAG (`retrieve()` + `format_for_prompt()`)
para montar o contexto da Política Interna. Neste serviço esse contexto chega
**pronto no corpo da requisição** (`policy_context`), montado pelo
`fin_orchestrator` a partir do `fin_rag`. `fin_risk` só chama o Bedrock.

- `policy_context` **ausente** → usa `(nenhum trecho da política interna disponível)`.
- `rag_chunks_used` na resposta = `rag_chunks_count` do corpo (ou `0`).

Como `fin_risk` não depende do FAISS, roda em **Python 3.14** (só o `fin_rag`
está preso ao 3.12).

A API **chama o Amazon Bedrock de verdade** (`InvokeModel`) — não há fallback
local. Se a chamada falhar, o endpoint responde **HTTP 502** com
`detail = {codigo, mensagem, erro_aws}` (mesma taxonomia `BEDROCK_*` do
`fin_guardrail` / `fin_triage`). Se o modelo devolver um JSON inválido, o
resultado cai em valores neutros (`Baixo` / justificativa vazia / lista vazia).

Credenciais AWS: em dev local, `AWS_PROFILE` aponta para um profile de
`~/.aws/config` com acesso ao Bedrock (rode `aws sso login` antes). Na EC2,
deixe `AWS_PROFILE` vazio — vale a IAM role da instância (IMDS).

## Setup

```bash
cd fin_risk
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
uvicorn app.main:app --reload --port 8004
```

Docs interativas: http://localhost:8004/docs

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
| `BEDROCK_RECURSO_NAO_ENCONTRADO` | `BEDROCK_MODEL_RISK` / `AWS_REGION` errados, ou modelo não habilitado. |
| `BEDROCK_REGIAO_AUSENTE` | Nenhuma `AWS_REGION` configurada. |
| `BEDROCK_SEM_CONECTIVIDADE` | Sem rota de rede até o `bedrock-runtime`. |
| `BEDROCK_THROTTLING` | Bedrock limitando as chamadas. |
| `BEDROCK_ERRO_DESCONHECIDO` | Outra falha — ver `erro_aws` no log. |

Defina `PROBE_ON_STARTUP=false` para pular (CI, ou subir sem AWS).

## Endpoints

### `GET /health`
Healthcheck → `{"status": "ok"}`.

### `POST /v1/risk`
Avalia o risco da reclamação.

```json
// request
{
  "text": "Já é a terceira vez que ligo e ninguém resolve. Vou denunciar ao Banco Central.",
  "triage": {
    "category": "Atendimento",
    "product": "Conta Corrente",
    "sentiment": "Crítico",
    "urgency": "Crítica",
    "summary": "Cliente relata múltiplas tentativas de contato sem resolução e ameaça acionar o Banco Central."
  },
  "policy_context": "Trechos relevantes da Política Interna:\n\n[1] Fonte: KS_POLITICA_INTERNA.pdf (trecho 3)\n...",
  "rag_chunks_count": 4
}

// response
{
  "risk_level": "Alto",
  "risk_justification": "Há risco reputacional e regulatório pela menção ao Banco Central, conforme §3.1 da POL-SAC-001. ...",
  "acoes_recomendadas": [
    "Registrar a reclamação como prioritária e responder em até 5 dias úteis",
    "Encaminhar à área de Ouvidoria",
    "Preparar resposta formal para eventual demanda do Banco Central"
  ],
  "rag_chunks_used": 4
}
```

`policy_context` e `rag_chunks_count` são opcionais. Sem `policy_context`, o
serviço avalia só com a triagem e o texto, anotando `rag_chunks_used: 0`.

Exemplo `curl`:

```bash
curl -X POST http://localhost:8004/v1/risk \
  -H "Content-Type: application/json" \
  -d '{"text":"compra que não reconheço, é fraude","triage":{"category":"Fraude/Segurança","product":"Cartão de Crédito","sentiment":"Crítico","urgency":"Crítica","summary":"Transação não reconhecida."}}'
```

### Autenticação (opcional)
Se `API_KEY` estiver definida no `.env`, `POST /v1/risk` exige o header
`X-API-Key: <valor>`.

## Testes

```bash
pytest
```

Não tocam a AWS: `tests/conftest.py` substitui `RiskService._call_llm` por
um stub e desliga o probe de startup.

## Integração com o grafo do FinGuard

Corresponde ao nó `risk` da arquitetura do Nível 3. O `fin_orchestrator` chama
`POST /v1/risk` **depois** do `fin_triage` e do `fin_rag` — injeta o
`policy_context` (saída do `fin_rag`) no corpo — e **antes** do
`fin_consolidate`.

## Docker

```bash
docker build -t fin-risk .
docker run --env-file .env -p 8004:8004 fin-risk
```
