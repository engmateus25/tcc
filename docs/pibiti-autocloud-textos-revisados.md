# Textos revisados para AutoCloud no PIBITI

Data de consolidacao: 2026-08-31.

Este arquivo consolida os trechos revisados sobre AutoCloud para as secoes de Metodologia, Resultados e Conclusao. Os textos abaixo ja consideram a implementacao atual do codigo, na qual o AutoCloud usa vetores normalizados de ciclos de enchimento e grava amostras na colecao `autocloud_filling_samples`.

## Metodologia

```latex
\section{Analise temporal com AutoCloud}

A analise temporal dos ciclos de enchimento foi implementada como uma camada posterior as regras deterministicas de consistencia. Inicialmente, cada evento recebido do reservatorio e validado para identificar problemas como ausencia de horario confiavel, duplicidade, chegada fora de ordem ou sequencia fisicamente incoerente entre as boias. Somente eventos que nao bloqueiam o processamento sao utilizados para formar ciclos de enchimento, evitando que leituras invalidas componham a base historica do algoritmo.

O ciclo de enchimento representa o intervalo entre o inicio efetivo do bombeamento e a chegada da agua ao limite superior. Para determinar o instante inicial, o \textit{backend} procura prioritariamente um comando de ligacao da bomba que tenha sido aplicado e confirmado. Quando essa confirmacao nao esta disponivel, utiliza-se como referencia a transicao da boia inferior. O encerramento do ciclo ocorre quando a boia superior e acionada. Assim, o tempo total de enchimento e calculado por:

\begin{equation}
    t_{enchimento} = t_{alto \uparrow} - t_{inicio}.
\end{equation}

Alem do tempo total, o sistema registra dois intervalos auxiliares. O primeiro corresponde ao tempo entre a boia inferior e a boia superior:

\begin{equation}
    t_{baixo\rightarrow alto} = t_{alto \uparrow} - t_{baixo \uparrow}.
\end{equation}

O segundo corresponde ao intervalo entre o inicio confirmado do bombeamento e a transicao da boia inferior:

\begin{equation}
    t_{bomba\rightarrow baixo} = t_{baixo \uparrow} - t_{inicio}.
\end{equation}

Cada ciclo valido e representado por um vetor de atributos:

\begin{equation}
    \mathbf{x} =
    [t_{enchimento},\,
    t_{baixo\rightarrow alto},\,
    t_{bomba\rightarrow baixo},\,
    s_{origem},\,
    s_{sequencia}].
\end{equation}

Os tres primeiros componentes sao temporais. O componente \(s_{origem}\) codifica a confiabilidade da origem do inicio do ciclo, assumindo valor 1,0 quando o ciclo inicia por comando de bomba aplicado e confirmado, 0,65 quando utiliza fallback por sensor e 0 quando a origem nao e reconhecida. O componente \(s_{sequencia}\) indica a completude da sequencia observada, assumindo valor 1,0 quando a transicao da boia inferior foi registrada, 0,5 quando apenas a relacao entre inicio e fim e conhecida, e 0 quando a sequencia esta incompleta.

Antes da clusterizacao, os atributos sao normalizados com base nas amostras historicas validas. Para cada atributo \(j\), calcula-se a mediana historica \(m_j\) e uma escala robusta \(\sigma_j^\ast\). Sempre que possivel, essa escala e obtida pelo intervalo interquartil, ajustado por 1,349; na ausencia de dispersao suficiente, utiliza-se o desvio padrao populacional ou uma escala minima. A normalizacao e dada por:

\begin{equation}
    \tilde{x}_j = \frac{x_j - m_j}{\max(\sigma_j^\ast, \epsilon)}.
\end{equation}

Com os vetores normalizados, o AutoCloud organiza incrementalmente os ciclos em nuvens de dados. Cada nuvem mantem a quantidade de amostras \(n_i\), o centro \(\mu_i\) e a variancia \(\sigma_i^2\). Para um novo ciclo, calcula-se a distancia normalizada em relacao as nuvens existentes:

\begin{equation}
    d_i = \frac{\lVert \tilde{\mathbf{x}} - \mu_i \rVert}{\sqrt{\sigma_i^2 + \epsilon}}.
\end{equation}

Quando a distancia para a nuvem mais proxima excede o limiar \(m\), configurado como 2,5, o ciclo pode formar uma nova nuvem. Caso contrario, o algoritmo avalia a pertinencia do ponto as nuvens existentes por meio da excentricidade normalizada. Para uma nuvem candidata atualizada com o novo ponto, a excentricidade e aproximada por:

\begin{equation}
    \xi_i =
    \frac{1}{n_i + 1}
    +
    \frac{\lVert \mu_i' - \tilde{\mathbf{x}} \rVert^2}
    {(n_i + 1)\sigma_i'^2}.
\end{equation}

A amostra e aceita por uma nuvem quando:

\begin{equation}
    \frac{\xi_i}{2} \leq \frac{m^2 + 1}{2(n_i + 1)}.
\end{equation}

O modulo somente emite conclusoes temporais apos existir uma base minima de cinco ciclos historicos validos. Alem da resposta do agrupamento, sao avaliadas condicoes de dominio para facilitar a interpretacao do resultado: ciclo lento quando o tempo atual e maior ou igual a 1,5 vez a mediana historica; mudanca persistente quando ha crescimento progressivo na janela recente de tres ciclos; e novo agrupamento temporal quando o ciclo se distancia estatisticamente do historico ou cria uma nova nuvem com distancia normalizada acima do limiar. Quando uma dessas condicoes e satisfeita, o resultado e persistido como alerta e exibido na interface com o tempo observado, a mediana historica, a diferenca percentual e a distancia normalizada do agrupamento.
```

## Resultados

```latex
\section{Deteccao de anomalias e AutoCloud}

O modulo AutoCloud foi validado sobre ciclos de enchimento persistidos no Firebase. A base tecnica utilizada para a demonstracao continha 12 amostras historicas validas na colecao \texttt{autocloud\_filling\_samples}, quantidade superior ao minimo de cinco ciclos exigido para iniciar a analise temporal. Em seguida, foi gerado um ciclo anomalo de 960 s, representando um enchimento mais demorado que o comportamento previamente observado.

Para esse experimento, a mediana historica calculada foi de 482,5 s. O ciclo analisado apresentou 960,0 s, resultando em diferenca absoluta de 477,5 s em relacao a mediana, isto e, aumento aproximado de 99,0\%. Como esse valor supera o criterio de ciclo lento, definido por \(t_{atual} \geq 1{,}5 \cdot \mathrm{mediana}\), o sistema gerou um alerta do tipo \texttt{slow\_fill\_cycle}. A execucao tambem indicou criacao de nova nuvem pelo AutoCloud, com distancia normalizada de 90,76 em relacao ao agrupamento mais proximo e total de tres nuvens apos a analise.

A interface passou a apresentar o alerta com informacoes quantitativas associadas ao desvio. O card exibido ao usuario mostra o tempo observado, o padrao historico baseado na mediana, a diferenca absoluta e percentual e a distancia normalizada do cluster. Esses dados tornam o alerta mais interpretavel, pois permitem identificar nao apenas que houve anomalia, mas tambem a magnitude do afastamento em relacao ao comportamento historico do reservatorio.

\begin{table}[H]
    \centering
    \caption{Resultado da demonstracao do AutoCloud para ciclo lento de enchimento.}
    \label{tab:resultado_autocloud_ciclo_lento}
    \small
    \begin{tabular}{|p{6.0cm}|p{6.0cm}|}
        \hline
        \textbf{Indicador} & \textbf{Valor observado} \\ \hline
        Amostras historicas disponiveis & 12 ciclos validos \\ \hline
        Tempo mediano historico & 482,5 s \\ \hline
        Tempo do ciclo analisado & 960,0 s \\ \hline
        Diferenca absoluta & 477,5 s \\ \hline
        Diferenca percentual & aproximadamente 99,0\% \\ \hline
        Tipo de alerta gerado & \texttt{slow\_fill\_cycle} \\ \hline
        Distancia normalizada do agrupamento & 90,76 \\ \hline
        Nuvens apos a analise & 3 \\ \hline
    \end{tabular}
    \legend{Fonte: O autor.}
\end{table}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/autocloud_alerta_tempo_enchimento.png}
    \caption{Alerta de ciclo lento gerado pelo AutoCloud a partir de um ciclo de enchimento de 960 s, comparado a mediana historica de 482,5 s.}
    \legend{Fonte: O autor.}
    \label{fig:autocloud_alerta_tempo_enchimento}
\end{figure}

Os resultados mostram que a analise temporal ficou integrada ao fluxo operacional do sistema. O alerta nao e apresentado como diagnostico definitivo de falha, mas como indicativo de desvio relevante que pode estar associado a reducao de vazao da bomba, obstrucao hidraulica, entrada de agua limitada ou atraso no acionamento da boia superior. Dessa forma, o AutoCloud atua como recurso de apoio a decisao, destacando ciclos que justificam inspecao ou acompanhamento pelo usuario.
```

## Conclusao

```latex
Entre os principais resultados do trabalho, destaca-se a aplicacao do AutoCloud a analise temporal dos ciclos de enchimento. A versao final do modulo nao utiliza apenas o tempo total de enchimento de forma isolada: cada ciclo e representado por um vetor com cinco atributos, incluindo tempo total, intervalo entre boia inferior e boia superior, intervalo entre inicio da bomba e boia inferior, origem do inicio do ciclo e completude da sequencia de sensores. Esses atributos sao normalizados por mediana e escala robusta antes da clusterizacao, reduzindo a influencia de unidades diferentes e de variacoes extremas.

Nos testes demonstrativos, o sistema utilizou 12 ciclos historicos validos e gerou alerta para um ciclo de 960,0 s, enquanto a mediana historica era de 482,5 s. O desvio de 477,5 s, equivalente a aproximadamente 99,0\%, levou a classificacao \texttt{slow\_fill\_cycle}. A distancia normalizada de 90,76 e a criacao de nova nuvem reforcaram que o ciclo analisado estava distante do comportamento previamente observado. Com isso, o AutoCloud mostrou-se adequado para destacar alteracoes relevantes no padrao temporal do reservatorio, mantendo a interpretacao final como apoio a verificacao humana e nao como diagnostico automatico conclusivo.
```

## Dados do alerta demonstrativo gerado

- `test_run_id`: `pibiti-20260831-144602`.
- Colecao de amostras: `autocloud_filling_samples`.
- Base usada: amostras existentes no Firestore.
- Amostras historicas disponiveis: 12.
- Ciclo lento gerado: 960,0 s.
- Mediana historica: 482,5 s.
- Diferenca: 477,5 s.
- Aumento percentual: 98,9637%, arredondado para 99,0%.
- Distancia normalizada do cluster: 90,7589, arredondada para 90,76.
- Nuvens apos a analise: 3.
- Alerta gerado: `slow_fill_cycle`.
- Intertravamento gerado nesta execucao: nenhum.

