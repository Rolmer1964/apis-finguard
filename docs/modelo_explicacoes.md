**O que faz**

É a primeira e a última barreira de segurança. Na entrada, valida a reclamação bruta contra o Amazon Bedrock Guardrails (tópicos negados, filtros de conteúdo, tentativa de manipulação do sistema) e decide se o texto pode seguir. Na saída, sanitiza os textos produzidos pelos agentes, removendo dados pessoais por expressão regular e aplicando as intervenções do próprio guardrail.

**O que recebe**

Na entrada, o texto da reclamação; na saída, cada campo textual a limpar (texto original, resumo, justificativa de risco) com o nome do campo, usado apenas para log. É chamado duas vezes por reclamação.

**O que retorna**

Na entrada, um indicador de bloqueio que decide o fluxo, o motivo técnico, o detalhe dos filtros que dispararam, a mensagem a mostrar ao cliente quando bloqueado e o texto de volta. Na saída, o texto já sanitizado mais um bloco de metadados dizendo o que foi encontrado ou alterado. Falha de AWS vira erro 502 com um código de causa.

**Usa modelo?**

Não usa modelo generativo. Usa o recurso gerenciado Amazon Bedrock Guardrails, mais regex local de dados pessoais e um filtro de palavrões. Precisa de credencial AWS e do identificador do guardrail já provisionado.

**Em que documento se baseia**

Na configuração do guardrail do Bedrock (criada por um script de operações) e nas regras locais de dados pessoais e profanidade herdadas do monólito. É a implementação de referência de estilo para todas as outras APIs.
