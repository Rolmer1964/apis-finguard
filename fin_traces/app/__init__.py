"""FinGuard - Traces API.

Serviço standalone que mantém o **log de execução** do pipeline (deque em
memória, sem limite) e deriva o **painel decisório** (matriz urgência×risco,
agregações por canal / área / prazo, estatísticas de timing).

Lógica 100% determinística: não usa AWS nem chama outros serviços. Opcionalmente
persiste o deque em disco (`TRACES_PERSIST_PATH`) para sobreviver a restarts.
"""
