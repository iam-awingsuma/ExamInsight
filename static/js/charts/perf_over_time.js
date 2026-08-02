// NO exports — attach to window
window.renderPerfOverTime = function (elId = "chart_perf_over_time") {
  // Parse JSON data from the chart container element, defaulting to an empty object if not found
  const d = JSON.parse(document.getElementById("chart-perf-over-time")?.textContent || "{}");
  // Define target subject labels array for tracking core academic progress
  const subjects = ["English","Maths","Science"];
  // Extract previous subject scores (English, Maths, Science) with fallback to 0
  const prev = [d.eng_prev ?? 0, d.maths_prev ?? 0, d.sci_prev ?? 0];
  // Extract current subject scores (English, Maths, Science) with fallback to 0
  const curr = [d.eng_curr ?? 0, d.maths_curr ?? 0, d.sci_curr ?? 0];
  // Determine colors based on whether current values are greater than or equal to previous values
  const currColors = curr.map((v,i) => v >= prev[i] ? "#A7E399" : "#FF0060");
  const deltas = curr.map((v,i) => +(v - prev[i]).toFixed(1));

  // Render the Plotly bar chart with grouped bars, average marks y-axis, and responsive layout
  // The chart displays previous and current academic year averages for English, Maths, and Science
  // with color-coded bars indicating improvement or decline, and hover tooltips showing detailed info.
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
