// =========================================================
// ExamInsight - NGRT Combined Report Filters
// Displays filtered NGRT-A, NGRT-B, and NGRT-C data
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
  // Search filter DOM element references
  const searchInput = document.getElementById("ngrtStudentSearch");
  const genderFilter = document.getElementById("ngrtGenderFilter");
  const yrgrpFilter = document.getElementById("ngrtYrgrpFilter");
  const statusFilter = document.getElementById("ngrtStatusFilter");
  const senFilter = document.getElementById("ngrtSenFilter");
  const clearBtn = document.getElementById("clearNgrtFiltersBtn");

  // Table display DOM element references
  const tableBody = document.getElementById("ngrtCombinedTableBody");
  const resultCount = document.getElementById("ngrtResultCount");

  // Guard clause: abort initialization if required filter or table DOM elements are missing
  if (
    !searchInput ||
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

    params.append("q", searchInput.value.trim());
    params.append("gender", genderFilter.value);
    params.append("yrgrp", yrgrpFilter.value);
    params.append("status", statusFilter.value);
    params.append("sen", senFilter.value);

    return params.toString();
  }

  // Check if at least one non-default filter is applied to prevent triggering empty queries
  function hasActiveFilter() {
    return (
      searchInput.value.trim().length > 0 ||
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
        <td colspan="17" class="text-center text-muted py-4">
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

  // Determine CSS class for Stanine scores based on standard score thresholds (1-3 below, 4-6 average, 7-9 above)
  function getStanineBandClass(stanine) {
    const value = Number(stanine);

    if (!value) return "";

    if (value <= 3) return "ngrt-band-below";
    if (value <= 6) return "ngrt-band-average";

    return "ngrt-band-above";
  }

  // Return CSS class mapping based on progress category description
  function getProgressClass(progress) {
    if (!progress) return "";

    switch (progress.toLowerCase()) {
      case "lower than expected":
        return "ngrt-progress-below";
      case "expected":
        return "ngrt-progress-expected";
      case "better than expected":
        return "ngrt-progress-above";
      default:
        return "";
    }
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

  // Render table cell HTML for an individual NGRT assessment set (SAS, Stanine, Reading Age, and Progress)
  function renderNgrtCells(result) {
    const bandClass = getStanineBandClass(result.stanine);
    const progressClass = getProgressClass(result.progress_category);

    return `
      <td>
        SAS: ${formatValue(result.sas)} | Stanine: <span class="${bandClass}">${formatValue(result.stanine)}</span><br/>
        Reading Age: ${formatValue(result.reading_age)}<br/>
        <span class="${progressClass}">${formatValue(result.progress_category)}</span>
      </td>
    `;
  }

  // Fetch combined NGRT data from API using active query parameters and render table rows
  function loadNgrtCombinedData() {
    if (!hasActiveFilter()) {
      setTableMessage("Select filters to view NGRT data.");
      return;
    }

    tableBody.innerHTML = `
      <tr>
        <td colspan="17" class="text-center text-muted py-4">
          Loading NGRT data...
        </td>
      </tr>
    `;

    fetch(`/api/reports/external/ngrt-combined-data?${buildQueryParams()}`)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Network response was not okay.");
        }

        return response.json();
      })
      .then(function (data) {
        if (!data.length) {
          setTableMessage("No students found for the selected filters.");
          return;
        }

        tableBody.innerHTML = "";

        data.forEach(function (student) {
          const row = document.createElement("tr");

          row.innerHTML = `
            <td class="text-center">
                <a href="/reports/external/individual/${student.student_id}">
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

            ${renderNgrtCells(student.ngrta)}
            ${renderNgrtCells(student.ngrtb)}
            ${renderNgrtCells(student.ngrtc)}
          `;

          tableBody.appendChild(row);
        });

        resultCount.textContent = `${data.length} record(s) loaded`;
      })
      .catch(function (error) {
        console.error("Error loading NGRT combined data:", error);
        setTableMessage("Unable to load NGRT data.");
      });
  }

  // Handle debounced search input to limit API request frequency while typing
  let searchTimer = null;

  function handleSearchInput() {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(function () {
      loadNgrtCombinedData();
    }, 300);
  }

  // Attach event listeners for text search, dropdown filters, and filter reset
  searchInput.addEventListener("input", handleSearchInput);
  genderFilter.addEventListener("change", loadNgrtCombinedData);
  yrgrpFilter.addEventListener("change", loadNgrtCombinedData);
  statusFilter.addEventListener("change", loadNgrtCombinedData);
  senFilter.addEventListener("change", loadNgrtCombinedData);

  clearBtn.addEventListener("click", function () {
    searchInput.value = "";
    genderFilter.value = "All Genders";
    yrgrpFilter.value = "All Year Groups";
    statusFilter.value = "All Registration Status";
    senFilter.value = "All SEN/SPED";

    setTableMessage("Select filters to view NGRT data.");
  });

  // Display initial instruction message on page load
  setTableMessage("Select filters to view NGRT data.");
});