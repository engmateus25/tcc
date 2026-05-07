# AGENTS.md

Este arquivo orienta IAs e agentes de desenvolvimento que trabalham no projeto AquaMonitor.

## Contexto

O AquaMonitor e um projeto de TCC para monitoramento e controle de reservatorio de agua.

Dominios principais:

- `backend/`: API FastAPI, servicos, relatorios, alertas, agente IA e integracao server-side com Firestore.
- `frontend/`: aplicacao Ionic React/Vite para web/mobile, dashboard, historico, chat IA, Firebase client SDK e MQTT.
- `firmware/`: sketches ESP32 para sensores de nivel, bomba, LEDs, MQTT e envio de eventos ao Firestore.
- Firebase/MQTT: camada de comunicacao, armazenamento e controle remoto.

## Regra principal

Antes de alterar codigo, analise a estrutura atual, explique o plano e confirme que a mudanca esta alinhada ao pedido do usuario.

Se o usuario pedir apenas analise, nao altere arquivos.

## Limites de seguranca

- Nao remover arquivos sem autorizacao explicita.
- Nao usar comandos destrutivos como `git reset --hard`, `git checkout --`, `rm -rf` ou equivalentes sem pedido claro do usuario.
- Nao alterar credenciais, chaves, tokens, arquivos `.env` ou configuracoes sensiveis sem autorizacao explicita.
- Nao publicar nem copiar credenciais em respostas.
- Se encontrar chaves hardcoded, apenas sinalize o risco e proponha uma migracao segura.
- Preserve alteracoes existentes que nao foram feitas por voce.

## Estilo de implementacao

- Manter o padrao existente do projeto.
- Fazer alteracoes pequenas, revisaveis e testaveis.
- Evitar grandes refatoracoes quando uma mudanca localizada resolve o problema.
- Separar responsabilidades entre backend, frontend, firmware e integracao.
- Preferir codigo simples e direto.
- Adicionar comentarios apenas quando explicarem uma regra de negocio ou integracao nao obvia.

## Arquitetura atual

### Backend

Ponto de entrada:

- `backend/app/main.py`

Organizacao:

- `backend/app/routers/`: rotas FastAPI.
- `backend/app/schemas/`: DTOs Pydantic.
- `backend/app/services/`: regras de negocio e integracoes.
- `backend/app/tasks/`: scheduler de relatorios.
- `backend/generated/`: PDFs gerados.

Rotas conhecidas:

- `GET /health`
- `POST /llm/chat`
- `POST /llm/chat/stream`
- `GET /llm/sessions/{session_id}`
- `POST /agent`
- `GET /reports/weekly`
- `GET /reports/monthly`
- `GET /alerts/sensors`
- `POST /alerts/sensor-event`

### Frontend

Pontos principais:

- `frontend/src/App.tsx`: rotas principais.
- `frontend/src/layouts/AppLayout.tsx`: layout comum.
- `frontend/src/pages/HomePage.tsx`: painel principal.
- `frontend/src/pages/HistoryPage.tsx`: historico/estatisticas.
- `frontend/src/pages/ChatPage.tsx`: assistente IA.
- `frontend/src/hooks/useWaterSystem.ts`: estado do sistema, Firestore e MQTT.
- `frontend/src/services/firestoreService.ts`: leitura da colecao `sensores`.
- `frontend/src/services/mqttService.ts`: topicos MQTT.
- `frontend/src/services/aiService.ts`: chamadas ao backend.

### Firmware

Pasta principal:

- `firmware/TCC.ino/`

Sketches atuais:

- `TCC_Final/TCC_Final.ino`
- `TCC_2_sensores/TCC_2_sensores.ino`

Responsabilidades:

- leitura dos sensores de nivel baixo e alto;
- controle da bomba;
- prioridade entre automatico, MQTT e chave fisica;
- publicacao de eventos no Firestore;
- recepcao de comandos MQTT;
- sincronizacao de horario via NTP.

## Contratos de integracao

Firestore:

- `sensores`: eventos com `sensor`, `estado`, `timestamp` e opcionalmente `device_id`.
- `comandos`: comandos/acionamentos da bomba.
- `chat_sessions`: sessoes e mensagens do chat no backend.

MQTT:

- `bomba/controle`: comandos enviados ao ESP32.
- `bomba/estado`: estado da bomba consumido pelo app quando disponivel.

Payload atual de controle:

```text
<nome> ligar
<nome> desligar
```

## Fluxo Spec-Driven Development

Para novas funcionalidades, trabalhe a partir de uma especificacao curta antes de implementar.

Pasta recomendada:

```text
specs/
```

Formato recomendado:

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

Processo:

1. Entender o requisito.
2. Criar ou revisar a spec.
3. Dividir tarefas pequenas por dominio: backend, frontend, firmware e integracao.
4. Implementar uma tarefa por vez.
5. Testar a tarefa.
6. Documentar o que mudou.

Para mudancas que afetam contratos, defina primeiro:

- rota HTTP ou topico MQTT;
- payload de entrada;
- payload de saida;
- comportamento esperado em erro;
- impacto em Firestore;
- impacto no firmware.

## Comandos uteis

Ver estrutura:

```bash
find . -maxdepth 2 -type d | sort
```

Listar arquivos:

```bash
rg --files
```

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

Firmware:

- abrir o sketch no Arduino IDE ou ambiente equivalente;
- selecionar placa ESP32;
- conferir bibliotecas WiFi, HTTPClient, PubSubClient e time;
- compilar antes de gravar no dispositivo.

## Entrega de mudancas

Ao finalizar uma alteracao, informe:

- arquivos alterados;
- motivo das alteracoes;
- comandos de validacao executados;
- testes nao executados e motivo;
- riscos ou proximos passos relevantes.

## Documentacao

O `README.md` da raiz e a documentacao principal para pessoas desenvolvedoras. Atualize-o quando houver mudanca em:

- comandos de instalacao/execucao;
- arquitetura;
- rotas;
- topicos MQTT;
- colecoes Firestore;
- fluxo SDD;
- requisitos de ambiente.
