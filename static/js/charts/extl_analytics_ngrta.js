// js/charts/extl_analytics_ngrta.js

(() => {
  // ---------------------------------------------
  // API Cache (fetch once for both charts)
  // ---------------------------------------------
  let _extNgrtCache = null;

  async function getExtNgrtPayload() {
    if (_extNgrtCache) return _extNgrtCache;

    const res = await fetch("/api/analytics_extl_ngrt", {
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    });

    if (!res.ok) throw new Error(`API error: ${res.status}`);
    _extNgrtCache = await res.json();
    return _extNgrtCache;
  }

  // -------------------------------------------------------------
  // Small UI helpers: add loading, error, empty states
  // -------------------------------------------------------------
  function setMessage(elId, html) {
    const el = document.getElementById(elId);
    if (!el) return false;
    el.innerHTML = html;
    return true;
  }

  function setLoading(elId) {
    return setMessage(elId, `<p class="text-muted text-sm fst-italic p-2 mb-0">Loading...</p>`);
  }

  function setError(elId, msg = "Failed to load data") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
  }

  function setEmpty(elId, msg = "No data available") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
  }

  // -----------------------------
  // Cohort Insights Graphs
  // -----------------------------

  // Cohort stanine pie renderer
  async function renderStanineThresholdPie({
    elId,
    datasetKey = "ngrta",
    stanineKey = "stanine",
    threshold = 5
  }) {
    // If container missing, silently exit
    const container = document.getElementById(elId);
    if (!container) return;

    // Loading placeholder
    setLoading(elId);

    try {
      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elId);
        return;
      }

      let above = 0;
      let below = 0;

      for (const row of rows) {
        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;
        if (s >= threshold) above++;
        else below++;
      }

      // If no valid stanine values found:
      if (above === 0 && below === 0) {
        setEmpty(elId, "No valid stanine values found.");
        return;
      }

      const el = document.getElementById(elId);
      if (!el) return;

      // clear "Loading..." or any placeholder HTML
      el.innerHTML = "";

      const trace = {
        type: "pie",
        labels: [`Stanine ${threshold} and above`, `Stanine ${threshold - 1} and below`],
        values: [above, below],
        hole: 0.3,
        textinfo: "label+percent",
        marker: {
            colors: ['#67C6E3', '#F5F1DC'] // Custom colors for better distinction
        },
        hovertemplate:
            "<b>%{label}</b><br>" +
            "Students: %{value}<br>" +
            "Percentage: %{percent}" +
            "<extra></extra>"
      };

      const layout = {
        margin: { t: 30, r: 10, b: 60, l: 10 },
        showlegend: true,
        autosize: true,
        legend: {
          orientation: "h",
          y: -0.1,
          x: 0.5,
          xanchor: "center",
          yanchor: "top"
        }
      };

      Plotly.newPlot(elId, [trace], layout, { responsive: true })
      .then(() => {
        const gd = document.getElementById(elId);
        Plotly.Plots.resize(gd);
        setTimeout(() => Plotly.Plots.resize(gd), 150);
      });
    } catch (err) {
      console.error("Stanine pie error:", err);
      setError(elId);
    }
  }

  // Generic gender stanine bar renderer
  async function renderGenderStanineThresholdBar({
    elId,
    datasetKey = "ngrta",
    stanineKey = "stanine",
    genderKey = "gender",
    threshold = 5
  }) {
    const container = document.getElementById(elId);
    if (!container) return;

    setLoading(elId);

    try {
      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elId);
        return;
      }

      // Denominators (all students by gender)
      let maleTotal = 0;
      let femaleTotal = 0;

      // Numerators (students >= threshold by gender)
      let maleMeet = 0;
      let femaleMeet = 0;

      for (const row of rows) {
        const gRaw = String(row?.[genderKey] ?? "").trim().toLowerCase();
        const isMale = (gRaw === "m" || gRaw === "male");
        const isFemale = (gRaw === "f" || gRaw === "female");
        if (!isMale && !isFemale) continue;

        if (isMale) maleTotal++;
        if (isFemale) femaleTotal++;

        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;

        if (s >= threshold) {
          if (isMale) maleMeet++;
          if (isFemale) femaleMeet++;
        }
      }

      if (maleTotal === 0 && femaleTotal === 0) {
        setEmpty(elId, "No valid gender values found.");
        return;
      }

      const labels = ["Male", "Female"];
      const totals = [maleTotal, femaleTotal];
      const meets = [maleMeet, femaleMeet];

      const percentValues = meets.map((v, i) => (totals[i] ? (v / totals[i]) * 100 : 0));

      const hoverText = labels.map((lbl, i) =>
        `${lbl}: ${meets[i]}/${totals[i]} students (${percentValues[i].toFixed(1)}%)`
      );

      const el = document.getElementById(elId);
      if (!el) return;

      // clear "Loading..." or any placeholder HTML
      el.innerHTML = "";

      const traces = [
        {
          type: "bar",
          x: ["Male"],
          y: [percentValues[0]],
          name: "Male",
          text: [`${percentValues[0].toFixed(1)}%`],
          textposition: "outside",
          hoverinfo: "text",
          hovertext: [hoverText[0]],
          marker: { color: "#FDEB9E" },
          width: 0.6,
        },
        {
          type: "bar",
          x: ["Female"],
          y: [percentValues[1]],
          name: "Female",
          text: [`${percentValues[1].toFixed(1)}%`],
          textposition: "outside",
          hoverinfo: "text",
          hovertext: [hoverText[1]],
          marker: { color: "#FCB53B" },
          width: 0.6,
        }
      ];

      const layout = {
        margin: { t: 30, r: 20, b: 60, l: 60 },
        yaxis: { title: "Percent of Gender Total", ticksuffix: "%", range: [0, 110], rangemode: "tozero" },
        xaxis: { title: "" },
        showlegend: true,
        hovermode: "x unified",
        legend: { orientation: "h" },
      };

      Plotly.newPlot(elId, traces, layout, { displayModeBar: false, responsive: true });
    } catch (err) {
      console.error("Gender bar error:", err);
      setError(elId);
    }
  }

  // -----------------------------
  // Year Group Insights Graphs
  // -----------------------------

  // Bar graph renderer External NGRTA - Year Group Insights
  // at/above curriculum standards (St5 & above) and
  // at least level above curriculum standards (St6 & above)
  // async function renderYearGroupStanineThresholdBar({
  //   elId,
  //   datasetKey = "ngrta",
  //   stanineKey = "stanine",
  //   yrgrpKey = "yrgrp",
  //   threshold = 5
  // }) {
  //   const container = document.getElementById(elId);
  //   if (!container) return;

  //   setLoading(elId);

  //   try {
  //     const payload = await getExtNgrtPayload();
  //     const rows = payload?.[datasetKey] || [];

  //     if (!Array.isArray(rows) || rows.length === 0) {
  //       setEmpty(elId);
  //       return;
  //     }

  //     // Denominators (all students by year group)
  //     let yr2ATotal = 0, yr2BTotal = 0, yr2CTotal = 0, yr2DTotal = 0, yr2ETotal = 0, yr2FTotal = 0;
  //     let cohortTotal = 0;

  //     // Numerators (students >= threshold by year group)
  //     let yr2AMeet = 0, yr2BMeet = 0, yr2CMeet = 0, yr2DMeet = 0, yr2EMeet = 0, yr2FMeet = 0;
  //     let cohortMeet = 0;

  //     for (const row of rows) {
  //       const yrgrpRaw = String(row?.[yrgrpKey] ?? "").trim().toLowerCase();
  //       const is2A = (yrgrpRaw === "2-a"), is2B = (yrgrpRaw === "2-b"), is2C = (yrgrpRaw === "2-c"),
  //             is2D = (yrgrpRaw === "2-d"), is2E = (yrgrpRaw === "2-e"), is2F = (yrgrpRaw === "2-f");
        
  //       if (!is2A && !is2B && !is2C && !is2D && !is2E && !is2F) continue;

  //       // total counts for each year group
  //       if (is2A) yr2ATotal++;
  //       if (is2B) yr2BTotal++;
  //       if (is2C) yr2CTotal++;
  //       if (is2D) yr2DTotal++;
  //       if (is2E) yr2ETotal++;
  //       if (is2F) yr2FTotal++;

  //       // total count for cohort (all year groups)
  //       cohortTotal++;

  //       const s = Number(row?.[stanineKey]);
  //       if (!Number.isFinite(s)) continue;

  //       if (s >= threshold) {
  //         if (is2A) yr2AMeet++;
  //         if (is2B) yr2BMeet++;
  //         if (is2C) yr2CMeet++;
  //         if (is2D) yr2DMeet++;
  //         if (is2E) yr2EMeet++;
  //         if (is2F) yr2FMeet++;

  //         // cohort count for students meeting threshold
  //         cohortMeet++;
  //       }
  //     }

  //     if (yr2ATotal === 0 && yr2BTotal === 0 && yr2CTotal === 0 && yr2DTotal === 0 && yr2ETotal === 0 && yr2FTotal === 0) {
  //       setEmpty(elId, "No valid year group values found");
  //       return;
  //     }

  //     const labels = ["2-A", "2-B", "2-C", "2-D", "2-E", "2-F", "Cohort"];
  //     const colorMap = {
  //       "2-A": "#F3A1B4", "2-B": "#C8DBAC", "2-C": "#FBE8AF",
  //       "2-D": "#B8EAEF", "2-E": "#D2CBF6", "2-F": "#E6978B",
  //       "Cohort": "#5DA3D4" // default fallback
  //     };
  //     const totals = [yr2ATotal, yr2BTotal, yr2CTotal, yr2DTotal, yr2ETotal, yr2FTotal, cohortTotal];
  //     const meets = [yr2AMeet, yr2BMeet, yr2CMeet, yr2DMeet, yr2EMeet, yr2FMeet, cohortMeet];

  //     const percentValues = meets.map((v, i) => (totals[i] ? (v / totals[i]) * 100 : 0));

  //     const tableBody = document.getElementById("tbl-yrgrp-st5-extl-ngrta");
  //     if (tableBody) {
  //       tableBody.innerHTML = labels.map((label, i) => `
  //         <tr class="text-center">
  //           <th scope="row">${label}</th>
  //           <td class="table-light">${totals[i]}</td>
  //           <td class="table-info">${meets[i]}</td>
  //           <td class="table-success">${percentValues[i].toFixed(1)}%</td>
  //         </tr>
  //       `).join("");
  //     }

  //     const hoverText = labels.map((lbl, i) =>
  //       `${lbl}: ${meets[i]}/${totals[i]} students (${percentValues[i].toFixed(1)}%)`
  //     );

  //     const el = document.getElementById(elId);
  //     if (!el) return;

  //     // clear "Loading..." or any placeholder HTML
  //     el.innerHTML = "";

  //     const traces = labels.map((label, i) => ({
  //       type: "bar",
  //       x: [label],
  //       y: [percentValues[i]],
  //       name: label,
  //       text: [`${percentValues[i].toFixed(1)}%`],
  //       textposition: "outside",
  //       hoverinfo: "text",
  //       hovertext: [hoverText[i]],
  //       marker: { color: colorMap[label] },
  //     }));

  //     const layout = {
  //       autosize:true, barmode:"group",
  //       yaxis: { title: "Percent of Students", ticksuffix: "%", range: [0, 110], rangemode: "tozero" },
  //       margin: { t: 30, r: 20, b: 60, l: 60 },
  //       showlegend: true,
  //       legend: { orientation: "h", y: -0.2},
  //       hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
  //       hovermode: "x unified",
  //     };

  //     Plotly.newPlot(elId, traces, layout, { displayModeBar: false, responsive: true })
  //     .then(() => {
  //       const gd = document.getElementById(elId);
  //       Plotly.Plots.resize(gd);
  //       setTimeout(() => Plotly.Plots.resize(gd), 150);
  //     });
  //   } catch (err) {
  //     console.error("Year Group bar error:", err);
  //     setError(elId);
  //   }
  // }

  async function renderYearGroupStanineThresholdBars({
  elId5,
  elId6,
  datasetKey = "ngrta",
  stanineKey = "stanine",
  yrgrpKey = "yrgrp"
  }) {

    // const thresholds = { 5: {}, 6: {} };

    const container5 = document.getElementById(elId5);
    const container6 = document.getElementById(elId6);
    if (!container5 || !container6) return;

    setLoading(elId5);
    setLoading(elId6);

    try {

      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elId5);
        setEmpty(elId6);
        return;
      }

      const yrGroups = ["2-A","2-B","2-C","2-D","2-E","2-F"];

      const totals = {
        "2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0
      };

      const meets5 = {...totals};
      const meets6 = {...totals};

      for (const row of rows) {

        const yrgrpRaw = String(row?.[yrgrpKey] ?? "").trim().toUpperCase();
        if (!yrGroups.includes(yrgrpRaw)) continue;

        totals[yrgrpRaw]++;
        totals["Cohort"]++;

        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;

        if (s >= 5) {
          meets5[yrgrpRaw]++;
          meets5["Cohort"]++;
        }

        if (s >= 6) {
          meets6[yrgrpRaw]++;
          meets6["Cohort"]++;
        }
      }

      const labels = [...yrGroups,"Cohort"];

      const colorMap = {
        "2-A":"#F3A1B4",
        "2-B":"#C8DBAC",
        "2-C":"#FBE8AF",
        "2-D":"#B8EAEF",
        "2-E":"#D2CBF6",
        "2-F":"#E6978B",
        "Cohort":"#5DA3D4"
      };

      function renderGraph(elId, meets, threshold){

        const percentValues = labels.map(l =>
          totals[l] ? (meets[l]/totals[l])*100 : 0
        );

        const hoverText = labels.map(l =>
          `${l}: ${meets[l]}/${totals[l]} students (${percentValues[labels.indexOf(l)].toFixed(1)}%)`
        );

        const traces = labels.map((label,i)=>({
          type:"bar",
          x:[label],
          y:[percentValues[i]],
          name:label,
          text:[`${percentValues[i].toFixed(1)}%`],
          textposition:"outside",
          hoverinfo:"text",
          hovertext:[hoverText[i]],
          marker:{color:colorMap[label]}
        }));

        const layout = {
          title:`Students ≥ Stanine ${threshold}`,
          autosize:true,
          barmode:"group",
          yaxis:{
            title:"Percent of Students",
            ticksuffix:"%",
            range:[0,110]
          },
          margin:{t:40,r:20,b:60,l:60},
          showlegend:true,
          legend:{orientation:"h",y:-0.2},
          hovermode:"x unified"
        };

        Plotly.newPlot(elId,traces,layout,{displayModeBar:false,responsive:true});
      }

      function renderTable(tblId, meets){

        const percentValues = labels.map(l =>
          totals[l] ? (meets[l]/totals[l])*100 : 0
        );

        const tableBody = document.getElementById(tblId);
        if (!tableBody) return;

        tableBody.innerHTML = labels.map((label,i)=>`
          <tr class="text-center">
            <th scope="row">${label}</th>
            <td class="table-light">${totals[label]}</td>
            <td class="table-info">${meets[label]}</td>
            <td class="table-success">${percentValues[i].toFixed(1)}%</td>
          </tr>
        `).join("");
      }

      // ---------- Render STANINE 5 ----------
      renderGraph(elId5,meets5,5);
      renderTable("tbl-yrgrp-st5-extl-ngrta",meets5);

      // ---------- Render STANINE 6 ----------
      renderGraph(elId6,meets6,6);
      renderTable("tbl-yrgrp-st6-extl-ngrta",meets6);

    }

    catch(err){
      console.error("Stanine combined error:",err);
      setError(elId5);
      setError(elId6);
    }
  }

  // ---------------------------------------------------
  // Resize Plotly charts when Bootstrap tabs/collapse open
  // ---------------------------------------------------
  document.addEventListener("shown.bs.tab", function () {
    [
      "pie-st5-extl-ngrta", "pie-st6-extl-ngrta",
      "bar-gender-st5-extl-ngrta","bar-gender-st6-extl-ngrta",
      "bar-yrgrp-st5-extl-ngrta", "bar-yrgrp-st6-extl-ngrta"
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  document.addEventListener("shown.bs.collapse", function () {
    [
      "pie-st5-extl-ngrta", "pie-st6-extl-ngrta",
      "bar-gender-st5-extl-ngrta","bar-gender-st6-extl-ngrta",
      "bar-yrgrp-st5-extl-ngrta","bar-yrgrp-st6-extl-ngrta"
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  // -----------------------------
  // Public functions (window.*)
  // -----------------------------
  window.renderStanine5Pie = function (elId = "pie-st5-extl-ngrta") {
    return renderStanineThresholdPie({
      elId,
      datasetKey: "ngrta",
      stanineKey: "stanine",
      threshold: 5
    });
  };

  window.renderStanine6Pie = function (elId = "pie-st6-extl-ngrta") {
    return renderStanineThresholdPie({
      elId,
      datasetKey: "ngrta",
      stanineKey: "stanine",
      threshold: 6
    });
  };

  window.renderGenderStanine5Bar = function (elId = "bar-gender-st5-extl-ngrta") {
    return renderGenderStanineThresholdBar({
      elId,
      datasetKey: "ngrta",
      stanineKey: "stanine",
      genderKey: "gender",
      threshold: 5
    });
  };

  window.renderGenderStanine6Bar = function (elId = "bar-gender-st6-extl-ngrta") {
    return renderGenderStanineThresholdBar({
      elId,
      datasetKey: "ngrta",
      stanineKey: "stanine",
      genderKey: "gender",
      threshold: 6
    });
  };

  window.renderYearGroupStanineBars = function () {
    return renderYearGroupStanineThresholdBars({
      elId5: "bar-yrgrp-st5-extl-ngrta",
      elId6: "bar-yrgrp-st6-extl-ngrta"
    });
  };

  // one function to render BOTH pies
  window.renderExternalNgrtAttainmentPies = function () {
    // Cohort pies
    window.renderStanine5Pie("pie-st5-extl-ngrta");
    window.renderStanine6Pie("pie-st6-extl-ngrta");

    // Gender-specific bars
    window.renderGenderStanine5Bar("bar-gender-st5-extl-ngrta");
    window.renderGenderStanine6Bar("bar-gender-st6-extl-ngrta");

    // Year group bars
    window.renderYearGroupStanineBars();
  };

  // ---------------------------------------------
  // Render on page accordion display
  // ---------------------------------------------
  function wireAccordionRender() {
    const panel = document.getElementById("btn_extl_att");
    if (!panel) return;

    // If panel is already visible on load
    if (panel.classList.contains("show")) {
      window.renderExternalNgrtAttainmentPies();
    }

    // Render when accordion opens
    panel.addEventListener("shown.bs.collapse", () => {
      window.renderExternalNgrtAttainmentPies();
    });
  }

  // -----------------------------
  // Resize handling
  // -----------------------------
  function wireResize() {
  window.addEventListener("resize", () => {
    const ids = [
      "pie-st5-extl-ngrta",
      "pie-st6-extl-ngrta",
      "bar-gender-st5-extl-ngrta",
      "bar-gender-st6-extl-ngrta",
      "bar-yrgrp-st5-extl-ngrta",
      "bar-yrgrp-st6-extl-ngrta"
    ];

    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) Plotly.Plots.resize(el);
    }
  });
}

  // Init
  document.addEventListener("DOMContentLoaded", () => {
    wireAccordionRender();
    wireResize();
  });
})();