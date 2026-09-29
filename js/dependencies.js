(() => {
  const libraries = [
    ['ECharts', 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js', () => Boolean(window.echarts?.init)],
    ...(document.location.pathname.endsWith('/dashboard.html')
      ? [['Papa Parse', 'https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js', () => Boolean(window.Papa?.parse)]]
      : [])
  ];
  const load = ([name, src, available]) => new Promise((resolve, reject) => {
    if (available()) { resolve(); return; }
    const script = document.createElement('script');
    const timer = setTimeout(() => {
      script.remove();
      reject(new Error(`${name} did not load from its CDN within 15 seconds`));
    }, 15000);
    script.src = src;
    script.async = true;
    script.onload = () => {
      clearTimeout(timer);
      if (available()) resolve();
      else reject(new Error(`${name} loaded without exposing its expected browser API`));
    };
    script.onerror = () => {
      clearTimeout(timer);
      reject(new Error(`${name} could not load from ${src}`));
    };
    document.head.append(script);
  });
  window.GridironDependencies = { ready: Promise.all(libraries.map(load)) };
})();
