# Planejamento das pendências do AquaMonitor

Quero que você atue como desenvolvedor responsável por analisar, planejar e implementar gradualmente as funcionalidades restantes do projeto **AquaMonitor**, desenvolvido como TCC.

## Regra principal desta primeira etapa

**Não comece implementando as funcionalidades imediatamente.**

Nesta primeira execução, faça somente:

1. Leia integralmente:

   * `AGENTS.md`; 
   * `README.md`,
   * arquivos de configuração;
   * backend;
   * frontend;
   * firmware;
   * integrações Firebase, MQTT e IA;
   * código atual relacionado a alertas, relatórios e AutoCloud.

2. Investigue como cada pendência se relaciona com o código existente.

3. Identifique:

   * o que já está implementado;
   * o que está parcialmente implementado;
   * o que está incorreto ou localizado em uma camada inadequada;
   * o que ainda não existe;
   * dependências entre as atividades;
   * riscos técnicos;
   * informações que precisam ser confirmadas comigo.

4. Crie um documento Markdown com o planejamento completo.

5. Não faça mudanças funcionais no projeto antes de eu revisar e aprovar esse planejamento.

---

# Documento que deve ser criado

Crie preferencialmente:

```text
specs/000-plano-geral-pendencias.md
```

Caso a pasta `specs/` ainda não exista, você pode criá-la.

O documento deve funcionar como um backlog técnico rastreável. Para cada atividade, inclua:

* ID da atividade;
* título;
* pendências relacionadas;
* objetivo;
* contexto encontrado no código;
* situação atual;
* proposta de solução;
* backend afetado;
* frontend afetado;
* firmware afetado;
* Firebase ou serviços externos afetados;
* contratos e payloads envolvidos;
* dependências;
* riscos;
* perguntas pendentes;
* critérios de aceite;
* plano de testes;
* arquivos provavelmente afetados;
* status;
* espaço para registrar o resultado da minha validação.

Use um status como:

```text
PENDENTE
EM ANÁLISE
AGUARDANDO RESPOSTA
PRONTO PARA IMPLEMENTAÇÃO
EM IMPLEMENTAÇÃO
AGUARDANDO VALIDAÇÃO
CONCLUÍDO
```

Organize as atividades em uma ordem técnica recomendada. Uma única atividade poderá resolver mais de uma pendência quando isso fizer sentido, mas explique claramente essa relação.

---

# Arquitetura que deve ser preservada

O projeto está dividido em:

```text
backend/
frontend/
firmware/
```

Considere a arquitetura documentada no README:

* backend em FastAPI;
* frontend em Ionic React;
* firmware em ESP32;
* Firestore para eventos;
* MQTT para controle da bomba;
* Firebase Admin no backend;
* serviços e integrações do frontend concentrados em `frontend/src/services/`;
* regras de negócio do backend separadas em `routers`, `schemas` e `services`.

Preserve a separação:

```text
router -> schema -> service
```

Não coloque código server-side dentro do frontend.

Existe uma tentativa de código semelhante a uma Firebase Cloud Function em:

```text
frontend/src/services/alerts.ts
```

Investigue esse arquivo. A tendência é que esse código saia do frontend e seja reorganizado em uma pasta server-side, por exemplo:

```text
functions/
```

Entretanto, confirme a estrutura mais adequada após analisar o projeto.

---

# Prioridade 1 — Firebase Functions e processamento automático de eventos

A primeira atividade a ser planejada e, depois da minha aprovação, implementada será a integração em tempo real com **Firebase Functions**.

## Fluxo desejado

Quando o código responsável pela leitura do ESP32 `tcc/firmware/TCC.ino/TCC_Final/TCC_FINAL.ino`, registrar um novo documento na coleção remota do Firestore, o seguinte fluxo deverá ocorrer automaticamente:

```text
ESP32
        ↓
Novo documento na coleção sensores
        ↓
Firebase Function acionada
        ↓
Chamada autenticada ao backend FastAPI
        ↓
Validação lógica do novo evento
        ↓
Processamento do AutoCloud, quando aplicável
        ↓
Criação de alerta, caso exista anomalia
        ↓
Atualização do aplicativo
```

## Firebase Function

Investigue e planeje uma Firebase Function acionada na criação de um novo documento na coleção de sensores.

Avalie:

* versão atual do Firebase Functions;
* uso de JavaScript ou TypeScript;
* estrutura da pasta `functions/`;
* configuração do Firebase;
* gatilho de criação de documento no Firestore;
* payload enviado ao backend;
* URL configurada por ambiente;
* autenticação da chamada;
* secrets;
* timeout;
* retentativas;
* idempotência;
* duplicidade de eventos;
* logs;
* tratamento de falhas;
* uso do Firebase Emulator para testes;
* estratégia para desenvolvimento local, homologação e produção.

A Function não deve depender de uma URL hardcoded.

O backend já possui ou aparenta possuir o endpoint:

```text
POST /alerts/sensor-event
```

Confirme:

* contrato atual;
* schema esperado;
* comportamento;
* validações;
* resposta;
* integração com Firestore;
* integração com alertas;
* integração com AutoCloud.

Caso o endpoint atual não seja suficiente, proponha a alteração no planejamento antes de modificar o código.

---

# Detecção de anomalias

A detecção deverá ter duas camadas diferentes.

## 1. Validações lógicas e determinísticas dos sensores

Essas validações não precisam utilizar AutoCloud ou clusterização. Elas podem ser regras de negócio configuráveis executadas a cada novo evento.

### Sequência esperada de enchimento

Quando o sensor de nível baixo é acionado e a caixa começa a encher, o próximo evento de nível esperado deve ser o sensor alto.

Uma sequência como esta é suspeita:

```text
sensor baixo
caixa enchendo
sensor baixo novamente
```

Antes de chegar ao sensor alto, outro evento de sensor baixo pode indicar:

* leitura duplicada;
* ruído;
* falha do sensor;
* evento fora de ordem;
* problema na gravação;
* reinicialização do dispositivo.

Não trate toda repetição automaticamente como falha física. Investigue timestamps, IDs e possíveis duplicidades.

### Transição rápida do sensor alto para o sensor baixo

Depois que a caixa chega ao sensor alto, não é esperado que ela alcance o sensor baixo em um intervalo fisicamente impossível ou muito curto.

Isso pode representar:

* leitura incorreta;
* ruído do sensor;
* evento duplicado;
* problema de ordenação;
* falha de hardware;
* vazamento muito grave;
* ruptura ou esvaziamento anormal da caixa.

O sistema não deve afirmar automaticamente qual dessas causas ocorreu. Ele deve registrar uma anomalia e apresentar as causas como hipóteses.

O intervalo mínimo plausível deverá ser configurável. Não deixe um valor arbitrário espalhado pelo código.

Exemplo de variável:

```text
MIN_PLAUSIBLE_DRAIN_TIME_SECONDS
```

O nome final pode ser ajustado às convenções do projeto.

### Outros pontos a avaliar

Planeje como lidar com:

* eventos repetidos;
* eventos atrasados;
* timestamps ausentes;
* timestamps fora de ordem;
* documentos processados mais de uma vez;
* reinicialização do ESP32;
* perda de conexão;
* sequência incompleta;
* alteração manual da bomba;
* caixa já iniciando em estado intermediário;
* ausência temporária de um dos eventos.

---

## 2. Análise temporal pelo AutoCloud

O principal objeto de interesse do AutoCloud será o **tempo de enchimento da caixa**.

Um ciclo válido de enchimento deve, em princípio, ser formado por:

```text
sensor baixo
        ↓
início do enchimento
        ↓
sensor alto
        ↓
fim do enchimento
```

Calcule:

```text
tempo_de_enchimento = timestamp_sensor_alto - timestamp_sensor_baixo
```

Antes de usar um ciclo no AutoCloud, valide se a sequência é confiável.

Eventos identificados como inválidos pelas regras lógicas não devem contaminar a análise temporal.

## Objetivo do AutoCloud

O AutoCloud deverá analisar os tempos de enchimento ao longo do tempo, utilizando a estratégia de clusterização já existente ou uma estratégia tecnicamente adequada após a investigação.

O sistema deverá detectar comportamentos como:

* aumento gradual do tempo de enchimento;
* mudança persistente do padrão;
* ciclo muito mais lento que o histórico;
* agrupamento novo e distante do comportamento normal;
* degradação progressiva;
* variação anormal recorrente.

Um aumento persistente no tempo de enchimento pode indicar, como hipótese:

* desgaste ou perda de desempenho da bomba;
* perda de potência;
* problema elétrico;
* obstrução da tubulação;
* vazamento;
* redução de vazão;
* alteração hidráulica;
* problema nos sensores ou na medição de tempo.

O sistema não deve apresentar essas hipóteses como diagnóstico confirmado.

## Investigação do AutoCloud atual

Localize todo o código relacionado ao termo `AutoCloud`, incluindo:

* serviços;
* classes;
* funções;
* rotas;
* notebooks;
* scripts;
* modelos;
* arquivos gerados;
* chamadas no frontend;
* integração com relatórios ou alertas.

Documente:

* como funciona atualmente;
* quais dados recebe;
* se está realmente sendo executado;
* quais erros existem;
* como persiste resultados;
* como diferencia treino, atualização e inferência;
* quantidade mínima de ciclos necessária;
* tratamento de poucos dados;
* tratamento de outliers;
* necessidade de normalização;
* necessidade de reprocessamento histórico;
* forma de explicar o resultado no aplicativo.

Não substitua a implementação existente sem antes entender seu objetivo.

---

# Demais pendências do projeto

Organize as pendências abaixo em atividades técnicas priorizadas.

## IA e chatbot

### Modelo local atual

O projeto já possui uma configuração semelhante a:

```text
OLLAMA_MODEL=qwen2:0.5b
```

Esse modelo é leve, mas atualmente apresenta baixa capacidade de contexto e respostas insatisfatórias.

Investigue:

* como o Ollama está integrado;
* quais rotas utilizam o modelo;
* como o prompt é montado;
* se há histórico de conversa;
* como as sessões são armazenadas;
* timeout;
* streaming;
* tratamento de indisponibilidade;
* tamanho de contexto;
* uso de dados do sistema;
* diferença entre chatbot genérico e agente analítico.

Não presuma que o problema está somente no tamanho do modelo. Avalie também prompt, contexto, recuperação de dados e arquitetura.

### Segundo modelo local mais potente

Planeje a adição de um segundo modelo Ollama mais capaz, que seja viável em uma máquina com aproximadamente **8 GB de RAM disponíveis para essa execução**.

Não escolha ou baixe o modelo sem apresentar antes:

* nome;
* tamanho aproximado;
* quantização;
* memória estimada;
* vantagens;
* limitações;
* qualidade esperada;
* velocidade;
* comando de instalação.

Dê preferência a um modelo da família Qwen caso seja compatível com o código e com o objetivo, mas não assuma isso antes da análise.

A seleção do modelo deverá ocorrer por variável de ambiente.

### Google AI Studio / Gemini

Planeje a integração do chatbot com a API do Google AI Studio Gemini.

A integração deverá:

* utilizar chave em variável de ambiente;
* não expor a chave no frontend;
* ser chamada pelo backend;
* possuir tratamento de timeout;
* possuir tratamento de limite de uso;
* tratar erros de autenticação;
* permitir selecionar o provedor;
* preservar sessões;
* permitir fallback, caso aprovado;
* registrar qual modelo respondeu;
* evitar acoplamento direto do chatbot a um único provedor.

Considere uma abstração como:

```text
LLMProvider
├── OllamaProvider
└── GeminiProvider
```

O nome final deve seguir as convenções encontradas no projeto.

Avalie variáveis como:

```text
LLM_PROVIDER
OLLAMA_BASE_URL
OLLAMA_MODEL
GEMINI_API_KEY
GEMINI_MODEL
```

Não implemente fallback silencioso sem deixar isso visível nos logs e na resposta da API.

---

## Segurança e configurações Firebase

Remova futuramente as configurações atualmente hardcoded no frontend e organize-as por ambiente.

Investigue:

* arquivos que contêm configuração Firebase;
* chaves Firebase Web;
* credenciais Firebase Admin;
* tokens;
* URLs;
* configurações MQTT;
* Wi-Fi e secrets do firmware.

Planeje:

* `.env`;
* `.env.example`;
* variáveis Vite com prefixo `VITE_`;
* validação das variáveis ao iniciar;
* exclusão correta no `.gitignore`;
* documentação das variáveis;
* secrets do Firebase Functions;
* secrets do backend;
* estratégia para firmware.

Importante: diferencie configuração pública do Firebase Web de credenciais administrativas secretas.

Variáveis `VITE_*` são incluídas no bundle do navegador. Portanto, mover uma configuração para `.env` não a transforma automaticamente em segredo. A segurança também deverá considerar:

* regras do Firestore;
* restrição das chaves;
* domínios autorizados;
* Firebase App Check, caso aplicável;
* princípio do menor privilégio.

Não remova, altere, invalide ou regenere credenciais existentes sem minha autorização explícita.

---

## Buffer offline no ESP32

Planeje um buffer limitado para guardar leituras quando não houver conexão no momento do evento.

O objetivo é evitar perda de eventos sem provocar uso ilimitado da memória do ESP32.

Avalie uma estrutura como:

* fila circular;
* ring buffer;
* vetor estático com índices;
* armazenamento persistente em NVS ou LittleFS, se necessário.

Não use crescimento dinâmico ilimitado.

O planejamento deverá considerar:

* capacidade máxima;
* tamanho aproximado de cada evento;
* memória RAM disponível;
* persistência após reinicialização;
* política quando o buffer ficar cheio;
* descarte do evento mais antigo ou rejeição do mais novo;
* número máximo de tentativas;
* backoff;
* ordem de reenvio;
* IDs únicos;
* deduplicação;
* confirmação de envio;
* prevenção de fragmentação de heap;
* watchdog;
* logs seriais;
* sincronização do timestamp após reconexão.

Antes de definir a capacidade, estime o consumo de memória.

---

## Alertas inteligentes no aplicativo

Planeje alertas no aplicativo para cada anomalia detectada.

Investigue se os alertas serão:

* exibidos somente dentro do app;
* armazenados no Firestore;
* enviados por push notification;
* processados pelo backend;
* lidos em tempo real pelo frontend.

Planeje um modelo de alerta contendo, quando aplicável:

```text
id
event_id
type
severity
title
message
detected_at
sensor_timestamp
status
possible_causes
metadata
acknowledged
acknowledged_at
```

Considere severidades como:

```text
info
warning
critical
```

Não crie notificações repetidas para o mesmo evento.

---

## Interface do aplicativo

Mapeie melhorias estéticas e funcionais necessárias no frontend.

Analise principalmente:

* `HomePage`;
* `HistoryPage`;
* `ChatPage`;
* layout principal;
* responsividade;
* loading;
* erros;
* estado sem dados;
* dados mockados;
* acessibilidade;
* navegação;
* feedback de conexão;
* feedback de comando da bomba;
* apresentação de alertas;
* indicadores de consumo;
* experiência em telas pequenas.

Não faça uma reescrita visual completa antes de apresentar uma proposta.

---

## Relatórios

O projeto já possui endpoints de relatório no backend.

Investigue:

```text
GET /reports/weekly
GET /reports/monthly
```

Planeje:

* melhoria visual dos PDFs;
* cabeçalho;
* identificação do período;
* resumo executivo;
* indicadores;
* tabelas;
* gráficos;
* alertas;
* consumo de água;
* custo da água;
* consumo elétrico;
* custo elétrico;
* paginação;
* rodapé;
* data de geração;
* tratamento de períodos sem dados.

Também deverá ser implementado futuramente o download diretamente pelo botão existente na tela de histórico.

O fluxo esperado é:

```text
Usuário seleciona período
        ↓
Clica em download
        ↓
Frontend chama a API
        ↓
Backend gera ou retorna o PDF
        ↓
Aplicativo faz o download ou compartilhamento
```

Considere diferenças entre navegador e aplicativo mobile.

---

## Portabilidade para mobile

Investigue se o frontend já possui Capacitor configurado.

Verifique:

* `package.json`;
* `capacitor.config.*`;
* diretórios `android/` e `ios/`;
* plugins instalados;
* configuração de build;
* URL do backend;
* permissões;
* acesso à rede;
* HTTPS;
* download de arquivos;
* notificações;
* Firebase;
* MQTT;
* comportamento do app em dispositivo físico.

Planeje os passos necessários para gerar e testar inicialmente no Android.

Não crie ou recrie a plataforma Android sem verificar se ela já existe.

---

## Estimativa de consumo de água

Deverá existir uma configuração para representar quantos litros existem entre o nível do sensor baixo e o nível do sensor alto.

Exemplo conceitual:

```text
RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS
```

Cada ciclo válido de enchimento entre sensor baixo e sensor alto poderá representar aproximadamente esse volume.

Planeje como calcular:

* quantidade de ciclos;
* volume abastecido;
* volume estimado consumido;
* consumo diário;
* consumo semanal;
* consumo mensal;
* custo em reais.

Também deverá existir uma configuração do preço da água.

Evite uma variável ambígua como “valor do litro” sem documentar a unidade. Avalie uma configuração como:

```text
WATER_PRICE_PER_CUBIC_METER_BRL
```

Como:

```text
1 m³ = 1000 litros
```

O sistema deverá converter corretamente para custo em reais.

Verifique se o preço deve ser:

* por litro;
* por metro cúbico;
* tarifa fixa;
* tarifa por faixa.

Caso o projeto utilize apenas uma estimativa simples, documente essa limitação.

---

## Estimativa de consumo elétrico da bomba

Crie o planejamento para estimar o gasto elétrico com base no tempo em que a bomba permanece ligada.

Investigue quais dados estão disponíveis atualmente:

* evento de bomba ligada;
* evento de bomba desligada;
* comandos MQTT;
* estado real da bomba;
* potência nominal;
* tensão;
* corrente;
* fator de potência;
* eficiência;
* tempo total de funcionamento.

Avalie uma configuração preferencialmente baseada em potência:

```text
PUMP_POWER_KW
ELECTRICITY_PRICE_PER_KWH_BRL
```

Cálculo esperado:

```text
energia_kWh = potência_kW × tempo_ligado_em_horas
custo_BRL = energia_kWh × preço_kWh
```

Caso o usuário forneça apenas consumo por minuto, converta para uma unidade claramente documentada.

Diferencie comando enviado de confirmação de que a bomba realmente ficou ligada.

---

# Ordem inicial sugerida

Analise se esta ordem é tecnicamente adequada:

1. Auditoria da arquitetura e criação do planejamento.
2. Definição do contrato de eventos dos sensores.
3. Firebase Functions.
4. Endpoint de processamento do novo evento.
5. Idempotência e persistência do processamento.
6. Regras lógicas de sequência dos sensores.
7. Integração automática do AutoCloud.
8. Persistência e consulta de anomalias.
9. Alertas em tempo real no aplicativo.
10. Remoção de hardcodes e organização de ambientes.
11. Buffer offline do ESP32.
12. Estimativas de água e energia.
13. Relatórios e download pela tela de histórico.
14. Refinamento dos provedores de IA.
15. Gemini pelo Google AI Studio.
16. Segundo modelo Ollama.
17. Melhorias de interface.
18. Portabilidade e validação no Android.

Você pode alterar essa ordem, desde que justifique no documento.

---

# Critérios obrigatórios para o planejamento

O planejamento deve evitar tarefas genéricas como:

```text
Implementar Firebase
Melhorar IA
Arrumar interface
```

Transforme cada item em atividades pequenas, verificáveis e testáveis.

Exemplo:

```text
ATV-002 — Criar estrutura server-side do Firebase Functions
ATV-003 — Definir schema do evento enviado ao backend
ATV-004 — Implementar trigger onCreate da coleção sensores
ATV-005 — Implementar autenticação Function → FastAPI
ATV-006 — Garantir idempotência por document_id
ATV-007 — Criar testes com Firebase Emulator
```

Cada atividade deverá ter critérios objetivos de aceite.

---

# Testes esperados

Planeje testes para os cenários:

1. Novo evento válido de sensor baixo.
2. Novo evento válido de sensor alto.
3. Ciclo completo de enchimento.
4. Evento de sensor baixo duplicado.
5. Sensor baixo repetido antes do sensor alto.
6. Sensor alto seguido rapidamente por sensor baixo.
7. Eventos recebidos fora de ordem.
8. Evento sem timestamp.
9. Firebase Function executada duas vezes para o mesmo documento.
10. Backend indisponível.
11. Timeout ao chamar o backend.
12. Retentativa sem duplicar alerta.
13. AutoCloud sem quantidade mínima de dados.
14. AutoCloud com aumento gradual no tempo de enchimento.
15. Evento inválido que não deve alimentar o AutoCloud.
16. Alerta criado e exibido no frontend.
17. ESP32 offline armazenando eventos.
18. Reenvio dos eventos na ordem correta.
19. Buffer do ESP32 atingindo o limite.
20. Geração e download de relatório.
21. Execução do frontend no Android.

---

# Pytest para validação?

Analise se vale a pena criar um módulo/motor de pytest no backend (adicionando no requirements.txt, pode ficar avontade para entrar na .venv) para testar endpoints, casos de alertas, anomalias, entre outras coisas que possam ser últeis testar após a conclusão da atividade por vc.

# Comportamento esperado nesta primeira resposta

Depois da investigação:

1. Crie o documento Markdown de planejamento.
2. Informe o caminho do arquivo criado.
3. Apresente um resumo das principais descobertas.
4. Liste inconsistências encontradas.
5. Liste decisões técnicas que precisam da minha aprovação.
6. Faça perguntas objetivas sobre requisitos que não puderem ser determinados pelo código.
7. Identifique quais atividades podem ser agrupadas.
8. Indique qual será a primeira atividade implementável.
9. Aguarde minha aprovação antes de começar a implementação.

Não faça alterações irreversíveis.

Não apague código existente.

Não regenere credenciais.

Não altere regras do Firebase em produção.

Não baixe modelos Ollama antes da aprovação.

Não realize deploy.

Não avance silenciosamente para outras atividades.

Depois que eu aprovar o plano, trabalharemos em uma atividade por vez. Ao finalizar cada atividade, você deverá:

* executar os testes aplicáveis;
* mostrar os arquivos alterados;
* explicar as decisões;
* atualizar o status no documento;
* informar limitações;
* aguardar minha validação antes de seguir para a próxima.
