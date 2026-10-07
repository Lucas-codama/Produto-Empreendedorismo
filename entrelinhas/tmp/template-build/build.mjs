import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
const ROOT='C:/Users/Lucas/Documents/Produto Empreendedorismo/entrelinhas';
const SKILL='C:/Users/Lucas/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const PYTHON='C:/Users/Lucas/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const build=path.join(ROOT,'tmp/template-build');
const {resolvePresentationFont,finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({preferred:'Arial'});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const contents=[
 ['Título da aula','[Disciplina e turma]\n[Nome do professor]\n[Objetivo da aula]'],
 ['Tema e conceitos','[Explique um conceito por bloco de texto.]\n\n[Use frases curtas e indique a relação entre os conceitos.]'],
 ['Atividade','[Escreva o enunciado.]\n\n[Informe como responder e quais recursos podem ser utilizados.]'],
];
for(const [title,body] of contents){
 const s=p.slides.add();s.background.fill='#FFFFFF';
 const t=s.shapes.add({geometry:'textbox',position:{left:80,top:70,width:1120,height:110},fill:'none',line:{fill:'none',width:0}});
 t.text=title;t.text.style={typeface:font,fontSize:56,bold:true,color:'#000000',autoFit:'none'};
 const b=s.shapes.add({geometry:'textbox',position:{left:80,top:240,width:1120,height:390},fill:'none',line:{fill:'none',width:0}});
 b.text=body;b.text.style={typeface:font,fontSize:40,color:'#000000',autoFit:'none'};
 s.speakerNotes.textFrame.setText('Substitua os textos entre colchetes. Preserve o título do slide e a ordem de leitura: título, conteúdo. Confira a fonte com o estudante. Se adicionar imagens informativas, escreva descrições alternativas. O modelo não certifica acessibilidade.');
}
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
execFileSync(PYTHON,[path.join(build,'patch.py'),candidate]);
const revision=Date.now();
const final=path.join(ROOT,`templates/Modelo_Aula_${revision}.pptx`);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:final,pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:[font]},explicitTotalSlideCount:3,verifyArtifactToolImport:true,receiptPath:path.join(build,`validation-${revision}.json`)});
await fs.copyFile(final,path.join(ROOT,'templates/Modelo_Aula.pptx'));
console.log(JSON.stringify(result));
const verified=await PresentationFile.importPptx(await FileBlob.load(final));
for(const [index,slide] of [...verified.slides.items].entries()){
 const png=await verified.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${index+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
