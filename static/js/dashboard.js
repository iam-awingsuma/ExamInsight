// JS for dashboard.html — handles tab switching and chart resizing
document.addEventListener("DOMContentLoaded", function () {

  // Tab switching logic for the dashboard
  const tabs = document.querySelectorAll(".ei-tab");
  const sections = document.querySelectorAll(".tab-section");

  // Initialize by showing the first section and setting the first tab as active
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {

      // Switch active tab
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      // Hide all sections
      sections.forEach(sec => sec.classList.add("d-none"));

      // Show selected section
      const target = tab.dataset.tab;
      const section = document.getElementById("section-" + target);

    // Show the selected section and hide others
    section.classList.remove("d-none");
    
    // resize Plotly AFTER showing
    setTimeout(() => {
    if (target === "internal") {
        Plotly.Plots.resize("chart_cohort_attainment");
    }
    }, 200);
    });
  });
});