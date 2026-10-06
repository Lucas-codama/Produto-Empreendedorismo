# Entrelinhas

Plataforma de análise de acessibilidade de documentos e apresentações. Ajuda professores a compreender barreiras, corrigir itens compatíveis e revisar versões.

## Como abrir

Neste computador, dê dois cliques em **Iniciar.cmd**. Ele utiliza o Python já disponível no ambiente do Codex e abre **http://127.0.0.1:8765** no navegador. Se o servidor já estiver ativo, o atalho reutiliza o serviço.

Para executar manualmente:

```powershell
& 'C:\Users\Lucas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' server.py
```

Em outro computador, use Python 3.11 ou superior e instale as dependências de `requirements.txt`. O servidor utiliza a biblioteca padrão do Python e não depende de uma conta ou chave de IA.

## Fluxo de uso

1. Clique em **Abrir um exemplo** para analisar uma atividade real em PPTX com contexto fictício e barreiras conhecidas. Você também pode enviar um arquivo próprio.
2. Clique em **Escolher arquivo**. Para materiais próprios, informe disciplina, tipo de atividade, necessidades e tecnologias assistivas. O tamanho de fonte preferido é opcional e deve refletir o estudante.
3. Explore **Lado a lado** e **Passo a passo**. A explicação e a evidência de cada apontamento ficam em **Entender este ponto**.
4. Em arquivos DOCX e PPTX, ajuste fonte, cor do texto e descrição de imagens. Cada edição gera uma nova versão, preservando o original.
5. Use **Ajustes sugeridos** para selecionar ajustes técnicos de fonte e contraste. Descrições não são inventadas automaticamente.
6. Baixe o arquivo revisado, abra no Word ou PowerPoint e confira layout e conteúdo.
7. Você pode editar externamente e usar **Nova versão**. A comparação mostra itens persistentes, novos e não reencontrados.
8. Consulte materiais anteriores na aba **Histórico**. **Limpar histórico** recolhe os cartões para a lixeira com uma explosão de formas. **Desfazer** recupera os materiais e suas versões, inclusive após recarregar a página. A animação respeita movimento reduzido e o controle de pausa. O relatório HTML continua disponível na API, sem um modo de relatório na interface.

Arquivos de exemplo também estão em `examples/Atividade_Geografia.pptx` e `examples/Atividade_Geografia.docx` para testar o envio pelo formulário.

## Verificações efetivamente implementadas

| Verificação | Cobertura |
|---|---|
| Contraste do texto | Cálculo de luminância quando as cores do texto e do fundo são conhecidas. Referência WCAG de 4,5:1 para texto comum e 3:1 para texto grande. Cores herdadas não resolvidas, fundo de imagem, transparências e composição complexa são encaminhados para revisão. |
| Tamanho da fonte | Compara os tamanhos identificados à preferência informada. Nenhum mínimo universal é presumido. |
| Descrição de imagens | Inspeciona os metadados em DOCX/PPTX; aponta ausência e alguns nomes genéricos. Descrições existentes continuam sujeitas à conferência de sentido. |
| PDF | Extrai texto, posições, tamanho e cor; mede fundos complexos pela renderização e inspeciona árvore vazia, referências MCID, saltos de títulos, figuras sem descrição, idioma e tabelas sem cabeçalho. A ordem semântica exige conferência. |
| Slides | Verifica presença de título e encaminha elementos complexos para revisão. |
| Versões | Cada correção ou reenvio gera uma análise nova. A comparação usa regra e localização; deslocamentos no arquivo podem modificar a correspondência. |

## Cobertura e limites

- Aceita **PDF, DOCX, PPTX, PNG e JPG**, até **20 MB**. PDF/PPTX: até 60 páginas/slides. DOCX: até 2.000 parágrafos. Documentos muito complexos podem exigir divisão.
- As prévias DOCX e PPTX são reconstruções. DOCX mostra grupos de trechos e números de parágrafos, não a paginação do Word. PPTX não reproduz completamente fontes, temas, grupos, objetos e efeitos.
- O PDF é mostrado por uma imagem renderizada do próprio arquivo. Uma imagem de página na interface não representa por si só uma versão acessível do conteúdo.
- OCR clássico local foi integrado para imagens e PDFs digitalizados, com dados de português e inglês. A ativação depende de instalar Tesseract. Neste computador a instalação foi cancelada pelo Windows; o teste real fica pendente até a instalação ser autorizada e concluída. Não é usado um modelo generativo ou API externa.
- O texto reconhecido e seu contraste por pixels são estimados e exigem revisão. Altura do texto em uma imagem não é convertida em tamanho físico de fonte.
- O botão **Texto para leitura** permite revisar transcrições, ordenar trechos, definir títulos e descrever imagens. Salva uma versão HTML separada, com idioma e confirmação individual. Isso não modifica nem certifica as tags do PDF original.
- O motor não interpreta o sentido de gráficos, fórmulas, mapas ou avaliações e não assegura que uma descrição esteja correta.
- A revisão automática do Word inclui corpo, células, cabeçalhos, rodapés, notas, caixas de texto e hyperlinks. As correções preservam as partes originais do pacote; a prévia não reproduz a paginação ou sobreposições do Word.
- Aumentar fontes pode mudar o layout. A plataforma pede revisão do resultado no programa original.
- A verificação é parcial. Não emite certificado, percentual de acessibilidade ou nota de aprendizado do professor.

## Arquivos e privacidade local

O servidor escuta somente em **127.0.0.1**. Os arquivos e resultados ficam em **.runtime/jobs/** neste computador. Não são enviados a serviços externos. As análises persistem entre reinícios e aparecem no Histórico. O original é mantido, e cada revisão é gravada separadamente.

Para encerrar um servidor iniciado pelo atalho, execute `Parar.ps1`. A limpeza pelo Histórico move as análises para `.runtime/trash`, sem apagá-las definitivamente. O botão Desfazer recupera a última limpeza; seu identificador fica salvo neste navegador.

## Testes de desenvolvimento

```powershell
& 'C:\Users\Lucas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest -v test_analyzer test_extended test_history
```

A suíte verifica contraste, parâmetros individuais, arquivos corrompidos, posições do PDF, descrições, preservação do original, correções reais nos arquivos, exportação, relatório e o ciclo HTTP de análise/revisão. Esses testes técnicos não substituem os testes planejados com professores, estudante e especialista.

## Referências técnicas

- [W3C: contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- [python-docx: texto e formatação](https://python-docx.readthedocs.io/en/latest/user/text.html).
- [python-pptx: objetos de texto](https://python-pptx.readthedocs.io/en/latest/api/text.html).
- [Tesseract: modo clássico e modos de reconhecimento](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).
- [W3C: ordem de leitura de PDF](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF3).
- [W3C: descrição alternativa em tags de PDF](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF1).

O planejamento acadêmico permanece em `../output/Planejamento_Desenvolvimento_do_Produto.md` e no PDF preenchido em `../output/pdf/`.

## Interface

A navegação reúne Analisar e Histórico. O formulário aparece após a escolha do arquivo. A página inicial usa uma cena de documentos em WebGL com Three.js; há uma composição em CSS quando WebGL não está disponível. A animação pausa fora da tela e respeita a preferência por movimento reduzido. O controle no topo permite pausar manualmente.

Fredoka e Nunito são distribuídas sob a licença SIL Open Font License. Three.js usa licença MIT. As fontes, o módulo e as respectivas licenças estão em static/assets; a interface não consulta CDN ou serviço externo.

A revisão usa uma prancheta com sombras, folhas e animações leves. O histórico apresenta uma transição de aproximação e afastamento da cena 3D. Ao pausar animações ou preferir movimento reduzido, a navegação ocorre diretamente. A cobertura não é exibida como seção na interface; as verificações continuam funcionando no analisador.

## Motor de verificação e navegação

O contraste em PDF considera fundos retangulares de cor uniforme e separa trechos quando o fundo muda. Fundos complexos, transparências e CMYK usam renderização em RGB do original e uma cópia em memória sem objetos de texto. O pior contraste amostrado é identificado como estimativa; o arquivo fonte permanece intacto. Em DOCX, são considerados realces por trecho, sombreamentos e cores de tema. Em PPTX, são analisados textos agrupados e textos de tabelas, além de caixas sobre retângulos sólidos. As correções de cor são aplicadas apenas aos trechos que falharam, usando o fundo de cada trecho.

As análises salvas são recalculadas quando a versão do motor muda, sem modificar os materiais originais. O botão Voltar restaura a tela, a página e o modo de revisão anteriores durante a sessão.

Os dois modos de revisão têm Anterior e Próximo. Escolher um apontamento abre sua página e destaca o elemento identificado; escolher uma página seleciona um apontamento dela ou informa que não há um específico. Conferências do documento inteiro mantêm esse escopo explícito enquanto o professor percorre as páginas. A marcação pessoal e a posição são preservadas ao trocar de modo. As explicações apresentam o resultado concreto e a ação correspondente; descrições existentes ficam visíveis no painel.

A aplicação utiliza verificações por regras, sem integração de IA generativa ou agente de IA. A suíte contém 50 testes, incluindo regressões de texto branco sobre fundo amarelo, realces mistos, tabelas, grupos, degradês, CMYK, transparência, conteúdo fora do corpo do Word, estrutura do PDF, versão HTML e limpeza/recuperação do histórico. Bordas e sublinhados não são tratados como fundo dos caracteres; a renderização sem texto é regenerada após remover os objetos. O teste com OCR real é pulado quando o executável não está instalado; os demais continuam sendo executados.

O arquivo `../output/Teste_Acessibilidade/Teste_Acessibilidade_10_Paginas.pdf` contém nove casos adversos e uma página de controle. Use a preferência de fonte de 20 pt para reproduzir os apontamentos de tamanho. `Gabarito.md`, na mesma pasta, explica o que deve ser detectado e o que exige revisão humana. `build_accessibility_fixture.py` recria o PDF e registra a análise real. Os apontamentos de figuras, títulos e tabelas do PDF agora carregam a página correspondente.

`python audit_capabilities.py` executa mais 19 casos com documentos adversos. A tabela de resultados e as evidências ficam em `../output/Auditoria_Verificacoes.md` e `../output/Auditoria_Verificacoes.json`. Há casos de funcionalidades confirmadas e casos que confirmam limites; esses resultados não equivalem a uma certificação de acessibilidade.

## Reconhecimento de texto em imagens

Execute `Instalar_OCR.ps1` somente quando desejar ativar o recurso e confirme a janela do Windows. O aplicativo procura o executável em `.runtime/tools/tesseract`, em `C:/Program Files/Tesseract-OCR` ou no PATH. Os dados de idioma ficam em `.runtime/tools/tessdata`. O processamento usa o modo clássico `--oem 0`, sem rede neural LSTM, e não faz upload dos materiais. O texto é obtido de uma cópia com contraste realçado; as medições usam sempre os pixels originais. Imagens e transcrições não são aprovadas automaticamente.
