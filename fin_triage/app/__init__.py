"""FinGuard - Triage API.

Serviço standalone (nó de triagem do grafo do FinGuard) que classifica uma
reclamação bancária via Amazon Bedrock — Claude Haiku: categoria, produto,
sentimento, urgência e um resumo neutro, aplicando os gatilhos de urgência
da POL-SAC-001.

Chama o Amazon Bedrock de verdade (InvokeModel). Não usa nenhum outro serviço.
"""
