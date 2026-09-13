# fin_web

Interface HTML **server-side** do FinGuard (porta **8008**). É a camada de
apresentação — formulário individual, processamento em lote, listagem e
detalhe de relatórios, log de execução, painel decisório, admin, ADR e
relatório técnico.

Depende **só** do `fin_orchestrator`. Não conhece o endereço de nenhuma folha,
não usa AWS e não guarda estado (exceto o recorde do joguinho da tela de
espera do batch, um JSON local). Roda em Python 3.12+ (só Python puro).

## Como funciona

Cada tela busca os dados nos **proxies de leitura** do orquestrador e renderiza
o template. Os envios repassam o form ao orquestrador e devolvem um **303**
para `/report/{stem}`, igual ao monólito.

| Rota (browser) | O que faz | Chama no orquestrador |
|---|---|---|
| `GET /` | formulário individual + lote | — |
| `GET /reports` | lista de relatórios | `GET /reports` |
| `GET /report/{stem}` | relatório gerencial (Chart.js + modal) | `GET /reports/{stem}` |
| `GET /traces` | log de execução (com stats de timing) | `GET /traces` |
| `GET /politica-decisoria` | painel decisório (client-side) | `GET /decisorio/stats` (via `/api/decisorio/stats`) |
| `GET /admin` | estado agregado + re-ingestão | `GET /reports`, `/rag/stats`, `/traces` |
| `GET /adr`, `GET /relatorio-tecnico` | HTML estático de `app/assets/` | — |
| `POST /analyze-form` | roda o pipeline, persiste relatório unitário | `POST /analyze-form` → 303 |
| `POST /batch` | processa um CSV (AIMD) | `POST /batch` → 303 |
| `DELETE /report/{stem}` | remove um relatório | `DELETE /reports/{stem}` |
| `POST /traces/recompose?stem=` | reconstrói o log a partir de um relatório | `GET /output/{stem}.json` + `POST /traces/recompose` |
| `GET /records/{id}` | registro completo (fallback do modal) | `GET /records/{id}` |
| `GET /output/{filename}` | baixa o artefato bruto (json/csv/md) | `GET /output/{filename}` |
| `POST /ingest`, `GET /ingest/status` | re-ingestão do RAG (tela admin) | `POST /rag/ingest`, `GET /rag/ingest/status` |
| `GET\|POST /snake/record` | recorde do joguinho (JSON local) | — |
| `GET /health` | healthcheck local | — |

### Diferenças vs. o monólito

- **Templates de relatório** (`report.html.j2`, `reports.html.j2`, `_modal`,
  `_style`, `_header`) foram **copiados** do `fin_report_writer`; os demais
  (`index`, `traces`, `admin`, `politica_decisoria`) do monólito.
- O modal (`_modal.html.j2`) busca cada registro por `GET /records/{id}`
  (proxy → `fin_report_writer`), não mais `/api/record/{id}`.
- A tela **`/admin` é read-only** para estado: os botões de "zerar" saíram
  porque o orquestrador não expõe proxy para `rag/reset`, `DELETE /traces`
  nem remoção em massa de relatórios. Só a ação "Re-ingerir documentos"
  permanece. Para zerar, use os endpoints de cada serviço diretamente.
- `timings_ms` (mostrado no modal e no log) inclui latência de rede e tem a
  chave extra `rag` — herdado do orquestrador.

## Setup

```bash
cd fin_web
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # Windows
```

`.env`: `ORCHESTRATOR_URL` (localhost:8000 em dev; `http://fin_orchestrator:8000`
em compose) e, se o orquestrador exigir, `API_KEY` (a **mesma** chave — é
repassada).

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8008
```

Abre em http://localhost:8008 · docs em `/docs`. Requer o `fin_orchestrator`
no ar (que por sua vez requer as 7 folhas). Sem o orquestrador, `/` e `/health`
respondem, as telas de dados dão 502 e `/admin` abre degradada.

## Testes

```bash
pytest
```

Não sobe o orquestrador: o `httpx` é interceptado com `respx`. 20 testes
cobrindo render das telas, redirects dos envios, proxies e o recorde local.

## Docker

```bash
docker build -t fin-web .
docker run --env-file .env -p 8008:8008 fin-web
```
