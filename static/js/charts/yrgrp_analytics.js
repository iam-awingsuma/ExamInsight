window.yrgrp_analytics = function (elId = "chart_yrgrp_analytics") {
  // Fetch data from backend API
  fetch("/api/yrgrp_analytics")
    .then(r => r.json())
    .then(td => {
      if (!td.subjects || !td.traces) {
        console.error("[yrgrp_analytics] Invalid payload", td);
        return;
      }

      const subjects = td.subjects;

      // Define a color for each class / trace name
      const colorMap = {
        "2-A": "#9656a2",
        "2-B": "#369acc",
        "2-C": "#95cf92",
        "2-D": "#f8e16f",
        "2-E": "#f4895f",
        "2-F": "#de324c",
        "Cohort": "#577590" // default fallback
      };

      // Create traces for Plotly (bars per class + cohort)
      const traces = td.traces.map(r => ({
        x: subjects,
        y: r.y.map(v => Number(v ?? 0)),
        type: "bar",
        name: r.name,
        marker: {
          color: colorMap[r.name] || "#90be6d",   // fallback green
          // opacity: r.isCohort ? 0.5 : 0.9 // lighter for cohort
        },
        text: r.y.map(v => `${Number(v).toFixed(1)}`),
        textposition: "outside",
        hovertemplate: "%{x}: %{y:.1f}%<extra>" + r.name + "</extra>"
      }));

      Plotly.newPlot(
        elId,
        traces,
        {
          autosize: true,
          barmode: "group",
          yaxis: { title: "Average Attainment", range: [0, 110] },
          margin: { t: 20, r: 20, b: 60, l: 60 },
          legend: { orientation: "h", y: -0.2 },
          hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
          hovermode:"x unified"
        },
        { displayModeBar: false, responsive: true }
      );

      // --- Responsive handling ---
      const el = document.getElementById(elId);
      window.addEventListener("resize", () => Plotly.Plots.resize(el));
      new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
      document.addEventListener("shown.bs.tab", () => Plotly.Plots.resize(el));
      document.addEventListener("shown.bs.collapse", () => Plotly.Plots.resize(el));
    })
    .catch(err => console.error("[renderYrgrpAnalytics] Fetch error:", err));
};
