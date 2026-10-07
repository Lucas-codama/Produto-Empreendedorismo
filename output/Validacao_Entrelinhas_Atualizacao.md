# Validação da atualização do Entrelinhas

06 de outubro de 2026. Aplicativo local, sem IA generativa. Motor 9.

## Recursos entregues

- Perfis reutilizáveis: necessidades, tecnologias e fonte preferida. Criação, edição e remoção.
- Filtros: contraste, imagens, fonte, estrutura; pendentes, conferidos e conferência humana. Lista, marcações e navegação usam o mesmo conjunto.
- Modelos editáveis: atividade DOCX, avaliação DOCX e aula PPTX com três slides.
- Continuação: página, apontamento, modo, filtros, conferência pessoal e rolagem salvos no servidor, com apoio local no navegador.
- Cadastro e login opcionais no servidor local, separação dos materiais por conta e importação explícita de uma cópia do acervo sem conta.
- Três personagens em forma de cápsula; olham ao redor e cobrem os olhos ao exibir a senha, com movimento de espiar. Pausa de animações é respeitada.
- Confirmação discreta ao terminar uma análise, já incorporada ao fluxo de envio e nova versão.

## Testes técnicos

| Grupo | Resultado |
|---|---|
| Python | 60 testes: 59 aprovados, 1 pulado por ausência do OCR instalado |
| Regras de revisão em JavaScript | 8 aprovados |
| Auditoria de documentos adversos | 19 casos: nenhum critério testado falhou |
| Sintaxe de app.js e workspace.js | Sem erros |
| Modelos DOCX e PPTX servidos pela API | Arquivos reais, títulos e estilos inspecionados |

Os testes incluem baixo contraste e controles de contraste bom, herança e realce no Word, texto em grupos e tabelas, CMYK, degradê e transparência no PDF, descrições ausentes e genéricas, tags vazias, conteúdo sem associação à estrutura, preservação do original e correções reais. A auditoria detalhada está em `Auditoria_Verificacoes.md` e `Auditoria_Verificacoes.json`.

As contas foram testadas com dois usuários e visitante: os materiais, perfis, posições e lixeiras permanecem separados. Rotas de arquivo, original, relatório e leitura de outra conta foram recusadas. Login em uma segunda sessão recuperou a revisão; logout revogou o token. Senhas têm sais e hashes distintos, sessões guardam somente o hash do token e o limite de tentativas persiste.

## Conferência no navegador

Usado um servidor isolado na porta 8766, com dados fictícios e PDF de três páginas gerado exclusivamente para QA. O histórico real da porta 8765 não foi apagado nem importado.

- Cadastro, troca entre login e cadastro, login incorreto, login correto e saída.
- Criação de perfil e reapresentação na lista salva.
- Filtrar contraste mostrou somente marcações de contraste no lado a lado.
- Conferir um item no filtro de pendentes fez o item sair da lista e das marcações.
- Próximo passou da página 1 para a página 2 correspondente.
- Após recarregar, Continuar revisão recuperou a página 3, o mesmo apontamento, Passo a passo, o filtro e a marcação de conferência.
- O início com Continuar revisão coube na altura de 720 px sem conteúdo excedente.
- Menu e cadastro conferidos em 390 × 844, sem transbordamento horizontal.
- Pausa desativou animações e transições dos personagens; senha exibida manteve a pose de cobrir os olhos.
- Limpar o histórico retirou a continuação de materiais movidos para a lixeira. Desfazer recuperou os arquivos e o botão de retomada com a posição preservada.

## Verificação dos modelos

Os três slides finais passaram pelos validadores de pacote, geometria, fontes e reimportação e foram renderizados e inspecionados individualmente.

O renderizador canônico de DOCX foi executado, mas não encontrou LibreOffice neste ambiente. Um renderizador alternativo local gerou uma prévia aproximada de cada DOCX; todas as páginas foram inspecionadas, sem corte ou sobreposição observados. Estilos de título e seções, idioma, fontes de 20 pt no corpo e cor preta foram conferidos no arquivo real. A paginação nativa do Word não foi validada. O renderizador alternativo é usado somente para QA e não integra o aplicativo. Referência do método: [Aspose FOSS](https://docs.aspose.org/words/python/getting-started/installation/).

## Limites que permanecem explícitos

- A análise técnica não certifica acessibilidade integral. Sentido de descrições, gráficos e adequação pedagógica dependem da revisão e do uso com o estudante.
- OCR em imagens e PDFs digitalizados aguarda instalação. O site informa ausência de reconhecimento; não conta esses textos como aprovados.
- A conta funciona neste servidor local. Ainda não existe hospedagem compartilhada para sincronizar computadores. Não há confirmação de e-mail ou recuperação de senha nesta implementação local.
- A prévia do Word não corresponde à paginação nativa e a edição completa dentro do aplicativo ficou para a próxima etapa, conforme solicitado.
