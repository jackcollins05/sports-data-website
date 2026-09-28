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
    for (const item of chart.data) {
      const v = valueFor(item, chart.metric);
      const row = el('div', 'viz-row');
      row.append(el('span', 'viz-label', item.label));
      const track = el('span', 'viz-track'); track.style.setProperty('--zero', `${zero}%`);
      const bar = el('i', 'viz-bar');
      const left = v < 0 ? ((v - min) / range) * 100 : zero;
      const width = Math.max(1, Math.abs(v / range) * 100);
      bar.style.setProperty('--left', `${left}%`); bar.style.setProperty('--width', `${width}%`);
      bar.style.setProperty('--bar-color', v < 0 ? 'var(--blue)' : 'var(--accent)');
      track.append(bar); row.append(track); row.append(el('span', 'viz-value', metricText(v, chart.metric)));
      const count = el('span', 'viz-count', `${Saturday.compact(item.n)} plays`); row.append(count);
      rows.append(row);
    }
    figure.append(rows);
    const axis = el('div', 'viz-axis'); axis.append(el('span', '', metricText(min, chart.metric))); axis.append(el('span', '', metricText(max, chart.metric))); figure.append(axis);
    return figure;
  }
  function stat(label, value, foot) {
    const card = el('div', 'stat-card'); card.append(el('strong', 'stat-value', value)); card.append(el('span', 'stat-label', label));
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
      const copy = el('div', 'finding-copy'); const kicker = el('div', 'finding-kicker'); kicker.append(el('span', '', finding.kicker)); kicker.append(el('b', '', `FIELD NOTE ${String(i + 1).padStart(2, '0')}`));
      copy.append(kicker); copy.append(el('h2', '', finding.title)); copy.append(el('p', '', finding.copy));
      const mark = el('div', 'finding-mark', `${Saturday.compact(meta.actual_play_rows)} actual plays in the season view`); copy.append(mark);
      section.append(copy); section.append(buildBars(finding.chart)); findings.append(section);
    });
  }
  fetch(path).then((response) => { if (!response.ok) throw new Error(`Could not load ${path}`); return response.json(); })
    .then(render).catch((error) => { document.getElementById('findings').textContent = `The report findings could not be loaded: ${error.message}`; });
})();
