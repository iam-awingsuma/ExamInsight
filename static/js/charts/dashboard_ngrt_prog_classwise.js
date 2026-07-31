
async function renderNGRTClasswiseProgressChart() {
  // Fetch classwise progress data from backend API
  const res = await fetch("/api/ngrt_classwise_progress");
  // Parse response payload as JSON
  const data = await res.json();
  // Extract exam label fallback to "NGRT"
  const examLabel = data.exam_label || "NGRT";
  // Extract year groups array
  const yearGroups = data.year_groups || [];
  // Extract percentage metrics per progress category
  const lowerPct = data.lower_pct || [];
  const expectedPct = data.expected_pct || [];
  const betterPct = data.better_pct || [];
  // Extract student counts per progress category
  const lowerCount = data.lower_count || [];
  const expectedCount = data.expected_count || [];
  const betterCount = data.better_count || [];
  // Extract total student count array
  const totals = data.totals || [];
  // Update DOM element text with active exam label if present
  const labelEl = document.getElementById("ngrt-progress-exam-label");
  if (labelEl) {
    labelEl.textContent = examLabel;
  }
  // Map custom data tuples [category_count, total_students] for hover tooltips
  const lowerCustom = lowerCount.map((count, i) => [count, totals[i] || 0]);
  const expectedCustom = expectedCount.map((count, i) => [count, totals[i] || 0]);
  const betterCustom = betterCount.map((count, i) => [count, totals[i] || 0]);
  // Define Plotly stacked bar chart data series
  const traces = [
    {
      x: yearGroups,
      y: lowerPct,
      customdata: lowerCustom,
      name: "Lower than Expected",
      type: "bar",
      marker: { color: "#FF5A5A" },
      hoverlabel: {font: { size: 11 }},
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Category: Lower than Expected<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: expectedPct,
      customdata: expectedCustom,
      name: "Expected",
      type: "bar",
      marker: { color: "#FCB53B" },
      hoverlabel: {font: { size: 11 }},
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Category: Expected<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: betterPct,
      customdata: betterCustom,
      name: "Better than Expected",
      type: "bar",
      marker: { color: "#A7E399" },
      hoverlabel: {font: { size: 11 }},
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Category: Better than Expected<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    }
  ];
  // Configure chart layout dimensions, legend, and percentage scaling
  const layout = {
    autosize: true,
    width: null,
    barmode: "stack",
    yaxis: {
      title: "Percent of Students",
      range: [0, 100],
      ticksuffix: "%"
    },
    legend: {
      orientation: "h",
      x: 0,
      xanchor: "left",
      y: -0.2,
      font: { size: 11 }
    },
    margin: { t: 30, r: 10, b: 50, l: 50 }
  };
  // Set Plotly display options for responsiveness and toolbar visibility
  const config = {
    responsive: true,
    displayModeBar: false
  };
  // Target container element and render chart
  const el = document.getElementById("chart-ngrt-classwise-progress");

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
document.addEventListener("DOMContentLoaded", renderNGRTClasswiseProgressChart);