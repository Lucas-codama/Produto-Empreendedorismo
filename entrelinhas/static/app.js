'use strict';
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let job = null, original = null, mode = 'side', selected = 0, currentPage = 0, file = null;
let reviewed = new Set(), dialogReturnFocus = null;
let readingDraft=null;
let historyClearing=false,historyUndoToken=localStorage.getItem('entrelinhas-history-undo') || null;
let navigationInProgress = false;
const navigationStack=[];
let restoringPage=false;
function currentView(){return !$('history-view').hidden?'history':!$('result-view').hidden?'result':!$('context-panel').hidden?'context':'home';}
function rememberPage(){
  if(restoringPage)return;
  navigationStack.push({view:currentView(),job,original,mode,selected,currentPage,file,context:context(),scrollY:window.scrollY});
  if(navigationStack.length>12)navigationStack.shift();updateBack();
}
function updateBack(){$('page-controls').hidden=!navigationStack.length;}
async function goBack(){
  if(navigationInProgress || restoringPage || !navigationStack.length)return;
  const previous=navigationStack.pop(),from=currentView();restoringPage=true;
  const restore=async()=>{
    job=previous.job;original=previous.original;mode=previous.mode;file=previous.file;
    $('upload-view').hidden=!['home','context'].includes(previous.view);
    $('start-panel').hidden=previous.view!=='home';$('context-panel').hidden=previous.view!=='context';
    $('history-view').hidden=previous.view!=='history';$('result-view').hidden=previous.view!=='result';
    setContext(previous.context);$('file-label').textContent=file?.name || '';
    if(previous.view==='result') {await showJobContent(previous.job,false);selected=previous.selected;currentPage=previous.currentPage;render();}
    else {nav(previous.view==='history'?'history':'analyze');if(previous.view==='history')await recent();}
    updateBack();message('');window.scrollTo({top:previous.scrollY,behavior:'instant'});$('main').focus({preventScroll:true});announce('Você voltou à tela anterior.');
  };
  try{if((from==='history')!==(previous.view==='history'))await navigatePaper(from==='history'?'out':'in',restore);else await restore();}
  catch(error){navigationStack.push(previous);message(error.message || 'Não foi possível voltar.');}
  finally{restoringPage=false;updateBack();}
}

function announce(text) { $('live').textContent = text; }
function message(text) { $('message').textContent = text; $('message').hidden = !text; if (text) announce(text); }
function busy(on, title = 'Analisando o material') {
  $('busy-title').textContent = title; $('busy').hidden = !on;
  $('material-form').setAttribute('aria-busy', String(on));
  $('analyze-button').disabled = on; $('demo-button').disabled = on;
}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'A operação não pôde ser concluída.');
  return result;
}
async function run(task, title) {
  message(''); busy(true, title);
  try { return await task(); } catch (error) { message(error.message || 'Não foi possível concluir.'); return null; }
  finally { busy(false); }
}
function context() {
  return {discipline:$('discipline').value.trim(), activity:$('activity').value,
    needs:$('needs').value.trim(), technology:$('technology').value.trim(), min_font:$('min-font').value || null};
}
function setContext(c) {
  $('discipline').value=c.discipline; $('activity').value=c.activity;
  $('needs').value=c.needs; $('technology').value=c.technology; $('min-font').value=c.min_font ?? '';
}
function chooseFile(candidate) {
  if (!candidate) return;
  if (candidate.size > 20*1024*1024) { message('Escolha um arquivo com até 20 MB.'); return; }
  if (!/\.(pdf|docx|pptx|png|jpe?g)$/i.test(candidate.name)) { message('Use PDF, DOCX, PPTX, PNG ou JPG. Converta arquivos DOC ou PPT antigos.'); return; }
  file=candidate; $('file-label').textContent=candidate.name; message('');
  rememberPage();
  $('start-panel').hidden=true; $('context-panel').hidden=false;
  window.scrollTo({top:0,behavior:'instant'}); $('discipline').focus();
}
function encodeFile(f) {
  return new Promise((resolve,reject)=>{ const reader=new FileReader(); reader.onload=()=>resolve(String(reader.result).split(',')[1]); reader.onerror=()=>reject(new Error('Não foi possível ler o arquivo.')); reader.readAsDataURL(f); });
}
async function recent() {
  if(historyClearing)return;
  try {
    const jobs=await api('/api/jobs');
    if(historyClearing)return;
    $('history-clear').disabled=!jobs.length;
    $('recent-list').innerHTML=jobs.length ? jobs.map(j=>`<button class="recent-item" data-open="${j.id}"><span class="history-file"><span class="file-badge" aria-hidden="true">${esc(j.filename.split('.').pop().toUpperCase())}</span><strong>${esc(j.filename)}</strong></span><small>v${j.version} · ${new Date(j.created_at).toLocaleDateString('pt-BR')}</small><span class="history-arrow" aria-hidden="true">↗</span></button>`).join('') : '<div class="empty-state">Você ainda não analisou nenhum material.</div>';
  } catch (_) { $('history-clear').disabled=true;$('recent-list').innerHTML='<p class="muted">Não foi possível carregar o histórico.</p>'; }
}

async function animateHistoryClear(rows){
  if(motionPaused || motionPreference.matches || !rows.length)return;
  const layer=document.createElement('div');layer.className='history-trash-scene';layer.setAttribute('aria-hidden','true');layer.dataset.phase='collecting';
  const x=Math.max(90,Math.min(innerWidth-100,innerWidth*.73)),y=Math.min(innerHeight-135,Math.max(150,innerHeight*.62));
  layer.innerHTML=`<div class="trash-target" style="left:${x}px;top:${y}px"><div class="trash-orbit"></div><svg class="trash-can" viewBox="0 0 120 130"><g class="trash-lid"><path d="M21 31h78"/><path d="M43 29V17h34v12"/></g><path class="trash-body" d="M29 38l7 72q1 7 9 7h30q8 0 9-7l7-72Z"/><path class="trash-slots" d="M48 56l2 41M72 56l-2 41"/></svg><span>Até a próxima.</span></div>`;
  document.body.append(layer);const can=layer.querySelector('.trash-target'),lid=layer.querySelector('.trash-lid');const animations=[];
  const play=(element,frames,options)=>{const a=element.animate(frames,{fill:'both',...options});animations.push(a);return a.finished.catch(()=>{});};
  const finish=()=>{if(motionPaused || motionPreference.matches)animations.forEach(a=>{try{a.finish();}catch(_){}});};
  document.addEventListener('entrelinhas-motion',finish);
  try{
    await play(can,[{opacity:0,transform:'translateY(60px) scale(.65) rotate(8deg)'},{opacity:1,transform:'translateY(0) scale(1) rotate(0)'}],{duration:230,easing:'cubic-bezier(.2,.8,.2,1)'});
    play(lid,[{transform:'rotate(0deg)'},{transform:'translate(-7px,-8px) rotate(-24deg)'}],{duration:240});
    const flights=rows.map((row,index)=>{
      const r=row.getBoundingClientRect(),clone=row.cloneNode(true);clone.classList.add('flying-history-item');clone.disabled=true;clone.tabIndex=-1;
      Object.assign(clone.style,{left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'});layer.append(clone);row.style.visibility='hidden';
      const dx=x+60-r.left-r.width/2,dy=y+62-r.top-r.height/2,rotation=(index%2?1:-1)*(9+index%5);
      return play(clone,[{opacity:1,transform:'translate(0,0) scale(1) rotate(0)'},{offset:.28,opacity:1,transform:`translate(0,-14px) scale(.72,.46) rotate(${rotation}deg)`},{offset:.72,opacity:1,transform:`translate(${dx*.74}px,${dy*.62-50}px) scale(.22,.2) rotate(${rotation*3}deg)`},{opacity:0,transform:`translate(${dx}px,${dy}px) scale(.02) rotate(${rotation*5}deg)`}],{duration:880,delay:index*32,easing:'cubic-bezier(.3,.05,.25,1)'});
    });
    await Promise.all(flights);layer.dataset.phase='burst';
    play(lid,[{transform:'translate(-7px,-8px) rotate(-24deg)'},{transform:'rotate(0)'}],{duration:190});
    play(can,[{transform:'scale(1)'},{offset:.35,transform:'scale(.9,1.08)'},{offset:.7,transform:'scale(1.08,.92)'},{transform:'scale(1)'}],{duration:430,easing:'ease-out'});
    const colors=['#9c7be8','#ef9b81','#efcb66','#a8c6bb','#c8afe6'];
    await Promise.all(Array.from({length:27},(_,index)=>{
      const part=document.createElement('i');part.className='trash-confetti';part.dataset.shape=String(index%4);part.style.background=colors[index%colors.length];part.style.left=(x+60)+'px';part.style.top=(y+62)+'px';layer.append(part);
      const angle=index*2.39996,distance=70+(index%7)*17,dx=Math.cos(angle)*distance,dy=Math.sin(angle)*distance;
      return play(part,[{opacity:0,transform:'translate(0,0) scale(.2)'},{offset:.15,opacity:1},{offset:.55,opacity:1,transform:`translate(${dx}px,${dy-30}px) scale(1) rotate(${index*31}deg)`},{opacity:0,transform:`translate(${dx*1.2}px,${dy+35}px) scale(.45) rotate(${index*51}deg)`}],{duration:820,delay:index%5*14,easing:'cubic-bezier(.15,.65,.45,1)'});
    }));
    await play(can,[{opacity:1,transform:'scale(1)'},{opacity:0,transform:'translateY(20px) scale(.85)'}],{duration:180});
  } finally{document.removeEventListener('entrelinhas-motion',finish);animations.forEach(a=>a.cancel());layer.remove();rows.forEach(r=>r.style.removeProperty('visibility'));}
}

async function clearHistory(){
  if(historyClearing || navigationInProgress)return;
  historyClearing=true;navigationInProgress=true;
  const controls=['history-clear','history-new','new-material','history-button','go-back'].map($);controls.forEach(b=>b.disabled=true);
  const rows=[...document.querySelectorAll('.recent-item')];$('history-feedback').hidden=false;$('history-undo').hidden=true;$('history-status').textContent='Recolhendo seus materiais…';
  try{
    const result=await api('/api/history/clear',{});historyUndoToken=result.undo_token;
    if(historyUndoToken)localStorage.setItem('entrelinhas-history-undo',historyUndoToken);else localStorage.removeItem('entrelinhas-history-undo');
    const removed=new Set(result.ids);
    navigationStack.splice(0,navigationStack.length,...navigationStack.filter(s=>!removed.has(s.job?.id) && !removed.has(s.original?.id)));
    if(removed.has(job?.id)){job=null;original=null;readingDraft=null;}
    if(removed.has(localStorage.getItem('entrelinhas-last')))localStorage.removeItem('entrelinhas-last');
    updateBack();
    try{await animateHistoryClear(rows);}catch(_){/* A visual failure never changes the saved operation. */}
    $('history-status').textContent=result.count?'Histórico limpo.':'O histórico já está vazio.';$('history-undo').hidden=!historyUndoToken;
  }catch(error){$('history-status').textContent=error.message || 'Não foi possível limpar o histórico.';$('history-undo').hidden=!historyUndoToken;}
  finally{historyClearing=false;navigationInProgress=false;controls.forEach(b=>b.disabled=false);await recent();if(historyUndoToken)$('history-undo').focus();else $('history-new').focus();}
}

async function restoreHistory(){
  if(!historyUndoToken || historyClearing)return;
  historyClearing=true;navigationInProgress=true;
  const controls=['history-clear','history-new','new-material','history-button','go-back'].map($);controls.forEach(b=>b.disabled=true);$('history-undo').disabled=true;
  try{const restored=await api('/api/history/restore',{token:historyUndoToken});historyUndoToken=null;localStorage.removeItem('entrelinhas-history-undo');$('history-undo').hidden=true;$('history-status').textContent=`${restored.count} ${restored.count===1?'análise recuperada.':'análises recuperadas.'}`;}
  catch(error){$('history-status').textContent=error.message;}
  finally{historyClearing=false;navigationInProgress=false;controls.forEach(b=>b.disabled=false);$('history-undo').disabled=false;await recent();if(!historyUndoToken)$('history-clear').focus();}
}
async function showJob(next, focus=true) {
  rememberPage();
  if (!$('history-view').hidden) return navigatePaper('out',()=>showJobContent(next,focus));
  return showJobContent(next,focus);
}
async function showJobContent(next, focus=true) {
  job=next; original=job.root_id === job.id ? job : await api('/api/job/'+job.root_id);
  selected=job.analysis.issues.length?0:-1; currentPage=job.analysis.issues[0]?.page ?? 0;
  reviewed=new Set(JSON.parse(localStorage.getItem('entrelinhas-reviewed-'+job.id) || '[]'));
  localStorage.setItem('entrelinhas-last',job.id);
  $('upload-view').hidden=true; $('history-view').hidden=true; $('result-view').hidden=false; nav('analyze');
  const a=job.analysis;
  $('result-title').textContent=job.filename;
  $('result-context').textContent=`${a.context.discipline} · ${a.context.activity} · Versão ${job.version}`;
  $('download-material').href='/api/job/'+job.id+'/file';
  $('stats').innerHTML=`<span class="analysis-count"><span class="count-dot" aria-hidden="true"></span><b>${a.counts.attention}</b> ${a.counts.attention===1?'ponto de atenção':'pontos de atenção'}</span>${a.counts.review?`<span class="analysis-count human"><b>${a.counts.review}</b> para conferir</span>`:''}${a.measured.unknown_contrast?`<span class="analysis-count incomplete" title="Esses trechos não tiveram o contraste medido.">Contraste pendente em ${a.measured.unknown_contrast} ${a.measured.unknown_contrast===1?'trecho':'trechos'}</span>`:''}`;
  $('comparison').hidden=!job.comparison;
  if (job.comparison) {
    const c=job.comparison;
    $('comparison').innerHTML=`<details><summary>Comparar com a versão ${c.previous_version}<span>${c.not_found} ${c.not_found===1?'item não reapareceu':'itens não reapareceram'}</span></summary><p>${c.persistent} persistentes · ${c.not_found} não reapareceram · ${c.new} novos.</p><p>${esc(c.note)}</p></details>`;
  }
  $('assist-button').disabled=!a.issues.some(i=>['font','contrast'].includes(i.action));
  $('assist-button').hidden=$('assist-button').disabled;
  $('assist-button').title=$('assist-button').disabled?'Não há ajustes técnicos compatíveis nesta análise.':'';
  render(); recent();
  announce(`Análise concluída. ${a.counts.attention} ${a.counts.attention===1?'ponto':'pontos'} de atenção e ${a.counts.review} ${a.counts.review===1?'item':'itens'} para revisão.`);
  if (focus) { $('result-title').tabIndex=-1; $('result-title').focus(); window.scrollTo({top:0,behavior:'instant'}); }
}
function nav(view) {
  for (const [id,active] of [['new-material',view==='analyze'],['history-button',view==='history']]) {
    $(id).classList.toggle('active',active);
    if(active) $(id).setAttribute('aria-current','page'); else $(id).removeAttribute('aria-current');
  }
  document.dispatchEvent(new CustomEvent('entrelinhas-view'));
}
function reset() {
  if(navigationInProgress)return;
  if(currentView()!=='home')rememberPage();
  if (!$('history-view').hidden) return navigatePaper('out',resetContent);
  if(navigationInProgress)return;
  resetContent();
}
function resetContent() {
  $('upload-view').hidden=false; $('result-view').hidden=true; $('history-view').hidden=true;
  $('start-panel').hidden=false; $('context-panel').hidden=true; nav('analyze');
  $('material-form').reset();
  job=null; original=null; file=null; $('file-input').value=''; $('file-label').textContent='';
  localStorage.removeItem('entrelinhas-last'); message('');
  window.scrollTo({top:0,behavior:'instant'});
  $('new-material').focus({preventScroll:true});
}
function showHistory() {
  if (!$('history-view').hidden || navigationInProgress) return;
  rememberPage();
  return navigatePaper('in',()=>{
  $('upload-view').hidden=true; $('result-view').hidden=true; $('history-view').hidden=false;
  nav('history'); recent(); message(''); window.scrollTo({top:0,behavior:'instant'});
  $('history-title').tabIndex=-1; $('history-title').focus({preventScroll:true});
  });
}

function paperOrigin() {
  const source = !$('upload-view').hidden && !$('start-panel').hidden ? $('hero-art') : document.querySelector('.analysis-emblem');
  const r=source?.getBoundingClientRect();
  return r?.width && r?.height && r.bottom>0 && r.top<innerHeight ? {x:r.x,y:r.y,w:r.width,h:r.height} : {x:innerWidth*.58,y:innerHeight*.24,w:Math.min(innerWidth*.36,450),h:Math.min(innerHeight*.55,500)};
}
async function navigatePaper(direction, change) {
  if(navigationInProgress)return;
  if(motionPaused || motionPreference.matches){await change();return;}
  navigationInProgress=true;document.body.classList.add('is-navigating');
  $('main').setAttribute('aria-busy','true');
  let changed=false, changePromise;
  const covered=()=>{if(changed)return changePromise;changed=true;changePromise=Promise.resolve(change());return changePromise;};
  try {
    const detail={direction,origin:paperOrigin(),getOrigin:paperOrigin,covered,promise:null};
    document.dispatchEvent(new CustomEvent('entrelinhas-portal',{detail}));
    try { await (detail.promise || paperFallback(detail)); }
    catch(error) { if(changed)await changePromise; }
    await covered();
  } finally {
    $('page-transition').hidden=true;document.body.classList.remove('is-navigating');
    $('main').removeAttribute('aria-busy');navigationInProgress=false;
  }
}
async function paperFallback({direction,origin,covered}) {
  const overlay=$('page-transition'),stage=$('portal-stage'),veil=$('portal-veil');
  overlay.hidden=false;stage.classList.add('css-portal');
  const start={left:origin.x+'px',top:origin.y+'px',width:origin.w+'px',height:origin.h+'px',transform:'rotate(-9deg) scale(.72)'},end={left:'0px',top:'0px',width:innerWidth+'px',height:innerHeight+'px',transform:'rotate(0deg) scale(1.15)'};
  try {
    if(direction==='out')await covered();
    const a=stage.animate(direction==='in'?[start,end]:[end,start],{duration:760,easing:'cubic-bezier(.65,0,.2,1)',fill:'forwards'});
    const v=veil.animate(direction==='in'?[{opacity:0,offset:0},{opacity:0,offset:.55},{opacity:1,offset:1}]:[{opacity:1,offset:0},{opacity:0,offset:.45},{opacity:0,offset:1}],{duration:760,fill:'forwards'});
    await a.finished;
    if(direction==='in')await covered();
    await overlay.animate([{opacity:1},{opacity:0}],{duration:180,fill:'forwards'}).finished;
    a.cancel();v.cancel();
  } finally {
    overlay.getAnimations().forEach(a=>a.cancel());stage.getAnimations().forEach(a=>a.cancel());veil.getAnimations().forEach(a=>a.cancel());
    stage.classList.remove('css-portal');overlay.hidden=true;
  }
}

function blockMarkers(page,index,selectedIssue,which) {
  if (which!=='marked') return '';
  const grouped=new Map();
  for (const issue of job.analysis.issues.filter(i=>i.page===index)) {
    const b=page.blocks.find(b=>b.id===issue.block_id);
    if (!b || b.x===undefined || grouped.has(b.id)) continue;
    grouped.set(b.id,true);
  }
  return [...grouped.keys()].map(id=>{
    const b=page.blocks.find(b=>b.id===id);
    const issue=selectedIssue?.page===index && selectedIssue.block_id===id?selectedIssue:job.analysis.issues.find(i=>i.page===index && i.block_id===id);
    const ix=job.analysis.issues.indexOf(issue);
    const active=selectedIssue && selectedIssue.block_id===id && selectedIssue.page===index;
    return `<button class="finding-marker ${active?'selected':''}" style="left:${b.x/page.width*100}%;top:${b.y/page.height*100}%;width:${Math.max(b.w/page.width*100,1)}%;height:${Math.max(b.h/page.height*100,1)}%" data-issue="${ix}" aria-label="Problema ${issue.number}: ${esc(issue.title)}"><span aria-hidden="true">${issue.number}</span></button>`;
  }).join('');
}
function selectPage(index) {
  currentPage=Math.max(0,Math.min(index,job.analysis.pages.length-1));
  const issues=job.analysis.issues;
  if(issues[selected]?.page!==null && issues[selected]?.page!==currentPage)selected=issues.findIndex(i=>i.page===currentPage);
  render();announce(job.analysis.pages[currentPage].label);
}
function pageHTML(material,index,which='plain',large=false) {
  const page=material.analysis.pages[index];
  if (!page) return '<div class="empty-state">Essa versão não possui uma página correspondente.</div>';
  const chosen=job.analysis.issues[selected];
  const markers=blockMarkers(page,index,chosen,which);
  if (page.kind==='pdf') return `<div class="document-page" style="aspect-ratio:${page.width}/${page.height}"><img class="page-image" src="/api/job/${material.id}/page/${index}" alt="Imagem da ${esc(page.label)} do material. Os apontamentos estão descritos na lista de problemas.">${markers}</div>`;
  if (page.kind==='raster') return `<div class="document-page" style="aspect-ratio:${page.width}/${page.height}"><img class="page-image" src="${esc(page.blocks.find(b=>b.image)?.image || '')}" alt="Imagem enviada; texto reconhecido disponível em Texto para leitura.">${markers}</div>`;
  if (page.kind==='slide') {
    const blocks=page.blocks.map(b=>{
      const style=`left:${b.x/page.width*100}%;top:${b.y/page.height*100}%;width:${b.w/page.width*100}%;height:${b.h/page.height*100}%;${b.background?'background:'+b.background+';':''}`;
      if (b.type==='image') return `<div class="slide-block" style="${style}"><img src="${esc(b.image)}" alt="${esc(b.alt || (b.decorative?'':'Imagem ainda sem descrição alternativa.'))}"></div>`;
      if (b.type==='shape_background' || b.type==='table') return `<div class="slide-block" style="${style}" aria-hidden="true"></div>`;
      if (b.type==='text') return `<div class="slide-block" style="${style}">${b.runs.map(r=>`<span style="font-size:${(r.size || 18)/page.width*100}cqw;${r.color?'color:'+r.color+';':''}${r.background?'background-color:'+r.background+';':''}${r.bold?'font-weight:700;':''}">${esc(r.text)}</span>`).join('')}</div>`;
      return `<div class="slide-block placeholder" style="${style}">${esc(b.text || 'Elemento visual')}</div>`;
    }).join('');
    return `<div class="document-page slide" style="aspect-ratio:${page.width}/${page.height};container-type:inline-size;background:${page.background}">${blocks}${markers}</div>`;
  }
  return `<div class="document-page doc-flow" style="${page.background?'background-color:'+page.background+';':''}">${page.blocks.map(b=>{
    const issues=which==='marked'?job.analysis.issues.filter(i=>i.page===index && i.block_id===b.id):[];
    const active=issues.length && chosen?.block_id===b.id && chosen?.page===index;
    const label=issues.length?`<span class="flow-label">${issues.map(i=>'Item '+i.number).join(' · ')} · ${esc(b.location || page.label)}</span>`:'';
    let content;
    if (b.image) content=`<img src="${esc(b.image)}" alt="${esc(b.alt || 'Imagem a conferir; descrição disponível no painel de revisão.')}">`;
    else if(b.runs) content=b.runs.map(r=>`<span style="${r.size?'font-size:'+r.size+'pt;':''}${r.color?'color:'+r.color+';':''}${r.background?'background-color:'+r.background+';':''}${r.bold?'font-weight:700;':''}">${esc(r.text)}</span>`).join('');
    else content=esc(b.text || 'Elemento visual');
    return `<div class="flow-block ${issues.length?'marked':''} ${active?'selected':''}" style="${b.background?'background-color:'+b.background+';':''}">${label}${content}</div>`;
  }).join('')}</div>`;
}
function preview(side=true) {
  const page=job.analysis.pages[currentPage];
  const options=job.analysis.pages.map((p,i)=>`<option value="${i}" ${i===currentPage?'selected':''}>${esc(p.label)}</option>`).join('');
  const issue=job.analysis.issues[selected];
  const scope=issue?issue.page===null?'Conferência do documento inteiro. Use as páginas para conferir a sequência.':`${page.label} · ${issue.block_id==='document'?'Conferência da página; sem posição exata identificada.':'O elemento selecionado está marcado na revisão.'}`:`${page.label} · Nenhum apontamento específico nesta página.`;
  return `<div class="preview-card paper-board"><div class="board-clip" aria-hidden="true"></div><div class="preview-toolbar"><span class="format-chip">${esc(job.analysis.info.format)}</span><div><button class="text-button" data-zoom="1">Ampliar ↗</button> <select id="page-select" aria-label="Selecionar página ou grupo de trechos">${options}</select></div></div><p class="preview-scope">${esc(scope)}</p><div class="preview-columns">${side?`<div class="paper-column"><div class="preview-title">Original <span>v1</span></div>${pageHTML(original,currentPage)}</div>`:''}<div class="paper-column"><div class="preview-title">Revisão <span>v${job.version}</span></div>${pageHTML(job,currentPage,'marked')}</div></div><details class="preview-note"><summary>Sobre a prévia</summary><p>${esc(job.analysis.info.preview)}</p></details></div>`;
}
function issueDetail(i,index,compact=false) {
  if (!i) return '<div class="empty-state"><span class="empty-flower" aria-hidden="true">✳</span><h3>Nenhum apontamento nesta página</h3><p>Escolha outro apontamento ou avance para continuar a revisão.</p></div>';
  let action='';
  if(i.image)action+=`<details class="image-check"><summary>Ver imagem</summary><img src="${esc(i.image)}" alt="Imagem sob revisão. A descrição encontrada está no painel de apontamentos.">${i.image_text?`<p><strong>Texto reconhecido:</strong> ${esc(i.image_text)}</p>`:''}</details>`;
  if (i.action==='alt') action+=`<form class="edit-form" data-index="${index}"><label>Descrição da imagem<textarea name="value" rows="3" required maxlength="3000" placeholder="O que é necessário para compreender a imagem?">${esc(['alt_quality','alt_placeholder'].includes(i.rule)?job.analysis.pages[i.page].blocks.find(b=>b.id===i.block_id)?.alt || '':'')}</textarea></label><button class="primary" type="submit">Salvar e verificar <span aria-hidden="true">↗</span></button></form>`;
  if (i.action==='font') action=`<form class="edit-form" data-index="${index}"><label>Fonte (pt)<input name="value" type="number" min="6" max="96" step="0.5" required value="${job.analysis.context.min_font}"></label><button class="primary" type="submit">Aplicar e verificar <span aria-hidden="true">↗</span></button></form>`;
  if (i.action==='contrast') action=`<button class="primary" data-correct="${index}">Corrigir contraste <span aria-hidden="true">↗</span></button>`;
  const isReviewed=reviewed.has(i.id);
  return `<div class="issue-detail"><span class="issue-category ${i.severity}"><span aria-hidden="true">${i.severity==='review'?'✳':'●'}</span> ${i.severity==='review'?'Conferência humana':'Ponto de atenção'} · ${esc(i.location)}</span><h3 tabindex="-1">${esc(i.title)}</h3><p class="issue-fact">${esc(i.explanation)}</p>${i.evidence?`<div class="evidence"><strong>${['alt_quality','alt_placeholder'].includes(i.rule)?'Descrição encontrada':'Identificado'}</strong><br>${esc(i.evidence)}</div>`:''}<p class="issue-guidance">${esc(i.suggestion)}</p>${i.text?`<details class="issue-more"><summary>Ver trecho <span aria-hidden="true">＋</span></summary><p>“${esc(i.text)}”</p></details>`:''}${action}<button class="text-button review-button" data-review="${index}" aria-pressed="${isReviewed}" title="Esta marcação pessoal não altera o diagnóstico.">${isReviewed?'✓ Conferido por mim':'Conferi este ponto'}</button>${isReviewed?'<span class="reviewed-label">Sua conferência não altera o diagnóstico.</span>':''}</div>`;
}
function issuePicker(issues) {
  return issues.length?`<div class="issue-picker"><label for="issue-select">Apontamento</label><select id="issue-select" aria-label="Escolher apontamento">${selected<0?'<option value="-1" selected disabled>Nenhum nesta página</option>':''}${issues.map((i,index)=>`<option value="${index}" ${index===selected?'selected':''}>${index+1} de ${issues.length} · ${esc(i.location)} · ${esc(i.title)}</option>`).join('')}</select></div>`:'';
}
function issueControls(issues) {
  return `<div class="step-controls" aria-label="Navegar pelos apontamentos"><button class="secondary small" data-step="-1" ${adjacentIssue(-1)<0?'disabled':''}>← Anterior</button><span class="step-counter">${selected<0?0:selected+1} / ${issues.length}</span><button class="secondary small" data-step="1" ${adjacentIssue(1)<0?'disabled':''}>Próximo →</button></div>`;
}
function adjacentIssue(direction) {
  const issues=job.analysis.issues;
  if(selected>=0){const target=selected+direction;return target>=0 && target<issues.length?target:-1;}
  const candidates=issues.map((i,index)=>({page:i.page,index})).filter(i=>i.page!==null && (direction>0?i.page>currentPage:i.page<currentPage)).sort((a,b)=>direction*(a.page-b.page) || a.index-b.index);
  return candidates[0]?.index ?? (direction>0?issues.findIndex(i=>i.page===null):-1);
}
function render() {
  if (!job) return;
  document.querySelectorAll('.tabs [role=tab]').forEach(b=>{
    const active=b.dataset.mode===mode; b.setAttribute('aria-selected',String(active)); b.tabIndex=active?0:-1;
  });
  $('review-panel').setAttribute('aria-labelledby','tab-'+mode);
  const issues=job.analysis.issues;
  const issue=issues[selected];
  if (mode==='side') {
    $('review-panel').innerHTML=`<div class="review-grid">${preview()}<aside class="issues-panel note-card" aria-label="Apontamentos da análise">${issuePicker(issues)}${issueDetail(issue,selected)}${issueControls(issues)}</aside></div>`;
  } else if (mode==='step') {
    $('review-panel').innerHTML=`<div class="step-layout">${preview(false)}<div class="step-note note-card">${issuePicker(issues)}${issueDetail(issue,selected)}${issueControls(issues)}</div></div>`;
  }
}
function animateReview() {
  const panel=$('review-panel');panel.getAnimations().forEach(a=>a.cancel());
  if(motionPaused || motionPreference.matches)return;
  panel.animate([{opacity:0,transform:'translateY(16px) scale(.988) rotateX(2deg)'},{opacity:1,transform:'translateY(0) scale(1) rotateX(0deg)'}],{duration:480,easing:'cubic-bezier(.22,1,.36,1)'});
}
function switchMode(next,focus=false) {
  if(!['side','step'].includes(next))return;
  mode=next;render();animateReview();if(focus)$('tab-'+mode).focus();announce('Modo '+$('tab-'+mode).textContent);
}
function selectIssue(index,focus=false) {
  selected=Math.max(0,Math.min(index,job.analysis.issues.length-1));
  const i=job.analysis.issues[selected]; if (i && i.page!==null) currentPage=i.page;
  render();
  if (focus) document.querySelector('.issue-detail h3')?.focus();
  if(i) announce('Item '+i.number+': '+i.title+'. '+i.location);
}
function dialog(title,html) {
  dialogReturnFocus=document.activeElement; $('dialog-title').textContent=title;
  $('dialog-body').innerHTML=html; $('dialog').showModal();
}
function initialReading(){
  return {title:job.filename,language:'pt-BR',items:job.analysis.pages.flatMap(p=>p.blocks.filter(b=>(b.type==='text' && b.text?.trim()) || b.image).map(b=>({id:b.id,page:p.label,text:b.type==='text'?b.text:b.alt || '',role:b.type==='text'?(b.heading?'h2':'p'):(b.decorative?'decorative':'figure'),confirmed:false})))};
}
function collectReading(){
  readingDraft.title=$('reading-title').value;readingDraft.language=$('reading-language').value;
  document.querySelectorAll('.reading-item').forEach(row=>{const item=readingDraft.items[Number(row.dataset.readingIndex)];item.text=row.querySelector('textarea').value;item.role=row.querySelector('select').value;item.confirmed=row.querySelector('input[type=checkbox]').checked;});
}
function renderReading(){
  const images=new Map(job.analysis.pages.flatMap(p=>p.blocks.filter(b=>b.image).map(b=>[b.id,b.image])));
  $('dialog-body').innerHTML=`<p>Confira o texto, as descrições e a ordem. Esta versão em HTML pode ser ampliada e lida por tecnologias assistivas; o arquivo original continua separado.</p><form id="reading-form"><label>Título<input id="reading-title" maxlength="180" required value="${esc(readingDraft.title)}"></label><label>Idioma<input id="reading-language" required value="${esc(readingDraft.language)}"></label><div class="reading-items">${readingDraft.items.map((item,index)=>`<section class="reading-item" data-reading-index="${index}"><div class="reading-item-heading"><strong>${index+1} · ${esc(item.page)}</strong><div><button class="text-button" type="button" data-reading-move="${index}" data-direction="-1" aria-label="Mover trecho ${index+1} para cima" ${index===0?'disabled':''}>↑</button><button class="text-button" type="button" data-reading-move="${index}" data-direction="1" aria-label="Mover trecho ${index+1} para baixo" ${index===readingDraft.items.length-1?'disabled':''}>↓</button></div></div>${images.has(item.id)?`<img src="${esc(images.get(item.id))}" alt="Imagem para conferir a descrição abaixo.">`:''}<label>Tipo<select>${(images.has(item.id)?[['figure','Imagem com descrição'],['decorative','Imagem decorativa']]:[['p','Parágrafo'],['h1','Título principal'],['h2','Título de seção'],['h3','Subtítulo']]).map(([value,label])=>`<option value="${value}" ${value===item.role?'selected':''}>${label}</option>`).join('')}</select></label><label>${images.has(item.id)?'Descrição':'Texto'}<textarea rows="3" maxlength="10000">${esc(item.text)}</textarea></label><label class="reading-confirm"><input type="checkbox" ${item.confirmed?'checked':''}> Conferi o conteúdo e esta posição na leitura</label></section>`).join('')}</div><div class="reading-save"><button class="primary" type="submit">Salvar leitura</button><a class="secondary" href="/api/job/${job.id}/reading" download>Baixar HTML</a><span>${job.reading?.reviewed?'Conferência do professor registrada.':'Aguardando conferência.'}</span></div><p id="reading-message" role="status"></p></form>`;
}
$('reading-button').addEventListener('click',()=>{readingDraft=structuredClone(job.reading || initialReading());dialog('Texto para leitura','');renderReading();});
async function correction(index,value) {
  const issue=job.analysis.issues[index];
  if ($('dialog').open) $('dialog').close();
  await run(async()=>showJob(await api('/api/edit',{id:job.id,issue_id:issue.id,value})), 'Salvando a alteração e verificando a nova versão');
}

$('file-input').addEventListener('change',e=>chooseFile(e.target.files[0]));
$('dropzone').addEventListener('dragover',e=>{e.preventDefault();$('dropzone').classList.add('dragover');});
$('dropzone').addEventListener('dragleave',()=>$('dropzone').classList.remove('dragover'));
$('dropzone').addEventListener('drop',e=>{e.preventDefault();$('dropzone').classList.remove('dragover');const f=e.dataTransfer.files[0];chooseFile(f);if(file===f){const dt=new DataTransfer();dt.items.add(f);$('file-input').files=dt.files;}});
$('material-form').addEventListener('submit',async e=>{
  e.preventDefault(); if(!file){message('Escolha um material para analisar.');return;}
  await run(async()=>{const data=await encodeFile(file); await showJob(await api('/api/analyze',{filename:file.name,file:data,context:context()}));},'Analisando o material');
});
$('demo-button').addEventListener('click',()=>run(async()=>{const j=await api('/api/demo',{});setContext(j.analysis.context);await showJob(j);},'Analisando uma atividade de exemplo'));
$('new-material').addEventListener('click',reset);
$('go-back').addEventListener('click',goBack);
document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();reset();});
$('history-new').addEventListener('click',reset);
$('history-clear').addEventListener('click',clearHistory);
$('history-undo').addEventListener('click',restoreHistory);
$('history-button').addEventListener('click',showHistory);
$('back-upload').addEventListener('click',()=>{ $('context-panel').hidden=true; $('start-panel').hidden=false; document.dispatchEvent(new CustomEvent('entrelinhas-view')); $('file-input').focus(); });
const motionPreference=window.matchMedia('(prefers-reduced-motion: reduce)');
let motionPaused=localStorage.getItem('entrelinhas-motion')==='paused' || motionPreference.matches;
function updateMotion() {
  document.body.classList.toggle('motion-paused',motionPaused);
  $('motion-button').setAttribute('aria-pressed',String(motionPaused));
  $('motion-button').setAttribute('aria-label',motionPaused?'Ativar animações':'Pausar animações');
  $('motion-button').title=motionPaused?'Ativar animações':'Pausar animações';
  $('motion-button').firstElementChild.textContent=motionPaused?'▷':'Ⅱ';
  document.dispatchEvent(new CustomEvent('entrelinhas-motion'));
}
$('motion-button').addEventListener('click',()=>{motionPaused=!motionPaused;localStorage.setItem('entrelinhas-motion',motionPaused?'paused':'enabled');updateMotion();});
motionPreference.addEventListener('change',e=>{motionPaused=e.matches;updateMotion();});
updateMotion();
$('recent-list').addEventListener('click',e=>{const b=e.target.closest('[data-open]');if(b)run(async()=>showJob(await api('/api/job/'+b.dataset.open)),'Abrindo a análise');});
$('upload-revision').addEventListener('click',()=>$('revision-input').click());
$('revision-input').addEventListener('change',async e=>{
  const revision=e.target.files[0];if(!revision)return;
  if(revision.size>20*1024*1024){message('O limite por material é de 20 MB.');return;}
  await run(async()=>{const data=await encodeFile(revision);await showJob(await api('/api/analyze',{filename:revision.name,file:data,context:job.analysis.context,parent_id:job.id}));},'Verificando a versão reenviada');
  e.target.value='';
});
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('[data-mode]');if(b && b.dataset.mode!==mode)switchMode(b.dataset.mode);});
document.querySelector('.tabs').addEventListener('keydown',e=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();
  const names=['side','step'];let index=names.indexOf(mode);
  index=e.key==='Home'?0:e.key==='End'?1:(index+(e.key==='ArrowRight'?1:-1)+names.length)%names.length;
  switchMode(names[index],true);
});
$('review-panel').addEventListener('change',e=>{if(e.target.id==='page-select'){selectPage(Number(e.target.value));$('page-select')?.focus();}if(e.target.id==='issue-select'){selectIssue(Number(e.target.value));animateReview();$('issue-select')?.focus();}});
$('review-panel').addEventListener('submit',e=>{const f=e.target.closest('.edit-form');if(f){e.preventDefault();correction(Number(f.dataset.index),new FormData(f).get('value'));}});
$('review-panel').addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.issue!==undefined){selectIssue(Number(b.dataset.issue));animateReview();$('issue-select')?.focus({preventScroll:true});}
  if(b.dataset.step){const target=adjacentIssue(Number(b.dataset.step));if(target>=0){selectIssue(target,true);animateReview();}}
  if(b.dataset.correct!==undefined){correction(Number(b.dataset.correct));}
  if(b.dataset.review!==undefined){const i=job.analysis.issues[Number(b.dataset.review)];reviewed.has(i.id)?reviewed.delete(i.id):reviewed.add(i.id);localStorage.setItem('entrelinhas-reviewed-'+job.id,JSON.stringify([...reviewed]));render();document.querySelector(`[data-review="${selected}"]`)?.focus({preventScroll:true});announce(reviewed.has(i.id)?'Item marcado como conferido por você.':'Conferência desmarcada.');}
  if(b.dataset.zoom){dialog(job.analysis.pages[currentPage].label,`<p class="muted">Prévia ampliada da versão ${job.version}. ${esc(job.analysis.info.preview)}</p>${pageHTML(job,currentPage,'marked',true)}`);}
});
$('assist-button').addEventListener('click',()=>{
  const eligible=job.analysis.issues.filter(i=>['font','contrast'].includes(i.action));
  dialog('Revise os ajustes antes de aplicar',`<p>Selecione os ajustes técnicos que deseja aplicar ao material. Será criada uma nova versão; o original permanece disponível.</p><form id="assist-form"><div class="assist-list">${eligible.slice(0,100).map(i=>`<label class="assist-option"><input type="checkbox" name="issues" value="${esc(i.id)}" checked><span><strong>${esc(i.title)}</strong><small>${esc(i.location)} · ${esc(i.evidence)}</small></span></label>`).join('')}</div><p>Descrições de imagens e o sentido da atividade continuam sob sua revisão. Mudanças de tamanho podem alterar o espaço ocupado pelo texto.</p><button class="primary" type="submit">Aplicar os ajustes selecionados</button></form>`);
});
$('dialog-body').addEventListener('submit',e=>{
  if(e.target.id==='reading-form'){
    e.preventDefault();collectReading();const button=e.target.querySelector('[type=submit]');button.disabled=true;
    api('/api/reading',{id:job.id,reading:readingDraft}).then(next=>{job=next;readingDraft=structuredClone(job.reading);renderReading();$('reading-message').textContent='Leitura salva. O arquivo original foi preservado.';}).catch(error=>{$('reading-message').textContent=error.message;button.disabled=false;});return;
  }
  if(e.target.id==='assist-form'){e.preventDefault();const selectedIssues=new FormData(e.target).getAll('issues');if(!selectedIssues.length)return;
    $('dialog').close();run(async()=>showJob(await api('/api/assist',{id:job.id,issues:selectedIssues})),'Aplicando os ajustes e verificando a nova versão');}
});
$('dialog-body').addEventListener('click',e=>{const move=e.target.closest('[data-reading-move]');if(move){collectReading();const index=Number(move.dataset.readingMove),next=index+Number(move.dataset.direction);[readingDraft.items[index],readingDraft.items[next]]=[readingDraft.items[next],readingDraft.items[index]];renderReading();document.querySelector(`[data-reading-move="${next}"][data-direction="${move.dataset.direction}"]`)?.focus();return;}const b=e.target.closest('[data-issue]');if(b){$('dialog').close();selectIssue(Number(b.dataset.issue),true);}});
$('close-dialog').addEventListener('click',()=>$('dialog').close());
$('dialog').addEventListener('close',()=>dialogReturnFocus?.isConnected && dialogReturnFocus.focus());
if(historyUndoToken){$('history-feedback').hidden=false;$('history-status').textContent='Você pode desfazer a última limpeza.';$('history-undo').hidden=false;}
recent();
