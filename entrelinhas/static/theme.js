'use strict';
(() => {
  const preference=window.matchMedia('(prefers-color-scheme: dark)');
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  let changing=false,finishTransition=null;
  let choice=null;
  try{choice=localStorage.getItem('entrelinhas-theme');}catch(_){}
  const apply=(theme)=>{
    document.documentElement.dataset.theme=theme;
    const button=document.getElementById('theme-button');
    if(button){const dark=theme==='dark';button.setAttribute('aria-pressed',String(dark));button.setAttribute('aria-label',dark?'Ativar modo claro':'Ativar modo escuro');button.title=button.getAttribute('aria-label');}
  };
  const current=()=>choice==='dark' || choice==='light'?choice:preference.matches?'dark':'light';
  apply(current());
  const motionAllowed=()=>!reduced.matches && !document.hidden && !document.body.classList.contains('motion-paused');
  function contour(x,y,r,progress){
    const points=[],count=64,envelope=Math.sin(Math.PI*progress);
    const lobe=(angle,center,width)=>{
      const distance=Math.atan2(Math.sin(angle-center),Math.cos(angle-center));
      return Math.exp(-distance*distance/width);
    };
    const edge=angle=>1+envelope*(
      .09*Math.sin(angle*3-.4-progress*.7)+.055*Math.cos(angle*5+.8)
      +.24*lobe(angle,Math.PI*.57,.025)
      +.20*lobe(angle,Math.PI*.79,.035)
      +.17*lobe(angle,Math.PI*.97,.025)
    );
    for(let i=0;i<count;i++){
      const angle=i/count*Math.PI*2;
      const radius=r*edge(angle);
      points.push([x+Math.cos(angle)*radius,y+Math.sin(angle)*radius]);
    }
    let path=`M ${points[0][0].toFixed(2)} ${points[0][1].toFixed(2)}`;
    for(let i=0;i<count;i++){
      const a=points[(i+count-1)%count],b=points[i],c=points[(i+1)%count],d=points[(i+2)%count];
      const coordinates=[b[0]+(c[0]-a[0])/6,b[1]+(c[1]-a[1])/6,c[0]-(d[0]-b[0])/6,c[1]-(d[1]-b[1])/6,c[0],c[1]];
      path+=' C '+coordinates.map(v=>v.toFixed(2)).join(' ');
    }
    path+=' Z';
    // Separate drops are swallowed by the expanding front. Keep the same
    // commands in every frame so native path interpolation stays continuous.
    const splash=Math.sin(Math.PI*Math.min(progress/.68,1));
    for(const [angle,size,gap] of [[.48,16,30],[.67,11,45],[.88,19,36],[1.04,9,42]]){
      const a=angle*Math.PI,d=r*edge(a)+gap*splash,rx=size*splash,ry=rx*.8;
      const cx=x+Math.cos(a)*d,cy=y+Math.sin(a)*d,k=.55228475;
      const n=value=>value.toFixed(2);
      path+=` M ${n(cx+rx)} ${n(cy)}`;
      path+=` C ${n(cx+rx)} ${n(cy+k*ry)} ${n(cx+k*rx)} ${n(cy+ry)} ${n(cx)} ${n(cy+ry)}`;
      path+=` C ${n(cx-k*rx)} ${n(cy+ry)} ${n(cx-rx)} ${n(cy+k*ry)} ${n(cx-rx)} ${n(cy)}`;
      path+=` C ${n(cx-rx)} ${n(cy-k*ry)} ${n(cx-k*rx)} ${n(cy-ry)} ${n(cx)} ${n(cy-ry)}`;
      path+=` C ${n(cx+k*rx)} ${n(cy-ry)} ${n(cx+rx)} ${n(cy-k*ry)} ${n(cx+rx)} ${n(cy)} Z`;
    }
    return path;
  }
  async function liquidChange(theme,button){
    if(changing)return;
    const rect=button.getBoundingClientRect(),x=rect.x+rect.width/2,y=rect.y+rect.height/2;
    const radius=Math.hypot(Math.max(x,innerWidth-x),Math.max(y,innerHeight-y))+70;
    document.documentElement.style.setProperty('--theme-origin-x',x+'px');
    document.documentElement.style.setProperty('--theme-origin-y',y+'px');
    changing=true;document.body.classList.add('theme-changing');button.setAttribute('aria-busy','true');
    document.dispatchEvent(new CustomEvent('entrelinhas-theme-motion'));
    let transition,animation,layer,frame=0;
    try{
      if(typeof document.startViewTransition==='function' && CSS.supports('clip-path',"path('M 0 0 L 1 1 Z')")){
        transition=document.startViewTransition(()=>apply(current()));
        // Release snapshots before releasing the clip animation. Otherwise a
        // cancelled mask can expose the old snapshot for a compositor frame.
        finishTransition=()=>{apply(current());transition.skipTransition();};
        await transition.ready;
        const frames=Array.from({length:61},(_,index)=>{
          const p=index/60,r=3+(radius-3)*Math.pow(p,.88);
          return {offset:p,clipPath:`path('${contour(x,y,r,p)}')`};
        });
        animation=document.documentElement.animate(frames,{duration:1300,easing:'cubic-bezier(.4,0,.18,1)',fill:'both',pseudoElement:'::view-transition-new(root)'});
        await animation.finished;
        // Keep the fully revealed snapshot held until the live page takes
        // over, instead of relying on automatic snapshot teardown timing.
        transition.skipTransition();
        await transition.finished;
      }else{
        // A painted wave is used when snapshot transitions are unavailable.
        layer=document.createElement('canvas');layer.className='theme-fluid-canvas';layer.setAttribute('aria-hidden','true');
        const scale=Math.min(devicePixelRatio,1.5);layer.width=innerWidth*scale;layer.height=innerHeight*scale;document.body.append(layer);
        const ctx=layer.getContext('2d');ctx.scale(scale,scale);
        finishTransition=()=>{cancelAnimationFrame(frame);apply(current());layer.remove();};
        await new Promise(resolve=>{
          let start;
          const paint=now=>{
            start??=now;const p=motionAllowed()?Math.min((now-start)/900,1):1;
            const eased=1-Math.pow(1-p,3),r=3+(radius-3)*eased;
            ctx.clearRect(0,0,innerWidth,innerHeight);ctx.fillStyle=theme==='dark'?'#19151f':'#f7f3ed';ctx.fill(new Path2D(contour(x,y,r,p)));
            if(p<1)frame=requestAnimationFrame(paint);else resolve();
          };
          frame=requestAnimationFrame(paint);
          // Cancelling must settle this promise as well as stop its frames.
          finishTransition=()=>{cancelAnimationFrame(frame);apply(current());layer.remove();resolve();};
        });
        apply(current());
        if(layer.isConnected && motionAllowed())await layer.animate([{opacity:1},{opacity:0}],{duration:200,fill:'forwards'}).finished;
      }
    }catch(_){transition?.skipTransition();apply(current());}
    finally{
      cancelAnimationFrame(frame);layer?.remove();layer?.getAnimations().forEach(a=>a.cancel());animation?.cancel();
      document.documentElement.style.removeProperty('--theme-origin-x');document.documentElement.style.removeProperty('--theme-origin-y');
      finishTransition=null;changing=false;document.body.classList.remove('theme-changing');button.removeAttribute('aria-busy');
      document.dispatchEvent(new CustomEvent('entrelinhas-theme-motion'));
    }
  }
  document.addEventListener('DOMContentLoaded',()=>{
    apply(current());
    document.getElementById('theme-button').addEventListener('click',event=>{
      if(changing)return;
      choice=document.documentElement.dataset.theme==='dark'?'light':'dark';
      try{localStorage.setItem('entrelinhas-theme',choice);}catch(_){}
      if(motionAllowed())liquidChange(choice,event.currentTarget);else apply(choice);
    });
  });
  document.addEventListener('entrelinhas-motion',()=>{if(!motionAllowed())finishTransition?.();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)finishTransition?.();});
  reduced.addEventListener('change',()=>{if(reduced.matches)finishTransition?.();});
  window.addEventListener('resize',()=>finishTransition?.());
  document.addEventListener('click',event=>{if(changing && !event.target.closest('#theme-button'))finishTransition?.();},true);
  document.addEventListener('wheel',()=>finishTransition?.(),{passive:true});
  document.addEventListener('touchmove',()=>finishTransition?.(),{passive:true});
  preference.addEventListener('change',()=>{if(choice!=='dark' && choice!=='light')apply(current());});
  window.addEventListener('storage',event=>{if(event.key==='entrelinhas-theme'){choice=event.newValue;finishTransition?.();apply(current());}});
})();
