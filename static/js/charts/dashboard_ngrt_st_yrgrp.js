async function renderClasswiseAvgNGRTStanineChart() {
  // Fetch classwise average NGRT stanine data from backend API
  const res = await fetch("/api/classwise_avg_ngrt_stanine");
  // Parse response payload as JSON
  const data = await res.json();

  // Extract year groups array for X-axis categories
  const x = data.year_groups;
  // Extract series data list containing NGRT test variants
  const series = data.series || [];

  // Find individual test series data by name identifier
  const ngrta = series.find(s => s.name === "NGRT-A");
  const ngrtb = series.find(s => s.name === "NGRT-B");
  const ngrtc = series.find(s => s.name === "NGRT-C");

  // Define Plotly line trace for NGRT-A average stanines
  const ngrtaTrace = {
    x: x,
    y: ngrta ? ngrta.data : [],
    mode: "lines+markers",
    name: "NGRT-A",
    line: { color: "#0BA6DF", width: 3 }, // Blue line styling
    marker: { size: 8 },
    hoverlabel: { font: { size: 11 } },
    hovertemplate: "NGRT-A Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
  };

  // Define Plotly line trace for NGRT-B average stanines
  const ngrtbTrace = {
    x: x,
    y: ngrtb ? ngrtb.data : [],
    mode: "lines+markers",
    name: "NGRT-B",
    line: { color: "#FCB53B", width: 3 }, // Orange line styling
    marker: { size: 8 },
    hoverlabel: { font: { size: 11 } },
    hovertemplate: "NGRT-B Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
  };

  // Define Plotly line trace for NGRT-C average stanines
  const ngrtcTrace = {
    x: x,
    y: ngrtc ? ngrtc.data : [],
    mode: "lines+markers",
    name: "NGRT-C",
    line: { color: "#A7E399", width: 3 }, // Green line styling
    marker: { size: 8 },
    hoverlabel: { font: { size: 11 } },
    hovertemplate: "NGRT-C Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
  };

  // Configure chart layout dimensions, Y-axis scale (0-9 stanine scale), and legend
  const layout = {
    autosize: true,
    width: null,
    margin: { l: 70, r: 30, t: 20, b: 70 },
    yaxis: {
      title: "Average Stanine",
      range: [0, 9] // Sets Y-axis bounds to standard stanine range
    },
    hovermode: "x unified",
    legend: { orientation: "h", y: -0.2, font: { size: 11 } },
    font: { size: 12 }
  };

  // Set Plotly display options
  const config = {
    responsive: true,
    displayModeBar: false
  };

  // Target container element and render chart
  const el = document.getElementById("chart-classwise-avg-ngrt-stanine");

  if (el) {
    // Render plot in target container with all three NGRT series
    Plotly.newPlot(el, [ngrtaTrace, ngrtbTrace, ngrtcTrace], layout, config);

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
document.addEventListener("DOMContentLoaded", renderClasswiseAvgNGRTStanineChart);