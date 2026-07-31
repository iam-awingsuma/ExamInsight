async function renderNGRTClasswiseThresholdChart() {
  // Fetch classwise reading threshold metrics from backend API
  const res = await fetch("/api/ngrt_classwise_reading_thresholds");
  // Parse response payload as JSON
  const data = await res.json();

  // Extract exam label fallback to "NGRT"
  const examLabel = data.exam_label || "NGRT";
  // Extract year groups array for X-axis categories
  const x = data.year_groups || [];

  // Extract percentage metrics per threshold category (SAS ≥90, ≥110, ≥120)
  const sas90Pct = data.sas_90_pct || [];
  const sas110Pct = data.sas_110_pct || [];
  const sas120Pct = data.sas_120_pct || [];

  // Extract student counts per threshold category
  const sas90Count = data.sas_90_count || [];
  const sas110Count = data.sas_110_count || [];
  const sas120Count = data.sas_120_count || [];
  // Extract total student count array
  const totals = data.totals || [];

  // Update DOM element text with active exam label if present
  const examLabelEl = document.getElementById("ngrt-threshold-exam-label");
  if (examLabelEl) {
    examLabelEl.textContent = examLabel;
  }

  // Map custom data tuples [category_count, total_students] for hover tooltips
  const sas90Custom = sas90Count.map((count, i) => [count, totals[i] || 0]);
  const sas110Custom = sas110Count.map((count, i) => [count, totals[i] || 0]);
  const sas120Custom = sas120Count.map((count, i) => [count, totals[i] || 0]);

  // Define Plotly grouped bar trace for SAS ≥ 90
  const sas90Trace = {
    x: x,
    y: sas90Pct,
    customdata: sas90Custom,
    type: "bar",
    name: "SAS ≥90",
    marker: { color: "#89D4FF" },
    hoverlabel: {font: { size: 11 }},
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥90: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  // Define Plotly grouped bar trace for SAS ≥ 110
  const sas110Trace = {
    x: x,
    y: sas110Pct,
    customdata: sas110Custom,
    type: "bar",
    name: "SAS ≥110",
    marker: { color: "#44ACFF" },
    hoverlabel: {font: { size: 11 }},
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥110: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  // Define Plotly grouped bar trace for SAS ≥ 120
  const sas120Trace = {
    x: x,
    y: sas120Pct,
    customdata: sas120Custom,
    type: "bar",
    name: "SAS ≥120",
    marker: { color: "#5478FF" },
    hoverlabel: {font: { size: 11 }},
    hovertemplate:
      "<b>Year %{x}</b><br>" +
      "SAS ≥120: <b>%{y:.1f}%</b><br>" +
      "Count: <b>%{customdata[0]}</b> student(s)<br>" +
      "Total: <b>%{customdata[1]}</b> student(s)<extra></extra>",
  };

  // Combine traces into a single data array
  const traces = [sas90Trace, sas110Trace, sas120Trace];

  // Configure chart layout dimensions, legend, unified hover, and grouped bar mode
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
      y: -0.2,
      font: { size: 11 }
    },
    font: { size: 12 },
    hovermode: "x unified",
    margin: { l: 70, r: 30, t: 20, b: 70 },
    bargap: 0.15,
    bargroupgap: 0.05
  };

  // Set Plotly display options for responsiveness and toolbar visibility
  const config = {
    responsive: true,
    displayModeBar: false
  };

  // Target container element and render chart
  const el = document.getElementById("chart-ngrt-classwise-thresholds");

  if (el) {
    // Render plot in target container
    Plotly.newPlot(el, traces, layout, config);

    // Initial resize trigger after DOM paint delay
    setTimeout(() => Plotly.Plots.resize(el), 100);
    // Listen to window resize events to keep chart responsive
    window.addEventListener("resize", () => Plotly.Plots.resize(el));

    // Observe element-level container dimensions for responsive adjustments
    const ro = new ResizeObserver(() => Plotly.Plots.resize(el));
    ro.observe(el);
  }
}

// Execute chart initialization once DOM tree is fully loaded
document.addEventListener("DOMContentLoaded", renderNGRTClasswiseThresholdChart);