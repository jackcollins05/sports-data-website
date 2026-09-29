(function () {
  const path = 'data/report_findings.json';
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function valueFor(point, metric) { return Number(point[metric]) || 0; }
  function metricText(value, metric) {
    return metric.includes('rate') ? Saturday.percent(value) : Saturday.signed(value, 3);
  }
  function buildBars(chart) {
    const figure = el('figure', 'finding-visual');
    figure.setAttribute('aria-label', `${chart.unit} comparison chart`);
    const heading = el('div', 'viz-header');
    heading.append(el('span', '', chart.metric === 'success_rate' ? 'EPA SUCCESS SHARE' : chart.metric.includes('def_epa') ? 'DEFENSIVE EPA / ACTUAL PLAY' : chart.metric.includes('rate') ? 'PLAY RATE' : 'AVERAGE EPA / ACTUAL PLAY'));
    heading.append(el('span', 'viz-unit', chart.unit)); figure.append(heading);
    const values = chart.data.map((d) => valueFor(d, chart.metric));
    let min = Math.min(0, ...values); let max = Math.max(0, ...values);
    if (min === max) { min -= 1; max += 1; }
    const range = max - min; const zero = (-min / range) * 100;
    const rows = el('div', 'viz-bars');
    for (const [index, item] of chart.data.entries()) {
      const v = valueFor(item, chart.metric);
      const row = el('div', 'viz-row');
      row.append(el('span', 'viz-label', item.label));
      const track = el('span', 'viz-track'); track.style.setProperty('--zero', `${zero}%`);
      const bar = el('i', 'viz-bar');
      const left = v < 0 ? ((v - min) / range) * 100 : zero;
      const width = Math.max(1, Math.abs(v / range) * 100);
      bar.style.setProperty('--left', `${left}%`); bar.style.setProperty('--width', `${width}%`);
      bar.style.setProperty('--bar-i', index);
      bar.style.setProperty('--bar-color', v < 0 ? 'var(--blue)' : 'var(--accent)');
      track.append(bar); row.append(track); row.append(el('span', 'viz-value', metricText(v, chart.metric)));
      const count = el('span', 'viz-count', `${Saturday.compact(item.n)} plays`); row.append(count);
      rows.append(row);
    }
    figure.append(rows);
    const axis = el('div', 'viz-axis'); axis.append(el('span', '', metricText(min, chart.metric))); axis.append(el('span', '', metricText(max, chart.metric))); figure.append(axis);
    return figure;
  }
  function buildSignalMap(chart) {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    const data = chart.data.filter((point) => Number.isFinite(point.mean_epa) && Number.isFinite(point.explosive_rate));
    const W = 760; const H = 440; const m = { top: 46, right: 30, bottom: 60, left: 74 };
    const xMin = Math.min(0, ...data.map((p) => p.mean_epa)); const xMax = Math.max(...data.map((p) => p.mean_epa));
    const yMin = 0; const yMax = Math.max(...data.map((p) => p.explosive_rate)) * 1.16;
    const x = (value) => m.left + ((value - xMin) / (xMax - xMin || 1)) * (W - m.left - m.right);
    const y = (value) => H - m.bottom - ((value - yMin) / (yMax - yMin || 1)) * (H - m.top - m.bottom);
    const meanX = data.reduce((sum, point) => sum + point.mean_epa, 0) / data.length;
    const meanY = data.reduce((sum, point) => sum + point.explosive_rate, 0) / data.length;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('role', 'group');
    svg.setAttribute('aria-label', 'Efficiency and EPA explosive-play rate for the ten highest EPA teams with at least 300 actual plays. Focus or hover a marker for team values.');
    const node = (tag, attrs, text) => {
      const item = document.createElementNS(NS, tag);
      Object.entries(attrs || {}).forEach(([key, value]) => item.setAttribute(key, value));
      if (text !== undefined) item.textContent = text;
      svg.append(item); return item;
    };
    const x0 = m.left; const x1 = W - m.right; const y0 = m.top; const y1 = H - m.bottom;
    node('rect', { x: x0, y: y0, width: x1 - x0, height: y1 - y0, class: 'signal-plot' });
    for (let i = 0; i <= 4; i++) {
      const value = xMin + (xMax - xMin) * i / 4; const px = x(value);
      node('line', { x1: px, y1: y0, x2: px, y2: y1, class: 'signal-gridline' });
      node('text', { x: px, y: y1 + 23, class: 'signal-tick', 'text-anchor': 'middle' }, value.toFixed(2));
      const rate = yMax * i / 4; const py = y(rate);
      node('line', { x1: x0, y1: py, x2: x1, y2: py, class: 'signal-gridline' });
      node('text', { x: x0 - 12, y: py + 4, class: 'signal-tick', 'text-anchor': 'end' }, `${(rate * 100).toFixed(1)}%`);
    }
    node('line', { x1: x(meanX), y1: y0, x2: x(meanX), y2: y1, class: 'signal-midline' });
    node('line', { x1: x0, y1: y(meanY), x2: x1, y2: y(meanY), class: 'signal-midline' });
    node('text', { x: (x0 + x1) / 2, y: H - 12, class: 'signal-axis-title', 'text-anchor': 'middle' }, 'AVERAGE EPA / ACTUAL PLAY');
    const yTitle = node('text', { x: 19, y: (y0 + y1) / 2, class: 'signal-axis-title', 'text-anchor': 'middle', transform: `rotate(-90 19 ${(y0 + y1) / 2})` }, 'EPA-EXPLOSIVE RATE');
    yTitle.setAttribute('aria-hidden', 'true');
    node('text', { x: x0 + 10, y: y0 + 17, class: 'signal-quadrant' }, 'HIGHER RATE / LOWER EPA');
    node('text', { x: x1 - 10, y: y0 + 17, class: 'signal-quadrant', 'text-anchor': 'end' }, 'HIGHER ON BOTH');
    node('text', { x: x0 + 10, y: y1 - 10, class: 'signal-quadrant' }, 'LOWER ON BOTH');
    node('text', { x: x1 - 10, y: y1 - 10, class: 'signal-quadrant', 'text-anchor': 'end' }, 'HIGHER EPA / LOWER RATE');
    data.forEach((point, index) => {
      const group = document.createElementNS(NS, 'g');
      group.setAttribute('class', point.mean_epa === Math.max(...data.map((item) => item.mean_epa)) ? 'signal-point signal-point-lead' : 'signal-point');
      group.setAttribute('tabindex', '0'); group.setAttribute('role', 'img');
      group.setAttribute('aria-label', `${point.label}: average EPA ${Saturday.signed(point.mean_epa, 3)}, EPA explosive rate ${Saturday.percent(point.explosive_rate)}, success rate ${Saturday.percent(point.success_rate)}, ${Saturday.compact(point.n)} actual plays`);
      const title = document.createElementNS(NS, 'title'); title.textContent = `${point.label} • EPA ${Saturday.signed(point.mean_epa, 3)} • explosive ${Saturday.percent(point.explosive_rate)} • success ${Saturday.percent(point.success_rate)} • ${Saturday.compact(point.n)} plays`; group.append(title);
      const halo = document.createElementNS(NS, 'circle'); halo.setAttribute('cx', x(point.mean_epa)); halo.setAttribute('cy', y(point.explosive_rate)); halo.setAttribute('r', index === 0 ? 13 : 11); halo.setAttribute('class', 'signal-halo'); group.append(halo);
      const dot = document.createElementNS(NS, 'circle'); dot.setAttribute('cx', x(point.mean_epa)); dot.setAttribute('cy', y(point.explosive_rate)); dot.setAttribute('r', index === 0 ? 6 : 5); dot.setAttribute('class', 'signal-dot'); group.append(dot);
      svg.append(group);
    });
    const figure = el('figure', 'finding-visual signal-figure');
    const heading = el('div', 'viz-header'); heading.append(el('span', '', 'THE SIGNAL MAP / 300+ PLAY COHORT')); heading.append(el('span', 'viz-unit', 'EPA × EPA-EXPLOSIVE RATE'));
    figure.append(heading, svg);
    const note = el('figcaption', 'signal-caption', `Each point is a team from the 10 highest qualifying offensive EPA averages. Crosshairs mark the cohort means: ${Saturday.signed(meanX, 3)} EPA and ${Saturday.percent(meanY)} explosive rate. Focus a point with the keyboard for its exact values.`);
    figure.append(note); return figure;
  }
  function stat(label, value, foot) {
    const card = el('div', 'stat-card'); card.append(el('strong', 'stat-value', value)); card.append(el('span', 'stat-label', label));
    const count = Number(String(value).replace(/,/g, ''));
    if (Number.isFinite(count)) card.querySelector('.stat-value').dataset.count = String(count);
    if (foot) card.append(el('span', 'stat-foot', foot)); return card;
  }
  function render(data) {
    const meta = data.meta; const overall = meta.overall;
    const idx = Object.fromEntries(data.sections.map((item) => [item.id, item]));
    const rush = idx['pass-rush'].chart.data.find((item) => item.label === 'Rush-coded');
    const pass = idx['pass-rush'].chart.data.find((item) => item.label === 'Pass-coded');
    document.getElementById('report-summary').textContent =
      `This season’s ${Saturday.compact(meta.rows)} play records contain ${Saturday.compact(meta.actual_play_rows)} actual plays, ${Saturday.compact(meta.unique_teams)} teams and ${meta.weeks.length} weeks. Across actual plays, average EPA was ${Saturday.signed(overall.mean_epa)} and ${Saturday.percent(overall.success_rate)} had positive EPA. One clear split: the selected pass-coded labels averaged ${Saturday.signed(pass.mean_epa)} EPA per play, compared with ${Saturday.signed(rush.mean_epa)} for rush-coded plays; just ${Saturday.percent(overall.explosive_rate)} carried the source’s EPA-explosive flag.`;
    const setText = (id, value) => { const node = document.getElementById(id); if (node) node.textContent = value; };
    setText('method-row-count', Saturday.compact(meta.rows) + ' rows');
    setText('method-game-count', Saturday.compact(meta.unique_games) + ' games');
    setText('method-team-count', Saturday.compact(meta.unique_teams));
    setText('method-week-range', `${Math.min(...meta.weeks)}–${Math.max(...meta.weeks)}`);
    setText('method-date-range', `${meta.date_min} to ${meta.date_max}`);
    setText('method-column-count', `${meta.columns} selected dashboard columns`);
    setText('method-admin-count', Saturday.compact(meta.administrative_rows));
    setText('method-actual-count', `${Saturday.compact(meta.actual_play_rows)} actual plays`);
    setText('method-type-missing', Saturday.compact(meta.definitions.missing_values.orig_play_type || 0));
    setText('method-clock-missing', Saturday.compact(meta.definitions.missing_values.wallclock || 0));
    const stats = document.getElementById('headline-stats'); stats.replaceChildren(
      stat('PLAY-BY-PLAY RECORDS', Saturday.compact(meta.rows)),
      stat('ACTUAL PLAYS', Saturday.compact(meta.actual_play_rows)),
      stat('TEAMS IN POSSESSION FIELDS', Saturday.compact(meta.unique_teams)),
      stat('WEEKS IN THE FILE', String(meta.weeks.length))
    );
    const index = document.getElementById('story-index-links');
    const findings = document.getElementById('findings'); index.replaceChildren(); findings.replaceChildren();
    data.sections.forEach((finding, i) => {
      const link = el('a', 'index-link'); link.href = `#finding-${finding.id}`;
      link.append(el('b', '', String(i + 1).padStart(2, '0'))); link.append(el('span', '', finding.title)); index.append(link);
      const section = el('article', 'finding'); section.id = `finding-${finding.id}`;
      section.dataset.reveal = '';
      section.dataset.index = String(i + 1).padStart(2, '0');
      section.classList.add(i % 3 === 1 ? 'finding--wide' : i % 3 === 2 ? 'finding--stat' : 'finding--standard');
      const copy = el('div', 'finding-copy'); copy.dataset.index = section.dataset.index; const kicker = el('div', 'finding-kicker'); kicker.append(el('span', '', finding.kicker)); kicker.append(el('b', '', `FIELD NOTE ${String(i + 1).padStart(2, '0')}`));
      copy.append(kicker); copy.append(el('h2', '', finding.title)); copy.append(el('p', '', finding.copy));
      const mark = el('div', 'finding-mark', `${Saturday.compact(meta.actual_play_rows)} actual plays in the season view`); copy.append(mark);
      section.append(copy); section.append(finding.id === 'offense-teams' ? buildSignalMap(finding.chart) : buildBars(finding.chart)); findings.append(section);
    });
    installReveals();
  }
  function installReveals() {
    const targets = document.querySelectorAll('[data-reveal], .hero-scoreline strong[data-count], .stat-value[data-count]');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const reveal = (target) => {
      target.classList.add('is-visible');
      const counter = target.matches('[data-count]') ? target : target.querySelector('[data-count]');
      if (!counter) return;
      const end = Number(counter.dataset.count); if (!Number.isFinite(end)) return;
      if (reduced || end < 25) { counter.textContent = end.toLocaleString('en-US'); return; }
      const start = performance.now(); const duration = 850;
      function tick(now) {
        const t = Math.min(1, (now - start) / duration); const eased = 1 - Math.pow(1 - t, 3);
        counter.textContent = Math.round(end * eased).toLocaleString('en-US');
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    };
    if (!('IntersectionObserver' in window) || reduced) { targets.forEach(reveal); return; }
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      reveal(entry.target); observer.unobserve(entry.target);
    }), { threshold: .12, rootMargin: '0px 0px -5% 0px' });
    targets.forEach((target) => observer.observe(target));
  }
  fetch(path).then((response) => { if (!response.ok) throw new Error(`Could not load ${path}`); return response.json(); })
    .then(render).catch((error) => { document.getElementById('findings').textContent = `The report findings could not be loaded: ${error.message}`; });
})();
