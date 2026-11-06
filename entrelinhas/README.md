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
- Histórico com limpeza reversível e retomada de materiais próprios.
- Exemplo interativo separado do histórico e da retomada.
- Perfis reutilizáveis de necessidades e tecnologias assistivas.
- Contas locais opcionais, login por e-mail ou nome e edição do nome/e-mail.
- Temas claro/escuro, pausa de animações e suporte a movimento reduzido.

## Armazenamento

O serviço escuta apenas em `127.0.0.1`. Os arquivos não são enviados a serviços externos durante a análise. Não há sincronização entre dispositivos.

A pasta `.runtime` contém os materiais, contas, perfis, posições de revisão e lixeira. Preserve essa pasta para manter os dados. As senhas são armazenadas como hashes com sal; a aplicação não dispõe de recuperação de senha ou confirmação de e-mail.

## Limitações

A análise utiliza regras locais e não certifica acessibilidade integral. Significado de descrições, gráficos, fórmulas, ordem de leitura e adequação pedagógica exigem revisão humana. A preferência de fonte é individual, sem um mínimo universal presumido.

As prévias de Word e PowerPoint são reconstruções e podem diferir do programa original. Ajustes de fonte podem modificar o layout. PDF e imagens não recebem correções diretas no arquivo pela interface.

O reconhecimento de texto depende do Tesseract. Para instalar, execute `Instalar_OCR.ps1`. O processamento usa dados de português e inglês e o modo clássico `--oem 0`; transcrições e contraste por pixels precisam de conferência. O instalador precisa de internet para obter o programa e os idiomas.

A API também oferece download dos materiais, relatório HTML e documento complementar de leitura.

## Recursos distribuídos

As fontes Fredoka e Nunito e os módulos Three.js ficam em `static/assets`. As licenças SIL Open Font License e MIT correspondentes acompanham esses arquivos. A interface utiliza os recursos locais, sem CDN.
