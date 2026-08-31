Implemente as alterações abaixo no projeto. O contexto técnico e as boas práticas já estão documentados  no `AGENTS.md` deste diretório.

### 1. Reorganização responsiva da Home na versão web

Reorganize a Home somente em telas de computador e notebook, utilizando os breakpoints e padrões responsivos já existentes no projeto. Não altere negativamente o layout mobile.

Nas telas web, aproveite melhor o espaço horizontal por meio de uma composição em duas colunas:

* Na coluna esquerda, concentre os componentes iniciais da Home até a visualização do nível do reservatório.
* Na coluna direita, organize:

  * botões de Histórico e Assistente IA, preferencialmente próximos ao topo;
  * último sensor alterado;
  * controle da bomba;
  * modo de acionamento;
  * energia da bomba.

A ordem e as dimensões podem ser refinadas de acordo com o que produzir o melhor resultado visual. Evite cards excessivamente largos, grandes espaços vazios e a simples distribuição de poucos componentes por toda a largura. O layout deve funcionar adequadamente em diferentes resoluções de notebooks e monitores.

A identificação da versão web deve ser feita pelas dimensões da viewport e pelos breakpoints da aplicação, não pelo sistema operacional ou pelo navegador.

### 2. Comportamento da barra superior

A barra azul com o título “AquaMonitor”, subtítulo e botão de ajuda não deve permanecer fixa durante a rolagem.

Ela deve:

* aparecer normalmente quando a página estiver no topo;
* sair da área visível conforme o usuário rolar a página para baixo;
* voltar a aparecer quando o usuário retornar ao topo.

Remova o comportamento `fixed` ou `sticky` e faça a barra participar do fluxo normal da página. Aplique o ajuste nas telas em que esse cabeçalho compartilhado é utilizado, verificando que o conteúdo não fique com margens ou espaços superiores incorretos.

### 3. Sincronização visual do estado da bomba

Corrija a origem e a atualização do estado da bomba na interface. Atualmente, quando a bomba é ligada automaticamente pela lógica dos sensores, o sistema inicia a contagem do enchimento e das métricas de energia, mas continua mostrando a bomba como desligada.

Quando a bomba estiver efetivamente ligada, independentemente de o acionamento ter sido automático, remoto ou físico, todas as representações devem ser atualizadas de maneira consistente:

* card de resumo acima do reservatório;
* indicador e botão ON/OFF do controle da bomba;
* campo “Estado atual” em Energia da bomba;
* cores, textos e demais indicadores relacionados.

Não faça apenas uma correção visual isolada. Investigue o fluxo completo entre eventos dos sensores, acionamento aplicado, estado confirmado, backend, MQTT e atualização do frontend. Use uma única fonte confiável para representar o estado operacional da bomba e evite que o botão mostre somente o último comando manual.

Valide, no mínimo, o fluxo observado no teste:

1. sensor alto desceu;
2. sensor baixo desceu;
3. sensor baixo subiu;
4. a bomba liga automaticamente;
5. todas as áreas da interface passam a indicar que ela está ligada.

Quando a bomba desligar, os mesmos componentes devem voltar ao estado desligado.

### 4. Alerta determinístico de intertravamento dos sensores

Revise as regras de sequência dos sensores. O sistema não está gerando alerta para a seguinte sequência inválida:

1. sensor baixo desceu;
2. sensor alto subiu sem que o sensor baixo tenha subido antes.

Essa transição não representa uma evolução física válida do nível. A sequência esperada para o enchimento é:

1. sensor baixo desceu;
2. sensor baixo subiu;
3. sensor alto subiu.

Portanto, se o sensor alto subir enquanto o sistema ainda registra o sensor baixo como não acionado, deve ser criado um alerta determinístico de intertravamento. O alerta precisa ser persistido e exibido em “Alertas inteligentes”, respeitando os mecanismos existentes de idempotência, reconhecimento e prevenção de duplicidades.

Revise também as regras relacionadas para garantir que o estado anterior realmente utilizado na validação corresponde ao estado atual confirmado dos dois sensores.

### 5. Filtros de Histórico e Estatísticas

Melhore a aparência e a usabilidade dos filtros:

* períodos: 7, 30 e 90 dias;
* tipos: Água, Energia e Sensores.

Atualmente, principalmente “Água”, “Energia” e “Sensores” parecem textos comuns e não deixam claro que são clicáveis.

Transforme cada opção em um controle visualmente identificável, com:

* contorno ou container;
* área clicável adequada;
* estados de `hover`, foco e seleção;
* boa legibilidade e acessibilidade;
* adaptação às versões web e mobile.

Mesmo antes da seleção, deve ficar evidente que cada item é clicável. Depois do clique, somente a opção ativa deve receber um destaque mais forte, deixando clara a seleção. Substitua o barramento preto atual por uma solução visual mais coerente com o restante da interface.

### 6. Remoção do bloco de Assistente IA do histórico

Remova da tela “Histórico e Estatísticas” o bloco localizado abaixo dos gráficos que contém:

* “Assistente IA”;
* “Analise os dados do período atual com perguntas em linguagem natural”;
* opção “Abrir Chat”.

Esse bloco é desnecessário. Não remova o botão de acesso ao Assistente IA existente na Home nem a rota e as funcionalidades do chatbot.

### 7. Correção do PDF

Corrija a geração do relatório PDF de Histórico e Estatísticas. Nos campos “Alertas recentes” e “Observações”, títulos, descrições e demais textos estão sobrepostos.

Ajuste:

* altura dinâmica dos itens conforme a quantidade de texto;
* quebra automática de linhas;
* espaçamento entre título, descrição, status e próximo alerta;
* espaçamento entre o cabeçalho “Observações” e seu conteúdo;
* margens e altura de linha;
* quebra de página quando o conteúdo não couber no espaço restante.

Nenhum texto pode ficar sobreposto, cortado ou fora da área da página. Valide o PDF com textos curtos e longos, vários alertas, nenhum alerta e os diferentes períodos disponíveis. Mantenha a paginação organizada, evitando páginas extras ou grandes espaços vazios quando for possível posicionar o conteúdo de forma segura.

### Validação final

Após implementar:

* preserve o funcionamento da versão mobile;
* valide a Home em mais de uma resolução web;
* confirme o desaparecimento natural do cabeçalho durante a rolagem;
* teste o acionamento automático da bomba e a sincronização de todos os indicadores;
* teste a sequência inválida dos sensores e a criação do alerta;
* confira os estados dos filtros;
* gere e inspecione o PDF corrigido;
* execute os testes, verificações de tipos e build disponíveis no projeto.

Ao final, apresente um resumo das alterações realizadas, arquivos modificados, testes executados e qualquer limitação ou pendência encontrada.
