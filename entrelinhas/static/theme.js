'use strict';
(() => {
  const preference=window.matchMedia('(prefers-color-scheme: dark)');
  let choice=null;
  try{choice=localStorage.getItem('entrelinhas-theme');}catch(_){}
  const apply=(theme)=>{
    document.documentElement.dataset.theme=theme;
    const button=document.getElementById('theme-button');
    if(button){const dark=theme==='dark';button.setAttribute('aria-pressed',String(dark));button.setAttribute('aria-label',dark?'Ativar modo claro':'Ativar modo escuro');button.title=button.getAttribute('aria-label');}
  };
  const current=()=>choice==='dark' || choice==='light'?choice:preference.matches?'dark':'light';
  apply(current());
  document.addEventListener('DOMContentLoaded',()=>{
    apply(current());
    document.getElementById('theme-button').addEventListener('click',()=>{
      choice=document.documentElement.dataset.theme==='dark'?'light':'dark';
      try{localStorage.setItem('entrelinhas-theme',choice);}catch(_){}
      apply(choice);
    });
  });
  preference.addEventListener('change',()=>{if(choice!=='dark' && choice!=='light')apply(current());});
  window.addEventListener('storage',event=>{if(event.key==='entrelinhas-theme'){choice=event.newValue;apply(current());}});
})();
