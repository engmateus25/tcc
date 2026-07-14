# AquaMonitor

AquaMonitor e um sistema de monitoramento e controle de reservatorio de agua para projeto de TCC. O projeto integra um ESP32 com sensores/atuadores, um aplicativo web/mobile em Ionic React, uma API FastAPI e servicos Firebase/MQTT para comunicacao, armazenamento e controle remoto.

## Visao geral

O sistema esta dividido em tres dominios principais:

- `backend/`: API, agentes de IA, relatorios, alertas e integracao server-side com Firestore.
- `frontend/`: aplicacao Ionic React para visualizacao, controle da bomba, historico e assistente IA.
- `firmware/`: codigo do ESP32 responsavel por sensores, bomba, MQTT e envio de eventos ao Firestore.

Fluxo principal:

```text
ESP32 -> Firestore REST -> colecao sensores
ESP32 <- MQTT bomba/controle <- Frontend
Frontend -> Firestore client SDK -> dados em tempo real
Frontend -> FastAPI -> agente IA, chat, relatorios e alertas
Backend -> Firebase Admin -> leitura de eventos, sessoes e alertas
```

## Estrutura do projeto

```text
.
|-- AGENTS.md
|-- README.md
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- routers/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- tasks/
|   |-- generated/
|   `-- requirements.txt
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

### Variaveis de ambiente do backend

As variaveis abaixo aparecem no codigo atual ou sao esperadas pelas integracoes:

```text
CORS_ORIGINS
GOOGLE_APPLICATION_CREDENTIALS
FIREBASE_CREDENTIALS_JSON
FIRESTORE_SENSORS_COLLECTION
FIRESTORE_ALERTS_COLLECTION
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
- MQTT `bomba/controle`: comandos enviados pelo app.
- MQTT `bomba/estado`: status lido pelo app quando publicado.

Ha tambem codigo com formato de Cloud Function em `frontend/src/services/alerts.ts`. Pelo conteudo, ele representa uma funcao server-side para disparar o webhook `/alerts/sensor-event` quando um documento novo entra em `sensores`. Em uma reorganizacao futura, esse codigo deve sair do frontend e ir para uma pasta propria, por exemplo `functions/`.

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
python -m compileall app
uvicorn app.main:app --reload
```

Para firmware, validar no Arduino IDE ou ambiente equivalente com placa ESP32 e bibliotecas necessarias instaladas.

## Estado atual conhecido

- A tela de historico ainda possui dados mockados.
- O frontend ja escuta Firestore para ultimo evento de sensor.
- O controle da bomba usa MQTT diretamente do frontend.
- O backend le Firestore para relatorios, alertas e agente IA.
- A Cloud Function de alertas esta representada dentro de `frontend/src/services/alerts.ts`, mas deveria viver em um modulo server-side separado no futuro.
