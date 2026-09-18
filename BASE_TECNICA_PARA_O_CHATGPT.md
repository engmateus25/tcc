# Base tecnica para escrita do TCC - Sistema Inteligente

Este documento foi preparado para servir como base tecnica para a escrita dos topicos de **Metodologia**, **Resultados**, **Conclusoes** e **Resumo** do projeto **Sistema Inteligente**. O objetivo e fornecer ao ChatGPT responsavel pela redacao academica uma visao detalhada da arquitetura, das funcionalidades implementadas, dos contratos de integracao, dos algoritmos utilizados e dos resultados esperados/observados no desenvolvimento do sistema.

O texto deve ser usado como fonte tecnica. A redacao final do TCC deve transformar estas informacoes em linguagem academica, coesa e alinhada ao template do trabalho.

## Respostas diretas para as duvidas iniciais

- O prototipo final utiliza **duas boias/sensores de nivel**: sensor de nivel baixo (`baixo`) e sensor de nivel alto (`alto`).
- O aplicativo foi desenvolvido com **Ionic React**, **React 19**, **Vite**, **TypeScript** e componentes visuais em Radix UI/lucide-react.
- O Firebase utilizado para armazenamento e integracao e o **Cloud Firestore**, nao o Realtime Database.
- O broker MQTT configurado no projeto e o **HiveMQ publico**, usando `broker.hivemq.com`. No frontend web/mobile a conexao ocorre por WebSocket seguro (`wss://broker.hivemq.com:8884/mqtt`). No firmware ESP32 a conexao MQTT usa `broker.hivemq.com` na porta `1883`.
- O projeto possui um backend proprio implementado em **Python com FastAPI**.
- A IA do chatbot foi estruturada no backend com provedores configuraveis. Foram implementados provedores para **Ollama local**, **Gemini API** e **OpenAI**. O modelo local recomendado/configurado no backend e `qwen3:4b-instruct`; para Gemini, o modelo configurado por padrao e `gemini-3.6-flash`.
- O AutoCloud foi implementado no backend. Ele e usado como camada de analise temporal dos ciclos de enchimento, principalmente sobre a variavel `fill_time_seconds`, que representa o tempo entre o inicio confirmado do enchimento, preferencialmente bomba aplicada e confirmada como ligada, e o acionamento do sensor alto no fim do enchimento.

## Visao geral do sistema

O Sistema Inteligente de monitoramento e controle de reservatorio de agua e baseado na integracao entre hardware embarcado, aplicativo web/mobile, backend, Firebase, MQTT e inteligencia artificial. O prototipo permite acompanhar o nivel de agua do reservatorio, registrar historico de eventos, controlar uma bomba d'agua, detectar inconsistencias de sensores, estimar consumo de agua, estimar consumo eletrico da bomba, gerar relatorios e consultar informacoes por meio de um assistente de IA.

A arquitetura esta dividida em quatro dominios principais:

1. **Firmware ESP32**: faz a leitura dos sensores de nivel, controla a bomba, publica/recebe mensagens MQTT, registra eventos no Firestore e mantem um buffer local para eventos nao enviados em caso de falha de conexao.
2. **Frontend Ionic React**: fornece a interface do usuario, com dashboard operacional, historico, graficos, alertas inteligentes, controle remoto da bomba, relatorios e chatbot.
3. **Backend FastAPI**: concentra regras de negocio, processamento de eventos de sensores, geracao de relatorios, deteccao de alertas, calculos de consumo e energia, persistencia server-side no Firestore e integracao com provedores LLM.
4. **Firebase Functions**: executa uma funcao em tempo real quando um novo documento e criado na colecao `sensores`, encaminhando o evento ao backend por webhook autenticado.

Fluxo geral de dados:

```text
ESP32 -> Firestore REST -> colecao sensores
Firestore sensores -> Firebase Function -> Backend /alerts/sensor-event
Backend -> Firestore Admin -> alerts, filling_cycles, sensor_event_processing, chat_sessions
Frontend -> Firestore client SDK -> leitura realtime de sensores
Frontend -> FastAPI -> chat, agente IA, alertas, relatorios, consumo e energia
Frontend -> MQTT WebSocket -> broker HiveMQ -> ESP32
ESP32 -> MQTT bomba/estado -> Frontend
```

## Hardware e firmware

O firmware principal esta em `firmware/TCC.ino/TCC_Final/TCC_Final.ino`. Ele foi desenvolvido para ESP32 e utiliza as bibliotecas `WiFi.h`, `HTTPClient.h`, `PubSubClient.h` e `time.h`.

### Sensores utilizados

O prototipo trabalha com dois sensores de nivel:

- `SENSOR_BAIXO_PIN = 18`: sensor de nivel baixo.
- `SENSOR_ALTO_PIN = 21`: sensor de nivel alto.

A semantica usada pelo firmware e:

- Sensor `baixo` em `HIGH`: evento `desceu`, indicando que o nivel chegou ao limite inferior.
- Sensor `baixo` em `LOW`: evento `subiu`, indicando que o nivel voltou a superar o sensor baixo.
- Sensor `alto` em `HIGH`: evento `subiu`, indicando que o reservatorio atingiu o nivel superior.
- Sensor `alto` em `LOW`: evento `desceu`, indicando que o nivel deixou o sensor alto.

O firmware faz uma verificacao simples de debounce: le o pino, aguarda 15 ms e le novamente. Caso as duas leituras sejam diferentes, o evento e descartado como ruido.

### Atuacao da bomba

A bomba e acionada pelo pino:

- `BOMBA_ATIVACAO_PIN = 22`

O status da bomba e lido por:

- `BOMBA_STATUS_PIN = 23`

O firmware tenta confirmar o acionamento fisico da bomba. Ao ligar, aguarda ate 5 segundos pelo pino de status em `HIGH`. Ao desligar, verifica se o pino de status fica em `LOW`. Essa confirmacao e registrada no Firestore e publicada por MQTT.

### LEDs de indicacao

O prototipo possui tres LEDs:

- `LED_BAIXO_PIN = 32`
- `LED_MEDIO_PIN = 19`
- `LED_ALTO_PIN = 33`

Eles indicam condicoes relacionadas aos sensores baixo, medio/intervalo e alto.

### Prioridade de acionamento

O controle da bomba foi implementado com sobreposicao de prioridades:

```text
acionamento fisico > comando remoto MQTT > controle automatico
```

O acionamento fisico e lido pelo pino:

- `ACIONAMENTO_FISICO_PIN = 25`

Regras principais:

- Se a chave fisica estiver ativa, a bomba e forçada ligada.
- Se houver comando remoto e a chave fisica nao estiver ativa, o comando remoto prevalece.
- Se nao houver chave fisica ativa nem comando remoto, prevalece a logica automatica baseada nos sensores.
- O controle automatico liga a bomba quando `baixo desceu`.
- O controle automatico desliga a bomba quando `alto subiu`.

Quando um comando nao e obedecido por causa de uma prioridade superior, o firmware registra esse fato na colecao `comandos` e publica o estado no topico `bomba/estado`. Assim, o sistema diferencia o comando solicitado do comando realmente aplicado.

### Auditoria dos comandos da bomba

Na colecao `comandos`, o firmware registra informacoes detalhadas:

- `bomba`: mensagem textual do comando.
- `acionamento`: origem logica do comando (`fisico`, `remoto`, `automatico`).
- `source`: origem do comando.
- `command_id`: identificador unico do comando.
- `event_id`: identificador do evento na colecao.
- `device_id`: identificador do ESP32, por padrao `esp32-reservatorio-01`.
- `requested_state`: estado solicitado para a bomba.
- `applied_state`: estado efetivamente aplicado.
- `applied`: indica se o comando foi aplicado.
- `confirmed`: indica se o estado foi confirmado fisicamente.
- `state_changed`: indica se houve mudanca real de estado.
- `priority`: prioridade que prevaleceu.
- `overridden_by`: prioridade que sobrepos o comando, quando aplicavel.
- `reason`: motivo do registro.
- `timestamp`, `created_at_device`, `sent_at`: horarios em UTC.

Essa estrutura foi importante para calcular corretamente o consumo eletrico, pois apenas eventos aplicados e confirmados entram no calculo do tempo ligado da bomba.

### MQTT no firmware

O firmware assina dois topicos de controle:

```text
bomba/controle
bomba/controle/v2
```

O topico legado `bomba/controle` aceita mensagens de texto:

```text
bomba ligar
bomba desligar
```

O topico versionado `bomba/controle/v2` aceita JSON:

```json
{
  "schema_version": 1,
  "command_id": "web-123",
  "command": "ligar",
  "desired_on": true,
  "source": "frontend",
  "timestamp": "2026-07-28T12:00:00Z"
}
```

O firmware publica confirmacoes em:

```text
bomba/estado
```

Exemplo de payload publicado:

```json
{
  "schema_version": 1,
  "pump_on": true,
  "mode": "remoto",
  "confirmed": true,
  "applied": true,
  "source": "remoto",
  "priority": "remoto",
  "overridden_by": "",
  "command_id": "web-123",
  "reason": "mqtt ligar",
  "timestamp": "2026-07-28T12:00:01Z"
}
```

### Registro de sensores no Firestore

Cada mudanca de sensor gera um documento na colecao `sensores` via Firestore REST API. O payload contem:

- `sensor`: `baixo` ou `alto`.
- `estado`: `subiu` ou `desceu`.
- `event_id`: identificador unico do evento.
- `device_id`: identificador do dispositivo.
- `source`: `firmware`.
- `timestamp`: horario UTC do evento.
- `created_at_device`: horario UTC no dispositivo.
- `sent_at`: horario UTC do envio.

### Sincronizacao de horario

O firmware sincroniza horario por NTP usando `pool.ntp.org` e `time.nist.gov`, mantendo timestamps em UTC no formato ISO 8601. Antes de iniciar a operacao, o firmware aguarda ate que o epoch indique uma data valida.

### Buffer offline

Foi implementado um buffer circular para evitar perda de eventos quando o ESP32 nao consegue enviar dados ao Firestore. As configuracoes principais sao:

- `OFFLINE_BUFFER_CAPACITY = 32`
- `FIRESTORE_RETRY_INTERVAL_MS = 5000`

Quando um envio falha por ausencia de Wi-Fi ou erro HTTP, o evento e colocado em fila. Quando a conexao retorna, a funcao `flushFirestoreBuffer()` tenta reenviar os eventos em ordem. Se o buffer fica cheio, o evento mais antigo e descartado, preservando os eventos mais recentes e evitando crescimento ilimitado de memoria.

## Firebase Functions

A pasta `functions/` contem uma Function em TypeScript usando Firebase Functions v2 e runtime Node.js 22.

Funcao principal:

```text
onSensorCreated
```

Ela e acionada quando um novo documento e criado em:

```text
sensores/{docId}
```

O fluxo e:

1. Firestore cria um documento novo na colecao `sensores`.
2. A Function recebe o snapshot do documento.
3. A Function normaliza o payload com `document_id`, `event_id`, `sensor`, `estado`, `timestamp`, `device_id`, `source`, `raw_path` e `received_at`.
4. A Function envia uma requisicao `POST` para o backend no endpoint configurado por `BACKEND_SENSOR_EVENT_URL`.
5. Quando configurado, a Function envia o segredo compartilhado no header `X-AquaMonitor-Webhook-Secret`.
6. Se o backend responde erro, a Function registra log e lança excecao, permitindo retentativa automatica.

Configuracoes relevantes:

- `BACKEND_SENSOR_EVENT_URL`: URL do endpoint do backend.
- `FUNCTION_REGION`: regiao da Function, com padrao `us-central1`.
- `SENSOR_EVENT_WEBHOOK_SECRET`: segredo compartilhado com o backend.
- `SENSOR_DOCUMENT_PATH = sensores/{docId}`.

O projeto `firebase.json` configura:

- `functions.source = functions`
- `runtime = nodejs22`
- predeploy com build TypeScript
- emuladores de Functions, Firestore e UI

## Backend FastAPI

O backend fica em `backend/` e usa FastAPI. O ponto de entrada e:

```text
backend/app/main.py
```

O app FastAPI e registrado como:

```text
AquaMonitor AI Backend
```

Ele usa CORS para permitir acesso do frontend local, Ionic e IPs de rede. As origens podem ser configuradas por `CORS_ORIGINS`.

Rotas principais:

- `GET /health`
- `POST /llm/chat`
- `POST /llm/chat/stream`
- `GET /llm/sessions/{session_id}`
- `POST /agent`
- `GET /reports/summary?period=7d`
- `GET /reports/weekly?period=7d`
- `GET /reports/monthly`
- `GET /alerts/sensors`
- `GET /alerts?period=7d&status=open&limit=20`
- `PATCH /alerts/{alert_id}/ack`
- `POST /alerts/sensor-event`

### Integracao com Firebase Admin

O backend acessa o Firestore por Firebase Admin. A inicializacao aceita:

- `GOOGLE_APPLICATION_CREDENTIALS`: caminho do arquivo de credenciais.
- `FIREBASE_CREDENTIALS_JSON`: credencial em JSON via variavel de ambiente.
- Application Default Credentials, se disponivel.

As operacoes usam timeout configuravel:

```text
FIRESTORE_OPERATION_TIMEOUT_SECONDS
```

Isso evita que erros de credencial ou indisponibilidade do Firestore prendam as rotas por muito tempo. Em falhas de dependencia, as rotas retornam `503`.

### Colecoes Firestore usadas pelo backend

- `sensores`: eventos dos sensores de nivel.
- `comandos`: comandos e estados da bomba.
- `alerts`: alertas inteligentes persistidos.
- `sensor_event_processing`: controle de idempotencia do processamento de eventos.
- `filling_cycles`: ciclos validos de enchimento.
- `chat_sessions`: sessoes do chatbot e do agente IA.

Os nomes de algumas colecoes podem ser alterados por variaveis de ambiente:

- `FIRESTORE_SENSORS_COLLECTION`
- `FIRESTORE_COMMANDS_COLLECTION`
- `FIRESTORE_ALERTS_COLLECTION`
- `FIRESTORE_SENSOR_EVENT_PROCESSING_COLLECTION`
- `FIRESTORE_FILLING_CYCLES_COLLECTION`

## Processamento automatico de eventos de sensor

O endpoint central do processamento em tempo real e:

```text
POST /alerts/sensor-event
```

Esse endpoint recebe eventos vindos da Firebase Function ou payload legado. O schema aceita:

- `sensor`: `baixo` ou `alto`.
- `estado`: `subiu` ou `desceu`.
- `timestamp`: data/hora do evento.
- `device_id`: opcional.
- `document_id`: opcional.
- `event_id`: opcional.
- `source`: origem do evento.
- `raw_path`: caminho do documento no Firestore.
- `received_at`: horario de recebimento.

O schema normaliza texto para minusculo, remove espacos extras, converte timestamps para UTC e marca `timestamp_missing` quando o evento chega sem timestamp confiavel.

Quando `SENSOR_EVENT_WEBHOOK_SECRET` esta definido no backend, o endpoint exige o header:

```text
X-AquaMonitor-Webhook-Secret
```

O processamento segue esta ordem:

1. Reserva idempotente do evento em `sensor_event_processing`.
2. Se o evento ja foi processado, retorna como duplicado sem reprocessar regras nem AutoCloud.
3. Busca historico recente anterior ao evento.
4. Aplica regras deterministicas de consistencia fisica.
5. Persiste alertas deduplicados em `alerts`.
6. Se nao houver alerta bloqueante, tenta montar ciclo de enchimento.
7. Persiste ciclo valido em `filling_cycles`.
8. Executa analise temporal do tempo de enchimento.
9. Se houver anomalia temporal, persiste alerta AutoCloud.
10. Marca o processamento como `processed` ou `failed`.

Resposta do endpoint:

```json
{
  "processed": true,
  "duplicate": false,
  "event_id": "sensores/doc-1",
  "processing_key": "hash",
  "processing_status": "processed",
  "payload_hash_mismatch": false,
  "alerts_created": [],
  "cycle_created": null,
  "autocloud": {}
}
```

## Idempotencia

A idempotencia e feita pela colecao `sensor_event_processing`. O backend cria uma chave estavel a partir de:

1. `event_id`, se existir.
2. `raw_path`, se existir.
3. `document_id`, se existir.
4. hash do payload legado.

O `processing_key` e o SHA-256 do `event_id` final. Ao tentar criar um documento com a mesma chave, o Firestore retorna conflito. Nesse caso, o backend reconhece o evento como duplicado e nao executa novamente as regras ou a criacao de alertas/ciclos.

Tambem e calculado um hash do payload para detectar quando um mesmo `event_id` aparece com conteudo diferente, preenchendo `payload_hash_mismatch`.

## Regras logicas de consistencia dos sensores

A deteccao deterministica usa `backend/app/services/sensor_rules.py`. Ela representa a camada de regras fisicas do sistema, independente de IA.

Configuracoes:

- `SENSOR_DUPLICATE_WINDOW_SECONDS`: janela para detectar evento duplicado. Padrao: 5 segundos.
- `SENSOR_OUT_OF_ORDER_TOLERANCE_SECONDS`: tolerancia para eventos fora de ordem. Padrao: 2 segundos.
- `MIN_PLAUSIBLE_DRAIN_TIME_SECONDS`: tempo minimo fisicamente plausivel para esvaziamento do sensor alto ate o baixo. Padrao: 60 segundos.

Alertas gerados:

- `missing_timestamp`: evento sem timestamp confiavel. Bloqueia ciclo e AutoCloud.
- `out_of_order_event`: evento com timestamp anterior ao ultimo processado alem da tolerancia.
- `duplicate_event`: mesmo sensor e mesmo estado repetidos dentro da janela de duplicidade.
- `unexpected_low_repeat`: sensor baixo repetiu `desceu` antes de um fechamento de ciclo pelo sensor alto.
- `implausible_drain_time`: tempo entre `alto subiu` e `baixo desceu` abaixo do minimo plausivel.
- `unexpected_high_without_low`: sensor alto subiu sem que o sensor baixo estivesse em estado coerente.
- `low_dropped_while_high_active`: sensor baixo desceu enquanto o sensor alto ainda estava ativo.

Cada alerta possui:

- `event_id`
- `type`
- `severity`
- `title`
- `message`
- `sensor_timestamp`
- `possible_causes`
- `metadata`

Os alertas que contem `metadata.blocks_cycle_processing = true` impedem que o evento alimente ciclos e AutoCloud. Isso evita que dados inconsistentes contaminem a analise temporal.

## Ciclos de enchimento

Os ciclos validos sao extraidos em `backend/app/services/filling_cycles.py`.

O inicio preferencial do ciclo e:

```text
bomba aplicada e confirmada como ligada
```

Quando nao houver confirmacao confiavel da bomba, o backend usa como fallback:

```text
sensor baixo desceu
```

O fim do ciclo e:

```text
sensor alto subiu
```

O tempo de enchimento e calculado como:

```text
fill_time_seconds = ended_at - started_at
```

O ciclo e descartado se:

- nao houver timestamp valido;
- o fim ocorrer antes do inicio;
- algum evento do ciclo tiver sido bloqueado por regra deterministica.

Cada ciclo persistido contem:

- `cycle_id`: SHA-256 de `start_event_id:end_event_id`.
- `start_event_id`
- `end_event_id`
- `started_at`
- `ended_at`
- `pump_started_at`
- `fill_time_seconds`
- `valid`
- `device_id`
- `start_source`
- `start_event_type`
- `pump_mode`
- `discard_reason`
- `metadata`

## AutoCloud e analise temporal do enchimento

O projeto possui duas camadas relacionadas ao AutoCloud:

1. Uma implementacao base em `autocloud_core.py`, com a estrutura de nuvens de dados.
2. Uma camada aplicada ao dominio em `autocloud_fill_time.py`, focada na analise temporal do tempo de enchimento da caixa.

Na aplicacao final, o elemento principal analisado e `fill_time_seconds`. A logica compara cada ciclo novo com o historico de ciclos validos.

Configuracoes:

- `FILL_TIME_MIN_SAMPLES`: numero minimo de amostras historicas. Padrao: 5.
- `FILL_TIME_SLOW_FACTOR`: fator para considerar um ciclo lento. Padrao: 1.5.
- `FILL_TIME_PERSISTENT_WINDOW`: janela para detectar aumento persistente. Padrao: 3.

Resultados possiveis:

- `insufficient_data`: ainda nao ha amostras suficientes.
- `normal_fill_time`: ciclo dentro do comportamento esperado.
- `slow_fill_cycle`: ciclo atual muito mais lento que a mediana historica.
- `persistent_fill_time_shift`: aumento progressivo do tempo de enchimento nos ultimos ciclos.
- `new_fill_time_cluster`: ciclo muito distante do comportamento medio, usando media e desvio padrao como referencia.

Os alertas AutoCloud indicam possiveis causas, mas nao afirmam diagnostico definitivo. Exemplos de causas apresentadas:

- bomba com baixa vazao;
- obstrucao hidraulica;
- entrada de agua limitada;
- sensor alto demorando a acionar.

## Persistencia e consulta de alertas

Os alertas sao persistidos na colecao `alerts`. O ID do alerta e estavel, gerado por SHA-256 de:

```text
event_id:type
```

Isso evita criar alertas repetidos para o mesmo evento e mesmo tipo de anomalia.

Campos principais:

- `id`
- `event_id`
- `type`
- `severity`
- `title`
- `message`
- `detected_at`
- `sensor_timestamp`
- `status`
- `possible_causes`
- `metadata`
- `acknowledged`
- `acknowledged_at`

Rotas:

- `GET /alerts`: lista alertas persistidos por periodo, status, severidade e limite.
- `PATCH /alerts/{alert_id}/ack`: reconhece um alerta, alterando `status` para `acknowledged`.
- `GET /alerts/sensors`: executa analise retrospectiva de eventos de sensores no periodo.

## Estimativa de consumo de agua

O consumo de agua e estimado a partir dos ciclos validos de enchimento.

Configuracoes:

- `RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS`: volume estimado entre o sensor baixo e o sensor alto. Padrao: 500 L.
- `WATER_PRICE_PER_CUBIC_METER_BRL`: preco da agua por metro cubico. Padrao: R$ 8,00/m3.

Calculo:

```text
total_liters = cycle_count * volume_between_sensors_liters
total_cubic_meters = total_liters / 1000
total_cost_brl = total_cubic_meters * water_price_per_cubic_meter_brl
average_liters_per_day = total_liters / dias_do_periodo
```

O resumo retorna:

- periodo;
- quantidade de ciclos validos;
- volume por ciclo;
- litros totais;
- metros cubicos totais;
- custo estimado;
- media diaria;
- serie diaria.

Essa estimativa usa uma aproximacao por ciclo entre os sensores. Ela e adequada para o prototipo porque o sistema mede eventos discretos de nivel, nao vazao continua.

## Estimativa de consumo eletrico da bomba

O consumo eletrico e calculado a partir dos comandos confirmados da bomba na colecao `comandos`.

Configuracoes:

- `PUMP_POWER_KW`: potencia nominal da bomba. Padrao: 0,75 kW.
- `ELECTRICITY_PRICE_PER_KWH_BRL`: preco da energia por kWh. Padrao: R$ 0,656/kWh.

O backend considera apenas eventos:

- `confirmed = true`
- `applied = true`
- `pump_on` ou `applied_state` booleano valido

Comandos nao aplicados, sobrepostos por prioridade ou sem confirmacao sao ignorados no tempo ligado, mas permanecem registrados para auditoria.

Calculo:

```text
tempo_ligado_horas = total_on_seconds / 3600
energia_kwh = PUMP_POWER_KW * tempo_ligado_horas
custo_brl = energia_kwh * ELECTRICITY_PRICE_PER_KWH_BRL
```

O resumo retorna:

- tempo ligado em segundos, minutos e horas;
- energia em kWh;
- custo estimado;
- quantidade de eventos confirmados;
- quantidade de comandos ignorados;
- intervalos de funcionamento;
- serie diaria de energia e custo.

## Relatorios

O backend gera relatorios PDF com ReportLab.

Rotas:

- `GET /reports/summary?period=7d`
- `GET /reports/weekly?period=7d`
- `GET /reports/monthly`

Periodos aceitos para resumo e PDF:

- `7d`
- `30d`
- `90d`

O payload do resumo inclui:

- resumo dos sensores;
- consumo estimado de agua;
- energia estimada da bomba;
- alertas recentes.

O PDF inclui:

- titulo: `AquaMonitor - Relatorio Operacional`;
- periodo analisado;
- data de geracao;
- total de eventos de sensores;
- eventos por sensor;
- eventos por acao;
- consumo estimado de agua;
- energia estimada da bomba;
- alertas recentes;
- observacoes metodologicas sobre estimativas.

Os arquivos sao gerados em `backend/generated` ou no diretorio configurado por `PDF_OUTPUT_DIR`.

## Chatbot e agente de IA

O projeto possui duas rotas relacionadas a IA:

```text
POST /llm/chat
POST /agent
```

A rota `/llm/chat` e um chat generico com historico de mensagens no formato:

```json
[
  {"role": "user", "content": "pergunta"}
]
```

A rota `/agent` e o agente analitico do Sistema Inteligente. Ela recebe:

```json
{
  "question": "Quantas vezes a caixa ficou vazia nos ultimos 7 dias?",
  "session_id": "opcional",
  "provider": "opcional"
}
```

O agente executa uma arquitetura hibrida:

1. Detecta a intencao da pergunta.
2. Extrai o periodo solicitado.
3. Consulta dados estruturados no Firestore e nos servicos do backend.
4. Monta um contexto tecnico com eventos, consumo, energia e alertas.
5. Gera uma resposta deterministica de referencia.
6. Envia contexto e resposta-base ao provedor LLM configurado.
7. Caso o LLM falhe e o modo permita, retorna fallback deterministico explicitamente identificado.

Intencoes reconhecidas:

- resumo geral;
- contagem de eventos;
- quantidade de vezes que a caixa ficou vazia;
- quantidade de vezes que a caixa ficou cheia;
- duracao em estado vazio;
- duracao em estado cheio;
- consumo de agua;
- consumo de energia;
- resumo de alertas;
- verificacao de consistencia dos sensores;
- smalltalk;
- desconhecido.

Periodos reconhecidos:

- `hoje`
- ultimas horas;
- ultimos X dias;
- semana atual;
- mes atual;
- 7, 20, 30 e 90 dias.

### Provedores LLM

O backend usa a abstracao `LLMProvider`, com provedores:

- `OllamaProvider`
- `GeminiProvider`
- `OpenAIProvider`

Variaveis:

- `LLM_PROVIDER`
- `LLM_TEMPERATURE`
- `LLM_MAX_TOKENS`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_BASE_URL`
- `GEMINI_TIMEOUT_SECONDS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AGENT_RESPONSE_MODE`
- `AGENT_ALLOW_DETERMINISTIC_FALLBACK`
- `AGENT_SEND_RAW_EVENTS_TO_LLM`
- `AGENT_MAX_HISTORY_MESSAGES`

Padroes importantes:

- Ollama: `qwen3:4b-instruct`
- Gemini: `gemini-3.6-flash`
- OpenAI: `gpt-4o-mini`

O prompt de sistema do agente instrui o modelo a responder em portugues do Brasil, usar somente os dados estruturados fornecidos e nao inventar contagens, custos, tempos, alertas ou estados de bomba. Por seguranca, o envio de eventos brutos ao LLM e desabilitado por padrao, sendo enviado apenas contexto agregado.

### Sessoes de chat

As sessoes sao salvas na colecao `chat_sessions`. Cada sessao possui subcolecao `messages`, com:

- `role`
- `content`
- `ts`

O frontend armazena `session_id` durante a conversa, permitindo continuidade logica do chat.

## Frontend Ionic React

O frontend fica em `frontend/` e foi desenvolvido com:

- Ionic React;
- React 19;
- Vite;
- TypeScript;
- Firebase Web SDK;
- MQTT.js;
- Recharts;
- Radix UI;
- lucide-react;
- motion/react;
- Capacitor.

Rotas:

- `/home`
- `/history`
- `/chat`

### Layout principal

O layout comum apresenta:

- cabecalho com nome AquaMonitor;
- conteudo rolavel;
- ajuda flutuante;
- rodape fixo com status de conexao Firebase e MQTT.

### Home

A Home e a tela operacional principal. Ela exibe:

- alerta visual do nivel do reservatorio;
- painel de alertas inteligentes;
- estatisticas rapidas;
- visualizacao grafica do tanque;
- status do ultimo sensor;
- controle da bomba;
- modo de acionamento;
- estimativa de energia;
- atalhos para historico e assistente IA.

O nivel de agua exibido e estimado a partir do ultimo evento de sensor:

- `baixo desceu` -> aproximadamente 15%;
- `baixo subiu` -> aproximadamente 55%;
- `alto desceu` -> aproximadamente 62%;
- `alto subiu` -> aproximadamente 96%.

### Controle da bomba na interface

O componente de controle da bomba envia comando MQTT e aguarda confirmacao. Enquanto o comando esta pendente, o botao fica bloqueado. A interface mostra mensagens como:

- aguardando confirmacao da bomba;
- MQTT desconectado;
- estado confirmado pela bomba;
- comando sobreposto por prioridade;
- comando aplicado sem confirmacao fisica.

### Alertas inteligentes na interface

O painel de alertas consulta o backend periodicamente por meio de `useAlerts`. Padroes:

- periodo: `7d`;
- status: `open`;
- limite: 20;
- atualizacao: a cada 15 segundos.

O usuario pode:

- atualizar manualmente;
- visualizar severidade, tipo, mensagem e possiveis causas;
- reconhecer um alerta, chamando `PATCH /alerts/{id}/ack`.

Tipos traduzidos na interface:

- duplicidade;
- sequencia;
- esvaziamento;
- ordem;
- timestamp;
- enchimento lento;
- tendencia;
- novo padrao.

### Historico e estatisticas

A tela de historico permite selecionar periodos de 7, 30 ou 90 dias. Ela busca `GET /reports/summary` e apresenta:

- consumo estimado de agua;
- custo de energia;
- grafico de consumo de agua em litros;
- grafico de energia em kWh e custo;
- grafico de eventos por sensor;
- insights sobre volume por ciclo, comandos sobrepostos e eventos confirmados;
- botao para baixar PDF.

O download chama:

```text
GET /reports/weekly?period=7d|30d|90d
```

O frontend interpreta o header `content-disposition` para definir o nome do arquivo; se nao houver nome, usa `relatorio_<periodo>.pdf`.

### Chat IA

A tela do chat possui:

- perguntas rapidas;
- envio por botao ou tecla Enter;
- campo de texto autoajustavel;
- indicador de digitacao/analise;
- bolhas diferenciadas para usuario e assistente;
- metadados de provedor/modelo na resposta;
- exibicao de fallback deterministico quando usado;
- botao para limpar a conversa.

Perguntas rapidas implementadas:

- resumo dos eventos dos sensores nesta semana;
- quantas vezes a caixa ficou vazia nos ultimos 20 dias;
- quantas vezes a caixa ficou cheia nesse mes;
- quanto tempo a caixa ficou vazia neste mes.

## Android com Capacitor

O projeto possui plataforma Android em `frontend/android/`.

Configuracao Capacitor:

```text
appId = br.com.aquamonitor.app
appName = AquaMonitor
webDir = dist
```

Scripts:

```text
npm run cap:sync
npm run android:sync
npm run android:open
```

O AndroidManifest inclui:

- permissao de internet;
- `android:usesCleartextTraffic="true"` para permitir chamadas HTTP locais durante testes com backend na rede local.

Para uso em celular, a variavel `VITE_AI_BASE_URL` deve apontar para o IP do computador que executa o backend, por exemplo:

```text
http://192.168.1.20:8000
```

O backend deve ser executado com:

```text
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Variaveis de ambiente principais

Backend:

- `CORS_ORIGINS`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `FIREBASE_CREDENTIALS_JSON`
- `FIRESTORE_SENSORS_COLLECTION`
- `FIRESTORE_COMMANDS_COLLECTION`
- `FIRESTORE_ALERTS_COLLECTION`
- `FIRESTORE_SENSOR_EVENT_PROCESSING_COLLECTION`
- `FIRESTORE_FILLING_CYCLES_COLLECTION`
- `FIRESTORE_OPERATION_TIMEOUT_SECONDS`
- `RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS`
- `WATER_PRICE_PER_CUBIC_METER_BRL`
- `PUMP_POWER_KW`
- `ELECTRICITY_PRICE_PER_KWH_BRL`
- `SENSOR_DUPLICATE_WINDOW_SECONDS`
- `SENSOR_OUT_OF_ORDER_TOLERANCE_SECONDS`
- `MIN_PLAUSIBLE_DRAIN_TIME_SECONDS`
- `FILL_TIME_MIN_SAMPLES`
- `FILL_TIME_SLOW_FACTOR`
- `FILL_TIME_PERSISTENT_WINDOW`
- `SENSOR_EVENT_WEBHOOK_SECRET`
- `LLM_PROVIDER`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENAI_API_KEY`
- `ENABLE_SCHEDULER`
- `PDF_OUTPUT_DIR`

Frontend:

- `VITE_AI_BASE_URL`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_DATABASE_URL`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MEASUREMENT_ID`
- `VITE_MQTT_URL`
- `VITE_MQTT_CLIENT_PREFIX`
- `VITE_MQTT_USERNAME`
- `VITE_MQTT_PASSWORD`
- `VITE_MQTT_CONTROL_TOPIC`
- `VITE_MQTT_CONTROL_V2_TOPIC`
- `VITE_MQTT_STATE_TOPIC`
- `VITE_MQTT_PUBLISH_LEGACY_CONTROL`

Firmware:

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `MQTT_BROKER_HOST`
- `MQTT_BROKER_PORT`
- `MQTT_CONTROL_TOPIC_VALUE`
- `MQTT_CONTROL_V2_TOPIC_VALUE`
- `MQTT_STATE_TOPIC_VALUE`
- `FIREBASE_SENSORES_COLLECTION_URL`
- `FIREBASE_COMANDOS_COLLECTION_URL`
- `FIREBASE_WEB_API_KEY`
- `DEVICE_ID`
- `OFFLINE_BUFFER_CAPACITY`
- `FIRESTORE_RETRY_INTERVAL_MS`

## Testes e validacoes implementados

O backend possui testes automatizados com pytest. Eles cobrem:

- normalizacao de payload legado de sensores;
- rejeicao de sensor invalido;
- preferencia de identidade por `raw_path` e `document_id`;
- autenticacao do webhook por segredo;
- rejeicao de segredo ausente ou incorreto;
- aceitacao de segredo correto;
- idempotencia de evento duplicado;
- rotas de alertas;
- retorno `503` quando Firestore esta indisponivel;
- regras de duplicidade;
- repeticao do sensor baixo antes do sensor alto;
- tempo de esvaziamento implausivel;
- evento fora de ordem;
- sensor alto subindo sem baixo coerente;
- timestamp ausente bloqueando ciclo;
- extracao de ciclos por bomba confirmada ou fallback baixo -> alto;
- bloqueio de eventos invalidos no ciclo;
- rejeicao de ciclo com duracao nao positiva;
- AutoCloud com dados insuficientes;
- alerta de ciclo lento;
- alerta de aumento persistente;
- calculo de consumo de agua;
- calculo de energia com eventos aplicados e confirmados;
- leitura do contrato estendido de comandos;
- provedores LLM Ollama/Gemini/OpenAI;
- fallback deterministico do agente;
- metadados de provedor/modelo no endpoint do agente;
- endpoint generico de chat.

As Functions possuem testes Node.js para:

- conversao de documento Firestore em payload do backend;
- preservacao de `event_id` explicito;
- normalizacao de timestamp Firestore por `toDate`;
- normalizacao por `seconds/nanoseconds`;
- fallback quando timestamp esta ausente;
- envio do header secreto apenas quando configurado.

O frontend possui teste Cypress basico para carregamento da aplicacao e da tela inicial.

Comandos de validacao usados no desenvolvimento:

```text
cd backend
pytest
python -m compileall app tests
```

```text
cd functions
npm run build
npm test
```

```text
cd frontend
npm run build
npm run lint
npm run android:sync
npx cap doctor android
```

## Pontos para metodologia

Sugestao de abordagem para escrever a Metodologia:

1. Apresentar o sistema como uma arquitetura integrada de IoT, aplicacao mobile/web e backend.
2. Explicar a divisao em camadas: firmware, comunicacao, armazenamento, processamento backend, frontend e IA.
3. Descrever o hardware: ESP32, duas boias, rele/acionamento da bomba, LEDs e pino de status.
4. Explicar a logica de leitura dos sensores e o contrato `sensor`/`estado`.
5. Descrever a comunicacao:
   - Firestore REST para persistencia de eventos no firmware;
   - MQTT para controle e confirmacao de estado da bomba;
   - Firebase Functions para disparo automatico do backend;
   - API FastAPI para regras, alertas, relatorios e IA.
6. Explicar a prioridade de acionamento da bomba e a diferenca entre comando solicitado e comando aplicado.
7. Descrever o mecanismo de idempotencia para evitar processamento duplicado.
8. Explicar as regras deterministicas de consistencia fisica.
9. Explicar a extracao de ciclos de enchimento.
10. Explicar o uso do AutoCloud/analise temporal para detectar anomalias no tempo de enchimento.
11. Descrever os calculos de agua e energia como estimativas baseadas em parametros configuraveis.
12. Descrever a implementacao do chatbot com dados estruturados e LLM configuravel.
13. Descrever os testes automatizados usados para validacao.

## Pontos para resultados

Sugestao de resultados a relatar:

- O sistema registrou eventos dos sensores em Firestore com timestamps em UTC e identificadores unicos.
- A Function automatizou o fluxo de processamento, reduzindo dependencia de verificacao manual.
- O backend processou eventos novos com idempotencia, evitando alertas duplicados.
- As regras deterministicas identificaram inconsistencias coerentes com o funcionamento fisico da caixa.
- Ciclos validos de enchimento foram extraidos e persistidos.
- A analise temporal detectou tempos de enchimento fora do padrao historico.
- Os alertas foram exibidos no aplicativo com severidade, causa provavel e opcao de reconhecimento.
- O controle remoto da bomba funcionou por MQTT, com confirmacao de estado e auditoria de comandos sobrepostos.
- A estimativa de consumo de agua foi obtida pela quantidade de ciclos entre os sensores.
- A estimativa de energia foi obtida pelo tempo confirmado de funcionamento da bomba.
- Os relatorios PDF reuniram sensores, consumo, energia e alertas.
- O chatbot permitiu consultar dados do sistema por linguagem natural, usando contexto estruturado para evitar respostas inventadas.
- O aplicativo foi preparado para execucao Android com Capacitor.

## Pontos para conclusoes

Sugestao de conclusoes tecnicas:

- A arquitetura modular facilitou a separacao entre captura fisica, comunicacao, armazenamento, processamento e visualizacao.
- O uso conjunto de Firestore e MQTT permitiu separar historico persistente de comandos em tempo quase real.
- A combinacao de regras deterministicas e analise temporal tornou a deteccao de anomalias mais adequada ao dominio fisico do reservatorio.
- A persistencia de alertas e ciclos permitiu transformar eventos simples de boias em informacao operacional.
- O registro de comandos com campos de prioridade e confirmacao evitou interpretar comandos sobrepostos como funcionamento real da bomba.
- O chatbot agregou uma camada de interpretacao em linguagem natural sem retirar do backend a responsabilidade pelos dados numericos.
- O prototipo demonstrou viabilidade para monitoramento residencial/experimental de reservatorios, podendo ser expandido com sensores de vazao, medicao eletrica real, notificacoes push e hospedagem HTTPS.

## Base para um resumo academico

O Sistema Inteligente consiste em um sistema embarcado e computacional para monitoramento e controle de reservatorio de agua, integrando ESP32, sensores de nivel, bomba, Firebase, MQTT, backend FastAPI, aplicativo Ionic React e recursos de inteligencia artificial. O firmware realiza a leitura de duas boias de nivel, aciona a bomba conforme uma politica de prioridade entre comando fisico, remoto e automatico, registra eventos no Firestore e utiliza buffer local para reduzir perdas durante falhas de conectividade. Uma Firebase Function e acionada automaticamente a cada novo evento de sensor e encaminha os dados ao backend, onde sao aplicadas regras deterministicas de consistencia, idempotencia, extracao de ciclos de enchimento e analise temporal do tempo de enchimento. O aplicativo apresenta dashboard, historico, graficos, controle remoto, alertas inteligentes, relatorios PDF e chatbot analitico. Os resultados demonstram a integracao entre hardware e software, a deteccao de eventos incoerentes, a estimativa de consumo de agua e energia e a possibilidade de consulta dos dados por linguagem natural. Assim, o sistema evidencia a viabilidade de uma solucao IoT de baixo custo para acompanhamento operacional de reservatorios, com potencial de expansao para notificacoes, hospedagem em nuvem e novas metricas fisicas.

## Sugestoes de figuras e tabelas para o TCC

Figuras recomendadas:

- Diagrama geral da arquitetura: ESP32, Firestore, Function, backend, frontend e MQTT.
- Foto do prototipo com ESP32, sensores e bomba/rele.
- Fluxograma do processamento de evento de sensor.
- Diagrama da prioridade de acionamento: fisico > remoto > automatico.
- Print da tela Home com reservatorio e alertas.
- Print da tela Historico com graficos.
- Print da tela Chat IA com pergunta analitica.
- Exemplo de relatorio PDF gerado.
- Diagrama das colecoes Firestore.
- Fluxo de ciclo de enchimento: `bomba confirmada ligada -> alto subiu`, com fallback `baixo desceu -> alto subiu`.

Tabelas recomendadas:

- Tabela de pinos do ESP32.
- Tabela de topicos MQTT.
- Tabela de colecoes Firestore.
- Tabela de endpoints do backend.
- Tabela de variaveis de ambiente.
- Tabela de tipos de alertas.
- Tabela de testes automatizados.
- Tabela de parametros configuraveis de consumo, energia e anomalias.

## Tabela de endpoints para usar no texto

| Endpoint | Metodo | Funcao |
| --- | --- | --- |
| `/health` | GET | Verifica disponibilidade da API |
| `/alerts/sensor-event` | POST | Processa novo evento de sensor vindo da Function |
| `/alerts/sensors` | GET | Executa analise retrospectiva de sensores |
| `/alerts` | GET | Lista alertas persistidos |
| `/alerts/{alert_id}/ack` | PATCH | Reconhece alerta |
| `/reports/summary` | GET | Retorna resumo JSON de sensores, agua, energia e alertas |
| `/reports/weekly` | GET | Gera/retorna PDF de relatorio por periodo |
| `/reports/monthly` | GET | Gera/retorna PDF mensal |
| `/llm/chat` | POST | Chat generico com provedor LLM |
| `/llm/chat/stream` | POST | Chat generico em streaming NDJSON |
| `/llm/sessions/{session_id}` | GET | Retorna historico de uma sessao |
| `/agent` | POST | Agente analitico com contexto estruturado do Sistema Inteligente |

## Tabela de colecoes Firestore

| Colecao | Finalidade |
| --- | --- |
| `sensores` | Eventos de nivel gerados pelo ESP32 |
| `comandos` | Auditoria de comandos e estados da bomba |
| `alerts` | Alertas inteligentes persistidos |
| `sensor_event_processing` | Controle de idempotencia |
| `filling_cycles` | Ciclos validos de enchimento |
| `chat_sessions` | Sessoes e mensagens do chatbot |

## Tabela de topicos MQTT

| Topico | Direcao | Funcao |
| --- | --- | --- |
| `bomba/controle` | Frontend -> ESP32 | Comando legado em texto |
| `bomba/controle/v2` | Frontend -> ESP32 | Comando JSON versionado |
| `bomba/estado` | ESP32 -> Frontend | Estado confirmado/aplicado da bomba |

## Tabela de regras de alerta

| Tipo | Descricao | Efeito |
| --- | --- | --- |
| `missing_timestamp` | Evento sem horario confiavel | Bloqueia ciclo e AutoCloud |
| `duplicate_event` | Mesmo sensor/estado repetido em janela curta | Bloqueia ciclo e AutoCloud |
| `out_of_order_event` | Evento recebido fora de ordem cronologica | Bloqueia ciclo e AutoCloud |
| `unexpected_low_repeat` | Sensor baixo repetiu antes do alto | Bloqueia ciclo e AutoCloud |
| `implausible_drain_time` | Esvaziamento rapido demais | Bloqueia ciclo e AutoCloud |
| `unexpected_high_without_low` | Sensor alto subiu sem baixo coerente | Bloqueia ciclo e AutoCloud |
| `low_dropped_while_high_active` | Baixo desceu com alto ativo | Bloqueia ciclo e AutoCloud |
| `slow_fill_cycle` | Enchimento mais lento que o historico | Gera alerta temporal |
| `persistent_fill_time_shift` | Tendencia persistente de aumento | Gera alerta temporal |
| `new_fill_time_cluster` | Novo padrao distante do historico | Gera alerta temporal |

## Observacoes para redacao final

- Evitar dizer que o sistema "diagnostica" defeitos fisicos. O correto e afirmar que o sistema "detecta anomalias" e apresenta "possiveis causas".
- Explicar que as estimativas de agua e energia dependem de parametros configuraveis e, portanto, representam aproximacoes.
- Enfatizar que a IA nao consulta diretamente o banco; o backend monta contexto estruturado e controla os dados enviados ao modelo.
- Destacar que o uso de idempotencia evita duplicidade quando a Firebase Function faz retentativas.
- Destacar que a prioridade fisica/remota/automatica e essencial para seguranca operacional.
- Para resultados, usar linguagem de validacao do prototipo: "foi verificado", "foi observado", "permitiu", "apresentou", "registrou".
- Para conclusao, sugerir expansoes como sensor de vazao, medicao eletrica dedicada, notificacoes push, HTTPS em producao, App Check/Firebase Rules e dashboards comparativos.
