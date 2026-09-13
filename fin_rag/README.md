# fin_rag

API standalone que implementa o **nó de RAG** do FinGuard (Nível 3 do desafio
Future Minds). Indexa a **Política Interna** e devolve os trechos mais
relevantes para uma consulta — já formatados como `policy_context`, prontos
para o prompt do `fin_risk`.

- **Índice:** FAISS `IndexIDMap2(IndexFlatIP)` sobre vetores normalizados
  (produto interno = cosseno) + um `manifest.json` com o texto e os metadados
  de cada trecho.
- **Embeddings:** Amazon Bedrock — **Titan Embed Text v2** (1024 dim).
- **Ingestão incremental:** compara o hash de cada arquivo em `RAG_DOCS_DIR`
  com o manifest; só re-embeda o que é novo ou mudou, e remove o que sumiu.
- **Standalone:** com o índice vazio, `/v1/rag/retrieve` responde
  `count: 0` e um `policy_context` de aviso — não quebra.

A API **chama o Amazon Bedrock de verdade** (`InvokeModel`) para embutir a
consulta e os documentos. Se a chamada falhar, o endpoint responde **HTTP 502**
com `detail = {codigo, mensagem, erro_aws}` (taxonomia `BEDROCK_*`).

## Setup

> **Requer Python 3.12** (o `faiss-cpu` ainda não tem wheel para 3.14). O
> Dockerfile já usa `python:3.12-slim`.

```bash
cd fin_rag
py -3.12 -m venv .venv        # Windows
# python3.12 -m venv .venv    # Linux/Mac
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
copy .env.example .env        # Windows
```

A Política Interna já vem em `assets/docs/KS_POLITICA_INTERNA.pdf`. Coloque
outros PDFs/MDs/TXTs nessa pasta e rode a ingestão.

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8003
```

Docs: http://localhost:8003/docs

No startup, com os padrões: (1) faz 1 embedding real para checar conectividade
(aborta com `RuntimeError: [CODIGO] ...` se falhar — mesma tabela do
`fin_triage`); (2) dispara a ingestão incremental em background. Desligue com
`PROBE_ON_STARTUP=false` / `INGEST_ON_STARTUP=false`.

## Endpoints

### `GET /health`
Healthcheck → `{"status": "ok"}`.

### `POST /v1/rag/retrieve`
Busca os top-k trechos.

```json
// request
{ "query": "cliente menciona Banco Central e cobrança indevida no cartão", "k": 4 }

// response
{
  "chunks": [
    { "text": "…", "source": "KS_POLITICA_INTERNA.pdf", "chunk_idx": 7, "score": 0.71 }
  ],
  "count": 4,
  "policy_context": "Trechos relevantes da Política Interna:\n\n[1] Fonte: KS_POLITICA_INTERNA.pdf (trecho 7)\n…"
}
```

`k` é opcional (default `RAG_TOP_K`). Índice vazio → `count: 0` e
`policy_context` de aviso.

### `POST /v1/rag/ingest`
Dispara a ingestão incremental em **background**. Responde `202` na hora.

```json
{ "status": "started" }   // ou "already_running"
```

### `GET /v1/rag/ingest/status`
```json
{ "status": "done", "stats": { "chunks_added": 42, "skipped": ["KS_POLITICA_INTERNA.pdf"], "total_vectors_after": 42 }, "error": null }
```
`status`: `idle` | `running` | `done` | `error`.

### `GET /v1/rag/stats`
```json
{ "total_vectors": 42, "files": [ { "path": "KS_POLITICA_INTERNA.pdf", "chunks": 42, "hash": "9f2c1a0b3d4e" } ], "updated_at": "2026-09-09T21:00:00-03:00" }
```

### `POST /v1/rag/reset`
**Destrutivo:** apaga os arquivos do índice (`faiss.bin`, `manifest.json`).
O índice é regenerável via `/v1/rag/ingest`.

### Autenticação (opcional)
Se `API_KEY` estiver no `.env`, os endpoints (menos `/health` e
`/v1/rag/ingest/status`) exigem o header `X-API-Key`.

## Testes

```bash
pytest
```

Não tocam a AWS nem o índice real: `tests/conftest.py` substitui
`RagService._embed_one` por um stub determinístico e aponta o índice para um
diretório temporário.

## Integração com o grafo do FinGuard

Corresponde ao nó de RAG. O orquestrador chama `POST /v1/rag/retrieve` com
`query = texto da reclamação + dimensões da triagem`, e passa o
`policy_context` recebido no corpo da chamada ao `fin_risk` — que **não**
conhece este serviço.

## Docker

```bash
docker build -t fin-rag .
docker run --env-file .env -p 8003:8003 \
  -v "$PWD/assets/docs:/app/assets/docs:ro" \
  -v fin_rag_index:/app/assets/index \
  fin-rag
```
