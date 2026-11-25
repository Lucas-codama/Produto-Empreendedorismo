'use strict';
let reviewAudio=null,stopReviewCelebration=()=>{};
let reviewSoundEnabled=localStorage.getItem('entrelinhas-success-sound')!=='off';
function prepareReviewSound(preview=false){
  if(!reviewSoundEnabled || (!preview && (motionPaused || motionPreference.matches)))return;
  try{const Audio=window.AudioContext || window.webkitAudioContext;if(!Audio)return;reviewAudio ||= new Audio();reviewAudio.resume().catch(()=>{});}catch(_){}
}
function playReviewSound(){
  if(!reviewSoundEnabled || document.hidden || reviewAudio?.state!=='running')return;
  try{
    const now=reviewAudio.currentTime;
    [523.25,659.25,783.99].forEach((frequency,index)=>{
      const tone=reviewAudio.createOscillator(),volume=reviewAudio.createGain(),start=now+index*.065;
      tone.type='sine';tone.frequency.value=frequency;volume.gain.setValueAtTime(0,start);
      volume.gain.linearRampToValueAtTime(.035,start+.015);volume.gain.exponentialRampToValueAtTime(.001,start+.24);
      tone.connect(volume);volume.connect(reviewAudio.destination);tone.start(start);tone.stop(start+.25);
      tone.onended=()=>{tone.disconnect();volume.disconnect();};
    });
  }catch(_){}
}
function celebrateReview(text='Ajuste salvo!'){
  stopReviewCelebration();
  const layer=document.createElement('div');layer.className='review-celebration';layer.setAttribute('aria-hidden','true');
  const toast=document.createElement('div');toast.className='review-success-toast';toast.textContent='✓ '+text;layer.append(toast);document.body.append(layer);
  const animations=[];let timer;
  const cleanup=()=>{clearTimeout(timer);animations.forEach(a=>a.cancel());layer.remove();document.removeEventListener('visibilitychange',cancel);document.removeEventListener('entrelinhas-motion',cancel);motionPreference.removeEventListener('change',cancel);};
  const cancel=()=>{if(document.hidden || motionPaused || motionPreference.matches)cleanup();};
  stopReviewCelebration=cleanup;
  document.addEventListener('visibilitychange',cancel);document.addEventListener('entrelinhas-motion',cancel);motionPreference.addEventListener('change',cancel);
  if(!motionPaused && !motionPreference.matches && !document.hidden){
    playReviewSound();
    animations.push(toast.animate([{opacity:0,transform:'translateY(14px) scale(.94)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:240,easing:'cubic-bezier(.2,.8,.2,1)'}));
    const colors=['#bb97f1','#f2bf6b','#a9d6bb','#ef947f','#8051ca'];
    const fragment=document.createDocumentFragment();
    for(let n=0;n<30;n++){
      const piece=document.createElement('i');piece.className='review-confetti';piece.style.background=colors[n%colors.length];piece.style.left='50%';piece.style.top='70%';fragment.append(piece);
    }
    layer.append(fragment);
    layer.querySelectorAll('i').forEach((piece,n)=>{
      const angle=Math.PI+(n/29)*Math.PI,reach=100+Math.random()*190,dx=Math.cos(angle)*reach,dy=Math.sin(angle)*reach;
      animations.push(piece.animate([{opacity:1,transform:'translate(0,0) rotate(0deg)'},{offset:.65,opacity:1,transform:`translate(${dx}px,${dy}px) rotate(${n*37}deg)`},{opacity:0,transform:`translate(${dx*1.15}px,${dy+110}px) rotate(${n*53}deg)`}],{duration:850+Math.random()*350,easing:'cubic-bezier(.15,.55,.35,1)',fill:'both'}));
    });
  }
  timer=setTimeout(cleanup,2200);
}
