(() => {
  const BRAND = 'GRIDIRON PULSE';
  const nf = new Intl.NumberFormat('en-US');
  window.GridironPulse = {
    brand: BRAND,
    number: (value, digits = 0) => Number.isFinite(Number(value)) ? new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(value)) : '—',
    compact: (value) => Number.isFinite(Number(value)) ? nf.format(Number(value)) : '—',
    signed: (value, digits = 1) => Number.isFinite(Number(value)) ? `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(digits)}` : '—',
    percent: (value, digits = 1) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(digits)}%` : '—',
    esc: (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]),
    initials: (name) => String(name || 'CF').replace(/[^a-zA-Z0-9 ]/g, '').split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'CF',
    color: (value, fallback = '#c7ff4a') => /^#[0-9a-f]{6}$/i.test(String(value || '')) ? value : fallback
  };
  document.querySelectorAll('[data-brand]').forEach((node) => { node.textContent = BRAND; });
  document.title = document.body.classList.contains('dashboard-page') ? `FBS Explorer — ${BRAND}` : `2025 Season Report — ${BRAND}`;
})();
