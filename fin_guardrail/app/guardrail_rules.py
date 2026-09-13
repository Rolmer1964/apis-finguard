"""Dados de configuração do guardrail: regex de PII, listas de termos e
mapeamentos de rótulos.

Nada aqui é lógica — só as "regras" que `guardrail_service` consome.
Ajuste este arquivo para calibrar o fallback local sem tocar no serviço.
"""

import re

# ── Regex de PII (fallback / segunda camada) ────────────────────────────────

CPF_RE = re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\b")
CARD_RE = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
ACCOUNT_RE = re.compile(r"\b\d{5,12}[-–]\d{1,2}\b")

# Nome precedido de marcador explícito — evita falsos positivos em
# "Banco Central", nomes de cidades, instituições, etc.
_NOME_SEQ = (
    r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ][a-záéíóúâêîôûãõàèìòùç]+"
    r"(?:\s+(?:(?:da|de|do|dos|das|e)\s+)?"
    r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ][a-záéíóúâêîôûãõàèìòùç]+){1,5}"
)
NOME_RE = re.compile(
    # marcadores em grupo capturável (group 1) com flag case-insensitive;
    # \b em "sou" evita casar dentro de palavras como "recusou"
    r"((?i:meu nome é\s+|nome\s*[eé:]?\s+|\bsou (?:o|a)\s+|"
    r"titular[:\s]+|portador[a]?\s+do\s+cpf\b[^,]*,\s*))"
    + rf"({_NOME_SEQ})",
    re.UNICODE,
)

# ── Mensagem exibida ao cliente quando o input é bloqueado ──────────────────

BLOCKED_INPUT_MESSAGE = (
    "Esta entrada não pode ser processada pelo FinGuard. "
    "O sistema está disponível exclusivamente para análise de reclamações bancárias de clientes. "
    "Por favor, envie o texto de uma reclamação válida."
)

# ── Listas de termos do antigo fallback local de INPUT ─────────────────────
# NÃO ESTÃO EM USO: o guardrail de INPUT agora é 100% Bedrock (sem fallback).
# Mantidas aqui como referência caso se queira reativar uma checagem local.

INJECTION_TERMS = [
    "ignore suas instruções", "ignore as instruções anteriores",
    "ignore as instruções", "esqueça tudo que foi dito",
    "you are now", "você agora é", "finja ser", "aja como se fosse",
    "pretend to be", "jailbreak", "system prompt", "prompt injection",
    "revelar suas instruções", "mostre seu prompt", "what is your system prompt",
    "ignore previous instructions", "repita as instruções", "prompt inicial",
    "histórico de conversas", "dados dos outros clientes", "você é agora dan",
    "sem filtros", "sem restrições", "aja como o gerente",
]

THREAT_TERMS = [
    "vou explodir", "vou incendiar", "vou machucar", "vou te encontrar",
    "sei onde vocês moram", "sei onde você mora", "vocês vão se arrepender",
    "vou matar", "vou destruir a agência",
]

# ── Mapeamentos de rótulos das respostas do Bedrock ───────────────────────

PII_TYPE_LABELS: dict = {
    "EMAIL": "E-mail",
    "EMAIL_ADDRESS": "E-mail",
    "PHONE": "Telefone",
    "PHONE_NUMBER": "Telefone",
    "NAME": "Nome",
    "CREDIT_DEBIT_NUMBER": "Cartão",
    "CREDIT_DEBIT_EXPIRY": "Validade cartão",
    "CREDIT_DEBIT_CVV": "CVV",
    "AWS_ACCESS_KEY": "Chave AWS",
    "AWS_SECRET_KEY": "Chave secreta AWS",
    "IP_ADDRESS": "IP",
    "ADDRESS": "Endereço",
    "US_SOCIAL_SECURITY_NUMBER": "CPF/SSN",
    "DRIVER_ID": "CNH",
    "PASSPORT_NUMBER": "Passaporte",
}

CONTENT_LABELS: dict = {
    "INSULTS": "Linguagem ofensiva",
    "HATE": "Discurso de ódio",
    "VIOLENCE": "Violência",
    "SEXUAL": "Conteúdo sexual",
    "MISCONDUCT": "Conduta imprópria",
    "PROMPT_ATTACK": "Prompt injection",
}
