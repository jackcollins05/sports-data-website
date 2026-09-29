(function () {
  window.__SATURDAY_DASHBOARD_STARTED__ = true;
  const CSV_URL = 'data/cfb_pbp_2025_dashboard.csv';
  const BRAND_URL = 'data/team_branding.json';
  const EXPECTED_ROWS = 166053;
  const REQUIRED_HEADERS = ['season', 'seasonType', 'week', 'game_id', 'wallclock', 'homeTeamName', 'awayTeamName', 'pos_team', 'def_pos_team', 'period', 'clock.displayValue', 'down', 'distance', 'orig_play_type', 'play', 'statYardage', 'yds_rushed', 'yds_receiving', 'scoring_play', 'pos_score_pts', 'EPA', 'def_EPA', 'EPA_success', 'EPA_explosive'];
  const els = {
    status: document.getElementById('load-status'), team: document.getElementById('team-filter'), week: document.getElementById('week-filter'),
    type: document.getElementById('type-filter'), season: document.getElementById('season-filter'), perspective: document.getElementById('perspective-filter'),
    measure: document.getElementById('measure-filter'), breakdown: document.getElementById('breakdown-filter'), reset: document.getElementById('reset-filters'),
    context: document.getElementById('team-broadcast'), identityLogo: document.getElementById('team-identity-logo'), identityName: document.getElementById('team-identity-name'), identityKicker: document.getElementById('team-identity-kicker'), error: document.getElementById('dashboard-error'), sort: document.getElementById('table-sort'),
    prev: document.getElementById('table-prev'), next: document.getElementById('table-next'), range: document.getElementById('table-range'), tbody: document.querySelector('#results-table tbody')
  };
  els.loading = document.getElementById('loading-overlay'); els.loadCount = document.getElementById('load-count'); els.loadStage = document.getElementById('load-stage'); els.loadFill = document.getElementById('load-progress-fill');
  const PAGE_SIZE = 15;
  const build = { offense: [], defense: [], week: [], season: [], type: [], down: [], period: [], epa: [], defEPA: [], yards: [], success: [], explosive: [], scoring: [], points: [] };
  const lookup = { teams: [''], types: [''], seasons: [''] };
  const ids = { teams: new Map(), types: new Map(), seasons: new Map() };
  let rows = null; let branding = {}; let chartInstances = []; let resultRows = []; let page = 0; let debounce = 0; let chartColor = '#cbff50'; let lastIdentity = null;
  let settled = false; let loadWatchdog = 0; let loadStartedAt = Date.now();
  const measureLabels = { epa: 'Average EPA / actual play', success: 'EPA success rate', explosive: 'EPA explosive-play rate', yards: 'Average recorded yards', scoring: 'Scoring-play rate', plays: 'Actual play count' };
  const breakdownLabels = { team: 'Team', opponent: 'Opponent', week: 'Week', type: 'Play type', down: 'Down', quarter: 'Quarter / period' };

  function intern(value, key) {
    const text = String(value ?? '').trim() || (key === 'types' ? 'Unspecified' : '');
    const map = ids[key];
    if (map.has(text)) return map.get(text);
    const id = lookup[key].length; map.set(text, id); lookup[key].push(text); return id;
  }
  function numeric(value, fallback = 0) { const n = Number(value); return Number.isFinite(n) ? n : fallback; }
  function boolean(value) { return String(value).toLowerCase() === 'true'; }
  function pushRow(r) {
    const off = intern(r.pos_team, 'teams'); const def = intern(r.def_pos_team, 'teams');
    build.offense.push(off); build.defense.push(def); build.week.push(numeric(r.week)); build.season.push(numeric(r.seasonType));
    build.type.push(intern(r.orig_play_type, 'types')); build.down.push(numeric(r.down)); build.period.push(numeric(r.period));
    build.epa.push(numeric(r.EPA)); build.defEPA.push(numeric(r.def_EPA)); build.yards.push(numeric(r.statYardage));
    build.success.push(boolean(r.EPA_success) ? 1 : 0); build.explosive.push(boolean(r.EPA_explosive) ? 1 : 0);
    build.scoring.push(boolean(r.scoring_play) ? 1 : 0); build.points.push(numeric(r.pos_score_pts));
  }
  function finalize() {
    const typed = {};
    Object.entries(build).forEach(([key, value]) => { typed[key] = Float64Array.from(value); });
    rows = typed;
    Object.keys(build).forEach((key) => { build[key].length = 0; });
    ids.teams = new Map(lookup.teams.map((value, i) => [value, i]));
  }
  function addOptions(select, values, labelFn = (v) => v) {
    values.forEach((value) => {
      const option = document.createElement('option'); option.value = value; option.textContent = labelFn(value); select.append(option);
    });
  }
  function initializeFilters() {
    const teams = lookup.teams.slice(1).sort((a, b) => a.localeCompare(b));
    const weeks = [...new Set(Array.from(rows.week))].sort((a, b) => a - b).map(String);
    const types = lookup.types.slice(1).sort((a, b) => a.localeCompare(b));
    const seasons = [...new Set(Array.from(rows.season))].sort().map(String);
    addOptions(els.team, teams); addOptions(els.week, weeks, (w) => `Week ${w}`); addOptions(els.type, types);
    addOptions(els.season, seasons, (s) => ({ '2': 'Regular season', '3': 'Postseason' }[s] || `Season type ${s}`));
    ['change', 'input'].forEach((event) => [els.team, els.week, els.type, els.season, els.perspective, els.measure, els.breakdown].forEach((el) => el.addEventListener(event, scheduleRender)));
    els.perspective.addEventListener('change', syncMeasureLabels);
    els.sort.addEventListener('change', () => { page = 0; renderTable(resultRows); });
    els.prev.addEventListener('click', () => { page = Math.max(0, page - 1); renderTable(resultRows); });
    els.next.addEventListener('click', () => { page += 1; renderTable(resultRows); });
    els.reset.addEventListener('click', reset);
    chartInstances = ['chart-primary', 'chart-trend', 'chart-down', 'chart-type'].map((id) => echarts.init(document.getElementById(id), null, { renderer: 'canvas', useDirtyRect: true }));
    window.addEventListener('resize', () => chartInstances.forEach((chart) => chart.resize()), { passive: true });
    render();
  }
  function syncMeasureLabels() {
    const defensive = els.perspective.value === 'defense';
    Object.assign(measureLabels, defensive ? {
      epa: 'Average defensive EPA / actual play', success: 'Defensive stop rate', explosive: 'Non-explosive share allowed',
      yards: 'Average yards allowed', scoring: 'Opponent scoring-play rate', plays: 'Actual play count'
    } : {
      epa: 'Average offensive EPA / actual play', success: 'EPA success rate', explosive: 'EPA explosive-play rate',
      yards: 'Average recorded yards', scoring: 'Scoring-play rate', plays: 'Actual play count'
    });
    Array.from(els.measure.options).forEach((option) => { option.textContent = measureLabels[option.value]; });
  }
  function reset() {
    els.team.value = ''; els.week.value = ''; els.type.value = ''; els.season.value = '';
    els.perspective.value = 'offense'; els.measure.value = 'epa'; els.breakdown.value = 'team'; els.sort.value = 'metric'; page = 0; scheduleRender();
  }
  function scheduleRender() {
    window.clearTimeout(debounce);
    document.getElementById('summary-cards').classList.add('filter-pending');
    debounce = window.setTimeout(() => { page = 0; render(); document.getElementById('summary-cards').classList.remove('filter-pending'); }, 85);
  }
  function chosenTeamId() { return els.team.value ? ids.teams.get(els.team.value) : null; }
  function selectedValue(key, value, perspective) {
    if (key === 'team') return lookup.teams[perspective === 'offense' ? rows.offense[value] : rows.defense[value]];
    if (key === 'opponent') return lookup.teams[perspective === 'offense' ? rows.defense[value] : rows.offense[value]];
    if (key === 'week') return `Week ${rows.week[value]}`;
    if (key === 'type') return lookup.types[rows.type[value]] || 'Unspecified';
    if (key === 'down') return rows.down[value] ? `${rows.down[value]}${rows.down[value] === 1 ? 'st' : rows.down[value] === 2 ? 'nd' : rows.down[value] === 3 ? 'rd' : 'th'} down` : 'Not recorded';
    if (key === 'quarter') return rows.period[value] < 5 ? `Period ${rows.period[value]}` : `Overtime ${rows.period[value] - 4}`;
    return 'All plays';
  }
  function computeViews(filters, primaryKey) {
    const buckets = { primary: new Map(), week: new Map(), down: new Map(), type: new Map() };
    const keys = { primary: primaryKey, week: 'week', down: 'down', type: 'type' };
    const total = { n: 0, epa: 0, defEpa: 0, yards: 0, success: 0, explosive: 0, scoring: 0, points: 0 };
    const n = rows.week.length; const perspective = els.perspective.value; const teamId = chosenTeamId();
    const weekVal = filters.week ? Number(filters.week) : null; const seasonVal = filters.season ? Number(filters.season) : null;
    const typeId = filters.type ? ids.types.get(filters.type) : null;
    for (let i = 0; i < n; i++) {
      if (teamId !== null && (perspective === 'offense' ? rows.offense[i] !== teamId : rows.defense[i] !== teamId)) continue;
      if (weekVal !== null && rows.week[i] !== weekVal) continue;
      if (seasonVal !== null && rows.season[i] !== seasonVal) continue;
      if (typeId !== null && rows.type[i] !== typeId) continue;
      const offenseSuccess = rows.success[i] === 1; const offenseExplosive = rows.explosive[i] === 1;
      const value = { epa: rows.epa[i], defEpa: rows.defEPA[i], yards: rows.yards[i],
        success: perspective === 'offense' ? Number(offenseSuccess) : Number(!offenseSuccess),
        explosive: perspective === 'offense' ? Number(offenseExplosive) : Number(!offenseExplosive),
        scoring: rows.scoring[i], points: rows.points[i] };
      total.n++; Object.keys(value).forEach((key) => { total[key] += value[key]; });
      for (const [bucketName, map] of Object.entries(buckets)) {
        const group = selectedValue(keys[bucketName], i, perspective);
        let g = map.get(group);
        if (!g) { g = { label: group, n: 0, epa: 0, defEpa: 0, yards: 0, success: 0, explosive: 0, scoring: 0, points: 0 }; map.set(group, g); }
        g.n++; Object.keys(value).forEach((key) => { g[key] += value[key]; });
      }
    }
    const finish = (map) => [...map.values()].map((g) => ({ ...g, meanEpa: g.epa / g.n, meanDefEpa: g.defEpa / g.n, meanYards: g.yards / g.n, successRate: g.success / g.n, explosiveRate: g.explosive / g.n, scoringRate: g.scoring / g.n }));
    return { primary: finish(buckets.primary), week: finish(buckets.week), down: finish(buckets.down), type: finish(buckets.type), total };
  }
  function currentMetric(group, measure = els.measure.value, perspective = els.perspective.value) {
    if (measure === 'plays') return group.n;
    if (measure === 'epa') return perspective === 'offense' ? group.meanEpa : group.meanDefEpa;
    if (measure === 'success') return group.successRate;
    if (measure === 'explosive') return group.explosiveRate;
    if (measure === 'yards') return group.meanYards;
    return group.scoringRate;
  }
  function formatMeasure(value, measure) {
    if (!Number.isFinite(value)) return '—';
    if (measure === 'success' || measure === 'explosive' || measure === 'scoring') return Saturday.percent(value);
    if (measure === 'epa') return Saturday.signed(value, 3);
    if (measure === 'yards') return Saturday.number(value, 2);
    return Saturday.compact(value);
  }
  function unitText(measure) {
    if (measure === 'epa') return els.perspective.value === 'offense' ? 'Offensive EPA / actual play' : 'Defensive EPA / actual play';
    return { success: 'Share of actual plays', explosive: 'Share of actual plays', yards: 'Yards / actual play', scoring: 'Share of actual plays', plays: 'Actual plays' }[measure];
  }
  function filtersNow() { return { team: els.team.value, week: els.week.value, type: els.type.value, season: els.season.value }; }
  function updateCards(all) {
    const p = els.perspective.value; const metricEPA = p === 'offense' ? all.epa : all.defEpa;
    const cards = document.querySelectorAll('.summary-card');
    const values = [Saturday.compact(all.n), all.n ? Saturday.signed(metricEPA / all.n, 3) : '—', all.n ? Saturday.percent(all.success / all.n) : '—', all.n ? Saturday.percent(all.explosive / all.n) : '—', all.n ? Saturday.percent(all.scoring / all.n) : '—'];
    const labels = ['Actual plays', p === 'offense' ? 'Average offensive EPA' : 'Average defensive EPA', p === 'offense' ? 'Offensive success' : 'Defensive stop rate', p === 'offense' ? 'Explosive-play rate' : 'Non-explosive share', p === 'offense' ? 'Scoring-play rate' : 'Opponent scoring rate'];
    const feet = ['Filtered actual-play count', 'Per actual play', p === 'offense' ? 'EPA > 0 share' : 'EPA ≤ 0 allowed share', p === 'offense' ? 'Source EPA explosive flag' : 'Source EPA explosive flag is false', 'Source scoring flag'];
    cards.forEach((card, i) => { card.querySelector('.summary-value').textContent = values[i]; card.querySelector('.summary-label').textContent = labels[i]; card.querySelector('.summary-foot').textContent = feet[i]; });
    document.getElementById('broadcast-epa-label').textContent = p === 'offense' ? 'OFFENSIVE EPA' : 'DEFENSIVE EPA';
    document.getElementById('broadcast-success-label').textContent = p === 'offense' ? 'SUCCESS RATE' : 'DEFENSIVE STOP RATE';
    document.getElementById('broadcast-explosive-label').textContent = p === 'offense' ? 'EXPLOSIVE RATE' : 'NON-EXPLOSIVE SHARE';
    document.getElementById('broadcast-yards-label').textContent = p === 'offense' ? 'AVERAGE YARDS' : 'AVERAGE YARDS ALLOWED';
    document.getElementById('broadcast-epa').textContent = all.n ? Saturday.signed(metricEPA / all.n, 3) : '—';
    document.getElementById('broadcast-success').textContent = all.n ? Saturday.percent(all.success / all.n) : '—';
    document.getElementById('broadcast-explosive').textContent = all.n ? Saturday.percent(all.explosive / all.n) : '—';
    document.getElementById('broadcast-yards').textContent = all.n ? Saturday.number(all.yards / all.n, 2) : '—';
    document.getElementById('broadcast-plays').textContent = Saturday.compact(all.n);
  }
  function fillBrandContext() {
    const name = els.team.value; const team = branding[name]; const initials = Saturday.initials(name);
    const context = els.context; const logo = els.identityLogo; logo.replaceChildren();
    const primary = team && /^#[0-9a-f]{6}$/i.test(team.primaryColor) ? team.primaryColor : '#cbff50';
    const secondary = team && /^#[0-9a-f]{6}$/i.test(team.secondaryColor) ? team.secondaryColor : '#344427';
    const color = contrastColor(primary, secondary);
    context.style.setProperty('--selected-team', color); context.style.setProperty('--selected-primary', primary); context.style.setProperty('--selected-secondary', secondary); document.documentElement.style.setProperty('--team', color); document.documentElement.style.setProperty('--team-secondary', secondary); document.body.style.setProperty('--team', color); document.body.style.setProperty('--team-secondary', secondary); chartColor = color;
    if (name && team && team.logo) {
      const image = document.createElement('img'); image.src = team.logo; image.alt = `${name} logo`; image.loading = 'lazy'; image.referrerPolicy = 'no-referrer';
      image.onerror = () => { image.replaceWith(fallback()); }; logo.append(image);
    } else logo.append(fallback());
    els.identityName.textContent = (name || 'ALL TEAMS').toUpperCase();
    els.identityKicker.textContent = name ? `${team && team.conference || '2025 COLLEGE FOOTBALL'} / ${els.perspective.value.toUpperCase()} PERFORMANCE` : 'SEASON-WIDE LENS / 2025';
    if (lastIdentity !== name) {
      context.classList.remove('team-changed'); void context.offsetWidth; context.classList.add('team-changed'); lastIdentity = name;
    }
    function fallback() { const box = document.createElement('span'); box.className = 'broadcast-logo-fallback'; box.textContent = initials; box.setAttribute('aria-hidden', 'true'); return box; }
  }
  function contrastColor(primary, secondary) {
    const luminance = (hex) => {
      const rgb = hex.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16) / 255).map((value) => value <= .04045 ? value / 12.92 : Math.pow((value + .055) / 1.055, 2));
      return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
    };
    if (luminance(primary) >= .2) return primary;
    return luminance(secondary) >= .2 ? secondary : '#cbff50';
  }
  function setOption(chart, groups, measure, label, kind = 'bar', emphasizeLeader = false) {
    const perspective = els.perspective.value; const val = groups.map((g) => currentMetric(g, measure, perspective));
    const categories = groups.map((g) => g.label);
    const commonText = '#b6c2c7'; const gridLine = '#26343e';
    const opts = {
      animationDuration: 350, animationDurationUpdate: 260,
      grid: { left: kind === 'bar' ? 132 : 46, right: 24, top: 25, bottom: 44, containLabel: false },
      tooltip: { trigger: kind === 'line' ? 'axis' : 'item', backgroundColor: '#101923', borderColor: chartColor, borderWidth: 1, padding: [11, 14], extraCssText: 'box-shadow:0 12px 34px rgba(0,0,0,.42);border-radius:2px', textStyle: { color: '#f2f3ee', fontFamily: 'DM Mono', fontSize: 10 }, formatter: (params) => {
        const item = Array.isArray(params) ? params[0] : params; const g = groups[item.dataIndex];
        const epaLabel = perspective === 'offense' ? 'Offensive EPA / play' : 'Defensive EPA / play';
        return `<strong>${Saturday.esc(g.label)}</strong><br>${Saturday.esc(measureLabels[measure])}: ${formatMeasure(item.value, measure)}<br>Actual plays: ${Saturday.compact(g.n)}<br>${epaLabel}: ${Saturday.signed(perspective === 'offense' ? g.meanEpa : g.meanDefEpa)}<br>Success: ${Saturday.percent(g.successRate)}`;
      } },
      xAxis: kind === 'bar' ? { type: 'value', axisLabel: { color: '#85949c', fontFamily: 'DM Mono', fontSize: 9, formatter: (v) => (measure === 'success' || measure === 'explosive' || measure === 'scoring') ? `${Math.round(v * 100)}%` : v }, splitLine: { lineStyle: { color: gridLine } }, axisLine: { lineStyle: { color: gridLine } } }
        : { type: 'category', data: categories, boundaryGap: kind !== 'line', axisLabel: { color: commonText, fontSize: 9, interval: 'auto', rotate: categories.length > 8 ? 25 : 0, formatter: (v) => v.length > 17 ? `${v.slice(0, 16)}…` : v }, axisLine: { lineStyle: { color: gridLine } }, axisTick: { show: false } },
      yAxis: kind === 'bar' ? { type: 'category', data: categories, inverse: true, axisLabel: { color: commonText, fontSize: 9, width: 120, overflow: 'truncate', formatter: (v) => v.length > 20 ? `${v.slice(0, 19)}…` : v }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
        : { type: 'value', min: measure === 'success' || measure === 'explosive' || measure === 'scoring' ? 0 : undefined, max: measure === 'success' || measure === 'explosive' || measure === 'scoring' ? 1 : undefined, axisLabel: { color: '#85949c', fontFamily: 'DM Mono', fontSize: 9, formatter: (v) => measure === 'success' || measure === 'explosive' || measure === 'scoring' ? `${Math.round(v * 100)}%` : v }, splitLine: { lineStyle: { color: gridLine } }, axisLine: { lineStyle: { color: gridLine } } },
      series: [{ type: kind, data: val, smooth: kind === 'line', symbolSize: 7, showSymbol: kind === 'line', barMaxWidth: 17, itemStyle: { color: kind === 'bar' && emphasizeLeader ? (params) => params.dataIndex === 0 ? chartColor : '#53656d' : chartColor, borderRadius: kind === 'bar' ? [0, 2, 2, 0] : 0 }, lineStyle: { color: chartColor, width: 2 }, areaStyle: kind === 'line' ? { color: `${chartColor}18` } : undefined, label: { show: categories.length <= 7 && kind === 'bar', position: 'right', color: '#dfe6e0', fontFamily: 'DM Mono', fontSize: 9, formatter: (p) => formatMeasure(p.value, measure) } }],
      aria: { enabled: true, decal: { show: true } }
    };
    chart.setOption(opts, true);
    const node = chart.getDom(); node.setAttribute('aria-label', `${label}. ${groups.length} categories. Measure: ${measureLabels[measure]}.`);
  }
  function renderCharts(primary, week, down, type) {
    const m = els.measure.value; const b = els.breakdown.value;
    document.getElementById('primary-chart-title').textContent = `${measureLabels[m]} by ${breakdownLabels[b].toLowerCase()}`;
    document.getElementById('primary-chart-unit').textContent = unitText(m);
    ['trend-unit', 'down-unit', 'type-unit'].forEach((id) => { document.getElementById(id).textContent = unitText(m); });
    const cap = (groups, max, sortFn = (a, b) => currentMetric(b, m) - currentMetric(a, m)) => groups.slice().sort(sortFn).slice(0, max);
    let first = primary;
    if (b === 'week') first = primary.slice().sort((a, z) => parseInt(a.label.replace(/\D/g, ''), 10) - parseInt(z.label.replace(/\D/g, ''), 10));
    else if (b === 'down') first = primary.slice().sort((a, z) => a.label.localeCompare(z.label));
    else if (b === 'quarter') first = primary.slice().sort((a, z) => a.label.localeCompare(z.label));
    else first = cap(primary, 14);
    const typePoints = cap(type, 14, (a, z) => z.n - a.n);
    const weekPoints = week.slice().sort((a, z) => Number(a.label.replace(/\D/g, '')) - Number(z.label.replace(/\D/g, '')));
    const downPoints = down.slice().sort((a, z) => Number(a.label.replace(/\D/g, '')) - Number(z.label.replace(/\D/g, '')));
    setOption(chartInstances[0], first, m, `${measureLabels[m]} by ${breakdownLabels[b]}`, b === 'week' ? 'line' : 'bar', b === 'team');
    setOption(chartInstances[1], weekPoints, m, `${measureLabels[m]} by week`, 'line');
    setOption(chartInstances[2], downPoints, m, `${measureLabels[m]} by down`, 'bar');
    setOption(chartInstances[3], typePoints, m, `${measureLabels[m]} by play type`, 'bar');
  }
  function renderTable(groups) {
    const measure = els.measure.value; const sort = els.sort.value;
    const sorted = groups.slice().sort((a, b) => sort === 'label' ? a.label.localeCompare(b.label) : sort === 'n' ? b.n - a.n : currentMetric(b, measure) - currentMetric(a, measure));
    resultRows = sorted; const pages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE)); page = Math.min(page, pages - 1);
    const start = page * PAGE_SIZE; const shown = sorted.slice(start, start + PAGE_SIZE); els.tbody.replaceChildren();
    if (!shown.length) { const tr = document.createElement('tr'); const td = document.createElement('td'); td.colSpan = 7; td.className = 'empty-cell'; td.textContent = 'No actual plays match these filters.'; tr.append(td); els.tbody.append(tr); }
    shown.forEach((g) => {
      const tr = document.createElement('tr'); const cells = [g.label, Saturday.compact(g.n), formatMeasure(currentMetric(g, measure), measure), Saturday.signed(g.meanEpa), Saturday.percent(g.successRate), Saturday.percent(g.explosiveRate), Saturday.percent(g.scoringRate)];
      cells.forEach((value, index) => { const td = document.createElement('td'); td.textContent = value; if (index === 0) td.title = g.label; tr.append(td); }); els.tbody.append(tr);
    });
    document.getElementById('table-caption').textContent = `Aggregated by ${breakdownLabels[els.breakdown.value]} • ${Saturday.compact(sorted.length)} groups • actual plays only`;
    document.getElementById('measure-heading').textContent = measureLabels[measure]; document.getElementById('table-title').textContent = 'Numbers behind this view';
    const headers = document.querySelectorAll('#results-table thead th');
    headers[3].textContent = els.perspective.value === 'offense' ? 'Mean offensive EPA' : 'Mean defensive EPA';
    headers[4].textContent = els.perspective.value === 'offense' ? 'EPA success' : 'Defensive stop rate';
    headers[5].textContent = els.perspective.value === 'offense' ? 'Explosive rate' : 'Non-explosive share';
    headers[6].textContent = els.perspective.value === 'offense' ? 'Scoring rate' : 'Opponent scoring rate';
    els.range.textContent = sorted.length ? `Showing ${start + 1}–${Math.min(start + PAGE_SIZE, sorted.length)} of ${Saturday.compact(sorted.length)} groups` : 'No groups';
    els.prev.disabled = page === 0; els.next.disabled = page >= pages - 1;
  }
  function render() {
    if (!rows) return;
    syncMeasureLabels();
    fillBrandContext();
    const filters = filtersNow();
    const groupKey = els.breakdown.value;
    const views = computeViews(filters, groupKey);
    updateCards(views.total);
    renderCharts(views.primary, views.week, views.down, views.type);
    renderTable(views.primary);
    els.status.textContent = `${Saturday.compact(rows.week.length)} actual plays • filters applied`;
  }
  function fail(error) {
    if (!els.error.hidden && settled) return;
    settled = true; window.clearTimeout(loadWatchdog);
    const message = error && (error.message || error.reason || error.type) ? (error.message || error.reason || error.type) : String(error || 'Unknown loading error');
    els.error.hidden = false;
    if (els.loading) els.loading.hidden = true;
    document.getElementById('main').inert = false;
    els.error.textContent = `The dashboard could not load its data: ${message}. ${location.protocol === 'file:' ? 'Open it through a local web server (see README) instead of opening the HTML file directly.' : 'Check that the CSV and JavaScript files are being served, then reload.'}`;
    els.status.textContent = 'Dashboard failed to load';
    els.status.setAttribute('data-state', 'error');
  }
  function showProgress(seen) {
    els.status.textContent = `Loading ${Saturday.compact(seen)} / ${Saturday.compact(EXPECTED_ROWS)} rows…`;
    els.loadCount.textContent = `${Saturday.compact(seen)} / ${Saturday.compact(EXPECTED_ROWS)} ROWS PARSED`;
    els.loadStage.textContent = seen ? 'Indexing teams and play outcomes…' : 'Receiving and parsing the play-by-play file…';
    const percentage = Math.min(100, seen / EXPECTED_ROWS * 100);
    els.loadFill.style.width = `${percentage}%`;
    els.loadFill.parentElement.setAttribute('aria-valuenow', String(seen));
    window.clearTimeout(loadWatchdog);
    loadWatchdog = window.setTimeout(() => fail(new Error(`No CSV loading progress for 60 seconds (${Saturday.compact(seen)} rows received)`)), 60000);
  }
  function load() {
    if (location.protocol === 'file:') { fail(new Error('Local file access blocks the CSV request')); return; }
    if (!window.Papa || !window.echarts) { fail(new Error('Visualization libraries are unavailable')); return; }
    const brandPromise = fetch(BRAND_URL).then((response) => { if (!response.ok) throw new Error('Team branding metadata could not load'); return response.json(); }).then((data) => { branding = data.teams || {}; }).catch(() => { branding = {}; });
    Promise.all([brandPromise]).then(() => {
      let seen = 0;
      let headersChecked = false;
      loadStartedAt = Date.now();
      showProgress(seen);
      Papa.parse(CSV_URL, {
        download: true, worker: false, header: true, skipEmptyLines: 'greedy', dynamicTyping: false,
        chunkSize: 1024 * 1024,
        chunk(result, parser) {
          try {
          if (!headersChecked) {
            const headers = result.meta && result.meta.fields || [];
            const missing = REQUIRED_HEADERS.filter((header) => !headers.includes(header));
            if (missing.length) throw new Error(`CSV header mismatch; missing: ${missing.join(', ')}`);
            headersChecked = true;
          }
          if (result.errors && result.errors.length) throw new Error(`CSV parse error: ${result.errors[0].message || result.errors[0].code}`);
          for (const record of result.data) {
            if (!record || !record.game_id) throw new Error(`CSV contains a row without game_id near row ${seen + 2}`);
            seen++;
            if (boolean(record.play)) pushRow(record);
          }
          showProgress(seen);
          } catch (error) {
            fail(error);
            if (parser && typeof parser.abort === 'function') parser.abort();
          }
        },
        complete() {
          try {
            if (!headersChecked) throw new Error('The CSV was empty or its header could not be read');
            if (seen !== EXPECTED_ROWS) throw new Error(`Expected ${Saturday.compact(EXPECTED_ROWS)} CSV rows but received ${Saturday.compact(seen)}`);
            if (lookup.teams.length <= 1) throw new Error('No team names were found in pos_team or def_pos_team');
            if (lookup.teams.length - 1 < 10) throw new Error(`Only ${lookup.teams.length - 1} distinct teams were found`);
            finalize(); initializeFilters();
            settled = true; window.clearTimeout(loadWatchdog);
            els.status.textContent = `${Saturday.compact(rows.week.length)} actual plays loaded in ${((Date.now() - loadStartedAt) / 1000).toFixed(1)}s`;
            els.status.setAttribute('data-state', 'ready');
            els.loadCount.textContent = `${Saturday.compact(seen)} SOURCE ROWS / ${Saturday.compact(rows.week.length)} ACTUAL PLAYS`;
            els.loadStage.textContent = 'Signal acquired. The season is ready.';
            els.loadFill.style.width = '100%'; els.loadFill.parentElement.setAttribute('aria-valuenow', String(EXPECTED_ROWS));
            els.loading.classList.add('is-dismissed'); window.setTimeout(() => { els.loading.hidden = true; document.getElementById('main').inert = false; }, 480);
          } catch (error) { fail(error); }
        },
        error: fail
      });
    }).catch(fail);
  }
  window.addEventListener('error', (event) => {
    if (!settled && (event.target instanceof HTMLScriptElement || event.message)) fail(new Error(event.message || `Script failed to load: ${event.target && event.target.src || 'unknown script'}`));
  }, true);
  window.addEventListener('unhandledrejection', (event) => { if (!settled) fail(event.reason); });
  load();
})();
