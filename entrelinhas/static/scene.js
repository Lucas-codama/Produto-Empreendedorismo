import * as THREE from './assets/three.module.js';

// Decorative only: the upload and analysis work independently of WebGL.
const host = document.getElementById('hero-art');
const canvas = document.getElementById('document-scene');
const paused = () => document.body.classList.contains('motion-paused');
try {
  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.8));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, .1, 100);
  camera.position.set(0, .4, 9.5);
  camera.lookAt(0, 0, 0);
  scene.add(new THREE.AmbientLight(0xffffff, 2.1));
  const sun = new THREE.DirectionalLight(0xfff5e5, 4.2);
  sun.position.set(-4, 6, 8); sun.castShadow = true;
  sun.shadow.mapSize.set(1024,1024);
  sun.shadow.camera.left = -6; sun.shadow.camera.right = 6;
  sun.shadow.camera.top = 6; sun.shadow.camera.bottom = -6;
  sun.shadow.normalBias = .04;
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xb7a7ff, 2.1);
  fill.position.set(4,-1,3); scene.add(fill);

  function rounded(w,h,r) {
    const s = new THREE.Shape(), x=-w/2, y=-h/2;
    s.moveTo(x+r,y);s.lineTo(x+w-r,y);s.quadraticCurveTo(x+w,y,x+w,y+r);
    s.lineTo(x+w,y+h-r);s.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    s.lineTo(x+r,y+h);s.quadraticCurveTo(x,y+h,x,y+h-r);
    s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);return s;
  }
  function texture(kind) {
    const c=document.createElement('canvas');c.width=768;c.height=1024;
    const g=c.getContext('2d');
    g.fillStyle=kind==='front'?'#fff9ef':kind==='middle'?'#ad94e4':'#eb835f';g.fillRect(0,0,768,1024);
    if(kind==='front') {
      g.fillStyle='#5739b8';g.font='500 188px Fredoka';g.fillText('Aa',74,268);
      g.fillStyle='#d1bfed';
      for(const [y,w] of [[338,565],[392,450],[446,525]]){g.beginPath();g.roundRect(78,y,w,19,10);g.fill();}
      g.fillStyle='#f3dfcf';g.beginPath();g.roundRect(78,528,608,384,38);g.fill();
      g.fillStyle='#ec7852';g.save();g.translate(382,720);
      for(let i=0;i<8;i++){g.rotate(Math.PI/4);g.beginPath();g.roundRect(-27,-150,54,154,27);g.fill();}g.restore();
      g.fillStyle='#5739b8';g.beginPath();g.arc(382,720,43,0,Math.PI*2);g.fill();
    } else {
      g.fillStyle=kind==='middle'?'#7253ba':'#d05c38';
      g.font='500 98px Fredoka';g.fillText(kind==='middle'?'Slides':'PDF',70,160);
      for(let i=0;i<5;i++){g.beginPath();g.roundRect(72,240+i*75,520-i%2*100,24,12);g.fill();}
    }
    const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=renderer.capabilities.getMaxAnisotropy();return t;
  }
  await document.fonts.ready;
  const stack = new THREE.Group();scene.add(stack);
  const cards=[];
  for(const [kind,color,z,angle,x,y] of [['back',0xe7835d,-.46,.23,.3,.04],['middle',0xa98cdf,-.19,.08,.1,.08],['front',0xfff8ee,.12,-.17,-.14,.1]]) {
    const card=new THREE.Group();
    const geo=new THREE.ExtrudeGeometry(rounded(2.9,3.86,.23),{depth:.075,bevelEnabled:true,bevelSegments:4,steps:1,bevelSize:.035,bevelThickness:.03,curveSegments:24});
    const body=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,roughness:.43,metalness:.03}));body.castShadow=true;body.receiveShadow=true;card.add(body);
    // Front face uses UVs independent of the extruded edge and retains rounded corners.
    const frontGeo=new THREE.ShapeGeometry(rounded(2.9,3.86,.23),24);
    const uv=frontGeo.attributes.uv, pos=frontGeo.attributes.position;
    for(let i=0;i<uv.count;i++)uv.setXY(i,(pos.getX(i)+1.45)/2.9,(pos.getY(i)+1.93)/3.86);
    const face=new THREE.Mesh(frontGeo,new THREE.MeshStandardMaterial({map:texture(kind),roughness:.68}));
    face.position.z=.108;card.add(face);
    card.position.set(x,y,z);card.rotation.z=angle;stack.add(card);cards.push(card);
  }
  stack.rotation.set(.14,-.35,0);
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(20,20),new THREE.ShadowMaterial({opacity:.14}));
  floor.rotation.x=-Math.PI/2;floor.position.y=-2.7;floor.receiveShadow=true;scene.add(floor);
  const bead=new THREE.Mesh(new THREE.SphereGeometry(.19,32,24),new THREE.MeshStandardMaterial({color:0xe77f58,metalness:.28,roughness:.28}));
  bead.position.set(-2,1.6,.25);bead.castShadow=true;scene.add(bead);
  const ring=new THREE.Mesh(new THREE.TorusGeometry(.33,.09,16,56),new THREE.MeshStandardMaterial({color:0x8061cc,roughness:.32,metalness:.15}));
  ring.position.set(1.85,-1.56,.7);ring.rotation.set(.45,-.55,-.5);scene.add(ring);
  let pointerX=0,pointerY=0,frame=0,visible=false,time=0,last=0,portalActive=false;
  function resize(){if(portalActive)return;const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();draw();}
  function draw(){renderer.render(scene,camera);}
  function animate(now){frame=0;if(!visible||paused()||document.hidden)return;time+=Math.min((now-(last||now))/1000,.05);last=now;
    stack.rotation.y+=(-.35+pointerX*.28+Math.sin(time*.43)*.06-stack.rotation.y)*.05;
    stack.rotation.x+=(.14-pointerY*.16-stack.rotation.x)*.05;
    stack.position.y=Math.sin(time*.85)*.085;
    cards[0].position.x=.3+Math.sin(time*.6)*.045;
    ring.rotation.z=time*.2-.5;ring.position.y=-1.56+Math.sin(time*.85+2)*.1;
    bead.position.y=1.6+Math.sin(time*.9)*.12;draw();frame=requestAnimationFrame(animate);
  }
  function sync(){if(portalActive)return;if(frame){cancelAnimationFrame(frame);frame=0;}last=0;if(visible&&!paused()&&!document.hidden && host.clientWidth)frame=requestAnimationFrame(animate);else draw();}
  async function travelPaper({direction,origin,getOrigin,covered}) {
    const overlay=document.getElementById('page-transition'),stage=document.getElementById('portal-stage'),veil=document.getElementById('portal-veil');
    const saved={camera:camera.position.clone(),rotation:stack.rotation.clone(),position:stack.position.clone()};
    const home=canvas.parentElement;
    const mix=(a,b,p)=>a+(b-a)*p;
    const ease=p=>p<.5?4*p*p*p:1-Math.pow(-2*p+2,3)/2;
    let travelFrame=0;
    portalActive=true;if(frame){cancelAnimationFrame(frame);frame=0;}
    overlay.hidden=false;overlay.dataset.direction=direction;stage.classList.add('webgl-portal');
    veil.style.opacity=direction==='out'?'1':'0';stage.append(canvas);
    // Keep the drawing buffer stable while the canvas travels; only its CSS box
    // and camera projection change, avoiding a GPU allocation on every frame.
    let viewportW=innerWidth,viewportH=innerHeight;renderer.setSize(viewportW,viewportH,false);
    const renderPortal=p=>{
      const w=mix(origin.w,innerWidth,p),h=mix(origin.h,innerHeight,p);
      stage.style.left=mix(origin.x,0,p)+'px';stage.style.top=mix(origin.y,0,p)+'px';stage.style.width=w+'px';stage.style.height=h+'px';
      if(viewportW!==innerWidth || viewportH!==innerHeight){viewportW=innerWidth;viewportH=innerHeight;renderer.setSize(viewportW,viewportH,false);}
      camera.aspect=w/h;camera.updateProjectionMatrix();
      camera.position.set(mix(saved.camera.x,-.14,p),mix(saved.camera.y,.1,p),mix(saved.camera.z,1.45,p));camera.lookAt(mix(0,-.14,p),mix(0,.1,p),mix(0,.22,p));
      stack.rotation.set(mix(saved.rotation.x,0,p),mix(saved.rotation.y,0,p),mix(saved.rotation.z,0,p));stack.position.set(0,mix(saved.position.y,0,p),0);
      cards[2].rotation.z=mix(-.17,0,p);
      veil.style.opacity=String(Math.max(0,Math.min(1,(p-.62)/.38)));draw();
    };
    try {
      if(direction==='out'){await covered();origin=getOrigin();}
      renderPortal(direction==='in'?0:1);
      await new Promise((resolve,reject)=>{
        let start;
        const tick=now=>{
          try {
            start??=now;const progress=paused() || document.hidden?1:Math.min((now-start)/880,1);
            renderPortal(direction==='in'?ease(progress):1-ease(progress));
            if(progress<1)travelFrame=requestAnimationFrame(tick);else resolve();
          } catch(error) { reject(error); }
        };travelFrame=requestAnimationFrame(tick);
      });
      if(direction==='in')await covered();
      // On exit, p=0 already matches the home canvas. Reparent it in this same
      // frame instead of holding the endpoint for another fade animation.
      if(direction==='in' && !paused() && !document.hidden)await overlay.animate([{opacity:1},{opacity:0}],{duration:160,fill:'forwards'}).finished;
    } finally {
      cancelAnimationFrame(travelFrame);overlay.getAnimations().forEach(a=>a.cancel());
      home.append(canvas);camera.position.copy(saved.camera);camera.lookAt(0,0,0);stack.rotation.copy(saved.rotation);stack.position.copy(saved.position);cards[2].rotation.z=-.17;
      stage.classList.remove('webgl-portal');stage.removeAttribute('style');veil.removeAttribute('style');overlay.hidden=true;
      portalActive=false;resize();sync();
    }
  }
  document.addEventListener('entrelinhas-portal',event=>{if(!portalActive && host.classList.contains('ready'))event.detail.promise=travelPaper(event.detail);});
  host.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse'||paused())return;const r=host.getBoundingClientRect();pointerX=(e.clientX-r.left)/r.width*2-1;pointerY=(e.clientY-r.top)/r.height*2-1;});
  host.addEventListener('pointerleave',()=>{pointerX=0;pointerY=0;});
  new ResizeObserver(resize).observe(host);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();}).observe(host);
  document.addEventListener('entrelinhas-motion',sync);
  document.addEventListener('visibilitychange',sync);
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();if(frame)cancelAnimationFrame(frame);host.classList.remove('ready');});
  resize();host.classList.add('ready');sync();
} catch(error) {
  // The CSS paper sculpture remains visible when WebGL is unavailable.
  host.classList.remove('ready');
}
