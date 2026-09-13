# fin_guardrail

API standalone que implementa o **nó de guardrail** do FinGuard (Nível 3 do
desafio Future Minds). Encapsula chamadas ao **Amazon Bedrock Guardrails**
(`apply_guardrail`) para:

- **Input**: validar a reclamação recebida antes de ela entrar no pipeline
  de agentes (bloqueia prompt injection, ameaças e entradas que não são
  reclamações válidas).
- **Output**: sanitizar o texto gerado pelos agentes (remove/anonimiza CPF,
  cartão, conta, nome, e reage a intervenções do Bedrock como conteúdo
  ofensivo).

A API **exige** `GUARDRAIL_ID` e chama o Amazon Bedrock de verdade — não há
fallback local. Sem `GUARDRAIL_ID` o serviço não sobe. **No startup**, a API
faz uma chamada real de teste (`apply_guardrail`) ao Bedrock e **aborta** se
não houver conectividade — o erro é `RuntimeError: [CODIGO] mensagem`, com um
código específico da causa (ver tabela em "Rodando localmente"). Em runtime,
se a chamada ao Bedrock falhar, o endpoint responde **HTTP 502** com
`detail = {codigo, mensagem, erro_aws}`.

No endpoint de OUTPUT, além do guardrail do Bedrock, roda uma segunda camada
de scrub de PII por regex (CPF, cartão, conta, nome) sobre o texto já
processado — defesa em profundidade, não fallback.

Credenciais AWS: em dev local, defina `AWS_PROFILE` no `.env` apontando para
um profile de `~/.aws/config` com acesso ao Bedrock (ex.: um profile SSO ou
de assume-role — rode `aws sso login` antes). Na **EC2**, deixe `AWS_PROFILE`
vazio: vale a **IAM role da instância** (IMDS). Nenhuma credencial vai no
código; chaves estáticas no `.env` só se você quiser forçá-las.

## Setup

```bash
cd fin_guardrail
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```

Edite o `.env` com o `GUARDRAIL_ID` do seu guardrail (visível na página do
guardrail no console do Bedrock, ex.: `abcd1234efgh`). As credenciais AWS
vêm do `aws configure` / profile / IAM role — só coloque chave e segredo no
`.env` se quiser forçar credenciais estáticas.

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8001
```

Docs interativas: http://localhost:8001/docs

### Verificação de conectividade no startup

Ao subir, a API chama `apply_guardrail` uma vez. Se o Bedrock não estiver
acessível, o processo **não sobe** (`Application startup failed. Exiting.`) e
loga `RuntimeError: [CODIGO] mensagem`:

| Código | Significado |
|---|---|
| `BEDROCK_SEM_CREDENCIAIS` | Nenhuma credencial AWS resolvida (profile / env / IAM role). |
| `BEDROCK_PROFILE_INEXISTENTE` | `AWS_PROFILE` não existe em `~/.aws/config`. |
| `BEDROCK_SSO_EXPIRADO` | Sessão SSO / token expirado — rode `aws sso login`. |
| `BEDROCK_CREDENCIAL_INVALIDA` | Chave / segredo / token rejeitados pelo Bedrock. |
| `BEDROCK_SEM_PERMISSAO` | Falta `bedrock:ApplyGuardrail` na policy IAM. |
| `BEDROCK_GUARDRAIL_NAO_ENCONTRADO` | `GUARDRAIL_ID` / `GUARDRAIL_VERSION` / `AWS_REGION` errados. |
| `BEDROCK_REGIAO_AUSENTE` | Nenhuma `AWS_REGION` configurada. |
| `BEDROCK_SEM_CONECTIVIDADE` | Sem rota de rede até o endpoint do `bedrock-runtime`. |
| `BEDROCK_THROTTLING` | Bedrock limitando as chamadas. |
| `BEDROCK_ERRO_DESCONHECIDO` | Outra falha — ver `erro_aws` no log. |

Os mesmos códigos aparecem no `detail` do HTTP 502 dos endpoints em runtime.

## Endpoints

### `GET /health`
Healthcheck simples.

### `POST /v1/guardrail/input`
Valida o texto de entrada.

```json
// request
{ "text": "Fui cobrado duas vezes na fatura do cartão e ninguém resolve." }

// response (liberado)
{
  "blocked": false,
  "reason": null,
  "block_reason": null,
  "message": null,
  "sanitized_text": "Fui cobrado duas vezes na fatura do cartão e ninguém resolve."
}

// response (bloqueado)
{
  "blocked": true,
  "reason": "bedrock_guardrail",
  "block_reason": "prompt-injection",
  "message": "Não posso ajudar com isso. Envie uma reclamação bancária válida.",
  "sanitized_text": "<texto original>"
}
```

Quando `blocked=true`, o campo `message` já traz a **resposta de bloqueio
configurada no guardrail do Bedrock** (*Messaging for blocked prompts*),
lida de `outputs[].text` da resposta do `apply_guardrail`. Se o Bedrock não
devolver texto, `message` cai no `BLOCKED_INPUT_MESSAGE` local. O endpoint
`GET /v1/guardrail/blocked-message` continua existindo como fonte do texto
fixo local.

### `POST /v1/guardrail/output`
Sanitiza o texto de saída.

```json
// request
{ "text": "Titular do cpf é João da Silva, CPF 123.456.789-00.", "field": "resumo" }

// response
{
  "sanitized_text": "Titular do cpf é [NOME OMITIDO], CPF [CPF OMITIDO].",
  "meta": {
    "field": "resumo",
    "bedrock_intervened": false,
    "pii": { "cpf": 1, "nome": 1 }
  }
}
```

### Autenticação (opcional)
Se `API_KEY` estiver definida no `.env`, todos os endpoints de guardrail
exigem o header `X-API-Key: <valor>`. Deixe em branco para desabilitar em
dev local — os agentes/serviços que chamarem esta API em produção devem
enviar o header.

## Testes

```bash
pytest
```

Os testes não tocam a AWS: `tests/conftest.py` substitui
`GuardrailService._apply` por um stub (fixture autouse `stub_bedrock`) e
define um `GUARDRAIL_ID` fake só para o boot passar.

## Integração com o grafo do FinGuard

Este serviço corresponde ao nó `guardrail` (entrada) e `guardrail_saida`
(saída) da arquitetura do Nível 3. O node de orquestração (LangGraph) deve:

1. Chamar `POST /v1/guardrail/input` com o texto bruto da reclamação.
2. Se `blocked=true`, encerrar o fluxo e retornar a mensagem de bloqueio
   (sem processar a reclamação).
3. Se `blocked=false`, seguir para os agentes de triagem/risco/relatório.
4. Antes de devolver o relatório final, chamar
   `POST /v1/guardrail/output` para cada campo de texto livre gerado pelos
   agentes.

## Docker

```bash
docker build -t fin-guardrail .
docker run --env-file .env -p 8001:8001 fin-guardrail
```
