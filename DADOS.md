4 EXPERIMENTOS E RESULTADOS

4.1 Introdução

4.2 Protótipo Integrado ao Ambiente Experimental
    4.2.1 Configuração Final do Protótipo
    4.2.2 Condições e Registros dos Ensaios

4.3 Resultados do Monitoramento e Controle
    4.3.1 Identificação dos Níveis e Sinalização
    4.3.2 Acionamento Automático
    4.3.3 Acionamento Remoto e Prioridade Física
    4.3.4 Registro dos Eventos e Estados de Acionamento

4.4 Resultados da Aplicação Web e Android
    4.4.1 Visualização do Estado do Sistema
    4.4.2 Apresentação da Interface nas Duas Plataformas
    4.4.3 Consulta ao Histórico e Geração de Relatórios

4.5 Resultados da Detecção de Anomalias
    4.5.1 Identificação de Inconsistências nos Eventos
    4.5.2 Detecção de Ciclo de Enchimento Lento
    4.5.3 Agrupamento e Evidências Produzidas pelo AutoCloud

4.6 Resultados do Assistente em Linguagem Natural
    4.6.1 Consultas com o Modelo Local
    4.6.2 Consultas com o Modelo Online
    4.6.3 Correspondência entre Respostas e Dados do Sistema

4.7 Considerações Finais



| Seção | Evidências existentes | Complemento útil |
|---                          |---                                                    |                                                                      ---|
| **4.2 Protótipo integrado** | Fotografia externa e registro da operação na bancada. | Nenhum inicialmente. A montagem passo a passo permanece na Metodologia. |
| **4.3 Monitoramento e controle** | Fotografia da condição de nível baixo e relato dos acionamentos. | Registros de uma sequência automática e de comandos remoto e físico, obtidos no histórico, Firestore ou logs. |
| **4.4 Aplicação web e Android** | Três capturas da tela principal, tela de histórico e trecho do relatório PDF. | Se possível, histórico e relatório referentes ao mesmo período, para conferir a correspondência dos valores. |
| **4.5 Detecção de anomalias** | Alerta de ciclo lento e tabela com 12 ciclos históricos, mediana de 482,5 s, ciclo de 960 s e distância normalizada de 90,76. | Exemplo de alerta determinístico e durações dos 12 ciclos para construir um gráfico. |
| **4.6 Assistente** | Exemplos de consulta ao modelo local e ao online. | Uma pequena bateria com as mesmas perguntas nos dois modelos e os dados de referência para conferir as respostas. |
| **4.7 Síntese** | Resultados apresentados nas seções anteriores. | Tabela curta relacionando resultado, evidência e limite da avaliação. |





Para reforçar o capítulo sem exigir novas montagens físicas, os complementos mais úteis são:
1. Controle: uma sequência de eventos e comandos contendo horário, origem, estado solicitado, aplicação e confirmação. Pode ser uma exportação ou captura legível.
2. AutoCloud: os tempos dos 12 ciclos utilizados como histórico. Com eles, construo um gráfico do histórico e do ciclo de 960 s, indicando a mediana e o limite de detecção.
3. Regras determinísticas: um exemplo registrado de inconsistência e o alerta correspondente.
4. Chatbot: três a cinco perguntas iguais nos dois modelos, acompanhadas dos valores corretos consultados no sistema.