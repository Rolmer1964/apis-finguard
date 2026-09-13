"""Fixtures dos testes.

As folhas apontam para hosts fictícios `*.test` (definidos antes de importar
`app.config`, que cacheia as settings). O pipeline é testado com as funções de
`app.clients` monkeypatchadas; os proxies, com `respx` interceptando o httpx.
"""

import os

os.environ.setdefault("GUARDRAIL_URL", "http://guardrail.test")
os.environ.setdefault("TRIAGE_URL", "http://triage.test")
os.environ.setdefault("RAG_URL", "http://rag.test")
os.environ.setdefault("RISK_URL", "http://risk.test")
os.environ.setdefault("CONSOLIDATE_URL", "http://consolidate.test")
os.environ.setdefault("REPORT_WRITER_URL", "http://report-writer.test")
os.environ.setdefault("TRACES_URL", "http://traces.test")
os.environ.setdefault("HTTP_TIMEOUT", "5")
os.environ.setdefault("BATCH_RETRY_DELAY", "0")
os.environ.setdefault("BATCH_MAX_PASSES", "2")
os.environ.setdefault("BATCH_MAX_WORKERS", "2")
