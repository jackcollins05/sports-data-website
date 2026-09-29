(() => {
  const DATA = 'data/football_2025/report_findings_2025.json';
  const BRAND_URL = 'data/team_branding.json';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const fmt = GridironPulse;
  let teams = {};
  const charts = [];
  const make = (tag, cls, text) => { const el = document.createElement(tag); if (cls) el.className = cls; if (text != null) el.textContent = text; return el; };
  const brand = (teamId) => {
    for (const [name, value] of Object.entries(teams)) if (String(value.id) === String(teamId)) return { name, ...value };
    return null;
  };
  const logo = (teamId, className = 'team-mark') => {
    const meta = brand(teamId); const wrap = make('span', className);
    if (meta?.logo) { const img = document.createElement('img'); img.src = meta.logo; img.alt = `${meta.team_name || meta.name} logo`; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer'; img.onerror = () => img.replaceWith(make('span','mark-fallback',fmt.initials(meta.shortName || meta.team_name))); wrap.append(img); }
    else wrap.append(make('span','mark-fallback',fmt.initials(meta?.shortName)));
    if (meta?.primaryColor) wrap.style.setProperty('--mark-color',fmt.color(meta.primaryColor));
    return wrap;
  };
  const chartBase = {
    animationDuration: 680, animationDurationUpdate: 360,
    textStyle: { fontFamily: 'Manrope, sans-serif', color: '#a9b5bd' },
    grid: { left: 138, right: 35, top: 20, bottom: 38, containLabel: false },
    tooltip: { trigger:'axis', axisPointer:{type:'shadow'}, backgroundColor:'#101b26', borderColor:'#314552', textStyle:{color:'#f2f5f1',fontFamily:'DM Mono,monospace',fontSize:11}, extraCssText:'box-shadow:0 14px 40px #0009;border-radius:4px' },
    xAxis: { type:'value', axisLabel:{color:'#80909a',fontSize:10,fontFamily:'DM Mono'}, splitLine:{lineStyle:{color:'#263540'}}, axisLine:{lineStyle:{color:'#263540'}} },
    yAxis: { type:'category', inverse:true, axisLabel:{color:'#d3dbdc',fontSize:11,width:124,overflow:'truncate'}, axisTick:{show:false}, axisLine:{show:false} },
    aria:{enabled:true,decal:{show:true}}
  };
  async function loadJson(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') throw new Error(`${url} did not respond within 25 seconds`);
      throw error;
    } finally { clearTimeout(timer); }
  }
  function optionFor(story) {
    const data = story.data;
    const labels = Array.isArray(data) ? data.map(d => d.label || d.team || d.name || `Week ${d.week}`) : [];
    if (story.kind === 'movement') {
      const merged=[...data.risers.map(x=>({...x,kind:'Riser'})),...data.fallers.map(x=>({...x,kind:'Fall'}))];
      return {...chartBase,grid:{...chartBase.grid,left:165},tooltip:{...chartBase.tooltip,formatter:p=>{const x=merged[p[0].dataIndex];return `<b>${fmt.esc(x.team)}</b><br>Preseason #${x.preseason_rank} → Final #${x.final_rank}<br>${x.movement>0?'Up':'Down'} ${Math.abs(x.movement)} places`; }},yAxis:{...chartBase.yAxis,data:merged.map(x=>x.team)},series:[{type:'bar',data:merged.map(x=>({value:x.movement,itemStyle:{color:x.movement>=0?'#bded57':'#ff7c70'}})),barMaxWidth:18,label:{show:true,position:'right',color:'#e8ede8',fontFamily:'DM Mono',formatter:p=>`${p.value>0?'+':''}${p.value}`}}],legend:{show:false}};
    }
    if (story.kind === 'weekly') return { ...chartBase, grid:{left:50,right:24,top:24,bottom:38}, tooltip:{...chartBase.tooltip,trigger:'axis',formatter:p=>{const w=data[p[0].dataIndex];return `<b>Week ${w.week}</b><br>${fmt.number(w.points_per_team_game,1)} points / team-game<br>${w.team_games} team games`; }}, xAxis:{type:'category',data:data.map(x=>`W${x.week}`),axisLabel:{color:'#84949b',fontFamily:'DM Mono'},axisLine:{lineStyle:{color:'#263540'}},axisTick:{show:false}},yAxis:{type:'value',axisLabel:{color:'#84949b',fontFamily:'DM Mono'},splitLine:{lineStyle:{color:'#263540'}}},series:[{type:'line',data:data.map(x=>x.points_per_team_game),smooth:.28,symbolSize:7,lineStyle:{color:'#c7ff4a',width:3},itemStyle:{color:'#c7ff4a',borderColor:'#07101a',borderWidth:2},areaStyle:{color:'rgba(199,255,74,.10)'}}]};
    if (story.kind === 'churn') return {...chartBase,grid:{left:60,right:25,top:36,bottom:42},tooltip:{...chartBase.tooltip,trigger:'axis'},legend:{top:0,right:8,textStyle:{color:'#a9b5bd'},data:['Entered','Dropped']},xAxis:{type:'category',data:data.map(x=>x.poll_label.replace('Week ','W')),axisLabel:{color:'#84949b',fontFamily:'DM Mono'},axisLine:{lineStyle:{color:'#263540'}},axisTick:{show:false}},yAxis:{type:'value',axisLabel:{color:'#84949b'},splitLine:{lineStyle:{color:'#263540'}}},series:[{name:'Entered',type:'bar',data:data.map(x=>x.entered),itemStyle:{color:'#c7ff4a'},barMaxWidth:18},{name:'Dropped',type:'bar',data:data.map(x=>x.dropped),itemStyle:{color:'#ff7c70'},barMaxWidth:18}]};
    if (story.kind === 'stacked-teams') return {...chartBase,tooltip:{...chartBase.tooltip,trigger:'axis',formatter:p=>{const d=data[p[0].dataIndex];return `<b>${fmt.esc(d.label)}</b><br>Net passing: ${fmt.number(d.pass,1)} yd / game<br>Rushing: ${fmt.number(d.rush,1)} yd / game<br>Total offense: ${fmt.number(d.value,1)} yd / game`; }},yAxis:{...chartBase.yAxis,data:labels},series:[{name:'Net passing yards / game',type:'bar',stack:'yards',data:data.map(x=>x.pass),itemStyle:{color:'#55b9e8'},barMaxWidth:18},{name:'Rushing yards / game',type:'bar',stack:'yards',data:data.map(x=>x.rush),itemStyle:{color:'#c7ff4a'},barMaxWidth:18}],legend:{top:0,right:6,textStyle:{color:'#a9b5bd'}}};
    const metric=story.kind==='players'?story.metric:story.metric;
    const values=data.map(x=> Number(x[metric] ?? x.value));
    const percent=story.kind==='third-down';
    return {...chartBase,tooltip:{...chartBase.tooltip,formatter:p=>{const x=data[p[0].dataIndex];const value=Number(x[metric]??x.value);return `<b>${fmt.esc(x.name||x.label||x.team)}</b><br>${fmt.esc(story.unit)}: ${percent?fmt.percent(value,1):fmt.number(value,metric==='sacks'?1:0)}${story.kind==='players'?`<br>${fmt.esc(x.team)} · ${fmt.esc(x.position||'')}`:''}${x.games?`<br>${x.games} games`:''}`;}},yAxis:{...chartBase.yAxis,data:labels},xAxis:{...chartBase.xAxis,max:percent?100:undefined,axisLabel:{...chartBase.xAxis.axisLabel,formatter: v=>percent?`${v}%`:fmt.number(v)}},series:[{type:'bar',data:values.map((v,i)=>({value:v,itemStyle:{color:brand(data[i].team_id)?.primaryColor?fmt.color(brand(data[i].team_id).primaryColor):'#c7ff4a',borderRadius:[0,4,4,0]}})),barMaxWidth:18,label:{show:true,position:'right',color:'#e8ede8',fontFamily:'DM Mono',fontSize:10,formatter:p=>percent?`${Number(p.value).toFixed(1)}%`:fmt.number(p.value,story.metric==='sacks'?1:0)}}]};
  }
  function playerSpotlight(story) {
    const p=story.data[0]; if (!p) return null;
    const card=make('aside','player-spotlight'); card.append(logo(p.team_id,'spotlight-team-logo'));
    const portrait=make('div','player-portrait');
    if(p.headshot_url){const img=document.createElement('img');img.src=p.headshot_url;img.alt=`${p.name}, ${p.team}`;img.loading='lazy';img.referrerPolicy='no-referrer';img.onerror=()=>img.replaceWith(make('span','portrait-fallback',fmt.initials(p.name)));portrait.append(img);}else portrait.append(make('span','portrait-fallback',fmt.initials(p.name)));
    const bio=make('div','player-spotlight-bio');bio.append(make('span','spotlight-kicker',`${p.position || 'PLAYER'} / #${p.jersey || '—'} / ${p.team_abbreviation}`),make('strong','',p.name),make('span','spotlight-school',p.team));
    const values=story.metric==='passing_yards'?[[fmt.number(p.passing_yards),'PASS YARDS'],[fmt.number(p.passing_touchdowns),'PASS TD'],[fmt.percent(p.completion_pct,1),'COMPLETION']]:story.metric==='rushing_yards'?[[fmt.number(p.rushing_yards),'RUSH YARDS'],[fmt.number(p.rushing_attempts),'CARRIES'],[fmt.number(p.rushing_yards_per_attempt,2),'YARDS / CARRY']]:story.metric==='receiving_yards'?[[fmt.number(p.receiving_yards),'REC YARDS'],[fmt.number(p.receptions),'CATCHES'],[fmt.number(p.receiving_touchdowns),'REC TD']]:[[fmt.number(p.sacks,1),'SACKS'],[fmt.number(p.tackles),'TACKLES'],[fmt.number(p.tfl,1),'TACKLES FOR LOSS']];
    const metrics=make('div','spotlight-metrics');values.forEach(([v,k])=>{const cell=make('div','');cell.append(make('b','',v),make('span','',k));metrics.append(cell);});
    card.append(portrait,bio,metrics);return card;
  }
  function gameScoreboard(data) {
    const host=make('div','game-feature-row');
    for(const game of data.close.slice(0,4)){
      const card=make('article','scorebug');card.append(make('span','scorebug-meta',`${game.season_type==='3'?'POSTSEASON':`WEEK ${game.week}`} · ${game.margin===1?'1-POINT FINISH':`${game.margin}-POINT FINISH`}`));
      const sides=make('div','scorebug-sides');
      const home=make('div','scorebug-side');home.append(logo(game.home_team_id,'game-logo'),make('span','scorebug-name',shortTeamName(game.home_team)),make('b','scorebug-score',fmt.number(game.home_score)));
      const away=make('div','scorebug-side');away.append(logo(game.away_team_id,'game-logo'),make('span','scorebug-name',shortTeamName(game.away_team)),make('b','scorebug-score',fmt.number(game.away_score)));
      sides.append(home,make('span','scorebug-at','FINAL'),away);card.append(sides);host.append(card);
    }
    return host;
  }
  function shortTeamName(name) { return String(name || '').replace(/ (Tigers|Bulldogs|Eagles|Wildcats|Bears|Huskies|Rebels|Panthers|Cardinals|Hawks|Trojans|Raiders|Knights|Rams|Wolves|Lions|Spartans|Warriors|Owls|Falcons|Bruins|Gators|Hurricanes|Cougars|Aggies|Mustangs|Pirates|Buffaloes|Volunteers|Sooners|Buckeyes|Hoosiers|Irish|RedHawks|Golden Hurricane|Mean Green|Ragin' Cajuns|Thundering Herd|Dukes|Tide|Gamecocks|Seminoles|Orange|Aztecs)$/,''); }
  function chartFor(story, index) {
    const figure=make('figure','report-chart');figure.setAttribute('aria-label',`${story.unit || story.kicker} visualization`);
    const head=make('figcaption','report-chart-heading');head.append(make('span','chart-ledger-mark',String(index+1).padStart(2,'0')),make('span','',story.unit || story.kicker));figure.append(head);
    if(story.kind==='games'){
      figure.append(make('div','game-count-callout',fmt.compact(story.data.close_count)));
      figure.append(make('p','game-count-label','close finishes from the full FBS-involving schedule'));
      figure.append(gameScoreboard(story.data));
      const top=story.data.high_scoring[0]; if(top){const badge=make('div','big-scoreline');badge.append(make('span','',`HIGHEST TOTAL · ${top.season_type==='3'?'POSTSEASON':`WEEK ${top.week}`}`),make('strong','',`${top.home_score} — ${top.away_score}`),make('small','',`${top.home_team} vs ${top.away_team} / ${fmt.number(top.combined)} combined points`));figure.append(badge);}
      return figure;
    }
    const canvas=make('div','report-chart-canvas');canvas.id=`report-chart-${story.id}`;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`${story.kicker}; ${story.data.length || story.data.risers?.length || 0} displayed records`);figure.append(canvas);
    if(story.kind==='players') {const spot=playerSpotlight(story);if(spot)figure.append(spot);}
    if(story.kind==='movement') figure.append(make('p','chart-caption','Rise is preseason rank minus final rank; positive values mean moved up. This graphic includes teams ranked in both snapshots.'));
    return figure;
  }
  function card(label,value,foot){const el=make('div','stat-card');const number=make('strong','stat-value',value);const end=Number(String(value).replace(/,/g,''));if(Number.isFinite(end))number.dataset.count=String(end);el.append(number,make('span','stat-label',label),make('span','stat-foot',foot));return el;}
  function installReveals(){const els=$$('[data-reveal],.stat-value');const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;const show=node=>{node.classList.add('is-visible');const n=node.matches('[data-count]')?node:node.querySelector('[data-count]');if(n&&!n.dataset.counted){n.dataset.counted='true';const end=+n.dataset.count;if(reduced){n.textContent=end.toLocaleString('en-US');return;}const start=performance.now();const step=t=>{const p=Math.min(1,(t-start)/800);n.textContent=Math.round(end*(1-Math.pow(1-p,3))).toLocaleString('en-US');if(p<1)requestAnimationFrame(step);};requestAnimationFrame(step);}};if(reduced||!('IntersectionObserver'in window)){els.forEach(show);return;}const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){show(e.target);io.unobserve(e.target);}}),{threshold:.12});els.forEach(x=>io.observe(x));}
  function render(data){
    const o=data.overview;const values={'fbs_teams':o.fbs_teams,'fbs_games':o.fbs_games,'players':o.players};
    $$('[data-overview]').forEach(n=>n.textContent=fmt.compact(values[n.dataset.overview]));
    $('#report-summary').textContent=`The 2025 FBS season spans ${fmt.compact(o.fbs_teams)} teams and ${fmt.compact(o.fbs_games)} scheduled games involving at least one FBS program, including FBS–FCS matchups. The prepared player pool contains ${fmt.compact(o.players)} FBS roster entries; the source schedule reports ${fmt.compact(o.fbs_points_scored)} FBS team points. Official AP data supplies ${fmt.compact(o.poll_snapshots)} snapshots: preseason, regular polls labeled Weeks 2–16, and the final poll.`;
    const cards=$('#headline-stats');cards.replaceChildren(card('FBS PROGRAMS',fmt.compact(o.fbs_teams),'Full FBS roster coverage'),card('FBS-INVOLVING GAMES',fmt.compact(o.fbs_games),'Includes games against FCS opponents'),card('PLAYER / TEAM ENTRIES',fmt.compact(o.players),'Prepared FBS roster entries'),card('AP POLL SNAPSHOTS',fmt.compact(o.poll_snapshots),`Preseason + ${o.regular_polls} regular + final`),card('FBS TEAM POINTS',fmt.compact(o.fbs_points_scored),'Across reported team-game scores'));
    const index=$('#story-index-links'),container=$('#findings');index.replaceChildren();container.replaceChildren();
    if (!data?.overview || !Array.isArray(data.stories) || data.stories.length < 8) throw new Error('The report findings JSON is missing its overview or story sections.');
    if (!window.echarts?.init) throw new Error('ECharts is unavailable; report charts cannot initialize.');
    data.stories.forEach((story,i)=>{
      const link=make('a','index-link');link.href=`#story-${story.id}`;link.append(make('b','',String(i+1).padStart(2,'0')),make('span','',story.title));index.append(link);
      const section=make('article',`finding finding--${i%3===1?'wide':i%3===2?'stat':'standard'}`);section.id=`story-${story.id}`;section.dataset.reveal='';
      const copy=make('div','finding-copy');const kicker=make('div','finding-kicker');kicker.append(make('span','',story.kicker),make('b','',`FIELD NOTE ${String(i+1).padStart(2,'0')}`));copy.append(kicker,make('h2','',story.title),make('p','',story.copy));
      if(story.kind==='movement'){const rankItems=[...story.data.risers.slice(0,3).map(x=>({...x,type:'BIGGEST RISE'})),...story.data.fallers.slice(0,2).map(x=>({...x,type:'BIGGEST DROP'}))];const chips=make('div','movement-calls');for(const x of rankItems){const item=make('div','movement-chip');item.append(logo(x.team_id,'movement-logo'),make('span','',`${x.team} · ${x.type}`),make('strong','',`${x.movement>0?'+':''}${x.movement}`));chips.append(item);}copy.append(chips);}
      section.append(copy,chartFor(story,i));container.append(section);
    });
    // ECharts measures its host at initialization. Initialize only after the
    // complete report section is attached and has its final CSS dimensions.
    data.stories.forEach(story=>{
      if(story.kind==='games')return;
      const host=$(`#report-chart-${story.id}`);
      if(!host||!host.isConnected)throw new Error(`Report chart container is missing for ${story.id}.`);
      const rect=host.getBoundingClientRect();
      if(rect.width<1||rect.height<1)throw new Error(`Report chart container has no visible size for ${story.id}.`);
      const chart=window.echarts.init(host,null,{renderer:'canvas'});
      chart.setOption(optionFor(story));charts.push(chart);
    });
    installReveals();window.addEventListener('resize',()=>charts.forEach(c=>c.resize()),{passive:true});
  }
  Promise.all([window.GridironDependencies.ready,loadJson(DATA),loadJson(BRAND_URL)])
    .then(([,data,brandData])=>{teams=brandData.teams||{};render(data);window.GridironBoot?.ready();})
    .catch(error=>{const message=`The season report could not finish loading: ${error.message}. Check the local server, CDN access, and prepared data files.`;$('#findings').textContent=message;window.GridironBoot?.fail(error.message);});
})();
