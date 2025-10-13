window.renderCohortProgress = function (elId = "chart_cohort_progress") {
  const ps = JSON.parse(document.getElementById("chart-cohort-progress")?.textContent || "[]");
  const subjects = ["English","Maths","Science"];
  const pos = Object.fromEntries(subjects.map((s,i)=>[s,i]));
  const sumExpectedAbove = [0,0,0], aboveOnly = [0,0,0];

  ps.forEach(r => {
    const i = pos[r.subject];
    if (i !== undefined) {
      sumExpectedAbove[i] = r.sum_expected_above ?? 0;
      aboveOnly[i]        = r.above_only ?? 0;
    }
  });

  Plotly.newPlot(elId, [
    { x: subjects, y: aboveOnly, type:"bar", name:"Students that made better progress",
      marker:{ color:"#0073e5" }, text: aboveOnly.map(v=>v.toFixed(1)+"%"), textposition:"outside" },
    { x: subjects, y: sumExpectedAbove, type:"bar", name:"Students that made expected or better progress",
      marker:{ color:"#7ddc1f" }, text: sumExpectedAbove.map(v=>v.toFixed(1)+"%"), textposition:"outside" }
  ], {
    autosize:true, barmode:"stack", barnorm:"percent",
    yaxis:{ title:"Percent of Students", range:[0,110] },
    margin:{ t:20, r:20, b:60, l:60 }, legend:{ orientation:"h" }
  }, { displayModeBar:false, responsive:true });

  const el = document.getElementById(elId);
  window.addEventListener("resize", () => Plotly.Plots.resize(el));
  new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
  document.addEventListener("shown.bs.tab", () => Plotly.Plots.resize(el));
  document.addEventListener("shown.bs.collapse", () => Plotly.Plots.resize(el));
};
