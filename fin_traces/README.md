# fin_traces

API standalone que implementa o **log de execução** e o **painel decisório**
do FinGuard (Nível 3 do desafio Future Minds).

- **Log de execução** — um `deque` em memória (sem limite) com uma entrada por
  reclamação processada: id, prévia do texto, se foi bloqueada, categoria,
  urgência, risco, canal, prazo, área responsável e a latência de cada etapa.
- **Painel decisório** — agregações sobre o log: matriz **urgência × risco**,
  contagem por canal (com destaque de críticas), por área responsável e por
  prazo de resposta, além da latência média.

Serviço **determinístico**: não usa AWS nem chama outros serviços. Opcionalmente
persiste o log em disco (`TRACES_PERSIST_PATH`) para sobreviver a restarts.
Roda em Python 3.14.

## Quem alimenta o log

O `fin_orchestrator` faz `POST /v1/traces` ao fim de cada reclamação (passo 7
do pipeline), com a entrada já montada. O `fin_web` consome `GET /v1/traces` e
`GET /v1/decisorio/stats` (via proxy do orquestrador) para renderizar as telas
`traces.html.j2` e `politica_decisoria.html.j2`.

## Setup

```bash
cd fin_traces
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # Windows
```

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8007
```

Docs interativas: http://localhost:8007/docs

## Endpoints

### `GET /health`
`{"status": "ok"}`.

### `POST /v1/traces` → `201`
Registra uma entrada. `timestamp` e `total_ms` são preenchidos se vierem
ausentes (`total_ms` = soma de `timings_ms`). Campos extras são tolerados.

```json
{
  "trace_id": "a1b2c3d4",
  "text_preview": "cobrança dupla no cartão…",
  "blocked": false,
  "category": "Cobrança Indevida",
  "urgency": "Crítica",
  "risk_level": "Alto",
  "product": "Cartão de Crédito",
  "canal": "Banco Central",
  "prazo_resposta": "4 horas",
  "area_responsavel": "Ouvidoria",
  "timings_ms": {"guardrail_input": 10, "triage": 100, "risk": 200, "report": 5},
  "total_ms": 315
}
```
→ `{"status": "stored", "count": 42}`

### `GET /v1/traces`
Contexto completo do log (o mesmo dict que o monólito passava ao
`traces.html.j2`): `{count, has_data, st, traces:[...]}`, já com larguras de
barra e pills HTML por linha.

### `GET /v1/traces/stats`
Só o bloco `st` — estatísticas (`mean/median/stdev/cv/p95/p99`) de `total_ms`,
`triage`, `risk`, `report`.

### `GET /v1/decisorio/stats`
Agregações do painel decisório: `total`, `bloqueados`, `processados`,
`avg_total_ms`, `urgency`, `risk`, `canais`, `areas`, `prazos`, `matrix`
(urgência × risco), `urgency_levels`, `risk_levels`.

### `POST /v1/traces/recompose`
Reconstrói entradas de log a partir do `results` de um relatório batch
(payload do `fin_report_writer`). Injeta na ordem cronológica (mais antigo
primeiro). → `{"status": "ok", "recomposed": 12}`

```json
{ "results": [ { "id": "R001", "texto_original": "...", "category": "...",
  "urgency": "...", "risk_level": "...", "canal": "...",
  "timings_ms": {"triage": 40, "risk": 55, "report": 3} } ] }
```

### `DELETE /v1/traces`
Limpa o log. → `{"status": "ok", "cleared": 42}`

### Autenticação (opcional)
Se `API_KEY` estiver definida, as rotas de escrita (`POST /v1/traces`,
`POST /v1/traces/recompose`, `DELETE /v1/traces`) exigem `X-API-Key`.

## Persistência opcional

Com `TRACES_PERSIST_PATH=/data/traces.json`, o deque é despejado em JSON a cada
escrita e recarregado no startup. Vazio → log só em memória (perde no restart).

## Testes

```bash
pytest
```

Log em memória, limpo entre testes; um teste cobre o ciclo de persistência.

## Docker

```bash
docker build -t fin-traces .
docker run --env-file .env -p 8007:8007 fin-traces
# com persistência:
docker run --env-file .env -e TRACES_PERSIST_PATH=/data/traces.json \
  -v $(pwd)/data:/data -p 8007:8007 fin-traces
```
