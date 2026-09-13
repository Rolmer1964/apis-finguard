# Explicações das APIs — apis_finguard

Panorama atual de cada serviço do projeto. As sete folhas aparecem na ordem do
pipeline; depois o orquestrador e a interface.

---

## fin_guardrail — porta 8001

**O que faz**

É a primeira e a última barreira de segurança do pipeline. Na entrada, valida a reclamação bruta contra o Amazon Bedrock Guardrails (tópicos negados, filtros de conteúdo, tentativa de manipulação do sistema) e decide se o texto pode seguir. Na saída, sanitiza os textos produzidos pelos agentes, removendo dados pessoais por expressão regular e aplicando as intervenções do próprio guardrail.

**O que recebe**

Do orquestrador: na entrada, o texto da reclamação; na saída, cada campo textual a limpar (texto original, resumo, justificativa de risco) com o nome do campo, usado apenas para log. É chamado duas vezes por reclamação.

**O que retorna**

Na entrada, um indicador de bloqueio que decide o fluxo, o motivo técnico, o detalhe dos filtros que dispararam, a mensagem a mostrar ao cliente quando bloqueado e o texto de volta. Na saída, o texto já sanitizado mais um bloco de metadados dizendo o que foi encontrado ou alterado. Falha de AWS vira erro 502 com um código de causa.

**Usa modelo?**

Não usa modelo generativo. Usa o recurso gerenciado Amazon Bedrock Guardrails, mais regex local de dados pessoais e um filtro de palavrões. Precisa de credencial AWS e do identificador do guardrail já provisionado.

**Em que documento se baseia**

Na configuração do guardrail do Bedrock, criada por um script de operações que acompanha o serviço, e nas regras locais de dados pessoais e profanidade que ele carrega. É a implementação de referência de estilo para as demais APIs.

---

## fin_triage — porta 8002

**O que faz**

É a primeira leitura estruturada da reclamação. Classifica o texto em categoria, produto, sentimento e urgência, todos escolhidos de listas fixas, e escreve um resumo neutro de duas a três linhas com palavrões mascarados.

**O que recebe**

Do orquestrador: o texto da reclamação já liberado pelo guardrail de entrada e, opcionalmente, uma pista de produto vinda do canal de origem. É o segundo passo do pipeline.

**O que retorna**

Os quatro rótulos e o resumo. Se a resposta do modelo vier malformada, adota valores neutros; produto fora da lista permitida vira "Não Identificado". Falha de AWS vira erro 502 com código.

**Usa modelo?**

Sim — Claude Haiku, via Amazon Bedrock, com temperatura baixa e poucos tokens de saída. A escolha do Haiku é deliberada: é tarefa fechada de classificação, roda em todo registro e por isso custo e latência pesam; o julgamento mais fino fica para o fin_risk.

**Em que documento se baseia**

Na Política Interna (POL-SAC-001): as classes de categoria e produto e, principalmente, os gatilhos obrigatórios de urgência entram no prompt de sistema.

---

## fin_rag — porta 8003

**O que faz**

Faz busca semântica sobre a Política Interna e administra o índice vetorial. Numa consulta, transforma a pergunta em vetor e devolve os trechos mais relevantes da política, já formatados como bloco de contexto pronto para o prompt do fin_risk. Também ingere o PDF da política de forma incremental por hash, mantém o índice FAISS em volume persistente e expõe estatísticas e reset.

**O que recebe**

Do orquestrador: uma consulta em texto livre, que é a reclamação somada às dimensões da triagem, e opcionalmente quantos trechos retornar. É o terceiro passo. As rotas de ingestão e de estatísticas são acionadas pela tela de administração através do orquestrador.

**O que retorna**

A lista de trechos com origem e pontuação de similaridade, a contagem e o contexto da política já montado. Com o índice vazio, devolve um aviso fixo sem chamar o modelo. Falha ao gerar o vetor vira erro 502 com código.

**Usa modelo?**

Sim, mas apenas para embeddings — Amazon Titan Embed Text v2, via Bedrock, com vetores normalizados de dimensão fixa. Não há modelo generativo. O Titan foi escolhido por ser o embedding nativo do Bedrock, barato e de dimensão compatível com o FAISS. Este serviço roda em Python 3.12, porque o FAISS não tem pacote pronto para a versão mais nova.

**Em que documento se baseia**

No próprio documento que indexa: a Política Interna, distribuída como PDF semente junto do serviço.

---

## fin_risk — porta 8004

**O que faz**

Avalia risco e conformidade. À luz da política e da triagem, decide o nível de risco entre Baixo, Médio, Alto e Crítico e monta a lista de ações imediatas obrigatórias. Funciona como segunda linha de defesa: capta ataques que passaram pelo guardrail e pela triagem.

**O que recebe**

Do orquestrador: o texto original da reclamação, a saída da triagem, o contexto da política já formatado pelo fin_rag e a contagem de trechos que o compõem. É o quarto passo. Se o contexto não vier, usa um aviso de índice vazio.

**O que retorna**

O nível de risco, uma justificativa de duas a três frases citando a seção da política, até cinco ações recomendadas e o número de trechos da política usados. Se a resposta do modelo não puder ser interpretada, assume risco "Baixo" e campos vazios. Falha de AWS vira erro 502.

**Usa modelo?**

Sim — Claude Sonnet 4.5, via Amazon Bedrock, com mais tokens e temperatura um pouco maior que a triagem. Sonnet porque a tarefa exige julgamento: enquadrar o risco, citar a política e reconhecer intenção maliciosa em texto aparentemente legítimo.

**Em que documento se baseia**

Na Política Interna, com destaque para as seções de ações imediatas e as seções citadas na justificativa; a ideia de "segunda linha" vem do registro de decisão arquitetural do projeto (ADR-001).

---

## fin_consolidate — porta 8005

**O que faz**

Consolidação totalmente determinística, sem inteligência artificial. Aplica as regras de negócio da política sobre a triagem e o risco já calculados: deriva o prazo de resposta a partir da urgência, a área responsável a partir do produto, aplica os overrides de canal regulatório (Banco Central, Procon e Justiça elevam a urgência a Crítica e o risco a um mínimo Alto) e a escalação de segunda linha (risco Crítico garante urgência mínima Alta).

**O que recebe**

Do orquestrador: a saída da triagem, a saída do risco e o canal de origem. É o quinto passo.

**O que retorna**

O registro consolidado — os campos da triagem, a urgência e o risco já ajustados pelos overrides, o prazo de resposta, a área responsável, a justificativa com a nota do override anexada quando houve, e as ações. Traz também o nível de risco original quando um override de canal o alterou.

**Usa modelo?**

Não. Nenhuma chamada a modelo nem a AWS — são tabelas de mapeamento e condicionais.

**Em que documento se baseia**

Na Política Interna: a tabela de prazo por urgência, o mapeamento de produto para área, a seção de canais regulatórios e a regra de escalação por risco.

---

## fin_report_writer — porta 8006

**O que faz**
A partir de uma lista de registros já processados, gera o relatório gerencial em três formatos de arquivo, renderiza a versão em página com gráficos, agrega as distribuições e as recomendações, e guarda e serve os artefatos. Também responde a consulta de um registro individual por identificador.
**O que recebe**
Do orquestrador: ao fim de um lote ou de uma consulta unitária, a lista de registros consolidados mais os metadados da execução, como início, fim, duração e estatísticas dos passes. Das telas, recebe pela via do orquestrador pedidos de listagem, de contexto, de página renderizada, de registro por identificador e de remoção.
**O que retorna**
Na geração, o identificador do relatório e os caminhos dos arquivos criados. Nas leituras, a lista de relatórios, o contexto agregado para renderização, a página pronta, o registro individual ou a confirmação de remoção. Serve ainda os arquivos brutos para download.
**Usa modelo? **
Não. Nenhuma inteligência artificial nem AWS — é agregação de dados, geração de página por template e escrita de arquivo.
**Em que documento se baseia **
Não parte de um documento normativo. As distribuições e a lista de reclamações críticas refletem as dimensões da Política Interna, como urgência, risco, área e canal.

---

## fin_traces — porta 8007

**O que faz**
Mantém o log de execução em memória e o painel decisório. Guarda uma entrada por reclamação processada e agrega os números do painel: cruzamento de urgência com risco, distribuição por canal, área e prazo, e estatísticas de tempo como média, desvio e percentis. Pode gravar a fila em disco para sobreviver a reinício e reconstruir o log a partir de um relatório salvo.
**O que recebe**
Do orquestrador: ao fim de cada reclamação, a entrada de rastreamento com identificador, horário, prévia do texto, indicador de bloqueio, categoria, urgência, risco, produto, canal, prazo, área e os tempos por etapa. Na recomposição, recebe a lista de registros de um relatório. As leituras chegam da interface pela via do orquestrador.
**O que retorna**
No registro, a contagem atual de entradas. Nas leituras, o contexto completo do log já preparado para renderização, as estatísticas de tempo isoladas, as agregações do painel decisório, ou quantas entradas foram recompostas ou removidas.
**Usa modelo? **
Não. Sem inteligência artificial e sem AWS — estruturas em memória e cálculo estatístico.
**Em que documento se baseia **
Não tem documento normativo próprio. As agregações espelham a Política Interna, e a leitura da combinação urgência baixa com risco crítico como segunda linha de defesa vem do registro de decisão arquitetural (ADR-001).

---

## fin_orchestrator — porta 8000

**O que faz**
É o ponto único de entrada. Executa o fluxo fim a fim chamando as sete folhas por HTTP na ordem correta — guardrail de entrada, triagem, RAG, risco, consolidação, guardrail de saída e registro no log — e roda o processamento de CSV em lote com controle adaptativo de vazão. Como é o único serviço que conhece o endereço de todas as folhas, também oferece repasses finos de leitura para a interface.
**O que recebe**
Da interface, ou de qualquer cliente: o texto de uma reclamação com canal e pista de produto, ou um arquivo CSV para o lote. Nos repasses, recebe pedidos de relatórios, de log, de painel decisório e de estatísticas e ingestão do RAG.
**O que retorna**
No fluxo individual, o resultado consolidado com triagem, risco, campos consolidados e os tempos por etapa. No lote, o resumo da execução com o identificador do relatório e as estatísticas dos passes. Se qualquer folha falha, responde erro 502 preservando a causa original. Os repasses devolvem a resposta da folha dona sem alteração.
**Usa modelo? **
Não diretamente. Delega todo o uso de Bedrock às folhas e não tem credencial AWS.
**Em que documento se baseia **
No plano de divisão do projeto, que define os contratos entre serviços e a ordem do fluxo.

---

## fin_web — porta 8008

**O que faz**
É a interface em HTML gerada no servidor. Renderiza as telas: formulário de reclamação individual, envio de lote, lista e detalhe de relatórios com gráficos e janela de detalhe, log de execução, painel decisório, administração, o registro de decisão arquitetural e o relatório técnico. Não contém regra de negócio.
**O que recebe**
Do navegador: os formulários, com o texto da reclamação e o canal ou o arquivo CSV, e a navegação entre páginas. Abaixo dela, consome apenas o orquestrador — lê os repasses para montar cada tela e encaminha os envios.
**O que retorna**
As páginas HTML. Nos envios, redireciona para a página do relatório recém-gerado. Alguns endereços são apenas repasses finos usados pelo JavaScript das telas, como registro por identificador, arquivo bruto, estatísticas do painel e ingestão. O recorde do joguinho da tela de espera é um arquivo local.
**Usa modelo? **
Não. Sem inteligência artificial e sem AWS — apenas geração de página por template e chamadas HTTP ao orquestrador.
**Em que documento se baseia **
Não parte de documento normativo. Os textos das telas de política e de decisão arquitetural remetem à Política Interna e ao registro de decisão do projeto (ADR-001).
