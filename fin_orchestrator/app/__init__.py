"""FinGuard - Orchestrator API.

Ponto único de entrada do FinGuard. Duas faces, um serviço:

1. **Pipeline** — reproduz o fluxo fim-a-fim do monólito (guardrail de entrada →
   triagem → RAG → risco → consolidação → guardrail de saída → log) e o batch
   com controle adaptativo (AIMD), orquestrando as folhas por HTTP.
2. **Proxies de leitura** — é o único serviço que conhece o endereço de todos
   os outros; expõe repasses finos (relatórios, traces, painel decisório,
   stats/ingest do RAG, artefatos) para o `fin_web`.

Sem AWS direto: delega tudo às folhas.
"""
