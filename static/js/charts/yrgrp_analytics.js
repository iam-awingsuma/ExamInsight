// Year Group: Average Attainment Comparison Chart
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
        "2-F": "#DC3C22",
        "Cohort": "#065084" // default fallback
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
    .catch(err => console.error("[yrgrp_analytics] Fetch error:", err));
};

// Year Group: Attainment Comparison Chart ≥60
window.yrgrp_analytics60 = function (elId = "chart_yrgrp_analytics60") {
  // Fetch data from backend API
  fetch("/api/yrgrp_analytics")
    .then(r => r.json())
    .then(td => {
      if (!td.subjects || !td.by_class) {
        console.error("[yrgrp_analytics60] Invalid payload", td);
        return;
      }

      const subjects = td.subjects; // ["English", "Maths", "Science"]
      const order = ["2-A","2-B","2-C","2-D","2-E","2-F","Cohort"];

      // Fast lookup by class name
      const byName = Object.fromEntries(td.by_class.map(r => [r.class, r]));

      // % ≥60 helper that handles Cohort's different keys
      const pct60 = (rec, subjKey) => {
        if (!rec) return 0;
        if (rec.class === "Cohort") {
          const k = subjKey === "eng" ? "engC60_pct" : subjKey === "maths" ? "mathsC60_pct" : "sciC60_pct";
          return Number(rec[k] ?? 0);
        }
        return Number(rec[`${subjKey}60_pct`] ?? 0);
      };

      // Define a color for each class / trace name
      const colorMap = {
        "2-A": "#9656a2",
        "2-B": "#369acc",
        "2-C": "#95cf92",
        "2-D": "#f8e16f",
        "2-E": "#F8961e",
        "2-F": "#DC3C22",
        "Cohort": "#065084" // default fallback
      };

      // Build traces from by_class (%≥60 per subject)
      const traces = order
      .map(name => byName[name])
      .filter(Boolean)
      .map(rec => {
        const y = [
          pct60(rec, "eng"), pct60(rec, "maths"), pct60(rec, "sci")
        ];
        return {
          x: subjects,
          y,
          type: "bar",
          name: rec.class,
          marker: {
            color: colorMap[rec.class] || "#90be6d",
            // opacity: rec.class === "Cohort" ? 0.5 : 0.95
          },
          text: y.map(v => `${Number(v).toFixed(1)}%`),
          textposition: "outside",
          hovertemplate: "%{y:.1f}%<extra><b>" + rec.class + "</b></extra>"
        };
      });

      Plotly.newPlot(
        elId,
        traces,
        {
          autosize: true,
          barmode: "group",
          yaxis: { title: "Percent of Students", range: [0, 110] },
          margin: { t: 20, r: 20, b: 60, l: 60 },
          legend: { orientation: "h", y: -0.2 },
          hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
          hovermode:"x unified"
        },
        { displayModeBar: false, responsive: true }
      );

      // --- Responsive handling ---
      const el = document.getElementById(elId);
      if (el) {
        const resize = () => Plotly.Plots.resize(el);
        window.addEventListener("resize", resize);
        new ResizeObserver(resize).observe(el);
        document.addEventListener("shown.bs.tab", resize);
        document.addEventListener("shown.bs.collapse", resize);
      }
    })
    .catch(err => console.error("[yrgrp_analytics60] Fetch error:", err));
};

// Year Group: Attainment Comparison Chart ≥70
window.yrgrp_analytics70 = function (elId = "chart_yrgrp_analytics70") {
  // Fetch data from backend API
  fetch("/api/yrgrp_analytics")
    .then(r => r.json())
    .then(td => {
      if (!td.subjects || !td.by_class) {
        console.error("[yrgrp_analytics70] Invalid payload", td);
        return;
      }

      const subjects = td.subjects; // ["English", "Maths", "Science"]
      const order = ["2-A","2-B","2-C","2-D","2-E","2-F","Cohort"];

      // Fast lookup by class name
      const byName = Object.fromEntries(td.by_class.map(r => [r.class, r]));

      // % ≥70 helper that handles Cohort's different keys
      const pct70 = (rec, subjKey) => {
        if (!rec) return 0;
        if (rec.class === "Cohort") {
          const k = subjKey === "eng" ? "engC70_pct" : subjKey === "maths" ? "mathsC70_pct" : "sciC70_pct";
          return Number(rec[k] ?? 0);
        }
        return Number(rec[`${subjKey}70_pct`] ?? 0);
      };

      // Define a color for each class / trace name
      const colorMap = {
        "2-A": "#9656a2",
        "2-B": "#369acc",
        "2-C": "#95cf92",
        "2-D": "#f8e16f",
        "2-E": "#F8961e",
        "2-F": "#DC3C22",
        "Cohort": "#065084" // default fallback
      };

      // Build traces from by_class (%≥60 per subject)
      const traces = order
      .map(name => byName[name])
      .filter(Boolean)
      .map(rec => {
        const y = [
          pct70(rec, "eng"), pct70(rec, "maths"), pct70(rec, "sci")
        ];
        return {
          x: subjects,
          y,
          type: "bar",
          name: rec.class,
          marker: {
            color: colorMap[rec.class] || "#90be6d",
            // opacity: rec.class === "Cohort" ? 0.5 : 0.95
          },
          text: y.map(v => `${Number(v).toFixed(1)}%`),
          textposition: "outside",
          hovertemplate: "%{y:.1f}%<extra><b>" + rec.class + "</b></extra>"
        };
      });

      Plotly.newPlot(
        elId,
        traces,
        {
          autosize: true,
          barmode: "group",
          yaxis: { title: "Percent of Students", range: [0, 110] },
          margin: { t: 20, r: 20, b: 60, l: 60 },
          legend: { orientation: "h", y: -0.2 },
          hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
          hovermode:"x unified"
        },
        { displayModeBar: false, responsive: true }
      );

      // --- Responsive handling ---
      const el = document.getElementById(elId);
      if (el) {
        const resize = () => Plotly.Plots.resize(el);
        window.addEventListener("resize", resize);
        new ResizeObserver(resize).observe(el);
        document.addEventListener("shown.bs.tab", resize);
        document.addEventListener("shown.bs.collapse", resize);
      }
    })
    .catch(err => console.error("[yrgrp_analytics70] Fetch error:", err));
};