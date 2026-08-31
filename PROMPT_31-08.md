Essafoi a saida daúltima tarefa que o codex implementou:

• Implementei o AutoCloud funcional e corrigi a regressão do intertravamento.

  O Que Mudou

  - AutoCloud agora usa o núcleo em backend/app/services/autocloud_core.py:313, com vetor normalizado por mediana/escala robusta:
    fill_time_seconds, low_to_high_seconds, pump_to_low_seconds, start_source_score, sensor_sequence_score.

  - A análise em backend/app/services/autocloud_fill_time.py:43 agora retorna classe, nuvens, distância normalizada, created_cloud e metadados do vetor.
  - Criei a coleção técnica autocloud_filling_samples via backend/app/services/autocloud_samples.py:12.
  - O fluxo real em backend/app/services/sensor_realtime.py:189 busca baseline nessa coleção e salva nova amostra quando fecha ciclo.
  - O ciclo agora registra baixo subiu e calcula low_to_high_seconds em backend/app/services/filling_cycles.py:27.
  - Corrigi a busca de histórico para aceitar timestamp ISO/string e timestamp nativo no Firestore em backend/app/services/firestore.py:204. Isso resolve a falha prática do baixo
    desceu -> alto subiu.

  - Adicionei o script backend/scripts/seed_autocloud_firestore.py:91.

  Firestore
  Gravei dados reais com:

  test_run_id=pibiti-20260831-103355
  collection=autocloud_filling_samples

  Resultado:

  - 5 ciclos normais de baseline gravados.
  - 1 ciclo anômalo adicional salvo após alerta.
  - interlock_alerts_created=['unexpected_high_without_low']

  O endpoint /alerts retornou os alertas abertos para a interface, incluindo:

  - slow_fill_cycle com created_cloud=true, cloud_count=2, distância normalizada 67.08.
  - unexpected_high_without_low.

  Também validei por POST real em /alerts/sensor-event: baixo desceu -> alto subiu retornou e persistiu unexpected_high_without_low.

  Validação

  - cd backend && .venv/bin/pytest: 70 passed.
  - cd backend && .venv/bin/python -m compileall app tests scripts: ok.
  - git diff --check: ok.
  - Seed real no Firestore: ok.
  - Consulta direta da coleção: 6 amostras para o test_run_id, sendo 5 baseline + 1 anômala.
  - Backend local foi iniciado para validação e encerrado ao final.

  Não rodei build do frontend nesta etapa porque a mudança foi backend/Firestore; os arquivos frontend pendentes no git status são da tarefa anterior.

  Observação
  Há alertas demonstrativos abertos no Firebase para screenshot. A validação HTTP também gerou um unexpected_low_repeat, porque já havia histórico real anterior de baixo desceu; o
  intertravamento específico foi gerado corretamente em seguida.

  Suggested semantic commit

  feat(autocloud): cluster filling cycles from normalized sensor timing vectors
  fix(alerts): restore interlock detection with firestore timestamp fallback
  test(autocloud): cover seeded samples and realtime anomaly alerts
  docs(readme): document autocloud firestore baseline validation




No tópico de metodologia para o meu PIBITI:
\section{Análise temporal com AutoCloud para ciclos de enchimento}

O ciclo de enchimento representa o intervalo entre o início efetivo do bombeamento e a chegada da água ao limite superior. Para determinar o instante inicial, o \textit{backend} procura prioritariamente um comando de ligação aplicado e confirmado. Quando essa confirmação não está disponível, utiliza-se como referência a transição de subida da boia inferior. O encerramento ocorre quando a boia superior é acionada e indica o nível alto. Assim, o tempo é calculado por:

\begin{equation}
    t_{enchimento} = t_{alto\,acionado} - t_{início\,confirmado}.
\end{equation}

O ciclo é descartado quando não possui horários válidos, quando o término ocorre antes do início ou quando algum de seus eventos é bloqueado pelas regras determinísticas. Para os ciclos aceitos, são armazenados os identificadores dos eventos de início e término, os horários, a duração, o dispositivo de origem e os metadados necessários à auditoria.

O algoritmo AutoCloud atua somente após o fechamento de um ciclo válido. A duração recém-calculada é comparada com o histórico do mesmo tipo de ciclo, evitando que eventos isolados ou incoerentes componham a linha de base. A análise começa quando existem pelo menos cinco ciclos históricos válidos. A Tabela~\ref{tab:parametros_autocloud} apresenta as condições utilizadas para classificar o comportamento temporal.

\begin{table}[H]
    \centering
    \caption{Critérios empregados na análise temporal dos ciclos de enchimento.}
    \label{tab:parametros_autocloud}
    \small
    \begin{tabular}{|p{4.2cm}|p{5.6cm}|p{4.2cm}|}
        \hline
        \textbf{Resultado} & \textbf{Critério} & \textbf{Interpretação} \\ \hline
        Dados insuficientes & Menos de cinco ciclos históricos válidos. & Mantém o registro sem emitir conclusão temporal. \\ \hline
        Tempo normal & Duração compatível com o comportamento histórico. & Não gera alerta de anomalia. \\ \hline
        Ciclo lento & Duração atual igual ou superior a 1,5 vez a mediana histórica. & Indica aumento pontual do tempo de enchimento. \\ \hline
        Mudança persistente & Crescimento progressivo nas três durações mais recentes. & Indica alteração gradual do padrão. \\ \hline
        Novo agrupamento temporal & Duração superior à média histórica acrescida de três desvios padrão. & Indica comportamento distante da distribuição anterior. \\ \hline
    \end{tabular}
    \legend{Fonte: O autor.}
\end{table}

Quando uma condição anômala é encontrada, o resultado se torna um alerta disponível na aplicação. A mensagem apresenta o comportamento observado, o método não estabelece diagnóstico definitivo, sua função é destacar desvios que justificam inspeção e acompanhamento.



No tópico de resultados:
\section{Detecção de anomalias e AutoCloud}

As regras determinísticas foram aplicadas antes da análise temporal para identificar sequências incompatíveis com o comportamento esperado das boias. Eventos duplicados, fora de ordem ou sem horário confiável foram sinalizados e impedidos de participar da formação dos ciclos de enchimento. Esse procedimento evitou que registros incoerentes alterassem a análise do tempo entre os níveis inferior e superior.

O AutoCloud foi executado sobre a variável \texttt{fill\_time\_seconds}. Nos testes realizados, o módulo processou os ciclos válidos e permitiu comparar novos tempos de enchimento com o comportamento registrado anteriormente. A integração possibilitou classificar o ciclo analisado e gerar um alerta quando o tempo se afastava do padrão histórico. Os valores quantitativos e a descrição do cenário final deverão ser inseridos após a consolidação dos experimentos.

% TODO: informar quantidade de ciclos, tempos observados e anomalia simulada.
% PRODUZIR CAPTURA do alerta e, se possível, do histórico de tempos de enchimento.
% Nome do arquivo: figs/autocloud_alerta_tempo_enchimento.png
\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/autocloud_alerta_tempo_enchimento.png}
    \caption{Exemplo de análise temporal e alerta produzido a partir do tempo de enchimento.}
    \legend{Fonte: O autor.}
    \label{fig:autocloud_alerta_tempo_enchimento}
\end{figure}

Os alertas apresentaram a condição identificada e possíveis causas relacionadas ao domínio físico, sem tratar a anomalia como diagnóstico definitivo. Dessa forma, o AutoCloud atuou como recurso de apoio para destacar mudanças que exigem verificação do usuário.


Tópico para o autocloud na Conclusão:

Entre os principais resultados do trabalho, destaca-se a aplicação do AutoCloud à análise temporal do tempo de enchimento. O módulo identifica três comportamentos de interesse, os ciclos lentos, as alterações persistentes e a formação de um novo padrão temporal. A análise utiliza uma base mínima de cinco ciclos válidos, considera lento o ciclo com duração igual ou superior a 1,5 vez a mediana histórica e avalia mudanças persistentes em uma janela de três ciclos. Dessa forma, o sistema destaca desvios que podem estar relacionados à redução da vazão, a obstruções ou a alterações no funcionamento do reservatório, sem apresentá-los como diagnóstico definitivo de falha.
