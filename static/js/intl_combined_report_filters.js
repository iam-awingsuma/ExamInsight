// =========================================================
// ExamInsight - Internal Assessment Combined Report Filters
// Displays filtered internal assessment data
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
  // Search filter elements
  const internalSearchInput = document.getElementById("internalSearchInput");
  const genderFilter = document.getElementById("intlGenderFilter");
  const yrgrpFilter = document.getElementById("intlYrgrpFilter");
  const statusFilter = document.getElementById("intlStatusFilter");
  const senFilter = document.getElementById("intlSenFilter");
  const clearBtn = document.getElementById("clearIntlFiltersBtn");

  // Table elements
  const tableBody = document.getElementById("intlCombinedTableBody");
  const resultCount = document.getElementById("intlResultCount");

  // Stop script if this page does not contain the report filter section.
  if (
    !internalSearchInput ||
    !genderFilter ||
    !yrgrpFilter ||
    !statusFilter ||
    !senFilter ||
    !clearBtn ||
    !tableBody ||
    !resultCount
  ) {
    return;
  }

  // ---------------------------------------------------------
  // Build query parameters for the API request
  // ---------------------------------------------------------
  function buildQueryParams() {
    const params = new URLSearchParams();

    params.append("q", internalSearchInput.value.trim());
    params.append("gender", genderFilter.value);
    params.append("yrgrp", yrgrpFilter.value);
    params.append("status", statusFilter.value);
    params.append("sen", senFilter.value);

    return params.toString();
  }

  // ---------------------------------------------------------
  // Check if at least one filter is selected
  // This prevents loading all data accidentally.
  // ---------------------------------------------------------
  function hasActiveFilter() {
    return (
      internalSearchInput.value.trim().length > 0 ||
      genderFilter.value !== "All Genders" ||
      yrgrpFilter.value !== "All Year Groups" ||
      statusFilter.value !== "All Registration Status" ||
      senFilter.value !== "All SEN/SPED"
    );
  }

  // ---------------------------------------------------------
  // Show empty/loading/error message inside table
  // ---------------------------------------------------------
  function setTableMessage(message) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-muted py-4">
          ${message}
        </td>
      </tr>
    `;

    resultCount.textContent = "No records loaded";
  }

  // ---------------------------------------------------------
  // Format blank values safely
  // ---------------------------------------------------------
  function formatValue(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    return value;
  }

  // ---------------------------------------------------------
  //   Apply color to class based on progress category
  //   below expected, expected, above expected
  // ---------------------------------------------------------
  function getProgressClass(progress) {
    if (!progress) return "";

    switch (progress.toLowerCase()) {
      case "below expected":
        return "intl-progress-below";
      case "expected":
        return "intl-progress-expected";
      case "above expected":
        return "intl-progress-above";
      default:
        return "";
    }
  }

  // ---------------------------------------------------------
  //   Apply gender icon based on gender value
  // ---------------------------------------------------------
  function getGenderIcon(gender) {
    const value = String(gender || "").trim().toLowerCase();

    if (value === "male") {
        return `
        <img
            class="me-1"
            width="50"
            height="50"
            src="https://img.icons8.com/?size=100&id=4V1nG4SioGjp&format=png&color=000000"
            alt="Male"
            title="Male"
        />
        `;
    }

    if (value === "female") {
        return `
        <img
            class="me-1"
            width="50"
            height="50"
            src="https://img.icons8.com/?size=100&id=Sz1FlYHdFpV4&format=png&color=000000"
            alt="Female"
            title="Female"
        />
        `;
    }

    return "";
  }

  // ---------------------------------------------------------
  //   Display the SEN/SPED status as text based on boolean value
  // ---------------------------------------------------------
  function getSenValue(sen) {
    // Convert the database value into a clean string.
    const value = String(sen || "").trim();

    // If No, show nothing.
    if (
        // value === "" ||
        value.toLowerCase() === "no"
        // value.toLowerCase() === "none" ||
        // value.toLowerCase() === "null" ||
        // value.toLowerCase() === "undefined"
    ) {
        return "";
    }

    // Otherwise, show the actual database value from the sped column.
    return `SEN Details:&nbsp;<span class="badge bg-gradient-danger">${value}</span>`;
  }

  // ---------------------------------------------------------------------
  // Progress category class
  // Works for: below expected, expected, above expected
  // ---------------------------------------------------------------------
  function getProgressClass(progressCategory) {
    if (!progressCategory) {
      return "";
    }

    const value = progressCategory.toString().trim().toLowerCase();

    if (value.includes("below")) {
      return "progress-below";
    }

    if (value.includes("above")) {
      return "progress-above";
    }

    if (value.includes("expected")) {
      return "progress-expected";
    }

    return "";
  }

  // ---------------------------------------------------------------------
  // Render one Internal Assessment subject cell
  // Example: Previous %/Grade | Current %/Grade | Progress
  // ---------------------------------------------------------------------
  function renderSubjectCells(subjectResult) {
    if (!subjectResult) {
      return `
        <td>
          Previous AY: -<br/>
          Current AY: -<br/>
          Progress: -
        </td>
      `;
    }

    const progressClass = getProgressClass(subjectResult.progress_category);

    return `
      <td>
        Previous AY: ${formatValue(subjectResult.previous_percentage)}% / ${formatValue(subjectResult.previous_grade)}<br/>
        Current AY: ${formatValue(subjectResult.current_percentage)}% / ${formatValue(subjectResult.current_grade)}<br/>
        Progress: <span class="${progressClass}">${formatValue(subjectResult.progress_category)}</span>
      </td>
    `;
  }

  // ----------------------------------------
  // Fetch Internal Assessment combined data
  // ----------------------------------------
  async function loadInternalAssessmentData() {
    // Do not load data if no filter is selected
    if (!hasActiveFilter()) {
      setTableMessage("Select filters to view Internal Assessment data.");
      return;
    }

    try {
      setTableMessage("Loading Internal Assessment data...");

      const queryString = buildQueryParams();

      const response = await fetch(`/api/reports/internal/combined-data?${queryString}`);

      if (!response.ok) {
        throw new Error("Failed to load internal assessment data.");
      }

      const students = await response.json();

      tableBody.innerHTML = "";

      if (!students || students.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center text-muted py-4">
              No matching records found.
            </td>
          </tr>
        `;

        resultCount.textContent = "0 records";
        return;
      }

      students.forEach(student => {
        const row = document.createElement("tr");

        row.innerHTML = `
          <td class="text-center">
            <a href="/reports/internal/individual/${student.student_id}">
              <img
                class="me-1"
                width="45"
                height="45"
                src="https://img.icons8.com/?size=100&id=WTtEHNdDRYwj&format=png&color=000000"
                alt="Download PDF"
                title="Download PDF"
              />
            </a>
          </td>

          <td>
            <div class="d-inline-flex align-items-center justify-content-center gap-1 text-nowrap">
              <div>
                ${getGenderIcon(student.gender)}
              </div>

              <div>
                <span class="text-dark font-weight-bold">
                  ${formatValue(student.student_id)}
                </span>

                <span class="text-primary font-weight-bold">
                  ${formatValue(student.name)}
                </span><br/>

                ${formatValue(student.gender)},&nbsp;${formatValue(student.nationality)}<br/>
                ${formatValue(student.status)},&nbsp;${formatValue(student.yrgrp)}<br/>
                ${getSenValue(student.sped)}
              </div>
            </div>
          </td>

          ${renderSubjectCells(student.internal_assessment.english)}
          ${renderSubjectCells(student.internal_assessment.mathematics)}
          ${renderSubjectCells(student.internal_assessment.science)}
        `;

        tableBody.appendChild(row);
      });

      resultCount.textContent = `${students.length} record${students.length === 1 ? "" : "s"} found`;

    } catch (error) {
      console.error(error);

      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger py-4">
            Unable to load Internal Assessment data.
          </td>
        </tr>
      `;

      resultCount.textContent = "Error loading records";
    }
  }
  
  // ---------------------------------------------------------
  // Debounce typing in Internal Assessment search box
  // This avoids sending an API request on every single key press.
  // ---------------------------------------------------------
  let internalSearchTimer = null;

  function handleInternalSearchInput() {
    clearTimeout(internalSearchTimer);

    internalSearchTimer = setTimeout(function () {
      loadInternalAssessmentData();
    }, 300);
  }

  // ---------------------------------------------------------
  // Event listeners
  // ---------------------------------------------------------
  internalSearchInput.addEventListener("input", handleInternalSearchInput);
  genderFilter.addEventListener("change", loadInternalAssessmentData);
  yrgrpFilter.addEventListener("change", loadInternalAssessmentData);
  statusFilter.addEventListener("change", loadInternalAssessmentData);
  senFilter.addEventListener("change", loadInternalAssessmentData);

  clearBtn.addEventListener("click", function () {
    internalSearchInput.value = "";
    genderFilter.value = "All Genders";
    yrgrpFilter.value = "All Year Groups";
    statusFilter.value = "All Registration Status";
    senFilter.value = "All SEN/SPED";

    setTableMessage("Select filters to view Internal Assessment data.");
  });

  // Initial table message
  setTableMessage("Select filters to view Internal Assessment data.");
});