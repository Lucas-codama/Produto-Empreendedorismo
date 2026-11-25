"""Bounded inspection of tagged PDF structure, not a PDF/UA certificate."""
from pypdf.generic import ArrayObject


def inspect(reader):
    root=reader.trailer['/Root'];tree=root.get('/StructTreeRoot')
    result={'tagged':bool(tree),'findings':[],'figures':{},'reading_order':[],'headings':[],'elements':0}
    def issue(rule,title,evidence,page=None,path=None):result['findings'].append({'rule':rule,'title':title,'evidence':evidence,'page':page,'path':list(path) if path else None})
    if not tree:return result
    tree=tree.get_object();roles=tree.get('/RoleMap',{});roles=roles.get_object() if hasattr(roles,'get_object') else roles
    visited=set();last_heading=None
    page_ids={p.indirect_reference.idnum:i for i,p in enumerate(reader.pages) if p.indirect_reference}
    def content_refs(node,page,seen=None,depth=0):
        seen=set() if seen is None else seen
        if depth>80:return []
        node=node.get_object() if hasattr(node,'get_object') else node
        if isinstance(node,int):return [{'page':page,'mcid':int(node)}] if page is not None else []
        if isinstance(node,list):return [ref for child in node for ref in content_refs(child,page,seen,depth+1)]
        if not isinstance(node,dict) or id(node) in seen:return []
        seen.add(id(node));page=page_ids.get(getattr(node.get('/Pg'),'idnum',None),page)
        # MCIDs inside a Form XObject have their own namespace; do not guess a page match.
        if node.get('/Stm') is not None:return []
        if node.get('/Type')=='/MCR':return content_refs(node.get('/MCID'),page,seen,depth+1)
        return content_refs(node.get('/K'),page,seen,depth+1)
    def walk(node,path=(),page=None,depth=0):
        nonlocal last_heading
        if depth>80 or result['elements']>=20000:
            issue('pdf_structure_limit','Estrutura excede o limite de inspeção','Mais de 80 níveis ou 20.000 elementos.');return
        node=node.get_object() if hasattr(node,'get_object') else node
        if isinstance(node,(ArrayObject,list)):
            for i,child in enumerate(node):walk(child,path+(i,),page,depth+1)
            return
        if not isinstance(node,dict):return
        if id(node) in visited:
            issue('pdf_structure_cycle','Referência repetida na árvore de estrutura','A árvore não pôde ser percorrida de forma única.');return
        visited.add(id(node))
        ref=node.get('/Pg');page=page_ids.get(getattr(ref,'idnum',None),page)
        if node.get('/Type')=='/MCR':
            if page is not None:result['reading_order'].append({'page':page,'mcid':int(node.get('/MCID',-1))})
            return
        role=str(node.get('/S',''));role=str(roles.get(role,role))
        if role:
            result['elements']+=1
            if role.startswith('/H') and role[2:].isdigit():
                level=int(role[2:])
                heading={'level':level,'refs':content_refs(node,page),'text':str(node.get('/ActualText') or node.get('/T') or '').strip()}
                result['headings'].append(heading)
                previous_level=last_heading['level'] if last_heading else 0
                if level>previous_level+1:
                    issue('pdf_heading_skip','Hierarquia de títulos com salto',f'Título H{level} após H{previous_level}.' if last_heading else f'Primeiro título identificado: H{level}.',page,path)
                    result['findings'][-1].update(heading=heading,previous_heading=last_heading,suggested_level=min(previous_level+1,6))
                last_heading=heading
            if role=='/Figure':
                alt=str(node.get('/Alt','')).strip();children=node.get('/K')
                ids=[children] if isinstance(children,int) else children if isinstance(children,list) else [children]
                for child in ids:
                    child=child.get_object() if hasattr(child,'get_object') else child
                    mcid=child if isinstance(child,int) else child.get('/MCID') if isinstance(child,dict) else None
                    if mcid is not None and page is not None:result['figures'][(page,int(mcid))]={'alt':alt,'path':list(path),'caption':str(node.get('/EntrelinhasCaption',''))}
                if not alt:issue('pdf_figure_alt','Figura do PDF sem descrição alternativa','Tag Figure sem entrada /Alt.',page,path)
            if role=='/Table':
                def has_header(n,seen=None):
                    seen=set() if seen is None else seen;n=n.get_object() if hasattr(n,'get_object') else n
                    if isinstance(n,list):return any(has_header(c,seen) for c in n)
                    if not isinstance(n,dict) or id(n) in seen:return False
                    seen.add(id(n))
                    return str(n.get('/S'))=='/TH' or has_header(n.get('/K'),seen)
                if not has_header(node):issue('pdf_table_headers','Tabela do PDF sem cabeçalho identificado','Tag Table sem descendente TH.',page,path)
        children=node.get('/K')
        if isinstance(children,int):
            if page is not None:result['reading_order'].append({'page':page,'mcid':int(children),'role':role})
            else:issue('pdf_tag_orphan','Conteúdo marcado sem página identificada',f'Tag {role or "sem tipo"} com MCID {children}.')
        elif children is not None:walk(children,path+('K',),page,depth+1)
    walk(tree.get('/K'),('K',))
    if not result['elements']:issue('pdf_tags_empty','Árvore de tags vazia ou sem elementos utilizáveis','Existe StructTreeRoot, mas nenhum elemento de estrutura foi encontrado.')
    if not str(root.get('/Lang','')).strip():issue('pdf_language_missing','Idioma do PDF não informado','Entrada /Lang ausente no catálogo.')
    return result
