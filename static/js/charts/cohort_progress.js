window.renderCohortProgress = function (elId = "chart_cohort_progress") {
  const ps = JSON.parse(document.getElementById("chart-cohort-progress")?.textContent || "[]");
  const subjects = ["English","Maths","Science"];
  const pos = Object.fromEntries(subjects.map((s,i)=>[s,i]));
  const sumExpectedAbove = [0,0,0], aboveOnly = [0,0,0];
  const cntExpectedAbove = [0,0,0], cntAboveOnly = [0,0,0];

  ps.forEach(r => {
    const i = pos[r.subject];
    if (i !== undefined) {
      sumExpectedAbove[i] = r.sum_expected_above ?? 0;
      aboveOnly[i]        = r.above_only ?? 0;
      cntExpectedAbove[i] = r.count_expected_above ?? 0;
      cntAboveOnly[i]     = r.count_above_only ?? 0;
    }
  });

  // const custom_AboveOnly = subjects.map((_, i) => [ge70_count[i], (n[i] ? (ge70_count[i]/n[i]*100) : ge70_pct[i])]);
  // const custom_sumExpectedAbove = subjects.map((_, i) => [ge60_count[i], (n[i] ? (ge60_count[i]/n[i]*100) : ge60_pct[i])]);

  Plotly.newPlot(
    elId,
    [
    { x: subjects, y: aboveOnly, type:"bar", name:"Students that made better progress",
      marker:{ color:"#0073e5" },
      text: aboveOnly.map(v=>v.toFixed(1)+"%"),
      // text: aboveOnly.map(v=> `${Number(v).toFixed(1)}%`),
      textposition:"outside",
      // hovertemplate: cntAboveOnly + text + " students"
    },
    { x: subjects, y: sumExpectedAbove, type:"bar", name:"Students that made expected or better progress",
      marker:{ color:"#7ddc1f" },
      // text: sumExpectedAbove.map(v=>v.toFixed(1)+"%"),
      text: sumExpectedAbove.map(v=> `${Number(v).toFixed(1)}%`),
      textposition:"outside",
      // hovertemplate: cntExpectedAbove + " students"
    }
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
