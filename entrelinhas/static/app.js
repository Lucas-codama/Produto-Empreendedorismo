'use strict';
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let job = null, original = null, mode = 'side', selected = 0, currentPage = 0, file = null;
let resolvedNotice=null,finalPreviewJobId=null,reviewDrafts={};
let reviewed = new Set(), resolved = new Set(), dialogReturnFocus = null;
let storageScope='guest',reviewFilters={category:'all',status:'all'};
const historyStorageKey=()=> 'entrelinhas-history-undo'+(storageScope==='guest'?'':'-'+storageScope);
const visibleIssueIndexes=()=>job?ReviewRules.indexes(job.analysis.issues,reviewFilters,resolved):[];
let historyClearing=false,historyUndoToken=localStorage.getItem('entrelinhas-history-undo') || null;
let navigationInProgress = false;
const navigationStack=[];
let restoringPage=false;
function currentView(){return !$('history-view').hidden?'history':!$('result-view').hidden?'result':!$('context-panel').hidden?'context':'home';}
function rememberPage(){
  if(restoringPage)return;
  navigationStack.push({view:currentView(),job,original,mode,selected,currentPage,file,filters:{...reviewFilters},context:context(),scrollY:window.scrollY});
  if(navigationStack.length>12)navigationStack.shift();updateBack();
}
function updateBack(){$('page-controls').hidden=currentView()==='home';}
document.addEventListener('entrelinhas-view',updateBack);
async function goBack(){
  if(navigationInProgress || restoringPage)return;
  restoringPage=true;$('go-back').disabled=true;
  try{
    if(currentView()==='result'){captureReviewDraft();saveReviewProgress();}
    await flushProgress();navigationStack.length=0;resetContent();updateBack();
    announce('Você voltou ao início. Seu andamento foi salvo.');
  }catch(error){message(error.message || 'Não foi possível salvar o andamento. Tente novamente.');}
  finally{restoringPage=false;$('go-back').disabled=false;}
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
async function completeAnalysis(next){
  const overlay=$('busy'),icon=overlay.querySelector('.analysis-success-icon'),check=icon.querySelector('path');
  const animations=new Set();
  const allowed=()=>!motionPaused && !motionPreference.matches && !document.hidden;
  const stop=()=>{if(!allowed())animations.forEach(animation=>animation.finish());};
  const animate=async(element,frames,options)=>{
    if(!allowed())return;
    const animation=element.animate(frames,{fill:'forwards',...options});animations.add(animation);
    try{await animation.finished;}catch(_){}
  };
  document.addEventListener('entrelinhas-motion',stop);document.addEventListener('visibilitychange',stop);motionPreference.addEventListener('change',stop);
  try{
    $('main').classList.add('portal-managed');
    await showJob(next,false);
    // Success means the analysis finished, including when it found barriers.
    // Never show this confirmation after a failed request or before rendering.
    overlay.classList.add('analysis-success');$('busy-title').textContent='Análise concluída';
    window.scrollTo({top:0,behavior:'instant'});
    await Promise.all([
      animate(icon,[{opacity:0,transform:'scale(.88)'},{opacity:1,transform:'scale(1)'}],{duration:350,easing:'cubic-bezier(.22,1,.36,1)'}),
      animate(check,[{strokeDashoffset:40},{strokeDashoffset:0}],{duration:350,easing:'ease-out'})
    ]);
    await Promise.all([
      animate(overlay,[{opacity:1},{opacity:0}],{duration:220,easing:'ease-out'}),
      animate($('result-view'),[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],{duration:360,easing:'cubic-bezier(.22,1,.36,1)'})
    ]);
    $('result-title').tabIndex=-1;$('result-title').focus({preventScroll:true});
    return next;
  }finally{
    busy(false);animations.forEach(animation=>animation.cancel());overlay.classList.remove('analysis-success');
    document.removeEventListener('entrelinhas-motion',stop);document.removeEventListener('visibilitychange',stop);motionPreference.removeEventListener('change',stop);
  }
}
AccessProfile.write($('access-profile'));
function context() {
  return {discipline:$('discipline').value.trim(), activity:$('activity').value,
    needs:$('needs').value.trim(), technology:AccessProfile.summary($('access-profile')), min_font:$('min-font').value || null, access_preferences:AccessProfile.read($('access-profile'))};
}
function setContext(c) {
  $('discipline').value=c.discipline; $('activity').value=c.activity;
  AccessProfile.write($('access-profile'),c.access_preferences,c.technology);
  $('needs').value=c.needs; $('min-font').value=c.min_font ?? '';
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
    const section=(title,rows,done)=>`<section class="history-group"><h3>${title} <span>${rows.length}</span></h3>${rows.length?rows.map(j=>`<button class="recent-item" ${done?'data-review-record':'data-open'}="${j.id}"><span class="history-file"><span class="file-badge" aria-hidden="true">${esc(j.filename.split('.').pop().toUpperCase())}</span><strong>${esc(j.filename)}</strong></span><small>v${j.version} · ${done?'Concluída':'Em revisão'} · ${new Date(j.review?.completed_at || j.created_at).toLocaleDateString('pt-BR')}</small><span class="history-arrow" aria-hidden="true">${done?'✓':'↗'}</span></button>`).join(''):`<p class="muted">${done?'Nenhuma revisão concluída ainda.':'Nenhum material em revisão.'}</p>`}</section>`;
    $('recent-list').innerHTML=jobs.length?`<div class="history-groups">${section('Em revisão',jobs.filter(j=>j.review?.status!=='completed'),false)}${section('Concluídos',jobs.filter(j=>j.review?.status==='completed'),true)}</div>`:'<div class="empty-state">Você ainda não analisou nenhum material.</div>';
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
  const controls=['history-clear','history-new','new-material','history-button','go-back','account-button'].map($);controls.forEach(b=>b.disabled=true);
  const rows=[...document.querySelectorAll('.recent-item')];$('history-feedback').hidden=false;$('history-undo').hidden=true;$('history-status').textContent='Recolhendo seus materiais…';
  try{
    if(typeof flushProgress==='function')await flushProgress();
    const result=await api('/api/history/clear',{});historyUndoToken=result.undo_token;
    if(historyUndoToken)localStorage.setItem(historyStorageKey(),historyUndoToken);else localStorage.removeItem(historyStorageKey());
    const removed=new Set(result.ids);
    navigationStack.splice(0,navigationStack.length,...navigationStack.filter(s=>!removed.has(s.job?.id) && !removed.has(s.original?.id)));
    if(removed.has(job?.id)){job=null;original=null;}
    if(removed.has(localStorage.getItem('entrelinhas-last')))localStorage.removeItem('entrelinhas-last');
    updateBack();
    try{await animateHistoryClear(rows);}catch(_){/* A visual failure never changes the saved operation. */}
    $('history-status').textContent=result.count?'Histórico limpo.':'O histórico já está vazio.';$('history-undo').hidden=!historyUndoToken;
  }catch(error){$('history-status').textContent=error.message || 'Não foi possível limpar o histórico.';$('history-undo').hidden=!historyUndoToken;}
  finally{historyClearing=false;navigationInProgress=false;controls.forEach(b=>b.disabled=false);await recent();if(typeof reloadWorkspace==='function')await reloadWorkspace().catch(()=>{});if(historyUndoToken)$('history-undo').focus();else $('history-new').focus();}
}

async function restoreHistory(){
  if(!historyUndoToken || historyClearing)return;
  historyClearing=true;navigationInProgress=true;
  const controls=['history-clear','history-new','new-material','history-button','go-back','account-button'].map($);controls.forEach(b=>b.disabled=true);$('history-undo').disabled=true;
  try{const restored=await api('/api/history/restore',{token:historyUndoToken});historyUndoToken=null;localStorage.removeItem(historyStorageKey());$('history-undo').hidden=true;$('history-status').textContent=`${restored.count} ${restored.count===1?'análise recuperada.':'análises recuperadas.'}`;}
  catch(error){$('history-status').textContent=error.message;}
  finally{historyClearing=false;navigationInProgress=false;controls.forEach(b=>b.disabled=false);$('history-undo').disabled=false;await recent();if(typeof reloadWorkspace==='function')await reloadWorkspace().catch(()=>{});if(!historyUndoToken)$('history-clear').focus();}
}
async function showJob(next, focus=true) {
  rememberPage();
  if (!$('history-view').hidden) return navigatePaper('out',()=>showJobContent(next,focus));
  return showJobContent(next,focus);
}
async function showJobContent(next, focus=true) {
  resolvedNotice=null;
  if(typeof flushProgress==='function')await flushProgress();
  job=next; original=job.root_id === job.id ? job : await api('/api/job/'+job.root_id);
  let saved;
  if(!job.is_example){
    try{const state=await api('/api/workspace');saved=state.progress[job.id];}catch(_){}
    if(!saved){try{saved=JSON.parse(localStorage.getItem('entrelinhas-progress-'+storageScope+'-'+job.id) || 'null');}catch(_){}}
    if(!saved && storageScope==='guest'){let old=[];try{old=JSON.parse(localStorage.getItem('entrelinhas-reviewed-'+job.id) || '[]');}catch(_){}saved={reviewed:old};}
  }
  job.analysis.resolved_by_edit=job.resolved_issues || [];
  if(!Array.isArray(saved?.resolved))saved={...saved,resolved:job.resolved_issues || []};
  if(job.review?.status==='completed'){job.analysis.resolved_by_edit=job.analysis.issues.map(i=>i.id);saved={...saved,resolved:job.analysis.resolved_by_edit,filters:{category:'all',status:'pending'}};}
  reviewDrafts=saved?.drafts || {};finalPreviewJobId=null;
  const restored=ReviewRules.restore(job.analysis,saved);
  selected=restored.selected;currentPage=restored.page;mode=restored.mode;reviewed=restored.reviewed;resolved=restored.resolved;reviewFilters=restored.filters;

  if(!job.is_example)localStorage.setItem('entrelinhas-last',job.id);
  $('upload-view').hidden=true; $('history-view').hidden=true; $('result-view').hidden=false; nav('analyze');
  const a=job.analysis;
  $('result-title').textContent=job.filename;
  $('download-material').href='/api/job/'+job.id+'/file';
  $('download-material').textContent='Baixar documento · v'+job.version;
  $('result-context').textContent=`${a.context.discipline} · ${a.context.activity} · Versão ${job.version}`;
  $('access-focus').textContent=a.access_context?'Ajustes para: '+a.access_context.label:'';
  const access=a.access_context || {};
  $('access-plan').hidden=!access.checks?.length;
  $('access-plan-body').innerHTML=(access.checks || []).map(check=>`<p><strong>${esc(check.tool)}</strong><br>${esc(check.text)}</p>`).join('')+'<p class="muted">Estes testes são feitos com o recurso do estudante. A análise do site não confirma a compatibilidade com ele.</p>';
  $('upload-revision').hidden=job.review?.status==='completed';
  render(); recent();
  announce(resolved.size?`Revisão carregada. ${a.issues.length-resolved.size} apontamentos pendentes. ${resolved.size} ${resolved.size===1?'resolvido':'resolvidos'} por você.`:`Análise concluída. ${a.counts.attention} ${a.counts.attention===1?'ponto':'pontos'} de atenção e ${a.counts.review} ${a.counts.review===1?'item':'itens'} para revisão.`);
  if (focus) { $('result-title').tabIndex=-1; $('result-title').focus({preventScroll:true}); window.scrollTo({top:saved?.scroll || 0,behavior:'instant'}); }
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
  resolvedNotice=null;
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

function paperSource() {
  return !$('upload-view').hidden && !$('start-panel').hidden ? $('hero-art') : !$('result-view').hidden?document.querySelector('.analysis-emblem'):null;
}
function paperOrigin() {
  const source = paperSource();
  const r=source?.getBoundingClientRect();
  return r?.width && r?.height && r.bottom>0 && r.top<innerHeight ? {x:r.x,y:r.y,w:r.width,h:r.height} : {x:innerWidth*.58,y:innerHeight*.24,w:Math.min(innerWidth*.36,450),h:Math.min(innerHeight*.55,500)};
}
async function navigatePaper(direction, change) {
  if(navigationInProgress)return;
  if(motionPaused || motionPreference.matches){await change();return;}
  // The portal owns the entrance. A second CSS entrance moves its destination
  // while it is being measured and restarts the paper after the handoff.
  $('main').classList.add('portal-managed');
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
async function paperFallback({direction,origin,getOrigin,covered}) {
  const overlay=$('page-transition'),stage=$('portal-stage'),veil=$('portal-veil');
  overlay.hidden=false;stage.classList.add('css-portal');
  veil.style.opacity=direction==='out'?'1':'0';
  if(direction==='out'){await covered();origin=getOrigin();}
  const copy=paperSource()?.cloneNode(true);
  if(copy){copy.removeAttribute('id');copy.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));copy.classList.add('portal-copy');copy.setAttribute('aria-hidden','true');stage.append(copy);stage.classList.add('has-copy');}
  const start={left:origin.x+'px',top:origin.y+'px',width:origin.w+'px',height:origin.h+'px',transform:'none'},end={left:'0px',top:'0px',width:innerWidth+'px',height:innerHeight+'px',transform:'scale(1.15)'};
  try {
    const a=stage.animate(direction==='in'?[start,end]:[end,start],{duration:760,easing:'cubic-bezier(.65,0,.2,1)',fill:'forwards'});
    const v=veil.animate(direction==='in'?[{opacity:0,offset:0},{opacity:0,offset:.55},{opacity:1,offset:1}]:[{opacity:1,offset:0},{opacity:0,offset:.45},{opacity:0,offset:1}],{duration:760,fill:'forwards'});
    await a.finished;
    if(direction==='in')await covered();
    if(direction==='in')await overlay.animate([{opacity:1},{opacity:0}],{duration:160,fill:'forwards'}).finished;
    a.cancel();v.cancel();
  } finally {
    overlay.getAnimations().forEach(a=>a.cancel());stage.getAnimations().forEach(a=>a.cancel());veil.getAnimations().forEach(a=>a.cancel());
    copy?.remove();stage.classList.remove('css-portal','has-copy');veil.removeAttribute('style');overlay.hidden=true;
  }
}

function blockMarkers(page,index,selectedIssue,which) {
  if (which!=='marked') return '';
  const grouped=new Map();
  for (const issue of job.analysis.issues.filter(i=>i.page===index && ReviewRules.matches(i,reviewFilters,resolved))) {
    const b=page.blocks.find(b=>b.id===issue.block_id);
    if (!b || b.x===undefined || grouped.has(b.id)) continue;
    grouped.set(b.id,true);
  }
  return [...grouped.keys()].map(id=>{
    const b=page.blocks.find(b=>b.id===id);
    const issue=selectedIssue?.page===index && selectedIssue.block_id===id?selectedIssue:job.analysis.issues.find(i=>i.page===index && i.block_id===id && ReviewRules.matches(i,reviewFilters,resolved));
    const ix=job.analysis.issues.indexOf(issue);
    const active=selectedIssue && selectedIssue.block_id===id && selectedIssue.page===index;
    return `<button class="finding-marker ${active?'selected':''}" style="left:${b.x/page.width*100}%;top:${b.y/page.height*100}%;width:${Math.max(b.w/page.width*100,1)}%;height:${Math.max(b.h/page.height*100,1)}%" data-issue="${ix}" aria-label="Problema ${issue.number}: ${esc(issue.title)}"><span aria-hidden="true">${issue.number}</span></button>`;
  }).join('');
}
function selectPage(index) {
  captureReviewDraft();resolvedNotice=null;
  currentPage=Math.max(0,Math.min(index,job.analysis.pages.length-1));
  const issues=job.analysis.issues;
  if(issues[selected]?.page!==null && issues[selected]?.page!==currentPage)selected=visibleIssueIndexes().find(index=>issues[index].page===currentPage) ?? -1;
  render();announce(job.analysis.pages[currentPage].label);
}
function pageHTML(material,index,which='plain',large=false) {
  const page=material.analysis.pages[index];
  if (!page) return '<div class="empty-state">Essa versão não possui uma página correspondente.</div>';
  const chosen=job.analysis.issues[selected];
  const markers=blockMarkers(page,index,chosen,which);
  if (page.kind==='pdf') return `<div class="document-page" style="aspect-ratio:${page.width}/${page.height}"><img class="page-image" src="/api/job/${material.id}/page/${index}" alt="Imagem da ${esc(page.label)} do material. Os apontamentos estão descritos na lista de problemas.">${markers}</div>`;
  if (page.kind==='raster') return `<div class="document-page" style="aspect-ratio:${page.width}/${page.height}"><img class="page-image" src="${esc(page.blocks.find(b=>b.image)?.image || '')}" alt="Imagem enviada. Consulte os apontamentos no painel de revisão.">${markers}</div>`;
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
    const issues=which==='marked'?job.analysis.issues.filter(i=>i.page===index && i.block_id===b.id && ReviewRules.matches(i,reviewFilters,resolved)):[];
    const active=issues.length && chosen?.block_id===b.id && chosen?.page===index;
    const label=issues.length?`<span class="flow-label">${issues.map(i=>'Item '+i.number).join(' · ')} · ${esc(b.location || page.label)}</span>`:'';
    let content;
    if (b.image) content=`<img src="${esc(b.image)}" alt="${esc(b.alt || 'Imagem a conferir; descrição disponível no painel de revisão.')}">`;
    else if(b.runs) content=b.runs.map(r=>`<span style="${r.size?'font-size:'+r.size+'pt;':''}${r.color?'color:'+r.color+';':''}${r.background?'background-color:'+r.background+';':''}${r.bold?'font-weight:700;':''}">${esc(r.text)}</span>`).join('');
    else content=esc(b.text || 'Elemento visual');
    return `<div class="flow-block ${issues.length?'marked':''} ${active?'selected':''}" style="${b.background?'background-color:'+b.background+';':''}">${label}${content}</div>`;
  }).join('')}</div>`;
}
function completedPreview(){
  const options=job.analysis.pages.map((page,index)=>`<option value="${index}" ${index===currentPage?'selected':''}>${esc(page.label)}</option>`).join('');
  return `<section class="completed-preview"><div class="completed-preview-toolbar"><h3>Prévia da versão final</h3><label>Página<select id="completed-page" aria-label="Selecionar página da versão final">${options}</select></label><button class="text-button" type="button" data-final-zoom>Ampliar ↗</button></div><div class="completed-preview-paper">${pageHTML(job,currentPage,'plain',true)}</div></section>`;
}
function preview(side=true) {
  const page=job.analysis.pages[currentPage];
  const options=job.analysis.pages.map((p,i)=>`<option value="${i}" ${i===currentPage?'selected':''}>${esc(p.label)}</option>`).join('');
  const issue=job.analysis.issues[selected];
  const scope=issue?issue.page===null?'Conferência do documento inteiro. Use as páginas para conferir a sequência.':`${page.label} · ${issue.block_id==='document'?'Conferência da página; sem posição exata identificada.':'O elemento selecionado está marcado na revisão.'}`:`${page.label} · Nenhum apontamento específico nesta página.`;
  return `<div class="preview-card paper-board"><div class="board-clip" aria-hidden="true"></div><div class="preview-toolbar"><span class="format-chip">${esc(job.analysis.info.format)}</span><div><button class="text-button" data-zoom="1">Ampliar ↗</button> <select id="page-select" aria-label="Selecionar página ou grupo de trechos">${options}</select></div></div><p class="preview-scope">${esc(scope)}</p><div class="preview-columns">${side?`<div class="paper-column"><div class="preview-title">Original <span>v1</span></div>${pageHTML(original,currentPage)}</div>`:''}<div class="paper-column"><div class="preview-title">Revisão <span>v${job.version}</span></div>${pageHTML(job,currentPage,'marked')}</div></div><details class="preview-note"><summary>Sobre a prévia</summary><p>${esc(job.analysis.info.preview)}</p></details></div>`;
}
function quickImageForm(issue,index){
  const access=job.analysis.access_context || {},block=job.analysis.pages[issue.page].blocks.find(b=>b.id===issue.block_id);
  const aiUsage=job.ai_checks?.[issue.block_id] || {used:0,remaining:2};
  const description=aiUsage.result?aiUsage.description:block?.alt || block?.caption || '';
  const previousAI=aiUsage.result && aiUsage.description===description?aiUsage.result:null;
  return `<form class="quick-image-form" data-index="${index}" data-alt-supported="true"><h4>Editar imagem</h4><label>Descrição da imagem<textarea name="description" rows="4" maxlength="3000" placeholder="O que o aluno precisa saber sobre esta imagem?">${esc(description)}</textarea></label><div class="image-ai-tools"><button type="button" class="secondary" data-ai-check ${aiUsage.remaining===0?'disabled':''}>${aiUsage.remaining===0?'Descrição já aprovada':'Verificar com IA'}</button><div class="image-ai-result" role="status" ${previousAI?'':'hidden'}>${previousAI?imageAIResultHTML(previousAI):''}</div></div><label>Ampliação<select name="scale">${[1,1.25,1.5,2].map(scale=>`<option value="${scale}" ${scale===(access.image_scale || 1)?'selected':''}>${scale===1?'Manter tamanho':`Aumentar ${Math.round((scale-1)*100)}%`}</option>`).join('')}</select></label><label class="quick-caption-check"><input type="checkbox" name="visible" ${(block?.caption || (access.visible_caption ?? access.magnification))?'checked':''}>Mostrar a descrição como legenda</label><button class="primary" type="submit">Salvar imagem e verificar</button><p class="quick-image-feedback" role="status"></p></form>`;
}
function contrastRatio(first,second){
  const luminance=color=>{const c=[1,3,5].map(index=>parseInt(color.slice(index,index+2),16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2];};
  const a=luminance(first),b=luminance(second);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}
function resolvedNoticeHTML(){
  if(!resolvedNotice)return '';
  const pending=job.analysis.issues.some(issue=>!resolved.has(issue.id));
  return `<section class="resolved-notice" role="status"><span class="resolved-notice-icon" aria-hidden="true">✓</span><div><span class="resolved-notice-badge">Resolvido</span><h3 tabindex="-1">${esc(resolvedNotice.title)}</h3><p>${esc(resolvedNotice.location)}</p><p>${resolvedNotice.manual?'Você marcou este ponto como resolvido.':'A alteração foi salva e este ponto foi resolvido.'}</p>${pending?'<button type="button" class="secondary" data-next-pending>Continuar revisão</button>':''}</div></section>`;
}
function issueDetail(i,index,compact=false) {
  if(resolvedNotice)return resolvedNoticeHTML();
  if(i && resolved.has(i.id))return `<section class="resolved-notice"><span class="resolved-notice-icon">✓</span><div><span class="resolved-notice-badge">Resolvido</span><h3>${esc(i.title)}</h3><p>${esc(i.location)}</p></div></section>`;
  if(job.review?.status==='completed')return '<p>Revisão concluída. Consulte o registro no histórico.</p>';
  if(!i && !visibleIssueIndexes().length && job.analysis.issues.length)return '<div class="empty-state"><h3>Nenhum item nesses filtros</h3><p>Mude o tipo ou a conferência para ver outros apontamentos.</p></div>';
  if (!i) return '<div class="empty-state"><span class="empty-flower" aria-hidden="true">✳</span><h3>Nenhum apontamento nesta página</h3><p>Escolha outro apontamento ou avance para continuar a revisão.</p></div>';
  let action='';
  if(i.image)action+=`<details class="image-check"><summary>Ver imagem</summary><img src="${esc(i.image)}" alt="Imagem sob revisão. A descrição encontrada está no painel de apontamentos.">${i.image_text?`<p><strong>Texto reconhecido:</strong> ${esc(i.image_text)}</p>`:''}</details>`;
  if (i.action==='alt' && !i.quick_image) action+=`<form class="edit-form" data-index="${index}"><label>Descrição da imagem<textarea name="value" rows="3" required maxlength="3000" placeholder="O que é necessário para compreender a imagem?">${esc(['alt_quality','alt_placeholder'].includes(i.rule)?job.analysis.pages[i.page].blocks.find(b=>b.id===i.block_id)?.alt || '':'')}</textarea></label><button class="primary" type="submit">Salvar e verificar <span aria-hidden="true">↗</span></button></form>`;
  if (i.action==='font') action+=`<form class="edit-form" data-index="${index}"><label>Fonte (pt)<input name="value" type="number" min="6" max="96" step="0.5" required value="${job.analysis.context.min_font}"></label><button class="primary" type="submit">Aplicar e verificar <span aria-hidden="true">↗</span></button></form>`;
  if (i.action==='contrast') {
    const background=i.background || '#FFFFFF';
    const suggested=contrastRatio('#000000',background)>=contrastRatio('#FFFFFF',background)?'#000000':'#FFFFFF';
    action=`<form class="edit-form contrast-editor" data-index="${index}"><h4>Alterar a cor pelo site</h4><p>Escolha a cor e confira a amostra antes de salvar.</p><label>Cor do texto<input name="value" type="color" value="${suggested}" data-contrast-color data-background="${esc(background)}"></label><div class="contrast-sample" style="background:${esc(background)};color:${suggested}" aria-label="Amostra da combinação de cores">Texto de exemplo</div><p class="contrast-sample-info">${contrastRatio(suggested,background).toFixed(2)}:1 sobre o fundo identificado${i.explanation.includes('estim')?' (estimado)':''}.</p>${job.extension==='.pdf'?'<p>Confira o resultado na página depois de salvar.</p>':''}<button class="primary" type="submit">Salvar cor e verificar <span aria-hidden="true">↗</span></button></form>`;
  }
  if(i.rule==='contrast' && !i.action)action+='<p class="contrast-edit-limit">Este trecho não permite um ajuste rápido. Corrija no editor original e envie a nova versão.</p>';

  if(i.action==='language')action+=`<form class="edit-form" data-index="${index}"><label>Idioma do documento<input name="value" required maxlength="35" value="pt-BR" placeholder="pt-BR, en-US ou es-ES"></label><p>O idioma orienta a pronúncia do leitor de tela; não traduz o conteúdo.</p><button class="primary" type="submit">Salvar idioma e verificar</button></form>`;
  if(i.action==='heading')action+=`<form class="edit-form" data-index="${index}"><label>Alterar para<select name="value">${[1,2,3,4,5,6].map(level=>`<option value="H${level}" ${level===(i.heading_context?.suggested_level || 1)?'selected':''}>Título ${level}${level===i.heading_context?.suggested_level?' (sugerido)':''}</option>`).join('')}</select></label><button class="primary" type="submit">Salvar nível e verificar</button></form>`;
  if(i.action==='slide_title')action+=`<form class="edit-form" data-index="${index}"><label>Título do slide<input name="value" maxlength="200" required placeholder="O assunto principal deste slide"></label><p>O título será inserido no slide. Confira o espaço e possíveis sobreposições depois de salvar.</p><button class="primary" type="submit">Salvar título e verificar</button></form>`;
  if(i.action==='table_headers')action+=`<form class="edit-form" data-index="${index}"><p>Use somente se a primeira linha contiver os nomes das colunas.</p><button class="primary" type="submit">Marcar primeira linha como cabeçalho</button></form>`;
  if(i.quick_image)action+=quickImageForm(i,index);
  const resolution=(ReviewRules.canResolve(i) || resolved.has(i.id))?`<div class="manual-resolution"><button class="secondary" data-resolve="${index}" aria-pressed="${resolved.has(i.id)}">${resolved.has(i.id)?'Reabrir apontamento':'Marcar como resolvido'}</button>${resolved.has(i.id)?'<p role="status">Resolvido por você. Essa marcação não altera o arquivo.</p>':''}</div>`:'';
  const h=i.heading_context;
  const headingTarget=h?`<div class="heading-target"><strong>Título com problema</strong>${h.text?`<blockquote>“${esc(h.text)}”</blockquote>`:'<p>Não foi possível extrair o texto deste título nem localizar sua posição na página.</p>'}<p>${h.previous_level?`Título ${h.previous_level} → <strong>Título ${h.level}</strong>`:`Primeiro título: <strong>Título ${h.level}</strong>`}</p>${h.previous_text?`<p class="heading-previous">Título anterior: “${esc(h.previous_text)}”</p>`:''}${h.located?'<p>O trecho está destacado na prévia da revisão.</p>':h.text?'<p>A posição exata deste título não foi localizada na prévia.</p>':''}</div>`:'';
  return `<div class="issue-detail"><span class="issue-category ${i.severity}"><span aria-hidden="true">${i.severity==='review'?'✳':'●'}</span> ${i.severity==='review'?'Conferência humana':'Ponto de atenção'} · ${esc(i.location)}</span><h3 tabindex="-1">${esc(i.title)}</h3>${headingTarget}<p class="issue-fact">${esc(i.explanation)}</p>${i.rule==='contrast'?`<details class="evidence"><summary>Ver as cores e os valores medidos</summary><p>${esc(i.evidence)}</p></details>`:i.evidence?`<details class="evidence"><summary>Ver detalhes</summary><strong>${['alt_quality','alt_placeholder'].includes(i.rule)?'Descrição encontrada':'Identificado'}</strong><br>${esc(i.evidence)}</details>`:''}<p class="issue-guidance">${esc(i.suggestion)}</p>${i.text && !h?`<details class="issue-more"><summary>Ver trecho <span aria-hidden="true">＋</span></summary><p>“${esc(i.text)}”</p></details>`:''}${action}${resolution}</div>`;
}
function issuePicker(issues) {
  if(resolvedNotice)return "";
  const visible=visibleIssueIndexes();
  return visible.length?`<div class="issue-picker"><label for="issue-select">Apontamento</label><select id="issue-select" aria-label="Escolher apontamento">${selected<0?'<option value="-1" selected disabled>Nenhum nesta página</option>':''}${visible.map((index,position)=>`<option value="${index}" ${index===selected?'selected':''}>${position+1} de ${visible.length} · ${esc(issues[index].location)} · ${esc(issues[index].title)}</option>`).join('')}</select></div>`:'';
}
function issueControls(issues) {
  if(resolvedNotice)return "";
  const visible=visibleIssueIndexes();
  if(!visible.length)return '';
  return `<div class="step-controls" aria-label="Navegar pelos apontamentos"><button class="secondary small" data-step="-1" ${adjacentIssue(-1)<0?'disabled':''}>← Anterior</button><span class="step-counter">${visible.indexOf(selected)+1} / ${visible.length}</span><button class="secondary small" data-step="1" ${adjacentIssue(1)<0?'disabled':''}>Próximo →</button></div>`;
}
function adjacentIssue(direction) {
  const issues=job.analysis.issues;
  const visible=visibleIssueIndexes();
  if(selected>=0 && visible.includes(selected)){return visible[visible.indexOf(selected)+direction] ?? -1;}
  const candidates=visible.map(index=>({page:issues[index].page,index})).filter(i=>i.page!==null && (direction>0?i.page>currentPage:i.page<currentPage)).sort((a,b)=>direction*(a.page-b.page) || a.index-b.index);
  return candidates[0]?.index ?? (direction>0?visible.find(index=>issues[index].page===null) ?? -1:-1);
}
function render() {
  if (!job) return;
  const visible=visibleIssueIndexes();
  if(selected>=0 && !visible.includes(selected)){selected=visible[0] ?? -1;const next=job.analysis.issues[selected];if(next?.page!==null && next?.page!==undefined)currentPage=next.page;}
  $('filter-category').value=reviewFilters.category;$('filter-status').value=reviewFilters.status;
  const pending=job.analysis.issues.filter(issue=>!resolved.has(issue.id)),attention=pending.filter(issue=>issue.severity!=='review').length,human=pending.length-attention;
  $('stats').innerHTML=`<span class="analysis-count"><span class="count-dot" aria-hidden="true"></span><b>${attention}</b> ${attention===1?'ponto pendente':'pontos pendentes'}</span>${human?`<span class="analysis-count human"><b>${human}</b> para conferir</span>`:''}${resolved.size?`<span class="analysis-count human">${resolved.size} ${resolved.size===1?'resolvido por você':'resolvidos por você'}</span>`:''}${job.analysis.measured.unknown_contrast?`<span class="analysis-count incomplete" title="Esses trechos não tiveram o contraste medido.">Contraste pendente em ${job.analysis.measured.unknown_contrast} trechos</span>`:''}`;
  $('filter-count').textContent=`${visible.length} de ${job.analysis.issues.length} itens`;
  $('filters-clear').hidden=reviewFilters.category==='all' && reviewFilters.status==='all';
  document.querySelectorAll('.tabs [role=tab]').forEach(b=>{
    const active=b.dataset.mode===mode; b.setAttribute('aria-selected',String(active)); b.tabIndex=active?0:-1;
  });
  $('review-panel').setAttribute('aria-labelledby','tab-'+mode);
  const issues=job.analysis.issues;
  const issue=issues[selected];
  const panel=$('review-panel'),key=[job.id,original.id,currentPage,mode].join(':'),oldPreview=panel.querySelector('.preview-card');
  const reuse=oldPreview && panel.dataset.previewKey===key && job.analysis.pages[currentPage].kind!=='flow';
  if(job.review?.status==='completed' || (!pending.length && reviewFilters.status!=='resolved' && reviewFilters.status!=='all')){
    if(finalPreviewJobId!==job.id){currentPage=0;finalPreviewJobId=job.id;}
    panel.innerHTML=`<div class="review-complete" tabindex="-1"><span aria-hidden="true">✓</span><h3>Revisão concluída!</h3><p>Todos os apontamentos desta versão foram tratados. Consulte as alterações no histórico.</p>${resolvedNoticeHTML()}${completedPreview()}<a class="primary review-download" href="/api/job/${job.id}/file">Baixar nova versão</a></div>`;
    panel.dataset.previewKey='';
  }else{
    const paper=reuse?'<div data-preview-slot></div>':preview(mode==='side');
    const template=document.createElement('template');
    template.innerHTML=mode==='side'?`<div class="review-grid">${paper}<aside class="issues-panel note-card" aria-label="Apontamentos da análise">${issuePicker(issues)}${issueDetail(issue,selected)}${issueControls(issues)}</aside></div>`:`<div class="step-layout">${paper}<div class="step-note note-card">${issuePicker(issues)}${issueDetail(issue,selected)}${issueControls(issues)}</div></div>`;
    if(reuse){
      template.content.querySelector('[data-preview-slot]').replaceWith(oldPreview);
      const current=oldPreview.querySelector('.paper-column:last-child .document-page');
      current?.querySelectorAll('.finding-marker').forEach(marker=>marker.remove());
      current?.insertAdjacentHTML('beforeend',blockMarkers(job.analysis.pages[currentPage],currentPage,issue,'marked'));
      oldPreview.querySelector('.preview-scope').textContent=issue?.page===null?'Conferência do documento inteiro. Use as páginas para conferir a sequência.':job.analysis.pages[currentPage].label+' · O elemento selecionado está marcado na revisão.';
    }
    panel.replaceChildren(template.content);panel.dataset.previewKey=key;
  }
  restoreReviewDraft();
  if(typeof saveReviewProgress==='function')saveReviewProgress();
}
function animateReview() {
  const panel=document.querySelector('.issues-panel,.step-note');if(!panel)return;panel.getAnimations().forEach(a=>a.cancel());
  if(motionPaused || motionPreference.matches)return;
  panel.animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:'cubic-bezier(.22,1,.36,1)'});
}
function switchMode(next,focus=false) {
  if(!['side','step'].includes(next))return;
  mode=next;render();animateReview();if(focus)$('tab-'+mode).focus();announce('Modo '+$('tab-'+mode).textContent);
}
function selectIssue(index,focus=false) {
  captureReviewDraft();resolvedNotice=null;
  selected=Math.max(0,Math.min(index,job.analysis.issues.length-1));
  const i=job.analysis.issues[selected]; if (i && i.page!==null) currentPage=i.page;
  render();
  if (focus) document.querySelector('.issue-detail h3')?.focus();
  if(i) announce('Item '+i.number+': '+i.title+'. '+i.location);
}
function dialog(title,html) {
  $('dialog').classList.remove('auth-dialog');
  dialogReturnFocus=document.activeElement; $('dialog-title').textContent=title;
  $('dialog-body').innerHTML=html; $('dialog').showModal();
}
async function acceptEditedJob(next,previousResolved,previousIssue){
  const ids=new Set(next.analysis.issues.map(i=>i.id));
  next.resolved_issues=[...new Set([...(next.resolved_issues || []),...previousResolved])].filter(id=>ids.has(id));
  const scroll=window.scrollY;
  await showJob(next,false);
  reviewFilters.status='all';
  const counterpart=next.analysis.issues.findIndex(issue=>ReviewRules.sameTarget(previousIssue,issue));
  const stillPending=counterpart>=0 && !resolved.has(next.analysis.issues[counterpart].id);
  resolvedNotice=previousIssue && !stillPending?{title:previousIssue.title,location:previousIssue.location,manual:false}:null;
  selected=counterpart;
  if(selected<0)selected=visibleIssueIndexes()[0] ?? -1;
  if(selected>=0 && job.analysis.issues[selected].page!==null)currentPage=job.analysis.issues[selected].page;
  render();window.scrollTo({top:scroll,behavior:'instant'});
  (document.querySelector('.resolved-notice h3,.issue-detail h3,.review-complete') || $('result-title')).focus({preventScroll:true});
  return !stillPending;
}
async function correction(index,value) {
  const issue=job.analysis.issues[index],identity=job.id,previousResolved=[...resolved];prepareReviewSound();
  let completed=false;
  if ($('dialog').open) $('dialog').close();
  const updated=await run(async()=>{await flushProgress();const next=await api('/api/edit',{id:identity,issue_id:issue.id,value});if(job?.id!==identity)return null;completed=await acceptEditedJob(next,previousResolved,issue);return next;}, 'Salvando a alteração e verificando a nova versão');
  if(updated && completed)celebrateReview(job.analysis.issues.some(i=>!resolved.has(i.id))?'Alteração salva!':'Revisão concluída!');
  else if(updated)message('A alteração foi salva, mas este ponto ainda precisa de ajuste. Confira o valor informado.');
}

$('file-input').addEventListener('change',e=>chooseFile(e.target.files[0]));
$('dropzone').addEventListener('dragover',e=>{e.preventDefault();$('dropzone').classList.add('dragover');});
$('dropzone').addEventListener('dragleave',()=>$('dropzone').classList.remove('dragover'));
$('dropzone').addEventListener('drop',e=>{e.preventDefault();$('dropzone').classList.remove('dragover');const f=e.dataTransfer.files[0];chooseFile(f);if(file===f){const dt=new DataTransfer();dt.items.add(f);$('file-input').files=dt.files;}});
$('material-form').addEventListener('submit',async e=>{
  e.preventDefault(); if(!$('busy').hidden)return;if(!file){message('Escolha um material para analisar.');return;}
  await run(async()=>{const data=await encodeFile(file); await completeAnalysis(await api('/api/analyze',{filename:file.name,file:data,context:context()}));},'Analisando o material');
});
let exampleOpening=false;
async function openExample(){
  if(exampleOpening || navigationInProgress)return;
  exampleOpening=true;
  const overlay=$('busy'),card=overlay.querySelector('.busy-card'),progress=$('example-progress');
  const animations=new Set();
  const allowed=()=>!motionPaused && !motionPreference.matches && !document.hidden;
  const stop=()=>{if(!allowed())animations.forEach(animation=>animation.finish());};
  const animate=async(element,frames,options)=>{
    if(!allowed())return;
    // Hold each endpoint until the whole transition is finished. Cancelling
    // the shorter fade early restored the loading overlay's opacity to 1.
    const animation=element.animate(frames,{fill:'forwards',...options});animations.add(animation);
    try{await animation.finished;}catch(_){}
  };
  message('');overlay.classList.add('example-loading');progress.removeAttribute('aria-valuenow');
  progress.setAttribute('aria-label','Carregando o exemplo');busy(true,'Abrindo o exemplo');
  document.addEventListener('entrelinhas-motion',stop);document.addEventListener('visibilitychange',stop);motionPreference.addEventListener('change',stop);
  try{
    // The bar stays indeterminate while the server works; completion is only
    // shown after the material and review are actually ready.
    const [next]=await Promise.all([
      api('/api/demo',{}),
      animate(card,[{opacity:0,transform:'translateY(140px) rotate(4deg)'},{opacity:1,transform:'translateY(0) rotate(0deg)'}],{duration:430,easing:'cubic-bezier(.22,1,.36,1)'})
    ]);
    // This transition owns the entrance; suppress the ordinary entrance so
    // it does not restart when the pull-up animation releases the element.
    $('main').classList.add('portal-managed');
    setContext(next.analysis.context);await showJob(next,false);
    overlay.classList.add('example-ready');progress.setAttribute('aria-valuenow','100');progress.setAttribute('aria-label','Exemplo carregado');
    $('busy-title').textContent='Pronto para revisar';
    await animate(progress.firstElementChild,[{transform:'scaleX(.35)'},{transform:'scaleX(1)'}],{duration:230,easing:'ease-out'});
    $('result-view').classList.add('example-arrival');
    await Promise.all([
      animate(overlay,[{opacity:1},{opacity:0}],{duration:300,easing:'ease-out'}),
      animate($('result-view'),[{opacity:0,transform:'translateY(80px)'},{opacity:1,transform:'translateY(0)'}],{duration:560,easing:'cubic-bezier(.22,1,.36,1)'})
    ]);
    $('result-title').tabIndex=-1;$('result-title').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});
  }catch(error){message(error.message || 'Não foi possível abrir o exemplo.');}
  finally{
    // Hide first, then release the held animation styles; never expose the
    // loading card again between the fade and the end of the result entrance.
    busy(false);
    animations.forEach(animation=>animation.cancel());
    document.removeEventListener('entrelinhas-motion',stop);document.removeEventListener('visibilitychange',stop);motionPreference.removeEventListener('change',stop);
    overlay.classList.remove('example-loading','example-ready');$('result-view').classList.remove('example-arrival');exampleOpening=false;
  }
  if(typeof saveReviewProgress==='function')saveReviewProgress();
}
$('demo-button').addEventListener('click',openExample);
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
$('recent-list').addEventListener('click',e=>{const b=e.target.closest('[data-review-record]');if(b)run(()=>showReviewRecord(b.dataset.reviewRecord),'Abrindo revisão concluída');});
$('upload-revision').addEventListener('click',()=>$('revision-input').click());
$('revision-input').addEventListener('change',async e=>{
  const revision=e.target.files[0];if(!revision)return;
  if(revision.size>20*1024*1024){message('O limite por material é de 20 MB.');return;}
  await run(async()=>{const data=await encodeFile(revision);await completeAnalysis(await api('/api/analyze',{filename:revision.name,file:data,context:job.analysis.context,parent_id:job.id}));},'Verificando a versão reenviada');
  e.target.value='';
});
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('[data-mode]');if(b && b.dataset.mode!==mode)switchMode(b.dataset.mode);});
document.querySelector('.tabs').addEventListener('keydown',e=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();
  const names=['side','step'];let index=names.indexOf(mode);
  index=e.key==='Home'?0:e.key==='End'?1:(index+(e.key==='ArrowRight'?1:-1)+names.length)%names.length;
  switchMode(names[index],true);
});
$('review-panel').addEventListener('change',e=>{if(e.target.id==='completed-page'){currentPage=Number(e.target.value);render();$('completed-page')?.focus({preventScroll:true});}if(e.target.id==='page-select'){selectPage(Number(e.target.value));$('page-select')?.focus();}if(e.target.id==='issue-select'){selectIssue(Number(e.target.value));animateReview();$('issue-select')?.focus();}});
$('review-panel').addEventListener('submit',e=>{const f=e.target.closest('.edit-form');if(f){e.preventDefault();correction(Number(f.dataset.index),new FormData(f).get('value'));}});
$('review-panel').addEventListener('submit',async event=>{
  const form=event.target.closest('.quick-image-form');if(!form)return;
  event.preventDefault();const values=Object.fromEntries(new FormData(form)),issue=job.analysis.issues[Number(form.dataset.index)],identity=job.id;
  const feedback=form.querySelector('.quick-image-feedback'),button=form.querySelector('[type=submit]');
  const description=values.description.trim(),value={scale:Number(values.scale)};
  if(description && form.dataset.altSupported==='true')value.alt=description;
  if(values.visible && description)value.caption=description;
  if(value.scale===1 && !value.alt && !value.caption){feedback.textContent='Escreva a descrição ou escolha uma ampliação.';return;}
  prepareReviewSound();const previousResolved=[...resolved];button.disabled=true;feedback.textContent='Salvando…';
  try{await flushProgress();const next=await api('/api/image-adjust',{id:identity,issue_id:issue.id,value});if(job?.id===identity){
    const completed=await acceptEditedJob(next,previousResolved,issue);
    if(completed)celebrateReview(job.analysis.issues.some(i=>!resolved.has(i.id))?'Imagem atualizada!':'Revisão concluída!');
    else{const text=next.unchanged?'Esta descrição já está salva. Confira o conteúdo e marque como resolvido quando estiver correto.':'Descrição salva. Confira o conteúdo ou verifique com IA; depois marque como resolvido quando estiver correto.';const currentFeedback=document.querySelector('.quick-image-feedback');if(currentFeedback)currentFeedback.textContent=text;announce(text);}
  }}
  catch(error){if(feedback.isConnected)feedback.textContent=error.message;}
  finally{button.disabled=false;}
});
$('review-panel').addEventListener('input',event=>{
  if(!event.target.matches('[data-contrast-color]'))return;
  const input=event.target,form=input.closest('.contrast-editor');
  form.querySelector('.contrast-sample').style.color=input.value;
  form.querySelector('.contrast-sample-info').textContent=contrastRatio(input.value,input.dataset.background).toFixed(2)+':1 sobre o fundo identificado. O resultado final será verificado depois de salvar.';
});
$('review-panel').addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.issue!==undefined){selectIssue(Number(b.dataset.issue));animateReview();$('issue-select')?.focus({preventScroll:true});}
  if(b.dataset.step){const target=adjacentIssue(Number(b.dataset.step));if(target>=0){selectIssue(target,true);animateReview();}}
  if(b.hasAttribute('data-show-resolved')){reviewFilters={category:'all',status:'resolved'};selected=visibleIssueIndexes()[0] ?? -1;render();return;}
  if(b.hasAttribute('data-next-pending')){resolvedNotice=null;reviewFilters.status='all';const next=job.analysis.issues.findIndex(issue=>!resolved.has(issue.id));if(next>=0)selectIssue(next,true);return;}
  if(b.dataset.resolve!==undefined){const issue=job.analysis.issues[Number(b.dataset.resolve)];if(!issue || (!ReviewRules.canResolve(issue) && !resolved.has(issue.id)))return;const reopening=resolved.has(issue.id);prepareReviewSound();reopening?resolved.delete(issue.id):resolved.add(issue.id);resolvedNotice=reopening?null:{title:issue.title,location:issue.location,manual:true};reviewFilters.status='all';render();(document.querySelector('.resolved-notice h3,.issue-detail h3,.review-complete') || $('filter-status')).focus({preventScroll:true});announce(reopening?'Apontamento reaberto.':'Marcado como resolvido por você.');if(!reopening)celebrateReview(job.analysis.issues.some(i=>!resolved.has(i.id))?'Ponto resolvido!':'Revisão concluída!');}
  if(b.dataset.correct!==undefined){correction(Number(b.dataset.correct));}
  if(b.hasAttribute('data-final-zoom')){dialog('Prévia da versão final',pageHTML(job,currentPage,'plain',true));}
  if(b.dataset.zoom){dialog(job.analysis.pages[currentPage].label,`<p class="muted">Prévia ampliada da versão ${job.version}. ${esc(job.analysis.info.preview)}</p>${pageHTML(job,currentPage,'marked',true)}`);}
});
$('dialog-body').addEventListener('click',e=>{const b=e.target.closest('[data-issue]');if(b){$('dialog').close();selectIssue(Number(b.dataset.issue),true);}});
$('close-dialog').addEventListener('click',()=>$('dialog').close());
$('dialog').addEventListener('close',()=>dialogReturnFocus?.isConnected && dialogReturnFocus.focus());
if(historyUndoToken){$('history-feedback').hidden=false;$('history-status').textContent='Você pode desfazer a última limpeza.';$('history-undo').hidden=false;}
recent();
