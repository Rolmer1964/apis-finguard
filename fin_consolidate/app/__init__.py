"""FinGuard - Consolidate API.

Serviço standalone (nó de consolidação/relatório do grafo do FinGuard) que
aplica as regras determinísticas da POL-SAC-001 sobre o resultado da triagem
e da análise de risco: SLA por urgência, área responsável por produto e
overrides de canal regulatório (Banco Central / Procon / Justiça).

Não usa AWS nem nenhum outro serviço — é lógica pura.
"""
