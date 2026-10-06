# Atividades de desenvolvimento de produto

Tema: Matrícula não garante inclusão. Professor: Adson Rezende. Turma: 303 - A. Planejamento consolidado em 05/10/2026.

Produto: plataforma web de análise e adaptação orientada de documentos didáticos. Os nomes abaixo descrevem as possibilidades de conceito; a marca comercial ainda poderá ser definida.


## Base comum aos conceitos

**Problema/oportunidade:** Professores do ensino médio regular nem sempre recebem formação específica para reconhecer e corrigir barreiras de acessibilidade em documentos, slides, atividades e avaliações. A falta de conhecimento, familiaridade e tempo dificulta a preparação desses materiais. O problema central do projeto é a dificuldade de integrar, com qualidade, os conteúdos escolares às tecnologias assistivas utilizadas pelos estudantes cegos e com baixa visão.

**Usuário principal:** Professor do ensino médio regular. Beneficiário final: estudante cego ou com baixa visão.

**Proposta de valor:** Ajudar o professor a preparar materiais mais acessíveis, compreender as barreiras e suas correções e ganhar autonomia e rapidez ao longo do trabalho. O aprendizado é um benefício esperado, sem atribuição de notas ao professor ou medição obrigatória de seu aprendizado.


## Contexto mínimo fornecido pelo professor

**Disciplina:** Área em que o material será utilizado.

**Tipo de atividade:** Prova, atividade, tarefa de sala, material de estudo ou apresentação.

**Necessidades do estudante:** Informações conhecidas pelo professor sobre como o estudante acessa os conteúdos.

**Tecnologias assistivas:** Recursos que o estudante efetivamente utiliza; não são deduzidos pelo arquivo.

Informações detalhadas sobre conteúdo, objetivo pedagógico e preferências do estudante são complementares. O professor precisa conhecer o estudante antes de definir as adaptações.


## Materiais e forma de acesso

Documentos de texto e apresentações são as duas categorias principais: PDF, arquivos do Word (prioritariamente DOCX) e PowerPoint (PPTX). Imagens inseridas nesses materiais fazem parte da análise. Imagens enviadas separadamente e páginas digitalizadas integram o escopo planejado; a cobertura de formatos e funções será desenvolvida e verificada por etapas.

Acesso pelo navegador, com execução local na primeira versão de teste. A plataforma parte do material que o professor já possui e preserva sua decisão final.


# Conceito 1: Verificador educativo de materiais

**Nome do conceito:** Verificador educativo de materiais

**Problema/oportunidade:** Dificuldade de perceber as barreiras do material e compreender por que prejudicam o acesso ao conteúdo.

**Usuário principal:** Professor do ensino médio regular. Beneficiário final: estudante cego ou com baixa visão.

**Proposta de valor:** Oferecer um diagnóstico explicado e um relatório que ajudem o professor a reconhecer os problemas e aprender a corrigi-los.

**Como funciona?:** O professor envia o arquivo e o contexto mínimo. A plataforma identifica possíveis barreiras, localiza os problemas e explica suas consequências. O professor corrige no programa original e pode reenviar uma nova versão.

**Principais características:** Análise contextualizada; localização dos problemas; explicações e recomendações; relatório para baixar; acompanhamento da nova versão.

**Principal diferencial:** Organizar a verificação em torno do estudante e da atividade escolar, com linguagem educativa e orientações para preparar os próximos materiais.

**Observações:** A correção ocorre principalmente fora da plataforma. Favorece um começo com diagnóstico e relatório, mantendo o professor responsável pela revisão.


## Representação visual pretendida

Esboço ilustrativo do conceito, sem resultados de testes.

Arquivo e contexto -> diagnóstico explicado -> relatório -> correção externa -> nova verificação. Esboço de tela: lista de problemas por localização, explicação e recomendação.


# Conceito 2: Assistente de adaptação guiada

**Nome do conceito:** Assistente de adaptação guiada

**Problema/oportunidade:** Dificuldade de transformar o diagnóstico em uma correção prática e verificar se as alterações resolveram as barreiras.

**Usuário principal:** Professor do ensino médio regular. Beneficiário final: estudante cego ou com baixa visão.

**Proposta de valor:** Acompanhar o professor na revisão, permitindo compreender, corrigir e conferir os problemas no próprio fluxo de trabalho.

**Como funciona?:** Após enviar arquivo e contexto, o professor escolhe a visualização. Pode corrigir os elementos compatíveis na plataforma ou editar o arquivo original e reenviá-lo. A análise da versão revisada mostra problemas resolvidos, pendentes e novos.

**Principais características:** Original e versão marcada lado a lado; revisão de um problema por vez; relatório geral; correção orientada; histórico e comparação entre versões.

**Principal diferencial:** Conectar a explicação ao ponto exato do material e acompanhar a revisão pelo professor, respeitando a finalidade pedagógica e o perfil do estudante.

**Observações:** É a base do conceito geral. Edição, localização e comparação dependem do formato; funções sem suporte precisam ser informadas claramente ao professor.


## Representação visual pretendida

Esboço ilustrativo do conceito, sem resultados de testes.

Original | versão com marcações; ao selecionar um problema, abrir explicação, sugestão e ação de correção. Alternativamente, conduzir o professor por uma barreira de cada vez.


# Conceito 3: Adaptador assistido de materiais

**Nome do conceito:** Adaptador assistido de materiais

**Problema/oportunidade:** Falta de tempo para realizar adaptações, especialmente quando há várias barreiras ou materiais a preparar.

**Usuário principal:** Professor do ensino médio regular. Beneficiário final: estudante cego ou com baixa visão.

**Proposta de valor:** Propor uma versão adaptada com mais rapidez, mantendo as explicações e a aprovação do professor.

**Como funciona?:** O professor fornece o material e o contexto e solicita a adaptação. A plataforma sugere alterações ou gera uma versão revisada, registra o que mudou e apresenta itens que exigem revisão. O professor confere e aprova antes do uso.

**Principais características:** Geração opcional de adaptações; comparação entre original e proposta; explicações das mudanças; revisão e aprovação pelo professor; verificação posterior.

**Principal diferencial:** Combinar a assistência à adaptação com o contexto escolar, o perfil do estudante e a preservação do objetivo da atividade.

**Observações:** É um recurso adicional. A automação não deve alterar a exigência da avaliação nem entregar respostas ao estudante. A abrangência depende da validação de cada tipo de alteração.


## Representação visual pretendida

Esboço ilustrativo do conceito, sem resultados de testes.

Original e contexto -> solicitar adaptação -> versão proposta e explicações -> revisão do professor -> verificação e aprovação.


# Comparação dos conceitos

Comparação das características previstas para as três alternativas. As avaliações são hipóteses de projeto e serão revistas após os testes; não representam medições de desempenho já realizadas.

| Critério | Conceito 1 | Conceito 2 | Conceito 3 |
|---|---|---|---|
| Qualidade da acessibilidade | Identifica barreiras e orienta; a melhoria depende da correção externa e da verificação posterior. | Conecta diagnóstico, correção e nova verificação; favorece acompanhar a melhoria do material. | Propõe adaptações; a qualidade depende da precisão das alterações e da revisão do professor. |
| Aprendizado e autonomia | Explicações podem ajudar o professor a reconhecer e evitar erros nos próximos materiais. | Explicação e prática de correção ficam próximas; o professor participa das decisões. | Explicações ficam disponíveis, mas o uso automático exige cuidado para manter a participação do professor. |
| Facilidade de uso | Fluxo mais enxuto, com relatório; exige alternar com o programa de edição. | Oferece três modos e revisão localizada; a interface precisa manter essa variedade compreensível. | Reduz ações manuais, mas exige uma forma clara de revisar e aprovar as alterações. |
| Rapidez | Concentra os problemas em um relatório; a correção permanece manual. | Revisão por problema e acompanhamento das versões podem reduzir retrabalho. | Pode acelerar alterações apoiadas; revisão e casos complexos continuam necessários. |
| Viabilidade de implementação | Requer importação, verificações, explicações e relatório; concentra um conjunto inicial de funções. | Acrescenta marcações, edição e comparação de versões; exige desenvolvimento por formato. | Acrescenta geração e exportação das adaptações; exige validação técnica e pedagógica de cada função. |

## Síntese da avaliação

O verificador educativo fornece a base de diagnóstico e explicação. O assistente de adaptação guiada é o núcleo escolhido para integrar análise, participação do professor e revisão das versões. O adaptador assistido será uma opção complementar para tarefas em que a automação possa ser revisada com segurança. Assim, a escolha final reúne as contribuições dos três conceitos, com desenvolvimento por etapas.

Não serão atribuídos pesos. Aprendizado e autonomia avaliam o potencial formativo do conceito; a plataforma analisa o material e não atribui notas ao professor.


# Conceito geral do produto

**Conceito GERAL:** Plataforma web de análise e adaptação orientada de documentos didáticos para estudantes cegos e com baixa visão. O professor informa o contexto da atividade e as necessidades e tecnologias assistivas do estudante. A plataforma identifica e explica barreiras, recomenda correções e permite trabalhar por visualização lado a lado, passo a passo ou relatório geral. O professor pode corrigir na plataforma ou no arquivo original, reenviar versões e acompanhar a resolução dos problemas. Uma função adicional pode propor uma versão adaptada, sujeita à revisão e aprovação do professor. A primeira versão será um site executado localmente para testes.


## Justificativa da conceituação geral

**Qualidade da acessibilidade:** A análise considera o estudante real e o uso pedagógico do material. A revisão das versões permite acompanhar se as alterações resolvem as barreiras sem mudar o objetivo da atividade.

**Aprendizado e autonomia:** Localizar, explicar e orientar cada correção ajuda o professor a compreender seus erros e evitá-los em novos materiais. A ferramenta atua como apoio formativo temporário, sem avaliar ou dar notas ao professor.

**Facilidade de uso:** Os três modos apresentam a mesma análise de formas diferentes, permitindo que o professor escolha a organização mais útil para seu trabalho.

**Rapidez:** Problemas localizados, revisão orientada e comparação entre versões reduzem a repetição de etapas. A adaptação assistida oferece um caminho adicional para tarefas que precisem de maior rapidez.

**Viabilidade de implementação:** O site local permite testar o fluxo com o grupo e ampliar a avaliação. Importação, verificações, edição e adaptação serão implementadas progressivamente, com cobertura explícita para cada formato.


## Fluxo integrado pretendido

Fluxo: enviar arquivo e contexto -> receber diagnóstico -> corrigir ou solicitar adaptação -> verificar a versão revisada -> revisar e aprovar para o uso.

A correção orientada é o caminho principal. A geração de adaptações permanece uma opção adicional para acelerar tarefas, com revisão das mudanças e preservação do objetivo pedagógico.


# Funcionalidades e formas de uso

**Contexto obrigatório:** Solicitar disciplina, tipo de atividade, necessidades do estudante e tecnologias assistivas. Conteúdo, objetivo pedagógico e preferências detalhadas podem ser acrescentados.

**Diagnóstico contextualizado:** Verificar barreiras relacionadas a texto, legibilidade, contraste, imagens, descrições, estrutura e leitura por tecnologias assistivas, conforme a cobertura implementada. Gráficos, tabelas e fórmulas exigem atenção ao sentido e ao objetivo pedagógico.

**Orientação para cada problema:** Apresentar localização, evidência, motivo da barreira e sugestão de correção. Identificar itens que dependem de revisão humana.

**Três modos de trabalho:** Original e versão marcada lado a lado; um problema por vez; relatório geral para baixar. Marcações visuais também terão identificação textual.

**Duas formas de corrigir:** Editar elementos apoiados dentro da plataforma ou corrigir o arquivo original e reenviá-lo. Preservar o original e permitir a revisão das mudanças.

**Verificação entre versões:** Mostrar barreiras resolvidas, pendentes e novas, com foco nas alterações e sem repetir desnecessariamente explicações já apresentadas.

**Adaptação assistida opcional:** Propor correções ou uma versão adaptada para o professor revisar e aprovar. Preservar o conteúdo e a finalidade da atividade.

**Interface acessível:** Planejar navegação por teclado, identificação de controles, leitura por leitor de tela, ampliação e informação compreensível sem depender somente de cores.


## As três visualizações pertencem ao mesmo produto

Lado a lado, passo a passo e relatório geral são formas de apresentar e trabalhar com a mesma análise. Elas não substituem os três conceitos comparados na matriz: diagnóstico educativo, correção guiada e adaptação assistida.

O professor escolhe o modo mais útil. Ao receber uma segunda versão, o sistema apresenta a evolução das barreiras detectadas, mantendo os problemas identificados em texto e por localização.


# Plano de testes e observações

O teste começa com o grupo e poderá envolver outras pessoas da escola, conforme disponibilidade e interesse. Os convites serão feitos pelo próprio grupo.


## 1. Grupo

Materiais de exemplo, incluindo versões com barreiras conhecidas e versões corrigidas. Conferir envio, contexto, localização, explicações, três modos, relatório e reenvio de versões.


## 2. Professor

Um professor da escola, conforme disponibilidade. Verificar clareza das orientações, esforço de correção e adequação ao preparo de aulas e avaliações.


## 3. Estudante cega

Convidar a colega da escola, conforme disponibilidade e interesse. Testar o acesso aos materiais com a tecnologia assistiva que ela utiliza e identificar barreiras que a análise não apontou.


## 4. Professora especialista

Convidar a professora com doutorado na área de acessibilidade. Revisar diagnóstico, adaptações, explicações e preservação dos objetivos pedagógicos.


## O que será observado nos testes

Comparar original e versão corrigida: quais barreiras foram detectadas, quais passaram despercebidas, quais alertas não se confirmaram e quais problemas foram resolvidos. Registrar tempo de tarefa, clareza das explicações, facilidade dos três modos e acesso efetivo ao conteúdo com os recursos usados pelo estudante.

A revisão da professora especialista ajudará a estabelecer referências para conferir os diagnósticos e as adaptações. O relato do estudante ajudará a verificar se o material permite compreender e realizar a atividade, preservando sua finalidade.


## Observações do planejamento

- A participação dos professores e da estudante está planejada; os convites e testes ainda serão organizados pelo grupo.

- Os testes com a colega representam sua experiência individual. Pretende-se ampliar a avaliação para pessoas com baixa visão e outros perfis conforme houver participantes disponíveis.

- Aprendizado e autonomia são benefícios e critérios do conceito. A plataforma não atribui notas ao professor nem presume seu aprendizado por uma alteração no arquivo.

- O primeiro produto será um site no navegador, executado localmente. Um programa instalado poderá ser considerado em uma etapa futura.

- O suporte a diferentes formatos, a edição no navegador e a geração de adaptações são funções planejadas, com implantação e verificação progressivas.


# Diferencial e referências


## O que já existe nas soluções consultadas

A documentação do Microsoft Accessibility Checker descreve identificação de problemas em arquivos do Office, explicações e sugestões de correção [1]. A documentação do Adobe Acrobat descreve verificações de PDF, relatório, orientações de correção, nova verificação e itens que exigem conferência manual [2].


## Diferencial proposto para o projeto

O diferencial é combinar esses tipos de recurso em um fluxo dedicado ao professor do ensino médio: análise com contexto da atividade e necessidades do estudante; orientação pedagógica durante a correção; três formas de visualização; revisão entre versões; e adaptação assistida opcional com decisão final do professor.

Essa diferenciação é uma proposta de posicionamento do produto, baseada no problema pesquisado pelo grupo. Sua utilidade deverá ser verificada nos testes. A contribuição está na organização e contextualização do fluxo, sem pressupor exclusividade de cada função isolada.


## Fontes utilizadas

Documento da atividade: 1as Atividades_Desenvolvimento_de_Produto_01.pdf - roteiro de conceitos, representação, comparação e fechamento fornecido pelo professor.

Trabalho anterior do grupo: APRESENTACAO CONCEITO.pdf; Documento sem título-17.pdf; levantamento dos principais dados sobre o problema; apresentação sobre inclusão de estudantes com deficiência visual.

Respostas do planejamento: Definições fornecidas por Lucas Santana nesta conversa, consolidadas em 05/10/2026.

[1] Microsoft Support. [Rules for the Accessibility Checker](https://support.microsoft.com/en-us/accessibility/office-accessibility/rules-for-the-accessibility-checker). Acesso em 05/10/2026.

[2] Adobe Help. [Create and verify PDF accessibility, Acrobat Pro](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html). Acesso em 05/10/2026.


## Correspondência com a entrega solicitada

Conceitos desenvolvidos e refinados: páginas 2 a 4. Representação visual de cada conceito: páginas 2 a 4. Matriz de comparação e síntese: página 5. Conceito geral e justificativa: página 6. Funcionalidades e observações: páginas 7 e 8.
