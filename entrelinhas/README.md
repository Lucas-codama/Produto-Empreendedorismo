# Entrelinhas

Aplicação local para analisar barreiras de acessibilidade em documentos e apresentações, revisar os apontamentos e aplicar ajustes compatíveis.

## Executar

Abra `Iniciar.cmd`. O serviço inicia em http://127.0.0.1:8765 e abre o navegador.

O atalho procura o Python do ambiente local do Codex e, se ele não estiver disponível, usa o Python instalado no PATH. Em outro computador, instale Python 3.11 ou superior e as dependências:

```powershell
python -m pip install -r requirements.txt
python server.py
```

Para encerrar o servidor iniciado pelo atalho, execute `Parar.ps1`.

## Recursos

- Análise de PDF, DOCX, PPTX, PNG e JPG de até 20 MB.
- Até 60 páginas/slides em PDF/PPTX e 2.000 parágrafos em DOCX.
- Verificações de contraste, tamanho de fonte informado, descrições de imagens e aspectos de estrutura.
- Revisão lado a lado ou passo a passo, com filtros, evidências e conferência pessoal.
- Ajustes de fonte, contraste e descrições em DOCX/PPTX, preservando o original em novas versões.
- Em PDFs, texto isolado permite edição de cor e fonte; figuras com tags permitem descrição gravada no próprio `/Alt`. O site também permite corrigir idioma, nível dos títulos e marcar a primeira linha das tabelas estruturadas como cabeçalho, quando o elemento estiver identificado.
- Histórico com limpeza reversível e retomada de materiais próprios.
- Exemplo interativo separado do histórico e da retomada.
- Perfis reutilizáveis de necessidades e tecnologias assistivas.
- Contas locais opcionais, login por e-mail ou nome e edição do nome/e-mail.
- Temas claro/escuro, pausa de animações e suporte a movimento reduzido.

## Armazenamento

Os materiais ficam na pasta `.runtime` do serviço. A análise de acessibilidade é local. Somente ao clicar em “Verificar com IA”, a imagem selecionada e a descrição são enviadas ao OpenRouter; o documento inteiro e os dados do perfil não são enviados. Não há sincronização entre dispositivos.

A pasta `.runtime` contém os materiais, contas, perfis, posições de revisão e lixeira. Preserve essa pasta para manter os dados. As senhas são armazenadas como hashes com sal; a aplicação não dispõe de recuperação de senha ou confirmação de e-mail.

## Limitações

A análise utiliza regras locais e não certifica acessibilidade integral. Significado de descrições, gráficos, fórmulas, ordem de leitura e adequação pedagógica exigem revisão humana. A preferência de fonte é individual, sem um mínimo universal presumido.

As prévias de Word e PowerPoint são reconstruções e podem diferir do programa original. Ajustes de fonte podem modificar o layout. O contraste de texto em PDF pode ser editado pelo seletor de cor quando o trecho for identificado como objeto de texto seguro para edição. O ajuste gera uma nova versão e uma nova análise. Textos incorporados em imagens, páginas rotacionadas ou objetos não isolados precisam de correção no arquivo de origem; o aplicativo informa essa limitação. A interface também permite baixar a versão atual.

O reconhecimento de texto depende do Tesseract. Para instalar, execute `Instalar_OCR.ps1`. O processamento usa dados de português e inglês e o modo clássico `--oem 0`; transcrições e contraste por pixels precisam de conferência. O instalador precisa de internet para obter o programa e os idiomas.

A API também oferece download dos materiais e relatório de análise.

## Recursos distribuídos

As fontes Fredoka e Nunito e os módulos Three.js ficam em `static/assets`. As licenças SIL Open Font License e MIT correspondentes acompanham esses arquivos. A interface utiliza os recursos locais, sem CDN.

## Ajustes rápidos por recurso de acesso

Os novos perfis têm escolhas explícitas de leitura visual ampliada, leitor de tela com voz e linha Braille, inclusive combinadas, além dos recursos utilizados e das preferências de ampliação de imagens e legenda visível. Essas escolhas prevalecem sobre palavras presentes nos campos livres. “Ainda não sei” mantém a necessidade de confirmação com o estudante. Perfis antigos continuam disponíveis; ao reutilizá-los, confirme as novas opções.

A análise prioriza os apontamentos conforme a forma de leitura, sem ocultar os demais. As preferências preenchem o editor de imagens e são preservadas nos perfis e nas novas versões. O resultado também oferece orientações de teste com os recursos selecionados. Selecionar NVDA, ZoomText ou linha Braille não executa essas ferramentas nem comprova compatibilidade: a conferência deve ocorrer no aplicativo e no equipamento utilizados pelo estudante. Não há transcrição Braille automática.

O formulário de necessidades e tecnologias orienta as opções: leitor de tela prioriza descrição alternativa; leitura ampliada oferece ampliação da imagem e legenda visível; uso combinado oferece os dois. Isso não é um diagnóstico nem um teste da tecnologia assistiva. A imagem é preservada.

Word: imagens em linha podem ser ampliadas e receber legenda. PowerPoint: ampliação e legenda são permitidas quando cabem sem cobrir outros elementos. PDF: a descrição alternativa é gravada na tag da figura quando identificada; a imagem é ajustada na própria página, com descrição e legenda próximas ao conteúdo, sem acrescentar páginas. Ajustes de layout complexos devem ser feitos no editor original.

Ao salvar imagens em PDF, a figura recebe também os limites de posição usados pelo leitor de PDF do Firefox para expor a imagem e sua descrição às tecnologias assistivas. Salvar novamente uma descrição antiga repara esses limites quando ausentes. Ajustes posteriores de fonte e cor mantêm essa associação e atualizam a posição quando a imagem se desloca. Isso não substitui o teste com o leitor de tela utilizado pelo estudante.

O download de PDF também corrige esses limites automaticamente nas versões antigas, inclusive nas revisões concluídas. Essa preparação ocorre na rota de download do produto; os arquivos originais e os registros do histórico são preservados.

As alterações geram uma nova versão no formato do arquivo para download. O editor de versões de leitura HTML foi retirado.

## Verificação de descrição com IA (local)

Preencha `OPENROUTER_API_KEY` no arquivo `.env` da raiz (há um modelo em `.env.example`). Reinicie com `Parar.ps1` e `Iniciar.ps1`. A chave fica no backend local, não é enviada ao navegador e está ignorada pelo Git. A integração não funciona em acessos remotos nem no ambiente Render.

Na execução local, `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` do `.env` têm prioridade sobre valores herdados do Windows. No Render, as variáveis do servidor continuam tendo prioridade.

O modelo padrão é `google/gemini-2.5-flash-lite`, pelo OpenRouter, configurável em `OPENROUTER_MODEL`. Ele aceita imagem e texto. A referência consultada é US$ 0,10 por milhão de tokens de entrada e US$ 0,40 por milhão de tokens de saída: https://openrouter.ai/google/gemini-2.5-flash-lite. O preço e a disponibilidade podem mudar.

No editor da imagem, escreva a descrição e clique em **Verificar com IA**. O resultado compara o conteúdo, aponta diferenças e oferece uma descrição sugerida. É necessário escrever uma descrição antes de verificar. **Usar sugestão** só preenche o campo; **Salvar imagem e verificar** grava a alteração no documento. A IA não conclui nem certifica acessibilidade por conta própria.



## Histórico de revisões concluídas

A tela final oferece **Baixar nova versão**. O histórico mostra a versão mais recente de cada material, separada entre **Em revisão** e **Concluídos**. Os concluídos abrem um registro somente para consulta, com download, ajustes aplicados, valores antes/depois quando disponíveis e pontos conferidos manualmente. Uma revisão concluída não pode ser reaberta nem editada pelas rotas da API. Para começar outro trabalho, envie um novo material na tela inicial.

O banco SQLite `reviews.sqlite` guarda versões, apontamentos e alterações em tabelas separadas, com transações e chaves de referência. Ele fica em `.runtime` para uso sem conta e na pasta `.runtime/accounts/<id>` para cada conta. Os arquivos originais continuam nas pastas de materiais; faça backup da pasta `.runtime` completa para preservar registros e documentos juntos. Registros antigos são incorporados ao acessar o material ou o histórico; informações de antes/depois que não foram registradas nas versões antigas não são inventadas. A limpeza reversível do histórico preserva o estado de conclusão ao recuperar os materiais.

A avaliação numérica da IA vai de 0 a 1000, é interna e não é enviada ao navegador. A aprovação exige nota acima de 950 e correspondência suficiente com a imagem. Uma descrição aprovada não recebe novas sugestões. O limite conta somente duas aprovações da mesma combinação de imagem e texto, com espaços e maiúsculas normalizados. A contagem fica no SQLite da conta e continua após reiniciar ou criar outra versão com a mesma imagem e descrição. Descrições que precisam de ajustes não consomem aprovações. Respostas aprovadas são reutilizadas para evitar outra chamada paga. A execução mantém somente uma verificação de IA simultânea.

Em gráficos e tabelas, citar apenas o tema não é suficiente. A IA deve extrair as categorias, os valores e as unidades visíveis e indicar trechos da descrição que comunicam esses dados. O backend confere essas evidências antes de aceitar uma aprovação; dados ausentes ou não confirmados mantêm a necessidade de ajustes. As aprovações são versionadas, para que resultados de critérios antigos não sejam reaproveitados em novas verificações.

Uma sugestão só é exibida depois de passar pela mesma avaliação de imagem e texto. Essa conferência pode fazer uma segunda chamada à IA. Se a sugestão for aprovada, o resultado é guardado sem consumir as duas aprovações do usuário. Ao usar esse texto sem alterações na mesma imagem, a aprovação é reutilizada, inclusive após reiniciar o aplicativo. Não há uma sequência automática de novas sugestões se a candidata não for confirmada.

A tela de conclusão inclui uma prévia ampla da versão final, seleção de páginas e ampliação antes do download. PDFs usam a imagem renderizada da própria versão final; Word e PowerPoint usam a prévia extraída já existente no aplicativo.

Em **Sua conta → Editar perfil → Alterar senha**, informe a senha atual, a nova senha e sua confirmação. A nova senha precisa de 8 a 128 caracteres. A alteração renova a sessão atual e encerra as sessões anteriores; senhas continuam armazenadas apenas como hashes com salt.

Descrições existentes passam por revisão automática de IA durante a análise e ao salvar uma nova versão, na execução local com chave configurada. Aprovações da mesma imagem e descrição são reutilizadas sem outra chamada ou nova aceitação. Descrições aprovadas ficam resolvidas, inclusive em reenvios; indisponibilidade ou incerteza mantém o ponto para revisão humana. Abrir o histórico só consulta aprovações já registradas.

Depois de gravar uma descrição, essa conferência de conteúdo pode ser marcada manualmente como resolvida se a IA estiver indisponível. Imagens sem descrição continuam exigindo a gravação do texto antes dessa confirmação. Salvar novamente a mesma descrição, legenda e tamanho não cria uma versão duplicada. Confirmações e aprovações já registradas são preservadas ao avançar, retomar a revisão ou corrigir outro trecho.

## Configurações de acessibilidade

O botão de configurações no cabeçalho abre uma janela própria, sem fechar o editor nem descartar rascunhos. Ela oferece animações, som, tamanho da interface de 80% a 150% e alto contraste. As preferências ficam salvas neste navegador. A prévia de animações compara movimento e estado estático ao passar o mouse ou focar a opção; respeita movimento reduzido do sistema. A prévia de som usa o som de sucesso a cada três segundos enquanto a opção estiver sob o mouse, ou pelo botão de escuta. Sair, desligar o som, ocultar a aba ou fechar a janela interrompe a prévia. Escape fecha as configurações e devolve o foco ao botão.

