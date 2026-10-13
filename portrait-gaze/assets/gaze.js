/* Portrait Gaze: paired eye movement in source-image coordinates. No network. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PortraitGaze = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function offset(eyes, point) {
    if (!point) return {x: 0, y: 0};
    const [a,b] = eyes, dx=b.center[0]-a.center[0], dy=b.center[1]-a.center[1];
    const span=Math.hypot(dx,dy);
    if (!(span>0)) return {x:0,y:0};
    const ux=dx/span, uy=dy/span;
    const px=point.x-(a.center[0]+b.center[0])/2, py=point.y-(a.center[1]+b.center[1])/2;
    const distance=Math.hypot(px,py), gain=Math.min(1,Math.max(0,(distance-span*.15)/(span*.8)));
    let x=(px*ux+py*uy)/(span*1.2), y=(-px*uy+py*ux)/(span*1.8);
    const length=Math.max(1,Math.hypot(x,y));
    x=x/length*Math.min(a.max_offset[0],b.max_offset[0])*gain;
    y=y/length*Math.min(a.max_offset[1],b.max_offset[1])*gain;
    return {x:x*ux-y*uy,y:x*uy+y*ux};
  }
  function mount(svg, data) {
    const doc=svg.ownerDocument, win=doc.defaultView;
    const irises=Array.from(svg.querySelectorAll('[data-iris]'));
    if(irises.length!==2 || data.eyes.length!==2) throw new Error('Exactly two eyes are required.');
    const reduced=win.matchMedia('(prefers-reduced-motion: reduce)');
    const manual=svg.closest('[data-gaze-demo]')?.querySelector('[data-toggle-motion]');
    let target=null, current={x:0,y:0}, raf=0, last=0, disposed=false, paused=false, touch=null;
    function paint(){ irises.forEach((el,i)=>el.setAttribute('transform',`translate(${data.eyes[i].center[0]+current.x} ${data.eyes[i].center[1]+current.y})`)); }
    function goal(){
      if(!target || paused || reduced.matches) return {x:0,y:0};
      const m=svg.getScreenCTM(); if(!m) return {x:0,y:0};
      const p=new win.DOMPoint(target.x,target.y).matrixTransform(m.inverse());
      return offset(data.eyes,p);
    }
    function step(now){
      raf=0;if(disposed)return;const g=goal();const dt=Math.min(64,last?now-last:16);last=now;
      const alpha=1-Math.exp(-dt/65);current.x+=(g.x-current.x)*alpha;current.y+=(g.y-current.y)*alpha;
      if(Math.hypot(g.x-current.x,g.y-current.y)<.01){current=g;paint();last=0;}else{paint();raf=win.requestAnimationFrame(step);}
    }
    function wake(){if(!disposed&&!raf)raf=win.requestAnimationFrame(step);}
    function move(e){if(e.pointerType==='touch' && e.pointerId!==touch)return;if(e.pointerType==='touch')e.preventDefault();target={x:e.clientX,y:e.clientY};wake();}
    function down(e){if(e.pointerType!=='touch')return;touch=e.pointerId;svg.setPointerCapture(touch);move(e);}
    function up(e){if(e.pointerId===touch){touch=null;target=null;wake();}}
    function leave(){target=null;wake();}
    function motionChange(){current={x:0,y:0};paint();wake();}
    function toggle(){paused=!paused;manual.setAttribute('aria-pressed',String(paused));manual.textContent=paused?'继续跟随 / Resume':'暂停跟随 / Pause';wake();}
    win.addEventListener('pointermove',move,{passive:false});svg.addEventListener('pointerdown',down);
    win.addEventListener('pointerup',up);win.addEventListener('pointercancel',up);win.addEventListener('blur',leave);
    doc.documentElement.addEventListener('pointerleave',leave);win.addEventListener('resize',wake);win.addEventListener('scroll',wake,{passive:true});
    reduced.addEventListener('change',motionChange);manual?.addEventListener('click',toggle);paint();
    return {destroy(){disposed=true;if(raf)win.cancelAnimationFrame(raf);win.removeEventListener('pointermove',move);svg.removeEventListener('pointerdown',down);win.removeEventListener('pointerup',up);win.removeEventListener('pointercancel',up);win.removeEventListener('blur',leave);doc.documentElement.removeEventListener('pointerleave',leave);win.removeEventListener('resize',wake);win.removeEventListener('scroll',wake);reduced.removeEventListener('change',motionChange);manual?.removeEventListener('click',toggle);current={x:0,y:0};paint();}};
  }
  return {offset,mount};
});
