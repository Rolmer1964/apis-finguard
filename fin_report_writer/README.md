# fin_report_writer

API standalone que implementa o **nó de relatório** do FinGuard (Nível 3 do
desafio Future Minds). A partir de uma lista de registros já processados
(triagem + risco + consolidação), gera o **relatório gerencial**:

- **JSON** — os registros crus (`{stem}.json`)
- **CSV** — uma linha por reclamação (`{stem}.csv`)
- **Markdown** — resumo textual com distribuições e recomendações (`{stem}.md`)
- **HTML** — dashboard com Chart.js, tabela de críticas e modal de detalhe, renderizado sob demanda
- **`.meta.json`** — metadados da execução (label, filename, tempos, passes AIMD)

Também **agrega** as distribuições (por categoria, produto, urgência, risco,
sentimento, canal), monta a lista de **recomendações** e **serve** os artefatos.

Serviço **determinístico**: não usa AWS nem chama outros serviços. Depende só
de `jinja2` (além do stack FastAPI). Roda em Python 3.14.

## O `stem`

Cada relatório é identificado por um `stem` no formato
`report_YYYY-MM-DD-HH-MM-SS` (fuso de Brasília, UTC-3), gerado pelo serviço no
`POST`. É a chave de todas as demais rotas.

## Setup

```bash
cd fin_report_writer
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```

`OUTPUT_DIR` no `.env` define onde os artefatos são gravados (default
`./output` em dev; volume `/app/output` no container).

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8006
```

Docs interativas: http://localhost:8006/docs

## Endpoints

### `GET /health`
Healthcheck → `{"status": "ok"}`.

### `POST /v1/reports`
Gera os artefatos de uma execução em batch.

```json
// request
{
  "results": [
    {
      "id": "R001", "canal": "Banco Central", "texto_original": "...",
      "category": "Cobrança Indevida", "product": "Cartão de Crédito",
      "sentiment": "Crítico", "urgency": "Crítica", "summary": "...",
      "prazo_resposta": "1 dia útil", "area_responsavel": "Ouvidoria",
      "risk_level": "Alto", "risk_justification": "...",
      "acoes_recomendadas": ["...", "..."],
      "timings_ms": {"triage": 120, "risk": 300, "report": 4}
    }
  ],
  "meta": {
    "started_at": "2026-09-10T10:00:00-03:00",
    "finished_at": "2026-09-10T10:03:12-03:00",
    "elapsed_s": 192.0,
    "label": "lote de setembro",
    "filename": "reclamacoes.csv",
    "pass_stats": []
  }
}

// response
{
  "stem": "report_2026-09-10-10-03-12",
  "paths": {
    "json": "/app/output/report_2026-09-10-10-03-12.json",
    "csv":  "/app/output/report_2026-09-10-10-03-12.csv",
    "md":   "/app/output/report_2026-09-10-10-03-12.md"
  }
}
```

`meta` é opcional; sem ela, o `.meta.json` não é gravado.

### `GET /v1/reports`
Lista os relatórios (mais recentes primeiro) → `{reports: [...], total}`.

### `GET /v1/reports/{stem}`
Contexto agregado do relatório em JSON (`total`, `critical`, `by_category`,
`by_product`, `by_urgency`, `by_risk`, `by_sentiment`, `by_canal`,
`recommendations`, tempos).

### `GET /v1/reports/{stem}/html`
O relatório renderizado (`report.html.j2`) — dashboard Chart.js + modal.

### `GET /v1/reports/{stem}/record/{id}`
Registro completo por `id` dentro daquele relatório. Substitui o
`/api/record/{id}` do monólito; consumido pelo `_modal.html.j2` como fallback
quando o `id` não está no `INDEX` local da página.

### `DELETE /v1/reports/{stem}`
Remove `.json`, `.meta.json`, `.csv` e `.md`. `stem` fora do formato → 400.

### `GET /output/{filename}`
Serve o artefato bruto (`FileResponse`). Nome de arquivo é validado contra
path traversal.

### Autenticação (opcional)
Se `API_KEY` estiver definida no `.env`, as rotas de **escrita**
(`POST /v1/reports`, `DELETE /v1/reports/{stem}`) exigem o header
`X-API-Key: <valor>`.

## Testes

```bash
pytest
```

Gravam num `OUTPUT_DIR` temporário (ver `tests/conftest.py`), não tocam
`./output`.

## Integração com o grafo do FinGuard

Corresponde ao nó `report` da arquitetura do Nível 3. O `fin_orchestrator`
chama `POST /v1/reports` **ao fim de um batch**, com a lista consolidada, e
expõe proxies de leitura (`/reports`, `/reports/{stem}`, `/output/{filename}`,
`/records/{id}`) para o `fin_web`.

## Docker

```bash
docker build -t fin-report-writer .
docker run --env-file .env -p 8006:8006 -v $(pwd)/output:/app/output fin-report-writer
```
