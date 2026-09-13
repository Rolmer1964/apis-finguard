# tools/

Utilitários de desenvolvimento e verificação. Ficam **fora** dos serviços —
nenhum é importado por uma API. Só stdlib; rode com qualquer Python 3.11+.

| Script | Para quê |
|---|---|
| `smoke_e2e.py` | Smoke ponta a ponta contra um stack já no ar (`docker compose up`). Confere saúde das folhas e o **shape** de `/analyze` e `/batch` contra o do monólito finguard8. |
| `gerar_csv.py` | Gera um CSV grande e variado de reclamações bancárias (pools de texto por categoria + casos-limite: elogios, irrelevantes, ameaças, prompt injection). |
| `generate_synthetic.py` | Gera um CSV sintético menor a partir de templates parametrizados (mais rápido, menos realista). |
| `backfill_meta_timing.py` | **Legado.** Extrai `started_at/finished_at/elapsed_s` de HTMLs de relatório antigos e grava nos `.meta.json`. Só útil para relatórios gerados antes de o `fin_report_writer` passar a escrever o meta sozinho. |

## smoke_e2e.py

```bash
# stack local via compose
python tools/smoke_e2e.py

# endereços custom / com auth
python tools/smoke_e2e.py --orch http://localhost:8000 --web http://localhost:8008 --api-key SUACHAVE

# só o pipeline, sem os checks de tela
python tools/smoke_e2e.py --no-web
```

Etapas: (1) `/health` e `/health/downstream` do orquestrador; (2) `/analyze`
de uma reclamação benigna — valida as 16 chaves do payload e as 6 chaves de
`timings_ms`; (3) `/analyze` de um texto abusivo — espera `blocked=true`;
(4) `/batch` de um CSV mínimo + leitura do relatório gerado; (5) telas do
`fin_web`.

Falha (código 1) só em erro de shape ou HTTP inesperado. Etapas que dependem
de AWS viram **AVISO** quando a folha está fora — útil para checar o
cabeamento mesmo sem credencial Bedrock.

## Geradores de CSV

```bash
python tools/gerar_csv.py data/reclamacoes.csv          # ~500 linhas
python tools/generate_synthetic.py 200 data/mini.csv    # N linhas
```

Colunas: `id, data_reclamacao, canal, texto_reclamacao, produto, status`.
O pipeline só exige `texto_reclamacao`; `produto`, `canal` e `id` são opcionais.
Envie pelo `fin_web` (aba "Processamento em lote") ou direto em
`POST {orquestrador}/batch`.
