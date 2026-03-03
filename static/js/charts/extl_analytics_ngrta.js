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
    return setMessage(elId, `<p class="text-danger text-xs fst-italic p-2 mb-0">${msg}</p>`);
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
            colors: ['#03AED2', '#F5F1DC'] // Custom colors for better distinction
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

    // const trace = {
    //   type: "bar",
    //   x: labels,
    //   y: percentValues,
    //   text: percentValues.map(v => `${v.toFixed(1)}%`),
    //   textposition: "outside",
    //   hoverinfo: "text",
    //   hovertext: hoverText,
    //   marker: { color: ["#FDEB9E", "#FCB53B"] }
    // };
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
      margin: { t: 20, r: 20, b: 60, l: 60 },
      yaxis: { title: "Percent of Gender Total", ticksuffix: "%", range: [0, 100], rangemode: "tozero" },
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

  // Optional: one function to render BOTH pies
  window.renderExternalNgrtAttainmentPies = function () {
    // Cohort pies
    window.renderStanine5Pie("pie-st5-extl-ngrta");
    window.renderStanine6Pie("pie-st6-extl-ngrta");

    // Gender-specific bars
    window.renderGenderStanine5Bar("bar-gender-st5-extl-ngrta");
    window.renderGenderStanine6Bar("bar-gender-st6-extl-ngrta");
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
      "bar-gender-st6-extl-ngrta"
    ];

    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) Plotly.Plots.resize(el);
    }
  });
}
  // function wireResize() {
  //   window.addEventListener("resize", () => {
  //     const el5 = document.getElementById("pie-st5-extl-ngrta");
  //     const el6 = document.getElementById("pie-st6-extl-ngrta");

  //     if (el5) Plotly.Plots.resize(el5);
  //     if (el6) Plotly.Plots.resize(el6);
  //   });
  // }

  // Init
  document.addEventListener("DOMContentLoaded", () => {
    wireAccordionRender();
    wireResize();
  });
})();