"""FinGuard - Report Writer API.

Serviço standalone que, a partir de uma lista de registros já processados,
gera o relatório gerencial (JSON + CSV + Markdown), agrega as distribuições e
recomendações, e serve/armazena os artefatos.

Lógica 100% determinística: não usa AWS nem chama outros serviços. O HTML do
relatório é renderizado sob demanda com Jinja2 (`report.html.j2`).
"""
