"""Editable classroom starting points; not an accessibility certification."""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent

def document(name, title, sections):
    doc=Document()
    section=doc.sections[0]
    section.page_width=Inches(8.5);section.page_height=Inches(11)
    section.top_margin=section.bottom_margin=Inches(.7)
    section.left_margin=section.right_margin=Inches(.75)
    for style_name,size in [('Normal',20),('Title',28),('Heading 1',23),('Heading 2',21)]:
        style=doc.styles[style_name]
        style.font.name='Arial';style.font.size=Pt(size);style.font.color.rgb=RGBColor(0,0,0)
        style.paragraph_format.space_after=Pt(10)
        style.paragraph_format.line_spacing=1.15
        lang=OxmlElement('w:lang');lang.set(qn('w:val'),'pt-BR');style.element.get_or_add_rPr().append(lang)
    doc.core_properties.title=title;doc.core_properties.language='pt-BR'
    doc.add_paragraph(title,'Title')
    doc.add_paragraph('Disciplina: [preencher]\nTurma: [preencher]\nEstudante: [preencher]')
    for heading,text in sections:
        doc.add_heading(heading,1)
        doc.add_paragraph(text)
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name='Arial';run.font.size=paragraph.style.font.size
            run.font.color.rgb=RGBColor(0,0,0)
    doc.save(ROOT/'templates'/name)

if __name__=='__main__':
    (ROOT/'templates').mkdir(exist_ok=True)
    document('Modelo_Atividade.docx','Atividade de sala',[
        ('Orientações','[Explique o que o estudante deve fazer e como entregar a resposta.]'),
        ('Questão 1','[Escreva o enunciado aqui.]'),
        ('Resposta','[Espaço para resposta. Amplie conforme a necessidade.]'),
    ])
    document('Modelo_Avaliacao.docx','Avaliação de aprendizagem',[
        ('Orientações','[Informe o tempo, os recursos permitidos e a forma de responder.]'),
        ('Questão 1','[Escreva o enunciado e o valor da questão.]'),
        ('Resposta','[Espaço para resposta. Amplie conforme a necessidade.]'),
    ])
