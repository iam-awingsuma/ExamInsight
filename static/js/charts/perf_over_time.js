// NO exports — attach to window
window.renderPerfOverTime = function (elId = "chart_perf_over_time") {
  const d = JSON.parse(document.getElementById("chart-perf-over-time")?.textContent || "{}");
  const subjects = ["English","Maths","Science"];
  const prev = [d.eng_prev ?? 0, d.maths_prev ?? 0, d.sci_prev ?? 0];
  const curr = [d.eng_curr ?? 0, d.maths_curr ?? 0, d.sci_curr ?? 0];
  const currColors = curr.map((v,i) => v >= prev[i] ? "#A7E399" : "#FF0060");
  const deltas = curr.map((v,i) => +(v - prev[i]).toFixed(1));

  Plotly.newPlot(elId, [
    { x: subjects, y: prev, type:"bar", name:"Previous Academic Year",
      marker:{ color:"#0BA6DF" }, text: prev.map(v=>v.toFixed(1)), textposition:"outside",
      hovertemplate:
        "<b>%{x}</b><br>" +
        "Previous AY Avg: %{y:.1f}<extra></extra>"
    },
    { x: subjects, y: curr, type:"bar", name:"Current Academic Year",
      marker:{ color: currColors }, text: curr.map(v=>v.toFixed(1)), textposition:"outside",
      customdata: deltas, // pass deltas into the tooltip
      hovertemplate:
        "<b>%{x}</b><br>" +
        "Current AY Avg: %{y:.1f}<br>" +
        "Δ vs Previous: %{customdata:+.1f} pts<extra></extra>"
    }
  ], {
    autosize:true, barmode:"group", bargap:0.3, bargroupgap:0.1,
    yaxis:{ title:"Average Marks", range:[0,110] },
    margin:{ t:20, r:20, b:60, l:60 }, legend:{ orientation:"h", },
    hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
    hovermode:"x unified"
  }, { displayModeBar:false, responsive:true });
};
