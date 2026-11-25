'use strict';
const AccessProfile=(()=>{
  const channels={visual:'Leitura visual ampliada',speech:'Leitor de tela com voz',braille:'Linha Braille',unknown:'Ainda não sei'};
  const tools={nvda:'NVDA',jaws:'JAWS',voiceover:'VoiceOver',talkback:'TalkBack',orca:'Orca',narrator:'Narrador do Windows',zoomtext:'ZoomText',fusion:'Fusion',os_magnifier:'Lupa do sistema',browser_zoom:'Zoom do navegador',braille_display:'Linha Braille',other:'Outro recurso',unknown:'Ainda não sei'};
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function fields(value,legacyTechnology=''){
    const p=value || {channels:['unknown'],tools:['unknown'],image_scale:1,visible_caption:'auto'};
    const choices=(key,labels)=>Object.entries(labels).map(([id,label])=>`<label class="access-choice"><input type="checkbox" data-access-choice="${key}" value="${id}" ${p[key]?.includes(id)?'checked':''}><span>${label}</span></label>`).join('');
    return `<div class="access-profile-fields" data-legacy-technology="${escape(legacyTechnology)}"><fieldset><legend>Como o estudante lê o material?</legend><p>Marque os recursos que ele utiliza. Pode combinar opções.</p><div class="access-choices">${choices('channels',channels)}</div></fieldset><details class="access-resource-details"><summary>Recursos e preferências do estudante</summary><fieldset><legend>Quais recursos ele já utiliza?</legend><div class="access-choices">${choices('tools',tools)}</div></fieldset><div class="field-row"><label>Ampliação inicial das imagens<select data-access-scale>${[1,1.25,1.5,2].map(n=>`<option value="${n}" ${n===p.image_scale?'selected':''}>${n===1?'Manter tamanho':`Aumentar ${Math.round((n-1)*100)}%`}</option>`).join('')}</select></label><label>Descrição visível junto à imagem<select data-access-caption>${Object.entries({auto:'Conforme a forma de leitura',yes:'Mostrar como legenda',no:'Somente descrição alternativa'}).map(([id,label])=>`<option value="${id}" ${id===p.visible_caption?'selected':''}>${escape(label)}</option>`).join('')}</select></label></div></details>${!value && legacyTechnology?`<p>Informado anteriormente: ${escape(legacyTechnology)}. Confira na seleção de recursos.</p>`:""}<p class="access-profile-status" role="status">${value?'Preferências informadas pelo professor.':'Confirme a forma de leitura com o estudante; não será presumida pela deficiência.'}</p></div>`;
  }
  function read(root){
    const result={};
    for(const key of ['channels','tools']){
      result[key]=[...root.querySelectorAll(`[data-access-choice="${key}"]:checked`)].map(input=>input.value);
      if(!result[key].length)result[key]=['unknown'];
    }
    result.image_scale=Number(root.querySelector('[data-access-scale]').value);
    result.visible_caption=root.querySelector('[data-access-caption]').value;
    return result;
  }
  function summary(root){
    const selected=read(root).tools.filter(tool=>tool!=='unknown');
    return selected.length?selected.map(tool=>tools[tool]).join(', '):root.querySelector('.access-profile-fields').dataset.legacyTechnology || 'A confirmar com o estudante';
  }
  function write(root,value,legacyTechnology=''){root.innerHTML=fields(value,legacyTechnology);}
  document.addEventListener('change',event=>{
    const input=event.target;if(!input.matches('[data-access-choice]'))return;
    const root=input.closest('.access-profile-fields'),key=input.dataset.accessChoice;
    if(input.checked){for(const other of root.querySelectorAll(`[data-access-choice="${key}"]`)){if(other!==input && (input.value==='unknown' || other.value==='unknown'))other.checked=false;}}
    if(!root.querySelector(`[data-access-choice="${key}"]:checked`))root.querySelector(`[data-access-choice="${key}"][value="unknown"]`).checked=true;
    root.querySelector('.access-profile-status').textContent='Preferências atualizadas para este estudante.';
  });
  return {fields,read,write,summary};
})();
