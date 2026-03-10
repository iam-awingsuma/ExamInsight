// ---------------------------------------------------------------------
// Handles year group and student dropdowns for Student Insights NGRT-A
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
    const elYrgrp = document.getElementById("yrgrp");
    const elStudent = document.getElementById("student");

    // Store API data once
    let allStudents = [];
    // Load API data
    loadData();

    // Year group change event
    // elYrgrp.addEventListener("change", loadStudentsByYearGroup);
    elYrgrp.addEventListener("change", function(){
        loadStudentsByYearGroup();
        renderStanineScatter();
    });

    elStudent.addEventListener("change", function(){
        updateStudentGenderIcon();
        renderStanineScatter();
    });

    // Load API Data
    async function loadData() {
        try {
            const res = await fetch("/api/analytics_extl_ngrt");
            const data = await res.json();
            console.log("API DATA:", data);
            allStudents = data.ngrta || [];
            populateYearGroups(); // fill year group dropdown once data is loaded
            renderStanineScatter(); // draw graph immediately using all students
        } catch (err) {
            console.error("Failed to load API data:", err);
        }
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
            // Show default icon
            if (icon) { icon.src = "https://img.icons8.com/?size=100&id=Gziha7xJGho9&format=png&color=000000"; }
            elStudent.disabled = true;
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
        
        // reset graph when year group changes
        Plotly.purge("extl_ngrta_scatter");

        renderStanineScatter();
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

    // Render Stanine vs SAS Scatter Plot
    function renderStanineScatter() {

        const yrgrp = elYrgrp.value;
        const studentId = elStudent.value;

        // Filter by year group if selected
        let cohort = allStudents;

        if (yrgrp) {
            cohort = allStudents.filter(s =>
                s.yrgrp &&
                s.yrgrp.trim().toLowerCase() === yrgrp.trim().toLowerCase()
            );
        }

        if (!cohort.length) return;

        const x = [];
        const y = [];
        const names = [];

        cohort.forEach(s => {
            x.push(Number(s.sas));
            y.push(Number(s.stanine));
            names.push(`${s.forename} ${s.surname}`);
        });

        const cohortTrace = {
            x: x,
            y: y,
            mode: "markers",
            type: "scatter",
            text: names,
            hovertemplate:
                "<b>%{text}</b><br>SAS: %{x}<br>Stanine: %{y}<extra></extra>",
            marker: {
                size: 10,
                color: "#5e72e4",
                opacity: 0.6
            },
            name: "Cohort"
        };

        let traces = [cohortTrace];

        // Highlight selected student
        if (studentId) {

            const student = cohort.find(s => s.student_id == studentId);

            if (student) {
                traces.push({
                    x: [Number(student.sas)],
                    y: [Number(student.stanine)],
                    mode: "markers",
                    type: "scatter",
                    text: [`${student.forename} ${student.surname}`],
                    hovertemplate:
                        "<b>%{text}</b><br>SAS: %{x}<br>Stanine: %{y}<extra></extra>",
                    marker: {
                        size: 18,
                        color: "#f5365c",
                        line: {
                            width: 3,
                            color: "#000"
                        }
                    },
                    name: "Selected Student"
                });
            }
        }

        const layout = {
            // title: "NGRT-A Stanine vs Standard Age Score",
            xaxis: {
                title: "Standard Age Score (SAS)",
                range: [60,140]
            },

            yaxis: {
                title: "Stanine",
                range: [0.5,9.5],
                dtick: 1
            },

            hovermode: "closest",

            shapes: [

                // Stanine 1-3 band
                {
                    type: "rect",
                    xref: "paper",
                    yref: "y",
                    x0: 0,
                    x1: 1,
                    y0: 0.5,
                    y1: 3.5,
                    fillcolor: "rgba(245,54,92,0.12)",
                    line: {width:0}
                },

                // Stanine 4-6 band
                {
                    type: "rect",
                    xref: "paper",
                    yref: "y",
                    x0: 0,
                    x1: 1,
                    y0: 3.5,
                    y1: 6.5,
                    fillcolor: "rgba(255,193,7,0.12)",
                    line: {width:0}
                },

                // Stanine 7-9 band
                {
                    type: "rect",
                    xref: "paper",
                    yref: "y",
                    x0: 0,
                    x1: 1,
                    y0: 6.5,
                    y1: 9.5,
                    fillcolor: "rgba(40,167,69,0.12)",
                    line: {width:0}
                },

                // SAS benchmark
                {
                    type: "line",
                    x0: 100,
                    x1: 100,
                    y0: 0.5,
                    y1: 9.5,
                    line: {
                        color: "black",
                        width: 2,
                        dash: "dash"
                    }
                }
            ],

            annotations: [
                {
                    x: 100,
                    y: 9,
                    text: "National Average SAS (100)",
                    showarrow: false,
                    font: {size:11}
                }
            ]
        };

        Plotly.react("extl_ngrta_scatter", traces, layout, {responsive:true});
    }
});