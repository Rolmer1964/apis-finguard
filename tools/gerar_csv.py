import csv
import pathlib
import random
from datetime import date, timedelta

random.seed(42)

# ============================================================
# POOL DE TEXTOS - RECLAMAÇÕES BANCÁRIAS (a maioria)
# ============================================================

reclamacoes_cartao = [
    ("Fui cobrado duas vezes na fatura do cartão pela mesma compra no supermercado e ninguém resolve. Já liguei 4 vezes no SAC e cada atendente me passa pra outro. Quero o estorno IMEDIATO.", "Cartão de Crédito"),
    ("Apareceu uma compra de R$ 1.847,90 numa loja de eletrônicos em Manaus. Eu moro em Curitiba e o cartão estava no meu bolso. Como isso é possível?", "Cartão de Crédito"),
    ("Solicitei o cancelamento do cartão extra da minha esposa há 3 meses e continua chegando fatura com anuidade. Vocês são surdos?", "Cartão de Crédito"),
    ("A bandeira do meu cartão mudou sem aviso e agora não funciona em metade dos lugares que eu usava. Não fui consultado sobre essa mudança.", "Cartão de Crédito"),
    ("Tarifa de R$ 89 chamada 'serviço de proteção premium' que eu NUNCA contratei. Quero o estorno dos últimos 12 meses.", "Cartão de Crédito"),
    ("Fui ao caixa eletrônico, a máquina engoliu meu cartão e a agência diz que precisa esperar 10 dias úteis pra emitir outro. Como vou viver sem cartão por 2 semanas?", "Cartão de Crédito"),
    ("Cobrança de IOF absurda numa compra internacional de US$ 50. Vocês cobraram quase 30%, isso é roubo.", "Cartão de Crédito"),
    ("Cartão clonado pela TERCEIRA vez este ano. O que vocês estão fazendo com a segurança?", "Cartão de Crédito"),
    ("Pedi aumento de limite, foi negado, e dois dias depois chega proposta de cartão Black com limite de R$ 30 mil. Que palhaçada é essa?", "Cartão de Crédito"),
    ("Anuidade cobrada mesmo após eu ter feito o gasto mínimo do cartão Premium. Atendimento diz que não cumpri a regra mas o app mostra que cumpri.", "Cartão de Crédito"),
    ("Compra parcelada em 10x vinha sem juros e na fatura tem juros de 4,9% ao mês. Onde está o sem juros prometido?", "Cartão de Crédito"),
    ("O aplicativo aprovou minha compra de R$ 2 mil mas o estabelecimento disse que foi negada. Acabei pagando duas vezes pra não passar vergonha.", "Cartão de Crédito"),
    ("Cartão chegou ATIVADO na minha caixa de correio aberta. Já tinha duas compras antes mesmo de eu receber.", "Cartão de Crédito"),
    ("Limite reduzido sem aviso de R$ 8.000 pra R$ 1.500 no meio de uma viagem internacional. Tive que voltar antes do tempo. Inaceitável.", "Cartão de Crédito"),
    ("Cobrança recorrente de uma plataforma de streaming que cancelei em 2024. Disputo todo mês e todo mês ela volta.", "Cartão de Crédito"),
    ("Solicitei segunda via do cartão por defeito no chip e foi cobrada uma taxa de R$ 32. Defeito do produto deveria ser de graça.", "Cartão de Crédito"),
    ("Pontos do programa de fidelidade desapareceram. Tinha 47 mil pontos no mês passado e hoje só tem 12 mil. Cadê meus pontos?", "Cartão de Crédito"),
    ("Cobraram seguro proteção do cartão que eu recusei na hora da venda. A gravação da minha ligação prova que eu disse NÃO.", "Cartão de Crédito"),
    ("Parcelamento de fatura com taxa de juros de 14,5% ao mês. Isso é prática agiotagem disfarçada de banco.", "Cartão de Crédito"),
    ("Cartão virtual gerado no app não funciona em NENHUMA loja online. Pra que serve então?", "Cartão de Crédito"),
    ("Fatura veio com saldo devedor zero, paguei o boleto referente, e mês seguinte chegou cobrança de juros por atraso. Como pode juros sobre zero?", "Cartão de Crédito"),
    ("Compra estornada pelo lojista há 45 dias e até agora nada na minha fatura. O dinheiro está retido por vocês.", "Cartão de Crédito"),
    ("Meu cartão foi bloqueado por suspeita de fraude justamente quando eu estava no caixa pagando o jantar. Passei vergonha enorme.", "Cartão de Crédito"),
    ("A função cashback nunca creditou um centavo apesar de gastar R$ 4 mil por mês. Onde está meu retorno prometido?", "Cartão de Crédito"),
    ("Antecipação de fatura saiu mais cara que o juros do crédito rotativo. Como assim?", "Cartão de Crédito"),
    ("Cartão recusado em farmácia mesmo com saldo de R$ 6.000 disponíveis. Tive que deixar os remédios da minha mãe.", "Cartão de Crédito"),
    ("Promessa de cartão sem anuidade vitalícia na contratação. Hoje, 18 meses depois, começaram a cobrar. Tenho gravação da ligação.", "Cartão de Crédito"),
    ("Lançamento na fatura como 'COMPRAS DIVERSAS' sem identificar o estabelecimento. Como posso conferir se isso é meu ou não?", "Cartão de Crédito"),
]

reclamacoes_conta = [
    ("Fui à agência abrir uma conta corrente, perdi a manhã toda e me disseram no fim que precisava agendar pelo aplicativo. Por que ninguém avisou na entrada?", "Conta Corrente"),
    ("Tarifa de manutenção de conta de R$ 67 cobrada mesmo eu sendo cliente correntista há 22 anos. Onde está a fidelidade?", "Conta Corrente"),
    ("Conta encerrada por baixa movimentação SEM AVISO. Tinha R$ 3.400 de saldo que sumiram. Cadê meu dinheiro?", "Conta Corrente"),
    ("Cobrança de R$ 12 pra cada saque acima de 4 por mês. Isso desestimula o uso do meu próprio dinheiro.", "Conta Corrente"),
    ("Cheque devolvido por insuficiência de fundos sendo que eu tinha R$ 8 mil na conta. Saiu nome no Serasa por causa disso.", "Conta Corrente"),
    ("Transferência DOC ainda existe nesse banco e custa R$ 18,50. Em 2026? Pra onde fui mandar dinheiro, época das cavernas?", "Conta Corrente"),
    ("Limite de cheque especial reduzido sem aviso, conta entrou no negativo e cobraram juros de 12,7% ao mês. Isso é assalto formalizado.", "Conta Corrente"),
    ("Solicitei extrato dos últimos 5 anos pro imposto de renda e cobraram R$ 45 por ano. R$ 225 pra ver meu próprio histórico?", "Conta Corrente"),
    ("Saque negado no caixa eletrônico mas o valor foi debitado da minha conta. R$ 800 sumiram literalmente.", "Conta Corrente"),
    ("Pacote de serviços que eu pedi pra cancelar há 6 meses continua sendo debitado todo mês. Vão me devolver tudo com correção.", "Conta Corrente"),
    ("A agência fechou e me transferiram pra uma a 14 km da minha casa sem perguntar. Sou idosa, não dirijo.", "Conta Corrente"),
    ("Débito automático da conta de luz pago duas vezes no mesmo mês. A energia agradeceu, eu não.", "Conta Corrente"),
    ("Recebi salário, no mesmo dia debitaram tarifa de TED, manutenção de conta, cesta de serviços e seguro. Sobrou metade.", "Conta Corrente"),
    ("Cheque que eu assinei foi adulterado e o banco compensou sem verificar. Perdi R$ 4.700 e a culpa é minha?", "Conta Corrente"),
    ("Aplicativo mostra saldo de R$ 12.000 e o caixa diz que tenho R$ 6.000. Qual é o meu saldo de verdade?", "Conta Corrente"),
    ("Tive minha conta clonada, transferência de R$ 9 mil saiu via PIX pra desconhecido e o banco diz que a culpa é minha. Onde está a segurança?", "Conta Corrente"),
    ("Fim de semana inteiro sem acesso à conta porque vocês estavam 'em manutenção'. Tive que pedir dinheiro emprestado.", "Conta Corrente"),
    ("Pacote de tarifas mudou pra um mais caro automaticamente após mudança de pacote. Não autorizei isso.", "Conta Corrente"),
]

reclamacoes_emprestimo = [
    ("Fiz simulação de empréstimo de R$ 10 mil em 24x e o contrato chegou com 36 parcelas. Cadê os 24 meses simulados?", "Empréstimo"),
    ("CET do empréstimo prometido era 3,9% e na assinatura tinha 7,2%. Letras miúdas no contrato.", "Empréstimo"),
    ("Empréstimo consignado descontado em folha mesmo após quitação antecipada. Estou pagando duas vezes.", "Empréstimo"),
    ("Liberação do empréstimo demorou 23 dias úteis e a oferta era 'liberação imediata'. Perdi a oportunidade de negócio.", "Empréstimo"),
    ("Renegociação de dívida saiu MAIS cara que a dívida original. Como uma renegociação aumenta o valor?", "Empréstimo"),
    ("Empréstimo aprovado, dinheiro caiu na conta, mês seguinte pediram pra devolver tudo porque 'aprovação foi um erro'. Já gastei.", "Empréstimo"),
    ("Seguro prestamista obrigatório no empréstimo de R$ 5 mil custou R$ 870 a mais. Não foi explicado na hora.", "Empréstimo"),
    ("Empréstimo pessoal pra negativados com taxa de 14% ao MÊS. Isso é agiotagem, não banco.", "Empréstimo"),
    ("Liquidei meu empréstimo no mês passado e ainda recebo cobrança das parcelas. Já mostrei o comprovante 5 vezes.", "Empréstimo"),
    ("Fui contratar empréstimo consignado, acabei saindo com cartão de crédito consignado sem entender. Mil vezes pior.", "Empréstimo"),
    ("Empréstimo com garantia de imóvel, casa avaliada em R$ 450 mil, me ofereceram apenas R$ 80 mil de crédito. Avaliação é palhaçada.", "Empréstimo"),
    ("Refinanciamento aumentou minha parcela em 40%. Onde está a vantagem prometida?", "Empréstimo"),
    ("Empréstimo do FGTS aprovado mas o dinheiro nunca caiu. Já são 28 dias.", "Empréstimo"),
    ("Cobrança de tarifa de cadastro de R$ 350 num empréstimo de R$ 2 mil. Quase 18% só pra abrir o processo.", "Empréstimo"),
    ("Fui assediado por 14 ligações em uma semana oferecendo empréstimo. Pedi pra parar, continuou. Onde está a LGPD?", "Empréstimo"),
]

reclamacoes_pix_transferencia = [
    ("PIX feito há 6 horas para minha mãe ainda não caiu. Disseram que é 'instantâneo'. Que tipo de instante é esse?", "PIX"),
    ("PIX pra chave errada por causa do auto-completar do app. Banco diz que não pode reverter. R$ 2.300 perdidos.", "PIX"),
    ("Limite de PIX noturno reduziu pra R$ 100. Sou empresária, recebo até de madrugada de cliente.", "PIX"),
    ("Taxa de TED de R$ 22 pra transferir entre contas do MESMO banco. Mas fica calado se for pra outro.", "Transferência"),
    ("PIX agendado nunca foi executado, perdi prazo de aluguel e fui multado em R$ 500. Quem paga?", "PIX"),
    ("Transferência internacional via SWIFT cobrou R$ 290 de tarifa pra mandar US$ 200. 1/3 do valor em taxa.", "Transferência"),
    ("PIX devolvido pelo banco do destinatário e o dinheiro não voltou pra minha conta. Sumiu no meio do caminho.", "PIX"),
    ("Recebi PIX de pessoa desconhecida e dois dias depois ela me processou alegando golpe. Banco lavou as mãos.", "PIX"),
    ("Chave PIX cadastrada em duas contas, conflito de propriedade, fiquei sem usar PIX por 11 dias.", "PIX"),
    ("Tarifa de R$ 4,90 por cada PIX a partir do quinto no mês. Conta digital deveria ser sem taxa.", "PIX"),
    ("Transferência DOC ainda existe e leva 1 dia útil pra cair. PIX é instantâneo de graça. Por que ainda oferecer DOC?", "Transferência"),
    ("Comprovante de PIX não chega no email cadastrado. Tive que abrir reclamação no Banco Central.", "PIX"),
    ("PIX por QR Code lido no app abriu valor de R$ 4.000, eu paguei R$ 40. Banco cobrou os R$ 4.000 mesmo assim.", "PIX"),
    ("Chave aleatória do PIX vazou em golpe, mudei a chave, golpistas continuam tentando contato. Banco não me protege.", "PIX"),
]

reclamacoes_taxas_servicos = [
    ("Taxa de avaliação de imóvel pra financiamento custou R$ 1.450 e o financiamento foi negado depois. Cadê o estorno?", None),
    ("Cobrança de 'serviço de proteção financeira' que eu nunca contratei. R$ 38,90 por mês há 2 anos.", None),
    ("Tarifa de envio de boleto por correio R$ 8 cada um. Em 2026, ainda mandam por correio?", None),
    ("Cobrança de tarifa de extrato impresso na agência. R$ 6 pra ver meu próprio dinheiro?", None),
    ("Anuidade de cartão Black de R$ 1.190 cobrada apesar de eu ter cancelado o cartão antes do vencimento.", "Cartão de Crédito"),
    ("Serviço de SMS sobre movimentações cobra R$ 4,90/mês. Recebo notificação pelo app de graça. Pra que pagar?", None),
    ("Tarifa de manutenção de cofre alugado dobrou de valor sem aviso. R$ 280 pra R$ 560.", None),
    ("Cobrança chamada 'tarifa de adesão a serviços' de R$ 75 que ninguém sabe explicar o que é.", None),
    ("Multa por não usar o cheque especial. Sim, MULTA por NÃO usar. O quê?", None),
    ("Tarifa de R$ 35 cada vez que eu altero a senha do cartão. Como assim?", None),
]

reclamacoes_terceiros = [
    ("Compra de seguro residencial empurrada de uma seguradora terceirizada que não cobre nem chuva forte. Vendida como completa.", "Seguro"),
    ("Plano odontológico cobrado na minha conta há 8 meses. Eu nunca contratei NENHUM plano odontológico.", "Plano Odontológico"),
    ("Capitalização vendida como 'investimento garantido'. Resgate menor que o aplicado depois de 2 anos. Onde está o garantido?", "Capitalização"),
    ("Consórcio de carro vendido na agência, contemplei no primeiro mês, valor liberado é R$ 12 mil menor que o do consórcio. Sumiu na taxa de administração.", "Consórcio"),
    ("Previdência privada com taxa de carregamento de 4% e taxa de administração 3,5% ao ano. Estão é me empobrecendo.", "Previdência"),
    ("Seguro de cartão protegido vendido junto com a anuidade. Não cobre roubo, não cobre clonagem, não cobre nada. Pra que existe?", "Seguro"),
    ("Plano de saúde indicado pelo gerente. Operadora suspensa pela ANS um mês depois. Perdi R$ 2.800 de mensalidades.", "Plano de Saúde"),
    ("Título de capitalização presente de aniversário do banco. Resgate só após 5 anos com perda de 50% do valor. Que presente.", "Capitalização"),
    ("Empréstimo sob consignação intermediado por correspondente bancário com taxa 60% mais alta que diretamente no banco.", "Empréstimo"),
    ("Seguro de vida cobrado mensalmente sem que eu tenha assinado contrato. Telemarketing ligou e eu disse 'vou pensar'.", "Seguro"),
    ("Plano funerário oferecido pelo gerente do banco. Quando minha mãe faleceu, descobri que cobertura era apenas básica. Tive que pagar a diferença.", "Plano Funerário"),
    ("Assistência 24h cobrada todo mês, precisei usar uma vez, não atenderam, telefone caiu duas vezes. Serviço inexistente.", "Assistência"),
]

reclamacoes_app_atendimento = [
    ("Aplicativo do banco trava toda vez que tento acessar fatura do cartão. Já reinstalei 3 vezes.", None),
    ("Atendimento por chat me deixa esperando 45 minutos pra dizer 'precisa ir na agência'. Pra que existe o chat então?", None),
    ("Reconhecimento facial do app não funciona com meus óculos. Tenho que tirar a foto sem óculos, depois não enxergo a tela.", None),
    ("Token caiu, app travou, fiquei sem fazer transferência urgente. Aluguel atrasou.", None),
    ("Atendente me chamou de 'meu querido' o tempo todo. Quero respeito profissional, não intimidade.", None),
    ("URA infinita: aperte 1, depois 3, depois 7, depois 2... 14 minutos pra falar com humano que não resolveu nada.", None),
    ("Ouvidoria respondeu que 'a reclamação está fora do escopo'. Reclamei de uma tarifa indevida. Como isso está fora do escopo?", None),
    ("Banco abriu nova versão do app, perdi acesso aos meus investimentos por 8 dias. Mercado oscilou e eu sem agir.", None),
    ("Chamei suporte por causa de transação suspeita. Atendente desligou na minha cara após 22 minutos.", None),
    ("Tive que ir pessoalmente na agência pra tirar 2ª via de cartão porque o app não permite. Aplicativo serve pra quê?", None),
    ("Mensagens automáticas do banco vêm em português mal traduzido do inglês. 'Você foi creditado!' parece tradução de IA barata.", None),
    ("Site do banco fora do ar das 22h às 6h por causa de manutenção. Trabalho nesse horário.", None),
    ("Atendente passou minha ligação 6 vezes. Cada um pedia que eu repetisse a história desde o início.", None),
    ("Gerente do banco bloqueou meu WhatsApp porque eu estava reclamando demais. Sou cliente, não amigo dele.", None),
]

reclamacoes_investimentos = [
    ("CDB com promessa de 110% do CDI rendendo apenas 87% no extrato. Conferi todos os meses.", "CDB"),
    ("Fundo de investimento com taxa de administração de 3,5% ao ano. Rendeu menos que a poupança.", "Fundo de Investimento"),
    ("Aplicação resgatada antes do prazo perdeu 80% do rendimento. Não foi explicado isso na contratação.", "Investimento"),
    ("Ações compradas via home broker com taxa de corretagem absurda. R$ 19,90 por ordem em 2026?", "Ações"),
    ("Tesouro Direto retirado da conta e nunca apareceu na carteira. R$ 5 mil sumidos por 4 dias.", "Tesouro Direto"),
    ("LCI vendida como 'isenta de IR' com IOF que comeu o ganho. Onde está a isenção prometida?", "LCI"),
    ("Imposto de renda na fonte cobrado em fundo isento. Já mandei comprovantes 3 vezes.", "Investimento"),
    ("Venda de ações executada com cotação de 1 dia depois. Mercado caiu 4% nesse meio tempo.", "Ações"),
]

reclamacoes_outros_diversos = [
    ("Banco vazou meus dados pessoais e agora recebo ligações de golpistas usando informações que só vocês tinham.", None),
    ("Score de crédito caiu sem motivo aparente. Pago tudo em dia, nenhuma negativa.", None),
    ("Pediram pra eu atualizar meus dados, atualizei, mês seguinte pediram de novo. Estou em loop.", None),
    ("Notificação no celular dizendo 'você foi pré-aprovado'. Tentei aceitar, sistema diz que sou negativado. Como é?", None),
    ("Cobrança em agência de R$ 25 pra atualizar foto do cadastro. Foto MINHA, no cadastro DELES.", None),
    ("Banco fechou minha conta por 'incompatibilidade de movimentação' depois que recebi minha herança. Tratado como criminoso.", "Conta Corrente"),
    ("Promessa do gerente de R$ 500 de bônus por indicação de amigo. Amigo abriu conta, bônus nunca chegou. Já são 5 meses.", None),
    ("Recebo correspondências em endereço antigo apesar de ter atualizado o endereço 3 vezes. Carta importante voltou.", None),
    ("Funcionário da agência atendeu falando alto sobre meus saldos onde outros clientes ouviram. Privacidade?", None),
    ("Cobrança de 'taxa de sucesso' de operação de câmbio que eu não autorizei. R$ 178 sumiram.", None),
    ("Cliente VIP há 15 anos. Filho meu solicitou conta, foi negado por baixa renda. Tratamento desigual sem motivo.", None),
    ("Pacote de relacionamento Premium prometia atendimento prioritário. Espero 40 minutos no telefone igual aos outros.", None),
    ("Banco me cobrou IOF por uma operação que não aconteceu. Provei com extrato e nada de estorno.", None),
    ("Mudei de estado, conta continua atrelada à agência antiga, todo serviço presencial é uma novela.", "Conta Corrente"),
    ("Solicitei portabilidade de salário, banco antigo segurou o processo por 4 meses. Lei diz 5 dias úteis.", None),
    ("Boleto pago em dia, banco demorou 3 dias pra reconhecer pagamento, nome foi pro Serasa. Limpeza demorou 2 meses.", None),
]

reclamacoes_creativas_inusitadas = [
    ("Meu gerente foi promovido e a nova gerente é uma pedra. Faço reuniões com uma cadeira vazia, ninguém me liga.", None),
    ("Cabeça de boi na entrada da agência (em referência ao cofre) parece simbólico do tratamento que recebo.", None),
    ("Pediram pra eu provar que sou eu mesma com 12 documentos. Incluindo certidão de nascimento. Eu tenho 67 anos.", None),
    ("Caixa eletrônico cuspiu uma nota de R$ 200 picotada. Banco diz que é responsabilidade da Casa da Moeda. Foi a MÁQUINA de vocês!", None),
    ("Música de espera do telefone do banco é 'Nessun Dorma'. Adequada, porque ninguém dorme esperando atendimento.", None),
    ("Atendente perguntou se eu queria contratar plano de saúde, seguro de vida, capitalização e crédito numa mesma ligação. Era pra eu pagar boleto.", None),
    ("Carteirinha do banco veio com nome errado: 'Maria de Fátima' virou 'Maria de Fátiba'. Erro de digitação não é meu problema.", None),
    ("Banco enviou cartão de aniversário... pra meu pai. Que faleceu há 4 anos. Cliente desde 1971, trataram com respeito até o fim.", None),
    ("Criança de 9 anos conseguiu fazer login na minha conta porque sabia minha senha que era 12345. Culpa minha, mas vocês deveriam exigir senha forte!", None),
    ("Cachorro mordeu o cartão da máquina ao tentar comer (cheirinho de carne). Banco se recusa a emitir nova via porque 'não houve fraude'.", None),
    ("Recebi um e-mail dizendo 'caro Sr João' sendo que sou Joana. Personalização péssima.", None),
    ("Gerente do banco dorme em reunião comigo. Literalmente. Filmei.", None),
]

reclamacoes_complementares_curtinhas = [
    ("Tarifa indevida no extrato. Quero estorno.", None),
    ("Cobrança de seguro que não contratei.", "Seguro"),
    ("Cartão clonado e banco não reembolsa.", "Cartão de Crédito"),
    ("Aplicativo travado há 3 dias.", None),
    ("Pix não cai há horas.", "PIX"),
    ("Limite de cartão reduzido sem aviso.", "Cartão de Crédito"),
    ("Empréstimo aprovado mas dinheiro não caiu.", "Empréstimo"),
    ("Cobrança duplicada na fatura.", "Cartão de Crédito"),
    ("Atendimento horrível na agência tal.", None),
    ("Senha do app não funciona mais.", None),
    ("Conta bloqueada sem motivo.", "Conta Corrente"),
    ("Boleto pago e Serasa negativou meu nome.", None),
    ("Tarifa de manutenção mais cara que rendimento.", "Conta Corrente"),
    ("Não consigo cancelar serviço de SMS.", None),
    ("Estorno prometido nunca chegou.", None),
    ("PIX agendado não foi feito.", "PIX"),
    ("Anuidade cobrada após cancelamento do cartão.", "Cartão de Crédito"),
    ("Cobrança recorrente que cancelei já.", None),
    ("Limite reduzido durante viagem.", "Cartão de Crédito"),
    ("Saque não saiu mas debitou.", "Conta Corrente"),
]

# ============================================================
# AMEAÇAS (poucas, mas variadas)
# ============================================================
ameacas = [
    ("Se não resolverem isso até amanhã eu vou processar o banco e exigir reparação por danos morais.",),
    ("Já procurei advogado e a próxima parada é o Procon e o Banco Central. Vocês não fazem ideia do que vem aí.",),
    ("Vou expor essa palhaçada toda nas redes sociais com nomes de funcionários e tudo. Aguardem viralizar.",),
    ("Estou gravando todas as ligações e vou usar como prova. Vocês deveriam estar preocupados.",),
    ("Vou levar isso pro programa de TV de defesa do consumidor. Quero ver vocês explicando isso na frente das câmeras.",),
    ("Se meu nome não for tirado do Serasa hoje, eu vou pessoalmente na agência fazer um escândalo.",),
    ("Tenho 14 amigos correntistas desse banco e todos vão fechar conta junto comigo. Esperem só.",),
    ("Vou abrir uma ação coletiva. Já estou em contato com outros clientes prejudicados.",),
    ("Se acontecer mais uma cobrança indevida eu vou na imprensa. Tenho contato com jornalista.",),
    ("Estou guardando todos os e-mails e documentos. Quando eu processar, vão ver do que sou capaz.",),
    ("Vocês vão se arrepender de mexer comigo. Tenho recursos pra brigar até o STF se for preciso.",),
    ("Não vou parar até o presidente do banco saber dessa história. Vou cobrar pessoalmente.",),
    ("Próximo passo é boletim de ocorrência. Estelionato é crime, sabiam?",),
    ("Vou denunciar vocês na SUSEP, no Banco Central, no Procon e na Polícia Federal. Tudo de uma vez.",),
    ("Se em 48h nada resolver, contrato advogado especialista. Já tenho os contatos.",),
    ("Sou jornalista. Imagina o que vai sair na minha matéria amanhã sobre essa empresa.",),
    ("Tenho ações do banco e vou usar minha posição de acionista pra incomodar bastante.",),
]

# ============================================================
# ELOGIOS
# ============================================================
elogios = [
    ("Quero parabenizar a atendente Camila da agência centro. Resolveu meu problema em 5 minutos com sorriso e paciência.",),
    ("Sou cliente há 30 anos e nunca tive problema. Atendimento sempre cordial e eficiente.",),
    ("O novo aplicativo está fantástico! Bem mais rápido que o anterior, parabéns à equipe de TI.",),
    ("O gerente João da agência Tatuapé é um exemplo de profissionalismo. Resolveu uma situação complicada com calma.",),
    ("Estou impressionado com a rapidez do atendimento via chat. Em menos de 3 minutos meu problema foi resolvido.",),
    ("PIX é uma maravilha. Banco já melhorou muito desde os tempos do DOC.",),
    ("Minha aposentadoria caiu antes do prazo. Quero agradecer pela agilidade.",),
    ("A reforma da agência Pinheiros ficou linda. Ambiente acolhedor, parabéns.",),
    ("O programa de pontos do cartão me rendeu uma viagem inteira pra Europa. Estou super satisfeito.",),
    ("Atendente da Ouvidoria me ouviu com paciência e resolveu uma reclamação antiga. Recomendo demais.",),
    ("Gerente entrou em contato no meu aniversário. Detalhe simples mas importante.",),
    ("Fui muito bem atendido na agência mesmo sem ter horário marcado. Parabéns à equipe.",),
    ("Aprovação do empréstimo em 4 minutos pelo app. Nem precisei sair de casa. Vida moderna.",),
    ("Educação financeira oferecida pelo banco me ajudou muito a sair das dívidas. Obrigado!",),
    ("A função investimentos automáticos é incrível. Já economizei R$ 3 mil em 6 meses sem perceber.",),
    ("Sempre que ligo no SAC sou bem atendido. Equipe brasileira faz toda a diferença.",),
    ("Cartão de débito virtual pra compras online é uma ideia genial. Mais segurança pra todos.",),
    ("Atendimento em LIBRAS na agência foi maravilhoso. Inclusão de verdade!",),
    ("Reembolso de fraude foi feito em 3 dias úteis. Bem mais rápido que esperava.",),
    ("Treinamento dos atendentes melhorou muito. Antes era horrível, hoje é satisfatório.",),
    ("Quero registrar elogio à Cláudia, atendente do telemarketing. Profissional excelente.",),
    ("Banco patrocinando cultura. Vi a exposição patrocinada por vocês e foi linda.",),
    ("Agendamento online da agência funciona perfeito. Cheguei e fui atendido na hora.",),
    ("App acessível pra deficiente visual. Como cego, agradeço a preocupação com a acessibilidade.",),
    ("Tarifas competitivas no segmento jovem. Bom pra estudantes universitários.",),
    ("Linha de crédito pra pequeno empresário foi essencial pra meu negócio sobreviver. Gratidão.",),
]

# ============================================================
# MENSAGENS IRRELEVANTES
# ============================================================
irrelevantes = [
    ("Bom dia, alguém sabe que horas joga o Flamengo hoje?",),
    ("Preciso da receita do bolo de cenoura da minha vó. Alguém aí sabe?",),
    ("Esse banco tem estacionamento? E pra cachorro pode entrar?",),
    ("Oi tudo bem? rs como vc tá?",),
    ("teste 123 alguem ai?",),
    ("Tô vendo se isso aqui funciona, escrevi qualquer coisa pra ver",),
    ("kkkkk eu adoro mandar mensagem aleatória",),
    ("Procurando emprego, vocês contratam? Mando currículo?",),
    ("Quero saber a previsão do tempo pra amanhã em Florianópolis.",),
    ("Banco abre no domingo? Quero saber só por curiosidade.",),
    ("Como faço pra denunciar meu vizinho que faz barulho?",),
    ("Vocês vendem produtos da Apple? Tô interessado num iPhone.",),
    ("Tem alguma promoção de consórcio de lancha?",),
    ("Aqui é a Marina, será que essa é a área de atendimento mesmo?",),
    ("Olá! Estou vendendo cosméticos naturais. Posso indicar a vocês?",),
    ("Encaminhei a mensagem certa? Era pra minha tia.",),
    ("Boa tarde, qual o horário do almoço da agência?",),
    ("Vocês fazem dedetização?",),
    ("Tô fazendo um TCC sobre bancos digitais, podem responder umas perguntas?",),
    ("Achei um cachorro perdido perto da agência, alguém perdeu?",),
    ("Caí na piscina com o celular, vai dar pra recuperar minha conta?",),
    ("Posso chamar uma pizza pra entregar na agência?",),
    ("Tem alguma vaga pra estagiário? Sou universitário do 5º período.",),
    ("Olá tudo bem, sou da Igreja Esperança e gostaria de convidar...",),
    ("Estou com saudades, quando vou te ver?",),
    ("Mãe, manda dinheiro pra eu pagar o aluguel. Tô apertado.",),
    ("Agora não, estou ocupado.",),
    ("?????",),
    ("teste",),
    ("oi",),
    ("Pode mandar a localização?",),
    ("Tô a caminho",),
    ("Cheguei",),
    ("vc viu meu post novo?",),
    ("alguém comprou ovo pra páscoa esse ano?",),
]

# ============================================================
# MENSAGENS ERRADAS / DESTINO ERRADO
# ============================================================
mensagens_erradas = [
    ("Amor, não esquece de buscar o pão. E o leite também. Beijos.",),
    ("Profe, vou faltar amanhã na aula porque estou doente.",),
    ("Pedi um Uber pra rua das Flores 234, é o cinza?",),
    ("Boa tarde, quero confirmar minha consulta com o Dr. Ricardo às 14h amanhã.",),
    ("Mãe, o ônibus tá atrasado, vou chegar tarde no jantar.",),
    ("Pedido confirmado: 1 pizza calabresa, 1 refrigerante 2L. Entrega em 40min.",),
    ("Reservei mesa pra 4 pessoas às 20h no nome João. Confirma por favor.",),
    ("Doutor, estou com dor no joelho desde ontem. Posso passar antes?",),
    ("Confirmando consulta veterinária da Bisteca amanhã às 10h.",),
    ("Olá, sou da imobiliária. O imóvel da rua tal ainda está disponível?",),
    ("Galera, lembrando do treino amanhã às 6h, não atrasem.",),
    ("Senhor, sua encomenda chegou e está aguardando retirada nos correios da Vila Madalena.",),
    ("Vou viajar amanhã, alguém pode dar uma olhada nas plantas?",),
    ("Fiz a marmita do almoço, deixei na geladeira. É a azul.",),
    ("Boa noite, quero agendar manutenção do ar condicionado.",),
    ("Sua corrida foi cancelada. R$ 15 estornados em até 24h.",),
    ("Mensagem da escola: aviso de reunião de pais dia 15 às 19h30.",),
    ("Olá, recebi seu currículo e gostaria de marcar uma entrevista.",),
    ("Faltou pagar a faxineira, vou passar o pix dela?",),
    ("Doutor, esqueci de marcar retorno. Tem horário semana que vem?",),
    ("Boa noite, gostaria de cancelar minha assinatura da revista.",),
    ("Não esquece da reunião de família domingo na casa da vovó.",),
]

# ============================================================
# CHANNELS, STATUS, DATA RANGE
# ============================================================
canais = ["SAC", "Ouvidoria", "Banco Central", "Redes Sociais"]
canais_pesos = [40, 25, 15, 20]

status_list = ["Aberta", "Em análise", "Resolvida"]
status_pesos = [35, 30, 35]

start_date = date(2025, 6, 1)
end_date = date(2026, 4, 25)
date_range_days = (end_date - start_date).days

# ============================================================
# MONTAR LISTA COMPLETA - 500 ITENS
# ============================================================
todas_reclamacoes = []
todas_reclamacoes.extend(reclamacoes_cartao)
todas_reclamacoes.extend(reclamacoes_conta)
todas_reclamacoes.extend(reclamacoes_emprestimo)
todas_reclamacoes.extend(reclamacoes_pix_transferencia)
todas_reclamacoes.extend(reclamacoes_taxas_servicos)
todas_reclamacoes.extend(reclamacoes_terceiros)
todas_reclamacoes.extend(reclamacoes_app_atendimento)
todas_reclamacoes.extend(reclamacoes_investimentos)
todas_reclamacoes.extend(reclamacoes_outros_diversos)
todas_reclamacoes.extend(reclamacoes_creativas_inusitadas)
todas_reclamacoes.extend(reclamacoes_complementares_curtinhas)

# Variações para gerar mais conteúdo único nas reclamações
nomes_agencia = ["centro", "Tatuapé", "Pinheiros", "Moema", "Vila Mariana", "Itaim", "Barra Funda", "Mooca", "Lapa", "Bela Vista", "Santana", "Higienópolis", "Aclimação", "Brooklin", "Jardins"]
valores_baixos = ["R$ 12,90", "R$ 25,00", "R$ 38,50", "R$ 47,00", "R$ 89,90", "R$ 110,00", "R$ 145,80"]
valores_altos = ["R$ 1.200,00", "R$ 2.450,00", "R$ 3.700,00", "R$ 5.890,00", "R$ 8.300,00", "R$ 12.700,00", "R$ 18.500,00"]

reclamacoes_extras = []
templates_extras = [
    ("Fui à agência {agencia} resolver problema com cobrança de {valor} e ninguém soube me explicar. Voltei pra casa sem solução.", None),
    ("Cobrança indevida de {valor} na minha fatura referente a serviço que nunca contratei. Já abri 3 protocolos e nada.", None),
    ("Desconto não autorizado de {valor} na minha conta corrente. Pediram pra esperar 30 dias úteis pra análise. É demais.", "Conta Corrente"),
    ("Apareceu na fatura uma compra de {valor} numa cidade que eu nunca pisei. Cartão estava comigo. Como?", "Cartão de Crédito"),
    ("Tentei resolver questão de {valor} de tarifa pelo aplicativo, virou loop infinito de telas. Frustrante.", None),
    ("Tarifa de {valor} chamada genericamente de 'serviços' sem detalhamento. O que é isso?", None),
    ("Gerente da agência {agencia} prometeu estorno de {valor}, foram 4 meses, nada. Já não retorna minhas ligações.", None),
    ("Saque negado mas o valor de {valor} foi descontado. Demorou 12 dias pra estornar.", "Conta Corrente"),
    ("Empréstimo de {valor} aprovado verbalmente, contrato veio com taxa diferente da combinada. Recusei e ainda assim cobraram tarifa de cancelamento.", "Empréstimo"),
    ("Investimento de {valor} resgatado com perda de {valor_baixo} de IOF que não foi alertado na hora.", "Investimento"),
    ("Transferência de {valor} pra conta errada por erro do app. Banco diz que culpa é minha. Não foi minha digitação, foi sugestão automática.", "Transferência"),
    ("Solicitei adiamento de fatura de {valor} por dificuldade financeira. Atendente debochou: 'aprende a controlar dinheiro'.", "Cartão de Crédito"),
    ("Promessa de cashback de {valor} por gasto mínimo. Cumpri o gasto, cashback nunca veio.", "Cartão de Crédito"),
    ("Cobrança de seguro residencial de {valor_baixo} mensal sem que eu tenha autorizado. Já são 14 meses descontando.", "Seguro"),
    ("Linha de crédito de {valor} aprovada e cancelada no mesmo dia sem explicação. Já organizei pagamentos com base nela.", "Empréstimo"),
    ("Conta poupança rendendo menos que aplicação automática. Banco poderia avisar isso.", "Poupança"),
    ("Cartão de débito clonado em {valor}. Banco diz que não cobre porque eu ativei o cartão fora do aplicativo.", "Cartão de Débito"),
    ("Bloqueio preventivo de {valor} no meu cartão durante viagem internacional. Fiquei sem comer numa cidade estrangeira.", "Cartão de Crédito"),
    ("Dia de pagamento do FGTS, sistema do banco fora do ar. Tive que ir 3 vezes na agência {agencia}.", None),
    ("Pacote Premium custa {valor_baixo} mensais e não recebo nenhum benefício além do nome bonito.", None),
]

for i in range(60):
    template, prod = random.choice(templates_extras)
    texto = template.format(
        agencia=random.choice(nomes_agencia),
        valor=random.choice(valores_altos),
        valor_baixo=random.choice(valores_baixos)
    )
    reclamacoes_extras.append((texto, prod))

todas_reclamacoes.extend(reclamacoes_extras)

# Calcular distribuição
# Total: 500
# Reclamações: ~370
# Elogios: ~50
# Irrelevantes: ~40
# Mensagens erradas: ~25
# Ameaças: ~15

todos_itens = []

# Adiciona reclamações (~370) - permite repetições controladas
qtd_reclamacoes = 370
random.shuffle(todas_reclamacoes)
for i in range(qtd_reclamacoes):
    rec = todas_reclamacoes[i % len(todas_reclamacoes)]
    todos_itens.append(("reclamacao", rec[0], rec[1]))

# Adiciona elogios (~50)
qtd_elogios = 50
for i in range(qtd_elogios):
    el = elogios[i % len(elogios)]
    todos_itens.append(("elogio", el[0], None))

# Adiciona irrelevantes (~40)
qtd_irrelevantes = 40
for i in range(qtd_irrelevantes):
    ir = irrelevantes[i % len(irrelevantes)]
    todos_itens.append(("irrelevante", ir[0], None))

# Adiciona mensagens erradas (~25)
qtd_erradas = 25
for i in range(qtd_erradas):
    er = mensagens_erradas[i % len(mensagens_erradas)]
    todos_itens.append(("errada", er[0], None))

# Adiciona ameaças (~15)
qtd_ameacas = 15
for i in range(qtd_ameacas):
    am = ameacas[i % len(ameacas)]
    todos_itens.append(("ameaca", am[0], None))

print(f"Total de itens montados: {len(todos_itens)}")

# Embaralhar tudo
random.shuffle(todos_itens)

# Montar registros finais
registros = []
for i, (tipo, texto, produto) in enumerate(todos_itens):
    rec_id = f"REC-2026-{str(i+1).zfill(5)}"
    dia_random = random.randint(0, date_range_days)
    data_rec = (start_date + timedelta(days=dia_random)).isoformat()
    canal = random.choices(canais, weights=canais_pesos, k=1)[0]
    status = random.choices(status_list, weights=status_pesos, k=1)[0]
    
    # Para irrelevantes, erradas e ameaças, produto fica vazio com mais frequência
    if tipo in ("irrelevante", "errada", "ameaca", "elogio") and produto is None:
        prod_final = ""
    else:
        prod_final = produto if produto else ""
    
    registros.append({
        "id": rec_id,
        "data_reclamacao": data_rec,
        "canal": canal,
        "texto_reclamacao": texto,
        "produto": prod_final,
        "status": status,
    })

# Escrever CSV
import sys
output_path = sys.argv[1] if len(sys.argv) > 1 else "data/reclamacoes_bancarias_500.csv"
pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["id", "data_reclamacao", "canal", "texto_reclamacao", "produto", "status"],
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writeheader()
    for r in registros:
        writer.writerow(r)

print(f"CSV gerado em: {output_path}")
print(f"Total de registros: {len(registros)}")

# Estatísticas rápidas
from collections import Counter
canal_counter = Counter(r["canal"] for r in registros)
status_counter = Counter(r["status"] for r in registros)
produto_counter = Counter(r["produto"] if r["produto"] else "(vazio)" for r in registros)
print("\nDistribuição por canal:", dict(canal_counter))
print("Distribuição por status:", dict(status_counter))
print("Top produtos:", produto_counter.most_common(8))
