async function renderNGRTClasswiseStanineChart() {
  const res = await fetch("/api/ngrt_classwise_stanine");
  const data = await res.json();

  const yearGroups = data.year_groups || [];
  const examLabel = data.exam_label || "NGRT";

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
      marker: { color: "#dc3545" },
      hovertemplate:
        "<b>%{x}</b><br>" +
        "Band: Below Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]}<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: avgPct,
      customdata: avgCustom,
      name: "Average",
      type: "bar",
      marker: { color: "#fd7e14" },
      hovertemplate:
        "<b>%{x}</b><br>" +
        "Band: Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]}<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    },
    {
      x: yearGroups,
      y: abovePct,
      customdata: aboveCustom,
      name: "Above Average",
      type: "bar",
      marker: { color: "#28a745" },
      hovertemplate:
        "<b>%{x}</b><br>" +
        "Band: Above Average<br>" +
        "Percentage: %{y:.1f}%<br>" +
        "Count: %{customdata[0]}<br>" +
        "Total Students: %{customdata[1]}<extra></extra>"
    }
  ];

  const layout = {
    title: `${examLabel} Classwise Stanine Distribution`,
    barmode: "stack",
    xaxis: {
      title: "Year Group"
    },
    yaxis: {
      title: "Percentage of Students",
      range: [0, 100],
      ticksuffix: "%"
    },
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: 1.12
    },
    margin: { t: 70, r: 20, b: 60, l: 60 }
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  Plotly.newPlot("chart-ngrt-classwise-stanine", traces, layout, config);
}

document.addEventListener("DOMContentLoaded", renderNGRTClasswiseStanineChart);