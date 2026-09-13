"""FinGuard - Risk API.

Serviço standalone (nó de avaliação de risco do grafo do FinGuard) que avalia
uma reclamação bancária via Amazon Bedrock — Claude Sonnet: nível de risco
(Baixo/Médio/Alto/Crítico), justificativa citando a POL-SAC-001 e a lista de
ações imediatas obrigatórias (§2/§3 da política).

Chama o Amazon Bedrock de verdade (InvokeModel). **Não** chama o RAG: o
contexto da Política Interna chega pronto no corpo da requisição
(`policy_context`), montado pelo `fin_orchestrator` a partir do `fin_rag`.
"""
