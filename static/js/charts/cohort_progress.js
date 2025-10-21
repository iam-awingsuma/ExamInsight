window.renderCohortProgress = function (elId = "chart_cohort_progress") {
  // Parse payload embedded in the page
  const td = JSON.parse(document.getElementById("chart-cohort-progress")?.textContent || "[]");
  const subjects = ["English","Maths","Science"];
  const idx = Object.fromEntries(subjects.map((s,i)=>[s,i]));

  // Arrays per subject
  const n                   = new Array(subjects.length).fill(0);
  const sumExpectedAbove    = new Array(subjects.length).fill(0);
  const aboveOnly           = new Array(subjects.length).fill(0);
  const cntExpectedAbove    = new Array(subjects.length).fill(0);
  const cntAboveOnly        = new Array(subjects.length).fill(0);

  // Fill arrays from rows (support both snake_case keys shown below)
  td.forEach(r => {
    const i = idx[r.subject];
    if (i === undefined) return;

    n[i]                  = Number(r.n ?? r.intake ?? 0);
    sumExpectedAbove[i]   = Number(r.sum_expected_above ?? 0);
    aboveOnly[i]          = Number(r.above_only ?? 0);
    cntExpectedAbove[i]   = Number(r.count_exp_above ?? 0);
    cntAboveOnly[i]       = Number(r.count_above_only ?? 0);
  });

  const customAboveOnly = subjects.map((_, i) => [cntAboveOnly[i], (n[i] ? (cntAboveOnly[i]/n[i]*100) : aboveOnly[i])]);
  const customExpectedAbove = subjects.map((_, i) => [cntExpectedAbove[i], (n[i] ? (cntExpectedAbove[i]/n[i]*100) : sumExpectedAbove[i])]);

  const tAboveOnly = {
    x: subjects,
    y: cntAboveOnly,
    type: "bar",
    name: "Students that made better progress",
    marker: { color: "#0073e5" },
    text: aboveOnly.map(v => `${Number(v).toFixed(1)}%`),
    textposition: "outside",
    customdata: customAboveOnly,
    hovertemplate: "(%{x}, %{customdata[0]:,d} students, %{customdata[1]:.1f}%)<extra>made better progress</extra>"
  };

  const tExpectedAbove = {
    x: subjects,
    y: cntExpectedAbove,
    type: "bar",
    name: "Students that made expected or better progress",
    marker: { color: "#7ddc1f" },
    text: sumExpectedAbove.map(v => `${Number(v).toFixed(1)}%`),
    textposition: "outside",
    customdata: customExpectedAbove,
    hovertemplate: "(%{x}, %{customdata[0]:,d} students, %{customdata[1]:.1f}%)<extra>made expected or better progress</extra>"
  };

  Plotly.newPlot(
    elId,
    [tAboveOnly, tExpectedAbove],
    {
      autosize: true, barmode: "stack", barnorm: "percent", // normalize counts to %
      yaxis: { title: "Percent of Students", range: [0, 110] },
      margin: { t: 20, r: 20, b: 60, l: 60 }, legend: { orientation: "h" }
    }, { displayModeBar: false, responsive: true });
  
  const el = document.getElementById(elId);
  window.addEventListener("resize", () => Plotly.Plots.resize(el));
  new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
  document.addEventListener("shown.bs.tab", () => Plotly.Plots.resize(el));
  document.addEventListener("shown.bs.collapse", () => Plotly.Plots.resize(el));

};