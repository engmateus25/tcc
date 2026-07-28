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
- `GET /reports/weekly?period=7d`: relatorio PDF de 7, 30 ou 90 dias.
- `GET /reports/monthly`: relatorio PDF mensal.
- `GET /alerts/sensors`: analise de alertas no periodo.
- `GET /alerts?period=7d&status=open&severity=warning`: consulta de alertas persistidos.
- `PATCH /alerts/{alert_id}/ack`: marca um alerta persistido como reconhecido.
- `POST /alerts/sensor-event`: webhook para novo evento de sensor.

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

Os testes atuais cobrem contrato de schema, autenticacao do webhook e idempotencia com mocks locais. Eles nao exigem credenciais reais do Firestore.

### Variaveis de ambiente do backend

As variaveis abaixo aparecem no codigo atual ou sao esperadas pelas integracoes:

```text
CORS_ORIGINS
GOOGLE_APPLICATION_CREDENTIALS
FIREBASE_CREDENTIALS_JSON
FIRESTORE_SENSORS_COLLECTION
FIRESTORE_ALERTS_COLLECTION
FIRESTORE_SENSOR_EVENT_PROCESSING_COLLECTION
FIRESTORE_FILLING_CYCLES_COLLECTION
SENSOR_DUPLICATE_WINDOW_SECONDS
SENSOR_OUT_OF_ORDER_TOLERANCE_SECONDS
MIN_PLAUSIBLE_DRAIN_TIME_SECONDS
FILL_TIME_MIN_SAMPLES
FILL_TIME_SLOW_FACTOR
FILL_TIME_PERSISTENT_WINDOW
SENSOR_EVENT_WEBHOOK_SECRET
LLM_PROVIDER
OLLAMA_BASE_URL
OLLAMA_MODEL
OPENAI_API_KEY
OPENAI_MODEL
ENABLE_SCHEDULER
SCHEDULE_CRON_WEEKLY
SCHEDULE_CRON_MONTHLY
PDF_OUTPUT_DIR
```

Observacao: nao versionar arquivos `.env`, chaves privadas ou credenciais Firebase Admin.

## Frontend

O frontend usa Ionic React, React Router, Vite, Firebase client SDK, MQTT, Recharts, Radix UI e lucide-react.

Pontos principais:

- `frontend/src/App.tsx`: rotas da aplicacao.
- `frontend/src/layouts/AppLayout.tsx`: estrutura visual comum, header, conteudo e status de conexao.
- `frontend/src/pages/HomePage.tsx`: painel principal do reservatorio.
- `frontend/src/pages/HistoryPage.tsx`: historico e estatisticas, ainda com dados mockados em parte.
- `frontend/src/pages/ChatPage.tsx`: interface do assistente IA.
- `frontend/src/hooks/useWaterSystem.ts`: estado central, Firestore realtime e MQTT.
- `frontend/src/services/firestoreService.ts`: consultas e listeners da colecao `sensores`.
- `frontend/src/services/mqttService.ts`: conexao MQTT e publicacao em `bomba/controle`.
- `frontend/src/services/aiService.ts`: chamadas ao backend.

### Rodar o frontend

```bash
cd frontend
npm install
npm run dev
```

Comandos disponiveis:

```bash
npm run build
npm run lint
npm run test.unit
npm run test.e2e
```

Variavel de ambiente relevante:

```text
VITE_AI_BASE_URL=http://127.0.0.1:8000
```

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
- sincronizar horario via NTP.

Topicos MQTT atuais:

```text
bomba/controle
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

## Firebase e MQTT

Uso atual:

- Firestore `sensores`: eventos dos sensores com `sensor`, `estado` e `timestamp`.
- Firestore `comandos`: comandos/acionamentos da bomba.
- Firestore `chat_sessions`: sessoes e mensagens do chat no backend.
- Firestore `sensor_event_processing`: controle tecnico de processamento idempotente por evento.
- Firestore `alerts`: alertas padronizados com `event_id`, `type`, `severity`, `status`, causas possiveis e metadados.
- Firestore `filling_cycles`: ciclos validos `baixo subiu -> alto subiu` com `fill_time_seconds`.
- MQTT `bomba/controle`: comandos enviados pelo app.
- MQTT `bomba/estado`: status lido pelo app quando publicado.

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

Depois da idempotencia, o backend aplica regras deterministicas antes de qualquer analise temporal. Eventos com alerta bloqueante, como duplicidade, timestamp ausente, fora de ordem, repeticao suspeita do sensor baixo ou esvaziamento rapido demais, nao alimentam ciclos nem a analise de tempo de enchimento.

O ciclo de enchimento persistido considera `baixo subiu` como inicio e `alto subiu` como fim. O campo `fill_time_seconds` alimenta a analise temporal de enchimento, que retorna `insufficient_data` com poucos ciclos e gera alertas como `slow_fill_cycle`, `persistent_fill_time_shift` ou `new_fill_time_cluster` quando a duracao fica fora da linha de base.

## Firebase Functions

A pasta `functions/` contem a Function `onSensorCreated`, implementada com Firebase Functions v2 em TypeScript. Ela escuta `sensores/{docId}`, converte o documento Firestore para o contrato enriquecido de evento de sensor e chama `POST /alerts/sensor-event`.

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

- A tela de historico ainda possui dados mockados.
- O frontend ja escuta Firestore para ultimo evento de sensor.
- O controle da bomba usa MQTT diretamente do frontend.
- O backend le Firestore para relatorios, alertas e agente IA.
- O backend persiste alertas padronizados e ciclos de enchimento validos; a exibicao desses alertas no app ainda e pendencia de frontend.
- A Firebase Function de alertas esta estruturada em `functions/src/index.ts`, com build/test locais. Emulator e deploy ainda precisam de projeto Firebase, Firebase CLI e secrets configurados.
