// =========================================================
// ExamInsight - NGRT Combined Report Filters
// Displays filtered NGRT-A, NGRT-B, and NGRT-C data
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
  // Search filter elements
  const searchInput = document.getElementById("ngrtStudentSearch");
  const genderFilter = document.getElementById("ngrtGenderFilter");
  const yrgrpFilter = document.getElementById("ngrtYrgrpFilter");
  const statusFilter = document.getElementById("ngrtStatusFilter");
  const senFilter = document.getElementById("ngrtSenFilter");
  const clearBtn = document.getElementById("clearNgrtFiltersBtn");

  // Table elements
  const tableBody = document.getElementById("ngrtCombinedTableBody");
  const resultCount = document.getElementById("ngrtResultCount");

  // Stop script if this page does not contain the NGRT report filter section.
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

  // ---------------------------------------------------------
  // Build query parameters for the API request
  // ---------------------------------------------------------
  function buildQueryParams() {
    const params = new URLSearchParams();

    params.append("q", searchInput.value.trim());
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
      searchInput.value.trim().length > 0 ||
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
        <td colspan="17" class="text-center text-muted py-4">
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
  // Apply color class based on stanine band
  // 1-3 Below Average, 4-6 Average, 7-9 Above Average
  // ---------------------------------------------------------
  function getStanineBandClass(stanine) {
    const value = Number(stanine);

    if (!value) return "";

    if (value <= 3) return "ngrt-band-below";
    if (value <= 6) return "ngrt-band-average";

    return "ngrt-band-above";
  }

  // ---------------------------------------------------------
  // Render one NGRT assessment set of cells
  // Example: NGRT-A SAS, Stanine, Reading Age, Progress
  // ---------------------------------------------------------
  function renderNgrtCells(result) {
    const bandClass = getStanineBandClass(result.stanine);

    return `
      <td>${formatValue(result.sas)}</td>
      <td class="${bandClass}">${formatValue(result.stanine)}</td>
      <td>${formatValue(result.reading_age)}</td>
      <td>${formatValue(result.progress_category)}</td>
    `;
  }

  // ---------------------------------------------------------
  // Load combined NGRT-A, NGRT-B, NGRT-C data from Flask API
  // ---------------------------------------------------------
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
                <a
                    class="btn btn-sm btn-primary"
                    href="/reports/external/ngrt-individual/${student.student_id}"
                    target="_blank"
                >
                    PDF
                </a>
            </td>
            <td>
                <span class="text-dark font-weight-bold">
                    ${formatValue(student.student_id)}
                </span>
                <span class="text-primary font-weight-bold">
                    ${formatValue(student.name)}
                </span><br/>
                ${formatValue(student.gender)},&nbsp;${formatValue(student.nationality)}<br/>
                ${formatValue(student.status)},&nbsp;${formatValue(student.yrgrp)}
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

  // ---------------------------------------------------------
  // Debounce typing in search box
  // This avoids sending an API request every single key press.
  // ---------------------------------------------------------
  let searchTimer = null;

  function handleSearchInput() {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(function () {
      loadNgrtCombinedData();
    }, 300);
  }

  // ---------------------------------------------------------
  // Event listeners
  // ---------------------------------------------------------
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

  // Initial table message
  setTableMessage("Select filters to view NGRT data.");
});