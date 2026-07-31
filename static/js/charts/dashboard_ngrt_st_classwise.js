async function renderNGRTClasswiseStanineChart() {
  // Fetch classwise stanine distribution data from backend API
  const res = await fetch("/api/ngrt_classwise_stanine");
  // Parse response payload as JSON
  const data = await res.json();

  // Extract year groups array for X-axis categories
  const yearGroups = data.year_groups || [];
  // Extract exam label fallback to "NGRT"
  const examLabel = data.exam_label || "NGRT";

  // Update DOM element text with active exam label if present
  const examLabelEl = document.getElementById("ngrt-st-exam-label");
  if (examLabelEl) {
    examLabelEl.textContent = examLabel;
  }

  // Extract percentage metrics per stanine band (Below Average, Average, Above Average)
  const belowPct = data.below_average_pct || [];
  const avgPct = data.average_pct || [];
  const abovePct = data.above_average_pct || [];

  // Extract student counts per stanine band
  const belowCount = data.below_average_count || [];
  const avgCount = data.average_count || [];
  const aboveCount = data.above_average_count || [];
  // Extract total student count array
  const totals = data.totals || [];

  // Map custom data tuples [band_count, total_students] for hover tooltips
  const belowCustom = belowCount.map((count, i) => [count, totals[i] || 0]);
  const avgCustom = avgCount.map((count, i) => [count, totals[i] || 0]);
  const aboveCustom = aboveCount.map((count, i) => [count, totals[i] || 0]);

  // Define Plotly stacked bar chart data series
  const traces = [
    {
      x: yearGroups,
      y: belowPct,
      customdata: belowCustom,
      name: "Below Average",
      type: "bar",
      marker: { color: "#FF5A5A" }, // Red bar styling
      hoverlabel: { font: { size: 11 } },
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Band: Below Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: avgPct,
      customdata: avgCustom,
      name: "Average",
      type: "bar",
      marker: { color: "#FCB53B" }, // Orange bar styling
      hoverlabel: { font: { size: 11 } },
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Band: Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: abovePct,
      customdata: aboveCustom,
      name: "Above Average",
      type: "bar",
      marker: { color: "#A7E399" }, // Green bar styling
      hoverlabel: { font: { size: 11 } },
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Band: Above Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    }
  ];

  // Configure chart layout dimensions, legend, and percentage scaling
  const layout = {
    autosize: true,
    width: null,
    barmode: "stack", // Enables stacked bar representation
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

  // Set Plotly display options
  const config = {
    responsive: true,
    displayModeBar: false
  };

  // Target container element and render chart
  const el = document.getElementById("chart-ngrt-classwise-stanine");

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
document.addEventListener("DOMContentLoaded", renderNGRTClasswiseStanineChart);