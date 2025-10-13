// NO exports — attach to window
window.renderPerfOverTime = function (elId = "chart_perf_over_time") {
  const d = JSON.parse(document.getElementById("chart-perf-over-time")?.textContent || "{}");
  const subjects = ["English","Maths","Science"];
  const prev = [d.eng_prev ?? 0, d.maths_prev ?? 0, d.sci_prev ?? 0];
  const curr = [d.eng_curr ?? 0, d.maths_curr ?? 0, d.sci_curr ?? 0];
  const currColors = curr.map((v,i) => v >= prev[i] ? "#9BEC00" : "#FF0060");

  Plotly.newPlot(elId, [
    { x: subjects, y: prev, type:"bar", name:"Previous Academic Year",
      marker:{ color:"#00CAFF" }, text: prev.map(v=>v.toFixed(1)), textposition:"outside" },
    { x: subjects, y: curr, type:"bar", name:"Current Academic Year",
      marker:{ color: currColors, line:{ color:"#00000022", width:1 } },
      text: curr.map(v=>v.toFixed(1)), textposition:"outside" }
  ], {
    autosize:true, barmode:"group", bargap:0.3, bargroupgap:0.1,
    yaxis:{ title:"Average Marks", range:[0,110] },
    margin:{ t:20, r:20, b:60, l:60 }, legend:{ orientation:"h" }
  }, { displayModeBar:false, responsive:true });
};
