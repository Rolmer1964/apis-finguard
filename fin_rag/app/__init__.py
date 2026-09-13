"""FinGuard - RAG API.

Serviço standalone (nó de RAG do grafo do FinGuard) que indexa a Política
Interna e devolve os trechos mais relevantes para uma consulta, já formatados
como `policy_context` para o agente de risco.

Índice: FAISS (produto interno sobre vetores normalizados) + manifest JSON.
Embeddings: Amazon Bedrock — Titan Embed Text v2. Ingestão incremental por
hash de arquivo. Não usa nenhum outro serviço.
"""
