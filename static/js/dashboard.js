document.addEventListener("DOMContentLoaded", function () {

  const tabs = document.querySelectorAll(".ei-tab");
  const sections = document.querySelectorAll(".tab-section");

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

    // const activeSection = document.getElementById("section-" + target);
    section.classList.remove("d-none");

    //   if (activeSection) {
    //     activeSection.classList.remove("d-none");
    //   }
    // 🔥 resize Plotly AFTER showing
    setTimeout(() => {
    if (target === "internal") {
        Plotly.Plots.resize("chart_cohort_attainment");
    }
    }, 200);
    });
  });
});