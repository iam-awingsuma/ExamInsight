// ---------------------------------------------------------------------
// Handles External Assessments - Student Insights NGRT-A
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
    const main = document.getElementById("extl_si_analytics");
    // detect dataset and chart container
    const dataset = main?.getAttribute("data-ngrt") || "ngrta";
    const chartId = main?.getAttribute("data-chart") || "extl_ngrt_scatter";
    console.log("Dataset from HTML:", dataset);

    const elYrgrp = document.getElementById("yrgrp");
    const elStudent = document.getElementById("student");

    const rdgProfileCard = document.getElementById("rdg_profile_card");

    // Store API data once
    let allStudents = [];
    // Load API data
    loadData();

    const chartContainer = document.getElementById(chartId);
    // auto-resize
    if (chartContainer) {
        const resizeObserver = new ResizeObserver(() => {
            Plotly.Plots.resize(chartContainer);
        });
        resizeObserver.observe(chartContainer);
    }

    // Window resize event to make Plotly chart responsive
    window.addEventListener("resize", function () {
        const chart = document.getElementById(chartId);
        if (chart) {
            Plotly.Plots.resize(chart);
        }
    });

    // Year group change event
    elYrgrp.addEventListener("change", function(){
        resetAIAndReadingProfile();
        loadStudentsByYearGroup();
        updateDashboard();
    });

    // Student selection change event
    elStudent.addEventListener("change", function(){
        resetAIAndReadingProfile();
        updateDashboard();
    });

    // Load API Data
    async function loadData() {
        try {
            const res = await fetch("/api/analytics_extl_ngrt");
            const data = await res.json();
            console.log("API DATA:", data);
            allStudents = data[dataset] || [];
            populateYearGroups(); // fill year group dropdown once data is loaded
            displayNgrtLevel(); // display NGRT level in the headerz
            updateDashboard(); // one function to display KPI, Scatter plot, Student highlights, gender icon
        } catch (err) {
            console.error("Failed to load API data:", err);
        }
    }

    // display NGRT level in the header
    function displayNgrtLevel() {
        const elLevel = document.getElementById("extl_ngrt_level");
        if (!elLevel || !allStudents.length) return;
        const level = allStudents[0].ngrt_level || "NGRT";
        elLevel.textContent = level;
    }

    // Populate Year Groups
    function populateYearGroups() {
        const yrgrpSet = new Set();

        allStudents.forEach(row => {
            if (row.yrgrp) {
                yrgrpSet.add(row.yrgrp.trim().toUpperCase());
            }
        });

        elYrgrp.innerHTML = '<option value="">All Year Groups</option>';

        [...yrgrpSet].sort().forEach(yr => {
            const option = document.createElement("option");
            option.value = yr;
            option.textContent = yr;
            elYrgrp.appendChild(option);
        });
    }

    // Clear Student Dropdown
    function clearStudents() {
        elStudent.innerHTML = '<option value="">All Students</option>';
    }

    // Add Student Option
    function addStudentOption(id, name) {
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = name;
        elStudent.appendChild(opt);
    }

    // Load Students by Year Group
    function loadStudentsByYearGroup() {
        const yrgrp = elYrgrp.value;
        const icon = document.getElementById("student_gender_icon");

        clearStudents();

        if (!icon) return;

        // no year group selected, dropdown box is showing "All Year Groups"
        if (!yrgrp) {
            if (icon) {
                icon.src = "https://img.icons8.com/?size=100&id=Gziha7xJGho9&format=png&color=000000";
            }
            elStudent.disabled = true;
            // show all students scatter
            updateDashboard();
            return;
        }

        const filtered = allStudents.filter(s => {
            return (
                s.yrgrp &&
                s.yrgrp.trim().toLowerCase() === yrgrp.trim().toLowerCase()
            );
        });

        filtered.forEach(s => {
            const fullname = `${s.forename} ${s.surname}`;
            addStudentOption(s.student_id, fullname);
        });
        elStudent.disabled = false;
        
    }

    // update icon based on gender detection for students insights KPI
    function updateStudentGenderIcon() {
        const studentId = elStudent.value;
        const icon = document.getElementById("student_gender_icon");

        if (!icon) return;

        // If "All Students" selected → reset icon
        if (!studentId) {
            icon.src = "https://img.icons8.com/?size=100&id=Gziha7xJGho9&format=png&color=000000";
            return;
        }

        const student = allStudents.find(s => s.student_id == studentId);

        if (!student || !student.gender) return;

        const gender = student.gender.trim().toLowerCase();

        if (gender === "male") { icon.src = "https://img.icons8.com/?size=100&id=F9ipR5cXjxhq&format=png&color=000000"; }
        else if (gender === "female") { icon.src = "https://img.icons8.com/?size=100&id=Z6ZTBQJLLLWR&format=png&color=000000"; }
    }

    // Toggle reading profile card visibility based on student selection
    function toggleReadingProfileCard() {
        // Get the currently selected student ID from the dropdown
        const studentId = elStudent.value;
        // If a student is selected, show the Reading Profile card
        if (studentId && studentId !== "all") {
            rdgProfileCard.style.display = "block";
        } else {
            // If "All Students" or no student is selected,
            // hide the Reading Profile card
            rdgProfileCard.style.display = "none";
        }
    }

    // Reset AI Analysis and Reading Profile cards
    function resetAIAndReadingProfile() {
        // Reset AI interpretation text
        const aiTextTitle = document.getElementById("ai-interpretation");
        if (aiTextTitle) {
            aiTextTitle.innerHTML = `<div class="rounded-3 p-3" style="background-color: #FFF7CD;"> <strong><i class="fas fa-lightbulb"></i>&nbsp;
            <span class="text-info" id="ai_title"></span></strong><p id="interpretation-text" class="mb-0 mt-2 lh-base text-sm text-justify">
            Click 'Generate AI Analysis' to interpret the results using AI.</p></div>`;
        }

        // Reset Reading Profile fields
        const profileCategory = document.getElementById("rdg_profile_category");
        const profileDescription = document.getElementById("rdg_profile_description");
        const profileAI = document.getElementById("rdg_profile_ai_recommendations");

        if (profileCategory) {
            profileCategory.textContent = "Select a student & click 'Generate AI Analysis' to view their reading profile.";
            profileCategory.classList.remove(
                "badge",
                "bg-gradient-danger",
                "bg-gradient-info"
            );
        }

        if (profileDescription) {
            profileDescription.textContent = "Select a student & click 'Generate AI Analysis' to view their reading profile description.";
        }

        if (profileAI) {
            profileAI.textContent = "Click 'Generate AI Analysis' to interpret the results using AI.";
        }

        // Hide loading spinner if it was active
        const loading = document.getElementById("rdg_profile_loading");
        if (loading) loading.style.display = "none";
    }

    // -------------------------------------
    // Render Stanine vs SAS Scatter Plot
    // -------------------------------------
    function renderStanineScatter() {
        const yrgrp = elYrgrp.value;
        const studentId = elStudent.value;

        const cohort = yrgrp
            ? allStudents.filter(s =>
                s.yrgrp &&
                s.yrgrp.trim().toLowerCase() === yrgrp.trim().toLowerCase()
            )
            : allStudents;
        
            if (!cohort.length) {
            Plotly.react(chartId, [], {
                xaxis: {visible:false},
                yaxis: {visible:false}
            });
            return;
        }

        const x = cohort.map(s => Number(s.sas));
        const y = cohort.map(s => Number(s.stanine));
        const names = cohort.map(s => `${s.forename} ${s.surname}`);

        const cohortTrace = {
            x: x, y: y,
            mode: "markers", type: "scatter",
            text: names,
            hovertemplate:
                "<b>%{text}</b><br>SAS: %{x}<br>Stanine: %{y}<extra></extra>",
            marker: {
                size: 10, color: "#5e72e4", opacity: 0.6
            },
            name: yrgrp ? `Year ${yrgrp}` : `${cohort[0]?.ngrt_level} Cohort`,
        };

        let traces = [cohortTrace];

        // Highlight selected student
        if (studentId) {
            const student = cohort.find(s => s.student_id == studentId);

            if (student) {
                traces.push({
                    x: [Number(student.sas)], y: [Number(student.stanine)],
                    mode: "markers", type: "scatter",
                    text: [`${student.forename} ${student.surname}`],
                    hovertemplate:
                        "<b>%{text}</b><br>SAS: %{x}<br>Stanine: %{y}<extra></extra>",
                    marker: {
                        size: 18, color: "#ED3F27",
                        line: { width: 2, color: "#134686" }
                    },
                    name: "<b><span style='color:#008BFF'>" + student.forename + " " + student.surname + "</span></b>" +
                    "<b><span style='color:#008BFF'>" + " | Stanine: " + student.stanine + " | SAS: " + student.sas + "</span></b>",
                });
            }
        }

        const layout = {
            autosize: true,
            margin: { l: 70, r: 30, t: 20, b: 70 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            xaxis: {
                title: "<b>Standard Age Score (SAS)</b>",
                color: "#25343F",
                showspikes: false,
                range: [60,140],
            },
            yaxis: {
                title: "<b>Stanine</b>",
                color: "#25343F",
                showspikes: false,
                range: [0.5,9.5],
                dtick: 1
            },
            hovermode: "closest",
            showlegend: true,
            legend:{orientation:"h", y:-0.2},
            font: {size: 13, color: "#25343F"},
            shapes: [
                // Stanine 1-3 band
                {
                    type: "rect", xref: "paper", yref: "y",
                    x0: 0, x1: 1,
                    y0: 0.5, y1: 3.5,
                    fillcolor: "rgba(245,54,92,0.12)",
                    line: {width:0}
                },
                // Stanine 4-6 band
                {
                    type: "rect", xref: "paper", yref: "y",
                    x0: 0, x1: 1,
                    y0: 3.5, y1: 6.5,
                    fillcolor: "rgba(255,193,7,0.12)",
                    line: {width:0}
                },
                // Stanine 7-9 band
                {
                    type: "rect", xref: "paper", yref: "y",
                    x0: 0, x1: 1,
                    y0: 6.5, y1: 9.5,
                    fillcolor: "rgba(40,167,69,0.12)",
                    line: {width:0}
                },
                // SAS benchmark
                {
                    type: "line",
                    x0: 100, x1: 100,
                    y0: 0.5, y1: 9.5,
                    line: {
                        color: "black", width: 2, dash: "dash"
                    }
                }
            ],
            annotations: [
                {
                    x: 100, y: 9.3,
                    text: "<b>National Average SAS (100)</b>",
                    showarrow: false,
                    font: {size:14, color:"#ff7444"},
                }
            ]
        };
        Plotly.react(chartId, traces, layout, {displayModeBar: false, responsive:true});
    }

    // ---------------------------------------------
    // Render KPIs for Student Insights External
    // ---------------------------------------------
    function renderKPIs(cohort = [], student = null) {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent =
                (typeof val === "number" ? val.toFixed(0) : val ?? "-");
        };

        // student mode
        if (student) {
            set("kpi_total_value", 1);
            set("kpi_sas", Number(student.sas));
            set("kpi_stanine", Number(student.stanine));
            // show student's progress category
            set("kpi_progcat", student.progress_category || "-");
            return;
        }

        // cohort mode
        if (!cohort.length) {
            set("kpi_total_value", 0);
            set("kpi_sas", "-");
            set("kpi_stanine", "-");
            set("kpi_progcat", "-");
            return;
        }

        const totalStudents = cohort.length;

        const avgSAS =
            cohort.reduce((sum, s) => sum + Number(s.sas || 0), 0) / totalStudents;

        const avgStanine =
            cohort.reduce((sum, s) => sum + Number(s.stanine || 0), 0) / totalStudents;

        set("kpi_total_value", totalStudents);
        set("kpi_sas", avgSAS);
        set("kpi_stanine", avgStanine);

        // most common progress category
        const categories = cohort
            .map(s => s.progress_category)
            .filter(Boolean);

        let mostCommon = "-";

        if (categories.length) {
            const counts = {};
            categories.forEach(cat => {
                counts[cat] = (counts[cat] || 0) + 1;
            });

            mostCommon = Object.keys(counts).reduce((a, b) =>
                counts[a] > counts[b] ? a : b
            );
        }

        set("kpi_progcat", mostCommon);
    }

    // -------------------------------------------------------------
    // NGRT Line Graph (SAS + Stanine) - Attainment over Time
    // -------------------------------------------------------------
    function renderNgrtAttainmentLine(cohort = [], student = null) {
        const SASlabels = ["Previous SAS", "Latest SAS"];
        const Staninelabels = ["Previous Stanine", "Latest Stanine"];

        let prevSAS = 0, currSAS = 0;
        let prevStanine = 0, currStanine = 0;

        // Student mode - show individual student's progression
        if (student) {
            // student SAS and Stanine scores (use 0 if not available to avoid Plotly errors)
            prevSAS = Number(student.prev_sas || 0);
            currSAS = Number(student.sas || 0);
            prevStanine = Number(student.prev_stanine || 0);
            currStanine = Number(student.stanine || 0);
        }
        // Cohort / Year Group Mode - show average progression for the group
        else if (cohort.length) {
            const avg = (arr, key) => {
                const vals = arr.map(x => Number(x[key] || 0));
                return vals.length
                    ? Math.round(vals.reduce((a,b)=>a+b,0) / vals.length)
                    : 0;
            };
            // average previous and current SAS and Stanine for the cohort/year group
            prevSAS = avg(cohort, "prev_sas");
            currSAS = avg(cohort, "sas");
            prevStanine = avg(cohort, "prev_stanine");
            currStanine = avg(cohort, "stanine");
        }

        const traceSAS = [
            {x: SASlabels, y: [prevSAS, currSAS], type: "scatter", mode: "lines+markers", name: "SAS", 
                marker: { color: "#6FAF4F", size: 8 }, line: { color: "#A7E399", width: 2 }, 
            hovertemplate: "<b>SAS: </b><b>%{y}</b><extra></extra>"}
        ];

        const traceStanine = [
            {x: Staninelabels, y: [prevStanine, currStanine], type: "scatter", mode: "lines+markers", name: "Stanine", 
                marker: { color: "#6FAF4F", size: 8 }, line: { color: "#A7E399", width: 2 }, 
            hovertemplate: "<b>Stanine: </b><b>%{y}</b><extra></extra>"}
        ];

        const layout = {
            autosize: true,
            width: null,
            margin: { t: 20, r: 20, b: 40, l: 50 },
            legend: { orientation: "h" },
            hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left"},
            hovermode: "x unified",
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)"
        };

        Plotly.react("chart_attainment_over_time", traceSAS, layout, {
            displayModeBar: false,
            responsive: true
        });

        Plotly.react("chart_progress_over_time", traceStanine, layout, {
            displayModeBar: false,
            responsive: true
        });

        const chart1 = document.getElementById("chart_attainment_over_time");
        const chart2 = document.getElementById("chart_progress_over_time");

        [chart1, chart2].forEach(chart => {
            if (!chart) return;
            // Initial resize charts to ensure they fit their containers
            if (chart) Plotly.Plots.resize(chart);

            // automatically resize charts when their container size changes
            const observer = new ResizeObserver(() => {
                Plotly.Plots.resize(chart);
            });
            observer.observe(chart);
        });
    }

    // ---------------------------------------------------------------------
    // Update Dashboard (KPIs + Chart + Student Icon + Reading Profile card)
    // ---------------------------------------------------------------------
    function updateDashboard() {
        const yrgrp = elYrgrp.value;
        const studentId = elStudent.value;
        // Filter cohort
        let cohort = allStudents;

        if (yrgrp) {
            cohort = allStudents.filter(s =>
                s.yrgrp &&
                s.yrgrp.trim().toLowerCase() === yrgrp.trim().toLowerCase()
            );
        }
        // Detect selected student
        let selectedStudent = null;

        if (studentId) {
            selectedStudent = cohort.find(s => String(s.student_id) === String(studentId));
        }

        // Update KPIs
        renderKPIs(cohort, selectedStudent);
        // Update gender icon
        updateStudentGenderIcon();
        // Render scatter plot
        renderStanineScatter();
        // Render attainment over time line graph
        renderNgrtAttainmentLine(cohort, selectedStudent);
        // Toggle reading profile card
        toggleReadingProfileCard();
    }
});