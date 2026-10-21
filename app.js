document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  if (menu && nav) {
    menu.addEventListener('click', () => nav.classList.toggle('open'));
    nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => nav.classList.remove('open')));
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  document.querySelectorAll('[data-count]').forEach(el => {
    const target = Number(el.dataset.count || 0);
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 18));
    const tick = () => {
      current = Math.min(target, current + step);
      el.textContent = String(current).padStart(2, '0');
      if (current < target) requestAnimationFrame(tick);
    };
    tick();
  });

  const hero = document.querySelector('.hero-frame');
  if (hero && window.matchMedia('(pointer:fine)').matches) {
    hero.addEventListener('mousemove', e => {
      const r = hero.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - .5;
      const y = (e.clientY - r.top) / r.height - .5;
      hero.style.transform = `perspective(1000px) rotateY(${x * 5}deg) rotateX(${y * -4}deg)`;
    });
    hero.addEventListener('mouseleave', () => hero.style.transform = 'perspective(1000px) rotateY(-4deg)');
  }

  document.querySelectorAll('.toast').forEach(t => setTimeout(() => t.remove(), 6000));
});
