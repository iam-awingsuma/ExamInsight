(function () {
  const elYrgrp   = document.getElementById('yrgrp');
  const elStudent = document.getElementById('student');
  // const btnViewAnalytics = document.getElementById('btnViewAnalytics');

  // Helpers
  function setStudentDisabled(disabled) { elStudent.disabled = disabled; }
  function clearStudents() {
    elStudent.innerHTML = '<option value="">All Students in the Year Group</option>';
  }
  function addStudentOption(id, name) {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = name;
    elStudent.appendChild(opt);
  }

  async function fetchStudentsByYear(yrgrp) {
    clearStudents();
    if (!yrgrp) { setStudentDisabled(true); return; }
    setStudentDisabled(true);
    try {
      const res = await fetch(`/api/students_by_year?yrgrp=${encodeURIComponent(yrgrp)}`);
      const data = await res.json();
      (data.students || []).forEach(s => addStudentOption(s.id, s.name));
      setStudentDisabled(false);
    } catch (e) {
      console.error('Failed to load students:', e);
      setStudentDisabled(true);
    }
  }

  async function fetchAnalytics() {
    const yrgrp = elYrgrp.value.trim();
    const sid   = elStudent.value.trim();
    const qs = new URLSearchParams();
    if (yrgrp) qs.set('yrgrp', yrgrp);
    if (sid)   qs.set('student_id', sid);

    try {
      const res = await fetch(`/api/analytics?${qs.toString()}`);
      const payload = await res.json();
      renderKPIs(payload.kpi_subjects || {});
      renderTotalKPI(payload.kpi_total || {});
      renderLine(payload.line || {});
      renderBands(payload.bands || {});
      renderProgCats(payload.progcats || {});
    } catch (e) {
      console.error('Failed to load analytics:', e);
      renderKPIs({});
      renderTotalKPI({});
      renderLine({});
      renderBands({});
      renderProgCats({});
    }
  }

  // Renderers: display three adaptive KPI cards
  // per subject KPI (adapt to scope)
  function renderKPIs(k = {}) {
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = (typeof val === 'number' ? val.toFixed(1) : '—');
    };
    const setText = (id, txt) => {
      const el = document.getElementById(id);
      if (el) el.textContent = txt || '';
    };

    // Values
    set('kpi_eng',   k.english);
    set('kpi_maths', k.maths);
    set('kpi_sci',   k.science);
  }

  function renderTotalKPI(t = {}) {
    const titleEl = document.getElementById('kpi_total_title');
    const countEl = document.getElementById('kpi_total_value');

    if (titleEl) titleEl.textContent = t.title || 'Year 2 Cohort';
    if (countEl) countEl.textContent = t.count ?? '—';
  }

  function renderLine(line) {
    const labels = line.labels || ['Previous','Current'];
    const eng = line.english || [0,0];
    const math= line.maths   || [0,0];
    const sci = line.science || [0,0];
    const traces = [
      { x: labels, y: eng,  type: 'scatter', mode: 'lines+markers', name: 'English', marker:{ color:"#0BA6DF" }},
      { x: labels, y: math, type: 'scatter', mode: 'lines+markers', name: 'Maths', marker:{ color:"#FCB53B" }},
      { x: labels, y: sci,  type: 'scatter', mode: 'lines+markers', name: 'Science', marker:{ color:"#A7E399" }},
    ];
    const layout = {
      margin: { t: 10, r: 10, b: 40, l: 50 },
      yaxis: { title: '%', rangemode: 'tozero' },
      legend: { orientation: 'h' }
    };
    Plotly.newPlot('chart_line', traces, layout, {displayModeBar:false, responsive:true});
  }

  function renderBands(bands = {}) {
    const labels = bands.labels || ['E/D','C','B','A','A*'];
    const hasStacks = Array.isArray(bands.english) && Array.isArray(bands.maths) && Array.isArray(bands.science);
    const toNums = arr => (arr || []).map(v => (typeof v==='number'?v:Number(v)||0));

    const traces = hasStacks
      ? [
        { x: labels, y: toNums(bands.science), type:'bar', name:'Science', marker:{ color:"#A7E399" }},
        { x: labels, y: toNums(bands.maths),   type:'bar', name:'Maths', marker:{ color:"#FCB53B" }},
        { x: labels, y: toNums(bands.english), type:'bar', name:'English', marker:{ color:"#0BA6DF" }},
        ]
      : [{ x: labels, y: toNums(bands.counts), type:'bar', name:'All subjects' }];

    Plotly.newPlot('chart_bands', traces, {
      margin:{t:10,r:10,b:40,l:50},
      yaxis:{title:'Count', rangemode:'tozero'},
      barmode: hasStacks ? 'stack' : 'group',
      legend:{orientation:'h'}
    }, {displayModeBar:false, responsive:true});
  }

  function renderProgCats(progcats = {}) {
    // x-axis categories (order locked)
    const labels = progcats.labels || ['Below Expected', 'Expected', 'Above Expected'];
    const hasStacks = Array.isArray(progcats.english) && Array.isArray(progcats.maths) && Array.isArray(progcats.science);
    // helper
    const toNums = arr => (arr || []).map(v => (typeof v === 'number' ? v : Number(v) || 0));

    const tracess = hasStacks
      ? [
        { x: labels, y: toNums(progcats.science), type:'bar', name:'Science', marker:{ color:"#A7E399" }},  // previous color: #7ddc1f
        { x: labels, y: toNums(progcats.maths),   type:'bar', name:'Maths', marker:{ color:"#FCB53B" }},  // previous color: #FF6500
        { x: labels, y: toNums(progcats.english), type:'bar', name:'English', marker:{ color:"#0BA6DF" }},  // previous color: #0073e5
        ]
      : [{ x: labels, y: toNums(progcats.counts), type:'bar', name:'All subjects' }];

    // Plotly.newPlot('chart_progcats', tracess layout, { displayModeBar: false, responsive: true });
    Plotly.newPlot('chart_progcats', tracess, {
      margin:{t:10,r:10,b:40,l:50},
      xaxis: { title: 'Progress Category', categoryorder: 'array', categoryarray: labels},
      yaxis:{title:'Count', rangemode:'tozero'},
      // barmode: hasStacks ? 'stack' : 'group',
      legend:{orientation:'h'},
      barmode: 'stack',
    }, {displayModeBar:false, responsive:true});
  }

  // Event bindings
  elYrgrp.addEventListener('change', async () => {
    await fetchStudentsByYear(elYrgrp.value);
    await fetchAnalytics();
  });

  elStudent.addEventListener('change', fetchAnalytics);
  // btnViewAnalytics.addEventListener('click', fetchAnalytics);

  (async () => {
    if (elYrgrp.value) {
      await fetchStudentsByYear(elYrgrp.value);   // preload students if a year group is preselected
    } else {
      setStudentDisabled(true);                    // keep student dropdown disabled until a year group is chosen
    }
    await fetchAnalytics();
  })();

  // Responsive charts
  ['chart_line','chart_bands','chart_progcats', 'progressChart'].forEach(id => {
    const el = document.getElementById(id);
    window.addEventListener('resize', () => Plotly.Plots.resize(el));
    new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
    document.addEventListener('shown.bs.tab', () => Plotly.Plots.resize(el));
    document.addEventListener('shown.bs.collapse', () => Plotly.Plots.resize(el));
  });

})();