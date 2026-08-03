// =========================================================
// ExamInsight - Internal Assessment Combined Report Filters
// Displays filtered internal assessment data
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
  // Search filter DOM element references
  const internalSearchInput = document.getElementById("internalSearchInput");
  const genderFilter = document.getElementById("intlGenderFilter");
  const yrgrpFilter = document.getElementById("intlYrgrpFilter");
  const statusFilter = document.getElementById("intlStatusFilter");
  const senFilter = document.getElementById("intlSenFilter");
  const clearBtn = document.getElementById("clearIntlFiltersBtn");

  // Table display DOM element references
  const tableBody = document.getElementById("intlCombinedTableBody");
  const resultCount = document.getElementById("intlResultCount");

  // Guard clause: abort initialization if required filter or table DOM elements are missing
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

  // Construct URL query parameters string from active filter input values
  function buildQueryParams() {
    const params = new URLSearchParams();

    params.append("q", internalSearchInput.value.trim());
    params.append("gender", genderFilter.value);
    params.append("yrgrp", yrgrpFilter.value);
    params.append("status", statusFilter.value);
    params.append("sen", senFilter.value);

    return params.toString();
  }

  // Check if at least one non-default filter is applied to prevent triggering empty queries
  function hasActiveFilter() {
    return (
      internalSearchInput.value.trim().length > 0 ||
      genderFilter.value !== "All Genders" ||
      yrgrpFilter.value !== "All Year Groups" ||
      statusFilter.value !== "All Registration Status" ||
      senFilter.value !== "All SEN/SPED"
    );
  }

  // Display status or error message spanning across all table columns and update record counter
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

  // Safely format missing, null, or undefined values with a placeholder dash
  function formatValue(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    return value;
  }

  // Return male/female icon HTML string according to gender parameter
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

  // Format SEN/SPED details badge HTML if student has non-empty/non-"no" SEN status
  function getSenValue(sen) {
    const value = String(sen || "").trim();

    if (value.toLowerCase() === "no") {
        return "";
    }

    return `SEN Details:&nbsp;<span class="badge bg-gradient-danger">${value}</span>`;
  }

  // Determine progress CSS class mapping based on keywords (below, above, expected)
  function getProgressClass(progressCategory) {
    if (!progressCategory) {
      return "";
    }

    const value = progressCategory.toString().trim().toLowerCase();

    if (value.includes("below")) {
      return "intl-progress-below";
    }
    
    if (value.includes("above")) {
      return "intl-progress-above";
    }

    if (value.includes("expected")) {
      return "intl-progress-expected";
    }

    return "";
  }

  // Render table cell HTML for an individual internal assessment subject (English, Maths, or Science)
  function renderSubjectCells(subjectResult) {
    if (!subjectResult) {
      return `
        <td>
          Previous AY: -<br/>
          Current AY: -<br/>
        </td>
      `;
    }

    const progressClass = getProgressClass(subjectResult.progress_category);

    return `
      <td>
        Previous AY: ${formatValue(subjectResult.previous_percentage)}% / ${formatValue(subjectResult.previous_grade)}<br/>
        Current AY: ${formatValue(subjectResult.current_percentage)}% / ${formatValue(subjectResult.current_grade)}<br/>
        <span class="${progressClass}">${formatValue(subjectResult.progress_category)}</span>
      </td>
    `;
  }

  // Asynchronously fetch combined internal assessment data from API and render student table rows
  async function loadInternalAssessmentData() {
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

  // Handle debounced search input to limit API request frequency while typing
  let internalSearchTimer = null;

  function handleInternalSearchInput() {
    clearTimeout(internalSearchTimer);

    internalSearchTimer = setTimeout(function () {
      loadInternalAssessmentData();
    }, 300);
  }

  // Attach event listeners for text search, dropdown filters, and filter reset
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

  // Display initial instruction message on page load
  setTableMessage("Select filters to view Internal Assessment data.");
});