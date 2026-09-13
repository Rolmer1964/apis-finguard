# Visão de negócio — o que faz cada parte

> A cópia anterior deste arquivo tinha vários trechos truncados; este texto foi
> restaurado e complementado com a quarta estação (`fin_rag`).

## Definição do conjunto

Pense numa **linha de montagem para tratar reclamações de clientes do banco**.
Uma reclamação entra como texto solto ("fui cobrado duas vezes e ninguém
resolve") e precisa sair como um caso organizado, com prazo, responsável e
prioridade. Das nove estações dessa linha, **quatro já estão prontas**.

---

## O porteiro e o tarjador (fin_guardrail)

**O que faz:** trabalha nas duas pontas da linha.

- **Na entrada**, lê a reclamação antes de qualquer análise e decide se ela
  pode seguir. Barra três coisas: tentativas de manipular o sistema (gente
  tentando fazer a ferramenta responder o que não deve), ameaças, e textos que
  claramente não são uma reclamação bancária.
- **Na saída**, pega tudo que a linha produziu — resumos, justificativas — e
  remove dado sensível antes de qualquer pessoa ver: CPF, número de cartão,
  número de conta, nome de gente. Também troca palavrão por `***`.

**Por que importa para o negócio:** é a camada de conformidade e reputação.
Evita vazamento de dado pessoal (risco de LGPD e de imagem), impede que a
ferramenta seja enganada e garante que o material que chega às áreas internas
esteja apresentável. Se essa estação falha, o problema não é "ficou feio" — é
multa e manchete.

**Analogia:** o segurança na porta somado à pessoa que tarja documentos com
caneta preta antes de arquivar.

---

## A triagem (fin_triage)

**O que faz:** lê a reclamação e a transforma em rótulos padronizados:

- **Categoria** — é cobrança indevida? problema de atendimento? fraude?
  cancelamento?
- **Produto** — cartão, conta corrente, empréstimo, seguro, investimento.
- **Humor do cliente** — neutro, negativo, crítico.
- **Urgência** — de baixa a crítica. Aqui já entram regras do negócio: menção a
  Banco Central, Procon ou processo judicial vira **crítica na hora**; indício
  de fraude, idem.
- **Um resumo curto e neutro** do caso, sem dado sensível e sem palavrão.

**Por que importa para o negócio:** transforma texto bagunçado em informação
comparável. É o que torna possível priorizar, mandar cada caso para a área
certa e **medir** ("quantas reclamações de fraude em cartão tivemos esta
semana?"). Sem isso, alguém teria que ler uma a uma. Usa inteligência
artificial para "ler e entender" — um modelo pequeno e barato, porque
classificar é tarefa simples.

**Analogia:** a triagem do pronto-socorro — olha o paciente, classifica a
gravidade, encaminha.

---

## O consultor que conhece o manual da empresa (fin_rag)

**O que faz:** guarda a **Política Interna** do banco — o documento que diz
como cada tipo de reclamação deve ser tratada — de um jeito que dá para
"consultar". Quando um caso está sendo analisado, ele encontra e entrega **só
os trechos da política que têm a ver com aquele caso** — não o documento
inteiro, apenas os parágrafos relevantes.

Como acha o trecho certo: não é busca por palavra exata. Ele compara o
**significado**. Se a reclamação fala em "uma compra que eu não reconheço no
cartão", ele traz os trechos sobre contestação de cartão e fraude mesmo que a
política use outras palavras. Isso também é inteligência artificial, de um tipo
diferente do da triagem: em vez de "escrever", ela mede semelhança de sentido.

**Por que importa para o negócio:** garante que a decisão sobre cada reclamação
seja tomada com base no que a política **realmente diz**, e não no que a pessoa
(ou a ferramenta) acha que ela diz. Deixa rastro — a resposta final pode citar
"conforme a seção tal da política". E isola a política num lugar só: quando o
compliance atualiza o manual, é um upload, sem mexer no resto da linha.

**Analogia:** o assistente que, antes da reunião de decisão, separa da pasta
grossa do manual só as duas páginas que importam para aquele caso e deixa em
cima da mesa.

---

## O despachante que segue o manual (fin_consolidate)

**O que faz:** **não usa inteligência artificial** — é regra escrita, ponto.
Recebe a classificação da triagem (mais a avaliação de risco, de uma estação
que ainda vamos construir) e aplica a política interna da empresa para
preencher os campos de decisão:

- **Prazo de resposta** — derivado da urgência (crítica = 4 horas, alta = 24
  horas, e assim por diante).
- **Área responsável** — derivada do produto (cartão → Gerência de Cartões,
  etc.).
- **Reforços obrigatórios** — se a reclamação chegou via Banco Central, Procon
  ou Justiça, força a urgência para crítica e eleva o risco para no mínimo
  "alto", anotando o motivo. Se o risco é crítico, garante urgência de pelo
  menos "alta".

**Por que importa para o negócio:** garante que **toda** reclamação sai com o
mesmo tratamento, previsível e auditável. Ninguém esquece de aplicar o prazo
regulatório. E, por ser determinística de propósito, cada decisão é explicável
numa auditoria: "por que o prazo é de 4 horas? porque a regra tal manda."

**Analogia:** o despachante que pega o processo já classificado e carimba
prazo, setor e prioridade seguindo o manual — sem improviso.

---

## Como as quatro se encaixam

Reclamação chega → **o porteiro** decide se entra → **a triagem** classifica e
resume → **o consultor** busca na política os trechos que valem para o caso →
*(avaliação de risco — ainda por fazer; vai usar esses trechos)* → **o
despachante** carimba prazo, área e prioridade pelo regulamento → no fim, **o
tarjador** limpa os dados sensíveis da resposta.

Repare no equilíbrio: **duas das quatro estações são sobre segurança e regra**
(o porteiro/tarjador e o despachante) e **duas usam inteligência artificial** —
a triagem, para entender e classificar; o consultor, para casar significado
entre a reclamação e o manual. A IA entra onde o trabalho é "ler e relacionar";
o resto é proteção e política — de propósito, porque é aí que a empresa não
pode errar.

*Próxima estação a construir: a avaliação de risco (`fin_risk`) — pega a
reclamação, os rótulos da triagem e os trechos de política do consultor e
decide o nível de risco (de baixo a crítico) com uma justificativa e a lista de
ações imediatas. É a peça que fecha o "quão grave é isso e o que fazer agora".*

---

*Se for útil levar isso a uma reunião, dá para montar numa página de uma folha
só para apresentar — melhor fazer quando as nove estações estiverem prontas.*
