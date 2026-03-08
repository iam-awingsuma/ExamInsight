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

  function setError(elId, msg = "Failed to load data") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
  }

  function setEmpty(elId, msg = "No data available") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
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

      Plotly.newPlot(elId, [trace], layout, { responsive: true })
      .then(() => {
        const gd = document.getElementById(elId);
        // resize immediately
        Plotly.Plots.resize(gd);
        // resize after 150ms to handle any Bootstrap animation/layout changes
        setTimeout(() => Plotly.Plots.resize(gd), 150);
      });
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
        autosize: true,
        margin: { t: 30, r: 20, b: 60, l: 60 },
        yaxis: { title: "Percent of Gender Total", ticksuffix: "%", range: [0, 110], rangemode: "tozero" },
        xaxis: { title: "" },
        showlegend: true,
        hovermode: "x unified",
        legend: { orientation: "h" },
      };

      Plotly.newPlot(elId, traces, layout, { displayModeBar: false, responsive: true })
      .then(() => {
        const gd = document.getElementById(elId);
        // resize immediately
        Plotly.Plots.resize(gd);
        // resize after 150ms to handle any Bootstrap animation/layout changes
        setTimeout(() => Plotly.Plots.resize(gd), 150);
      });
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
        labels = ["Expected & Better Progress", "Below Expected"];
        values = [expected + better, lower];
      } else if (mode === "better_only") {
        labels = ["Better Progress", "Expected & Below Expected"];
        values = [better, expected + lower];
      } else {
        setError(elId, "Invalid pie mode.");
        return;
      }

      const el = document.getElementById(elId);
      if (!el) return;

      // clear "Loading..." or any placeholder HTML
      el.innerHTML = "";

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

      Plotly.newPlot(elId, [trace], layout, {displayModeBar: false, responsive: true })
      .then(() => {
        const gd = document.getElementById(elId);
        // resize immediately
        Plotly.Plots.resize(gd);
        // resize after 150ms to handle any Bootstrap animation/layout changes
        setTimeout(() => Plotly.Plots.resize(gd), 150);
      });
    } catch (err) {
      console.error("Progress category pie error:", err);
      setError(elId);
    }
  }

  // -------------------------------------------------------------
  // Bar renderer for gender-specific progress over time
  // Denominator counts ONLY rows with progress_category !== "-"
  // -------------------------------------------------------------
  async function renderGenderProgressBars({
    elIdExpectedPlus,
    elIdBetterOnly,
    datasetKey = "ngrtb",
    categoryKey = "progress_category",
    genderKey = "gender"
  }) {
    const c1 = elIdExpectedPlus ? document.getElementById(elIdExpectedPlus) : null;
    const c2 = elIdBetterOnly ? document.getElementById(elIdBetterOnly) : null;
    if (!c1 && !c2) return;

    if (c1) setLoading(elIdExpectedPlus);
    if (c2) setLoading(elIdBetterOnly);

    try {
      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        if (c1) setEmpty(elIdExpectedPlus);
        if (c2) setEmpty(elIdBetterOnly);
        return;
      }

      // ------------------------------------------------
      // Denominators (ONLY valid progress_category != "-")
      // ------------------------------------------------
      let maleTotal = 0;
      let femaleTotal = 0;

      // ------------------------------------------------
      // Numerators
      // ------------------------------------------------
      let maleBetter = 0;
      let femaleBetter = 0;

      let maleExpectedPlus = 0;
      let femaleExpectedPlus = 0;

      for (const row of rows) {
        // PROGRESS FILTER (denominator rule)
        const rawCat = String(row?.[categoryKey] ?? "").trim();
        if (!rawCat || rawCat === "-") continue; // ONLY exclude literal "-"

        const cat = rawCat.toLowerCase();

        // GENDER
        const gRaw = String(row?.[genderKey] ?? "").trim().toLowerCase();
        const isMale = (gRaw === "m" || gRaw === "male");
        const isFemale = (gRaw === "f" || gRaw === "female");
        if (!isMale && !isFemale) continue;

        // ----------------------------
        // Denominator (valid progress only)
        // ----------------------------
        if (isMale) maleTotal++;
        if (isFemale) femaleTotal++;

        // ----------------------------
        // Better than expected
        // ----------------------------
        if (cat === "better than expected") {
          if (isMale) maleBetter++;
          if (isFemale) femaleBetter++;
        }

        // ----------------------------
        // Expected + Better
        // ----------------------------
        if (cat === "expected" || cat === "better than expected") {
          if (isMale) maleExpectedPlus++;
          if (isFemale) femaleExpectedPlus++;
        }
      }

      if (maleTotal === 0 && femaleTotal === 0) {
        if (c1) setEmpty(elIdExpectedPlus, "No valid gender rows with progress_category != '-' found.");
        if (c2) setEmpty(elIdBetterOnly, "No valid gender rows with progress_category != '-' found.");
        return;
      }

      function buildBar(elId, title, maleCount, femaleCount) {
        const el = document.getElementById(elId);
        if (!el) return;

        // clear "Loading..." or any placeholder HTML
        el.innerHTML = "";

        const totals = [maleTotal, femaleTotal];
        const counts = [maleCount, femaleCount];
        const labels = ["Male", "Female"];

        const pct = counts.map((v, i) => (totals[i] ? (v / totals[i]) * 100 : 0));

        const hoverText = labels.map((lbl, i) =>
          `${lbl}: ${counts[i]}/${totals[i]} students (${pct[i].toFixed(1)}%)`
        );

        const traces = [
          {
            type: "bar",
            x: ["Male"],
            y: [pct[0]],
            name: "Male",
            text: [`${pct[0].toFixed(1)}%`],
            textposition: "outside",
            cliponxaxis: false,
            hoverinfo: "text",
            hovertext: [hoverText[0]],
            marker: { color: "#FDEB9E" },
            width: 0.6,
          },
          {
            type: "bar",
            x: ["Female"],
            y: [pct[1]],
            name: "Female",
            text: [`${pct[1].toFixed(1)}%`],
            textposition: "outside",
            cliponxaxis: false,
            hoverinfo: "text",
            hovertext: [hoverText[1]],
            marker: { color: "#FCB53B" },
            width: 0.6,
          }
        ];

        const layout = {
          autosize: true,
          height: 360,
          margin: { t: 30, r: 10, b: 60, l: 10 },
          yaxis: {
            title: "Percent of Gender Total",
            ticksuffix: "%",
            range: [0, 110],
            rangemode: "tozero",
            automargin: true,
          },
          xaxis: { title: "", automargin: true },
          showlegend: true,
          hovermode: "x unified",
          legend: {
            orientation: "h",
            x: 0.2,
            xanchor: "center",
            y: -0.15,
            yanchor: "top"
          },
        };

        Plotly.newPlot(elId, traces, layout, { displayModeBar: false, responsive: true })
        .then(() => {
          const gd = document.getElementById(elId);
          // resize immediately
          Plotly.Plots.resize(gd);
          // resize after 150ms to handle any Bootstrap animation/layout changes
          setTimeout(() => Plotly.Plots.resize(gd), 150);
        });
      }

      // Graph 1: Expected + Better
      if (c1) {
        buildBar(
          elIdExpectedPlus,
          "Expected + Better Than Expected (by Gender)",
          maleExpectedPlus,
          femaleExpectedPlus
        );
      }

      // Graph 2: Better Only
      if (c2) {
        buildBar(
          elIdBetterOnly,
          "Better Than Expected Only (by Gender)",
          maleBetter,
          femaleBetter
        );
      }

    } catch (err) {
      console.error("Gender bars error:", err);
      if (c1) setError(elIdExpectedPlus);
      if (c2) setError(elIdBetterOnly);
    }
  }

  // -------------------------------------------------------------
  // Year Group Insights Graphs - Attainment by Stanine Thresholds
  // -------------------------------------------------------------

  // Bar graph renderer External NGRTB - Year Group Insights
  // at/above curriculum standards (St5 & above) and
  // at least level above curriculum standards (St6 & above)
  async function renderYearGroupStanineThresholdBars({
  elId5,
  elId6,
  datasetKey = "ngrtb",
  stanineKey = "stanine",
  yrgrpKey = "yrgrp"
  }) {

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
        "2-A":"#F3A1B4", "2-B":"#C8DBAC", "2-C":"#FBE8AF",
        "2-D":"#B8EAEF", "2-E":"#D2CBF6", "2-F":"#E6978B",
        "Cohort":"#5DA3D4"
      };

      function renderGraph(elId, meets, threshold){

        const el = document.getElementById(elId);
        if (!el) return;

        // remove "Loading..." placeholder
        el.innerHTML = "";

        const percentValues = labels.map(l =>
          totals[l] ? (meets[l]/totals[l])*100 : 0
        );

        const hoverText = labels.map(l =>
          `${l}: ${meets[l]}/${totals[l]} students (${percentValues[labels.indexOf(l)].toFixed(1)}%)`
        );

        const traces = labels.map((label,i)=>({
          type:"bar", x:[label], y:[percentValues[i]],
          name:label,
          text:[`${percentValues[i].toFixed(1)}%`],
          textposition:"outside",
          hoverinfo:"text", hovertext:[hoverText[i]],
          marker:{color:colorMap[label]}
        }));

        const layout = {
          autosize:true, barmode:"group",
          bargap: 0, bargroupgap: 0.1,
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

        Plotly.newPlot(elId,traces,layout,{displayModeBar:false,responsive:true})
        .then(() => {
          const gd = document.getElementById(elId);
          // resize immediately
          Plotly.Plots.resize(gd);
          // resize after 150ms to handle any Bootstrap animation/layout changes
          setTimeout(() => Plotly.Plots.resize(gd), 150);
        });
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
      renderTable("tbl-yrgrp-st5-extl-ngrtb",meets5);

      // ---------- Render STANINE 6 ----------
      renderGraph(elId6,meets6,6);
      renderTable("tbl-yrgrp-st6-extl-ngrtb",meets6);

    }

    catch(err){
      console.error("Stanine combined error:",err);
      setError(elId5);
      setError(elId6);
    }
  }

  // Bar graph renderer External NGRTB - Year Group Insights
  // Gender-specific | Stanine 5 & above only
  async function renderYearGroupStanine5GenderBars({
    elIdMale,
    elIdFemale,
    datasetKey = "ngrtb",
    stanineKey = "stanine",
    yrgrpKey = "yrgrp",
    genderKey = "gender"
  }) {

    const containerMale = document.getElementById(elIdMale);
    const containerFemale = document.getElementById(elIdFemale);
    if (!containerMale || !containerFemale) return;

    setLoading(elIdMale);
    setLoading(elIdFemale);

    try {

      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elIdMale);
        setEmpty(elIdFemale);
        return;
      }

      const yrGroups = ["2-A","2-B","2-C","2-D","2-E","2-F"];

      function buildCounters(){
        return {
          totals: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0},
          meets: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0}
        };
      }

      const male = buildCounters();
      const female = buildCounters();

      for (const row of rows) {

        const yrgrpRaw = String(row?.[yrgrpKey] ?? "").trim().toUpperCase();
        const genderRaw = String(row?.[genderKey] ?? "").trim().toLowerCase();

        if (!yrGroups.includes(yrgrpRaw)) continue;

        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;

        const group = genderRaw === "male" ? male :
                      genderRaw === "female" ? female : null;

        if (!group) continue;

        group.totals[yrgrpRaw]++;
        group.totals["Cohort"]++;

        if (s >= 5) {
          group.meets[yrgrpRaw]++;
          group.meets["Cohort"]++;
        }
      }

      const labels = [...yrGroups,"Cohort"];

      const colorMap = {
        "2-A":"#F3A1B4","2-B":"#C8DBAC","2-C":"#FBE8AF",
        "2-D":"#B8EAEF","2-E":"#D2CBF6","2-F":"#E6978B",
        "Cohort":"#5DA3D4"
      };

      function renderGraph(elId, data, title){

        const el = document.getElementById(elId);
        if (!el) return;

        el.innerHTML = "";

        const percentValues = labels.map(l =>
          data.totals[l] ? (data.meets[l]/data.totals[l])*100 : 0
        );

        const hoverText = labels.map(l =>
          `${l}: ${data.meets[l]}/${data.totals[l]} students (${percentValues[labels.indexOf(l)].toFixed(1)}%)`
        );

        const traces = labels.map((label,i)=>({
          type:"bar",
          x:[label],
          y:[percentValues[i]],
          name:label,
          text:[`${percentValues[i].toFixed(1)}%`],
          textposition:"outside",
          hovertext:[hoverText[i]],
          hoverinfo:"text",
          marker:{color:colorMap[label]}
        }));

        const layout = {
          title:"",
          autosize:true,
          barmode: "group",
          bargap: 0,
          bargroupgap: 0.1,
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

        Plotly.newPlot(elId,traces,layout,{displayModeBar:false,responsive:true})
        .then(() => {
          const gd = document.getElementById(elId);
          Plotly.Plots.resize(gd);
          setTimeout(() => Plotly.Plots.resize(gd),150);
        });
      }

      function renderGenderYearGroupTable(tblId, data){
        const percentValues = labels.map(l =>
          data.totals[l] ? (data.meets[l] / data.totals[l]) * 100 : 0
        );

        const tableBody = document.getElementById(tblId);
        if (!tableBody) return;

        tableBody.innerHTML = labels.map((label,i)=>`
          <tr class="text-center">
            <th scope="row">${label}</th>
            <td class="table-light">${data.totals[label]}</td>
            <td class="table-info">${data.meets[label]}</td>
            <td class="table-success">${percentValues[i].toFixed(1)}%</td>
          </tr>
        `).join("");

      }

      // --------- Render Table & Graphs ---------
      renderGraph(elIdMale, male);
      renderGenderYearGroupTable("tbl-yrgrp-male-st5-extl-ngrtb", male);

      renderGraph(elIdFemale, female);
      renderGenderYearGroupTable("tbl-yrgrp-female-st5-extl-ngrtb", female);
    }

    catch(err){
      console.error("Gender Year Group Stanine5 error:",err);
      setError(elIdMale);
      setError(elIdFemale);
    }
  }

  // Bar graph renderer External NGRTB - Year Group Insights
  // Gender-specific | Stanine 6 & above only
  async function renderYearGroupStanine6GenderBars({
    elIdMale,
    elIdFemale,
    datasetKey = "ngrtb",
    stanineKey = "stanine",
    yrgrpKey = "yrgrp",
    genderKey = "gender"
  }) {

    const containerMale = document.getElementById(elIdMale);
    const containerFemale = document.getElementById(elIdFemale);
    if (!containerMale || !containerFemale) return;

    setLoading(elIdMale);
    setLoading(elIdFemale);

    try {

      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elIdMale);
        setEmpty(elIdFemale);
        return;
      }

      const yrGroups = ["2-A","2-B","2-C","2-D","2-E","2-F"];

      function buildCounters(){
        return {
          totals: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0},
          meets: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0}
        };
      }

      const male = buildCounters();
      const female = buildCounters();

      for (const row of rows) {

        const yrgrpRaw = String(row?.[yrgrpKey] ?? "").trim().toUpperCase();
        const genderRaw = String(row?.[genderKey] ?? "").trim().toLowerCase();

        if (!yrGroups.includes(yrgrpRaw)) continue;

        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;

        const group = genderRaw === "male" ? male :
                      genderRaw === "female" ? female : null;

        if (!group) continue;

        group.totals[yrgrpRaw]++;
        group.totals["Cohort"]++;

        if (s >= 6) {
          group.meets[yrgrpRaw]++;
          group.meets["Cohort"]++;
        }
      }

      const labels = [...yrGroups,"Cohort"];

      const colorMap = {
        "2-A":"#F3A1B4","2-B":"#C8DBAC","2-C":"#FBE8AF",
        "2-D":"#B8EAEF","2-E":"#D2CBF6","2-F":"#E6978B",
        "Cohort":"#5DA3D4"
      };

      function renderGraph(elId, data, title){

        const el = document.getElementById(elId);
        if (!el) return;

        el.innerHTML = "";

        const percentValues = labels.map(l =>
          data.totals[l] ? (data.meets[l]/data.totals[l])*100 : 0
        );

        const hoverText = labels.map(l =>
          `${l}: ${data.meets[l]}/${data.totals[l]} students (${percentValues[labels.indexOf(l)].toFixed(1)}%)`
        );

        const traces = labels.map((label,i)=>({
          type:"bar", x:[label], y:[percentValues[i]],
          name:label,
          text:[`${percentValues[i].toFixed(1)}%`],
          textposition:"outside",
          hovertext:[hoverText[i]],
          hoverinfo:"text",
          marker:{color:colorMap[label]}
        }));

        const layout = {
          autosize:true, barmode: "group",
          bargap: 0, bargroupgap: 0.1,
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

        Plotly.newPlot(elId,traces,layout,{displayModeBar:false,responsive:true})
        .then(() => {
          const gd = document.getElementById(elId);
          Plotly.Plots.resize(gd);
          setTimeout(() => Plotly.Plots.resize(gd),150);
        });
      }

      function renderGenderYearGroupTable(tblId, data){
        const percentValues = labels.map(l =>
          data.totals[l] ? (data.meets[l] / data.totals[l]) * 100 : 0
        );

        const tableBody = document.getElementById(tblId);
        if (!tableBody) return;

        tableBody.innerHTML = labels.map((label,i)=>`
          <tr class="text-center">
            <th scope="row">${label}</th>
            <td class="table-light">${data.totals[label]}</td>
            <td class="table-info">${data.meets[label]}</td>
            <td class="table-success">${percentValues[i].toFixed(1)}%</td>
          </tr>
        `).join("");

      }

      // --------- Render Table & Graphs ---------
      renderGraph(elIdMale, male);
      renderGenderYearGroupTable("tbl-yrgrp-male-st6-extl-ngrtb", male);

      renderGraph(elIdFemale, female);
      renderGenderYearGroupTable("tbl-yrgrp-female-st6-extl-ngrtb", female);
    }

    catch(err){
      console.error("Gender Year Group Stanine6 error:",err);
      setError(elIdMale);
      setError(elIdFemale);
    }
  }

  // ---------------------------------------
  // Year Group Insights Graphs - Progress
  // ---------------------------------------

  // Bar graph renderer External NGRTB - Year Group Insights
  // Expected/Better Progress and Better Progress
  async function renderYearGroupProgressThresholdBars({
    elIdEBP,
    elIdBP,
    datasetKey = "ngrtb",
    progressKey = "progress_category",
    yrgrpKey = "yrgrp"
  }) {
    const yrGroups = ["2-A","2-B","2-C","2-D","2-E","2-F"];
    const labels = [...yrGroups,"Cohort"];
    const colorMap = {
      "2-A":"#F3A1B4","2-B":"#C8DBAC","2-C":"#FBE8AF",
      "2-D":"#B8EAEF","2-E":"#D2CBF6","2-F":"#E6978B",
      "Cohort":"#5DA3D4"
    };
    const totals = Object.fromEntries(labels.map(l=>[l,0]));
    const meetsEBP = Object.fromEntries(labels.map(l=>[l,0]));
    const meetsBP = Object.fromEntries(labels.map(l=>[l,0]));

    try {
      setLoading(elIdEBP);
      setLoading(elIdBP);

      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      if (!rows.length) {
        setEmpty(elIdEBP);
        setEmpty(elIdBP);
        return;
      }

      let cohortEBP = 0, cohortBP = 0;

      // Process dataset
      rows.forEach(row => {
        const yr = String(row?.[yrgrpKey] ?? "")
          .trim().toUpperCase();

        if (!yrGroups.includes(yr)) return;

        totals[yr]++;
        totals["Cohort"]++;

        const progress = String(row?.[progressKey] ?? "")
          .trim().toLowerCase();

        if (progress === "expected" || progress === "better than expected") {
          meetsEBP[yr]++;
          meetsEBP["Cohort"]++;
        }

        if (progress === "better than expected") {
          meetsBP[yr]++;
          meetsBP["Cohort"]++;
        }
      });

      // Render Graph
      function renderGraph(elId, meets) {
        const el = document.getElementById(elId);
        if (!el) return;
        // remove "Loading..." placeholder
        el.innerHTML = "";

        const perc = labels.map(l =>
          totals[l] ? (meets[l] / totals[l]) * 100 : 0
        );
        const traces = labels.map((label,i)=>({
          type:"bar", x:[label], y:[perc[i]],
          name:label,
          text:[perc[i].toFixed(1)+"%"],
          textposition:"outside",
          marker:{color:colorMap[label]},
          hovertext:`${label}: ${meets[label]}/${totals[label]} students`,
          hoverinfo:"text"
        }));

        const layout = {
          autosize:true, barmode:"group",
          bargap: 0, bargroupgap: 0.1,
          yaxis:{
            title:"Percent of Students",
            ticksuffix:"%",
            range:[0,110]
          },
          margin:{t:40,r:20,b:60,l:60},
          legend:{orientation:"h", y:-0.2},
          hovermode:"x unified"
        };

        Plotly.newPlot(elId,traces,layout,{
          displayModeBar:false,
          responsive:true
        })
        .then(() => {
          const gd = document.getElementById(elId);
          // resize immediately
          Plotly.Plots.resize(gd);
          // resize after 150ms to handle any Bootstrap animation/layout changes
          setTimeout(() => Plotly.Plots.resize(gd), 150);
        });
      }

      // Render Table
      function renderTable(tblId, meets){
        const tbl = document.getElementById(tblId);
        if(!tbl) return;

        tbl.innerHTML = labels.map(l => {

          const pct = totals[l]
            ? ((meets[l]/totals[l])*100).toFixed(1)
            : "0.0";
          return `
            <tr class="text-center">
              <th scope="row">${l}</th>
              <td class="table-light">${totals[l]}</td>
              <td class="table-info">${meets[l]}</td>
              <td class="table-success">${pct}%</td>
            </tr>
          `;
        }).join("");
      }

      // -------------------------
      // Render outputs
      // -------------------------
      renderGraph(elIdEBP, meetsEBP);
      renderTable("tbl-yrgrp-ebp-extl-ngrtb", meetsEBP);

      renderGraph(elIdBP, meetsBP);
      renderTable("tbl-yrgrp-bp-extl-ngrtb", meetsBP);
    }
    catch(err){
      console.error("Progress category error:", err);
      setError(elIdEBP);
      setError(elIdBP);
    }
  }

  // ---------------------------------------------------
  // Resize Plotly charts when Bootstrap tabs/collapse open
  // ---------------------------------------------------
  document.addEventListener("shown.bs.tab", function () {
    [
      "pie-st5-extl-ngrtb", "pie-st6-extl-ngrtb",
      "bar-gender-st5-extl-ngrtb","bar-gender-st6-extl-ngrtb",
      "pie-prog-exp-plus-extl-ngrtb", "pie-prog-better-extl-ngrtb",
      "bar-gender-exp-plus-extl-ngrtb", "bar-gender-better-extl-ngrtb",
      "bar-yrgrp-st5-extl-ngrtb", "bar-yrgrp-st6-extl-ngrtb",
      "bar-yrgrp-male-st5-extl-ngrtb", "bar-yrgrp-female-st5-extl-ngrtb",
      "bar-yrgrp-male-st6-extl-ngrtb", "bar-yrgrp-female-st6-extl-ngrtb",
      "bar-yrgrp-ebp-extl-ngrtb", "bar-yrgrp-bp-extl-ngrtb"
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  document.addEventListener("shown.bs.collapse", function () {
    [
      "pie-st5-extl-ngrtb", "pie-st6-extl-ngrtb",
      "bar-gender-st5-extl-ngrtb","bar-gender-st6-extl-ngrtb",
      "pie-prog-exp-plus-extl-ngrtb", "pie-prog-better-extl-ngrtb",
      "bar-gender-exp-plus-extl-ngrtb", "bar-gender-better-extl-ngrtb",
      "bar-yrgrp-st5-extl-ngrtb", "bar-yrgrp-st6-extl-ngrtb",
      "bar-yrgrp-male-st5-extl-ngrtb", "bar-yrgrp-female-st5-extl-ngrtb",
      "bar-yrgrp-male-st6-extl-ngrtb", "bar-yrgrp-female-st6-extl-ngrtb",
      "bar-yrgrp-ebp-extl-ngrtb", "bar-yrgrp-bp-extl-ngrtb"
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  // -------------------------------
  // Public functions (window scope)
  // -------------------------------
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

  window.renderGenderProgressBars = function ({
    elIdExpectedPlus = "bar-gender-exp-plus-extl-ngrtb",
    elIdBetterOnly   = "bar-gender-better-extl-ngrtb",
    datasetKey = "ngrtb"
  } = {}) {
    return renderGenderProgressBars({
      elIdExpectedPlus,
      elIdBetterOnly,
      datasetKey
    });
  };

  window.renderYearGroupStanineBars = function () {
    return renderYearGroupStanineThresholdBars({
      elId5: "bar-yrgrp-st5-extl-ngrtb",
      elId6: "bar-yrgrp-st6-extl-ngrtb"
    });
  };

  window.renderYearGroupStanine5GenderBars = function () {
    return renderYearGroupStanine5GenderBars({
      elIdMale: "bar-yrgrp-male-st5-extl-ngrtb",
      elIdFemale: "bar-yrgrp-female-st5-extl-ngrtb"
    });
  }

  window.renderYearGroupStanine6GenderBars = function () {
    return renderYearGroupStanine6GenderBars({
      elIdMale: "bar-yrgrp-male-st6-extl-ngrtb",
      elIdFemale: "bar-yrgrp-female-st6-extl-ngrtb"
    });
  }

  window.renderYearGroupProgressBars = function () {
    return renderYearGroupProgressThresholdBars({
      elIdEBP: "bar-yrgrp-ebp-extl-ngrtb",
      elIdBP: "bar-yrgrp-bp-extl-ngrtb"
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

    // -----------------------------
    // Progress bars - gender-specific
    // -----------------------------
    window.renderGenderProgressBars({
      elIdExpectedPlus: "bar-gender-exp-plus-extl-ngrtb",
      elIdBetterOnly: "bar-gender-better-extl-ngrtb",
      datasetKey: "ngrtb"
    });

    // Year group bars
    window.renderYearGroupStanineBars();

    // Year Group Insights - Gender-specific Stanine 5 & above
    window.renderYearGroupStanine5GenderBars();

    // Year Group Insights - Gender-specific Stanine 6 & above
    window.renderYearGroupStanine6GenderBars();

    // Year group progress bars
    window.renderYearGroupProgressBars();
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
      "pie-st5-extl-ngrtb", "pie-st6-extl-ngrtb",
      "bar-gender-st5-extl-ngrtb", "bar-gender-st6-extl-ngrtb",
      "pie-prog-exp-plus-extl-ngrtb", "pie-prog-better-extl-ngrtb",
      "bar-gender-exp-plus-extl-ngrtb", "bar-gender-better-extl-ngrtb",
      "bar-yrgrp-st5-extl-ngrtb", "bar-yrgrp-st6-extl-ngrtb",
      "bar-yrgrp-male-st5-extl-ngrtb", "bar-yrgrp-female-st5-extl-ngrtb",
      "bar-yrgrp-male-st6-extl-ngrtb", "bar-yrgrp-female-st6-extl-ngrtb",
      "bar-yrgrp-ebp-extl-ngrtb", "bar-yrgrp-bp-extl-ngrtb",
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