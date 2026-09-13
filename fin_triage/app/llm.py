"""Chamada ao Claude via Amazon Bedrock InvokeModel + parsing de JSON.

Portado de `finguard8/app/src/llm.py`. Diferença: `invoke_claude` recebe o
client já criado (por `app/_bedrock.py`) em vez de criá-lo internamente.
"""

import json
import re

import anthropic


def bedrock_to_anthropic_model_id(model_id: str) -> str:
    """Converte um model id do Bedrock (ex. 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
    para o id nativo da Anthropic API (ex. 'claude-haiku-4-5-20251001')."""
    stripped = re.sub(r"^[a-z]+\.anthropic\.", "", model_id)
    return re.sub(r"-v\d+:\d+$", "", stripped)


def invoke_claude_anthropic(
    api_key: str,
    model_id: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 600,
    temperature: float = 0.2,
) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=bedrock_to_anthropic_model_id(model_id),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(p.text for p in resp.content if p.type == "text").strip()


def invoke_claude(
    client,
    model_id: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 600,
    temperature: float = 0.2,
) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    resp = client.invoke_model(
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())
    return "".join(
        p.get("text", "") for p in payload.get("content", []) if p.get("type") == "text"
    ).strip()


def parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
    return json.loads(cleaned)
