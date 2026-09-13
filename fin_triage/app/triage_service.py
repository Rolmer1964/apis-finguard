"""Lógica de triagem, adaptada para uso como serviço injetável.

Portado de `finguard8/app/src/agents/triage.py`. A API chama o Amazon Bedrock
(`invoke_model`) de verdade; se a chamada falhar, a exceção sobe e o router
responde 502.
"""

import logging

from . import _bedrock
from .config import Settings
from .llm import invoke_claude, invoke_claude_anthropic, parse_json_object
from .profanity import mask

logger = logging.getLogger("fin_triage.service")

SYSTEM_PROMPT = """
Você é um analista responsável pela triagem inicial de reclamações bancárias.
Seu objetivo é classificar a reclamação de forma consistente,
conservadora e auditável.

Classificações permitidas:

Categorias:
- Cobrança Indevida
- Atendimento
- Fraude/Segurança
- Produto/Serviço
- Cancelamento
- Outros

Produtos:
- Cartão de Crédito
- Conta Corrente
- Empréstimo
- Investimentos
- Seguros
- Não Identificado

Sentimentos:
- Positivo
- Neutro
- Negativo
- Crítico

Urgências:
- Baixa
- Média
- Alta
- Crítica

Critérios de decisão:
- Baseie-se apenas nas informações explícitas do texto.
- Não infira dados pessoais, financeiros ou sensíveis.
- Em caso de dúvida entre categorias, escolha a opção mais conservadora.
- Produto sugerido pelo canal é apenas uma pista, não uma certeza.

Gatilhos obrigatórios de urgência (POL-SAC-001):
- Menção a Banco Central, Procon ou processo judicial →
  urgência CRÍTICA obrigatória, independente de outros fatores.
- Indício de fraude ou transação não autorizada →
  urgência CRÍTICA obrigatória.
- Ameaça explícita de denúncia a órgão regulador →
  urgência CRÍTICA obrigatória.
- Valor financeiro em disputa explicitamente acima de R$ 500 →
  urgência mínima ALTA.
- Múltiplas tentativas anteriores sem resolução →
  urgência mínima ALTA.
- Vulnerabilidade emocional ou financeira do cliente
  (ex: comprometimento de subsistência) → urgência CRÍTICA.

Resumo:
- 2 a 3 linhas, em português.
- Tom profissional e neutro.
- Não incluir dados sensíveis (CPF, números, contas).
- Palavras impróprias devem ser substituídas por "***".

Se alguma informação não puder ser determinada com segurança, use
valores neutros ou "Não Identificado".

Formato de resposta:
Responda APENAS com um JSON válido no formato abaixo, sem comentários
adicionais:

{
  "categoria": "...",
  "produto": "...",
  "sentimento": "...",
  "urgencia": "...",
  "resumo": "..."
}
"""

_PRODUTOS_VALIDOS = {
    "Cartão de Crédito", "Conta Corrente", "Empréstimo",
    "Investimentos", "Seguros", "Não Identificado",
}


class TriageService:
    """Encapsula a chamada de triagem ao Amazon Bedrock (Claude Haiku).

    Uma instância é criada por request (via Depends no FastAPI), recebendo
    as Settings já resolvidas.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── seam testável: única chamada que toca a AWS/Anthropic ────────────
    def _call_llm(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.1
    ) -> str:
        if self._settings.ANTHROPIC_API_KEY:
            return invoke_claude_anthropic(
                self._settings.ANTHROPIC_API_KEY,
                self._settings.BEDROCK_MODEL_TRIAGE,
                system,
                user,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        client = _bedrock.bedrock_runtime(self._settings)
        return invoke_claude(
            client,
            self._settings.BEDROCK_MODEL_TRIAGE,
            system,
            user,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def ping(self) -> None:
        """Chamada mínima ao Bedrock (1 token) para verificar conectividade.

        Exercita toda a cadeia: resolução de credencial (profile/env/IMDS),
        rota de rede até o endpoint, existência do modelo e permissão
        `bedrock:InvokeModel`. Os erros boto3 propagam para o chamador
        (usado no startup da API).
        """
        self._call_llm("Responda apenas 'ok'.", "ok", max_tokens=1)

    def run_triage(self, text: str, product_hint: str | None) -> dict:
        user = f"Texto da reclamação:\n\n{text}\n"
        if product_hint:
            user += f"\nProduto sugerido pelo canal de origem: {product_hint}\n"
        user += "\nResponda apenas com o JSON solicitado."

        raw = self._call_llm(SYSTEM_PROMPT, user, max_tokens=600, temperature=0.1)
        try:
            data = parse_json_object(raw)
        except Exception:
            logger.exception("falha ao parsear triagem; raw=%r", raw)
            data = {}

        product = data.get("produto") or product_hint or "Não Identificado"
        if product not in _PRODUTOS_VALIDOS:
            product = "Não Identificado"

        return {
            "category": data.get("categoria") or "Outros",
            "product": product,
            "sentiment": data.get("sentimento") or "Neutro",
            "urgency": data.get("urgencia") or "Baixa",
            "summary": mask(data.get("resumo") or ""),
        }
