async function renderNGRTClasswiseProgressChart() {
  const res = await fetch("/api/ngrt_classwise_progress");
  const data = await res.json();

  const examLabel = data.exam_label || "NGRT";
  const yearGroups = data.year_groups || [];

  const lowerPct = data.lower_pct || [];
  const expectedPct = data.expected_pct || [];
  const betterPct = data.better_pct || [];

  const lowerCount = data.lower_count || [];
  const expectedCount = data.expected_count || [];
  const betterCount = data.better_count || [];
  const totals = data.totals || [];

  const labelEl = document.getElementById("ngrt-progress-exam-label");
  if (labelEl) {
    labelEl.textContent = examLabel;
  }

  const lowerCustom = lowerCount.map((count, i) => [count, totals[i] || 0]);
  const expectedCustom = expectedCount.map((count, i) => [count, totals[i] || 0]);
  const betterCustom = betterCount.map((count, i) => [count, totals[i] || 0]);

  const traces = [
    {
      x: yearGroups,
      y: lowerPct,
      customdata: lowerCustom,
      name: "Lower than Expected",
      type: "bar",
      marker: { color: "#FF5A5A" },
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
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Category: Better than Expected<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]} student(s)<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    }
  ];

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
    // margin: { t: 70, r: 20, b: 110, l: 60 }
    margin: { t: 30, r: 10, b: 50, l: 50 }
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  const el = document.getElementById("chart-ngrt-classwise-progress");

  if (el) {
    Plotly.newPlot(el, traces, layout, config);

    setTimeout(() => Plotly.Plots.resize(el), 100);
    window.addEventListener("resize", () => Plotly.Plots.resize(el));

    const ro = new ResizeObserver(() => Plotly.Plots.resize(el));
    ro.observe(el);
  }
}

document.addEventListener("DOMContentLoaded", renderNGRTClasswiseProgressChart);