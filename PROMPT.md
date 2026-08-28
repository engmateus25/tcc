Esse meu projeto de TCC também é um PIBITI (projeto de extensão e ensino), nele eu já fizum relatório parcial um tempo atráz, numa época qu o projeto estava no meio do desenvolvimento, hoje ele já está praticamente finalizado (mas como já chegou o prazo final de envio de relatório, tem-se que descrever o projeto como finalizado, parte física em laboratório, case 3D, chatboot assistente, alertasdeterminísticos e com autocloud, aplicação web/mobile convertida para android ficando pendente iOS....). Eu estou usando o chatgpt para fazer a escrita, ele já tem a janela de contexto com o padrão e modelo de relatório que eu quero. Então, eu quero de vc (agente codex) o seguinte: observe abaixo os pedidos do meu professor orientador sobre o atual estado do meu relatório final, precisarei mecher em resumo, metodologia, resultados e coclusão. Do relatório parcial para cá, eu já alterei apenas Metodologia e Conclusão, osoutros tópicos continuam com o texto do relatório parcial. 

Observações do meu professororientador:
a) Resumo e abstract precisam ser atualizados conforme os resultados finais (eles ainda estão com a descrição da proposta de desenvolvimento do projeto);

b) Metodologia: falta  explanar com mais detalhes como as ações são feitas; aplicação web, assistente de linguagem natural, autocloud,alertas determinísticos e com autocloud, etc... as informações estão muito rasas;

c) Resultados:  inserir os resultados finais e olhar se ainda existe qualquer tipo de situação onde você menciona resultados parciais; apresentar as informações de maneira quantitativa;

d) Conclusão: falta falar das informações mais quantitativas;

e) Ler o pdf por completo para identificar qualquer tipo de divergência



Então eu quero que vc invstigue dentro do projeto em documentação, codigos pertinentes, etc... As informações úteis para o desenvolvimento dos tópicos de interesse. Então vc vai investigar e deixar num .md as informações pertinentes para a complementação dos tópicoscque faltam, esse .md serácde alimentação para o chatgpt desenvolver o texto em latex. Também,eu quero que em outro arquivo, vc mesmo faça as incrementações nos tópicos de interesse, produzindo os textos e desixas umas estrutura mostada com sugestão de imagem onde vc achar que convém por imagem.



Abaixo deixo as seções de interesse do meu PIBITI, as seções de introdução e fundamentação teórica não precisam de alterações, logo, não as envio aqui.


Resumo:

A operação do abastecimento de água em condomínios depende de reservatórios, bombas e dispositivos de comando e proteção que precisam funcionar de forma contínua e segura. Entretanto, em muitos cenários, a supervisão do sistema ainda ocorre de maneira reativa, com pouca rastreabilidade e sem histórico confiável de eventos, o que dificulta o diagnóstico de falhas, aumenta custos de manutenção e pode favorecer desperdícios. Este relatório parcial apresenta o desenvolvimento de um sistema inteligente de baixo custo para monitorar e apoiar a gestão do abastecimento hídrico, integrando sensoriamento embarcado, comunicação por MQTT/HTTP, armazenamento em nuvem e aplicação \textit{web} para visualização em tempo quase real, histórico e controle remoto com validação por regras. Como resultados parciais, obteve-se um protótipo funcional em laboratório, com registro de comandos e eventos de sensores em banco de dados, telas de monitoramento e histórico com indicadores e gráficos, além da integração de um assistente em linguagem natural e da implementação inicial do módulo AutoCloud e de regras físicas por sequência de eventos para apoiar alertas. Foram observadas limitações relacionadas à instabilidade de rede, que podem ocasionar perda de eventos ou falhas de acionamento remoto. A continuidade do projeto inclui aprimorar a robustez da comunicação, finalizar a integração de alertas, realizar testes controlados de detecção de anomalias, solidificar a versão \textit{mobile} do app e avançar para implantação em condomínio real.


 \textbf{Palavras-chave}:  monitoramento; IoT; abastecimento hídrico; detecção de anomalias; manutenção preditiva; \textit{dashboard}.








\chapter{Metodologia}

\section{Etapas de desenvolvimento}

A metodologia adotada para o desenvolvimento do sistema inteligente é organizada
em etapas, de modo a garantir e validação progressiva dos componentes, antes da integração completa do sistema. Inicialmente, realiza-se a revisão bibliográfica e o levantamento dos requisitos relacionados ao monitoramento de reservatórios, à comunicação entre dispositivos IoT, ao armazenamento de eventos e à detecção de anomalias. Em seguida, monta-se um protótipo em laboratório para representar o funcionamento elétrico de um sistema de bombeamento predial em condições controladas.

Em seguida, o desenvolvimento do módulo embarcado baseado no ESP32, responsável pela leitura das boias de nível, sinalização do estado do reservatório, acionamento da bomba e transmissão dos eventos. Posteriormente, a implementação da comunicação MQTT, a persistência no Cloud Firestore, o \textit{backend} em FastAPI e a aplicação \textit{web}. A aplicação é então convertida para \textit{mobile} em sistema \textit{Android} por meio da ferramenta Capacitor, mantendo a mesma base de código da versão web.

Por fim, são incorporados o processamento dos ciclos de enchimento, as regras de consistência física, o AutoCloud e o assistente chatbot com LLM. A validação final é conduzida em bancada didática em laboratório, utilizando boias reais movimentadas manualmente para reproduzir as transições de nível.

\section{Arquitetura do sistema}

O sistema inteligente foi desenvolvido como uma arquitetura modular composta por quatro partes principais: módulo embarcado, serviços de comunicação e persistência, \textit{backend} de processamento e aplicação \textit{web/mobile}. Essa separação permite que a aquisição dos sinais físicos continue independente da interface, enquanto o processamento histórico e os recursos de inteligência são concentrados no \textit{backend}.

\begin{figure}[H]
    \centering
    \includegraphics[width=1.0\linewidth]{figs/Diagrama em blocos TCC.png}
    \caption{Diagrama em blocos do sistema.}
    \legend{Fonte: O autor.}
    \label{fig:diagrama_blocos_sistema}
\end{figure}

Conforme apresentado na Figura~\ref{fig:diagrama_blocos_sistema}, o ESP32 realiza a leitura das boias e o acionamento da bomba. Os eventos são armazenados no Cloud Firestore e os comandos em tempo real são trocados por MQTT. Uma função Firebase é executada quando um novo documento de sensor é criado e encaminha o evento ao \textit{backend} FastAPI. O \textit{backend} aplica as regras de negócio, organiza os ciclos de enchimento, gera alertas e fornece os dados utilizados pelos relatórios e pelo assistente de IA. A aplicação consulta esses serviços para apresentar o estado do reservatório, o histórico, as estimativas operacionais e os alertas ao usuário.

\section{Construção do módulo embarcado}

O módulo embarcado foi construído com um ESP32, duas boias de nível, um módulo de relés, três sinalizadores luminosos e uma chave seletora de acionamento físico. Após a validação inicial em protoboard, os componentes foram instalados em placa perfurada e acomodados em uma caixa produzida por impressão 3D. Os sinalizadores e a chave seletora foram fixados na tampa para permitir a visualização do nível e o comando local da bomba.

As duas boias representam os limites inferior e superior do reservatório. A combinação de seus estados permite classificar o nível como baixo, médio ou alto. O estado intermediário ocorre quando a boia inferior indica que a água ultrapassou o nível baixo, enquanto a boia superior ainda permanece desacionada. Os sinalizadores verde, amarelo e vermelho representam, respectivamente, os níveis de reservatório baixo, médio e alto.

\begin{table}[H]
    \centering
    \caption{Conexões utilizadas no módulo embarcado.}
    \label{tab:pinos_esp32}
    \small
    \begin{tabular}{|l|c|p{8.0cm}|}
        \hline
        \textbf{Elemento} & \textbf{Pino} & \textbf{Função} \\ \hline
        Boia de nível baixo & GPIO 18 & Detectar as transições associadas ao limite inferior. \\ \hline
        Boia de nível alto & GPIO 21 & Detectar as transições associadas ao limite superior. \\ \hline
        Acionamento da bomba & GPIO 22 & Comandar o relé responsável pelo acionamento. \\ \hline
        Retorno de estado da bomba & GPIO 23 & Confirmar o estado físico após o comando. \\ \hline
        Chave seletora & GPIO 25 & Forçar localmente a bomba a ligar ou desligar. \\ \hline
        Sinalização de nível baixo & GPIO 32 & Acionar o sinalizador verde. \\ \hline
        Sinalização de nível médio & GPIO 19 & Acionar o sinalizador amarelo. \\ \hline
        Sinalização de nível alto & GPIO 33 & Acionar o sinalizador vermelho. \\ \hline
    \end{tabular}
    \legend{Fonte: O autor.}
\end{table}

Para reduzir a influência de ruídos nas entradas, cada mudança é confirmada por uma segunda leitura após um intervalo de 15~ms. Caso as duas leituras sejam diferentes, a alteração é descartada. O horário do ESP32 é sincronizado por NTP e os eventos recebem marca temporal em UTC, facilitando a ordenação cronológica no banco de dados.

\section{Monitoramento e controle da bomba}

O funcionamento do sistema é orientado pelas transições das boias. Quando o nível atinge o limite inferior, é registrado um evento de nível baixo e o controle automático solicita o acionamento da bomba. Durante o enchimento, a liberação da boia inferior caracteriza o nível médio. Quando a boia superior é acionada, o nível alto é registrado e a bomba é desligada automaticamente.

A atuação foi implementada com a seguinte ordem de prioridade:

\begin{equation}
    \text{acionamento físico} > \text{comando remoto} > \text{controle automático}.
\end{equation}

A chave seletora força diretamente a bomba a ligar ou desligar e sobrescreve qualquer solicitação remota ou automática. Quando não há intervenção física, um comando recebido por MQTT prevalece sobre o modo automático. Na ausência dos dois modos anteriores, o acionamento é determinado exclusivamente pelas boias. Essa política evita que comandos concorrentes produzam estados indefinidos.

Após um comando de ligação, o \textit{firmware} aguarda por até cinco segundos a confirmação no pino de retorno da bomba. No desligamento, também é verificada a mudança do retorno para o estado inativo. O registro diferencia o estado solicitado do estado efetivamente aplicado e informa quando um comando foi impedido por uma prioridade superior. Dessa forma, o histórico não interpreta uma simples solicitação como funcionamento real da bomba.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\linewidth]{figs/Fluxograma TCC-convertido-de-svg.png}
    \caption{Fluxograma de monitoramento do sistema.}
    \legend{Fonte: O autor.}
    \label{fig:fluxograma_sistema}
\end{figure}

A Figura~\ref{fig:fluxograma_sistema} sintetiza a leitura das boias, a determinação do nível, a aplicação das prioridades, o acionamento da bomba e o registro dos eventos utilizados pelas etapas posteriores.

\section{Comunicação e persistência dos eventos}

O MQTT foi utilizado para o envio de comandos e para a confirmação do estado da bomba. O broker público HiveMQ foi configurado no endereço \texttt{broker.hivemq.com}. O ESP32 utiliza a porta 1883, enquanto a aplicação web/mobile estabelece conexão por WebSocket seguro na porta 8884. Os comandos remotos são publicados no tópico \texttt{bomba/controle} e as confirmações são retornadas pelo tópico \texttt{bomba/estado}.

Os eventos das boias e os registros da bomba são enviados ao Cloud Firestore. A comunicação utiliza mensagens em formato JSON, onde cada evento contém, entre outros campos, o sensor, a transição observada, um identificador único, o dispositivo de origem e os horários de criação e envio. Os registros da bomba incluem ainda o estado solicitado, o estado aplicado, a confirmação física e a prioridade que prevaleceu.

Para reduzir perdas durante falhas de conectividade, foi implementado no ESP32 um buffer circular com capacidade para 32 eventos. Quando o envio ao Firestore falha, o registro é armazenado localmente. Após o restabelecimento da conexão, os eventos pendentes são reenviados em ordem, com novas tentativas a cada cinco segundos. Caso o limite do buffer seja atingido, o evento mais antigo é removido para preservar os registros mais recentes e manter o uso de memória do ESP32 controlado.

\section{Processamento no backend e geração de alertas}

O \textit{backend} foi implementado em Python com FastAPI. Quando um novo documento é criado na coleção \texttt{sensores}, uma Firebase Function encaminha os dados ao endpoint de processamento. O evento é normalizado e reservado por uma chave segura calculada a partir de seu identificador. Assim, uma eventual repetição da Function não provoca a criação duplicada de ciclos ou alertas.

Em seguida, são aplicadas regras determinísticas baseadas na coerência física e temporal das boias. Entre as situações verificadas estão eventos duplicados em intervalo curto, registros fora de ordem, ausência de horário válido, repetição inesperada da boia inferior e acionamento incoerente da boia superior. Eventos considerados inválidos são registrados para análise, mas não participam do cálculo dos ciclos de enchimento.

Os dados foram organizados em coleções distintas no Firestore. A coleção \texttt{sensores} armazena as transições das boias, em \texttt{comandos} ficam os acionamentos da bomba, em \texttt{alerts} os alertas gerados, em \texttt{sensor\_event\_processing} o controle de idempotência, em \texttt{filling\_cycles} os ciclos válidos e em \texttt{chat\_sessions} as sessões/histórico do chatbot.

\section{Análise temporal com AutoCloud}

Os ciclos válidos de enchimento são formados entre a transição \texttt{baixo subiu}, que indica que o nível ultrapassou a boia inferior, e a transição \texttt{alto subiu}, correspondente à chegada ao limite superior. O tempo de enchimento é calculado por:

\begin{equation}
    t_{enchimento} = t_{alto\,subiu} - t_{baixo\,subiu}.
\end{equation}

O valor obtido é armazenado no Firebase e utilizado como entrada da análise temporal. O AutoCloud compara os ciclos recentes com o histórico de ciclos válidos para identificar tempos de enchimento acima do comportamento habitual, mudanças persistentes e formação de um novo padrão. A análise somente é iniciada após a obtenção da quantidade mínima de amostras configurada. Os alertas indicam anomalias e possíveis causas, como redução da vazão da bomba ou obstrução hidráulica, sem afirmar um diagnóstico definitivo.

\section{Aplicação web e versão Android}

A interface foi desenvolvida com Ionic, React, TypeScript e Vite. O aplicativo apresenta o nível estimado do reservatório, o estado confirmado da bomba, os alertas, o histórico e as estimativas operacionais. O Firebase Web SDK é utilizado para acompanhar os eventos persistidos, enquanto o MQTT realiza a troca de comandos com o ESP32. As requisições de relatórios, alertas e inteligência artificial são direcionadas ao \textit{backend} FastAPI.

A mesma base de código foi adaptada para Android por meio do Capacitor. Após a compilação dos arquivos web, o conteúdo foi sincronizado com o projeto Android e executado no Android Studio. A instalação e a depuração foram realizadas por cabo USB em um aparelho Android. Durante os testes em rede local, a URL do \textit{backend} foi configurada com o endereço IP do computador responsável pela execução da API.

\section{Assistente em linguagem natural}

O chatbot foi implementado no \textit{backend} para responder perguntas sobre eventos, períodos de nível baixo ou alto, consumo estimado, funcionamento da bomba, alertas, entre outros. Antes de consultar o modelo de linguagem, o sistema identifica a intenção e o período solicitado, consulta os dados estruturados e monta um contexto resumido. Essa separação mantém os cálculos no \textit{backend} e reduz a possibilidade de o modelo produzir valores sem correspondência com o histórico.

Foram configuradas duas formas de execução: um modelo local \texttt{qwen3:4b-instruct}, executado por meio do Ollama, e o modelo online \texttt{gemini-3.6-flash}, acessado por API online. Em ambos os casos, o modelo recebe a pergunta acompanhada do contexto produzido pelo sistema.

\section{Procedimento de validação experimental}

A validação foi realizada em bacada de laboratório, representando o circuito de acionamento do sistema de bombeamento. Foram utilizadas boias reais, porém sem o enchimento físico de um reservatório. As mudanças de nível foram simuladas movimentando manualmente as boias para cima e para baixo, reproduzindo as transições esperadas entre os estados baixo, médio e alto.

O procedimento contemplou verificação das entradas das duas boias, conferência da sinalização luminosa, acionamento automático nos limites inferior e superior, acionamento remoto por MQTT, sobrescrita dos modos remoto e automático pela chave seletora, confirmação do estado da bomba, persistência dos eventos, interrupção e restabelecimento da comunicação, visualização das informações na aplicação Android e execução dos módulos de alertas, AutoCloud e chatbot. Essa abordagem permitiu avaliar a integração ponta a ponta em condições controladas, sem afirmar equivalência completa com a operação de um condomínio real.














    
\chapter{Resultados}

\section{Ambiente Experimental em Laboratório}

Os resultados parciais deste trabalho são obtidos em ambiente de laboratório, por meio de um protótipo instrumentado que simula o sistema elétrico de bombeamento utilizado em condomínios. Essa abordagem permite observar o comportamento do sistema, validar a captura de eventos e testar o acionamento sob condições controladas, sem depender de intervenção em infraestrutura real. As Figuras~\ref{fig:lab_painel} e~\ref{fig:lab_visao_geral} apresentam a montagem do experimento e a interligação entre o painel didático, a bancada e os elementos de controle.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/lab_painel_conexoes.jpg}
    \caption{Painel e conexões do experimento em laboratório.}
    \legend{Fonte: O Autor.}
    \label{fig:lab_painel}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/lab_visao_geral.jpg}
    \caption{Visão geral do ambiente experimental com protótipo em operação.}
    \legend{Fonte: O Autor.}
    \label{fig:lab_visao_geral}
\end{figure}

A instrumentação utiliza um módulo embarcado conectado a um conjunto de acionamento e sinalização, permitindo registrar estados relevantes e executar o acionamento do sistema conforme regras e permissões. As Figuras~\ref{fig:lab_close_embarcado} e~\ref{fig:lab_operacao_manual} destacam o módulo embarcado e os elementos de apoio utilizados durante a operação e observação do protótipo.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.85\linewidth]{figs/lab_close_embarcado_reles.jpg}
    \caption{Módulo embarcado e placa de relés utilizados na instrumentação e acionamento.}
    \legend{Fonte: O Autor.}
    \label{fig:lab_close_embarcado}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/lab_operacao_manual.jpg}
    \caption{Operação e verificação do protótipo durante o experimento em laboratório.}
    \legend{Fonte: O Autor.}
    \label{fig:lab_operacao_manual}
\end{figure}

\section{Interface \textit{Web} e Monitoramento em Tempo Real}

A aplicação \textit{web} foi implementada para apresentar o estado do sistema de forma simples e acessível, reunindo informações de operação em tempo real e indicadores derivados do histórico. A Figura~\ref{fig:tela_home_nivel} mostra o painel principal, com a visualização do nível do reservatório e o estado da bomba. Nesta etapa do projeto, o valor exibido para volume é estimado, uma medição mais precisa por sensor de vazão e planejada para continuidade do trabalho.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/web_home_nivel_reservatorio.jpg}
    \caption{Tela principal da aplicação \textit{web} com nível do reservatório e status operacional.}
    \legend{Fonte: O Autor.}
    \label{fig:tela_home_nivel}
\end{figure}

Além do painel de nível, a interface oferece recursos de controle e informações operacionais adicionais, como modo de acionamento e estimativas relacionadas ao funcionamento. A Figura~\ref{fig:tela_controle_bomba} apresenta o controle da bomba e a indicação do modo de acionamento configurado, além de uma estimativa de consumo energético calculada a partir do tempo de funcionamento e da potência nominal considerada nesta fase do protótipo.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/web_controle_bomba_estimativas.jpg}
    \caption{Controle da bomba, modo de acionamento e estimativas operacionais na aplicação \textit{web}.}
    \legend{Fonte: O Autor.}
    \label{fig:tela_controle_bomba}
\end{figure}

\section{Histórico e Estatísticas}

O sistema registra telemetria e eventos em nuvem, permitindo consulta do histórico e geração de estatísticas por período. As Figuras~\ref{fig:historico_cards} e~\ref{fig:historico_grafico_hora} ilustram a tela de histórico e estatísticas, com filtros por período e gráficos que sintetizam consumo de água e estimativas de energia associadas à operação do bombeamento. Esse histórico fornece rastreabilidade e permite observar padrões de uso ao longo do tempo, o que é fundamental para análises posteriores e para suporte a alertas.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/web_historico_cards_periodo.jpg}
    \caption{Tela de histórico e estatísticas com indicadores e filtros por período.}
    \legend{Fonte: O Autor.}
    \label{fig:historico_cards}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/web_historico_consumo_hora.jpg}
    \caption{Gráfico de consumo por hora na tela de histórico e estatísticas.}
    \legend{Fonte: O Autor.}
    \label{fig:historico_grafico_hora}
\end{figure}


\section{Persistência em Nuvem e Organização do Histórico}

O acompanhamento do sistema é sustentado por uma estrutura de dados em nuvem organizada por coleções, permitindo registrar comandos, eventos de sensores, dados do módulo de anomalias e interações do assistente. A Figura~\ref{fig:firestore_collections} apresenta a visão do banco de dados, evidenciando quatro coleções principais: \textit{comandos} (acionamentos de liga/desliga com modo e horário), \textit{sensores} (mudanças de estado dos sensores baixo/alto com horário), \textit{autocloud} (informações armazenadas a cada etapa de clusterização/análise) e \textit{chat\_sessions} (perguntas e respostas do chatbot, registradas para aprimoramento).

\begin{figure}[H]
    \centering
    \includegraphics[width=0.98\linewidth]{figs/firestore_colecoes.jpg}
    \caption{Estrutura do banco de dados em nuvem com coleções para comandos, sensores, AutoCloud e sessões do chatbot.}
    \legend{Fonte: O Autor.}
    \label{fig:firestore_collections}
\end{figure}



\section{Assistente em Linguagem Natural}

Como funcionalidade adicional, foi integrada uma interface de chatbot para suporte ao usuário e consulta de informações do sistema em linguagem natural. Nesta etapa, a execução local utiliza um modelo leve via Ollama (\texttt{qwen2:0.5b}), escolhido por limitações de memória no ambiente de desenvolvimento. A Figura~\ref{fig:chatbot_exemplo} mostra um exemplo de consulta e resposta baseada no histórico de eventos, que consiste contagem de ocorrências associadas ao sensor de nível. Para continuidade do projeto, permanece prevista a avaliação com modelos mais robustos e uso de APIs externas, bem como aprimoramentos na estratégia de interpretação de intenção e formatação de respostas com \textit{frameworks} como LangChain.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/web_chatbot_exemplo.jpg}
    \caption{Exemplo de consulta ao assistente e resposta baseada no histórico do sistema.}
    \legend{Fonte: O Autor.}
    \label{fig:chatbot_exemplo}
\end{figure}

\section{Implementação dos Módulos de Anomalias e Regras Físicas}

Além do monitoramento e do histórico, foram iniciadas implementações voltadas à detecção de anomalias e geração de alertas. A Figura~\ref{fig:codigo_autocloud_regras} apresenta dois trechos relevantes, sendo uma parte do algoritmo matemático do AutoCloud, já integrada ao \textit{backend} para processamento do histórico, e um conjunto de regras físicas baseadas na ordem e consistência da sequência de eventos dos sensores, para detecção de combinações incoerentes entre estados do sensor baixo e do sensor alto, auxiliando em nos alertas inteligentes.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.98\linewidth]{figs/codigo_autocloud_regras.jpg}
    \caption{Trechos do código: algoritmo do AutoCloud (esquerda) e regras físicas por sequência de eventos dos sensores (direita).}
    \legend{Fonte: O Autor.}
    \label{fig:codigo_autocloud_regras}
\end{figure}

Nesta etapa do relatório parcial, o AutoCloud encontra-se implementado e em evolução, porém ainda carece de mais testes e aprimoramento para avaliação prática do seu desempenho com cenários controlados de falha.








%\begin{table}[h!]
%\centering
%\begin{tabular}{|>{\raggedright}m{3cm}|>{\centering\arraybackslash}m{3cm}|>{\centering\arraybackslash}m{3cm}|}
%\hline
%\textbf{Tipo de ferramenta} & \textbf{\% Acerto em Setas} & \textbf{\% Acerto em caracteres} \\
%\hline
%Resnet + Easyocr & 100 & 89,52 \\
%\hline
%Resnet + pytesseract & 100 & 46,77 \\
%\hline
%SVM + Easyocr & 18,18 & 89,52 \\
%\hline
%SVM + pytesseract & 18,18 & 46,77 \\
%\hline
%YOLO + Easyocr & 90,91 & 89,52 \\
%\hline
%YOLO + pytesseract & 90,91 & 46,77 \\
%\hline
%Tangente + Easyocr & 0 & 89,52 \\
%\hline
%Tangente + pytesseract & 0 & 46,77 \\
%\hline
%\end{tabular}
%\caption{Resultados de acerto para diferentes combinações de ferramentas}
%\label{tab:resultados}
%\end{table}


\begin{comment}

\section{Como criar uma definição}

\begin{defi}
Uma Topologia sobre o conjunto $X$ é uma família $\tau
\subset \beta(X)$ que satisfaz $ \mathbb{S} $:
\begin{enumerate}
 \item$\emptyset,X$ pertencem a $\tau;$
 \item Seja  $\{A_{\alpha} \in \tau /\alpha \in \Gamma\}$
 uma família arbitrária de subconjuntos de  $\tau$ então, a união dos elementos dessa família ainda pertence a  $\tau$, ou seja, $\bigcup \limits_{\alpha \in \Gamma} A_{\alpha}\in\tau;$
 \item Sejam $B_{1},B_{2},B_{3},..., B_{n} \in \tau$ uma família finita de subconjuntos de $\tau$, com $n \geq 1$, então
 interseção dessa família ainda pertence a $\tau$, ou seja, $\bigcap\limits_{i=1}^{n} B_{i}\in \tau.$
\end{enumerate}
\end{defi}

\section{Como criar uma observação}

\begin{obs}

\item Os elementos da Topologia  $\tau$ caracterizam os Conjuntos Abertos de $X.$

\item O par ordenado $(X,\tau)$ é chamado de Espaço Topológico.

\item Sim, de fato:

\item i) $\emptyset, X \in \tau$, pois são subconjuntos de $X;$

\item ii) Seja \{$J_{\lambda}\}_{\lambda\in L}$ temos que$J_{\lambda}\in \tau$ então $\bigcup\limits_{\lambda\in L} J_{\lambda}$ é
    um subconjunto de $X$ e portanto, pertence a $\tau;$

\item iii) Sejam $J_{1},J_{2},...J_{n} \in \tau$ temos que $J_{1}\bigcap J_{2}\bigcap ...J_{n}$ é um suconjunto de $X$ e portanto pertence a $\tau.$

\end{obs}

\section{Como criar um exemplo}

\begin{ex}{Topologia Euclidiana ou Usual} - $\tau_{us}$

Essa topologia é formada por intervalo do $\mathbb{R}^{n}$
Os dois tipos mais estudados são a Topologia Euclidiana Usual na Reta (ou  de $\mathbb{R}$) e a Topologia Euclidiana Usual (ou do  no Plano Complexo (ou do $\mathbb{R}^{2}$).

Seja a topologia $\tau = \{A \subset \mathbb{R}\}, \emptyset\}$ onde $X = \mathbb{R}$, dizemos que $A \in \tau$, se e somente se, para todo $y \in A$, existe um intervalo aberto $(c,d)$ tal que
$y \in (c,d) \subset A.$

\item i) É fácil notar que $\mathbb{R}, \emptyset \in \tau;$

\item ii) Consideremos a família $\{A_{\alpha} \in \tau / \alpha \in\tau\},$
queremos mostrar que, $\bigcup\limits_{\alpha\in \Gamma} A_{\alpha}\in \tau.$

De fato, considerando $y \in \bigcup\limits_{\alpha\in \Gamma} A_{\alpha}$ ,
desse modo, existe $\alpha_{0} \in \Gamma$ tal que $y \in A_{\alpha_{0}} \in \tau$, assim, existe $(c,d)$ e
temos que $y\in (c,d) \subset A_{\alpha_{0}}\subset \bigcup\limits_{\alpha\in \Gamma}A_{\alpha}.$

\item iii) Consideremos $B_{1},B_{2}$ subconjuntos finitos de $\tau$, desse modo
tomemos $y \in B_{1}\bigcap B_{2}$, assim $y\in B_{1}$ e $y\in B_{2}$,
logo existem $(c_{1}, d_{1})$ e $(c_{2}, d_{2})$ tais que $y$
$\in0 (c_{1}, d_{1}) \subset B_{1}$ e $y\in (c_{2}, d_{2}) \subset B_{2}.$

Vamos denotar por $c = max(c_{1},c_{2})$ e $d = min(d_{1},d_{2})$, assim temos:

\begin{center}
 $y \in (c,d) \subset B_{1} \bigcap B_{2}$
\end{center}
 
Por indução temos  se $B_{1},B_{2},..., B_{n}$ são conjuntos finitos de $\tau$, então, $\bigcap\limits_{i=1}^{n}B_{i}\in\tau.$
\end{ex}

\section{Como criar um teorema}

\begin{teo}: Seja $(X,\tau)$ um espaço topológico e $ \mathfrak{F}$ a
família de conjuntos fechados, então:
\begin{description}
  \item[i)]$\emptyset, X$ pertencem a $ \mathfrak{F}$;
  \item[ii)]Considere $F_{1}, F_{2},..., F_{n}$ conjuntos fechados
  em $X$; então a união finita $\bigcup\limits_{i=1}^{n} F_{i}$ é fechada
  em $X$;
  \item[iii)]Considere $\{ F_{\alpha} \in \mathfrak{F} / \alpha \in
  \Gamma\}$ uma família de elementos arbitrários de $\mathfrak{F}$,
  então, a interseção arbitrária $\bigcap\limits_{\alpha \in \Gamma}F_{\alpha}$ pertence a $\mathfrak{F}.$
\end{description}
\end{teo}

\section{Como criar uma Prova}

 \begin{prova}~

 \item i) $\emptyset$ e $X$ pertencem a $\mathfrak{F}$, pois seus
   complementares pertencem a $\tau$.
 \item ii) Se $F_{i}$ é fechado para $i = 1,...,n$. Utilizando a Lei de Morgan, temos:
   \begin{center}
   $(\bigcup\limits_{i=1}^{n} F_{i})^{c} = \bigcap\limits_{i=1}^{n} (F_{i})^{c}$
   \end{center}
   
   Como a interseção $(F_{i})^{c}$ é  um aberto, pois, a interseção
   de conjuntos abertos é aberta, portanto, $\bigcup\limits_{i=1}^{n} F_{i}$ é fechada
   em $X.$
  \item iii) Seja $\{F_{\alpha \in \mathfrak{F} / \alpha \in
   \Gamma}\}$ uma família arbitrária de conjuntos fechados.

  Utilizando a Lei de Morgan, temos:
   \begin{center}
   $(\bigcap_{\alpha \in \Gamma} F_{\alpha})_{c} = \bigcup\limits_{\alpha \in
   \Gamma} F_{\alpha}^{c}$
   \end{center}
   
   Sabemos que $(F_{\alpha})^{c}$ é aberto, assim, a união de
   conjuntos abertos é aberta, então, podemos concluir que $\bigcap\limits_{\alpha \in
   \Gamma}F_{\alpha}$ é fechado em $X$.
 \end{prova}
\end{comment}









\chapter{Conclusão}


Este trabalho tem como foco o desenvolvimento de um sistema inteligente de baixo
custo para monitoramento e apoio à gestão de reservatórios de água. A solução integra um módulo embarcado baseado no ESP32, duas boias de nível, acionamento por relés, sinalização luminosa, chave seletora, comunicação MQTT, armazenamento no Cloud Firestore, \textit{backend} em FastAPI e aplicação web/mobile. A construção modular permite registrar eventos das boias e da bomba, acompanhar o histórico operacional, realizar acionamentos e disponibilizar informações ao usuário em uma única interface.

A validação em laboratório é realizada com boias reais movimentadas manualmente no painel didático para reproduzir os estados baixo, médio e alto. Nesse ambiente, verifica-se o funcionamento da sinalização, do controle automático, dos comandos remotos e do acionamento físico. A prioridade atribuída à chave seletora permite sobrescrever os modos remoto e automático, enquanto o registro do estado solicitado, aplicado e confirmado aumenta a rastreabilidade das operações. A montagem em placa perfurada e a instalação em uma caixa produzida por impressão 3D também resultam em um protótipo mais organizado e protegido que a versão inicial em protoboard.

As melhorias de comunicação reduzem uma das principais limitações observadas no relatório parcial. O buffer circular implementado no ESP32 permite armazenar temporariamente eventos que não podem ser enviados e retransmiti-los após o restabelecimento da conexão. Em conjunto com os identificadores únicos e o processamento idempotente no \textit{backend}, esse mecanismo diminui o risco de perda e duplicação de registros. As regras determinísticas impedem que sequências fisicamente incoerentes contaminem os ciclos de enchimento, enquanto o AutoCloud fornece uma camada de análise temporal sobre o tempo necessário para o nível passar da boia inferior à superior. Dessa forma, o sistema detecta comportamentos anômalos e apresenta possíveis causas, sem caracterizá-los como diagnóstico definitivo de falha.

A aplicação também dispõe de uma versão para Android, gerada por meio do Capacitor e executada em aparelho físico, permitindo o uso das principais funções fora do navegador. O assistente em linguagem natural é integrado em duas configurações: o modelo local \texttt{qwen3:4b-instruct}, executado pelo Ollama, e o modelo online \texttt{gemini-3.6-flash}. A consulta prévia dos dados estruturados pelo \textit{backend} mantém as contagens, os tempos e as estimativas sob responsabilidade da aplicação, utilizando os modelos de linguagem principalmente para apresentar essas informações de forma mais acessível ao usuário.

Os resultados permitem concluir que o protótipo atende ao objetivo de integrar monitoramento, acionamento, persistência, análise temporal e interação em linguagem natural em um sistema funcional de laboratório. Entretanto, a validação não contempla a instalação em condomínio, o enchimento hidráulico de um reservatório real, a medição direta de vazão ou a compilação para iOS. Por isso, os valores de consumo de água e energia apresentados permanecem estimativas baseadas em parâmetros configuráveis. Como continuidade, recomenda-se avaliar o sistema em campo, incorporar sensores de vazão e medição elétrica, ampliar os testes quantitativos do AutoCloud e dos modelos de linguagem e validar o aplicativo em outras plataformas. Essas etapas permitirão verificar o comportamento da solução sob variações reais de consumo, conectividade e operação prolongada.

