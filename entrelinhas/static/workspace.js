'use strict';
let workspaceState={profiles:[],progress:{},resume:null},accountInfo={user:null,scope:'guest'},progressTimer=0,pendingProgress=null,progressChain=Promise.resolve();
function reviewSnapshot(){return job && !job.is_example?{id:job.id,page:currentPage,issue_id:job.analysis.issues[selected]?.id ?? null,mode,reviewed:[...reviewed],filters:{...reviewFilters},scroll:window.scrollY}:null;}
function saveReviewProgress(){
  if(!job || job.is_example || currentView()!=='result')return;
  const snapshot=reviewSnapshot();pendingProgress=snapshot;
  workspaceState.progress[job.id]=snapshot;workspaceState.resume={id:job.id,filename:job.filename,version:job.version};
  try{localStorage.setItem('entrelinhas-progress-'+storageScope+'-'+job.id,JSON.stringify(snapshot));}catch(_){}
  $('progress-status').textContent='Salvando…';clearTimeout(progressTimer);progressTimer=setTimeout(flushProgress,250);updateResume();
}
async function flushProgress(){
  clearTimeout(progressTimer);
  const snapshot=pendingProgress;pendingProgress=null;
  if(snapshot){progressChain=progressChain.then(async()=>{try{await api('/api/progress',snapshot);$('progress-status').textContent='Revisão salva';}catch(_){$('progress-status').textContent='Servidor indisponível; posição salva no navegador';}});}
  return progressChain;
}
function updateResume(){
  $('resume-button').hidden=!workspaceState.resume;
  $('resume-name').textContent=workspaceState.resume?.filename || '';
}
function updateProfiles(){
  const select=$('profile-select'),value=select.value;
  select.innerHTML='<option value="">Preencher manualmente</option>'+workspaceState.profiles.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  if(workspaceState.profiles.some(p=>p.id===value))select.value=value;
}
async function reloadWorkspace(){
  workspaceState=await api('/api/workspace');updateResume();updateProfiles();
}
async function initializeWorkspace(){
  try{
    accountInfo=await api('/api/account');storageScope=accountInfo.scope;
    historyUndoToken=localStorage.getItem(historyStorageKey()) || null;
    $('account-label').textContent=accountInfo.user?.name.split(' ')[0] || 'Entrar';
    $('account-button').setAttribute('aria-label',accountInfo.user?'Abrir minha conta':'Entrar ou criar conta');
    await reloadWorkspace();
  }catch(_){$('progress-status').textContent='Não foi possível carregar os perfis salvos.';}
}
const workspaceReady=initializeWorkspace();

$('profile-select').addEventListener('change',()=>{
  const profile=workspaceState.profiles.find(p=>p.id===$('profile-select').value);
  if(!profile)return;
  $('needs').value=profile.needs;$('technology').value=profile.technology;$('min-font').value=profile.min_font ?? '';
  announce('Perfil '+profile.name+' aplicado. Confira se atende a este estudante.');
});
function profileEditor(profile=null){
  const values=profile || context();
  dialog(profile?'Editar perfil':'Salvar perfil',`<form id="profile-form" data-id="${profile?.id || ''}"><p>Salve as necessidades para reutilizar em outros materiais.</p><label>Nome do perfil<input id="profile-name" required maxlength="60" placeholder="Ex.: Tomás" value="${esc(profile?.name || '')}"></label><label>Necessidades<textarea id="profile-needs" required maxlength="3000" rows="3">${esc(values.needs || '')}</textarea></label><label>Tecnologias assistivas<input id="profile-technology" required maxlength="3000" value="${esc(values.technology || '')}"></label><label>Fonte preferida em pt <span class="optional">opcional</span><input id="profile-font" type="number" min="6" max="96" step="0.5" value="${values.min_font ?? ''}"></label><button class="primary" type="submit">Salvar perfil</button><p id="profile-feedback" role="status"></p></form>`);
  $('profile-name').focus();
}
$('profile-save').addEventListener('click',()=>profileEditor());
function profilesManager(){
  dialog('Seus perfis',`<div class="profile-list">${workspaceState.profiles.map(p=>`<div class="profile-list-item"><div><strong>${esc(p.name)}</strong><small>${esc(p.technology)}</small></div><button class="text-button" data-profile-edit="${p.id}">Editar</button><button class="text-button" data-profile-remove="${p.id}">Remover</button></div>`).join('') || '<p>Nenhum perfil salvo.</p>'}</div><button class="primary" id="profile-new">Novo perfil</button><p id="profile-feedback" role="status"></p>`);
}
$('profiles-manage').addEventListener('click',profilesManager);
$('resume-button').addEventListener('click',()=>run(async()=>{await flushProgress();await showJob(await api('/api/job/'+workspaceState.resume.id));},'Retomando a revisão'));
function setFilters(){
  reviewFilters={category:$('filter-category').value,status:$('filter-status').value};
  const visible=visibleIssueIndexes();
  if(!visible.includes(selected)){selected=visible[0] ?? -1;const issue=job.analysis.issues[selected];if(issue?.page!==null && issue?.page!==undefined)currentPage=issue.page;}
  render();announce(`${visible.length} apontamentos nesses filtros.`);
}
$('filter-category').addEventListener('change',setFilters);$('filter-status').addEventListener('change',setFilters);
$('filters-clear').addEventListener('click',()=>{$('filter-category').value='all';$('filter-status').value='all';setFilters();});
window.addEventListener('scroll',()=>{if(job && currentView()==='result'){clearTimeout(progressTimer);progressTimer=setTimeout(saveReviewProgress,300);}},{passive:true});
window.addEventListener('pagehide',()=>{
  const snapshot=currentView()==='result'?reviewSnapshot():pendingProgress;
  if(!snapshot)return;
  try{localStorage.setItem('entrelinhas-progress-'+storageScope+'-'+snapshot.id,JSON.stringify(snapshot));}catch(_){}
  const body=JSON.stringify(snapshot);if(body.length<60000)fetch('/api/progress',{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}).catch(()=>{});
});

function mascots(){return `<div class="mascot-stage" data-gaze="idle" aria-hidden="true"><div class="mascot-orbit"></div><div class="mascot-ground"></div><div class="mascot-group">${[1,3,2].map(n=>`<div class="pill-mascot pill-${n}"><div class="mascot-body">${n===1?'<span class="mascot-curl"></span><span class="mascot-badge">✳</span>':n===3?'<span class="mascot-headphones"><i></i><i></i></span>':''}<div class="mascot-face"><div class="mascot-eyes"><i><span></span></i><i><span></span></i></div><b class="mascot-smile"></b><span class="mascot-cheek cheek-left"></span><span class="mascot-cheek cheek-right"></span></div><div class="mascot-hand hand-left"><i></i><i></i><i></i></div><div class="mascot-hand hand-right"><i></i><i></i><i></i></div><span class="mascot-foot left"></span><span class="mascot-foot right"></span></div></div>`).join('')}</div><span class="mascot-star">✳</span><span class="mascot-spark">✦</span></div>`;}
let stopMascotTracking=()=>{};
function startMascotTracking(){
  stopMascotTracking();
  const stage=document.querySelector('.mascot-stage');if(!stage)return;
  const characters=[...stage.querySelectorAll('.pill-mascot')].map(element=>({element,x:0,y:0,tx:0,ty:0}));
  let frame=0,lastTime=0,disposed=false;
  const allowed=()=>!motionPaused && !motionPreference.matches && !document.hidden && $('dialog').open && stage.isConnected;
  function draw(time){
    frame=0;if(disposed || !allowed())return;
    const blend=1-Math.exp(-Math.min(time-lastTime || 16,50)/65);lastTime=time;
    let moving=false;
    for(const c of characters){
      c.x+=(c.tx-c.x)*blend;c.y+=(c.ty-c.y)*blend;
      moving ||= Math.abs(c.tx-c.x)+Math.abs(c.ty-c.y)>.003;
      c.element.style.setProperty('--look-x',c.x.toFixed(3));c.element.style.setProperty('--look-y',c.y.toFixed(3));
    }
    if(moving)frame=requestAnimationFrame(draw);else lastTime=0;
  }
  function schedule(){if(!frame && allowed()){lastTime=0;frame=requestAnimationFrame(draw);}}
  function aim(x,y){
    if(!allowed())return;
    for(const c of characters){
      // A stationary anchor keeps their own movement from changing the target.
      const rect=c.element.getBoundingClientRect(),dx=x-(rect.left+rect.width/2),dy=y-(rect.top+rect.height*.3);
      const length=Math.hypot(dx,dy),amount=Math.min(length/190,1);
      c.tx=length?dx/length*amount:0;c.ty=length?dy/length*amount:0;
    }
    schedule();
  }
  const pointer=event=>{if(event.pointerType!=='touch')aim(event.clientX,event.clientY);};
  const reset=()=>{for(const c of characters){c.tx=0;c.ty=0;}schedule();};
  const focus=event=>{if(event.target.matches('#auth-form input')){const r=event.target.getBoundingClientRect();aim(r.left+r.width/2,r.top+r.height/2);}};
  function sync(){
    if(allowed()){reset();return;}
    cancelAnimationFrame(frame);frame=0;lastTime=0;
    for(const c of characters){c.x=c.y=c.tx=c.ty=0;c.element.style.setProperty('--look-x','0');c.element.style.setProperty('--look-y','0');}
  }
  document.addEventListener('pointermove',pointer,{passive:true});document.addEventListener('pointerleave',reset);
  $('dialog').addEventListener('focusin',focus);document.addEventListener('visibilitychange',sync);document.addEventListener('entrelinhas-motion',sync);motionPreference.addEventListener('change',sync);
  // Other dialogs can replace this one without emitting a close event.
  const observer=new MutationObserver(()=>{if(!stage.isConnected)stop();});observer.observe($('dialog-body'),{childList:true});
  function stop(){
    disposed=true;cancelAnimationFrame(frame);observer.disconnect();
    document.removeEventListener('pointermove',pointer);document.removeEventListener('pointerleave',reset);$('dialog').removeEventListener('focusin',focus);
    document.removeEventListener('visibilitychange',sync);document.removeEventListener('entrelinhas-motion',sync);motionPreference.removeEventListener('change',sync);
  }
  stopMascotTracking=stop;
}
let authMode='login';
function authDialog(next='login'){
  authMode=next;
  dialog(next==='register'?'Criar sua conta':'Que bom te ver',`
    <div class="auth-layout">${mascots()}<div class="auth-fields">
      <div class="auth-tabs"><button class="text-button ${next==='login'?'selected':''}" data-auth-mode="login">Entrar</button><button class="text-button ${next==='register'?'selected':''}" data-auth-mode="register">Criar conta</button></div>
      <form id="auth-form">
        ${next==='register'?'<label>Seu nome<input name="name" id="auth-name" required maxlength="60" autocomplete="name"></label>':''}
        <label>${next==='register'?'E-mail':'E-mail ou nome de perfil'}<input name="${next==='register'?'email':'identifier'}" id="auth-email" type="${next==='register'?'email':'text'}" required maxlength="254" autocomplete="username" autocapitalize="none" spellcheck="false"></label>
        <label class="password-label">Senha<div class="password-field">
          <input name="password" id="auth-password" type="password" required minlength="${next==='register'?8:1}" maxlength="128" ${next==='register'?'aria-describedby="password-help"':''} autocomplete="${next==='register'?'new-password':'current-password'}">
          <button id="password-toggle" class="password-toggle" type="button" aria-label="Mostrar senha" title="Mostrar senha" aria-pressed="false">
            <svg class="password-eye" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            <svg class="password-eye-off" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 5.1 12 5c7 0 10 7 10 7a18 18 0 0 1-3.2 4.2M6.2 6.2A18 18 0 0 0 2 12s3 7 10 7c1.8 0 3.4-.5 4.8-1.2M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>
          </button>
        </div></label>
        ${next==='register'?'<p id="password-help" class="password-help">Use pelo menos 8 caracteres.</p>':''}
        ${next==='register'?'<label>Confirmar senha<input name="password_confirmation" id="auth-password-confirmation" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label>':''}
        <button id="auth-submit" class="primary" type="submit">${next==='register'?'Criar conta':'Entrar'} <span aria-hidden="true">↗</span></button><p id="auth-feedback" role="status"></p>
      </form>
      <div class="guest-choices"><button id="auth-guest" class="text-button">Continuar sem conta</button></div>
    </div></div>`);
  $('dialog').classList.add('auth-dialog');startMascotTracking();
}

function accountDialog(){
  if(!accountInfo.user){authDialog();return;}
  dialog('Sua conta',`<div class="account-summary"><span class="account-avatar">${esc(accountInfo.user.name.slice(0,1).toUpperCase())}</span><div><h3>${esc(accountInfo.user.name)}</h3><p>${esc(accountInfo.user.email)}</p></div></div><div class="account-choices"><button id="account-edit" class="secondary">Editar perfil</button><button id="account-profiles" class="secondary">Meus perfis</button><button id="account-logout" class="text-button">Sair da conta</button></div><p id="auth-feedback" role="status"></p>`);
}
$('account-button').addEventListener('click',accountDialog);
function accountProfileEditor(){
  if(!accountInfo.user)return;
  dialog('Editar perfil',`<form id="account-profile-form"><label>Seu nome<input name="name" id="account-name" required maxlength="60" autocomplete="name" value="${esc(accountInfo.user.name)}"></label><label>E-mail<input name="email" id="account-email" type="email" required maxlength="254" autocomplete="email" value="${esc(accountInfo.user.email)}"></label><div class="account-edit-actions"><button class="primary" type="submit">Salvar alterações</button><button class="text-button" type="button" id="account-edit-cancel">Cancelar</button></div><p id="account-edit-feedback" role="status"></p></form>`);
  $('account-name').focus();
}
let stopAccountConfetti=()=>{};
function celebrateAccountSave(){
  stopAccountConfetti();
  const feedback=$('auth-feedback');
  feedback.classList.add('account-save-success');
  feedback.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>Perfil atualizado!';
  if(motionPaused || motionPreference.matches || document.hidden)return;
  const modal=$('dialog'),avatar=modal.querySelector('.account-avatar'),bounds=avatar.getBoundingClientRect();
  const layer=document.createElement('div');layer.className='account-confetti';layer.setAttribute('aria-hidden','true');
  modal.append(layer);
  const originX=bounds.left+bounds.width/2,originY=bounds.top+bounds.height/2;
  const colors=['#b895f2','#7850ca','#f3bd68','#ee947d','#a8cdbb'];
  const animations=[];
  const cleanup=()=>{
    animations.forEach(animation=>animation.cancel());layer.remove();
    modal.removeEventListener('close',cleanup);
    document.removeEventListener('entrelinhas-motion',stopForMotion);
    document.removeEventListener('visibilitychange',stopForMotion);
    motionPreference.removeEventListener('change',stopForMotion);
    window.removeEventListener('resize',cleanup);
    if(stopAccountConfetti===cleanup)stopAccountConfetti=()=>{};
  };
  const stopForMotion=()=>{if(motionPaused || motionPreference.matches || document.hidden)cleanup();};
  stopAccountConfetti=cleanup;
  modal.addEventListener('close',cleanup,{once:true});
  document.addEventListener('entrelinhas-motion',stopForMotion);
  document.addEventListener('visibilitychange',stopForMotion);
  motionPreference.addEventListener('change',stopForMotion);
  window.addEventListener('resize',cleanup,{once:true});
  try{
    for(let index=0;index<44;index++){
      const piece=document.createElement('i');
      piece.style.background=colors[index%colors.length];piece.dataset.shape=String(index%3);
      piece.style.left=originX+'px';piece.style.top=originY+'px';layer.append(piece);
      const angle=-Math.PI+Math.random()*Math.PI,distance=75+Math.random()*180;
      const dx=Math.cos(angle)*distance,dy=Math.sin(angle)*distance,spin=(Math.random()-.5)*720;
      animations.push(piece.animate([
        {opacity:0,transform:'translate(-50%,-50%) scale(.25) rotate(0deg)'},
        {offset:.12,opacity:1},
        {offset:.5,opacity:1,transform:`translate(${dx*.65}px,${dy}px) scale(1) rotate(${spin*.5}deg)`},
        {offset:.78,opacity:1},
        {opacity:0,transform:`translate(${dx}px,${dy*.35+140}px) scale(.7) rotate(${spin}deg)`}
      ],{duration:1100+Math.random()*450,delay:index%6*14,easing:'cubic-bezier(.15,.6,.35,1)',fill:'both'}));
    }
    Promise.all(animations.map(animation=>animation.finished.catch(()=>{}))).then(cleanup);
  }catch(_){cleanup();}
}
function mascotGaze(){
  const stage=document.querySelector('.mascot-stage'),password=$('auth-password');if(!stage || !password)return;
  stage.dataset.gaze=password.type==='text'?'peek':['auth-name','auth-email'].includes(document.activeElement?.id)?'typing':'idle';
}
$('dialog').addEventListener('focusin',mascotGaze);$('dialog').addEventListener('focusout',()=>queueMicrotask(mascotGaze));
async function accountChanged(){
  navigationStack.length=0;pendingProgress=null;clearTimeout(progressTimer);
  reviewed=new Set();reviewFilters={category:'all',status:'all'};
  resetContent();await initializeWorkspace();updateBack();
  $('history-feedback').hidden=!historyUndoToken;$('history-undo').hidden=!historyUndoToken;
  if(historyUndoToken)$('history-status').textContent='Você pode desfazer a última limpeza.';
  recent();
}
$('dialog').addEventListener('close',()=>{if(!$('dialog').open){stopMascotTracking();$('dialog').classList.remove('auth-dialog');$('dialog-body').innerHTML='';}});
$('dialog-body').addEventListener('input',event=>{
  if(event.target.closest('#auth-form')){
    mascotGaze();
    const confirmation=$('auth-password-confirmation');
    if(confirmation)confirmation.setCustomValidity(confirmation.value && confirmation.value!==$('auth-password').value?'As senhas não coincidem.':'');
  }
});
$('dialog-body').addEventListener('submit',async event=>{
  if(event.target.id==='account-profile-form'){
    event.preventDefault();const button=event.target.querySelector('[type=submit]');button.disabled=true;
    $('account-edit-feedback').textContent='';
    try{
      const result=await api('/api/account/update',Object.fromEntries(new FormData(event.target)));
      accountInfo={...accountInfo,...result};
      $('account-label').textContent=result.user.name.split(' ')[0];
      accountDialog();$('account-edit').focus();celebrateAccountSave();announce('Perfil atualizado.');
    }catch(error){if($('account-edit-feedback'))$('account-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
  }
  if(event.target.id==='profile-form'){
    event.preventDefault();const button=event.target.querySelector('[type=submit]');button.disabled=true;
    try{
      const profile=await api('/api/profiles/save',{id:event.target.dataset.id || undefined,name:$('profile-name').value,needs:$('profile-needs').value,technology:$('profile-technology').value,min_font:$('profile-font').value});
      await reloadWorkspace();$('profile-select').value=profile.id;$('dialog').close();announce('Perfil salvo.');
    }catch(error){$('profile-feedback').textContent=error.message;}finally{button.disabled=false;}
  }
  if(event.target.id==='auth-form'){
    event.preventDefault();const form=event.target;const submit=$('auth-submit');submit.disabled=true;$('auth-feedback').textContent='';
    try{
      await flushProgress();const values=Object.fromEntries(new FormData(form));
      if(authMode==='register' && values.password!==values.password_confirmation)throw new Error('As senhas não coincidem.');
      await api('/api/account/'+(authMode==='register'?'register':'login'),values);
      $('auth-password').value='';$('dialog').close();await accountChanged();announce('Você entrou na sua conta.');
    }catch(error){if($('auth-feedback'))$('auth-feedback').textContent=error.message;}finally{submit.disabled=false;}
  }
});
$('dialog-body').addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.authMode){$('dialog').close();authDialog(button.dataset.authMode);}
  if(button.id==='auth-guest')$('dialog').close();
  if(button.id==='account-edit')accountProfileEditor();
  if(button.id==='account-edit-cancel'){accountDialog();$('account-edit').focus();}
  if(button.id==='account-profiles'){await workspaceReady;$('dialog').close();profilesManager();}
  if(button.id==='password-toggle'){
    const input=$('auth-password'),show=input.type==='password';input.type=show?'text':'password';button.setAttribute('aria-pressed',String(show));button.setAttribute('aria-label',show?'Ocultar senha':'Mostrar senha');button.title=show?'Ocultar senha':'Mostrar senha';mascotGaze();
  }
  if(button.id==='profile-new'){ $('dialog').close();profileEditor(); }
  if(button.dataset.profileEdit){const profile=workspaceState.profiles.find(p=>p.id===button.dataset.profileEdit);$('dialog').close();profileEditor(profile);}
  if(button.dataset.profileRemove){
    try{await api('/api/profiles/delete',{id:button.dataset.profileRemove});await reloadWorkspace();$('dialog').close();profilesManager();}catch(error){$('profile-feedback').textContent=error.message;}
  }
  if(button.id==='account-logout'){
    button.disabled=true;try{await flushProgress();await api('/api/account/logout',{});$('dialog').close();await accountChanged();announce('Você saiu da conta.');}catch(error){$('auth-feedback').textContent=error.message;button.disabled=false;}
  }
  if(button.id==='account-import'){
    button.disabled=true;try{const result=await api('/api/account/import-local',{});await reloadWorkspace();recent();$('auth-feedback').textContent=result.copied+' materiais copiados. Os originais continuam no espaço sem conta.';}catch(error){$('auth-feedback').textContent=error.message;}finally{button.disabled=false;}
  }
});

