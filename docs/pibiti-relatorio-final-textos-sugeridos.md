# Textos sugeridos para complementacao do relatorio final PIBITI

Data de consolidacao: 2026-08-28.

Este arquivo contem textos sugeridos para as secoes de Resumo, Abstract, Metodologia, Resultados e Conclusao do relatorio final. Os trechos podem ser adaptados ao estilo do documento em LaTeX. A Introducao e a Fundamentacao Teorica nao foram incluidas porque a instrucao do `PROMPT.md` indica que elas nao precisam de alteracao neste momento.

## Resumo sugerido

Este trabalho apresenta o desenvolvimento e a validacao experimental do AquaMonitor, um sistema inteligente de baixo custo para monitoramento e controle de reservatorios de agua. A solucao integra um modulo embarcado baseado em ESP32, sensores de nivel tipo boia, acionamento de bomba por rele, sinalizacao local por LEDs, chave fisica de controle, comunicacao MQTT, persistencia em nuvem com Firestore, backend FastAPI, aplicacao web/mobile em Ionic React e um assistente baseado em modelos de linguagem. O firmware registra eventos de sensores e comandos com identificacao do dispositivo, timestamp sincronizado, confirmacao de acionamento e buffer offline para tolerancia a falhas temporarias de conectividade. No backend, os eventos sao processados por regras deterministas de consistencia, rotinas de idempotencia, calculos de ciclos de enchimento, estimativas de consumo de agua e energia e uma camada AutoCloud para deteccao de anomalias temporais no tempo de enchimento. A interface permite visualizar o estado do reservatorio e da bomba, consultar historico por periodo, gerar relatorios e interagir com um chatbot analitico conectado aos dados do sistema. O prototipo foi validado em ambiente de laboratorio com sensores reais acionados manualmente e montagem fisica em case tridimensional, demonstrando a integracao entre hardware, firmware, nuvem, backend, aplicativo Android e recursos de inteligencia artificial. Como resultado, o sistema consolidou uma arquitetura funcional para monitoramento residencial ou predial, com capacidade de registro historico, alertas automatizados e apoio a tomada de decisao sobre operacao da bomba e uso de agua.

Palavras-chave: monitoramento de agua; ESP32; Internet das Coisas; Firestore; MQTT; AutoCloud; chatbot; aplicativo movel.

## Abstract sugerido

This work presents the development and experimental validation of AquaMonitor, a low-cost intelligent system for water tank monitoring and pump control. The solution integrates an ESP32-based embedded module, float level sensors, relay-based pump actuation, local LED indicators, a physical control switch, MQTT communication, Firestore cloud persistence, a FastAPI backend, an Ionic React web/mobile application, and a language-model-based assistant. The firmware records sensor and command events with device identification, synchronized timestamps, actuation confirmation, and an offline buffer for temporary connectivity failures. In the backend, events are processed through deterministic consistency rules, idempotency routines, filling-cycle calculation, water and energy consumption estimates, and an AutoCloud layer for temporal anomaly detection in reservoir filling time. The interface enables users to monitor the tank and pump state, inspect historical data by period, generate reports, and interact with an analytical chatbot connected to system data. The prototype was validated in a laboratory environment using real manually actuated float sensors and a physical enclosure produced for the experiment, demonstrating integration among hardware, firmware, cloud services, backend, Android application, and artificial intelligence resources. The final system provides a functional architecture for residential or building-scale monitoring, including historical records, automated alerts, and decision support for pump operation and water usage analysis.

Keywords: water monitoring; ESP32; Internet of Things; Firestore; MQTT; AutoCloud; chatbot; mobile application.

## Metodologia sugerida

O desenvolvimento do AquaMonitor foi conduzido em etapas incrementais, envolvendo a construcao do modulo embarcado, a definicao dos contratos de comunicacao, a implementacao do backend, a criacao da aplicacao web/mobile, a integracao com servicos de nuvem e a validacao experimental em laboratorio. A arquitetura adotada separa responsabilidades entre firmware, aplicacao cliente, API server-side, Functions do Firebase e banco de dados Firestore, permitindo que cada camada seja testada e evoluida de forma independente.

No modulo embarcado, utilizou-se um ESP32 conectado a dois sensores de nivel tipo boia, responsaveis pela identificacao dos estados de nivel baixo e nivel alto do reservatorio. O circuito tambem contempla acionamento de bomba por rele, leitura de status da bomba, tres LEDs de sinalizacao para niveis baixo, medio e alto, alem de uma chave fisica para controle local. O firmware realiza leitura das entradas digitais, aplica logica de prioridade entre acionamento automatico, comando remoto e chave fisica, publica o estado da bomba por MQTT e registra eventos no Firestore por meio da API REST. Para aumentar a robustez, foram incorporados identificacao do dispositivo, timestamps sincronizados por NTP, confirmacao de comandos aplicados e um buffer offline capaz de armazenar 32 escritas pendentes em caso de indisponibilidade temporaria da rede.

A comunicacao foi estruturada com dois mecanismos complementares. O MQTT foi utilizado para comandos de baixa latencia e sincronizacao do estado da bomba, por meio dos topicos `bomba/controle`, `bomba/controle/v2` e `bomba/estado`. O Firestore foi utilizado como camada persistente para eventos de sensores, comandos, sessoes de chat, alertas, ciclos de enchimento e controle de idempotencia. Essa separacao permite que o aplicativo responda rapidamente a comandos operacionais sem perder o registro historico necessario para auditoria, relatorios e analises temporais.

O backend foi desenvolvido em FastAPI e organizado em rotas para saude da aplicacao, chatbot, agente IA, relatorios e alertas. A API implementa 13 endpoints principais, incluindo recepcao de eventos de sensores e comandos, consulta de alertas, reconhecimento de alertas, sumarios historicos e geracao de relatorios. As Firebase Functions monitoram novas escritas nas colecoes `sensores` e `comandos` e encaminham os eventos ao backend, onde sao normalizados, validados e persistidos de forma idempotente. Essa etapa evita processamento duplicado e reduz o risco de que eventos inconsistentes alimentem metricas historicas.

Para deteccao de inconsistencias, foram implementadas regras deterministas sobre a sequencia dos sensores. Essas regras identificam eventos sem timestamp, eventos fora de ordem, duplicidade, repeticoes inesperadas, acionamento incoerente do sensor alto, queda do sensor baixo enquanto o sensor alto permanece ativo e tempos hidraulicamente improvaveis. Quando necessario, os alertas bloqueiam o processamento de ciclos para impedir que dados invalidos interfiram nas estimativas de consumo ou nas analises temporais.

A camada AutoCloud foi aplicada sobre os ciclos validos de enchimento. O sistema identifica o fechamento de um ciclo quando ha informacoes suficientes para calcular o tempo entre o inicio do enchimento e o acionamento do sensor de nivel alto. Em seguida, o tempo do ciclo atual e comparado com ciclos historicos validos. A analise exige, por padrao, pelo menos cinco ciclos anteriores e pode gerar tres tipos de alerta: ciclo de enchimento lento, aumento persistente do tempo de enchimento e novo agrupamento temporal fora do padrao. A finalidade dessa camada e detectar anomalias e sugerir possiveis causas, nao substituir uma inspecao hidraulica ou eletrica definitiva.

A aplicacao cliente foi desenvolvida com Ionic React, Vite e TypeScript. A interface inclui dashboard em tempo real, pagina de historico com filtros por periodo e abas para agua, energia e sensores, alem de uma pagina de chat IA. O historico consome dados agregados do backend, enquanto o dashboard combina leitura do Firestore e mensagens MQTT. A aplicacao foi empacotada para Android com Capacitor 7, mantendo o mesmo codigo-base da versao web. A versao iOS nao foi finalizada no escopo atual.

O chatbot foi implementado com um agente analitico no backend. A interface envia perguntas ao endpoint `POST /agent`, que identifica a intencao, consulta dados do sistema quando aplicavel, monta um contexto estruturado e encaminha a resposta a um provedor LLM configuravel. O backend possui suporte a Ollama, Gemini e OpenAI, alem de resposta deterministica de fallback quando o provedor externo esta indisponivel.

Sugestao de figura para esta secao: incluir um diagrama de arquitetura com ESP32, sensores, MQTT, Firestore, Firebase Functions, backend FastAPI, aplicativo Ionic/Android e provedor LLM. Tambem e recomendavel incluir uma tabela de pinos do ESP32 e uma tabela dos topicos MQTT.

## Resultados sugeridos

Como resultado final, obteve-se um prototipo funcional do AquaMonitor, composto por modulo embarcado, backend, aplicacao web/mobile, integracao com nuvem, chatbot e mecanismo de alertas. A validacao ocorreu em ambiente de laboratorio, utilizando sensores de nivel reais acionados manualmente e montagem fisica em case tridimensional. Esse ambiente permitiu verificar o comportamento integrado do sistema sem depender de uma instalacao hidraulica definitiva em campo.

No modulo embarcado, o firmware final passou a controlar dois sensores de nivel, uma saida de acionamento da bomba, uma entrada de confirmacao de status, tres LEDs de sinalizacao e uma chave fisica. Foram utilizados oito GPIOs principais do ESP32. O dispositivo registra eventos com identificador unico, timestamp sincronizado, identificador do dispositivo e metadados de aplicacao ou confirmacao de comandos. Tambem foi implementado buffer offline de 32 eventos, com novas tentativas de envio ao Firestore a cada 5000 ms, aumentando a tolerancia a falhas temporarias de conectividade.

A comunicacao entre camadas foi consolidada com tres topicos MQTT principais e seis colecoes Firestore. O MQTT viabiliza controle remoto e atualizacao de estado da bomba, enquanto o Firestore armazena eventos, comandos, alertas, ciclos de enchimento e sessoes de chat. As Firebase Functions foram estruturadas para reagir a novas escritas em `sensores` e `comandos` e encaminhar os dados ao backend, mantendo a separacao entre registro de eventos e processamento server-side.

O backend FastAPI consolidou 13 endpoints principais. Entre eles, destacam-se as rotas de recepcao de eventos, consulta e reconhecimento de alertas, geracao de sumarios historicos, emissao de relatorios e atendimento ao agente IA. Os testes locais encontrados no repositorio incluem 59 testes Python no backend, 6 testes TypeScript nas Firebase Functions e 12 testes/specs no frontend, cobrindo regras de alertas, consumo, energia, relatorios, provedores de LLM, processamento de payloads e partes da interface.

O historico do sistema deixou de depender apenas de valores simulados e passou a consumir os sumarios do backend. A tela apresenta filtros por periodo, incluindo 7, 30 e 90 dias, e organiza as informacoes em abas de agua, energia e sensores. A estimativa de consumo de agua considera ciclos validos de enchimento e utiliza como parametros padrao 500 L entre os sensores e tarifa de R$ 8,00/m3. A estimativa de energia considera eventos aplicados e confirmados da bomba, potencia padrao de 0,75 kW e tarifa de R$ 0,656/kWh. Esses valores sao configuraveis por variaveis de ambiente e devem ser interpretados como estimativas, pois o prototipo nao utiliza medidor de vazao nem medidor eletrico dedicado.

O mecanismo de alertas foi dividido em duas camadas. A primeira, deterministica, identifica sete categorias de inconsistencias em eventos de sensores, como ausencia de timestamp, eventos fora de ordem, duplicidade e sequencias fisicamente incoerentes. A segunda, associada ao AutoCloud, analisa o tempo de enchimento dos ciclos validos e pode detectar ciclo lento, aumento persistente do tempo de enchimento ou novo agrupamento temporal fora do padrao historico. Por padrao, essa analise exige pelo menos cinco ciclos historicos validos antes de gerar inferencias temporais.

O assistente IA foi integrado a interface por meio da pagina de chat. O backend suporta tres provedores de modelos de linguagem, Ollama, Gemini e OpenAI, e preserva historico de conversa em `chat_sessions`. A resposta do agente e enriquecida por contexto obtido nas rotas e servicos do sistema, permitindo responder perguntas sobre estado, consumo, alertas e relatorios. Quando o provedor LLM nao responde, o backend possui fallback deterministico para evitar que o usuario fique sem retorno.

A aplicacao foi empacotada para Android por meio do Capacitor 7, com identificador `br.com.aquamonitor.app` e nome `AquaMonitor`. As specs do projeto registram validacao manual em dispositivo Android fisico conectado por USB. A versao iOS permanece como trabalho futuro ou pendencia de publicacao, pois nao ha projeto iOS finalizado no repositorio.

Tabela quantitativa sugerida para a secao de resultados:

| Item avaliado | Resultado consolidado |
| --- | --- |
| Sensores de nivel | 2 sensores tipo boia |
| Atuadores principais | 1 bomba/rele |
| Indicadores locais | 3 LEDs de nivel |
| Controle local | 1 chave fisica |
| GPIOs principais usados | 8 GPIOs |
| Topicos MQTT | 3 topicos |
| Colecoes Firestore | 6 colecoes principais/tecnicas |
| Endpoints backend | 13 endpoints principais |
| Provedores LLM | 3 provedores implementados |
| Regras deterministicas de alerta | 7 regras |
| Alertas temporais AutoCloud | 3 tipos |
| Periodos do historico | 7, 30 e 90 dias |
| Buffer offline do ESP32 | 32 eventos pendentes |
| Retry de envio Firestore | 5000 ms |
| Testes backend encontrados | 59 testes Python |
| Testes Functions encontrados | 6 testes TypeScript |
| Testes/specs frontend encontrados | 12 testes/specs |
| Plataforma mobile validada | Android |
| Plataforma mobile pendente | iOS |

Sugestoes de imagens para esta secao:

- Foto do prototipo fisico montado no case/caixa 3D.
- Foto ou detalhe dos sensores boia no reservatorio experimental.
- Captura do dashboard com estado do nivel e da bomba.
- Captura da pagina de historico exibindo abas de agua, energia e sensores.
- Captura do chatbot respondendo a uma pergunta sobre alertas ou consumo.
- Diagrama simples do fluxo de eventos ate a geracao de alerta.

## Conclusao sugerida

O desenvolvimento do AquaMonitor resultou em um sistema integrado para monitoramento e controle de reservatorios de agua, validado em ambiente de laboratorio e composto por hardware embarcado, comunicacao em nuvem, backend, interface web/mobile, relatorios, alertas e assistente IA. O prototipo demonstrou que e possivel combinar sensores de baixo custo, ESP32, MQTT, Firestore, FastAPI e Ionic React para construir uma solucao funcional de acompanhamento do nivel do reservatorio e de apoio a operacao da bomba.

Do ponto de vista quantitativo, o sistema final integra dois sensores de nivel, uma bomba controlada por rele, tres LEDs, uma chave fisica, oito GPIOs principais, tres topicos MQTT, seis colecoes Firestore e treze endpoints no backend. A camada de analise contempla sete regras deterministicas para consistencia de eventos e tres tipos de alertas temporais relacionados ao AutoCloud. Alem disso, o firmware incorpora buffer offline de 32 eventos e tentativas periodicas de reenvio, enquanto o backend oferece estimativas de consumo de agua e energia com parametros configuraveis.

Os resultados tambem indicam avancos em relacao a uma solucao apenas embarcada. A aplicacao permite acompanhamento em tempo real, consulta historica por periodo, visualizacao de graficos, geracao de relatorios e interacao com chatbot. A conversao para Android amplia a possibilidade de uso em dispositivos moveis, mantendo a versao web como base comum. O assistente IA, por sua vez, acrescenta uma camada de interpretacao sobre os dados do sistema, com suporte a diferentes provedores de modelos de linguagem e fallback deterministico.

Apesar dos resultados obtidos, alguns limites devem ser registrados. As estimativas de consumo de agua e energia dependem de parametros configurados e nao substituem medidores dedicados de vazao ou energia. A validacao ocorreu em laboratorio, nao em implantacao prolongada em condominio ou ambiente produtivo. A versao iOS permanece pendente e a efetividade estatistica do AutoCloud tende a aumentar conforme novos ciclos reais de enchimento sejam acumulados no Firestore. Ainda assim, o sistema alcancou o objetivo de consolidar uma plataforma funcional, extensivel e testavel para monitoramento inteligente de reservatorios de agua.

## Trechos atuais que devem ser removidos ou substituidos

- Substituir ocorrencias de "relatorio parcial", "resultados parciais" e "desenvolvimento inicial" por redacao de relatorio final.
- Remover a ideia de que o chatbot, o historico ou os relatorios sao apenas previstos, pois ha implementacao no backend e no frontend.
- Evitar "dados mockados" na descricao do resultado final; se necessario, mencionar apenas que mocks foram usados em fases preliminares.
- Substituir mencoes antigas a `qwen2:0.5b` por descricao generica de provedores LLM ou pela configuracao atual aplicavel.
- Evitar afirmar que o AutoCloud diagnostica defeitos; usar "detecta anomalias temporais e sugere possiveis causas".
- Evitar afirmar implantacao em ambiente real se a validacao comprovada foi em laboratorio.
- Manter Android como resultado final e iOS como pendencia.

