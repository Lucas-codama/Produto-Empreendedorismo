'use strict';
const imageAIResults=new WeakMap();
const normalizeAIText=text=>String(text || '').normalize('NFKC').trim().replace(/\s+/g,' ').toLocaleLowerCase('pt-BR');
const imageAITitles={adequada:'A descrição está boa',parcial:'A descrição precisa de ajustes',incompativel:'O texto não corresponde à imagem',incerta:'A IA não conseguiu confirmar',sem_descricao:'Escreva uma descrição'};
function imageAIResultHTML(result){
  const approved=result.approved===true;
  return `<strong>${approved?'A descrição está boa':esc(imageAITitles[result.verdict] || 'Resultado da verificação')}</strong><p>${esc(result.explanation)}</p>${!approved && result.differences.length?`<ul>${result.differences.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}${!approved && result.suggested_description?`<div class="image-ai-suggestion"><strong>Descrição sugerida</strong><p>${esc(result.suggested_description)}</p><button type="button" class="text-button" data-ai-use>Usar sugestão</button></div>`:''}`;
}
$('review-panel').addEventListener('click',async event=>{
  const button=event.target.closest('[data-ai-check],[data-ai-use]');if(!button)return;
  const form=button.closest('.quick-image-form');if(!form)return;
  const field=form.elements.description,resultBox=form.querySelector('.image-ai-result');
  const issue=job.analysis.issues[Number(form.dataset.index)];
  if(button.hasAttribute('data-ai-use')){
    const result=imageAIResults.get(form) || job.ai_checks?.[issue.block_id]?.result;if(!result?.suggested_description || result.approved)return;
    field.value=result.suggested_description;field.dispatchEvent(new Event('input',{bubbles:true}));field.focus();
    form.querySelector('.quick-image-feedback').textContent='Sugestão colocada no campo. Confira o texto e salve a imagem.';
    return;
  }
  const identity=job.id,description=field.value;
  if(!description.trim()){resultBox.hidden=false;resultBox.textContent='Escreva uma descrição antes de verificar com IA.';field.focus();announce(resultBox.textContent);return;}
  form.dataset.aiChecking='true';button.disabled=true;button.textContent='Verificando…';resultBox.hidden=false;resultBox.textContent='Comparando a descrição com a imagem…';imageAIResults.delete(form);
  try{
    const result=await api('/api/ai/image-description',{id:identity,issue_id:issue.id,description});
    if(!form.isConnected || job?.id!==identity)return;
    job.ai_checks ||= {};job.ai_checks[issue.block_id]={used:result.checks_used,remaining:result.checks_remaining,result,description};
    if(field.value!==description){resultBox.textContent='O texto mudou durante a análise. Clique em verificar novamente.';return;}
    imageAIResults.set(form,result);
    resultBox.innerHTML=imageAIResultHTML(result);
    announce(imageAITitles[result.verdict] || 'Verificação concluída.');
  }catch(error){
    if(job?.id===identity && error.message?.includes('já foi aprovada duas vezes')){
      job.ai_checks ||= {};job.ai_checks[issue.block_id]={...job.ai_checks[issue.block_id],description,used:2,remaining:0};
    }
    if(form.isConnected){resultBox.textContent=error.message || 'Não foi possível verificar a imagem.';announce(resultBox.textContent);}
  }finally{delete form.dataset.aiChecking;const same=normalizeAIText(field.value)===normalizeAIText(description),exhausted=same && job?.id===identity && job.ai_checks?.[issue.block_id]?.remaining===0;button.disabled=exhausted;button.textContent=exhausted?'Descrição já aprovada':'Verificar com IA';}
});
$('review-panel').addEventListener('input',event=>{
  if(event.target.name!=='description')return;
  const form=event.target.closest('.quick-image-form');if(!form)return;
  imageAIResults.delete(form);form.querySelector('.image-ai-result').hidden=true;
  if(form.dataset.aiChecking)return;
  const issue=job.analysis.issues[Number(form.dataset.index)],usage=job.ai_checks?.[issue.block_id];
  const exhausted=usage?.remaining===0 && normalizeAIText(event.target.value)===normalizeAIText(usage.description);
  const button=form.querySelector('[data-ai-check]');button.disabled=exhausted;button.textContent=exhausted?'Descrição já aprovada':'Verificar com IA';
});
