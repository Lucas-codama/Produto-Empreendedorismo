"""Generate a multi-page QA material directly in the isolated test workspace."""
import sys
from pathlib import Path
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reportlab.pdfgen import canvas
import server
server.DATA=server.ROOT/'.runtime'/'workspace-ui-qa'/'jobs'
with server.identity_store().connect() as db:
    row=db.execute('SELECT id,name,email FROM users WHERE email=?',('interface20261006@example.test',)).fetchone()
user=dict(row);token=server.CURRENT_USER.set(user)
try:
    output=BytesIO();c=canvas.Canvas(output,pagesize=(600,600));c.setTitle('Teste de retomada');c.setAuthor('Entrelinhas')
    for page in range(1,4):
        c.setFillColorRGB(1,1,0);c.rect(0,0,600,600,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.setFont('Helvetica',11);c.drawString(45,500,f'Texto de teste na pagina {page}');c.showPage()
    c.save()
    job=server.create_job(output.getvalue(),'Teste_Retomada_3_Paginas.pdf',dict(discipline='Teste de interface',activity='Material de estudo',needs='Texto ampliado',technology='Leitor de tela',min_font=20))
    print('Fixture criada com',len(job['analysis']['pages']),'páginas e',len(job['analysis']['issues']),'apontamentos.')
finally:server.CURRENT_USER.reset(token)
