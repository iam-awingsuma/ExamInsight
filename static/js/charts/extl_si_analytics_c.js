// ---------------------------------------------------------------------
// Handles year group and student dropdowns for Student Insights NGRT-C
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
    const elYrgrp = document.getElementById("yrgrp");
    const elStudent = document.getElementById("student");

    // Store API data once
    let allStudents = [];
    // Load API data
    loadData();

    // Year group change event
    elYrgrp.addEventListener("change", loadStudentsByYearGroup);

    // Load API Data
    async function loadData() {
        try {
            const res = await fetch("/api/analytics_extl_ngrt");
            const data = await res.json();
            console.log("API DATA:", data);
            allStudents = data.ngrtc || [];
            populateYearGroups();
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

        clearStudents();

        if (!yrgrp) {
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
    }
});