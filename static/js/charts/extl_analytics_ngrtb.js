// js/charts/extl_analytics_ngrtb.js

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

  function setError(elId, msg = "Failed to load data.") {
    return setMessage(elId, `<p class="text-danger text-sm p-2 mb-0">${msg}</p>`);
  }

  function setEmpty(elId, msg = "No data available.") {
    return setMessage(elId, `<p class="text-muted text-sm text-warning fst-italic p-2 mb-0">${msg}</p>`);
  }

  // -----------------------------
  // Stanine pie renderer
  // -----------------------------
  async function renderStanineThresholdPie({
    elId,
    datasetKey = "ngrtb",
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

      const trace = {
        type: "pie",
        labels: [`Stanine ${threshold} and above`, `Stanine ${threshold - 1} and below`],
        values: [above, below],
        hole: 0.3,
        textinfo: "label+percent",
        marker: {
            colors: ['#A4CE95', '#FFDEB9'] // Custom colors for better distinction
        },
        hovertemplate:
            "<b>%{label}</b><br>" +
            "Students: %{value}<br>" +
            "Percentage: %{percent}" +
            "<extra></extra>"
      };

      const layout = {
        autosize: true,
        margin: { t: 30, r: 10, b: 60, l: 10 },
        showlegend: true,
        legend: {
          orientation: "h",
          y: -0.1,
          x: 0.5,
          xanchor: "center",
          yanchor: "top"
        }
      };

      Plotly.newPlot(elId, [trace], layout, { responsive: true });
    } catch (err) {
      console.error("Stanine pie error:", err);
      setError(elId);
    }
  }

  // ---------------------------------------------
  // Gender stanine bar renderer
  // ---------------------------------------------
  async function renderGenderStanineThresholdBar({
    elId,
    datasetKey = "ngrtb",
    stanineKey = "stanine",
    genderKey = "gender",
    threshold = 5
  }) {
    // If container missing, silently exit
    const container = document.getElementById(elId);
    if (!container) return;

    // loading placeholder
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
          marker: { color: "#FDEB9E" }
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
          marker: { color: "#FCB53B" }
        }
      ];

      const layout = {
        autosize: true,
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
  // Progress pie renderer
  // -----------------------------
  async function renderProgressCategoryPie({
    elId,
    datasetKey = "ngrtb",
    categoryKey = "progress_category",
    mode = "expected_plus" // "expected_plus" or "better_only"
  }) {
    // If container missing, silently exit
    const container = document.getElementById(elId);
    if (!container) return;
    
    // loading placeholder
    setLoading(elId);

    try {
      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elId);
        return;
      }

      let better = 0;
      let expected = 0;
      let lower = 0;

      for (const row of rows) {
        const raw = String(row?.[categoryKey] ?? "").trim();

        // Exclude any value containing '-' from ALL computations
        if (!raw || raw.includes("-")) continue;

        const cat = raw.toLowerCase();

        if (cat === "better than expected") better++;
        else if (cat === "expected") expected++;
        else if (cat === "lower than expected") lower++;
        // ignore anything else silently
      }

      // If nothing valid after filtering, show empty
      const totalValid = better + expected + lower;
      if (totalValid === 0) {
        setEmpty(elId, "No valid progress category values found.");
        return;
      }

      let labels, values;

      if (mode === "expected_plus") {
        labels = ["Expected & Better Progress", "Lower than Expected"];
        values = [expected + better, lower];
      } else if (mode === "better_only") {
        labels = ["Better Progress", "Expected & Lower than Expected"];
        values = [better, expected + lower];
      } else {
        setError(elId, "Invalid pie mode.");
        return;
      }

      const trace = {
        type: "pie",
        labels,
        values,
        hole: 0.3,
        textinfo: "label+percent",
        marker: { colors: ["#A4CE95", "#FFDEB9"] },
        hovertemplate:
          "<b>%{label}</b><br>" +
          "Students: %{value}<br>" +
          "Percentage: %{percent}" +
          "<extra></extra>"
      };

      const layout = {
        autosize: true,
        height: 360,
        margin: { t: 30, r: 10, b: 60, l: 10 },
        showlegend: true,
        legend: {
          orientation: "h",
          x: 0.5,
          xanchor: "center",
          y: -0.15,
          yanchor: "top"
        }
      };

      Plotly.newPlot(elId, [trace], layout, {displayModeBar: false, responsive: true });

    } catch (err) {
      console.error("Progress category pie error:", err);
      setError(elId);
    }
  }

  // -----------------------------
  // Public functions (window.*)
  // -----------------------------
  window.renderStanine5Pie = function (elId = "pie-st5-extl-ngrtb") {
    return renderStanineThresholdPie({
      elId,
      datasetKey: "ngrtb",
      stanineKey: "stanine",
      threshold: 5
    });
  };

  window.renderStanine6Pie = function (elId = "pie-st6-extl-ngrtb") {
    return renderStanineThresholdPie({
      elId,
      datasetKey: "ngrtb",
      stanineKey: "stanine",
      threshold: 6
    });
  };

  window.renderGenderStanine5Bar = function (elId = "bar-gender-st5-extl-ngrtb") {
    return renderGenderStanineThresholdBar({
      elId,
      datasetKey: "ngrtb",
      stanineKey: "stanine",
      genderKey: "gender",
      threshold: 5
    });
  };

  window.renderGenderStanine6Bar = function (elId = "bar-gender-st6-extl-ngrtb") {
    return renderGenderStanineThresholdBar({
      elId,
      datasetKey: "ngrtb",
      stanineKey: "stanine",
      genderKey: "gender",
      threshold: 6
    });
  };

  window.renderProgressExpectedPlusPie = function (elId = "pie-prog-exp-plus-extl-ngrtb") {
    return renderProgressCategoryPie({
      elId,
      datasetKey: "ngrtb",
      mode: "expected_plus"
    });
  };

  window.renderProgressBetterOnlyPie = function (elId = "pie-prog-better-extl-ngrtb") {
    return renderProgressCategoryPie({
      elId,
      datasetKey: "ngrtb",
      mode: "better_only"
    });
  };

  // one function to render graphs
  window.renderExternalNGRTPies = function () {
    // Attainment pies - Cohort
    window.renderStanine5Pie("pie-st5-extl-ngrtb");
    window.renderStanine6Pie("pie-st6-extl-ngrtb");
  
    // Attainment bars - gender-specific
    window.renderGenderStanine5Bar("bar-gender-st5-extl-ngrtb");
    window.renderGenderStanine6Bar("bar-gender-st6-extl-ngrtb");

    // Progress pies - cohort
    window.renderProgressExpectedPlusPie("pie-prog-exp-plus-extl-ngrtb");
    window.renderProgressBetterOnlyPie("pie-prog-better-extl-ngrtb");
  };

  // ---------------------------------------------
  // Render on page accordion display
  // ---------------------------------------------
  function wireAccordionRender() {
    const panel = document.getElementById("btn_extl_att");
    if (!panel) return;

    // If panel is already visible on load
    if (panel.classList.contains("show")) {
      window.renderExternalNGRTPies();
    }

    // Render when accordion opens
    panel.addEventListener("shown.bs.collapse", () => {
      window.renderExternalNGRTPies();
    });
  }

  // -----------------------------
  // Resize handling
  // -----------------------------
  function wireResize() {
  window.addEventListener("resize", () => {
    const ids = [
      "pie-st5-extl-ngrtb",
      "pie-st6-extl-ngrtb",
      "bar-gender-st5-extl-ngrtb",
      "bar-gender-st6-extl-ngrtb",
      "pie-prog-exp-plus-extl-ngrtb",
      "pie-prog-better-extl-ngrtb",
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