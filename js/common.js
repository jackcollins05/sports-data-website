(function () {
  const nf = new Intl.NumberFormat('en-US');
  window.Saturday = {
    number: (value, digits = 0) => Number.isFinite(Number(value)) ? new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(value)) : '—',
    compact: (value) => nf.format(Number(value) || 0),
    signed: (value, digits = 3) => Number.isFinite(Number(value)) ? `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(digits)}` : '—',
    percent: (value, digits = 1) => Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(digits)}%` : '—',
    esc: (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]),
    initials: (name) => String(name || 'CF').replace(/[^a-zA-Z0-9 ]/g, '').split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'CF'
  };
})();
