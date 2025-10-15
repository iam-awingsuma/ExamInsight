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
      renderKPIs(payload.summary || {});
      renderLine(payload.line || {});
      renderBands(payload.bands || {});
      renderProgCats(payload.progcats || {});
    } catch (e) {
      console.error('Failed to load analytics:', e);
      renderKPIs({});
      renderLine({});
      renderBands({});
      renderProgCats({});
    }
  }

  // Renderers
  function renderKPIs(s) {
    document.getElementById('kpi_total').textContent = s.total_students ?? '0';
    document.getElementById('kpi_avg').textContent   = (s.avg_attainment ?? 0).toFixed(2);
    document.getElementById('kpi_delta').textContent = (s.progress_delta ?? 0).toFixed(2);
    document.getElementById('kpi_above').textContent = s.above_target ?? 0;
    document.getElementById('kpi_below').textContent = s.below_target ?? 0;
  }

  function renderLine(line) {
    const labels = line.labels || ['Previous','Current'];
    const eng = line.english || [0,0];
    const math= line.maths   || [0,0];
    const sci = line.science || [0,0];
    const traces = [
      { x: labels, y: eng,  type: 'scatter', mode: 'lines+markers', name: 'English', marker:{ color:"#0073e5" }},
      { x: labels, y: math, type: 'scatter', mode: 'lines+markers', name: 'Maths', marker:{ color:"#FF6500" }},
      { x: labels, y: sci,  type: 'scatter', mode: 'lines+markers', name: 'Science', marker:{ color:"#7ddc1f" }},
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
        { x: labels, y: toNums(bands.science), type:'bar', name:'Science', marker:{ color:"#7ddc1f" }},
        { x: labels, y: toNums(bands.maths),   type:'bar', name:'Maths', marker:{ color:"#FF6500" }},
        { x: labels, y: toNums(bands.english), type:'bar', name:'English', marker:{ color:"#0073e5" }},
        ]
      : [{ x: labels, y: toNums(bands.counts), type:'bar', name:'All subjects' }];

    Plotly.newPlot('chart_bands', traces, {
      margin:{t:10,r:10,b:40,l:50},
      yaxis:{title:'Count', rangemode:'tozero'},
      barmode: hasStacks ? 'stack' : 'group',
      legend:{orientation:'h'}
    }, {displayModeBar:false, responsive:true});
  }


  function renderProgCats(progcats) {
    const labels = progcats.labels || [];
    const counts = progcats.counts || [];
    const trace = { x: labels, y: counts, type: 'bar' };
    const layout = {
      margin: { t: 10, r: 10, b: 80, l: 50 },
      yaxis: { title: 'Count', rangemode: 'tozero' },
      xaxis: { title: 'Progress category', tickangle: -20 }
    };
    Plotly.newPlot('chart_progcats', [trace], layout, {displayModeBar:false, responsive:true});
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
  ['chart_line','chart_bands','chart_progcats'].forEach(id => {
    const el = document.getElementById(id);
    window.addEventListener('resize', () => Plotly.Plots.resize(el));
    new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
    document.addEventListener('shown.bs.tab', () => Plotly.Plots.resize(el));
    document.addEventListener('shown.bs.collapse', () => Plotly.Plots.resize(el));
  });
})();
