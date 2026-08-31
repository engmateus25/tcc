# AquaMonitor

AquaMonitor e um sistema de monitoramento e controle de reservatorio de agua para projeto de TCC. O projeto integra um ESP32 com sensores/atuadores, um aplicativo web/mobile em Ionic React, uma API FastAPI e servicos Firebase/MQTT para comunicacao, armazenamento e controle remoto.

## Visao geral

O sistema esta dividido em quatro dominios principais:

- `backend/`: API, agentes de IA, relatorios, alertas e integracao server-side com Firestore.
- `frontend/`: aplicacao Ionic React para visualizacao, controle da bomba, historico e assistente IA.
- `firmware/`: codigo do ESP32 responsavel por sensores, bomba, MQTT e envio de eventos ao Firestore.
- `functions/`: Firebase Functions v2 em TypeScript para acionar o backend a partir de eventos Firestore.

Fluxo principal:

```text
ESP32 -> Firestore REST -> colecao sensores
Firestore sensores -> Firebase Function -> Backend /alerts/sensor-event
Firestore comandos -> Firebase Function -> Backend /alerts/command-event
ESP32 <- MQTT bomba/controle <- Frontend
Frontend -> Firestore client SDK -> dados em tempo real
Frontend -> FastAPI -> agente IA, chat, relatorios e alertas
Backend -> Firebase Admin -> leitura de eventos, sessoes e alertas
```

## Estrutura do projeto

```text
.
|-- .node-version
|-- .nvmrc
|-- AGENTS.md
|-- README.md
|-- firebase.json
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- routers/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- tasks/
|   |-- generated/
|   `-- requirements.txt
|-- functions/
|   |-- src/
|   |   |-- config.ts
|   |   |-- index.ts
|   |   `-- payload.ts
|   |-- test/
|   |-- package.json
|   `-- tsconfig.json
|-- firmware/
|   `-- TCC.ino/
|       |-- TCC_Final/
|       `-- TCC_2_sensores/
`-- frontend/
    |-- android/
    |-- src/
    |   |-- components/
    |   |-- hooks/
    |   |-- layouts/
    |   |-- pages/
    |   |-- services/
    |   `-- types/
    |-- package.json
    `-- vite.config.ts
```

## Ambiente Node.js

Use Node.js 22 para o frontend e para `functions/`. O ambiente Linux oficial foi validado com Node.js `v22.23.1` e npm `10.9.8`.

Os arquivos `.nvmrc` e `.node-version` deixam a versao major `22` explicita para ferramentas de gerenciamento de Node.

## Backend

O backend usa FastAPI. O ponto de entrada e `backend/app/main.py`.

Responsabilidades principais:

- expor endpoints HTTP;
- consultar Firestore com Firebase Admin;
- gerar relatorios PDF;
- detectar inconsistencias/anomalias de sensores;
- responder perguntas analiticas com agente IA;
- manter sessoes de chat;
- executar scheduler opcional de relatorios.

Rotas principais:

- `GET /health`: verificacao simples da API.
- `POST /llm/chat`: chat generico com LLM.
- `POST /llm/chat/stream`: chat em streaming.
- `GET /llm/sessions/{session_id}`: historico de uma sessao.
- `POST /agent`: agente analitico do AquaMonitor.
- `GET /reports/summary?period=7d`: resumo JSON com sensores, consumo de agua, energia da bomba e alertas recentes.
- `GET /reports/weekly?period=7d`: relatorio PDF de 7, 30 ou 90 dias.
- `GET /reports/monthly`: relatorio PDF mensal.
- `GET /alerts/sensors`: analise de alertas no periodo.
- `GET /alerts?period=7d&status=open&severity=warning`: consulta de alertas persistidos.
- `PATCH /alerts/{alert_id}/ack`: marca um alerta persistido como reconhecido.
- `POST /alerts/sensor-event`: webhook para novo evento de sensor.
- `POST /alerts/command-event`: webhook para novo evento de comando/estado da bomba.

Camadas:

- `routers/`: definicao das rotas FastAPI.
- `schemas/`: DTOs Pydantic.
- `services/`: regras de negocio e integracoes.
- `tasks/`: scheduler com APScheduler.

### Rodar o backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Para que outros aparelhos possam se conectar a aplicação via IP do host

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Juntamente com a exposição do IP do host em .env de backend e frontend.

Por padrao, a API fica em:

```text
http://127.0.0.1:8000/docs
```

### Rodar testes do backend

```bash
cd backend
source .venv/bin/activate
pytest
python -m compileall app tests
```

Os testes atuais cobrem contrato de schema, autenticacao do webhook, idempotencia e falha operacional do Firestore com mocks locais. Eles nao exigem credenciais reais do Firestore.

### Seed seguro para integracao Firestore

O script `backend/scripts/seed_integration_firestore.py` cria dados controlados e idempotentes para validacao de integracao. Por padrao, ele usa colecoes de teste (`integration_test_sensores` e `integration_test_comandos`) e identifica todos os documentos com `source=integration_test` e `test_run_id`.

```bash
cd backend
source .venv/bin/activate
python scripts/seed_integration_firestore.py --dry-run --test-run-id codex-dryrun
python scripts/seed_integration_firestore.py --test-run-id codex-integracao
python scripts/seed_integration_firestore.py --cleanup --test-run-id codex-integracao
```

Para validar gatilhos reais nas colecoes operacionais `sensores` e `comandos`, use `--operational` conscientemente e remova somente os documentos do mesmo `test_run_id`. Nunca limpe colecoes inteiras.

### Seed do AutoCloud para PIBITI

O script `backend/scripts/seed_autocloud_firestore.py` grava cinco ciclos normais na colecao `autocloud_filling_samples`, valida um ciclo normal sem alerta, processa um ciclo lento para gerar `slow_fill_cycle` e processa um caso de intertravamento para gerar `unexpected_high_without_low`.

```bash
cd backend
.venv/bin/python scripts/seed_autocloud_firestore.py
```

Na validacao de 31/08/2026, foi gravado o `test_run_id=pibiti-20260831-103355`. Esse identificador pode ser usado no console do Firebase para localizar as amostras e alertas demonstrativos.

### Variaveis de ambiente do backend

As variaveis abaixo aparecem no codigo atual ou sao esperadas pelas integracoes:

```text
CORS_ORIGINS
GOOGLE_APPLICATION_CREDENTIALS
FIREBASE_CREDENTIALS_JSON
FIRESTORE_SENSORS_COLLECTION
FIRESTORE_COMMANDS_COLLECTION
FIRESTORE_ALERTS_COLLECTION
FIRESTORE_SENSOR_EVENT_PROCESSING_COLLECTION
FIRESTORE_FILLING_CYCLES_COLLECTION
FIRESTORE_OPERATION_TIMEOUT_SECONDS
RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS
WATER_PRICE_PER_CUBIC_METER_BRL
PUMP_POWER_KW
ELECTRICITY_PRICE_PER_KWH_BRL
SENSOR_DUPLICATE_WINDOW_SECONDS
SENSOR_OUT_OF_ORDER_TOLERANCE_SECONDS
MIN_PLAUSIBLE_DRAIN_TIME_SECONDS
FILL_TIME_MIN_SAMPLES
FILL_TIME_SLOW_FACTOR
FILL_TIME_PERSISTENT_WINDOW
SENSOR_EVENT_WEBHOOK_SECRET
LLM_PROVIDER
LLM_TEMPERATURE
LLM_MAX_TOKENS
OLLAMA_BASE_URL
OLLAMA_MODEL
OLLAMA_TIMEOUT_SECONDS
GEMINI_API_KEY
GEMINI_MODEL
GEMINI_BASE_URL
GEMINI_TIMEOUT_SECONDS
OPENAI_API_KEY
OPENAI_MODEL
AGENT_RESPONSE_MODE
AGENT_ALLOW_DETERMINISTIC_FALLBACK
AGENT_SEND_RAW_EVENTS_TO_LLM
AGENT_MAX_HISTORY_MESSAGES
ENABLE_SCHEDULER
SCHEDULE_CRON_WEEKLY
SCHEDULE_CRON_MONTHLY
PDF_OUTPUT_DIR
```

Observacao: nao versionar arquivos `.env`, chaves privadas ou credenciais Firebase Admin.

### Chatbot e provedores LLM

O backend possui uma fachada `LLMProvider` para selecionar o modelo por ambiente:

- `LLM_PROVIDER=ollama`: usa Ollama local em `OLLAMA_BASE_URL`.
- `LLM_PROVIDER=gemini`: usa Gemini API com `GEMINI_API_KEY`, mantida somente no backend.
- `LLM_PROVIDER=openai`: usa OpenAI com `OPENAI_API_KEY`.

O modelo local recomendado para sair do `qwen2:0.5b` e melhorar qualidade é `qwen3:4b-instruct`:

```bash
ollama pull qwen3:4b-instruct
```

Se o Ollama ainda nao estiver instalado:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:4b-instruct
```

Para Gemini, preencha no backend:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=<sua-chave-do-Google-AI-Studio>
GEMINI_MODEL=gemini-3.6-flash
```

O endpoint `POST /agent` monta contexto estruturado a partir de Firestore antes de chamar o modelo. Por padrao, `AGENT_RESPONSE_MODE=hybrid`: o backend tenta usar o LLM configurado e, se o provedor estiver indisponivel, retorna uma resposta deterministica com `fallback_used=true` e `llm_error` preenchido. Use `AGENT_RESPONSE_MODE=llm` e `AGENT_ALLOW_DETERMINISTIC_FALLBACK=0` quando quiser falhar explicitamente sem fallback.

Por seguranca, `AGENT_SEND_RAW_EVENTS_TO_LLM=0` envia apenas agregados e resumos para provedores online. Defina `1` somente se for aceitavel enviar eventos recentes de sensor ao provedor configurado.

## Frontend

O frontend usa Ionic React, React Router, Vite, Firebase client SDK, MQTT, Recharts, Radix UI e lucide-react.

Pontos principais:

- `frontend/src/App.tsx`: rotas da aplicacao.
- `frontend/src/layouts/AppLayout.tsx`: estrutura visual comum, header, conteudo e status de conexao.
- `frontend/src/pages/HomePage.tsx`: painel principal do reservatorio.
- `frontend/src/pages/HistoryPage.tsx`: historico e estatisticas, ainda com dados mockados em parte.
- `frontend/src/pages/ChatPage.tsx`: interface do assistente IA.
- `frontend/src/hooks/useWaterSystem.ts`: estado central, Firestore realtime e MQTT.
- `frontend/src/hooks/useAlerts.ts`: polling dos alertas persistidos no backend.
- `frontend/src/services/firestoreService.ts`: consultas e listeners das colecoes `sensores` e `comandos`.
- `frontend/src/services/mqttService.ts`: conexao MQTT configuravel por ambiente e publicacao em `bomba/controle/v2`.
- `frontend/src/services/aiService.ts`: chamadas ao backend.
- `frontend/src/services/alerts.ts`: consulta e reconhecimento de alertas inteligentes.

### Rodar o frontend

```bash
cd frontend
npm install
npm run dev
```

### Para que outros aparelhos possam se conectar a aplicação via IP do host

```bash
npm run dev -- --host 0.0.0.0
```

Comandos disponiveis:

```bash
npm run build
npm run lint
npm run test.unit
npm run test.e2e
npm run cap:sync
npm run android:sync
npm run android:open
```

Crie `frontend/.env` a partir de `frontend/.env.example` antes de iniciar o app. Variaveis principais:

```text
VITE_AI_BASE_URL=http://127.0.0.1:8000
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_DATABASE_URL=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
VITE_FIREBASE_MEASUREMENT_ID=
VITE_MQTT_URL=wss://broker.hivemq.com:8884/mqtt
VITE_MQTT_CLIENT_PREFIX=aquamonitor_web
VITE_MQTT_USERNAME=
VITE_MQTT_PASSWORD=
VITE_MQTT_CONTROL_TOPIC=bomba/controle
VITE_MQTT_CONTROL_V2_TOPIC=bomba/controle/v2
VITE_MQTT_STATE_TOPIC=bomba/estado
VITE_MQTT_PUBLISH_LEGACY_CONTROL=0
```

As variaveis `VITE_*` ficam publicas no bundle do frontend. Elas nao devem conter credenciais administrativas; proteja o Firebase com regras, dominios autorizados e App Check.

Se `frontend/.env` ainda nao existir, a interface abre em modo degradado com Firebase desconectado e registra no console quais variaveis faltam. Para dados reais de sensores, historico e alertas, preencha as variaveis Firebase antes de iniciar o Vite.

Durante desenvolvimento com Vite, o backend permite por padrao as origens locais `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5174` e `http://127.0.0.1:5174`, alem das origens Ionic `8100`.

`VITE_MQTT_PUBLISH_LEGACY_CONTROL=1` faz o app publicar tambem o payload texto em `bomba/controle`. Mantenha `0` com o firmware novo, porque ele ja assina `bomba/controle/v2`.

### Android com Capacitor

A plataforma Android fica em `frontend/android/` e foi gerada com Capacitor 7. A configuracao nativa atual usa:

```text
appId: br.com.aquamonitor.app
appName: AquaMonitor
webDir: dist
```

O `appId` ainda deve ser tratado como provisorio ate a definicao final do identificador de publicacao. Antes de abrir no Android Studio ou instalar em emulador/dispositivo, sincronize o bundle web:

```bash
cd frontend
npm run android:sync
```

Para abrir o projeto nativo:

```bash
cd frontend
npm run android:open
```

Em dispositivo fisico, `VITE_AI_BASE_URL=http://127.0.0.1:8000` aponta para o proprio celular, nao para o notebook. Use o IP do host na rede local, por exemplo `http://192.168.1.20:8000`, e rode o backend com `--host 0.0.0.0`. O manifesto Android permite `android:usesCleartextTraffic="true"` para esses testes locais com HTTP; antes de publicar, prefira backend HTTPS e remova essa permissao ampla.

Pre-requisitos da maquina para compilar/rodar o app:

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk
sudo snap install android-studio --classic
```

Depois de instalar o Android Studio, configure o Android SDK, uma imagem de emulador e aceite as licencas pelo proprio Android Studio.

### Home, Firestore realtime e nivel visual

A Home usa um listener da colecao `sensores` com `orderBy("timestamp", "desc")` e limite de eventos recentes. Snapshot vazio e tratado como Firestore conectado, nao como erro. O status global diferencia `conectando`, `conectado`, `offline/cache` e `erro`, sem usar `.info/connected` do Realtime Database.

O campo "Ultimo Sensor Alterado" mostra sensor, evento, estado operacional derivado e data/hora em `pt-BR`. O nivel cilindrico e uma estimativa visual calculada pelo timestamp do ultimo evento e parametros centralizados: nivel baixo em 20%, piso de esvaziamento em 21%, enchimento visual em 480s e esvaziamento visual em 480s. Durante enchimento sem confirmacao do sensor alto, a visualizacao fica limitada a 99% e exibe "Aguardando confirmacao do sensor alto". Essa animacao nao cria documentos no Firestore e nao e usada para calculo de consumo.

Em telas a partir de `1024px`, a Home organiza o painel em duas colunas: indicadores, alertas e reservatorio na coluna principal, e atalhos/estado do sistema na coluna lateral. Em telas menores, a composicao volta para uma coluna. O cabecalho azul compartilhado fica dentro do fluxo do `IonContent`, entao rola junto com o conteudo em vez de permanecer fixo.

O estado operacional da bomba e centralizado em `useWaterSystem`. A fonte preferencial e a colecao `comandos`, usando somente eventos realmente aplicados (`applied=true`) e seu `applied_state`; em seguida entram confirmacoes MQTT de `bomba/estado`; se ainda nao houver confirmacao operacional mais recente, a interface usa uma inferencia temporaria pelos sensores (`baixo desceu` liga automatico, `alto subiu` desliga automatico). Com isso, Home, controle da bomba, estimativas e estatisticas compartilham a mesma leitura efetiva.

### Historico e relatorios

A tela de Historico usa controles clicaveis com borda, foco e estado selecionado para periodos (`7d`, `30d`, `90d`) e tipos (`agua`, `energia`, `sensores`). O bloco antigo de atalho para o assistente IA foi removido dessa tela; o acesso ao chatbot continua disponivel pela Home e pela rota dedicada.

Os relatorios PDF gerados pelo backend quebram linhas longas em alertas recentes, valores de blocos-chave e observacoes. A geracao reserva altura dinamica e cria novas paginas quando necessario para evitar sobreposicao entre textos, tabelas e secoes.

## Firmware

O firmware fica em `firmware/TCC.ino/` e possui duas variantes:

- `TCC_Final/TCC_Final.ino`: versao mais completa, com prioridade entre chave fisica, comando remoto e controle automatico.
- `TCC_2_sensores/TCC_2_sensores.ino`: versao anterior/alternativa com dois sensores.

Responsabilidades do ESP32:

- conectar ao Wi-Fi;
- conectar ao broker MQTT HiveMQ;
- assinar o topico `bomba/controle`;
- controlar bomba e LEDs;
- ler sensores de nivel baixo e alto;
- registrar eventos na colecao Firestore `sensores`;
- registrar comandos na colecao Firestore `comandos`;
- manter buffer offline limitado em RAM para reenvio de eventos/comandos ao Firestore;
- sincronizar horario via NTP.

Antes de compilar `TCC_Final/TCC_Final.ino`, copie `firmware/TCC.ino/TCC_Final/secrets.h.example` para `firmware/TCC.ino/TCC_Final/secrets.h` e preencha Wi-Fi, Firebase Web API key, URLs das colecoes e MQTT. O `secrets.h` real fica ignorado pelo Git.

O buffer offline do firmware usa `OFFLINE_BUFFER_CAPACITY` e `FIRESTORE_RETRY_INTERVAL_MS`. Quando o limite e atingido, o firmware descarta o evento mais antigo, registra no Serial e preserva os mais recentes para reenvio em ordem apos reconexao.

Topicos MQTT atuais:

```text
bomba/controle
bomba/controle/v2
bomba/estado
```

Payload de controle esperado pelo firmware:

```text
<nome> ligar
<nome> desligar
```

Exemplos:

```text
bomba ligar
bomba desligar
```

O firmware tambem aceita o contrato JSON versionado no topico `bomba/controle/v2`:

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

O estado confirmado da bomba e publicado em `bomba/estado`:

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

## Firebase e MQTT

Uso atual:

- Firestore `sensores`: eventos dos sensores com `sensor`, `estado` e `timestamp`.
- Firestore `comandos`: comandos/acionamentos da bomba com estado solicitado, estado aplicado, confirmacao, prioridade e sobreposicao.
- Firestore `chat_sessions`: sessoes e mensagens do chat no backend.
- Firestore `sensor_event_processing`: controle tecnico de processamento idempotente por evento.
- Firestore `alerts`: alertas padronizados com `event_id`, `type`, `severity`, `status`, causas possiveis e metadados.
- Firestore `filling_cycles`: ciclos validos de enchimento com inicio preferencial em bomba aplicada/confirmada como ligada, transicao `baixo subiu` quando disponivel e fim em `alto subiu`.
- Firestore `autocloud_filling_samples`: amostras vetorizadas de ciclos validos usadas como linha de base de clusterizacao do AutoCloud.
- MQTT `bomba/controle`: comandos texto legados.
- MQTT `bomba/controle/v2`: comandos JSON versionados enviados pelo app.
- MQTT `bomba/estado`: status lido pelo app quando publicado.

Na colecao `comandos`, os campos `requested_state`, `applied_state`, `applied`, `confirmed`, `state_changed`, `source`, `priority`, `overridden_by`, `command_id` e `reason` distinguem comando solicitado de estado realmente aplicado. O calculo de energia considera apenas eventos aplicados e confirmados; comandos sobrepostos por prioridade fisica/remota/automatica ficam auditados, mas nao entram como tempo ligado.

O webhook `POST /alerts/sensor-event` aceita o payload legado do firmware e o payload enriquecido da Function:

```json
{
  "document_id": "firestore-doc-id",
  "event_id": "sensores/firestore-doc-id",
  "sensor": "baixo",
  "estado": "desceu",
  "timestamp": "2026-07-27T12:00:00Z",
  "device_id": "esp32-reservatorio-01",
  "source": "firestore_on_create",
  "raw_path": "sensores/firestore-doc-id",
  "received_at": "2026-07-27T12:00:01Z"
}
```

Quando `SENSOR_EVENT_WEBHOOK_SECRET` estiver definido no backend, a chamada deve enviar o header `X-AquaMonitor-Webhook-Secret`. O backend usa `event_id`, `raw_path` ou `document_id` como chave idempotente e registra o processamento em `sensor_event_processing`.

O webhook `POST /alerts/command-event` recebe documentos da colecao `comandos` e usa o mesmo segredo compartilhado. O payload inclui `command_id`, estado solicitado, estado aplicado, confirmacao, prioridade e sobreposicao. Comandos com `applied=true`, `confirmed=true` e `applied_state=true` iniciam preferencialmente um ciclo de enchimento; comandos nao aplicados, nao confirmados ou sobrepostos ficam auditados, mas nao entram como inicio de ciclo nem no calculo de energia.

As colecoes tecnicas `sensor_event_processing`, `alerts`, `filling_cycles` e `autocloud_filling_samples` sao criadas automaticamente pelo Firestore no primeiro documento gravado com credenciais Firebase Admin validas. Se a credencial estiver invalida ou indisponivel, as rotas de alertas retornam `503` em vez de aguardar o retry longo padrao do SDK. A consulta `GET /alerts` busca por periodo e filtra `status`/`severity` no backend para nao depender de indice composto do Firestore durante o desenvolvimento local.

Depois da idempotencia, o backend aplica regras deterministicas antes de qualquer analise temporal. Eventos com alerta bloqueante, como duplicidade, timestamp ausente, fora de ordem, repeticao suspeita do sensor baixo ou esvaziamento rapido demais, nao alimentam ciclos nem a analise de tempo de enchimento.

O ciclo de enchimento persistido considera como inicio preferencial o comando/estado da bomba aplicado e confirmado como ligada. Quando essa confirmacao nao existir, a sequencia de sensores valida e `baixo desceu`, `baixo subiu` e `alto subiu`; a transicao `baixo subiu` e armazenada como marco fisico de ultrapassagem da boia inferior. O ciclo guarda `fill_time_seconds`, `low_to_high_seconds` e `pump_to_low_seconds`.

O AutoCloud usa `autocloud_filling_samples` como baseline operacional. Cada ciclo e vetorizado com duracao total, tempo entre `baixo subiu` e `alto subiu`, tempo ate ultrapassar a boia baixa, tipo de inicio e completude da sequencia de sensores. O vetor e normalizado por mediana e escala robusta antes de entrar no algoritmo incremental de nuvens. A analise retorna `insufficient_data` com poucos ciclos e gera alertas como `slow_fill_cycle`, `persistent_fill_time_shift` ou `new_fill_time_cluster` quando a duracao ou o agrupamento fica fora da linha de base.

## Firebase Functions

A pasta `functions/` contem as Functions `onSensorCreated` e `onCommandCreated`, implementadas com Firebase Functions v2 em TypeScript. A primeira escuta `sensores/{docId}`, converte o documento Firestore para o contrato enriquecido de evento de sensor e chama `POST /alerts/sensor-event`. A segunda escuta `comandos/{docId}`, converte o documento para o contrato de comando/estado da bomba e chama `POST /alerts/command-event`.

Runtime e configuracao local:

```bash
cd functions
node -v
npm install
npm run build
npm test
```

Variaveis usadas pela Function:

```text
BACKEND_SENSOR_EVENT_URL
BACKEND_COMMAND_EVENT_URL
SENSOR_EVENT_WEBHOOK_SECRET
FUNCTION_REGION
```

`firebase.json` define a origem `functions/`, runtime Node.js 22 e portas dos emuladores. `.firebaserc.example` serve apenas como modelo; o projeto Firebase real deve ser configurado localmente ou em ambiente seguro. `functions/.env` e secrets reais nao devem ser versionados.

O build e os testes locais validam a estrutura e a conversao de payload. A execucao com Firebase Emulator e o deploy ainda dependem de Firebase CLI, projeto real/alias e configuracao de secrets.

## Cuidados de seguranca

O projeto atual contem configuracoes Firebase e credenciais/chaves em codigo fonte, principalmente no frontend e firmware. Antes de publicacao ou uso fora de ambiente controlado, revisar:

- regras de seguranca do Firestore;
- restricoes de chave Web API do Firebase;
- separacao de credenciais por ambiente;
- uso de arquivos `.env` no backend/frontend;
- estrategia para configurar secrets do firmware sem expor dados sensiveis.

Nao altere, remova ou regenere credenciais sem autorizacao explicita.

## Fluxo Spec-Driven Development

Para novas funcionalidades, usar specs curtas e implementaveis antes do codigo.

Sugestao de pasta:

```text
specs/
|-- 001-nome-da-funcionalidade.md
|-- 002-outra-tarefa.md
`-- template.md
```

Modelo recomendado de spec:

```markdown
# Nome da funcionalidade

## Objetivo

## Contexto

## Escopo

## Fora de escopo

## Contratos afetados

## Dados envolvidos

## Tarefas

## Criterios de aceite

## Plano de testes

## Arquivos provavelmente afetados
```

Como trabalhar:

1. Entender o requisito.
2. Criar ou revisar uma spec curta.
3. Dividir em tarefas pequenas por dominio: backend, frontend, firmware e integracao.
4. Implementar uma tarefa por vez.
5. Testar no menor nivel possivel.
6. Registrar o que mudou na spec ou na documentacao.

## Convencoes para tarefas futuras

- Backend: preservar a separacao `routers -> schemas -> services`.
- Frontend: concentrar integracoes em `src/services/` e estado reutilizavel em `src/hooks/`.
- Firmware: manter pinos, topicos e prioridades de controle documentados no proprio sketch quando necessario.
- Integracao: definir contratos de payload antes de mudar frontend, backend ou firmware.
- Documentacao: atualizar este README quando comandos, arquitetura ou contratos mudarem.

## Validacao recomendada

Antes de entregar uma mudanca, validar o que for aplicavel:

```bash
cd frontend
npm run build
npm run lint
```

```bash
cd backend
source .venv/bin/activate
pytest
python -m compileall app tests
```

```bash
cd functions
npm run build
npm test
```

Para firmware, validar no Arduino IDE ou ambiente equivalente com placa ESP32 e bibliotecas necessarias instaladas.

## Estado atual conhecido

- O frontend ja escuta Firestore para ultimo evento de sensor.
- O frontend exibe alertas inteligentes persistidos pelo backend e permite reconhecer alertas abertos.
- O controle da bomba usa MQTT diretamente do frontend e aguarda confirmacao em `bomba/estado`.
- A tela de historico consulta `/reports/summary` e baixa PDF real pelo backend.
- O backend le Firestore para relatorios, consumo, energia, alertas e agente IA.
- O backend persiste alertas padronizados e ciclos de enchimento validos.
- A Firebase Function de alertas esta estruturada em `functions/src/index.ts`, com build/test locais. Emulator e deploy ainda precisam de projeto Firebase, Firebase CLI e secrets configurados.
