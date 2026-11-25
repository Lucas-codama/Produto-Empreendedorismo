'use strict';
async function showReviewRecord(identity){
  const record=await api('/api/job/'+identity+'/review');
  if(record.status!=='completed')throw new Error('Esta revisão ainda está em andamento.');
  const valueText=(change)=>{
    const value=change.value;
    if(value && typeof value==='object')return Object.entries(value).map(([key,text])=>({alt:'Descrição: '+text,caption:'Legenda: '+text,scale:'Tamanho: '+Math.round(Number(text)*100)+'%'}[key] || '')).filter(Boolean).join('\n');
    return value==null?'':String(value)+(change.action==='font'?' pt':'');
  };
  const methods={manual:'Conferido e concluído pelo professor',edited:'Ajustado pelo editor do site',not_found:'Não reapareceu na nova análise'};
  dialog('Revisão concluída',`<div class="review-record"><p><strong>${esc(record.filename)}</strong> · Versão ${record.version}</p><p>Concluída em ${new Date(record.completed_at).toLocaleString('pt-BR')}. Este registro é somente para consulta.</p><a class="primary review-download" href="/api/job/${identity}/file">Baixar nova versão</a><h3>Ajustes realizados</h3>${record.changes.length?record.changes.map(change=>`<details><summary>${esc(change.title)} · v${change.version}</summary><p>${esc(change.location)}</p>${change.before?`<p><strong>Antes</strong><br>${esc(change.before)}</p>`:''}${valueText(change)?`<p class="review-record-value"><strong>Depois</strong><br>${esc(valueText(change))}</p>`:''}</details>`).join(''):'<p>Nenhum ajuste foi aplicado pelo editor nesta revisão.</p>'}<h3>Pontos tratados</h3>${record.findings.length?record.findings.map(item=>`<details><summary>✓ ${esc(item.title)}</summary><p>${esc(item.location)} · ${esc(methods[item.method] || 'Concluído')}</p>${item.text?`<p>“${esc(item.text)}”</p>`:''}<p>${esc(item.explanation)}</p></details>`).join(''):'<p>A análise não apontou pendências nesta versão.</p>'}</div>`);
}
