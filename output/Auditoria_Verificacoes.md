# Auditoria das verificações do Entrelinhas

Motor: 9. Data: 06/10/2026. Sem IA. Testes locais com arquivos sintéticos, sem envio de materiais.

O resultado confirma apenas os casos e recursos abaixo. Não certifica conformidade integral, compatibilidade com leitores de tela nem todos os arquivos desses formatos.

| Caso | Resultado | Critério |
|---|---|---|
| PDF branco sobre amarelo | CONFIRMADO | Contraste 1,07:1 e fonte de 11 pt abaixo de 20 pt. |
| PDF preto sobre amarelo | CONFIRMADO | Não emitir alerta de contraste. |
| Fonte no limite individual | CONFIRMADO | 20 pt não fica abaixo da preferência de 20 pt. |
| Sem preferência individual | CONFIRMADO | Não inventar um tamanho mínimo. |
| PDF com degradê escuro e texto preto | CONFIRMADO | Medir o fundo renderizado e detectar baixo contraste. |
| PDF com cor CMYK | CONFIRMADO | Converter pela renderização do PDF e detectar baixo contraste. |
| PDF digitalizado | ATIVAÇÃO PENDENTE | Reconhecer texto localmente e estimar contraste. Ativação depende da instalação do Tesseract. |
| JPG com texto | ATIVAÇÃO PENDENTE | Reconhecer texto localmente e estimar contraste; conferir transcrição. Ativação depende da instalação do Tesseract. |
| PDF com árvore de tags vazia | CONFIRMADO | Detectar erro objetivo de árvore vazia e texto não associado à estrutura. |
| alt-ausente | CONFIRMADO | Detectar alt_missing; não certificar o sentido da imagem. |
| alt-generico | CONFIRMADO | Detectar alt_placeholder; não certificar o sentido da imagem. |
| alt-falso | CONFERÊNCIA DO PROFESSOR | Detectar alt_quality; não certificar o sentido da imagem. |
| Imagem marcada decorativa | CONFIRMADO | Respeitar o marcador sem pedir descrição; intenção ainda é humana. |
| DOCX com problema apenas no cabeçalho | CONFIRMADO | Medir texto do cabeçalho e detectar contraste e fonte pequena. |
| DOCX com padrão de sombreamento sólido | CONFIRMADO | Não usar incorretamente a cor de preenchimento branca como fundo. |
| PPTX título reservado | CONFIRMADO | Reconhecer o espaço reservado; caixa comum não confirma título semântico. |
| PPTX título em caixa comum | CONFIRMADO | Reconhecer o espaço reservado; caixa comum não confirma título semântico. |
| Correção real de contraste em DOCX | CONFIRMADO | Cor gravada e baixo contraste desaparece; conteúdo preservado. |
| Correção real de fonte e original preservado | CONFIRMADO | Fonte de 20 pt salva; original permanece em 10 pt. |

## Problemas encontrados e tratados nesta auditoria

A execução anterior às correções apresentou falhas em: PDF com degradê escuro e texto preto, DOCX com problema apenas no cabeçalho, DOCX com padrão de sombreamento sólido.
Agora os fundos complexos de PDF são medidos pela renderização; o padrão sólido do Word usa a cor visível do padrão. Cabeçalhos, rodapés, notas, caixas de texto e hyperlinks do Word são extraídos e podem receber correções de fonte, cor e descrição.
A inspeção de PDF inclui árvore vazia, MCIDs, títulos, figuras, idioma e cabeçalhos de tabelas. A ordem semântica ainda requer conferência.
A evidência inicial foi preservada em `Auditoria_Verificacoes_Antes.json`.

## Limites

- OCR clássico local foi integrado para PNG/JPG/PDF digitalizado. Neste computador sua instalação foi cancelada pelo Windows; ativação e teste real aguardam autorização. Nenhum arquivo é enviado a uma API.
- PDF e imagens ganham uma versão de leitura editável em HTML. Isso não altera nem certifica as tags do PDF original.
- Descrição de imagem é metadado: o significado e a adequação pedagógica exigem conferência humana.
- A estrutura técnica do PDF é inspecionada. A sequência que preserva o significado, gráficos e relações de tabelas precisam ser conferidos pelo professor.
- Contraste de renderização e contraste de imagens são estimativas. Tamanho físico de fonte em imagem não é inferido pela altura dos pixels.
- Word: o corpo, células, cabeçalhos, rodapés, notas, caixas e hyperlinks são analisados. A prévia não reproduz a paginação original.
- Não verifica ortografia, linguagem clara, idioma, links, uso exclusivo de cores, conteúdo de gráficos, fórmulas ou layout após ampliação.
- Não houve teste com NVDA, JAWS ou a tecnologia assistiva do estudante.

Reprodução: `python -m unittest -v test_analyzer test_extended` e `python audit_capabilities.py`. Evidências por regra, contagens e arquivos em `Auditoria_Verificacoes.json`.

Referência usada na correção do sombreamento: [Microsoft — padrões de sombreamento](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.shadingpatternvalues?view=openxml-3.0.1). O padrão sólido tem preenchimento integral e não permite presumir a cor de fundo declarada como cor visível.
