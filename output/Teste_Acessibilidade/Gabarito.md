# Gabarito do teste de acessibilidade

Arquivo: Teste_Acessibilidade_10_Paginas.pdf. São 10 páginas; as barreiras foram inseridas intencionalmente. A última é uma página de comparação.

Use disciplina **Teste de acessibilidade**, atividade **Material de exemplo**, necessidades **Leitura ampliada e descrição de imagens**, tecnologia **Leitor de tela e ampliação** e fonte mínima **20 pt**. O parâmetro é deste teste, não um mínimo universal.

| Página | Caso | Resultado esperado |
|---|---|---|
| 1 | Contraste | Alerta automático: branco sobre amarelo, cerca de 1,07:1. |
| 2 | Fonte | Alerta automático: texto de 9 pt abaixo da preferência de 20 pt. |
| 3 | Imagem sem descrição | Alerta automático de ausência de descrição na imagem e na tag Figure. |
| 4 | Descrição genérica | Alerta automático para imagem_01.png. |
| 5 | Descrição incorreta | Conferência humana: a imagem é um gráfico; a descrição fala de um cachorro. O site não reconhece o significado de fotografias sem revisão. |
| 6 | Tabela sem cabeçalhos | Alerta automático de Table sem TH. |
| 7 | Hierarquia de títulos | Alerta automático de salto de H1 para H3. |
| 8 | Texto digitalizado | Alerta de página sem texto extraível. O OCR real aguarda instalação neste computador. |
| 9 | Ordem de leitura | Conferência humana: as tags colocam a etapa 2 antes da etapa 1. A revisão geral de estrutura continua necessária. |
| 10 | Página de comparação | Nenhum ponto de atenção previsto para fonte, contraste ou ausência de descrição. A descrição ainda pede conferência de sentido. |

Uma barreira pode produzir mais de um apontamento. O PDF tem estrutura técnica para permitir testar descrições e tags por página. As páginas 5 e 9 exigem conferência humana, mesmo quando a estrutura existe.

## Resultado do motor atual

- Página 1: Contraste de texto abaixo da referência.
- Página 2: Fonte abaixo do tamanho informado; Fonte abaixo do tamanho informado.
- Página 3: Imagem sem descrição alternativa; Figura do PDF sem descrição alternativa.
- Página 4: Descrição de imagem genérica.
- Página 5: Conferir o sentido da descrição.
- Página 6: Tabela do PDF sem cabeçalho identificado.
- Página 7: Hierarquia de títulos com salto.
- Página 8: Página sem texto extraível; Conferir o sentido da descrição; Reconhecimento de texto não concluído.
- Página 9: nenhum apontamento específico de página.
- Página 10: Conferir o sentido da descrição.
