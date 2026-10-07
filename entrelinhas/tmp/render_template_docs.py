"""QA fallback: packaged LibreOffice is absent on this Windows runtime.

Uses Aspose FOSS locally only for approximate previews;
the original DOCX files are read only and never saved through this renderer.
"""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tmp'/'foss-renderer'))
import aspose.words_foss as aw
import pypdfium2 as pdfium
for name,folder in [('Modelo_Atividade.docx','atividade'),('Modelo_Avaliacao.docx','avaliacao')]:
    doc=aw.Document(str(root/'templates'/name))
    dest=root/'tmp'/'template-build'/folder;dest.mkdir(exist_ok=True)
    doc.save(str(dest/'preview.pdf'),aw.SaveFormat.PDF)
    pdf=pdfium.PdfDocument(str(dest/'preview.pdf'))
    print(name,len(pdf),'page(s), approximate rendering')
    for index in range(len(pdf)):
        page=pdf[index];bitmap=page.render(scale=1.6);bitmap.to_pil().save(dest/f'page-{index+1}.png');bitmap.close();page.close()
    pdf.close()
