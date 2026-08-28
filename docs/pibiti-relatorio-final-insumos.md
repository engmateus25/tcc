# Insumos tecnicos para relatorio final PIBITI - AquaMonitor

Data de consolidacao: 2026-08-28.

Este arquivo reune informacoes factuais do projeto AquaMonitor para alimentar a redacao do relatorio final PIBITI/TCC em LaTeX. Ele nao e o texto final do relatorio; serve como base tecnica para outro modelo ou para revisao humana.

## Limitacao de revisao

Nao foi localizado no repositorio o PDF completo do relatorio final PIBITI/TCC citado no `PROMPT.md`. Foram encontrados apenas PDFs operacionais gerados pelo backend, como `backend/generated/relatorio_90d_20260824_132115.pdf` e `backend/relatorio_7d_20251111_112031.pdf`. Portanto, as divergencias textuais foram avaliadas a partir dos trechos fornecidos no `PROMPT.md`, do `README.md`, das specs e do codigo-fonte.

## Fontes locais consultadas

- `PROMPT.md`: instrucoes do professor, trechos atuais do relatorio e objetivo da tarefa.
- `README.md`: arquitetura consolidada, comandos de execucao, contratos de integracao e estado conhecido.
- `BASE_TECNICA_PARA_O_CHATGPT.md`: base tecnica anterior, com alertas sobre termos e escopo.
- `specs/000-plano-geral-pendencias.md`, `specs/TASKS.md` e `specs/RESPOSTA_1_CODEX.md`: historico de implementacao, validacoes e pendencias.
- `backend/app`: FastAPI, agente IA, relatorios, consumo, energia, alertas, AutoCloud e Firestore.
- `frontend/src`: paginas, servicos HTTP, Firebase client SDK, MQTT e configuracao Ionic/Capacitor.
- `functions/src`: Firebase Functions para eventos de sensores e comandos.
- `firmware/TCC.ino/TCC_Final/TCC_Final.ino`: firmware ESP32 final.

## Estado consolidado do projeto

O AquaMonitor pode ser descrito como um sistema finalizado em ambiente de laboratorio para monitoramento e controle de reservatorio de agua. O prototipo integra um modulo embarcado ESP32, sensores de nivel, controle de bomba, sinalizacao por LEDs, chave fisica de acionamento, comunicacao MQTT, persistencia em Firestore, backend FastAPI, aplicacao web/mobile Ionic React e assistente IA baseado em LLM.

O projeto possui validacao em bancada/laboratorio, com sensores boia reais acionados manualmente e com o conjunto fisico montado em case/caixa 3D. Nao ha evidencia no repositorio de implantacao em um condominio real ou em ambiente produtivo externo, portanto a redacao deve evitar afirmar validacao em campo operacional.

## Arquitetura resumida

Fluxo operacional principal:

```text
ESP32 -> Firestore REST -> colecao sensores
Firestore sensores -> Firebase Function -> Backend /alerts/sensor-event
Firestore comandos -> Firebase Function -> Backend /alerts/command-event
Frontend -> Firestore client SDK -> dashboard em tempo real
Frontend -> MQTT -> topicos de controle da bomba
Frontend -> FastAPI -> chat IA, agente, historico, relatorios e alertas
Backend -> Firebase Admin -> sessoes, eventos processados, alertas e ciclos de enchimento
```

Dominios:

- `firmware/`: leitura fisica dos sensores, controle local/remoto da bomba, envio de eventos e buffer offline.
- `frontend/`: interface Ionic React/Vite, dashboard, historico, chat IA e build Android via Capacitor.
- `backend/`: API FastAPI, integracao server-side com Firebase, relatorios, alertas e agente IA.
- `functions/`: gatilhos Firestore que encaminham eventos para o backend.

## Modulo embarcado e hardware

O firmware final usa ESP32 e o sketch `firmware/TCC.ino/TCC_Final/TCC_Final.ino`.

Elementos fisicos documentados no codigo:

- 2 sensores de nivel: sensor baixo no GPIO 18 e sensor alto no GPIO 21.
- 1 saida de acionamento da bomba/rele: GPIO 22.
- 1 entrada de status da bomba: GPIO 23.
- 3 LEDs de estado: nivel baixo no GPIO 32, nivel medio no GPIO 19 e nivel alto no GPIO 33.
- 1 chave fisica de acionamento: GPIO 25.
- 1 identificador de dispositivo padrao: `esp32-reservatorio-01`.
- Buffer offline configurado para 32 escritas pendentes no Firestore.
- Intervalo de nova tentativa para flush do Firestore: 5000 ms.
- Sincronizacao de horario via NTP com `pool.ntp.org` e `time.nist.gov`.

O firmware registra eventos com `event_id`, `device_id`, `sensor`, `estado`, `timestamp` e metadados de confirmacao quando aplicavel. Para comandos da bomba, o firmware diferencia comando aplicado, confirmado e sobrescrito por acionamento fisico ou remoto.

## MQTT

Topicos documentados:

- `bomba/controle`: comando textual legado no formato `<nome> ligar` ou `<nome> desligar`.
- `bomba/controle/v2`: topico estruturado para comando de controle da bomba.
- `bomba/estado`: publicacao do estado da bomba para consumo pela aplicacao.

Na redacao, vale destacar que o MQTT e usado para baixa latencia no controle remoto e no retorno de estado, enquanto o Firestore e usado como registro persistente para historico, relatorios e analise posterior.

## Firestore

Colecoes principais:

- `sensores`: eventos de sensores e registros enviados pelo ESP32.
- `comandos`: comandos e acionamentos de bomba.
- `chat_sessions`: sessoes e mensagens do chatbot no backend.
- `sensor_event_processing`: controle de idempotencia e processamento dos eventos.
- `alerts`: alertas deterministas e alertas de comportamento temporal.
- `filling_cycles`: ciclos validos de enchimento do reservatorio.

Nao tratar `autocloud` como colecao operacional atual sem confirmar no codigo/deploy. A implementacao atual do AutoCloud no backend persiste seus resultados por meio de `alerts` e dos ciclos analisados em `filling_cycles`.

## Backend e endpoints

O backend e uma API FastAPI. Foram identificados 13 endpoints principais:

- `GET /health`
- `POST /llm/chat`
- `POST /llm/chat/stream`
- `GET /llm/sessions/{session_id}`
- `POST /agent`
- `GET /reports/summary`
- `GET /reports/weekly`
- `GET /reports/monthly`
- `GET /alerts/sensors`
- `GET /alerts`
- `PATCH /alerts/{alert_id}/ack`
- `POST /alerts/sensor-event`
- `POST /alerts/command-event`

O agente IA analitico usa o endpoint `POST /agent`. Ele detecta a intencao da pergunta, consulta dados do sistema quando necessario, monta contexto estruturado e chama o provedor LLM configurado. Os provedores implementados sao Ollama, Gemini e OpenAI, com fallback deterministico quando a chamada ao provedor externo falha.

## Alertas deterministas

As regras deterministas de eventos de sensores ficam em `backend/app/services/sensor_rules.py`. Foram identificados 7 tipos principais:

- `missing_timestamp`: evento sem timestamp valido.
- `out_of_order_event`: evento fora de ordem temporal.
- `duplicate_event`: evento duplicado.
- `unexpected_low_repeat`: repeticao inesperada do sensor baixo.
- `implausible_drain_time`: tempo de esvaziamento hidraulicamente improvavel.
- `unexpected_high_without_low`: sensor alto acionado sem estado coerente do sensor baixo.
- `low_dropped_while_high_active`: sensor baixo desacionado enquanto o alto segue ativo.

Esses alertas devem ser descritos como verificacoes de consistencia e rastreabilidade dos eventos. Alguns bloqueiam o processamento de ciclos de enchimento para evitar que dados inconsistentes alimentem relatorios ou AutoCloud.

## AutoCloud

No estado atual do codigo, o AutoCloud atua como uma camada de analise temporal sobre ciclos de enchimento. A funcao principal e `analyze_fill_time_cycle`, em `backend/app/services/autocloud_fill_time.py`.

Momento em que o AutoCloud atua no funcionamento real:

1. O ESP32 registra um evento em `sensores`.
2. Uma Firebase Function encaminha o evento ao backend em `/alerts/sensor-event`.
3. O backend valida o evento com regras deterministas e registra idempotencia em `sensor_event_processing`.
4. O backend atualiza ou fecha um ciclo de enchimento em `filling_cycles`.
5. Quando um ciclo valido e fechado, com `fill_time_seconds`, o backend compara seu tempo com ciclos historicos validos.
6. Se houver amostras suficientes, o AutoCloud pode gerar um alerta temporal em `alerts`.

Parametros padrao:

- `FILL_TIME_MIN_SAMPLES`: 5 ciclos historicos validos antes de usar a analise temporal.
- `FILL_TIME_SLOW_FACTOR`: 1,5 vez a mediana historica para indicar ciclo lento.
- `FILL_TIME_PERSISTENT_WINDOW`: 3 ciclos para detectar aumento progressivo.

Tipos de alerta temporal:

- `slow_fill_cycle`: ciclo atual com tempo de enchimento maior ou igual a 1,5 vez a mediana historica.
- `persistent_fill_time_shift`: aumento progressivo nos ultimos ciclos, com janela padrao de 3 ciclos.
- `new_fill_time_cluster`: ciclo acima da media historica acrescida de 3 desvios padrao.

O AutoCloud nao deve ser descrito como diagnostico definitivo. A linguagem mais adequada e: "detecta anomalias temporais e sugere possiveis causas, como reducao de vazao da bomba, obstrucao hidraulica, entrada de agua limitada ou atraso no acionamento do sensor alto".

Observacao importante: se o Firestore ainda possui apenas uma leitura antiga em uma colecao chamada `autocloud`, isso nao invalida necessariamente a implementacao atual, pois o fluxo atual nao depende dessa colecao como armazenamento principal. Para ele atuar de fato, e necessario que novos eventos reais fechem ciclos validos em `filling_cycles` e que existam ao menos 5 ciclos historicos validos para formar linha de base.

## Ciclos de enchimento, consumo de agua e energia

O backend estima consumo de agua com base em ciclos validos de enchimento. O volume padrao entre sensores e 500 L, configuravel por `RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS`. O preco padrao da agua e R$ 8,00 por metro cubico, configuravel por `WATER_PRICE_PER_CUBIC_METER_BRL`.

A energia da bomba e estimada com base em eventos de comando aplicados e confirmados. A potencia padrao e 0,75 kW, configuravel por `PUMP_POWER_KW`. O preco padrao de energia e R$ 0,656/kWh, configuravel por `ELECTRICITY_PRICE_PER_KWH_BRL`.

Esses resultados devem ser apresentados como estimativas parametrizaveis, nao como medicoes diretas por sensor de vazao ou medidor eletrico dedicado.

## Frontend e aplicativo Android

O frontend usa Ionic React, Vite, TypeScript, Firebase client SDK, MQTT.js, Recharts e Capacitor.

Telas principais:

- Dashboard/Home: estado atual do reservatorio e da bomba, leitura via Firestore e MQTT.
- Historico: filtros por periodo e abas de agua, energia e sensores, consumindo `GET /reports/summary`.
- Chat IA: interface do assistente analitico, consumindo `POST /agent`.

O app foi convertido para Android via Capacitor 7, com `appId` `br.com.aquamonitor.app`, `appName` `AquaMonitor` e `webDir` `dist`. Ha evidencias nas specs de validacao manual em dispositivo Android fisico via USB. Nao ha projeto iOS finalizado no repositorio; iOS deve ser tratado como pendencia ou possibilidade futura.

## Firebase Functions

As Functions em Node.js 22 encaminham eventos de Firestore para o backend:

- `onSensorCreated`: dispara a partir de `sensores/{docId}` e chama `/alerts/sensor-event`.
- `onCommandCreated`: dispara a partir de `comandos/{docId}` e chama `/alerts/command-event`.

O codigo inclui normalizacao de payloads, cabecalhos de autenticacao e retry. A documentacao do projeto indica que build/test locais foram validados, mas tambem registra que o deploy/emulador Firebase depende de configuracao do projeto, secrets e ambiente. Portanto, no relatorio, diferenciar "implementado e validado localmente" de "implantado em producao", caso a implantacao real nao tenha sido comprovada.

## Validacoes e numeros verificaveis

Numeros uteis para resultados quantitativos:

- 2 sensores de nivel.
- 1 bomba/rele controlado.
- 1 entrada de status da bomba.
- 1 chave fisica de acionamento.
- 3 LEDs de sinalizacao.
- 8 GPIOs principais usados no firmware final.
- 3 topicos MQTT principais.
- 6 colecoes Firestore principais/tecnicas.
- 13 endpoints HTTP principais no backend.
- 3 provedores LLM implementados: Ollama, Gemini e OpenAI.
- 7 regras deterministas de alerta para eventos de sensores.
- 3 tipos de alerta temporal associados ao AutoCloud.
- 3 periodos de relatorio/historico tratados na interface: 7, 30 e 90 dias.
- Buffer offline de 32 registros no ESP32.
- Retry de Firestore no firmware a cada 5000 ms.
- 59 testes Python encontrados no backend.
- 6 testes TypeScript encontrados nas Firebase Functions.
- 12 testes/specs encontrados no frontend.

Validacoes registradas nas specs:

- Build e testes locais do backend executados em momentos anteriores do projeto.
- Build/lint/typecheck do frontend registrados nas specs.
- Endpoints de relatorio testados localmente em periodo anterior.
- Conversao Android validada pelo usuario em dispositivo fisico.

Validacoes nao comprovadas no repositorio:

- Deploy Firebase Functions em ambiente produtivo.
- Emulador Firebase executado ponta a ponta.
- Compilacao do firmware em Arduino IDE durante a sessao documentada.
- Validacao iOS.
- Medicao real de vazao ou energia por sensores dedicados.

## Divergencias textuais a corrigir no relatorio

- Trocar "relatorio parcial", "resultados parciais" e "implementacao inicial" por linguagem de relatorio final, quando a funcionalidade estiver implementada.
- Remover frases que tratam o chatbot, o historico e os relatorios como meras propostas, pois ha implementacao em backend e frontend.
- Evitar afirmar que os dados sao mockados, exceto ao citar documentos antigos ou fases anteriores.
- Atualizar mencoes antigas a modelo `qwen2:0.5b`; o backend atual possui provedores Ollama, Gemini e OpenAI, com padrao Ollama `qwen3:4b-instruct` quando aplicavel.
- Nao dizer que o AutoCloud depende de uma colecao `autocloud` se o codigo atual usa `filling_cycles` e `alerts`.
- Corrigir a descricao de ciclos de enchimento: o inicio operacional preferencial vem de comando de bomba aplicado/confirmado, com fallback em evento de nivel baixo; o fechamento ocorre quando o sensor alto indica reservatorio cheio.
- Manter a distincao entre validacao em laboratorio e implantacao em campo.
- Descrever agua e energia como estimativas parametrizadas.
- Registrar Android como implementado/validado e iOS como pendente.

## Sugestoes de figuras e tabelas

Figuras recomendadas:

- Foto do prototipo fisico completo, mostrando reservatorio, sensores, bomba/rele, LEDs, chave fisica e case/caixa 3D.
- Diagrama da arquitetura ponta a ponta: ESP32, Firestore, Functions, FastAPI, MQTT e app.
- Tela do dashboard em operacao.
- Tela do historico com graficos de agua, energia e sensores.
- Tela do chatbot respondendo a uma pergunta sobre o sistema.
- Sequencia de um ciclo de enchimento: bomba ligada, sensor baixo, sensor alto e registro do ciclo.

Tabelas recomendadas:

- Mapeamento de pinos do ESP32.
- Rotas HTTP do backend.
- Colecoes Firestore e finalidade.
- Topicos MQTT e payloads.
- Tipos de alerta determinista e temporal.
- Parametros usados nas estimativas de agua e energia.

