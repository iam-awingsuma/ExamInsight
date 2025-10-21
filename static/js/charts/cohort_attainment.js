window.renderCohortAttainment = function (elId = "chart_cohort_attainment") {
  // Parse payload embedded in the page
  const td = JSON.parse(document.getElementById("chart-cohort-attainment")?.textContent || "[]");

  const subjects = ["English","Maths","Science"];
  const idx = Object.fromEntries(subjects.map((s,i)=>[s,i]));

  // Arrays per subject
  const n          = new Array(subjects.length).fill(0);
  const ge60_pct   = new Array(subjects.length).fill(0);
  const ge70_pct   = new Array(subjects.length).fill(0);
  const ge60_count = new Array(subjects.length).fill(0);
  const ge70_count = new Array(subjects.length).fill(0);

  // Fill arrays from rows (support both snake_case keys shown below)
  td.forEach(r => {
    const i = idx[r.subject];
    if (i === undefined) return;

    n[i]          = Number(r.n ?? r.intake ?? 0);
    ge60_pct[i]   = Number(r.ge60 ?? 0);
    ge70_pct[i]   = Number(r.ge70 ?? 0);
    ge60_count[i] = Number(r.ge60_count ?? 0);
    ge70_count[i] = Number(r.ge70_count ?? 0);
  });

  const custom70 = subjects.map((_, i) => [ge70_count[i], (n[i] ? (ge70_count[i]/n[i]*100) : ge70_pct[i])]);
  const custom60 = subjects.map((_, i) => [ge60_count[i], (n[i] ? (ge60_count[i]/n[i]*100) : ge60_pct[i])]);

  const t70 = {
    x: subjects,
    y: ge70_count,
    type: "bar",
    name: "≥70 (Students above curriculum standard)",
    marker: { color: "#0073e5" },
    text: ge70_pct.map(v => `${Number(v).toFixed(1)}%`),   // label with total ≥70%
    textposition: "outside",
    customdata: custom70,
    hovertemplate: "(%{x}, %{customdata[0]:,d} students, %{customdata[1]:.1f}%)<extra>≥70% (above curriculum standard)</extra>"
  };

  const t60 = {
    x: subjects,
    y: ge60_count,
    type: "bar",
    name: "≥60 (Students at/above curriculum standard)",
    marker: { color: "#7ddc1f" },
    text: ge60_pct.map(v => `${Number(v).toFixed(1)}%`),   // label with total ≥60%
    textposition: "outside",
    customdata: custom60,
    hovertemplate: "(%{x}, %{customdata[0]:,d} students, %{customdata[1]:.1f}%)<extra>≥60% (at/above curriculum standard)</extra>"
  };

  Plotly.newPlot(
    elId,
    [t70, t60],
    {
      barmode: "stack",
      barnorm: "percent", // normalize counts to %
      yaxis: { title: "Percent of Students", range: [0, 110] },
      margin: { t: 20, r: 20, b: 60, l: 60 },
      legend: { orientation: "h" }
    },
    { displayModeBar: false, responsive: true }
  );
};