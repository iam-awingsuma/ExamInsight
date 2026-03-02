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
    return setMessage(elId, `<p class="text-muted text-xs fst-italic p-2 mb-0">Loading...</p>`);
  }

  function setError(elId, msg = "Failed to load data.") {
    return setMessage(elId, `<p class="text-danger text-xs p-2 mb-0">${msg}</p>`);
  }

  function setEmpty(elId, msg = "No data available.") {
    return setMessage(elId, `<p class="text-muted text-xs fst-italic p-2 mb-0">${msg}</p>`);
  }

  // -----------------------------
  // Generic stanine pie renderer
  // -----------------------------
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

      const trace = {
        type: "pie",
        labels: [`Stanine ${threshold} and above`, `Stanine ${threshold - 1} and below`],
        values: [above, below],
        hole: 0.3,
        textinfo: "label+percent",
        marker: {
            colors: ['#4B9DA9', '#F5F1DC'] // Custom colors for better distinction
        },
        hovertemplate:
            "<b>%{label}</b><br>" +
            "Students: %{value}<br>" +
            "Percentage: %{percent}" +
            "<extra></extra>"
      };

      const layout = {
        margin: { t: 10, r: 10, b: 10, l: 10 },
        showlegend: true
      };

      Plotly.newPlot(elId, [trace], layout, { responsive: true });
    } catch (err) {
      console.error("Stanine pie error:", err);
      setError(elId);
    }
  }

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

  // Optional: one function to render BOTH pies
  window.renderExternalNgrtAttainmentPies = function () {
    window.renderStanine5Pie("pie-st5-extl-ngrta");
    window.renderStanine6Pie("pie-st6-extl-ngrta");
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
      const el5 = document.getElementById("pie-st5-extl-ngrta");
      const el6 = document.getElementById("pie-st6-extl-ngrta");

      if (el5) Plotly.Plots.resize(el5);
      if (el6) Plotly.Plots.resize(el6);
    });
  }

  // Init
  document.addEventListener("DOMContentLoaded", () => {
    wireAccordionRender();
    wireResize();
  });
})();