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
        "2-E": "#F8961e",
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
        hovertemplate: "<b>"+r.name+"</b>: %{y:.1f}<extra></extra>"
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

      // --- Render data table below the chart ---
      const tableContainer = document.getElementById("tbl_yrgrp_analytics");
      if (tableContainer) {

        // Define per-subject column colors
        const colColors = {
          English:  "#d6ecff", // light blue
          Maths:    "#ffe8cc", // light orange
          Science:  "#e5f9e0"  // light green
        };
        
        let html = `
          <table class="table table-responsive table-tight table-sm text-xs text-center align-middle w-100 mb-0">
            <thead class="table-light">
              <tr>
                <th>Class / Cohort</th>
                ${subjects.map(s => `<th style="background:${colColors[s] || '#fff'}">${s}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              ${td.traces.map(t => `
                <tr ${t.isCohort ? "style='font-weight:bold;background:#f9f9f9;'" : ""}>
                  <td>${t.name}</td>
                  ${t.y.map(v => `<td>${Number(v).toFixed(1)}</td>`).join("")}
                </tr>`).join("")}
            </tbody>
          </table>
        `;
        tableContainer.innerHTML = html;
      }
    })
    .catch(err => console.error("[renderYrgrpAnalytics] Fetch error:", err));
};
