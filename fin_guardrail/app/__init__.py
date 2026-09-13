"""FinGuard - Guardrail API.

Serviço responsável por validar entradas (input guardrail) e sanitizar
saídas (output guardrail) usando Amazon Bedrock Guardrails, com fallback
local via regex quando o Bedrock não está configurado ou falha.
"""
