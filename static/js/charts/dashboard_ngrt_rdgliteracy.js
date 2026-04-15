async function renderNGRTClasswiseThresholdChart() {
  const res = await fetch("/api/ngrt_classwise_reading_thresholds");
  const data = await res.json();

  const examLabel = data.exam_label || "NGRT";
  const x = data.year_groups || [];

  const sas90Pct = data.sas_90_pct || [];
  const sas110Pct = data.sas_110_pct || [];
  const sas120Pct = data.sas_120_pct || [];

  const sas90Count = data.sas_90_count || [];
  const sas110Count = data.sas_110_count || [];
  const sas120Count = data.sas_120_count || [];
  const totals = data.totals || [];

  const examLabelEl = document.getElementById("ngrt-threshold-exam-label");
  if (examLabelEl) {
    examLabelEl.textContent = examLabel;
  }

  const sas90Custom = sas90Count.map((count, i) => [count, totals[i] || 0]);
  const sas110Custom = sas110Count.map((count, i) => [count, totals[i] || 0]);
  const sas120Custom = sas120Count.map((count, i) => [count, totals[i] || 0]);

  const sas90Trace = {
    x: x,
    y: sas90Pct,
    customdata: sas90Custom,
    type: "bar",
    name: "SAS ≥90",
    marker: { color: "#89D4FF" },
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥90: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  const sas110Trace = {
    x: x,
    y: sas110Pct,
    customdata: sas110Custom,
    type: "bar",
    name: "SAS ≥110",
    marker: { color: "#44ACFF" },
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥110: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  const sas120Trace = {
    x: x,
    y: sas120Pct,
    customdata: sas120Custom,
    type: "bar",
    name: "SAS ≥120",
    marker: { color: "#5478FF" },
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥120: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  const traces = [sas90Trace, sas110Trace, sas120Trace];

  const layout = {
    autosize: true,
    width: null,
    barmode: "group",
    yaxis: {
      title: "Percent of Students",
      range: [0, 100],
      ticksuffix: "%"
    },
    legend: {
      orientation: "h",
      xanchor: "left",
      y: -0.2
    },
    font: { size: 13 },
    hovermode: "x unified",
    margin: { l: 70, r: 30, t: 20, b: 70 },
    bargap: 0.15,
    bargroupgap: 0.05
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  const el = document.getElementById("chart-ngrt-classwise-thresholds");

  if (el) {
    Plotly.newPlot(el, traces, layout, config);

    setTimeout(() => Plotly.Plots.resize(el), 100);
    window.addEventListener("resize", () => Plotly.Plots.resize(el));

    const ro = new ResizeObserver(() => Plotly.Plots.resize(el));
    ro.observe(el);
  }
}

document.addEventListener("DOMContentLoaded", renderNGRTClasswiseThresholdChart);