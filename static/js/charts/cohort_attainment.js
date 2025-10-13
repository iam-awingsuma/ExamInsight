window.renderCohortAttainment = function (elId = "chart_cohort_attainment") {
  const td = JSON.parse(document.getElementById("chart-cohort-attainment")?.textContent || "[]");
  const subjects = ["English","Maths","Science"];
  const idx = Object.fromEntries(subjects.map((s,i)=>[s,i]));
  const ge60 = [0,0,0], ge70 = [0,0,0];

  td.forEach(r => {
    const i = idx[r.subject];
    if (i !== undefined) { ge60[i] = r.ge60 ?? 0; ge70[i] = r.ge70 ?? 0; }
  });

  Plotly.newPlot(elId, [
    { x: subjects, y: ge70, type:"bar", name:"≥70% (Students above curriculum standard)",
      marker:{ color:"#0073e5" }, text: ge70.map(v=>v.toFixed(1)+"%"), textposition:"outside" },
    { x: subjects, y: ge60, type:"bar", name:"≥60% (Students at/above curriculum standard)",
      marker:{ color:"#7ddc1f" }, text: ge60.map(v=>v.toFixed(1)+"%"), textposition:"outside" }
  ], {
    autosize:true, barmode:"stack", barnorm:"percent",
    yaxis:{ title:"Percent of Students", range:[0,110] },
    margin:{ t:20, r:20, b:60, l:60 }, legend:{ orientation:"h" }
  }, { displayModeBar:false, responsive:true });
};