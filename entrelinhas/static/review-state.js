'use strict';
const ReviewRules=(()=>{
  function category(issue){
    const rule=issue.rule || '';
    if(rule.includes('contrast'))return 'contrast';
    if(rule.startsWith('alt_') || rule.includes('figure_alt') || rule.startsWith('image_'))return 'images';
    if(rule.startsWith('font'))return 'font';
    return 'structure';
  }
  function matches(issue,filters,reviewed){
    return (filters.category==='all' || category(issue)===filters.category) &&
      (filters.status==='all' || filters.status==='pending' && !reviewed.has(issue.id) || filters.status==='reviewed' && reviewed.has(issue.id) || filters.status==='human' && issue.severity==='review');
  }
  function indexes(issues,filters,reviewed){return issues.map((issue,index)=>matches(issue,filters,reviewed)?index:-1).filter(index=>index>=0);}
  function restore(analysis,saved){
    const filters={category:['all','contrast','images','font','structure'].includes(saved?.filters?.category)?saved.filters.category:'all',status:['all','pending','reviewed','human'].includes(saved?.filters?.status)?saved.filters.status:'all'};
    const reviewed=new Set((Array.isArray(saved?.reviewed)?saved.reviewed:[]).filter(id=>analysis.issues.some(i=>i.id===id)));
    const visible=indexes(analysis.issues,filters,reviewed);
    let selected=saved && Object.hasOwn(saved,'issue_id')?(saved.issue_id?analysis.issues.findIndex(i=>i.id===saved.issue_id):-1):analysis.issues.length?0:-1;
    let page=Math.max(0,Math.min(Number.isInteger(saved?.page)?saved.page:analysis.issues[selected]?.page ?? 0,analysis.pages.length-1));
    if(saved?.issue_id && selected<0)selected=visible.find(index=>analysis.issues[index].page===page) ?? visible.find(index=>analysis.issues[index].page===null) ?? -1;
    if(selected>=0 && !visible.includes(selected)){selected=visible[0] ?? -1;if(analysis.issues[selected]?.page!==null && analysis.issues[selected]?.page!==undefined)page=analysis.issues[selected].page;}
    if(selected>=0 && analysis.issues[selected].page!==null && analysis.issues[selected].page!==page)selected=visible.find(index=>analysis.issues[index].page===page) ?? -1;
    return {mode:saved?.mode==='step'?'step':'side',page,selected,reviewed,filters};
  }
  return {category,matches,indexes,restore};
})();
