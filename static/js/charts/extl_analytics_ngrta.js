// js/charts/extl_analytics_ngrta.js

(() => {
  // Cache for API payload to avoid duplicate network calls
  let _extNgrtCache = null;

  // Fetches NGRT analytics data from API endpoint with caching
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

  // Updates inner HTML of a target DOM element by ID
  function setMessage(elId, html) {
    const el = document.getElementById(elId);
    if (!el) return false;
    el.innerHTML = html;
    return true;
  }

  // Displays a italicized loading state message in target element
  function setLoading(elId) {
    return setMessage(elId, `<p class="text-muted text-sm fst-italic p-2 mb-0">Loading...</p>`);
  }

  // Displays a red error badge message in target element
  function setError(elId, msg = "Failed to load data") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
  }

  // Displays a red empty-data badge message in target element
  function setEmpty(elId, msg = "No data available") {
    return setMessage(elId, `<p class="badge bg-danger mt-1">${msg}</p>`);
  }

  // Renders a pie chart showing proportion of students above vs below a stanine threshold
  async function renderStanineThresholdPie({
    elId,
    datasetKey = "ngrta",
    stanineKey = "stanine",
    threshold = 5
  }) {
    // Return early if container element does not exist in DOM
    const container = document.getElementById(elId);
    if (!container) return;

    // Show loading text while fetching data
    setLoading(elId);

    try {
      // Fetch payload and extract dataset rows
      const payload = await getExtNgrtPayload();
      const rows = payload?.[datasetKey] || [];

      // Render empty state if dataset is missing or empty
      if (!Array.isArray(rows) || rows.length === 0) {
        setEmpty(elId);
        return;
      }

      let above = 0;
      let below = 0;

      // Count students meeting or falling below threshold score
      for (const row of rows) {
        const s = Number(row?.[stanineKey]);
        if (!Number.isFinite(s)) continue;
        if (s >= threshold) above++;
        else below++;
      }

      // Render empty state if no valid numeric scores exist
      if (above === 0 && below === 0) {
        setEmpty(elId, "No valid stanine values found.");
        return;
      }

      const el = document.getElementById(elId);
      if (!el) return;

      // Clear loading message before rendering chart
      el.innerHTML = "";

      // Configure Plotly pie chart trace
      const trace = {
        type: "pie",
        labels: [`Stanine ${threshold} and above`, `Stanine ${threshold - 1} and below`],
        values: [above, below],
        hole: 0.3, // Donut style chart hole ratio
        textinfo: "label+percent",
        marker: {
          colors: ['#67C6E3', '#F5F1DC'] // Color palette for pie slices
        },
        hovertemplate:
          "<b>%{label}</b><br>" +
          "Students: %{value}<br>" +
          "Percentage: %{percent}" +
          "<extra></extra>"
      };

      // Configure layout margins, legend position, and responsiveness
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

      // Plot chart and resize after initial paint and layout animation
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

  // Renders a bar chart comparing percentage of male vs female students meeting a stanine threshold
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

      // Initialize counter variables for gender totals and threshold achievements
      let maleTotal = 0;
      let femaleTotal = 0;
      let maleMeet = 0;
      let femaleMeet = 0;

      // Aggregate counts by gender and stanine threshold criteria
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

      // Calculate percentage values per gender group
      const percentValues = meets.map((v, i) => (totals[i] ? (v / totals[i]) * 100 : 0));

      // Construct detailed hover text for bar tooltips
      const hoverText = labels.map((lbl, i) =>
        `${lbl}: ${meets[i]}/${totals[i]} students (${percentValues[i].toFixed(1)}%)`
      );

      const el = document.getElementById(elId);
      if (!el) return;

      el.innerHTML = "";

      // Configure separate traces for Male and Female bar series
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

      // Set Y-axis percentage limits and unified x-hover mode
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

  // Renders bar charts and tables comparing class groups and full cohort for Stanine 5+ and 6+
  async function renderYearGroupStanineThresholdBars({
    elId5,
    elId6,
    datasetKey = "ngrta",
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

      // Initialize class and cohort counters
      const totals = {
        "2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0
      };

      const meets5 = {...totals};
      const meets6 = {...totals};

      // Populate counters for Stanine >= 5 and Stanine >= 6
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

      // Map color scheme to specific class labels and cohort bar
      const colorMap = {
        "2-A":"#F3A1B4", "2-B":"#C8DBAC", "2-C":"#FBE8AF",
        "2-D":"#B8EAEF", "2-E":"#D2CBF6", "2-F":"#E6978B",
        "Cohort":"#5DA3D4"
      };

      // Helper function to build and plot year group bar graphs
      function renderGraph(elId, meets, threshold){
        const el = document.getElementById(elId);
        if (!el) return;

        el.innerHTML = "";

        const percentValues = labels.map(l =>
          totals[l] ? (meets[l]/totals[l])*100 : 0
        );

        const hoverText = labels.map(l =>
          `${l}: ${meets[l]}/${totals[l]} students (${percentValues[labels.indexOf(l)].toFixed(1)}%)`
        );

        // Map labels to individual bar traces with distinct colors
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
          title:"",
          autosize:true,
          barmode:"group",
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
          setTimeout(() => Plotly.Plots.resize(gd), 150);
        });
      }

      // Helper function to populate summary HTML table rows
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

      // Render Stanine 5 graph and table
      renderGraph(elId5,meets5,5);
      renderTable("tbl-yrgrp-st5-extl-ngrta",meets5);

      // Render Stanine 6 graph and table
      renderGraph(elId6,meets6,6);
      renderTable("tbl-yrgrp-st6-extl-ngrta",meets6);
    }
    catch(err){
      console.error("Stanine combined error:",err);
      setError(elId5);
      setError(elId6);
    }
  }

  // Renders gender-filtered year group bar charts and tables for Stanine 5 & above
  async function renderYearGroupStanine5GenderBars({
    elIdMale,
    elIdFemale,
    datasetKey = "ngrta",
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

      // Factory for nested counter structures
      function buildCounters(){
        return {
          totals: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0},
          meets: {"2-A":0,"2-B":0,"2-C":0,"2-D":0,"2-E":0,"2-F":0,"Cohort":0}
        };
      }

      const male = buildCounters();
      const female = buildCounters();

      // Filter and count male and female performance per class
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

      // Render chart for gender-filtered dataset
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

      // Render table for gender-filtered dataset
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

      // Execute render for Male and Female Stanine 5+ sections
      renderGraph(elIdMale, male);
      renderGenderYearGroupTable("tbl-yrgrp-male-st5-extl-ngrta", male);

      renderGraph(elIdFemale, female);
      renderGenderYearGroupTable("tbl-yrgrp-female-st5-extl-ngrta", female);
    }
    catch(err){
      console.error("Gender Year Group Stanine5 error:",err);
      setError(elIdMale);
      setError(elIdFemale);
    }
  }

  // Renders gender-filtered year group bar charts and tables for Stanine 6 & above
  async function renderYearGroupStanine6GenderBars({
    elIdMale,
    elIdFemale,
    datasetKey = "ngrta",
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

      // Aggregate male and female counts for Stanine >= 6
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
          hovertext:[hoverText[i]], hoverinfo:"text",
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

      // Execute render for Male and Female Stanine 6+ sections
      renderGraph(elIdMale, male);
      renderGenderYearGroupTable("tbl-yrgrp-male-st6-extl-ngrta", male);

      renderGraph(elIdFemale, female);
      renderGenderYearGroupTable("tbl-yrgrp-female-st6-extl-ngrta", female);
    }
    catch(err){
      console.error("Gender Year Group Stanine6 error:",err);
      setError(elIdMale);
      setError(elIdFemale);
    }
  }

  // Listens to Bootstrap tab switches to trigger Plotly container resizing
  document.addEventListener("shown.bs.tab", function () {
    [
      "pie-st5-extl-ngrta", "pie-st6-extl-ngrta",
      "bar-gender-st5-extl-ngrta","bar-gender-st6-extl-ngrta",
      "bar-yrgrp-st5-extl-ngrta", "bar-yrgrp-st6-extl-ngrta",
      "bar-yrgrp-male-st5-extl-ngrta", "bar-yrgrp-female-st5-extl-ngrta",
      "bar-yrgrp-male-st6-extl-ngrta", "bar-yrgrp-female-st6-extl-ngrta",
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  // Listens to Bootstrap collapse expansion events to trigger Plotly container resizing
  document.addEventListener("shown.bs.collapse", function () {
    [
      "pie-st5-extl-ngrta", "pie-st6-extl-ngrta",
      "bar-gender-st5-extl-ngrta","bar-gender-st6-extl-ngrta",
      "bar-yrgrp-st5-extl-ngrta","bar-yrgrp-st6-extl-ngrta",
      "bar-yrgrp-male-st5-extl-ngrta", "bar-yrgrp-female-st5-extl-ngrta",
      "bar-yrgrp-male-st6-extl-ngrta", "bar-yrgrp-female-st6-extl-ngrta",
    ].forEach(function(id){
      const gd = document.getElementById(id);
      if (gd) Plotly.Plots.resize(gd);
    });
  });

  // Expose public global methods on window object
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

  window.renderYearGroupStanine5GenderBars = function () {
    return renderYearGroupStanine5GenderBars({
      elIdMale: "bar-yrgrp-male-st5-extl-ngrta",
      elIdFemale: "bar-yrgrp-female-st5-extl-ngrta"
    });
  }

  window.renderYearGroupStanine6GenderBars = function () {
    return renderYearGroupStanine6GenderBars({
      elIdMale: "bar-yrgrp-male-st6-extl-ngrta",
      elIdFemale: "bar-yrgrp-female-st6-extl-ngrta"
    });
  }

  // Master function to execute rendering of all NGRT-A attainment charts
  window.renderExternalNgrtAttainmentPies = function () {
    // Cohort pies
    window.renderStanine5Pie("pie-st5-extl-ngrta");
    window.renderStanine6Pie("pie-st6-extl-ngrta");

    // Gender-specific bars
    window.renderGenderStanine5Bar("bar-gender-st5-extl-ngrta");
    window.renderGenderStanine6Bar("bar-gender-st6-extl-ngrta");

    // Year group bars
    window.renderYearGroupStanineBars();

    // Year Group Insights - Gender-specific Stanine 5 & above
    window.renderYearGroupStanine5GenderBars();

    // Year Group Insights - Gender-specific Stanine 6 & above
    window.renderYearGroupStanine6GenderBars();
  };

  // Attaches event listeners to render charts when accordion panel collapses/expands
  function wireAccordionRender() {
    const panel = document.getElementById("btn_extl_att");
    if (!panel) return;

    // Render immediately if panel is visible on page load
    if (panel.classList.contains("show")) {
      window.renderExternalNgrtAttainmentPies();
    }

    // Trigger chart render upon expanding collapse element
    panel.addEventListener("shown.bs.collapse", () => {
      window.renderExternalNgrtAttainmentPies();
    });
  }

  // Attaches window resize listener to update all active Plotly charts
  function wireResize() {
    window.addEventListener("resize", () => {
      const ids = [
        "pie-st5-extl-ngrta", "pie-st6-extl-ngrta",
        "bar-gender-st5-extl-ngrta", "bar-gender-st6-extl-ngrta",
        "bar-yrgrp-st5-extl-ngrta", "bar-yrgrp-st6-extl-ngrta",
        "bar-yrgrp-male-st5-extl-ngrta", "bar-yrgrp-female-st5-extl-ngrta",
        "bar-yrgrp-male-st6-extl-ngrta", "bar-yrgrp-female-st6-extl-ngrta",
      ];

      for (const id of ids) {
        const el = document.getElementById(id);
        if (el) Plotly.Plots.resize(el);
      }
    });
  }

  // Initialize event bindings once DOM content is fully loaded
  document.addEventListener("DOMContentLoaded", () => {
    wireAccordionRender();
    wireResize();
  });
})();