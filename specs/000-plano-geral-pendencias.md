# Plano geral de pendencias do AquaMonitor

Data da auditoria: 2026-07-27

Status do documento: EM IMPLEMENTACAO

## Objetivo

Registrar um backlog tecnico rastreavel para as pendencias restantes do AquaMonitor, sem implementar mudancas funcionais nesta etapa.

Este plano foi construido a partir da leitura do `AGENTS.md`, `README.md`, arquivos de configuracao, backend FastAPI, frontend Ionic React/Vite, firmware ESP32, integracoes Firebase/MQTT/IA e codigo atual de alertas, relatorios e AutoCloud.

## Escopo desta etapa

- Mapear o que ja existe, o que esta parcial, incorreto ou ausente.
- Planejar atividades pequenas, verificaveis e testaveis.
- Preservar a arquitetura `backend/`, `frontend/`, `firmware/`.
- Nao alterar codigo funcional antes da aprovacao do planejamento.
- Nao remover arquivos, nao publicar credenciais, nao baixar modelos, nao fazer deploy.

## Fontes locais inspecionadas

- Raiz: `AGENTS.md`, `README.md`, `TASKS.md`, `.gitignore`.
- Backend: `backend/app/main.py`, `backend/app/routers/*`, `backend/app/schemas/dto.py`, `backend/app/services/*`, `backend/app/tasks/scheduler.py`, `backend/requirements.txt`, `backend/.env.example`.
- Frontend: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/capacitor.config.ts`, `frontend/ionic.config.json`, `frontend/src/App.tsx`, `frontend/src/layouts/AppLayout.tsx`, `frontend/src/pages/*`, `frontend/src/hooks/*`, `frontend/src/services/*`, componentes principais e componentes `ui`.
- Firmware: `firmware/TCC.ino/TCC_Final/TCC_Final.ino`.
- Testes/configuracao: `frontend/cypress/*`, `frontend/src/setupTests.ts`.

Arquivos sensiveis existentes foram avaliados apenas quanto a presenca e nomes de variaveis; valores de credenciais nao foram reproduzidos neste documento.

## Referencias externas consultadas

Estas referencias foram consultadas apenas para planejar tecnologia atualizavel:

- Firebase Firestore triggers v2: https://firebase.google.com/docs/firestore/extend-with-functions-2nd-gen
- Firebase Functions runtime/Node.js: https://firebase.google.com/docs/functions/manage-functions
- Firebase Functions ambiente e secrets: https://firebase.google.com/docs/functions/config-env
- Google Cloud runtime support para Node.js: https://docs.cloud.google.com/functions/docs/runtime-support
- Pacote `firebase-functions` no npm: https://www.npmjs.com/package/firebase-functions
- Gemini API models: https://ai.google.dev/gemini-api/docs/models
- Gemini API models endpoint: https://ai.google.dev/api/models
- Ollama Qwen3 4B instruct: https://ollama.com/library/qwen3:4b-instruct
- Ollama Qwen3 tags: https://registry.ollama.com/library/qwen3/tags

## Estado do repositorio antes da criacao deste plano

- `AGENTS.md` ja estava modificado.
- `TASKS.md` estava nao rastreado.
- `firmware/TCC.ino/TCC_2_sensores/TCC_2_sensores.ino` aparece como removido no Git.
- A pasta `specs/` ja existia e continha `RESPOSTA_1_CODEX.md`.

Nenhuma dessas alteracoes existentes foi revertida.

## Observacao sobre ambiente de desenvolvimento

O desenvolvimento operacional do projeto deve ser considerado Linux/WSL Ubuntu. A auditoria de 2026-07-27 foi executada a partir de um notebook Windows com acesso ao workspace, mas a `.venv` existente em `backend/.venv` pertence ao ambiente Linux/WSL e nao deve ser recriada ou corrigida no Windows.

Por isso, falhas relacionadas a importacao do backend e execucao da `.venv` no Windows devem ser tratadas como inconclusivas ate repetirmos a validacao no ambiente Linux oficial. Ja os problemas estaticos do frontend encontrados por `tsc`, como imports versionados em componentes `ui`, conflito local de tipo e `frontend/src/services/alerts.ts` contendo codigo server-side, continuam registrados como riscos provaveis porque nao dependem diretamente da `.venv`.

Antes de iniciar alteracoes funcionais, a proxima sessao em Linux deve executar uma validacao de baseline:

- `cd backend && source .venv/bin/activate && python -c "import app.main; print('backend import ok')"`
- `cd backend && python -m compileall app`
- `cd frontend && npm exec tsc -- --noEmit`
- `cd frontend && npm run lint`
- se aplicavel, `cd frontend && npm run build`

Validacao refeita no Linux oficial em 2026-07-27 antes da ATV-001:

- `cd backend && source .venv/bin/activate && python -c "import app.main; print('backend import ok')"`: passou.
- `cd backend && source .venv/bin/activate && python -m compileall app`: passou.
- `cd frontend && npm exec tsc -- --noEmit`: falhou antes da ATV-001 por imports versionados em `ui`, conflito `PumpMode` e codigo server-side em `frontend/src/services/alerts.ts`.
- `cd frontend && npm run lint`: falhou antes da ATV-001 por erros simples de lint em frontend, alem do `alerts.ts` server-side.
- `cd frontend && npm run build`: falhou antes da ATV-001 porque executa `tsc` primeiro.

Conclusao inicial: a pendencia de `.venv` era especifica do ambiente Windows/WSL anterior e nao se reproduziu no Linux. Os bloqueios reais de baseline estavam concentrados no frontend e foram tratados na ATV-001.

Validacao apos ATV-001:

- `cd frontend && npm exec tsc -- --noEmit`: passou.
- `cd frontend && npm run lint`: passou com 6 avisos nao bloqueantes de `react-refresh/only-export-components` em componentes `ui`.
- `cd frontend && npm run build`: passou. Restaram avisos nao bloqueantes de bundle acima de 500 kB e bases Browserslist/Baseline desatualizadas.
- `cd frontend && npx cypress run --config baseUrl=http://127.0.0.1:5174`: passou com 1 teste E2E. O Vite usou a porta 5174 porque a 5173 ja estava ocupada.

## Descobertas principais

### Backend

- `backend/app/main.py` registra `chat`, `reports`, `agent` e `alerts`.
- O endpoint `POST /alerts/sensor-event` existe em `backend/app/routers/alerts.py` e chama `process_new_sensor_event`.
- Existe um router duplicado em `backend/app/routers/webhook_sensor.py`, mas ele nao e registrado no `main.py`.
- `backend/app/schemas/dto.py` declara `SensorEventIn` duas vezes com o mesmo conteudo.
- `ChatResponse` nao declara `session_id`, mas `backend/app/routers/chat.py` retorna esse campo.
- `backend/app/services/firestore.py` busca eventos da colecao `sensores` por `timestamp` e ordena cronologicamente, mas nao preserva `doc.id` na versao ativa de `fetch_sensor_events`.
- Alertas em tempo real sao gravados em `alerts`, mas sem modelo padronizado, `event_id`, status, severidade, causas possiveis, deduplicacao ou idempotencia.
- O AutoCloud existe em `backend/app/services/autocloud_core.py` e e usado por `sensor_anomaly.py` e `sensor_realtime.py`, mas analisa eventos individuais codificados como vetor, nao ciclos de enchimento baixo -> alto.
- O backend possui `.env.example`, mas ele nao cobre todas as variaveis usadas ou desejadas, como `FIRESTORE_ALERTS_COLLECTION`, `MIN_PLAUSIBLE_DRAIN_TIME_SECONDS`, `GEMINI_API_KEY`, `GEMINI_MODEL`, configuracoes de consumo de agua e energia.
- A importacao do backend com o Python global falhou por dependencia ausente (`python-dotenv`). A `.venv` existente parece ter estrutura Linux (`bin/`) e nao executou corretamente no Windows atual.

### Frontend

- `frontend/src/services/firestoreConfig.ts` contem configuracao Firebase Web hardcoded.
- `frontend/src/services/mqttService.ts` conecta diretamente no HiveMQ publico e publica em `bomba/controle`.
- `frontend/src/services/alerts.ts` contem codigo com formato de Firebase Function server-side dentro de `src/services`, usando `require`, `exports`, `firebase-functions/v2/firestore` e `node-fetch`. Isso e camada inadequada para o frontend e entra no `tsconfig`.
- `frontend/src/hooks/useWaterSystem.ts` escuta o ultimo evento em `sensores`, consome `bomba/estado` e publica comandos MQTT. O nivel de agua ainda e mockado.
- `frontend/src/pages/HistoryPage.tsx` usa dados mockados e o botao PDF chama `alert()`.
- `frontend/src/pages/ChatPage.tsx` usa `/agent`, nao `/llm/chat`, entao o fluxo de chat analitico nao preserva sessoes como a rota generica.
- `frontend/src/hooks/AntiguseWaterSystem.ts` e uma versao antiga com simulacoes e TODOs.
- `CylinderLevel.tsx`, `CylinderLevel.css` e `TankCylinder.tsx` estao vazios.
- `npm exec tsc -- --noEmit` falhou. Principais causas:
  - componentes `ui` importam pacotes com sufixo de versao no specifier, por exemplo `lucide-react@0.487.0` e `recharts@2.15.2`;
  - conflito de declaracao `PumpMode` em `useWaterSystem.ts`;
  - `alerts.ts` causa erros de frontend por usar padrao server-side;
  - tipos implicitos em alguns componentes `ui`.
- Nao ha diretorios `frontend/android` ou `frontend/ios`; existem apenas dependencias Capacitor e `capacitor.config.ts`.

### Firmware

- O sketch ativo e `firmware/TCC.ino/TCC_Final/TCC_Final.ino`.
- O firmware le sensor baixo e alto, controla bomba, LED, chave fisica, MQTT e grava documentos nas colecoes `sensores` e `comandos`.
- Payload atual de `sensores`: `sensor`, `estado`, `timestamp`.
- Nao envia `device_id`, `event_id`, informacao de boot/restart, origem do evento ou confirmacao de bomba.
- Se o Wi-Fi estiver indisponivel ao enviar sensor/comando, o evento e perdido; nao ha buffer offline.
- As URLs Firestore, chave Firebase Web/API e Wi-Fi estao hardcoded no sketch. Os valores nao sao reproduzidos aqui.
- O MQTT usa TCP em `broker.hivemq.com:1883`, enquanto o frontend usa WebSocket seguro no mesmo broker publico.
- O firmware nao publica claramente `bomba/estado` no fluxo lido pelo frontend.

### Firebase Functions

- `functions/` agora existe como projeto Firebase Functions v2 em TypeScript.
- `firebase.json` define `functions` como source, runtime `nodejs22`, predeploy de build e portas basicas de emuladores.
- `.firebaserc.example` foi criado apenas como modelo; `.firebaserc` real ainda depende do project id/alias Firebase aprovado pelo usuario.
- `functions/src/index.ts` exporta `onSensorCreated` com trigger `onDocumentCreated` em `sensores/{docId}`, retry habilitado, timeout curto, logs estruturados e chamada ao backend.
- `functions/src/payload.ts` concentra a conversao do documento Firestore para o payload enriquecido do contrato `ATV-002`.
- `functions/src/config.ts` centraliza parametros/secrets, incluindo `BACKEND_SENSOR_EVENT_URL`, `SENSOR_EVENT_WEBHOOK_SECRET` e `FUNCTION_REGION`.
- Pela documentacao atual, Firestore triggers `onDocumentCreated` existem em Cloud Functions for Firebase v2.
- Para Firebase Functions em 2026-07-27, Node.js 22 e a escolha conservadora para Firebase; Node.js 20 ja aparece em janela de depreciacao no calendario de runtime.
- Foi escolhida uma versao estavel explicita de `firebase-functions` (`7.3.0`) em vez de uma RC publicada como candidata mais recente no npm.
- Build e testes locais passam; Firebase Emulator e deploy ainda nao foram executados porque dependem de Firebase CLI/projeto/secrets.

### IA

- `backend/app/services/llm.py` possui fachada simples para Ollama e OpenAI.
- `backend/app/services/agent_langchain.py` usa diretamente `ChatOllama` para classificar intencao e responder com calculos sobre Firestore.
- O provider configuravel (`LLM_PROVIDER`) so afeta `/llm/chat`, nao o agente analitico em `/agent`.
- Nao ha Gemini.
- Nao ha tratamento uniforme de timeout, indisponibilidade, quota, erro de autenticacao, fallback visivel, modelo respondente e telemetria entre provedores.
- Modelo local atual esperado: `qwen2:0.5b`.
- Candidato tecnico a segundo modelo, sujeito a aprovacao: `qwen3:4b-instruct`, Q4_K_M, cerca de 2.5 GB no Ollama, viavel para uma maquina com aproximadamente 8 GB livres. Nao deve ser baixado antes da aprovacao.

### Relatorios, consumo e mobile

- `GET /reports/weekly` e `GET /reports/monthly` retornam PDF via `FileResponse`.
- Os PDFs atuais sao simples, baseados em resumo por sensor e acao.
- Ha PDFs gerados versionados em `backend/generated/` e `backend/`.
- A tela de historico nao chama a API de relatorios.
- Estimativa de energia existe apenas como estado local no componente `EnergyEstimate`, sem persistencia e com preco/potencia hardcoded.
- Estimativa de agua existe apenas como mock em `QuickStats`, com capacidade hardcoded.
- Capacitor esta instalado e configurado, mas plataformas Android/iOS nao existem no projeto.

## Inconsistencias encontradas na auditoria inicial

- Server-side Firebase Function dentro de `frontend/src/services/alerts.ts`.
- `SensorEventIn` duplicado em `backend/app/schemas/dto.py`.
- Router duplicado `webhook_sensor.py` nao registrado.
- `ChatResponse` sem `session_id`, apesar do router retornar esse campo.
- AutoCloud atual analisa eventos, nao ciclos de enchimento.
- Backend de alerta nao recebe `document_id` e nao consegue ser idempotente por documento Firestore.
- `fetch_sensor_events` ativo nao inclui `doc.id`, prejudicando rastreabilidade.
- Alertas persistidos nao seguem modelo padronizado.
- `useWaterSystem.ts` tem conflito de tipo `PumpMode`.
- Componentes UI importam pacotes com versao no nome do modulo, quebrando `tsc`.
- `alerts.ts` entra no build frontend e quebra tipagem.
- Historico, volume de agua e consumo energetico ainda dependem de mocks.
- Cypress ainda testa tela inicial padrao do Ionic, nao o AquaMonitor atual.
- README menciona `TCC_2_sensores`, mas o arquivo aparece removido no worktree.
- `.venv` do backend nao parece executavel no Windows atual.

## Ordem tecnica recomendada

Atualizacao apos implementacao local de `ATV-008`, `ATV-009`, `ATV-010` e `ATV-011`:

1. `ATV-015` + `ATV-017`: definir estado confirmado da bomba via MQTT e usar esse contrato para estimar energia.
2. `ATV-016` + `ATV-018`: calcular consumo de agua a partir dos ciclos validos e melhorar relatorios/download no historico.
3. `ATV-014`: adicionar buffer offline no firmware usando `event_id`/idempotencia ja disponiveis.
4. `ATV-013`: organizar configuracoes e secrets por ambiente antes de mobile/deploy real.
5. `ATV-019` + `ATV-020` + `ATV-021` + `ATV-022`: refatorar provedores LLM, integrar Gemini/modelo Ollama aprovado e melhorar prompt/sessoes.
6. `ATV-023`: refinar interface quando dados reais de alertas, bomba, consumo e relatorios estiverem disponiveis.
7. `ATV-024`: configurar Android depois de ambiente, relatorios e URLs estarem estabilizados.

Justificativa: a baseline, o contrato de sensores, a autenticacao do webhook e a idempotencia ja foram implementados e commitados. As proximas atividades foram reordenadas para evitar dependencias ainda ausentes e reduzir retrabalho entre backend, Functions, firmware e frontend.

## Atividades que podem ser agrupadas

Grupos recomendados a partir do estado atual:

- Grupo concluido localmente: `ATV-003`, `ATV-005`, `ATV-006`, `ATV-008`, `ATV-009`, `ATV-010`, `ATV-011`, `ATV-012`. Observacao: aguardam validacao/commit do usuario; emulador Firebase segue como validacao pendente.
- Grupo A: `ATV-015`, `ATV-017`. Dependencias atendidas: nenhuma pendencia bloqueante. Observacao: energia depende de estado confirmado da bomba, entao `ATV-015` vem primeiro no mesmo lote.
- Grupo B: `ATV-016`, `ATV-018`. Dependencias atendidas para agua: `ATV-009`; idealmente concluir `ATV-017` antes de incluir energia completa nos relatorios.
- Grupo C: `ATV-014`. Dependencias atendidas: `ATV-002` e `ATV-007`. Observacao: pode ser feito isoladamente porque altera firmware e politica de buffer.
- Grupo D: `ATV-019`, `ATV-020`, `ATV-021`, `ATV-022`. Dependencia anterior: decisao do usuario sobre Gemini/modelo local antes de `ATV-020`/`ATV-021`. Observacao: `ATV-019` deve abrir esse lote.
- Grupo E: `ATV-013`, `ATV-024`. Dependencia anterior para Android: `ATV-013` e URL/HTTPS definidos. Observacao: configuracao por ambiente deve vir antes de validar mobile.
- Grupo F: `ATV-023`. Dependencias anteriores: alertas, bomba, consumo e relatorios integrados.

## Proxima atividade implementavel apos aprovacao

Primeiro grupo recomendado agora: `ATV-015` e `ATV-017`.

Motivo: o app ja exibe os alertas persistidos. O proximo passo mais seguro e estabilizar o estado confirmado da bomba antes de estimar energia e antes de incluir esse dado em relatorios.

## Backlog tecnico

### ATV-001 - Corrigir baseline de validacao e bloqueios de camada

- ID da atividade: `ATV-001`.
- Titulo: Corrigir baseline de validacao e bloqueios de camada.
- Pendencias relacionadas: Firebase Functions fora de camada, TypeScript quebrado, testes atuais nao representativos, venv backend inconsistente.
- Objetivo: deixar o projeto pronto para mudancas incrementais com validacoes basicas confiaveis.
- Contexto encontrado no codigo: `frontend/src/services/alerts.ts` contem Function server-side; `useWaterSystem.ts` conflita `PumpMode`; componentes `ui` usam imports versionados; backend `.venv` tem estrutura Linux; Cypress testa tela padrao Ionic.
- Situacao atual: implementada localmente apos validacao de baseline no Linux oficial.
- Proposta de solucao: retirar codigo de Function do `tsconfig` frontend ao criar `functions/`, corrigir imports versionados, resolver conflito de tipo, revisar teste Cypress inicial e documentar ambiente Python reproduzivel.
- Backend afetado: ambiente `.venv`, comandos de validacao, possivel README.
- Frontend afetado: `frontend/src/services/alerts.ts`, `frontend/src/hooks/useWaterSystem.ts`, `frontend/src/components/ui/*`, testes Cypress.
- Firmware afetado: nenhum nesta atividade.
- Firebase ou servicos externos afetados: nenhum deploy; apenas organizacao local.
- Contratos e payloads envolvidos: nenhum contrato funcional novo.
- Dependencias: aprovacao para mexer em arquivos de frontend/configuracao.
- Riscos: alterar componentes `ui` pode gerar efeitos visuais; deve ser feito mecanicamente.
- Perguntas pendentes: posso remover ou arquivar os componentes vazios e hook antigo em etapa futura, ou devemos manter ate estabilizar?
- Criterios de aceite: `npm exec tsc -- --noEmit` sem erros de camada; backend importavel em ambiente documentado; Cypress inicial alinhado a uma tela real ou marcado como pendente.
- Plano de testes: `npm exec tsc -- --noEmit`; `npm run lint`; import do backend com ambiente correto sem escrever bytecode.
- Arquivos provavelmente afetados: `frontend/src/services/alerts.ts`, `frontend/src/hooks/useWaterSystem.ts`, `frontend/src/components/ui/*`, `frontend/cypress/e2e/test.cy.ts`, `README.md`, `backend/.env.example`.
- Status: CONCLUIDO.
- Resultado da validacao local: backend importavel e compilavel; `tsc`, `lint`, `build` e Cypress inicial passaram no Linux. Permanecem apenas avisos nao bloqueantes de fast refresh em componentes `ui`, bundle grande e bases Browserslist/Baseline desatualizadas.
- Resultado da validacao do usuario: validado pelo usuario e commitado antes do inicio de `ATV-002`, `ATV-004` e `ATV-007`.

### ATV-002 - Definir contrato de evento de sensor e IDs

- ID da atividade: `ATV-002`.
- Titulo: Definir contrato de evento de sensor e IDs.
- Pendencias relacionadas: Firebase Functions, endpoint `/alerts/sensor-event`, idempotencia, buffer offline, AutoCloud, alertas.
- Objetivo: estabelecer o payload canonico de evento do sensor entre ESP32, Firestore, Function e backend.
- Contexto encontrado no codigo: firmware grava `sensor`, `estado`, `timestamp`; schema backend espera esses campos e `device_id` opcional; Function atual nao envia `document_id`.
- Situacao atual: implementada localmente com payload legado e enriquecido aceitos pelo backend.
- Proposta de solucao: definir payload com `document_id`, `sensor`, `estado`, `timestamp`, `device_id`, `received_at`, `source`, `event_id` opcional, `raw_path` e metadados de Function.
- Backend afetado: schemas e servico de processamento.
- Frontend afetado: tipos de historico e exibicao de alertas no futuro.
- Firmware afetado: envio futuro de `device_id` e `event_id`.
- Firebase ou servicos externos afetados: colecao `sensores`; nova colecao de controle de processamento.
- Contratos e payloads envolvidos:

```json
{
  "document_id": "firestore-doc-id",
  "sensor": "baixo",
  "estado": "desceu",
  "timestamp": "2026-07-27T12:00:00Z",
  "device_id": "esp32-reservatorio-01",
  "source": "firestore_on_create",
  "raw_path": "sensores/firestore-doc-id"
}
```

- Dependencias: confirmacao futura do nome oficial do dispositivo e se o firmware passara a gerar `event_id`.
- Riscos: mudar payload sem compatibilidade pode quebrar eventos existentes.
- Perguntas pendentes: qual deve ser o identificador oficial do ESP32? Podemos tratar `doc.id` como idempotency key inicial mesmo antes de firmware enviar `event_id`?
- Criterios de aceite: contrato documentado; backend aceita payload atual e payload enriquecido; campos obrigatorios e opcionais definidos.
- Plano de testes: validar evento baixo, alto, sem `device_id`, sem `timestamp`, `timestamp` string/Firestore convertido.
- Arquivos provavelmente afetados: `specs/*`, `backend/app/schemas/dto.py`, `backend/app/services/sensor_realtime.py`, `firmware/TCC.ino/TCC_Final/TCC_Final.ino`, `README.md`.
- Status: CONCLUIDO.
- Resultado da validacao local: schema consolidado em `SensorEventIn`, com `document_id`, `event_id`, `source`, `raw_path`, `received_at`, normalizacao de `sensor/estado`, timestamp padrao quando ausente e compatibilidade com payload legado. Testes `unittest` cobrem payload legado e identidade por `raw_path`/`document_id`.
- Resultado da validacao do usuario: validado pelo usuario e commitado junto com `ATV-004` e `ATV-007`.

### ATV-003 - Criar harness pytest para backend

- ID da atividade: `ATV-003`.
- Titulo: Criar harness pytest para backend.
- Pendencias relacionadas: testes de endpoints, alertas, anomalias, idempotencia, AutoCloud.
- Objetivo: permitir testes automatizados do backend antes de alterar regras de negocio.
- Contexto encontrado no codigo: apos `ATV-002`, `ATV-004` e `ATV-007` ja existiam testes de contrato em `backend/tests/test_sensor_event_webhook.py`, mas ainda faltavam `pytest`, configuracao propria de descoberta e execucao padronizada no Linux.
- Situacao atual: implementada localmente com `pytest`.
- Proposta de solucao: adicionar `pytest`, `pytest.ini`, adaptar os testes de contrato para fixtures pytest e manter mocks locais de processamento/Firestore.
- Backend afetado: `requirements.txt`, `tests/`, possivel ajuste de inicializacao.
- Frontend afetado: nenhum.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: mocks locais; sem chamadas reais.
- Contratos e payloads envolvidos: `POST /alerts/sensor-event`, retorno de alertas, schemas de evento.
- Dependencias: `ATV-002` para contrato final.
- Riscos: se os servicos continuarem acoplados ao Firebase Admin, os testes ficarao frageis.
- Perguntas pendentes: em etapa futura, vale separar dependencias de desenvolvimento em `requirements-dev.txt` se a lista de ferramentas de teste crescer.
- Criterios de aceite: `pytest` executa localmente sem credenciais reais; pelo menos testes de schema e endpoint com Firestore mockado.
- Plano de testes: `pytest`; testes de sucesso, payload invalido, segredo ausente/incorreto, payload legado, identidade do evento e duplicidade.
- Arquivos provavelmente afetados: `backend/requirements.txt`, `backend/pytest.ini`, `backend/tests/test_sensor_event_webhook.py`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: `pytest` passou com 8 testes sem credenciais reais. Os testes chamam schema, servico e router diretamente com mocks; `TestClient`/ASGI ficou como risco tecnico porque travou localmente mesmo em rota simples durante a investigacao.
- Resultado da validacao do usuario: _a preencher_.

### ATV-004 - Ajustar endpoint `/alerts/sensor-event` e autenticacao Function -> FastAPI

- ID da atividade: `ATV-004`.
- Titulo: Ajustar endpoint de processamento de eventos.
- Pendencias relacionadas: Firebase Functions, chamada autenticada ao backend, validacao logica, processamento AutoCloud, alertas.
- Objetivo: transformar o endpoint existente em uma porta robusta para eventos criados no Firestore.
- Contexto encontrado no codigo: endpoint existe em `alerts.py`, mas sem autenticacao, sem idempotencia, sem doc id e com schema duplicado.
- Situacao atual: implementada localmente com autenticacao configuravel por header.
- Proposta de solucao: consolidar schema, incluir `document_id`, validar `sensor/estado`, normalizar timestamp, exigir segredo/header ou assinatura configuravel, retornar `processed`, `duplicate`, `alerts_created`, `cycle_created`.
- Backend afetado: router, schema, service.
- Frontend afetado: nenhum direto.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: Function enviara header secreto; Firestore recebera registros de processamento/alertas.
- Contratos e payloads envolvidos:

```json
{
  "processed": true,
  "duplicate": false,
  "event_id": "sensores/doc-id",
  "alerts_created": [],
  "autocloud": {
    "used": false,
    "reason": "cycle_not_complete"
  }
}
```

- Dependencias: `ATV-002`, decisao de autenticacao.
- Riscos: segredo compartilhado simples e suficiente para TCC, mas inferior a IAM/OIDC; precisa documentacao clara.
- Perguntas pendentes: backend sera publico na internet, tunnel local, Cloud Run ou outro host?
- Criterios de aceite: endpoint rejeita payload invalido e chamada sem autenticacao; aceita evento valido; resposta e rastreavel.
- Plano de testes: TestClient com payload valido, invalido, sem header, header incorreto, duplicado.
- Arquivos provavelmente afetados: `backend/app/routers/alerts.py`, `backend/app/routers/webhook_sensor.py`, `backend/app/schemas/dto.py`, `backend/app/services/sensor_realtime.py`, `backend/.env.example`.
- Status: CONCLUIDO.
- Resultado da validacao local: endpoint exige `X-AquaMonitor-Webhook-Secret` quando `SENSOR_EVENT_WEBHOOK_SECRET` esta configurado, rejeita segredo ausente/incorreto, aceita payload valido e retorna `processed`, `duplicate`, `event_id`, `alerts_created`, `cycle_created` e `autocloud`. A Function em `functions/src/index.ts` envia o payload enriquecido e o header quando configurado.
- Resultado da validacao do usuario: validado pelo usuario e commitado junto com `ATV-002` e `ATV-007`.

### ATV-005 - Criar estrutura server-side `functions/`

- ID da atividade: `ATV-005`.
- Titulo: Criar estrutura Firebase Functions.
- Pendencias relacionadas: Firebase Functions, `frontend/src/services/alerts.ts`, secrets, emulador, ambientes.
- Objetivo: mover a responsabilidade server-side para uma pasta propria e fora do bundle frontend.
- Contexto encontrado no codigo: existia apenas `functions/src/index.js` como rascunho JS; ainda nao havia pacote Firebase Functions instalavel/testavel.
- Situacao atual: implementada localmente como projeto Firebase Functions v2 em TypeScript.
- Proposta de solucao: criar `functions/` em TypeScript, com `package.json`, `package-lock.json`, `src/index.ts`, `src/config.ts`, `src/payload.ts`, `test/`, `tsconfig.json`, `.env.example` sem secrets, scripts de build/test, `firebase.json` e `.firebaserc.example`.
- Backend afetado: apenas URL/contrato consumido.
- Frontend afetado: nenhum nesta atividade atual; o codigo server-side ja havia sido retirado do bundle frontend na baseline.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: Cloud Functions, Emulator Suite.
- Contratos e payloads envolvidos: trigger `sensores/{docId}` e chamada HTTP para backend.
- Dependencias: aprovacao para criar `functions/` e escolher versoes.
- Riscos: projeto Firebase pode exigir plano Blaze para deploy; emulador pode demandar Firebase CLI local.
- Perguntas pendentes: qual project alias usar em `.firebaserc` real? Por seguranca, a atividade criou apenas `.firebaserc.example`.
- Criterios de aceite: `functions` compila localmente; frontend nao inclui codigo de Functions; scripts documentados.
- Plano de testes: `npm --prefix functions run build`; teste unitario do conversor de payload; emulador planejado.
- Arquivos provavelmente afetados: `functions/package.json`, `functions/package-lock.json`, `functions/src/index.ts`, `functions/src/config.ts`, `functions/src/payload.ts`, `functions/test/*`, `functions/tsconfig.json`, `firebase.json`, `.firebaserc.example`, `.gitignore`, `README.md`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: `npm install`, `npm run build` e `npm test` passaram. O ambiente Linux oficial foi atualizado para Node.js 22.23.1 e npm 10.9.8; com essa versao, `npm install` em `functions/` passou sem avisos de engine.
- Resultado da validacao do usuario: _a preencher_.

### ATV-006 - Implementar trigger Firestore `onDocumentCreated`

- ID da atividade: `ATV-006`.
- Titulo: Implementar Function de novo evento em `sensores`.
- Pendencias relacionadas: fluxo ESP32 -> Firestore -> Function -> Backend.
- Objetivo: chamar automaticamente o backend quando novo documento entrar em `sensores`.
- Contexto encontrado no codigo: o rascunho JS foi preservado apenas para rastreabilidade, e a implementacao efetiva passou para `functions/src/index.ts`.
- Situacao atual: implementada localmente com trigger v2 testavel por build/unit tests.
- Proposta de solucao: usar `onDocumentCreated` v2 em `sensores/{docId}`, converter `Timestamp` corretamente, incluir `docId`, enviar para `BACKEND_SENSOR_EVENT_URL` por parametro/secret, timeout curto, retry, logs estruturados e erro controlado.
- Backend afetado: endpoint de recepcao.
- Frontend afetado: nenhum direto.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: Firestore trigger, Cloud Functions, Secret Manager/params.
- Contratos e payloads envolvidos: payload de `ATV-002`, header de autenticacao de `ATV-004`.
- Dependencias: `ATV-004`, `ATV-005`.
- Riscos: retentativas podem duplicar processamento se idempotencia nao existir; URL local precisa estrategia de desenvolvimento.
- Perguntas pendentes: ambiente local usara Firebase Emulator chamando backend local em `host.docker.internal`, ngrok/tunnel ou URL de homologacao?
- Criterios de aceite: criar documento no emulador dispara chamada; falha do backend gera log claro; chamada inclui chave idempotente.
- Plano de testes: build TypeScript; teste unitario do payload; emulador com evento baixo, alto, backend indisponivel, timeout e duas execucoes do mesmo doc.
- Arquivos provavelmente afetados: `functions/src/index.ts`, `functions/src/config.ts`, `functions/test/*`, `backend/.env.example`, `README.md`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: `npm run build` e `npm test` passaram. A Function monta payload com `document_id`, `event_id`, `raw_path`, `source`, `received_at`, timestamp normalizado e header secreto opcional. Firebase Emulator/deploy nao foram executados nesta etapa por dependerem de Firebase CLI, project alias real e configuracao de secrets.
- Resultado da validacao do usuario: _a preencher_.

### ATV-007 - Persistir processamento e garantir idempotencia

- ID da atividade: `ATV-007`.
- Titulo: Garantir idempotencia por documento/evento.
- Pendencias relacionadas: duplicidade de eventos, retentativas, Function executada duas vezes, alertas duplicados.
- Objetivo: impedir processamento e alerta duplicados para o mesmo evento.
- Contexto encontrado no codigo: backend processa tudo em memoria e grava alertas sem chave unica.
- Situacao atual: implementada localmente com reserva atomica em Firestore.
- Proposta de solucao: criar colecao `sensor_event_processing` ou documento em `processed_sensor_events/{event_id}`, com status, hash do payload, timestamps, alerts gerados e resultado.
- Backend afetado: `sensor_realtime`, Firestore service, schemas.
- Frontend afetado: nenhum direto.
- Firmware afetado: envio futuro de `event_id` melhora robustez.
- Firebase ou servicos externos afetados: nova colecao de controle.
- Contratos e payloads envolvidos: `event_id = sensores/{docId}` inicialmente; opcional `device_id:event_id` no futuro.
- Dependencias: `ATV-002`, `ATV-004`.
- Riscos: corrida concorrente se duas invocacoes processarem ao mesmo tempo; precisa transacao Firestore ou create atomico.
- Perguntas pendentes: podemos criar nova colecao no Firestore para controle tecnico?
- Criterios de aceite: segunda chamada do mesmo evento retorna `duplicate: true` e nao cria alerta novo.
- Plano de testes: duas chamadas simultaneas, duas chamadas sequenciais, payload mesmo doc diferente, falha apos reservar processamento.
- Arquivos provavelmente afetados: `backend/app/services/firestore.py`, `backend/app/services/sensor_realtime.py`, `backend/app/schemas/dto.py`, `backend/tests/*`.
- Status: CONCLUIDO.
- Resultado da validacao local: criada a colecao tecnica configuravel `sensor_event_processing`; o backend usa `DocumentReference.create()` como reserva atomica, grava status `processing`, `processed` ou `failed`, registra hash do payload e retorna `duplicate: true` sem reprocessar quando a chave ja existe. Teste unitario cobre que evento duplicado nao chama o motor de processamento.
- Resultado da validacao do usuario: validado pelo usuario e commitado junto com `ATV-002` e `ATV-004`.

### ATV-008 - Implementar regras logicas deterministicas dos sensores

- ID da atividade: `ATV-008`.
- Titulo: Regras deterministicas de sequencia dos sensores.
- Pendencias relacionadas: sensor baixo repetido antes do alto, alto seguido rapidamente por baixo, eventos duplicados/atrasados/fora de ordem.
- Objetivo: detectar anomalias logicas sem AutoCloud e sem diagnostico conclusivo.
- Contexto encontrado no codigo: regras antigas verificavam apenas incoerencias simples de estado baixo/alto dentro de `sensor_realtime.py` e `sensor_anomaly.py`.
- Situacao atual: implementada localmente com motor deterministico dedicado.
- Proposta de solucao: criar motor de regras configuravel que usa historico recente, timestamps, doc ids, tolerancias, janela de duplicidade e `MIN_PLAUSIBLE_DRAIN_TIME_SECONDS`.
- Backend afetado: novo servico ou refatoracao de `sensor_realtime.py` e `sensor_anomaly.py`.
- Frontend afetado: futuro consumo de alertas.
- Firmware afetado: melhora se enviar `device_id`/`event_id`.
- Firebase ou servicos externos afetados: leitura de eventos anteriores e escrita de alertas.
- Contratos e payloads envolvidos: alertas de tipos `duplicate_event`, `unexpected_low_repeat`, `implausible_drain_time`, `out_of_order_event`, `missing_timestamp`.
- Dependencias: `ATV-007`.
- Riscos: falsos positivos se o estado inicial da caixa for desconhecido; precisa severidade e hipoteses, nao diagnostico.
- Perguntas pendentes: qual intervalo minimo plausivel de alto -> baixo para o reservatorio real? O default local ficou em 60 segundos ate haver medicao real.
- Criterios de aceite: casos esperados geram alerta unico com causas possiveis e metadados; eventos invalidos nao alimentam AutoCloud.
- Plano de testes: cenarios 1 a 12 da lista obrigatoria, com fixtures cronologicas e fora de ordem.
- Arquivos provavelmente afetados: `backend/app/services/sensor_rules.py`, `backend/app/services/sensor_realtime.py`, `backend/app/services/sensor_anomaly.py`, `backend/.env.example`, `backend/tests/*`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: criado `sensor_rules.py` com alertas `duplicate_event`, `unexpected_low_repeat`, `implausible_drain_time`, `out_of_order_event`, `missing_timestamp` e inconsistencias fisicas adicionais. Eventos com alerta bloqueante nao alimentam ciclo nem analise temporal. Testes unitarios cobrem duplicidade, repeticao do sensor baixo, esvaziamento rapido, evento fora de ordem e timestamp ausente.
- Resultado da validacao do usuario: _a preencher_.

### ATV-009 - Extrair e validar ciclos de enchimento

- ID da atividade: `ATV-009`.
- Titulo: Ciclos validos de enchimento baixo -> alto.
- Pendencias relacionadas: AutoCloud temporal, consumo de agua, relatorios.
- Objetivo: transformar eventos confiaveis em ciclos com duracao de enchimento.
- Contexto encontrado no codigo: AutoCloud atual nao trabalha com ciclos; consumo de agua e energia sao mocks.
- Situacao atual: implementada localmente.
- Proposta de solucao: parear `baixo subiu` indicando inicio do trecho medido de enchimento com `alto subiu` indicando fim, validar ordem, timestamp, duplicidade e anomalias logicas antes de persistir ciclo.
- Backend afetado: servico de ciclos, Firestore service.
- Frontend afetado: historico e relatorios no futuro.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: possivel colecao `filling_cycles`.
- Contratos e payloads envolvidos:

```json
{
  "cycle_id": "baixoDocId:altoDocId",
  "start_event_id": "sensores/doc-baixo",
  "end_event_id": "sensores/doc-alto",
  "started_at": "2026-07-27T12:00:00Z",
  "ended_at": "2026-07-27T12:08:00Z",
  "fill_time_seconds": 480,
  "valid": true
}
```

- Dependencias: `ATV-008`.
- Riscos: sem estado inicial, primeiro ciclo pode ser incompleto; eventos fora de ordem exigem reprocessamento.
- Perguntas pendentes: confirmacao fisica em bancada ainda e desejavel, mas pelo firmware atual `baixo desceu` liga a bomba e `baixo subiu` representa a agua chegando ao sensor baixo; por isso o ciclo baixo -> alto usa `baixo subiu`.
- Criterios de aceite: ciclo completo valido persiste duracao; ciclo com evento invalido nao persiste como valido.
- Plano de testes: ciclo completo, baixo duplicado, alto sem baixo, baixo sem alto, timestamp ausente, fora de ordem.
- Arquivos provavelmente afetados: `backend/app/services/filling_cycles.py`, `backend/app/services/sensor_realtime.py`, `backend/tests/*`, `README.md`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: criado `filling_cycles.py` com extracao pura de ciclos, tracker em tempo real e persistencia deduplicada em `filling_cycles`. Testes cobrem ciclo completo `baixo subiu -> alto subiu`, evento invalido que nao alimenta ciclo e duracao negativa/fora de ordem rejeitada.
- Resultado da validacao do usuario: _a preencher_.

### ATV-010 - Integrar AutoCloud a analise temporal de enchimento

- ID da atividade: `ATV-010`.
- Titulo: AutoCloud para tempo de enchimento.
- Pendencias relacionadas: aumento gradual, mudanca persistente, ciclo lento, novo agrupamento distante.
- Objetivo: usar AutoCloud ou estrategia equivalente em cima de `fill_time_seconds`, nao eventos crus.
- Contexto encontrado no codigo: `AutoCloud` existe, mas usa atributos `[sensor, estado, delta_t]` e estado global de classe.
- Situacao atual: implementada localmente com pipeline temporal sobre `fill_time_seconds`.
- Proposta de solucao: criar pipeline temporal que recebe ciclos validos, define minimo de dados, linha de base, outliers, inferencia e explicacao do resultado.
- Backend afetado: `autocloud_core.py`, novo servico temporal, alertas.
- Frontend afetado: exibicao de explicacoes e alertas.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: colecoes `filling_cycles`, `alerts`, possivel `autocloud_models` ou snapshots.
- Contratos e payloads envolvidos: alertas `slow_fill_cycle`, `persistent_fill_time_shift`, `new_fill_time_cluster`.
- Dependencias: `ATV-009`.
- Riscos: poucos dados podem gerar ruido; por isso a implementacao retorna `insufficient_data` antes de atingir a amostra minima configurada.
- Perguntas pendentes: quantos ciclos historicos reais existem hoje para calibrar? Podemos reprocessar historico?
- Criterios de aceite: com poucos dados, resposta e `insufficient_data`; com aumento gradual fixture, alerta e explicacao aparecem; eventos invalidos nao entram.
- Plano de testes: cenarios 13 a 15 obrigatorios, dataset pequeno, dataset normal, dataset com tendencia, reprocessamento historico.
- Arquivos provavelmente afetados: `backend/app/services/autocloud_fill_time.py`, `backend/app/services/filling_cycles.py`, `backend/tests/*`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: criado `autocloud_fill_time.py` com linha de base temporal para ciclos validos, retorno `insufficient_data`, alertas `slow_fill_cycle`, `persistent_fill_time_shift` e `new_fill_time_cluster`. Testes cobrem poucos dados, ciclo lento e aumento persistente.
- Resultado da validacao do usuario: _a preencher_.

### ATV-011 - Persistir e consultar alertas inteligentes

- ID da atividade: `ATV-011`.
- Titulo: Modelo persistente de alertas e consulta.
- Pendencias relacionadas: alertas no aplicativo, anomalias, nao repetir alerta para mesmo evento.
- Objetivo: padronizar alertas para backend e frontend.
- Contexto encontrado no codigo: `sensor_realtime.py` gravava dicionarios livres em `alerts`; frontend ainda nao le alertas persistidos.
- Situacao atual: implementada localmente no backend; exibicao no frontend foi implementada em `ATV-012`.
- Proposta de solucao: criar schema de alerta com `id`, `event_id`, `type`, `severity`, `title`, `message`, `detected_at`, `sensor_timestamp`, `status`, `possible_causes`, `metadata`, `acknowledged`, `acknowledged_at`.
- Backend afetado: schemas, service de alertas, rotas GET/PATCH.
- Frontend afetado: service HTTP, hook e painel implementados em `ATV-012`.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: colecao `alerts`.
- Contratos e payloads envolvidos:

```json
{
  "event_id": "sensores/doc-id",
  "type": "unexpected_low_repeat",
  "severity": "warning",
  "title": "Sequencia suspeita de sensor baixo",
  "possible_causes": ["leitura duplicada", "ruido", "evento fora de ordem"],
  "status": "open",
  "acknowledged": false
}
```

- Dependencias: `ATV-008`.
- Riscos: excesso de alertas pode prejudicar UX; precisa deduplicacao.
- Perguntas pendentes: alertas devem ser apenas in-app ou tambem push notification?
- Criterios de aceite: alerta unico por evento/tipo; consulta por status/severidade; acknowledge persistido.
- Plano de testes: alerta criado, duplicidade bloqueada, ack, listagem por periodo.
- Arquivos provavelmente afetados: `backend/app/routers/alerts.py`, `backend/app/schemas/dto.py`, `backend/app/services/alerts_store.py`, `backend/tests/*`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: criado `alerts_store.py` com id estavel por `event_id:type`, normalizacao de alerta, persistencia deduplicada por `DocumentReference.create()`, consulta por periodo/status/severidade e acknowledge. Foram adicionadas rotas `GET /alerts` e `PATCH /alerts/{alert_id}/ack`. Testes cobrem id estavel e defaults do modelo.
- Resultado da validacao do usuario: _a preencher_.

### ATV-012 - Exibir alertas em tempo real no aplicativo

- ID da atividade: `ATV-012`.
- Titulo: Alertas inteligentes no frontend.
- Pendencias relacionadas: alertas no aplicativo, estados de loading/erro, responsividade.
- Objetivo: mostrar anomalias detectadas sem depender de alertas de nivel mockados.
- Contexto encontrado no codigo: `WaterLevelAlert` usa apenas percentual mockado; app nao consumia alertas persistidos.
- Situacao atual: implementada localmente consumindo o backend.
- Proposta de solucao: criar service/hook para alertas, resumo no dashboard, lista com severidade e status, acao de reconhecer alerta.
- Backend afetado: rotas de alerta persistido e testes de endpoints.
- Frontend afetado: HomePage, services/hooks, componentes.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: colecao `alerts` acessada pelo backend; frontend usa API backend.
- Contratos e payloads envolvidos: modelo de `ATV-011`.
- Dependencias: `ATV-011`, `ATV-001`.
- Riscos: polling nao e realtime puro; para TCC e suficiente sem duplicar leitura Firestore no app.
- Perguntas pendentes: intervalo de polling deve permanecer em 15 segundos ou ser ajustado para ambiente de banca?
- Criterios de aceite: novo alerta aparece sem reload; duplicados nao aparecem; usuario pode reconhecer alerta.
- Plano de testes: pytest dos endpoints, `tsc`, `lint`, `build`, estado sem alertas, erro de conexao e reconhecimento.
- Arquivos provavelmente afetados: `frontend/src/services/alerts.ts`, `frontend/src/hooks/useAlerts.ts`, `frontend/src/components/IntelligentAlertsPanel.tsx`, `frontend/src/pages/HomePage.tsx`, `backend/tests/test_alert_endpoints.py`.
- Status: AGUARDANDO VALIDACAO.
- Resultado da validacao local: criado painel `IntelligentAlertsPanel` na Home, hook `useAlerts` com polling de 15 segundos, service HTTP para `GET /alerts` e `PATCH /alerts/{alert_id}/ack`, estados de loading/erro/vazio e acao de reconhecer alerta. O backend foi ajustado para expor as rotas sob `/alerts`, limitar chamadas Firestore, retornar `503` claro em falhas de credencial/conectividade e pytest cobre registro das rotas, chamadas diretas dos endpoints e falhas operacionais do Firestore.
- Resultado da validacao do usuario: _a preencher_.

### ATV-013 - Organizar configuracoes e secrets por ambiente

- ID da atividade: `ATV-013`.
- Titulo: Configuracoes por ambiente e reducao de hardcodes.
- Pendencias relacionadas: Firebase, MQTT, Wi-Fi, backend URL, secrets de Functions, backend, frontend e firmware.
- Objetivo: separar configuracao publica de segredo e documentar ambientes.
- Contexto encontrado no codigo: Firebase Web config, chave API e URLs em frontend/firmware; backend usa env; MQTT hardcoded.
- Situacao atual: parcialmente implementado no backend, hardcoded no frontend/firmware.
- Proposta de solucao: criar `.env.example` para frontend/functions, validar env no bootstrap, documentar que `VITE_*` e publico, mover secrets reais para Secret Manager/backend env/firmware strategy.
- Backend afetado: `.env.example`, validacao de settings.
- Frontend afetado: `firestoreConfig.ts`, `mqttService.ts`, `aiService.ts`.
- Firmware afetado: estrategia de `secrets.h` ignorado ou configuracao por build, sem versionar valores.
- Firebase ou servicos externos afetados: regras Firestore, dominios autorizados, restricao de chave, App Check planejado.
- Contratos e payloads envolvidos: nenhum payload novo; contratos de configuracao.
- Dependencias: nenhuma, mas deve evitar quebrar ambiente atual.
- Riscos: mover para `.env` nao torna Firebase Web secreto; risco e regra/permissao.
- Perguntas pendentes: quais ambientes deseja manter: local, homologacao e producao? Existe dominio final do app?
- Criterios de aceite: nenhum valor sensivel novo versionado; `.env.example` completo; app falha com mensagem clara se env obrigatoria faltar.
- Plano de testes: iniciar frontend/backend com env example adaptado; verificar bundle sem segredos administrativos; revisar `.gitignore`.
- Arquivos provavelmente afetados: `.gitignore`, `backend/.env.example`, `frontend/.env.example`, `functions/.env.example`, `frontend/src/services/firestoreConfig.ts`, `frontend/src/services/mqttService.ts`, `firmware/TCC.ino/TCC_Final/*`, `README.md`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-014 - Implementar buffer offline limitado no ESP32

- ID da atividade: `ATV-014`.
- Titulo: Buffer offline limitado no firmware.
- Pendencias relacionadas: perda de eventos, reconexao, deduplicacao, IDs unicos.
- Objetivo: evitar perda de eventos quando Wi-Fi/Firestore estiver indisponivel, sem crescimento ilimitado.
- Contexto encontrado no codigo: `enviarDadosFirestore` e `enviarComandoFirestore` retornam se Wi-Fi estiver desconectado.
- Situacao atual: nao implementado.
- Proposta de solucao: fila circular estatica em RAM inicialmente, com capacidade definida apos estimativa de memoria; opcional NVS/LittleFS depois.
- Backend afetado: deduplicacao por `event_id`.
- Frontend afetado: nenhum direto.
- Firmware afetado: estrutura de eventos pendentes, retry/backoff, flush em ordem, logs seriais.
- Firebase ou servicos externos afetados: Firestore recebera eventos atrasados com timestamp original.
- Contratos e payloads envolvidos: `event_id`, `device_id`, `created_at_device`, `sent_at`.
- Dependencias: `ATV-002`, `ATV-007`.
- Riscos: fragmentacao de heap se usar `String` em excesso; timestamps antes do NTP podem ser invalidos; buffer cheio exige politica clara.
- Perguntas pendentes: prefere descartar evento mais antigo ou rejeitar evento novo quando o buffer encher?
- Criterios de aceite: offline armazena ate N eventos; reconexao reenvia em ordem; limite nao e ultrapassado; logs indicam descarte.
- Plano de testes: simular Wi-Fi offline, reconectar, atingir limite, reiniciar, timestamp sem NTP.
- Arquivos provavelmente afetados: `firmware/TCC.ino/TCC_Final/TCC_Final.ino`, possivel `firmware/TCC.ino/TCC_Final/secrets.h.example`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-015 - Definir contrato MQTT e confirmacao real da bomba

- ID da atividade: `ATV-015`.
- Titulo: Contrato MQTT e estado real da bomba.
- Pendencias relacionadas: comando enviado versus bomba realmente ligada, consumo eletrico, feedback de comando.
- Objetivo: separar comando desejado, comando aplicado e estado confirmado.
- Contexto encontrado no codigo: frontend publica `<nome> ligar/desligar`; firmware assina `bomba/controle`; frontend escuta `bomba/estado`, mas firmware nao publica estado de forma clara.
- Situacao atual: parcialmente implementado.
- Proposta de solucao: manter payload texto por compatibilidade e planejar payload JSON opcional versionado; firmware publica `bomba/estado` com estado, origem e confirmacao.
- Backend afetado: possivel ingestao futura de eventos de bomba.
- Frontend afetado: `mqttService`, `useWaterSystem`, feedback de comando.
- Firmware afetado: callback MQTT e publish de estado.
- Firebase ou servicos externos afetados: topicos MQTT; possivel colecao `comandos`.
- Contratos e payloads envolvidos:

```json
{
  "pump_on": true,
  "mode": "manual mqtt",
  "confirmed": true,
  "source": "mqtt",
  "timestamp": "2026-07-27T12:00:00Z"
}
```

- Dependencias: nenhuma obrigatoria, mas ajuda `ATV-016`.
- Riscos: alterar payload MQTT sem compatibilidade quebra firmware/app.
- Perguntas pendentes: podemos manter texto legado e adicionar JSON em topico novo, por exemplo `bomba/controle/v2`?
- Criterios de aceite: app distingue comando pendente, confirmado e falho; firmware publica estado ao mudar bomba.
- Plano de testes: comando ligar/desligar, fisico ativo ignora remoto, status pin nao confirma, MQTT desconectado.
- Arquivos provavelmente afetados: `frontend/src/services/mqttService.ts`, `frontend/src/hooks/useWaterSystem.ts`, `firmware/TCC.ino/TCC_Final/TCC_Final.ino`, `README.md`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-016 - Estimar consumo de agua e custo

- ID da atividade: `ATV-016`.
- Titulo: Estimativa de consumo de agua.
- Pendencias relacionadas: volume entre sensores, consumo diario/semanal/mensal, custo em reais.
- Objetivo: calcular consumo estimado a partir de ciclos validos.
- Contexto encontrado no codigo: `QuickStats` usa capacidade total mockada; relatorios nao calculam consumo.
- Situacao atual: nao implementado de forma real.
- Proposta de solucao: configurar `RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS` e `WATER_PRICE_PER_CUBIC_METER_BRL`, calcular ciclos validos por periodo e converter litros para metros cubicos.
- Backend afetado: servico de consumo, relatorios, agente.
- Frontend afetado: dashboard/historico.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: `filling_cycles`.
- Contratos e payloads envolvidos: resumo de consumo por periodo.
- Dependencias: `ATV-009`.
- Riscos: estimativa simples nao cobre tarifa por faixa ou perdas; precisa documentar limitacao.
- Perguntas pendentes: qual volume real entre sensores? A tarifa de agua e por m3, fixa ou por faixa?
- Criterios de aceite: calculo usa litros -> m3 corretamente; periodos sem dados retornam zero/sem dados; unidade aparece documentada.
- Plano de testes: 1 ciclo, multiplos ciclos, periodo vazio, preco por m3.
- Arquivos provavelmente afetados: `backend/app/services/consumption.py`, `backend/.env.example`, `frontend/src/pages/HistoryPage.tsx`, `frontend/src/components/QuickStats.tsx`, `README.md`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-017 - Estimar consumo eletrico da bomba

- ID da atividade: `ATV-017`.
- Titulo: Estimativa de energia e custo da bomba.
- Pendencias relacionadas: potencia da bomba, tempo ligado, custo kWh, relatorios.
- Objetivo: calcular energia com base no tempo real confirmado de bomba ligada.
- Contexto encontrado no codigo: `EnergyEstimate` calcula localmente por sessao com 750 W e preco fixo; firmware registra comandos em `comandos`.
- Situacao atual: parcialmente implementado como mock/local.
- Proposta de solucao: definir `PUMP_POWER_KW` e `ELECTRICITY_PRICE_PER_KWH_BRL`, derivar intervalos ligado/desligado de eventos confirmados, calcular kWh e custo.
- Backend afetado: servico de energia, relatorios, agente.
- Frontend afetado: `EnergyEstimate`, historico.
- Firmware afetado: publicar/registrar estado real confirmado.
- Firebase ou servicos externos afetados: `comandos` ou nova colecao `pump_events`.
- Contratos e payloads envolvidos: evento de bomba `on/off`, origem, confirmado, timestamp.
- Dependencias: `ATV-015`.
- Riscos: comandos nao equivalem a funcionamento real; sem confirmacao, calculo e apenas estimativa fraca.
- Perguntas pendentes: qual potencia nominal da bomba em kW? Existe medicao real de status confiavel?
- Criterios de aceite: energia = potencia kW x horas; custo = kWh x preco; periodos incompletos tratados explicitamente.
- Plano de testes: liga/desliga normal, ligado antes do periodo, desligado depois do periodo, comando sem confirmacao.
- Arquivos provavelmente afetados: `backend/app/services/energy.py`, `frontend/src/components/EnergyEstimate.tsx`, `firmware/TCC.ino/TCC_Final/TCC_Final.ino`, `README.md`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-018 - Melhorar relatorios PDF e download no historico

- ID da atividade: `ATV-018`.
- Titulo: Relatorios PDF e download pelo app.
- Pendencias relacionadas: endpoints existentes, PDF visual, historico, mobile.
- Objetivo: gerar relatorios uteis e permitir download/compartilhamento pela tela de historico.
- Contexto encontrado no codigo: backend gera PDF simples; frontend tem botao mock; PDFs estao em `backend/generated`.
- Situacao atual: parcialmente implementado no backend e mockado no frontend.
- Proposta de solucao: melhorar layout PDF com cabecalho, periodo, resumo, tabelas, alertas, consumo de agua/energia e estados sem dados; frontend chama API e baixa arquivo.
- Backend afetado: `reports.py`, `pdf.py`, services de resumo.
- Frontend afetado: `HistoryPage`, `aiService` ou novo `reportService`.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: Firestore para eventos/alertas/ciclos.
- Contratos e payloads envolvidos: `GET /reports/weekly?period=7d|30d|90d`, `GET /reports/monthly`, possivel endpoint parametrizado futuro.
- Dependencias: `ATV-016`, `ATV-017` para indicadores completos, mas pode iniciar antes com dados existentes.
- Riscos: download em mobile Capacitor exige tratamento diferente de navegador.
- Perguntas pendentes: relatorio deve ser sempre PDF gerado sob demanda ou armazenado/reutilizado?
- Criterios de aceite: botao PDF baixa/abre arquivo; PDF identifica periodo e data; periodo sem dados nao quebra.
- Plano de testes: geracao 7d/30d/90d, sem dados, download navegador, mobile planejado.
- Arquivos provavelmente afetados: `backend/app/routers/reports.py`, `backend/app/services/pdf.py`, `frontend/src/pages/HistoryPage.tsx`, `frontend/src/services/reportService.ts`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-019 - Abstrair provedores LLM do backend

- ID da atividade: `ATV-019`.
- Titulo: Abstracao `LLMProvider`.
- Pendencias relacionadas: Ollama fraco, Gemini, fallback, sessoes, provedor selecionavel.
- Objetivo: desacoplar o chatbot de um unico provedor.
- Contexto encontrado no codigo: `/llm/chat` usa `llm.py` com Ollama/OpenAI; `/agent` usa `ChatOllama` diretamente.
- Situacao atual: parcialmente implementado.
- Proposta de solucao: criar interface comum para `OllamaProvider`, `OpenAIProvider` existente e futuro `GeminiProvider`; fazer agente analitico usar essa camada ou separar classificador deterministico/LLM.
- Backend afetado: `llm.py`, `agent_langchain.py`, schemas de resposta.
- Frontend afetado: `aiService`, ChatPage se exibir modelo/provedor.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: Ollama local, OpenAI opcional, Gemini futuro.
- Contratos e payloads envolvidos: resposta deve incluir `provider`, `model`, `session_id`, erro/fallback visivel.
- Dependencias: `ATV-001` para build frontend; nenhuma para backend.
- Riscos: modelos diferentes podem nao suportar structured output igual ao LangChain atual.
- Perguntas pendentes: o agente analitico deve sempre usar LLM ou podemos priorizar regras deterministicas para intencoes conhecidas?
- Criterios de aceite: provider selecionado por env; resposta identifica provider/model; indisponibilidade retorna erro claro.
- Plano de testes: provider Ollama mock, provider indisponivel, `/llm/chat`, `/agent`, sessoes.
- Arquivos provavelmente afetados: `backend/app/services/llm.py`, `backend/app/services/agent_langchain.py`, `backend/app/schemas/dto.py`, `frontend/src/services/aiService.ts`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-020 - Integrar Gemini via Google AI Studio

- ID da atividade: `ATV-020`.
- Titulo: GeminiProvider no backend.
- Pendencias relacionadas: Google AI Studio/Gemini, chave em env, timeout, quota, autenticacao.
- Objetivo: adicionar Gemini como provedor selecionavel pelo backend sem expor chave no frontend.
- Contexto encontrado no codigo: nao ha Gemini; `requirements.txt` nao possui SDK Google GenAI especifico.
- Situacao atual: nao implementado.
- Proposta de solucao: adicionar provider Gemini com `GEMINI_API_KEY`, `GEMINI_MODEL`, timeout, tratamento de 401/403/429/5xx, logs e metadata de modelo.
- Backend afetado: provider LLM, requirements, env example.
- Frontend afetado: apenas exibir provider/model se disponivel.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: API Gemini.
- Contratos e payloads envolvidos: mesmo contrato de chat de `ATV-019`.
- Dependencias: `ATV-019`.
- Riscos: custos/quota; modelo especifico pode mudar; fallback silencioso e proibido.
- Perguntas pendentes: qual modelo Gemini aprovar para uso inicial? Candidato conservador deve ser escolhido no momento da implementacao a partir dos modelos oficiais disponiveis.
- Criterios de aceite: `LLM_PROVIDER=gemini` responde; chave ausente retorna erro claro; limite/quota tratado; frontend nao recebe chave.
- Plano de testes: mock HTTP/SDK para sucesso, timeout, 401, 429, fallback aprovado/desativado.
- Arquivos provavelmente afetados: `backend/app/services/llm.py`, `backend/requirements.txt`, `backend/.env.example`, `README.md`.
- Status: AGUARDANDO RESPOSTA.
- Resultado da validacao do usuario: _a preencher_.

### ATV-021 - Selecionar e configurar segundo modelo Ollama

- ID da atividade: `ATV-021`.
- Titulo: Segundo modelo Ollama mais potente.
- Pendencias relacionadas: modelo local atual fraco, 8 GB de RAM, familia Qwen.
- Objetivo: permitir alternar entre modelo leve e modelo local mais capaz.
- Contexto encontrado no codigo: `OLLAMA_MODEL=qwen2:0.5b` e `ChatOllama` usam env.
- Situacao atual: suporte basico por env existe, mas sem orientacao de modelo e sem fallback.
- Proposta de solucao: aprovar modelo antes de baixar. Candidato inicial: `qwen3:4b-instruct`, Q4_K_M, cerca de 2.5 GB no Ollama, melhor qualidade esperada que 0.5B, ainda viavel em 8 GB livres; comando proposto somente apos aprovacao: `ollama pull qwen3:4b-instruct`.
- Backend afetado: env example e documentacao; possivel ajuste de prompt/contexto.
- Frontend afetado: nenhum direto.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: Ollama local.
- Contratos e payloads envolvidos: `OLLAMA_MODEL`, `OLLAMA_BASE_URL`.
- Dependencias: `ATV-019` recomendada.
- Riscos: desempenho pode ser lento; memoria real depende do sistema, contexto e quantizacao; qualidade tambem depende de prompt e dados.
- Perguntas pendentes: a maquina alvo tem GPU ou apenas CPU? Aceita latencia maior em troca de qualidade?
- Criterios de aceite: modelo aprovado documentado; troca por env; sem download automatico nesta etapa.
- Plano de testes: perguntas analiticas conhecidas, indisponibilidade Ollama, comparacao com modelo atual.
- Arquivos provavelmente afetados: `backend/.env.example`, `README.md`, possivelmente `backend/app/services/agent_langchain.py`.
- Status: AGUARDANDO RESPOSTA.
- Resultado da validacao do usuario: _a preencher_.

### ATV-022 - Melhorar prompt, contexto e sessoes do chatbot

- ID da atividade: `ATV-022`.
- Titulo: Qualidade do chatbot e agente analitico.
- Pendencias relacionadas: baixa capacidade de contexto, respostas insatisfatorias, historico de conversa.
- Objetivo: melhorar resposta antes de atribuir o problema apenas ao tamanho do modelo.
- Contexto encontrado no codigo: ChatPage usa `/agent`; `/llm/chat` persiste sessoes, mas nao e o fluxo principal da tela; agente busca Firestore e monta respostas deterministicas apos classificar intencao.
- Situacao atual: parcialmente implementado.
- Proposta de solucao: unificar ou coordenar sessao do ChatPage, adicionar contexto de sistema, limitar historico, recuperar dados relevantes e separar chatbot generico de agente analitico.
- Backend afetado: `chat.py`, `chat_store.py`, `agent_langchain.py`, `llm.py`.
- Frontend afetado: `ChatPage`, `aiService`.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: `chat_sessions`.
- Contratos e payloads envolvidos: `session_id`, mensagens, `intent`, `provider`, `model`.
- Dependencias: `ATV-019`.
- Riscos: historico grande pode afetar latencia; dados sensiveis nao devem ser enviados para provedor externo sem aprovacao.
- Perguntas pendentes: Gemini/OpenAI podem receber dados reais do sistema ou somente resumos anonimizados?
- Criterios de aceite: sessao preservada; respostas indicam periodo/dados usados; erro de backend exibido com clareza.
- Plano de testes: reabrir sessao, perguntas de resumo, perguntas fora de escopo, backend/LLM indisponivel.
- Arquivos provavelmente afetados: `backend/app/routers/chat.py`, `backend/app/services/chat_store.py`, `backend/app/services/agent_langchain.py`, `frontend/src/pages/ChatPage.tsx`, `frontend/src/services/aiService.ts`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-023 - Refinar interface do aplicativo

- ID da atividade: `ATV-023`.
- Titulo: Melhorias esteticas e funcionais do frontend.
- Pendencias relacionadas: HomePage, HistoryPage, ChatPage, responsividade, loading, erros, sem dados, acessibilidade.
- Objetivo: substituir mocks por estados reais e melhorar UX sem reescrita visual completa.
- Contexto encontrado no codigo: dashboard usa nivel mock; historico usa graficos mockados; chat tem estado local; QuickHelp contem textos de guia; alguns componentes vazios.
- Situacao atual: parcialmente implementado.
- Proposta de solucao: definir estados de carregamento/erro/sem dados, feedback de comando MQTT, componentes de alertas, remover mocks progressivamente e validar mobile.
- Backend afetado: APIs de dados para historico/alertas.
- Frontend afetado: paginas, hooks, services, componentes.
- Firmware afetado: nenhum direto.
- Firebase ou servicos externos afetados: Firestore/MQTT.
- Contratos e payloads envolvidos: eventos sensores, alertas, relatorios, estado bomba.
- Dependencias: `ATV-011`, `ATV-012`, `ATV-015`, `ATV-016`, `ATV-017`.
- Riscos: redesenho amplo pode atrasar funcionalidades principais; priorizar ajustes guiados por dados reais.
- Perguntas pendentes: qual tela sera usada na apresentacao principal do TCC?
- Criterios de aceite: sem mocks nos indicadores principais quando houver dados; estados vazios claros; layout sem quebra em telas pequenas.
- Plano de testes: `npm run build` apos baseline, testes manuais em 360px/768px/desktop, Playwright/Cypress futuro.
- Arquivos provavelmente afetados: `frontend/src/pages/*`, `frontend/src/hooks/*`, `frontend/src/components/*`, `frontend/src/services/*`.
- Status: PENDENTE.
- Resultado da validacao do usuario: _a preencher_.

### ATV-024 - Configurar e validar Android com Capacitor

- ID da atividade: `ATV-024`.
- Titulo: Portabilidade inicial para Android.
- Pendencias relacionadas: mobile, Capacitor, backend URL, HTTPS, downloads, notificacoes, MQTT.
- Objetivo: gerar e testar uma primeira versao Android sem recriar plataforma existente.
- Contexto encontrado no codigo: Capacitor instalado; `capacitor.config.ts` tem `appId` generico; nao ha `frontend/android`.
- Situacao atual: parcialmente configurado, plataforma ausente.
- Proposta de solucao: apos build frontend estabilizado, adicionar Android se aprovado, configurar appId/nome, URLs por ambiente, permissoes de rede e estrategia de download.
- Backend afetado: CORS/HTTPS e URL publica.
- Frontend afetado: Capacitor config, download de relatorios, notificacoes futuras.
- Firmware afetado: nenhum.
- Firebase ou servicos externos afetados: Firebase client, MQTT WebSocket, possivel push notification.
- Contratos e payloads envolvidos: nenhum novo, mas depende de URLs por ambiente.
- Dependencias: `ATV-001`, `ATV-013`, `ATV-018`.
- Riscos: Android exige JDK/Android Studio local; HTTP sem HTTPS pode falhar em dispositivo fisico; broker publico pode ser instavel.
- Perguntas pendentes: qual package id definitivo do app? O backend tera HTTPS acessivel pelo celular?
- Criterios de aceite: `npx cap add android` apenas se pasta nao existir e com aprovacao; build sincronizado; app abre em emulador/dispositivo.
- Plano de testes: build frontend, `npx cap sync android`, abrir Android Studio, testar rede, download, MQTT.
- Arquivos provavelmente afetados: `frontend/capacitor.config.ts`, `frontend/android/*` se aprovado, `README.md`.
- Status: AGUARDANDO RESPOSTA.
- Resultado da validacao do usuario: _a preencher_.

## Matriz de testes obrigatorios

| Cenario | Atividades principais |
| --- | --- |
| 1. Novo evento valido de sensor baixo | ATV-002, ATV-004, ATV-006, ATV-008 |
| 2. Novo evento valido de sensor alto | ATV-002, ATV-004, ATV-006, ATV-008 |
| 3. Ciclo completo de enchimento | ATV-009, ATV-010, ATV-016 |
| 4. Evento de sensor baixo duplicado | ATV-007, ATV-008 |
| 5. Sensor baixo repetido antes do sensor alto | ATV-008, ATV-011 |
| 6. Sensor alto seguido rapidamente por sensor baixo | ATV-008, ATV-011 |
| 7. Eventos recebidos fora de ordem | ATV-008, ATV-009 |
| 8. Evento sem timestamp | ATV-002, ATV-004, ATV-008 |
| 9. Firebase Function executada duas vezes para o mesmo documento | ATV-006, ATV-007 |
| 10. Backend indisponivel | ATV-006 |
| 11. Timeout ao chamar backend | ATV-006 |
| 12. Retentativa sem duplicar alerta | ATV-006, ATV-007, ATV-011 |
| 13. AutoCloud sem quantidade minima de dados | ATV-010 |
| 14. AutoCloud com aumento gradual no tempo de enchimento | ATV-010 |
| 15. Evento invalido que nao deve alimentar o AutoCloud | ATV-008, ATV-009, ATV-010 |
| 16. Alerta criado e exibido no frontend | ATV-011, ATV-012 |
| 17. ESP32 offline armazenando eventos | ATV-014 |
| 18. Reenvio dos eventos na ordem correta | ATV-014 |
| 19. Buffer do ESP32 atingindo o limite | ATV-014 |
| 20. Geracao e download de relatorio | ATV-018 |
| 21. Execucao do frontend no Android | ATV-024 |

## Decisoes tecnicas que precisam de aprovacao

- Criar `functions/` em TypeScript com Firebase Functions v2.
- Usar Node.js 22 para Firebase Functions, salvo restricao do ambiente Firebase CLI.
- Definir autenticacao Function -> FastAPI: segredo compartilhado via Secret Manager/header, ou mecanismo mais forte se o backend estiver em Cloud Run/ambiente Google.
- Criar colecoes tecnicas novas: `processed_sensor_events`, `filling_cycles`, possivelmente `pump_events`.
- Usar `doc.id` do Firestore como idempotency key inicial.
- Definir `device_id` oficial do ESP32.
- Definir `MIN_PLAUSIBLE_DRAIN_TIME_SECONDS`.
- Definir volume entre sensores e preco da agua por m3.
- Definir potencia da bomba em kW e preco da energia por kWh.
- Aprovar se alertas serao lidos diretamente do Firestore pelo frontend ou via backend.
- Aprovar se dados reais do sistema podem ser enviados ao Gemini/OpenAI ou somente a Ollama local.
- Escolher modelo Gemini inicial.
- Aprovar ou rejeitar o candidato `qwen3:4b-instruct` antes de qualquer download.
- Decidir se a plataforma Android sera adicionada neste repositorio e qual `appId` definitivo.

## Perguntas objetivas pendentes

1. Qual e o identificador desejado do ESP32 (`device_id`)?
2. O inicio de enchimento deve ser considerado em `baixo desceu` ou `baixo subiu` no contrato do TCC?
3. Qual e o tempo minimo fisicamente plausivel para a caixa ir de sensor alto para sensor baixo?
4. Qual e o volume em litros entre o sensor baixo e o sensor alto?
5. Qual tarifa de agua deve ser usada: valor por m3, por litro, tarifa fixa ou faixa?
6. Qual potencia nominal da bomba em kW?
7. Qual preco da energia em R$/kWh?
8. O backend estara hospedado onde para a Function chamar: local/tunnel, Cloud Run, VPS, outro?
9. Podemos criar colecoes tecnicas no Firestore para processamento, ciclos e alertas?
10. Alertas devem ter push notification ou apenas exibicao dentro do app nesta etapa?
11. O app deve ler alertas diretamente do Firestore ou via API backend?
12. Podemos enviar dados reais/resumos para provedores externos como Gemini?
13. Qual modelo Gemini voce quer aprovar para a primeira integracao?
14. A maquina que rodara Ollama tem GPU ou apenas CPU?
15. Qual package id Android definitivo substitui `io.ionic.starter`?

## Validacoes executadas nesta auditoria inicial

- `git status --short`: worktree ja estava sujo antes deste plano.
- `rg --files`: mapeamento de arquivos.
- `npm exec tsc -- --noEmit` em `frontend`: falhou pelos erros registrados em "Descobertas principais".
- Import do backend com Python global: falhou por dependencia ausente.
- Import do backend com `.venv` local: nao executou no Windows atual porque a `.venv` tem estrutura `bin/` e o executavel falhou com acesso negado.
- Verificacao de existencia: nao existem `functions/`, `firebase.json`, `.firebaserc`, `firestore.rules`, `frontend/android` ou `frontend/ios`.

## Validacoes executadas apos ATV-003, ATV-005 e ATV-006

- `node -v`: passou com `v22.23.1`.
- `npm -v`: passou com `10.9.8`.
- `cd backend && source .venv/bin/activate && pytest`: passou com 8 testes.
- `cd backend && source .venv/bin/activate && python -m compileall app tests`: passou.
- `cd functions && npm install`: passou sem avisos de engine.
- `cd functions && npm run build`: passou.
- `cd functions && npm test`: passou.
- `cd frontend && npm exec tsc -- --noEmit`: passou.
- `cd frontend && npm run lint`: passou com 6 avisos nao bloqueantes de `react-refresh/only-export-components`.
- `cd frontend && npm run build`: passou com avisos nao bloqueantes de Browserslist/Baseline desatualizados e chunks acima de 500 kB.
- `git diff --check`: passou.

## Validacoes executadas apos ATV-008, ATV-009, ATV-010 e ATV-011

- `cd backend && source .venv/bin/activate && pytest`: passou com 21 testes.
- `cd backend && source .venv/bin/activate && python -m compileall app tests`: passou.
- `cd backend && source .venv/bin/activate && python -c "import app.main; print('backend import ok')"`: passou.
- `git diff --check`: passou.

## Validacoes executadas apos ATV-012

- `cd backend && source .venv/bin/activate && pytest`: passou com 28 testes, incluindo endpoints de alertas persistidos e resposta `503` para falhas operacionais do Firestore.
- `cd backend && source .venv/bin/activate && python -m compileall app tests`: passou.
- `GET /alerts?period=7d&status=open&limit=1` com backend local: retornou `503 Service Unavailable` claro quando a credencial Firebase Admin atual falhou.
- `POST /alerts/sensor-event` com backend local: retornou `503 Service Unavailable` claro quando a credencial Firebase Admin atual falhou.
- `cd frontend && npm exec tsc -- --noEmit`: passou.
- `cd frontend && npm run lint`: passou com 6 avisos nao bloqueantes de `react-refresh/only-export-components`.
- `cd frontend && npm run build`: passou com avisos nao bloqueantes de Browserslist/Baseline desatualizados e chunks acima de 500 kB.
- `git diff --check`: passou.

## Testes nao executados nesta etapa

- Firebase Emulator: nao executado porque ainda falta definir project alias real, Firebase CLI/secrets e estrategia de URL para o backend local/homologacao.
- Deploy Firebase/backend/mobile: fora de escopo nesta etapa.
- Cypress E2E e Vitest unitario do frontend: nao executados nesta revalidacao; foram priorizados `tsc`, `lint`, build e pytest dos endpoints backend.
- Compilacao Arduino: nao ha ambiente Arduino/ESP32 configurado nesta sessao.

## Riscos gerais

- Sem `device_id`/`event_id` gerado no firmware, eventos offline e reprocessamento historico ainda ficam mais frageis que o ideal.
- Sem validar Firebase Emulator/deploy, o fluxo Firestore -> Function -> backend ainda precisa de prova integrada fora dos testes locais.
- Sem separar todos os secrets/configuracoes por ambiente, ha risco de expor credenciais e confundir configuracao publica com segredo.
- Sem estado confirmado da bomba via MQTT, calculo de energia e relatorios de acionamento ainda dependem de premissas incompletas.
- Sem confirmar hosting do backend, a Function pode ficar sem URL confiavel para chamada.

## Proximo passo recomendado

Aguardar revisao e commit do lote `ATV-012`.

Depois disso, iniciar `ATV-015` + `ATV-017`: estado confirmado da bomba e estimativa de energia.
