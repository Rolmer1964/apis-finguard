# fin_orchestrator

**Ponto único de entrada** do FinGuard (Nível 3 do desafio Future Minds).
Duas faces, um serviço:

1. **Pipeline** — reproduz o fluxo fim-a-fim do monólito, orquestrando as 7
   folhas por HTTP: guardrail de entrada → triagem → RAG → risco →
   consolidação → guardrail de saída → registro no log. Inclui o batch de CSV
   com controle adaptativo (**AIMD**).
2. **Proxies de leitura** — é o único serviço que conhece o endereço de todas
   as folhas; expõe repasses finos (relatórios, traces, painel decisório,
   stats/ingest do RAG, artefatos) para o `fin_web`, que fala **só** com ele.

Sem AWS direto — delega tudo às folhas. Roda em Python 3.14.

## Fluxo de um registro (`/analyze`)

| # | Chamada | Observação |
|---|---|---|
| 1 | `POST {GUARDRAIL_URL}/v1/guardrail/input` | Se `blocked`, encerra com a mensagem — nada mais roda. |
| 2 | `POST {TRIAGE_URL}/v1/triage` | `{category, product, sentiment, urgency, summary}` |
| 3 | `POST {RAG_URL}/v1/rag/retrieve` | query = texto + dimensões da triagem → `policy_context` + `count` |
| 4 | `POST {RISK_URL}/v1/risk` | recebe `policy_context` e `rag_chunks_count` no corpo |
| 5 | `POST {CONSOLIDATE_URL}/v1/consolidate` | aplica a POL-SAC-001 |
| 6 | `POST {GUARDRAIL_URL}/v1/guardrail/output` | para `texto_original`, `summary`, `risk_justification` |
| 7 | `POST {TRACES_URL}/v1/traces` | entrada consolidada do log (best-effort — não derruba o pipeline) |

A resposta tem o **mesmo shape da finguard8**:
`{trace_id, blocked, triage:{…}, risk:{…}, …consolidado, timings_ms}`.

> **`timings_ms` agora inclui latência de rede.** As chaves são
> `guardrail_input, triage, rag, risk, report, guardrail_output` (o monólito
> não tinha `rag` — o RAG vivia dentro do nó de risco). O `total_ms` postado
> no log soma todas elas.

Se **qualquer folha** responde não-2xx (ex.: Bedrock sem permissão) ou não
responde, o `/analyze` devolve **502** com
`detail = {service, downstream_status, erro}`, preservando o `detail` original
da folha.

## Setup

```bash
cd fin_orchestrator
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # Windows
```

Ajuste as 7 URLs no `.env` (localhost em dev; `http://<serviço>:<porta>` em
compose). Se as folhas exigirem `X-API-Key`, ponha a **mesma** chave em
`API_KEY` — ela é repassada a cada folha.

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs · Requer as folhas no ar (8001–8007).

## Endpoints

### Pipeline
- `POST /analyze` — body `{text, product_hint?, canal?}` → payload consolidado (shape da finguard8).
- `POST /analyze-form` — form `text, product_hint, canal`; roda o pipeline, persiste um relatório unitário (label "Consulta unitária") e devolve `{stem, paths, result}`.
- `POST /batch` — `multipart` com `file` (CSV com coluna `texto_reclamacao`; opcionais `produto`, `canal`, `id`) e `label`. Processa em passes AIMD e gera o relatório no `fin_report_writer`. → `{stem, paths, total, ok, blocked, errors, pass_stats, elapsed_s}`.

### Saúde
- `GET /health` — healthcheck local.
- `GET /health/downstream` — pinga `GET /health` de cada folha → `{status: ok|degraded, services:{…}}` (503 se alguma folha estiver fora).

### Proxies de leitura (consumidos pelo `fin_web`)
Repasse 1:1 (status, corpo, content-type) para o serviço dono:

| Rota no orquestrador | Folha |
|---|---|
| `GET /reports`, `GET /reports/{stem}` (+ `/html`), `DELETE /reports/{stem}`, `GET /records/{id}`, `GET /output/{filename}` | `fin_report_writer` |
| `GET /traces`, `GET /decisorio/stats`, `POST /traces/recompose` | `fin_traces` |
| `GET /rag/stats`, `POST /rag/ingest`, `GET /rag/ingest/status` | `fin_rag` |

## Controle adaptativo do batch (AIMD)

Cada passe roda os pendentes num `ThreadPoolExecutor`. Registros que batem em
**throttling** (`BEDROCK_THROTTLING` de qualquer folha) são adiados para o
próximo passe. Ao fim de cada passe:

- throttle > 5% → `workers //= 2`, `delay += 1s` (backoff multiplicativo);
- throttle = 0 → `workers += 1`, `delay -= 0.5s` (recuperação aditiva);
- `retries` decai 1 por passe; espera entre passes = `BATCH_RETRY_DELAY * (1 + throttle_rate)`.

Esgotados os `BATCH_MAX_PASSES`, o registro entra no relatório como `Erro`.

## Testes

```bash
pytest
```

Não sobem folhas: o pipeline testa com `app.clients` monkeypatchado; os
proxies, com `respx` interceptando o `httpx`.

## Docker

```bash
docker build -t fin-orchestrator .
docker run --env-file .env -p 8000:8000 fin-orchestrator
```
