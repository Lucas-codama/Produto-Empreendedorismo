from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'static/workspace.js'
s=p.read_text(encoding='utf-8')
start=s.index('function mascots()');end=s.index('function accountDialog()',start)
s=s[:start]+(root/'tmp/auth_redesign.js.txt').read_text(encoding='utf-8')+'\n'+s[end:]
s=s.replace("if(!$('dialog').open){$('dialog').classList.remove('auth-dialog');", "if(!$('dialog').open){stopMascotTracking();$('dialog').classList.remove('auth-dialog');")
s=s.replace("button.setAttribute('aria-label',show?'Ocultar senha':'Mostrar senha');mascotGaze();", "button.setAttribute('aria-label',show?'Ocultar senha':'Mostrar senha');button.title=show?'Ocultar senha':'Mostrar senha';mascotGaze();")
p.write_text(s,encoding='utf-8')
p=root/'static/workspace.css';s=p.read_text(encoding='utf-8')
start=s.index('.mascot-stage{');end=s.index('[data-theme=dark] .review-filters',start)
s=s[:start]+(root/'tmp/mascots_redesign.css.txt').read_text(encoding='utf-8')+'\n'+s[end:]
s=s.replace('.auth-intro{font-size:12px!important;line-height:1.5!important;margin-bottom:20px}','')
s=s.replace('.password-help{font-size:11px!important;margin-top:-8px}', '.auth-fields .password-label{margin-bottom:0}.password-help{font-size:11px!important;line-height:1.5!important;margin:9px 0 12px;color:var(--muted)}.password-toggle .password-eye-off{display:none}.password-toggle[aria-pressed=true] .password-eye{display:none}.password-toggle[aria-pressed=true] .password-eye-off{display:block}')
s=s.replace('.auth-fields #auth-guest', '.auth-footer{grid-column:1 / -1;padding-top:15px;border-top:1px solid var(--line);color:var(--muted)}.auth-footer p{font-size:11px!important;line-height:1.6!important;margin:0}.auth-footer p+p{margin-top:5px}.auth-fields #auth-guest')
s=s.replace('.mascot-stage{height:290px}.pill-1{left:0}.pill-3{right:0}', '.mascot-stage{height:290px}.mascot-group{transform:scale(.88)}')
start=s.index('.mascot-stage{height:195px');end=s.index('.auth-fields{width:100%}',start)
s=s[:start]+'.mascot-stage{height:180px;width:260px;align-self:center}.mascot-orbit{inset:4px 10px 6px}.mascot-group{transform:scale(.67);transform-origin:50% 92%;bottom:-8px}.mascot-ground{bottom:4px;width:170px;left:calc(50% - 78px);height:17px}.mascot-star{top:1px;right:16px;font-size:28px}.mascot-spark{bottom:25px;left:21px;font-size:20px}.auth-footer{margin-top:20px;width:100%}'+s[end:]
p.write_text(s,encoding='utf-8')
p=root/'README.md';s=p.read_text(encoding='utf-8').replace('senha de 12 a 128','senha de 8 a 128').replace('Os três personagens cobrem os olhos e espiam quando a senha é exibida;', 'Os três personagens acompanham o ponteiro e cobrem os olhos quando a senha é exibida; só o personagem da frente espreita por entre os dedos;')
p.write_text(s,encoding='utf-8')
