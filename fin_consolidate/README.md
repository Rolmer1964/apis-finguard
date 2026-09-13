# fin_consolidate

API standalone que implementa o **nó de consolidação** do FinGuard (Nível 3 do
desafio Future Minds). Recebe o resultado da **triagem** e da **análise de
risco** e aplica as regras determinísticas da **POL-SAC-001**:

- **SLA por urgência** — `prazo_resposta` derivado da urgência final.
- **Área responsável por produto** — ex.: `Cartão de Crédito → Gerência de
  Cartões`; produto desconhecido → `Área de Suporte Geral`.
- **Overrides de canal regulatório (§4.3)** — `canal` em
  `Banco Central` / `Procon` / `Justiça`:
  - força `urgency = "Crítica"`;
  - garante `risk_level` mínimo `"Alto"` (registrando o valor anterior em
    `risk_level_original` e anexando uma nota à justificativa).
- **Segunda linha de defesa** — `risk_level = "Crítico"` garante `urgency`
  mínima `"Alta"`.

Lógica **100% determinística**: não usa AWS, não chama nenhum outro serviço,
não tem estado. Portado de `finguard8/app/src/agents/report.py`.

## Setup

```bash
cd fin_consolidate
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

copy .env.example .env        # Windows  (opcional — só p/ definir API_KEY)
# cp .env.example .env        # Linux/Mac
```

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8005
```

Docs interativas: http://localhost:8005/docs

## Endpoints

### `GET /health`
Healthcheck simples → `{"status": "ok"}`.

### `POST /v1/consolidate`
Aplica as regras POL-SAC-001.

```json
// request
{
  "triage": {
    "category": "Cobrança Indevida",
    "product": "Cartão de Crédito",
    "sentiment": "Negativo",
    "urgency": "Baixa",
    "summary": "Cliente relata cobrança em duplicidade na fatura."
  },
  "risk": {
    "risk_level": "Baixo",
    "risk_justification": "Sem indício de fraude; conforme §2.1 da POL-SAC-001.",
    "acoes_recomendadas": ["Abrir chamado de contestação", "Contatar o cliente em 24h"]
  },
  "canal": "Banco Central"
}
```

```json
// response
{
  "category": "Cobrança Indevida",
  "product": "Cartão de Crédito",
  "sentiment": "Negativo",
  "urgency": "Crítica",
  "summary": "Cliente relata cobrança em duplicidade na fatura.",
  "prazo_resposta": "4 horas",
  "area_responsavel": "Gerência de Cartões",
  "risk_level": "Alto",
  "risk_justification": "Sem indício de fraude; conforme §2.1 da POL-SAC-001. [Nível elevado de Baixo para Alto por canal regulatório (Banco Central) — POL-SAC-001 §4.3]",
  "acoes_recomendadas": ["Abrir chamado de contestação", "Contatar o cliente em 24h"],
  "risk_level_original": "Baixo"
}
```

`risk_level_original` só aparece quando o override de canal regulatório
elevou o risco. Sem `canal` regulatório, o campo vem `null`.

Exemplo `curl`:

```bash
curl -X POST http://localhost:8005/v1/consolidate \
  -H "Content-Type: application/json" \
  -d '{"triage":{"category":"Atendimento","product":"Conta Corrente","sentiment":"Negativo","urgency":"Média","summary":"Fila demorada."},"risk":{"risk_level":"Médio","risk_justification":"","acoes_recomendadas":[]}}'
```

### Autenticação (opcional)
Se `API_KEY` estiver definida no `.env`, `POST /v1/consolidate` exige o header
`X-API-Key: <valor>`. Deixe em branco para desabilitar em dev local.

## Testes

```bash
pytest
```

Não tocam AWS nem rede — a consolidação é pura.

## Integração com o grafo do FinGuard

Corresponde ao nó `report` (consolidação) da arquitetura do Nível 3. O
orquestrador deve chamar `POST /v1/consolidate` **depois** de `fin_triage` e
`fin_risk` e **antes** do guardrail de saída, repassando `canal` quando
conhecido.

## Docker

```bash
docker build -t fin-consolidate .
docker run --env-file .env -p 8005:8005 fin-consolidate
```
