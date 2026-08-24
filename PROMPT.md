Você confirma que concluiu a construção de todas tasks planejadas? Se sim, agora entramos na etapa de auditoria, integração e validação funcional. O aplicativo Android já foi compilado com Capacitor, instalado por USB em um dispositivo físico e está abrindo e executando corretamente.

Lembre de seguir `AGENTS.md`, a documentação do projeto, os arquivos de planejamento/atividades e o estado atual do código. Use também como referência a documentação técnica já produzida para o TCC, mas não considere a documentação como prova de que uma funcionalidade está realmente funcionando.

## 1. Auditoria do planejamento existente

Antes de alterar o código, faça um levantamento de todas as atividades previstas no planejamento anterior.

O Android já foi validado pelo usuário em dispositivo físico via USB. Atualize o registro da ATV-024 com essa informação, sem executar novamente `npx cap add android` e sem recriar `frontend/android/`.

Depois do levantamento, prossiga diretamente com as correções e implementações abaixo. Não pare apenas para pedir confirmação, salvo se existir um bloqueio externo incontornável.

## 2. Autorização para configuração e testes

Você está autorizado, dentro do escopo deste projeto, a:

* inspecionar e ajustar arquivos `.env`;
* verificar as configurações do frontend, backend, Firebase, MQTT e provedores LLM;
* usar as credenciais reais já configuradas para implementações e testes;
* consultar o Firestore;
* realizar requisições reais às APIs;
* criar dados controlados de teste no Firebase;
* corrigir variáveis de ambiente e contratos de integração;
* reiniciar os serviços necessários;
* executar testes locais e de integração.

Não solicite autorização individual para cada variável já existente.

Apesar dessa autorização:

* não inclua segredos em commits;
* não mova chaves de backend para variáveis `VITE_*`;
* preserve `.env` no `.gitignore`;
* identifique dados de teste com `source`, `test_run_id` ou campos equivalentes;

## 3. Corrigir a integração Firestore da Home

O histórico está consultando corretamente os eventos da coleção `sensores`: os filtros retornam dados compatíveis com o Firestore. Entretanto, na Home:

* o campo “Último sensor alterado” não atualiza;
* o status global do Firebase aparece sempre como desconectado;
* o MQTT aparece corretamente como conectado.

Investigue e corrija a causa raiz.

Use como referência o mesmo cliente Firestore, projeto, coleção, normalização de documento e contrato que já funcionam na tela de histórico. O projeto utiliza Cloud Firestore, não Realtime Database. Portanto, não utilize mecanismos como `.info/connected`, específicos do Realtime Database.

Verifique especialmente:

* inicialização duplicada ou divergente do Firebase;
* variáveis `VITE_FIREBASE_*`;
* nome e caminho da coleção `sensores`;
* consultas `orderBy`, `limit` e índices;
* campo usado como timestamp;
* conversão de `Timestamp`, string ISO e valores legados;
* listeners `onSnapshot`;
* tratamento de erros;
* cancelamento do listener;
* estado compartilhado entre as telas;
* regras do Firestore;
* diferenças entre o bundle web e o Android;
* configuração copiada para `dist` e para os assets Android.

Crie ou centralize um serviço/hook de Firestore reutilizável. A Home e o indicador global (presente no canto inferior da tela) devem utilizar a mesma fonte de conexão e os mesmos contratos usados pelo histórico.

O status de conexão deve possuir comportamento coerente:

* `conectando` enquanto o primeiro snapshot não chega;
* `conectado` quando o listener recebe um snapshot válido, mesmo que vazio;
* `offline` quando houver ausência real de rede ou uso somente de cache;
* `erro/desconectado` quando o listener falhar.

Não represente “sem documentos” como “Firebase desconectado”.

## 4. Melhorar o campo “Último sensor alterado”

Além de corrigir a atualização em tempo real, exiba:

* nome do sensor;
* evento: `subiu` ou `desceu`;
* data;
* horário;
* estado operacional derivado, como `Enchendo`, `Esvaziando`, `Cheio` ou `Nível baixo`.

Use formatação `pt-BR` e trate corretamente timestamps UTC.

Exemplo visual:

```text
Sensor alto — subiu
Reservatório cheio
24/08/2026 às 14:32:10
```

Não derive “enchendo” ou “esvaziando” apenas de um texto isolado. Considere a sequência dos sensores e, quando disponível, o estado confirmado da bomba.

Adicione testes para:

* snapshot vazio;
* evento com `Timestamp` do Firestore;
* evento com string ISO;
* evento legado;
* erro no listener;
* mudança em tempo real;
* formatação da data;
* estado operacional derivado.

## 5. Animação do reservatório

A visualização cilíndrica da Home deve representar uma estimativa visual contínua do nível.

Parâmetros iniciais sugeridos:

```text
nível mínimo do sensor baixo: 20%
nível máximo: 100%
piso visual durante esvaziamento: 21%
tempo esperado de enchimento: 480 segundos
tempo visual esperado de esvaziamento: 480 segundos
velocidade de enchimento: 10 pontos percentuais por minuto
```

Comportamento desejado:

1. Ao ocorrer o evento que indica nível baixo e início do enchimento, o reservatório deve partir de aproximadamente 20%.
2. Durante o enchimento, deve avançar progressivamente até 100% em aproximadamente oito minutos.
3. Quando o sensor alto confirmar `subiu`, deve mostrar 100% e estado cheio.
4. Quando o sensor alto indicar `desceu`, deve iniciar a animação de esvaziamento.
5. O esvaziamento deve ir de 100% até aproximadamente 21% em oito minutos.
6. Ao atingir 21%, deve permanecer nesse nível até ocorrer o evento real de nível baixo.
7. O evento real do sensor baixo poderá então colocar o nível em 20% e iniciar um novo enchimento.

Prefira calcular o percentual pelo timestamp inicial e pelo tempo decorrido, em vez de incrementar valores com vários timers sujeitos a drift. Preserve o estado após navegação ou recarregamento reconstruindo-o a partir do último evento persistido.

Durante um enchimento sem confirmação do sensor alto, considere limitar visualmente em 99% e mostrar “Aguardando confirmação do sensor alto”, para não apresentar 100% como fato físico não confirmado.

Centralize esses limites em configuração. Você pode propor valores melhores, desde que:

* preserve o objetivo visual;
* não misture a animação com leituras físicas reais;
* não gere documentos no Firestore somente por causa da animação;
* documente a decisão adotada.

## 6. Consumo estimado de água

A tela de histórico aparentemente ainda apresenta valores mocados, embora a documentação afirme que o backend já possui cálculo por ciclos. Audite o código real e remova qualquer valor, série ou gráfico hardcoded.

Como não existe sensor de vazão, o consumo deve ser explicitamente apresentado como estimativa.

Use parâmetros configuráveis, incluindo:

```text
RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS
WATER_PRICE_PER_CUBIC_METER_BRL
```

A fonte do cálculo deve ser o backend e os eventos persistidos, não a animação do frontend.

Uma abordagem aceitável é:

```text
consumo estimado por ciclo = volume útil entre os sensores
consumo total = quantidade de ciclos válidos × volume útil
consumo em m³ = litros / 1000
custo estimado = consumo em m³ × tarifa
```

Para gráficos temporais, distribua os ciclos pelo período correspondente sem fabricar leituras contínuas inexistentes.

Garanta:

* exclusão de ciclos inválidos;
* idempotência;
* ausência de dupla contagem;
* estados de loading, vazio e erro;
* indicação textual de que o valor é estimado;
* integração real da tela de histórico com `/reports/summary`;
* coerência entre resumo JSON e relatório PDF.

## 7. Consumo estimado de energia

Audite se a estimativa atual está realmente calculada ou apenas mocada.

O cálculo deve usar somente comandos da bomba com:

```text
applied = true
confirmed = true
```

Utilize o estado aplicado ou confirmado, e não apenas o comando solicitado. Comandos ignorados, sobrepostos ou sem confirmação devem permanecer na auditoria, mas não devem entrar no tempo ligado.

Parâmetros:

```text
PUMP_POWER_KW
ELECTRICITY_PRICE_PER_KWH_BRL
```

Cálculo esperado:

```text
tempo ligado em horas = total_on_seconds / 3600
energia em kWh = potência da bomba × tempo ligado
custo = energia em kWh × tarifa
```

Valide intervalos incompletos, comandos duplicados, eventos fora de ordem, reinicializações e comandos sobrepostos pelas prioridades física, remota e automática.

Remova mocks do frontend e conecte os cards e gráficos ao backend.

## 8. Corrigir a definição do ciclo de enchimento

Existe uma divergência importante que precisa ser auditada.

A documentação atual informa:

```text
início: sensor baixo subiu
fim: sensor alto subiu
```

Entretanto, o objetivo funcional é medir o tempo desde o início real do funcionamento da bomba até o reservatório ficar cheio.

Revise o firmware, o contrato da coleção `comandos`, os eventos dos sensores e `filling_cycles.py`. Defina uma semântica canônica e documente-a.

A preferência é:

```text
início: comando/estado da bomba aplicado e confirmado como ligada
fim: sensor alto subiu, representando reservatório cheio
```

Para acionamento automático, o evento `baixo desceu` pode ser usado como fallback de início quando não houver confirmação confiável da bomba. Não utilize silenciosamente `baixo subiu` como início se esse evento ocorrer depois que o enchimento já começou.

Persista no ciclo:

* evento que iniciou o ciclo;
* origem do início;
* timestamp de acionamento confirmado;
* evento final;
* duração;
* modo da bomba;
* identificador do dispositivo;
* validade;
* motivo de descarte, quando inválido.

Atualize testes, documentação e cálculos dependentes desse contrato.

## 9. AutoCloud: tempo de enchimento e anomalias

O AutoCloud deve trabalhar sobre ciclos válidos de enchimento e sobre `fill_time_seconds`.

Use 480 segundos como referência inicial configurável, mas permita que a linha de base seja aprendida a partir de ciclos históricos válidos.

O algoritmo deve cobrir pelo menos:

### Caso normal

Tempos próximos de oito minutos, com variação natural, sem geração indevida de alerta.

### Anomalia abrupta

Exemplo: histórico próximo de oito minutos seguido por um ciclo de quinze minutos.

Deve gerar alerta de enchimento anormalmente lento ou novo padrão distante.

### Degradação gradual

Exemplo:

```text
8 min → 9 min → 10 min → 11 min → 12 min
```

Deve gerar alerta de tendência persistente de aumento, mesmo que cada ciclo isolado não ultrapasse imediatamente o limiar abrupto.

Revise os parâmetros existentes:

```text
FILL_TIME_MIN_SAMPLES
FILL_TIME_SLOW_FACTOR
FILL_TIME_PERSISTENT_WINDOW
```

Você pode sugerir estatísticas ou limiares mais robustos, mas deve justificar e validar com testes. O sistema deve detectar anomalias e apresentar possíveis causas, sem afirmar diagnóstico físico definitivo.

## 10. Fixtures JSON e testes do AutoCloud

Crie fixtures JSON versionadas no repositório, preferencialmente em uma estrutura como:

```text
backend/tests/fixtures/autocloud/
```

Os documentos devem reproduzir os contratos reais do Firestore para:

* coleção `comandos`;
* coleção `sensores`;
* ciclos derivados, quando necessário.

Inclua identificadores únicos, timestamps UTC, `device_id`, `source`, estado solicitado, estado aplicado, confirmação, prioridade e demais campos reais do contrato.

Cenários mínimos:

1. dados insuficientes;
2. cinco ou mais ciclos normais próximos de 480 segundos;
3. ciclo abrupto de aproximadamente 900 segundos;
4. progressão de 540, 600, 660 e 720 segundos;
5. eventos duplicados;
6. eventos fora de ordem;
7. timestamp ausente;
8. repetição inesperada do sensor baixo;
9. sensor alto sem sequência anterior válida;
10. esvaziamento fisicamente implausível;
11. comando solicitado, mas não aplicado;
12. comando aplicado sem confirmação;
13. comando sobreposto por prioridade;
14. ciclo válido com bomba confirmada;
15. reinício do dispositivo durante um ciclo.

Crie testes automatizados determinísticos que carreguem esses JSONs sem depender do Firebase remoto. Se os testes demonstrarem falhas no AutoCloud ou nas regras atuais, corrija o algoritmo e adicione testes de regressão.

## 11. Testes reais no Firebase

Além das fixtures locais, execute integração real usando as credenciais configuradas.

Preferência:

1. Firebase Emulator, se estiver configurado;
2. projeto Firebase de teste;
3. ambiente remoto atual, somente com dados claramente identificados.

Crie um script de seed reutilizável, seguro e idempotente, com opção `--dry-run`. Use `test_run_id` e `source=integration_test`.

Para manter uma base remota permanente sem contaminar histórico, consumo e alertas operacionais, utilize coleções de teste ou um namespace próprio. Para validar os gatilhos reais nas coleções operacionais, insira documentos temporários identificados, capture as evidências e remova apenas os documentos criados pelo teste.

Nunca limpe uma coleção inteira.

Documente:

* projeto utilizado;
* coleções;
* IDs criados;
* alertas esperados;
* alertas efetivamente gerados;
* ciclos criados;
* resultado da idempotência;
* procedimento de limpeza.

## 12. Processamento automático de sensores e comandos

Atualmente existe `onSensorCreated` para `sensores/{docId}` e o endpoint:

```text
POST /alerts/sensor-event
```

Verifique se todos os eventos novos de sensor realmente disparam o processamento automático.

O usuário também precisa que eventos da coleção `comandos` sejam processados automaticamente. Implemente uma solução coerente com a arquitetura existente, por exemplo:

```text
onCommandCreated
comandos/{docId}
POST /alerts/command-event
```

Você pode optar por um endpoint unificado se isso reduzir duplicação, desde que preserve contratos, compatibilidade e idempotência.

O processamento deve:

* validar o comando;
* diferenciar estado solicitado e aplicado;
* considerar confirmação física;
* respeitar prioridades;
* atualizar o estado temporal da bomba;
* correlacionar comandos e sensores;
* criar ou finalizar ciclos quando aplicável;
* executar regras de sequência e intervalo;
* executar AutoCloud somente quando houver um ciclo completo e válido;
* persistir alertas deduplicados;
* impedir reprocessamento em retentativas da Function.

Não execute todas as análises cegamente em eventos incompletos. Cada evento deve acionar a API, mas a API deve decidir quais análises são aplicáveis naquele estágio.

Proteja os webhooks com o segredo já existente e adicione testes para segredo ausente, incorreto, correto e evento duplicado.

## 13. Validar regras inteligentes existentes

Revise e teste todas as regras já documentadas:

* `missing_timestamp`;
* `duplicate_event`;
* `out_of_order_event`;
* `unexpected_low_repeat`;
* `implausible_drain_time`;
* `unexpected_high_without_low`;
* `low_dropped_while_high_active`;
* `slow_fill_cycle`;
* `persistent_fill_time_shift`;
* `new_fill_time_cluster`.

Para cada uma, confirme:

* sequência que dispara;
* severidade;
* mensagem;
* possíveis causas;
* se bloqueia ciclo;
* se bloqueia AutoCloud;
* deduplicação;
* persistência;
* exibição no frontend;
* reconhecimento pelo usuário.

Corrija regras contraditórias com a semântica real dos sensores e adicione testes de regressão.

## 14. Testes e validação final

Execute, no mínimo:

```bash
cd backend
pytest
python -m compileall app tests
```

```bash
cd functions
npm run build
npm test
```

```bash
cd frontend
npm run build
npm run lint
npm run android:sync
npx cap doctor android
```

Também execute:

* testes das fixtures JSON;
* testes de integração do Firestore;
* testes dos webhooks;
* teste do último sensor da Home;
* teste do indicador de conexão;
* teste dos cálculos de água;
* teste dos cálculos de energia;
* teste do ciclo de enchimento;
* teste abrupto e gradual do AutoCloud;
* teste de idempotência;
* teste dos gráficos e relatório PDF.

Não altere testes apenas para fazê-los passar. Corrija a implementação ou documente claramente uma mudança intencional de contrato.

## 15. Entrega esperada

Ao finalizar, apresente:

1. resumo executivo do que estava funcionando;
2. atividades anteriores realmente concluídas;
3. pendências encontradas;
4. causas-raiz dos problemas;
5. alterações realizadas;
6. arquivos modificados;
7. contratos ou variáveis novas;
8. resultados dos testes, com comandos e contagens;
9. dados de integração criados no Firebase;
10. alertas esperados versus encontrados;
11. decisões adotadas para os limites de nível e duração;
12. limitações ainda existentes;
13. checklist curto para validação manual no Android.

Atualize a documentação técnica para refletir o comportamento efetivamente implementado. Não registre como resultado observado algo que foi somente simulado ou coberto por teste automatizado.


## OBSERVAÇÕES FINAIS

- Você tem liberdade para startar e derrubar via comando local tanto backend, quanto frontend.
- Faça bateria de testes de possíveis perguntas para o chatbot, vc pode alternar entre ollhama e gemini, as duas já estão inclusas no .env e funcionando.
Eu quero que vc averigue e garanta a capacidade de adaptação a perguntas e oferta de dicas de ações pelas LLMs do chatbot. Garantindo o poder de interpretação, busca, apresentação de resposta humanizada, sugestão de dicas quando conveniênte, etc... O poder de uma LLM especialista na base de daddos do sistema. Faça tabela de comparações entre as LLMs após os testes.
- Também, os relatórios gerados ao clicar no botão de download estão muito básicos. Faça eles ficarem mais estilosos, com mais cores, ícones, divisão por linhas e colunas (se conveniente). Quando clico em download no celular, ele baixa no noteboook servidor, tente manter o dowload no celular, se for possível dentro do atual fluxo, se precisar mudar o fluxo, não mexa.