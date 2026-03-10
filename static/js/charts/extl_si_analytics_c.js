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
    elStudent.addEventListener("change", updateStudentGenderIcon);

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
        const icon = document.getElementById("student_gender_icon");

        clearStudents();

        if (!icon) return;

        // no year group selected
        // dropdown box is showing "All Year Groups"
        if (!yrgrp) {
            // Show default icon
            if (icon) {
                icon.src = "https://img.icons8.com/?size=100&id=Gziha7xJGho9&format=png&color=000000";
            }
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

        if (gender === "male") {
            icon.src = "https://img.icons8.com/?size=100&id=F9ipR5cXjxhq&format=png&color=000000";
        }
        else if (gender === "female") {
            icon.src = "https://img.icons8.com/?size=100&id=Z6ZTBQJLLLWR&format=png&color=000000";
        }
    }
});