"""Lógica de guardrail (input/output), adaptada para uso como serviço injetável.

A API chama o Amazon Bedrock (`apply_guardrail`) de verdade. Não há fallback
local: se a chamada ao Bedrock falhar, a exceção sobe e o router responde 502.

- INPUT: bloqueia/permite a reclamação recebida com base na intervenção do guardrail.
- OUTPUT: aplica o guardrail e, sobre o texto já processado, roda uma segunda
  camada de scrub de PII por regex (defesa em profundidade).

As credenciais AWS são resolvidas pela cadeia padrão do boto3 (env vars,
~/.aws/*, IAM role da EC2). Ver `config.Settings`.

Regex, listas e mapeamentos de rótulos ficam em `app/guardrail_rules.py`.
"""

import logging

import boto3

from . import guardrail_rules as rules
from .config import Settings

logger = logging.getLogger("fin_guardrail.service")

# Reexportado por conveniência para quem importa daqui (ex.: routers).
BLOCKED_INPUT_MESSAGE = rules.BLOCKED_INPUT_MESSAGE


class GuardrailService:
    """Encapsula as chamadas ao Amazon Bedrock Guardrails.

    Uma instância é criada por request (via Depends no FastAPI), recebendo
    as Settings já resolvidas.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── client ───────────────────────────────────────────────────────────

    def _bedrock_runtime(self):
        """Cria o client bedrock-runtime.

        Ordem de resolução das credenciais:
        1. AWS_PROFILE (profile de ~/.aws/config — SSO, assume-role, etc.);
        2. chaves estáticas (AWS_ACCESS_KEY_ID/...) se definidas no .env;
        3. cadeia padrão do boto3: ~/.aws/credentials, profile [default],
           IAM role da instância EC2 (IMDS).
        """
        session_kwargs: dict = {}
        if self._settings.AWS_PROFILE:
            session_kwargs["profile_name"] = self._settings.AWS_PROFILE

        client_kwargs: dict = {"region_name": self._settings.AWS_REGION}
        if not self._settings.AWS_PROFILE and self._settings.AWS_ACCESS_KEY_ID:
            client_kwargs["aws_access_key_id"] = self._settings.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = self._settings.AWS_SECRET_ACCESS_KEY
            if self._settings.AWS_SESSION_TOKEN:
                client_kwargs["aws_session_token"] = self._settings.AWS_SESSION_TOKEN

        return boto3.Session(**session_kwargs).client("bedrock-runtime", **client_kwargs)

    def _apply(self, source: str, text: str) -> dict:
        """Chama Bedrock apply_guardrail e devolve {"action", "outputs", "assessments"}.

        source=INPUT usa GUARDRAIL_ID; source=OUTPUT usa GUARDRAIL_ID_OUTPUT
        (fallback para GUARDRAIL_ID). Erros de rede/credencial/serviço (boto3)
        propagam para o chamador.
        """
        if source == "OUTPUT" and self._settings.GUARDRAIL_ID_OUTPUT:
            gid = self._settings.GUARDRAIL_ID_OUTPUT
            gver = self._settings.GUARDRAIL_VERSION_OUTPUT
        else:
            gid = self._settings.GUARDRAIL_ID
            gver = self._settings.GUARDRAIL_VERSION

        client = self._bedrock_runtime()
        resp = client.apply_guardrail(
            guardrailIdentifier=gid,
            guardrailVersion=gver,
            source=source,
            content=[{"text": {"text": text}}],
        )
        return {
            "action": resp.get("action", "NONE"),
            "outputs": resp.get("outputs", []),
            "assessments": resp.get("assessments", []),
        }

    def ping(self) -> None:
        """Chamada mínima ao Bedrock só para verificar conectividade.

        Reaproveita `_apply`, então exercita toda a cadeia: resolução de
        credencial (profile/env/IMDS), rota de rede até o endpoint,
        existência do guardrail e permissão `bedrock:ApplyGuardrail`.
        Os erros boto3 propagam para o chamador (usado no startup da API).
        """
        self._apply("INPUT", "fin_guardrail: verificacao de conectividade no startup")

    @staticmethod
    def _extract_block_reason(assessments: list) -> str:
        parts = []
        for a in assessments:
            for t in a.get("topicPolicy", {}).get("topics", []):
                if t.get("action") == "BLOCKED":
                    parts.append(t["name"])
            for f in a.get("contentPolicy", {}).get("filters", []):
                if f.get("action") == "BLOCKED":
                    conf = f.get("confidence", "")
                    parts.append(f"{f['type']} ({conf})" if conf else f["type"])
        return "; ".join(parts) if parts else "bedrock_guardrail"

    @staticmethod
    def _extract_output_detail(assessments: list) -> dict:
        pii_types: list = []
        content: list = []
        profanity = False
        for a in assessments:
            sip = a.get("sensitiveInformationPolicy", {})
            for p in sip.get("piiEntities", []):
                if p.get("action") not in ("NONE", None):
                    label = rules.PII_TYPE_LABELS.get(p["type"], p["type"])
                    if label not in pii_types:
                        pii_types.append(label)
            for rx in sip.get("regexes", []):
                if rx.get("action") not in ("NONE", None):
                    label = rx.get("name") or rx.get("regex") or "Regex"
                    if label not in pii_types:
                        pii_types.append(label)
            for f in a.get("contentPolicy", {}).get("filters", []):
                if f.get("action") not in ("NONE", None):
                    label = rules.CONTENT_LABELS.get(f["type"], f["type"])
                    conf = f.get("confidence", "")
                    entry = f"{label} ({conf})" if conf else label
                    if entry not in content:
                        content.append(entry)
            if a.get("wordPolicy", {}).get("managedWordLists"):
                profanity = True
        return {"pii_types": pii_types, "content": content, "profanity": profanity}

    # ── Input guardrail ──────────────────────────────────────────────────

    def check_input(self, text: str) -> dict:
        """Valida o texto de entrada antes de entrar no pipeline de agentes.

        Retorna {"blocked", "reason", "block_reason", "sanitized_text"}.
        Não sanitiza PII no input — isso é responsabilidade do guardrail de saída.
        Levanta exceção (boto3) se o Bedrock estiver indisponível.
        """
        r = self._apply("INPUT", text)
        logger.info("guardrail INPUT action=%s", r["action"])
        if r["action"] == "GUARDRAIL_INTERVENED":
            reason = self._extract_block_reason(r["assessments"])
            outputs = r["outputs"]
            # Mensagem de bloqueio configurada no guardrail do Bedrock
            # ("Messaging for blocked prompts"). Fallback para a mensagem local
            # se o Bedrock não devolver texto em outputs.
            message = (outputs[0].get("text") if outputs else None) or rules.BLOCKED_INPUT_MESSAGE
            return {
                "blocked": True,
                "reason": "bedrock_guardrail",
                "block_reason": reason,
                "message": message,
                "sanitized_text": text,
            }
        return {
            "blocked": False,
            "reason": None,
            "block_reason": None,
            "message": None,
            "sanitized_text": text,
        }

    # ── Output guardrail ─────────────────────────────────────────────────

    def sanitize_output(self, text: str, field: str = "") -> tuple:
        """Sanitiza o texto de saída removendo/anonimizando dados sensíveis.

        Aplica o guardrail do Bedrock e, sobre o resultado, uma segunda camada
        de scrub de PII por regex. Retorna (texto_sanitizado, meta).
        Levanta exceção (boto3) se o Bedrock estiver indisponível.
        """
        meta: dict = {"field": field, "bedrock_intervened": False, "pii": {}}

        if not text:
            return text, meta

        r = self._apply("OUTPUT", text)
        outputs = r["outputs"]
        text = outputs[0].get("text", text) if outputs else text
        if r["action"] == "GUARDRAIL_INTERVENED":
            meta["bedrock_intervened"] = True
            meta["bedrock_detail"] = self._extract_output_detail(r["assessments"])
            logger.info("guardrail OUTPUT interveio campo=%s detail=%s", field, meta["bedrock_detail"])

        # Segunda camada: scrub de PII por regex sobre o texto já processado.
        text, pii = self._regex_sanitize(text)
        meta["pii"] = pii
        return text, meta

    @staticmethod
    def _regex_sanitize(text: str) -> tuple:
        text, n_cpf = rules.CPF_RE.subn("[CPF OMITIDO]", text)
        text, n_card = rules.CARD_RE.subn("[CARTÃO OMITIDO]", text)
        text, n_account = rules.ACCOUNT_RE.subn("[CONTA OMITIDA]", text)
        text, n_nome = rules.NOME_RE.subn(r"\1[NOME OMITIDO]", text)
        meta = {}
        if n_cpf:
            meta["cpf"] = n_cpf
        if n_card:
            meta["cartao"] = n_card
        if n_account:
            meta["conta"] = n_account
        if n_nome:
            meta["nome"] = n_nome
        return text, meta
