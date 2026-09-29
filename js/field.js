(function () {
  const canvas = document.getElementById('field-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mobile = window.matchMedia('(max-width: 620px)').matches;
  const animate = !reduced && !mobile;
  let width = 0; let height = 0; let frame = 0; let active = true; let tick = 0;
  let scrollFrame = 0;
  const particles = Array.from({ length: 30 }, (_, i) => ({ x: (i * 73 % 100) / 100, y: (i * 47 % 100) / 100, speed: .00013 + (i % 5) * .000035, phase: i * 2.1 }));

  function resize() {
    const rect = canvas.getBoundingClientRect();
    width = rect.width; height = rect.height;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }
  function updateScroll() {
    if (scrollFrame) return;
    scrollFrame = requestAnimationFrame(() => {
      scrollFrame = 0;
      const progress = Math.min(1, Math.max(0, window.scrollY / Math.max(1, height) * .72));
      canvas.parentElement.style.setProperty('--hero-opacity', String(1 - progress * .5));
      const content = canvas.parentElement.querySelector('.hero-content');
      if (content) content.style.setProperty('--hero-shift', `${-progress * 24}px`);
    });
  }
  function draw() {
    if (!width || !height) return;
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, height * .2, width, height);
    gradient.addColorStop(0, 'rgba(9,23,22,0)'); gradient.addColorStop(.54, 'rgba(23,52,38,.48)'); gradient.addColorStop(1, 'rgba(29,63,39,.3)');
    ctx.fillStyle = gradient;
    ctx.beginPath(); ctx.moveTo(width * .52, height * .19); ctx.lineTo(width * 1.02, height * .19); ctx.lineTo(width * 1.16, height * 1.04); ctx.lineTo(width * .29, height * 1.04); ctx.closePath(); ctx.fill();
    const top = height * .2; const bottom = height * 1.02; const midTop = width * .77; const midBottom = width * .73;
    ctx.save(); ctx.strokeStyle = 'rgba(180,229,152,.18)'; ctx.lineWidth = 1;
    for (let n = 0; n <= 10; n++) {
      const p = n / 10; const y = top + (bottom - top) * p;
      const x1 = width * (.52 - .23 * p); const x2 = width * (1.02 + .14 * p);
      ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
      if (n % 2 === 0 && n > 0 && n < 10) {
        ctx.fillStyle = `rgba(228,244,211,${.12 + p * .12})`;
        ctx.font = `${Math.max(8, 8 + 7 * p)}px DM Mono, monospace`;
        ctx.fillText(String(n * 5), x1 + 15 * p, y - 4 * p); ctx.fillText(String(100 - n * 5), x2 - 32 * p, y - 4 * p);
      }
    }
    for (let n = -4; n <= 4; n++) {
      const p = (n + 4) / 8; const x1 = width * (.52 + p * .5); const x2 = width * (.29 + p * .87);
      ctx.beginPath(); ctx.moveTo(x1, top); ctx.lineTo(x2, bottom); ctx.stroke();
    }
    // Broadcast-style hash marks; intentionally understated behind the story copy.
    for (let row = 0; row < 7; row++) {
      const p = .27 + row * .095; const y = top + (bottom - top) * p; const scale = .35 + p;
      for (let n = 0; n < 18; n++) {
        const u = .18 + n * .038; const x = width * (.52 + u * (.4 + .19 * p));
        ctx.beginPath(); ctx.moveTo(x, y - 3 * scale); ctx.lineTo(x, y + 3 * scale); ctx.stroke();
      }
    }
    ctx.restore();
    if (animate) {
      for (const dot of particles) {
        const x = width * (.48 + dot.x * .7); const y = height * (.24 + ((dot.y + tick * dot.speed) % 1) * .72);
        const alpha = .17 + .18 * (Math.sin(tick * .002 + dot.phase) + 1) / 2;
        ctx.beginPath(); ctx.fillStyle = `rgba(205,255,112,${alpha})`; ctx.arc(x, y, 1 + (dot.phase % 2), 0, Math.PI * 2); ctx.fill();
      }
    }
    tick += 16;
    if (active && animate) frame = requestAnimationFrame(draw);
  }
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      active = entries[0].isIntersecting;
      if (active && animate && !frame) frame = requestAnimationFrame(draw);
      if (!active && frame) { cancelAnimationFrame(frame); frame = 0; }
    }, { threshold: 0 });
    observer.observe(canvas);
  }
  window.addEventListener('resize', resize, { passive: true });
  if (!reduced && !mobile) window.addEventListener('scroll', updateScroll, { passive: true });
  resize();
  if (!reduced && !mobile) updateScroll();
  if (animate && !('IntersectionObserver' in window)) frame = requestAnimationFrame(draw);
})();
