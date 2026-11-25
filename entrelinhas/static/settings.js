'use strict';
(() => {
  $('motion-button').after($('settings-button'));
  const root=document.documentElement;
  const savedScale=Number(localStorage.getItem('entrelinhas-interface-scale') || 100);
  let scale=Number.isFinite(savedScale)?Math.min(150,Math.max(80,savedScale)):100;
  let contrast=localStorage.getItem('entrelinhas-high-contrast')==='on';
  function applyAppearance(){root.style.zoom=String(scale/100);root.style.setProperty('--ui-scale',String(scale/100));root.classList.toggle('high-contrast',contrast);}
  applyAppearance();
  const modal=document.createElement('dialog');modal.id='accessibility-settings';modal.className='accessibility-settings';modal.setAttribute('aria-labelledby','settings-title');
  modal.innerHTML=`<div class="settings-heading"><div><span class="settings-eyebrow">Do seu jeito</span><h2 id="settings-title">Acessibilidade</h2></div><button type="button" class="icon-button" data-settings-close aria-label="Fechar configurações">×</button></div>
    <section class="settings-option" id="settings-animation-option"><label class="settings-toggle"><span><strong>Animações</strong><small>Movimentos e efeitos da interface</small></span><input type="checkbox" id="settings-motion"></label>
      <div class="settings-motion-preview"><div><span>Com animação</span><div class="motion-sample"><i class="sample-moving">✓</i></div></div><div><span>Sem animação</span><div class="motion-sample"><i>✓</i></div></div></div>
      <p class="settings-system-motion" hidden>Seu dispositivo está configurado para reduzir movimentos.</p></section>
    <section class="settings-option" id="settings-sound-option"><label class="settings-toggle"><span><strong>Som</strong><small>Som de sucesso ao concluir um ajuste</small></span><input type="checkbox" id="settings-sound"></label><button type="button" class="text-button settings-sound-test">Ouvir prévia</button></section>
    <section class="settings-option"><div class="settings-size"><label for="settings-size-value"><strong>Tamanho da interface</strong></label><div><button type="button" class="secondary" data-size="-10" aria-label="Diminuir interface">A−</button><output id="settings-size-value" aria-live="polite"></output><button type="button" class="secondary" data-size="10" aria-label="Aumentar interface">A+</button></div></div><button type="button" class="text-button" data-size-reset>Voltar a 100%</button></section>
    <section class="settings-option"><label class="settings-toggle"><span><strong>Alto contraste</strong><small>Cores mais marcantes nos controles e textos</small></span><input type="checkbox" id="settings-contrast"></label></section>`;
  document.body.append(modal);
  const motion=modal.querySelector('#settings-motion'),sound=modal.querySelector('#settings-sound'),highContrast=modal.querySelector('#settings-contrast');
  const soundOption=modal.querySelector('#settings-sound-option');
  let soundTimer=0,soundHovered=false,previousOverflow='';
  function sync(){
    motion.checked=!motionPaused && !motionPreference.matches;sound.checked=reviewSoundEnabled;highContrast.checked=contrast;
    motion.disabled=motionPreference.matches;modal.querySelector('.settings-system-motion').hidden=!motionPreference.matches;
    modal.querySelector('#settings-size-value').value=scale+'%';
    modal.querySelector('[data-size="-10"]').disabled=scale<=80;modal.querySelector('[data-size="10"]').disabled=scale>=150;
    modal.querySelector('.settings-sound-test').disabled=!reviewSoundEnabled;
  }
  function stopSound(){clearInterval(soundTimer);soundTimer=0;}
  function startSound(){
    stopSound();if(!modal.open || !reviewSoundEnabled || document.hidden)return;
    prepareReviewSound(true);
    const play=()=>{if(!modal.open || !reviewSoundEnabled || document.hidden){stopSound();return;}playReviewSound();};
    if(reviewAudio?.state==='suspended')reviewAudio.resume().then(()=>{if(modal.open && soundHovered)play();}).catch(()=>{});else play();
    soundTimer=setInterval(play,3000);
  }
  let motionAnimation=null;
  function stopMotion(){motionAnimation?.cancel();motionAnimation=null;}
  function startMotion(){
    stopMotion();if(!modal.open || document.hidden || motionPreference.matches)return;
    motionAnimation=modal.querySelector('.sample-moving').animate([{transform:'translateY(0) rotate(-4deg)'},{transform:'translateY(-14px) rotate(4deg)'},{transform:'translateY(0) rotate(-4deg)'}],{duration:1600,iterations:Infinity,easing:'ease-in-out'});
  }
  $('settings-button').addEventListener('click',()=>{
    if(modal.open)return;sync();previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';modal.showModal();startMotion();prepareReviewSound(true);
  });
  modal.querySelector('[data-settings-close]').addEventListener('click',()=>modal.close());
  modal.addEventListener('click',event=>{if(event.target!==modal)return;const box=modal.getBoundingClientRect();if(event.clientX<box.left || event.clientX>box.right || event.clientY<box.top || event.clientY>box.bottom)modal.close();});
  modal.addEventListener('close',()=>{stopSound();stopMotion();soundHovered=false;document.body.style.overflow=previousOverflow;$('settings-button').focus({preventScroll:true});});
  motion.addEventListener('change',()=>{motionPaused=!motion.checked;localStorage.setItem('entrelinhas-motion',motionPaused?'paused':'enabled');updateMotion();sync();});
  sound.addEventListener('change',()=>{reviewSoundEnabled=sound.checked;localStorage.setItem('entrelinhas-success-sound',reviewSoundEnabled?'on':'off');sync();if(reviewSoundEnabled && soundHovered)startSound();else stopSound();});
  highContrast.addEventListener('change',()=>{contrast=highContrast.checked;localStorage.setItem('entrelinhas-high-contrast',contrast?'on':'off');applyAppearance();});
  modal.querySelectorAll('[data-size]').forEach(button=>button.addEventListener('click',()=>{scale=Math.min(150,Math.max(80,scale+Number(button.dataset.size)));localStorage.setItem('entrelinhas-interface-scale',String(scale));applyAppearance();sync();}));
  modal.querySelector('[data-size-reset]').addEventListener('click',()=>{scale=100;localStorage.setItem('entrelinhas-interface-scale','100');applyAppearance();sync();});
  soundOption.addEventListener('pointerenter',()=>{soundHovered=true;startSound();});soundOption.addEventListener('pointerleave',()=>{soundHovered=false;stopSound();});
  soundOption.addEventListener('focusout',event=>{if(!soundOption.contains(event.relatedTarget))stopSound();});
  modal.querySelector('.settings-sound-test').addEventListener('click',()=>{soundHovered=true;startSound();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){stopSound();stopMotion();}else if(modal.open)startMotion();});
  motionPreference.addEventListener('change',()=>{sync();startMotion();});
})();
