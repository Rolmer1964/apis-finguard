"""Lógica de avaliação de risco, adaptada para uso como serviço injetável.

Portado de `finguard8/app/src/agents/risk.py`. Diferença central: **o RAG saiu
daqui**. No monólito, `run_risk` chamava `retrieve()` + `format_for_prompt()`
para montar o contexto da Política Interna; agora esse contexto (`policy_context`)
chega **pronto no corpo da requisição**, montado pelo `fin_orchestrator` a
partir do `fin_rag`. `_build_query`/`retrieve` deixaram de existir.

A API chama o Amazon Bedrock (`invoke_model`) de verdade; se a chamada falhar,
a exceção sobe e o router responde 502.
"""

import logging

from . import _bedrock
from .config import Settings
from .llm import invoke_claude, invoke_claude_anthropic, parse_json_object

logger = logging.getLogger("fin_risk.service")

# Usado quando `policy_context` não vem no corpo (índice vazio ou RAG fora).
EMPTY_POLICY_CONTEXT = "(nenhum trecho da política interna disponível)"

SYSTEM_PROMPT = """Você é um analista de risco e conformidade de uma instituição financeira.
Avalie a reclamação à luz dos trechos relevantes da Política Interna fornecida e da triagem prévia.

Avalie:
- Indícios de fraude ou transação não autorizada
- Violação de regulamentos (LGPD, sigilo bancário)
- Risco reputacional (imprensa, redes sociais, órgãos reguladores)
- Necessidade de escalação imediata

Níveis de risco permitidos: "Baixo", "Médio", "Alto", "Crítico".
A justificativa deve ter 2-3 frases, em português, tom profissional. Cite a seção da POL-SAC-001
que embasa a decisão (ex: "conforme §2.3 da POL-SAC-001"). NÃO inclua dados sensíveis.

Com base na urgência e no produto identificados na triagem, gere a lista de ações imediatas
obrigatórias conforme as seções 2 e 3 da POL-SAC-001. As ações devem ser concretas, citar
prazos quando a política os define e mencionar a área responsável quando relevante.
Máximo de 5 ações.

Responda APENAS com JSON:
{
  "risco": "...",
  "justificativa": "...",
  "acoes_recomendadas": ["ação 1", "ação 2", ...]
}"""


class RiskService:
    """Encapsula a chamada de avaliação de risco ao Amazon Bedrock (Claude Sonnet).

    Uma instância é criada por request (via Depends no FastAPI), recebendo
    as Settings já resolvidas.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── seam testável: única chamada que toca a AWS/Anthropic ────────────
    def _call_llm(
        self, system: str, user: str, *, max_tokens: int = 800, temperature: float = 0.2
    ) -> str:
        if self._settings.ANTHROPIC_API_KEY:
            return invoke_claude_anthropic(
                self._settings.ANTHROPIC_API_KEY,
                self._settings.BEDROCK_MODEL_RISK,
                system,
                user,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        client = _bedrock.bedrock_runtime(self._settings)
        return invoke_claude(
            client,
            self._settings.BEDROCK_MODEL_RISK,
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

    def run_risk(
        self,
        text: str,
        triage: dict,
        policy_context: str | None = None,
        rag_chunks_count: int | None = None,
    ) -> dict:
        ctx = policy_context or EMPTY_POLICY_CONTEXT
        rag_chunks_used = rag_chunks_count or 0

        user = f"""{ctx}

Triagem prévia:
- Categoria: {triage.get('category')}
- Produto: {triage.get('product')}
- Sentimento: {triage.get('sentiment')}
- Urgência: {triage.get('urgency')}
- Resumo: {triage.get('summary')}

Texto original da reclamação:
\"\"\"
{text}
\"\"\"

Avalie o risco e justifique com base nos trechos da política. Responda apenas com o JSON solicitado."""

        raw = self._call_llm(SYSTEM_PROMPT, user, max_tokens=800, temperature=0.2)
        try:
            data = parse_json_object(raw)
        except Exception:
            logger.exception("falha ao parsear risco; raw=%r", raw)
            data = {}

        logger.info("risk usou %d trechos da política (via policy_context)", rag_chunks_used)
        return {
            "risk_level":         data.get("risco") or "Baixo",
            "risk_justification": data.get("justificativa") or "",
            "acoes_recomendadas": data.get("acoes_recomendadas") or [],
            "rag_chunks_used":    rag_chunks_used,
        }
