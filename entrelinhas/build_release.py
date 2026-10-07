"""Package application code and public assets, excluding all personal state."""
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
DESTINATION=ROOT.parent/'output'/'Entrelinhas_Atualizado.zip'
def build():
    files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in {'.py','.ps1','.cmd','.md','.txt','.cjs'}]
    for directory in ['static','examples']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file())
    files.extend(ROOT/'templates'/name for name in ['Modelo_Atividade.docx','Modelo_Avaliacao.docx','Modelo_Aula.pptx'])
    with zipfile.ZipFile(DESTINATION,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p,'entrelinhas/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None
        assert all('/.runtime/' not in n and '/tmp/' not in n and not n.endswith('.sqlite') for n in archive.namelist())
        for required in ['server.py','accounts.py','workspace_store.py','static/workspace.js','static/review-state.js','templates/Modelo_Aula.pptx']:
            assert 'entrelinhas/'+required in archive.namelist()
    print(str(DESTINATION),DESTINATION.stat().st_size,'bytes')
if __name__=='__main__':build()
