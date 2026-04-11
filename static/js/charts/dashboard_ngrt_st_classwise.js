async function renderNGRTClasswiseStanineChart() {
  const res = await fetch("/api/ngrt_classwise_stanine");
  const data = await res.json();

  const yearGroups = data.year_groups || [];
  const examLabel = data.exam_label || "NGRT";

  const examLabelEl = document.getElementById("ngrt-exam-label");
  if (examLabelEl) {
    examLabelEl.textContent = examLabel;
  }

  const belowPct = data.below_average_pct || [];
  const avgPct = data.average_pct || [];
  const abovePct = data.above_average_pct || [];

  const belowCount = data.below_average_count || [];
  const avgCount = data.average_count || [];
  const aboveCount = data.above_average_count || [];
  const totals = data.totals || [];

  const belowCustom = belowCount.map((count, i) => [count, totals[i] || 0]);
  const avgCustom = avgCount.map((count, i) => [count, totals[i] || 0]);
  const aboveCustom = aboveCount.map((count, i) => [count, totals[i] || 0]);

  const traces = [
    {
      x: yearGroups,
      y: belowPct,
      customdata: belowCustom,
      name: "Below Average",
      type: "bar",
      marker: { color: "#FF5A5A" },
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
      marker: { color: "#FCB53B" },
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
      marker: { color: "#A7E399" },
      hovertemplate:
        "<b>Year %{x}</b><br>" +
        "Band: Above Average<br>" +
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
      x: 0.4,
      xanchor: "center",
      y: -0.12,
    //   y: 1.12 // legend above the chart
    },
    // margin: { t: 70, r: 20, b: 60, l: 60 }
    margin: { t: 30, r: 10, b: 50, l: 50 }
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  const el = document.getElementById("chart-ngrt-classwise-stanine");

  if (el) {
    Plotly.newPlot(el, traces, layout, config);

    setTimeout(() => Plotly.Plots.resize(el), 100);
    window.addEventListener("resize", () => Plotly.Plots.resize(el));

    const ro = new ResizeObserver(() => Plotly.Plots.resize(el));
    ro.observe(el);
  }
}

document.addEventListener("DOMContentLoaded", renderNGRTClasswiseStanineChart);