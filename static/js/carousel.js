(function(){
  function setup(root){
    const slides=Array.from(root.querySelectorAll('.hero-slide, .detail-slide'));
    if(!slides.length)return;
    let index=Math.max(0,slides.findIndex(s=>s.classList.contains('active')));
    const dots=root.querySelector('.carousel-dots');
    function show(i){index=(i+slides.length)%slides.length;slides.forEach((s,n)=>s.classList.toggle('active',n===index));if(dots){dots.querySelectorAll('button').forEach((b,n)=>{b.classList.toggle('active',n===index);b.setAttribute('aria-current',n===index?'true':'false')})}}
    if(dots){dots.innerHTML='';slides.forEach((_,i)=>{const b=document.createElement('button');b.type='button';b.setAttribute('aria-label','Show image '+(i+1));b.addEventListener('click',()=>{show(i);restart()});dots.appendChild(b)})}
    const prev=root.querySelector('.carousel-arrow.prev'),next=root.querySelector('.carousel-arrow.next');
    if(prev)prev.addEventListener('click',()=>{show(index-1);restart()});if(next)next.addEventListener('click',()=>{show(index+1);restart()});
    let timer=null;function restart(){if(timer)clearInterval(timer);if(slides.length>1)timer=setInterval(()=>show(index+1),5000)}
    show(index);restart();root.addEventListener('mouseenter',()=>timer&&clearInterval(timer));root.addEventListener('mouseleave',restart);
  }
  document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('[data-carousel]').forEach(setup));
})();
