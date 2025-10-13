
//   <!-- Icons (Lucide) -->
//   <script defer src="https://unpkg.com/lucide@latest"></script>
//   <!-- Chart.js -->
//   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>


// <script>
//   // Icons
//   window.addEventListener('DOMContentLoaded', () => { lucide.createIcons(); });

//   const yearSel = document.getElementById('year_group');
//   const studentSel = document.getElementById('student');
//   const btnApply = document.getElementById('btnApply');

//   let lineChart, barChart, catChart;

//   async function loadAnalytics() {
//     const yr = yearSel.value;
//     const sid = studentSel.value;
//     const url = new URL(window.location.origin + "/api/analytics");
//     if (yr) url.searchParams.set("yrgrp", yr);
//     if (sid) url.searchParams.set("student_id", sid);

//     const res = await fetch(url);
//     const data = await res.json();

//     // Line: Prev vs Current by Subject
//     const lineCtx = document.getElementById('lineChart').getContext('2d');
//     if (lineChart) lineChart.destroy();
//     lineChart = new Chart(lineCtx, {
//       type: 'line',
//       data: {
//         labels: data.line.labels,
//         datasets: [
//           { label: 'English', data: data.line.english, tension: .3 },
//           { label: 'Maths',   data: data.line.maths,   tension: .3 },
//           { label: 'Science', data: data.line.science, tension: .3 }
//         ]
//       },
//       options: {
//         responsive: true,
//         plugins: { legend: { position: 'bottom' } },
//         scales: { y: { beginAtZero: true, suggestedMax: 100 } }
//       }
//     });

//     // Bands (current %) with your colour scheme
//     const barCtx = document.getElementById('barChart').getContext('2d');
//     if (barChart) barChart.destroy();
//     const bandColors = ['#e63946', '#ffcc99', '#ffd166', '#06d6a0', '#118ab2']; // red, peach, yellow, green, blue
//     barChart = new Chart(barCtx, {
//       type: 'bar',
//       data: {
//         labels: data.bands.labels,
//         datasets: [{
//           label: 'Counts',
//           data: data.bands.counts,
//           backgroundColor: bandColors
//         }]
//       },
//       options: {
//         responsive: true,
//         plugins: { legend: { display: false } },
//         scales: { y: { beginAtZero: true, precision: 0 } }
//       }
//     });

//     // Progress Categories (from *_progcat)
//     const catElId = 'progCatChart';
//     let catCanvas = document.getElementById(catElId);
//     if (!catCanvas) {
//       // insert a third chart card if it doesn't exist yet
//       const row = document.querySelector('.row.g-4');
//       const col = document.createElement('div');
//       col.className = 'col-12';
//       col.innerHTML = `
//         <div class="card border-0 rounded-3 shadow-sm mt-4">
//           <div class="card-body">
//             <div class="d-flex justify-content-between align-items-center mb-2">
//               <h5 class="card-title mb-0">Progress Categories</h5>
//               <i data-lucide="pie-chart"></i>
//             </div>
//             <canvas id="${catElId}" height="220"></canvas>
//           </div>
//         </div>`;
//       row.appendChild(col);
//       lucide.createIcons();
//       catCanvas = document.getElementById(catElId);
//     }

//     if (catChart) catChart.destroy();
//     catChart = new Chart(catCanvas.getContext('2d'), {
//       type: 'bar',
//       data: {
//         labels: data.progcats.labels,
//         datasets: [{
//           label: 'Count',
//           data: data.progcats.counts
//         }]
//       },
//       options: {
//         responsive: true,
//         plugins: { legend: { display: false } },
//         scales: { y: { beginAtZero: true, precision: 0 } }
//       }
//     });
//   }

//   btnApply.addEventListener('click', loadAnalytics);
//   loadAnalytics();
// </script>

// <!-- Refactored: unified event handling and async logic -->
// <script>
// document.addEventListener('DOMContentLoaded', () => {
//   const yearSel    = document.getElementById('year_group');
//   const studentSel = document.getElementById('student');

//   async function loadStudentsAndAnalyze() {
//     // Reset options & disable while loading
//     studentSel.replaceChildren(new Option('All Students', ''));
//     studentSel.disabled = true;

//     const yr = (yearSel?.value || '').trim();

//     // Build the correct URL for your blueprint endpoint
//     const stuUrl = new URL('{{ url_for("home_blueprint.api_students_by_year") }}', window.location.origin);
//     if (yr) stuUrl.searchParams.set('yrgrp', yr);

//     try {
//       const res = await fetch(stuUrl.toString(), { credentials: 'same-origin', headers: { 'Accept': 'application/json' }});
//       if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);

//       const data = await res.json();
//       const students = Array.isArray(data.students) ? data.students : [];

//       // Populate options (if none, you'll still have "All Students")
//       for (const s of students) {
//         studentSel.add(new Option(s.name, s.id));
//       }
//     } catch (err) {
//       console.error('Failed to load students:', err);
//       // Optional: show a friendly fallback option
//       studentSel.add(new Option('— could not load —', '' ));
//     } finally {
//       // 🔑 ALWAYS re-enable so the user can select "All Students"
//       studentSel.disabled = false;

//       // If you want to auto-run analytics after loading:
//       if (typeof runAnalytics === 'function') {
//         runAnalytics();
//       }
//     }
//   }

//   // Wire events
//   if (yearSel) {
//     yearSel.addEventListener('change', loadStudentsAndAnalyze);
//     // On first load: run once (with or without year selected)
//     loadStudentsAndAnalyze();
//   }
//   if (studentSel && typeof runAnalytics === 'function') {
//     studentSel.addEventListener('change', runAnalytics);
//   }
// });
// </script>


// <!-- Accordion 1 Charts -->

// <!-- Performance over Time - Previous vs. Current Year (E,M,S) :: Chart 1 -->
// <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

// <!-- Safe embed: if data is missing, serialize {} instead of Undefined -->
// <script id="chart-perf-over-time" type="application/json">{{ data | default({}) | tojson | safe }}</script>

// <script>
//   const d = JSON.parse(document.getElementById('chart-perf-over-time').textContent);

//   // If d is empty ({}), provide sane fallbacks so Plotly won’t crash
//   const subjects = ["English","Maths","Science"];
//   const prev = [d.eng_prev ?? 0, d.maths_prev ?? 0, d.sci_prev ?? 0];
//   const curr = [d.eng_curr ?? 0, d.maths_curr ?? 0, d.sci_curr ?? 0];

//   // Colour current year bars: green if improved or equal, red if dropped
//   const currColors = curr.map((v,i) => v >= prev[i] ? "#9BEC00" : "#FF0060");

//   Plotly.newPlot("chart_perf_over_time", [
//     { x: subjects, y: prev, type:"bar", name:"Previous Academic Year",
//       marker:{ color:"#00CAFF" },
//       text: prev.map(v=>v.toFixed(1)), textposition:"outside" },
//     { x: subjects, y: curr, type:"bar", name:"Current Academic Year",
//       // apply conditional colours
//       marker:{ color: currColors, line:{ color:"#00000022", width:1 } },
//       text: curr.map(v=>v.toFixed(1)), textposition:"outside" }
//   ], {
//     autosize:true,
//     barmode:"group",
//     bargap:0.3, // space between groups
//     bargroupgap: 0.1, // space between bars in group
//     yaxis:{ title:"Average Marks", range:[0,110] },
//     margin:{ t:20, r:20, b:60, l:60 },
//     legend:{ orientation:"h" }
//   }, { displayModeBar:false, responsive:true });
// </script>

// <!-- Chart 2: Attainment -->
// <!-- Safe embed: if data is missing, serialize {} instead of Undefined -->
// <script id="chart-cohort-attainment" type="application/json">{{ threshold_data | default([]) | tojson | safe }}</script>

// <script>
//   // ------- ≥60 and ≥70 clustered bar -------
//   (function () {
//     const td = JSON.parse(document.getElementById('chart-cohort-attainment').textContent);

//     // ensure order English, Maths, Science
//     const subjects = ["English","Maths","Science"];
//     const idx = Object.fromEntries(subjects.map((s,i)=>[s,i]));
//     const ge60 = [0,0,0], ge70 = [0,0,0];

//     td.forEach(r => {
//       const i = idx[r.subject];
//       if (i !== undefined) {
//         ge60[i] = r.ge60 ?? 0;
//         ge70[i] = r.ge70 ?? 0;
//       }
//     });

//     const trace70 = {
//       x: subjects, y: ge70, type: "bar",
//       name: "% of Students Attaining above Curriculum Standard",
//       marker: { color: "#0073e5" },
//       text: ge70.map(v => v.toFixed(1) + "%"),
//       textposition: "outside",
//       hovertemplate: "%{x}<br>≥70: %{y:.1f}%<extra></extra>"
//     };

//     const trace60 = {
//       x: subjects, y: ge60, type: "bar",
//       name: "% of Students Attaining at & above Curriculum Standard",
//       marker: { color: "#7ddc1f" },
//       text: ge60.map(v => v.toFixed(1) + "%"),
//       textposition: "outside",
//       hovertemplate: "%{x}<br>≥60: %{y:.1f}%<extra></extra>"
//     };

//     Plotly.newPlot("chart_cohort_attainment", [trace70, trace60], {
//       autosize: true,
//       barmode: "stack",
//       barnorm: "percent",
//       bargap: 0.3,
//       bargroupgap: 0.1,
//       yaxis: { title: "Percent of Students", range: [0, 110] },
//       margin: { t: 20, r: 20, b: 60, l: 60 },
//       legend: { orientation: "h" }
//     }, { displayModeBar: false, responsive:true });
//   })();
// </script>

// <!-- Chart 3: Progress -->
// <script id="chart-cohort-progress" type="application/json">
//   {{ progress_simple_data | default([]) | tojson | safe }}
// </script>

// <script>
//   (function(){
//     const ps = JSON.parse(document.getElementById('chart-cohort-progress').textContent);

//     const subjects = ["English","Maths","Science"];
//     const pos = Object.fromEntries(subjects.map((s,i)=>[s,i]));

//     const sumExpectedAbove = [0,0,0]; // label 1: Expected + Above Expected
//     const aboveOnly        = [0,0,0]; // label 2: Above Expected only

//     ps.forEach(r => {
//       const i = pos[r.subject];
//       if (i !== undefined) {
//         sumExpectedAbove[i] = r.sum_expected_above ?? 0;
//         aboveOnly[i]        = r.above_only ?? 0;
//       }
//     });

//     const above_prog = {
//       x: subjects, y: aboveOnly, type:"bar",
//       name: "% of Students that made Better Progress",
//       marker:{ color:"#0073e5" },
//       text: aboveOnly.map(v=>v.toFixed(1)+"%"),
//       textposition:"outside",
//       hovertemplate: "%{x}<br>Above Only: %{y:.1f}%<extra></extra>"
//     };

//     const at_above_prog = {
//       x: subjects, y: sumExpectedAbove, type:"bar",
//       name: "% of Students that made Expected or Better Progress",
//       marker:{ color:"#7ddc1f" },
//       text: sumExpectedAbove.map(v=>v.toFixed(1)+"%"),
//       textposition:"outside",
//       hovertemplate: "%{x}<br>Expected or Above: %{y:.1f}%<extra></extra>"
//     };

//     Plotly.newPlot("chart_cohort_progress", [above_prog, at_above_prog], {
//       autosize:true,
//       barmode:"stack",
//       barnorm: "percent",
//       bargap:0.3,
//       bargroupgap:0.1,
//       yaxis:{ title:"Percent of Students", range:[0,110] },
//       margin:{ t:20, r:20, b:60, l:60 },
//       legend:{ orientation:"h" }
//     }, { displayModeBar:false, responsive:true });

//     const el = document.getElementById("chart_cohort_progress");
//     window.addEventListener("resize", () => Plotly.Plots.resize(el));
//     new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
//     document.addEventListener("shown.bs.tab", () => Plotly.Plots.resize(el));
//     document.addEventListener("shown.bs.collapse", () => Plotly.Plots.resize(el));
//   })();
// </script>

