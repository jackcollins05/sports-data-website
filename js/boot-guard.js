(() => {
  let ready = false;
  let failed = false;
  const dashboard = () => document.body?.classList.contains('dashboard-page');
  const show = (message) => {
    if (failed) return;
    failed = true;
    const detail = `The page could not finish loading: ${message}. Check that the local HTTP server is running, then reload.`;
    if (dashboard()) {
      const error = document.getElementById('dashboard-error');
      if (error) { error.hidden = false; error.textContent = detail; }
      const status = document.getElementById('load-status');
      if (status) { status.textContent = 'FBS Explorer failed to load'; status.dataset.state = 'error'; }
      const overlay = document.getElementById('loading-overlay');
      if (overlay) overlay.hidden = true;
      const main = document.getElementById('main');
      if (main) main.inert = false;
    } else {
      let error = document.getElementById('report-error');
      if (!error) {
        error = document.createElement('div');
        error.id = 'report-error';
        error.className = 'error-panel page-shell';
        error.setAttribute('role', 'alert');
        const findings = document.getElementById('findings');
        if (findings) findings.before(error);
        else document.body.append(error);
      }
      error.hidden = false;
      error.textContent = detail;
    }
  };
  window.GridironBoot = {
    ready() { ready = true; clearTimeout(watchdog); },
    fail: show
  };
  window.addEventListener('error', (event) => {
    if (event.target instanceof HTMLScriptElement) show(`required script failed (${event.target.src || 'inline script'})`);
    else if (!event.target?.tagName && event.message) show(event.message);
  }, true);
  window.addEventListener('unhandledrejection', (event) => {
    show(event.reason?.message || String(event.reason || 'an asynchronous initialization error occurred'));
  });
  const watchdog = setTimeout(() => {
    if (!ready) show('initialization took longer than 30 seconds, usually because a data or library request did not finish');
  }, 30000);
})();
