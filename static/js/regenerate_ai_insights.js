// Wait for the DOM content to fully load before initializing event listeners and UI handlers
document.addEventListener("DOMContentLoaded", function () {

  // Dynamically updates a button's inner HTML, label text, icon, and explicit pixel width
  function setRegenerateButtonLabel(button, label, widthPx) {
    button.style.width = widthPx;
    button.style.minWidth = widthPx;

    button.innerHTML = `
      <img
        width="20"
        height="20"
        class="me-1"
        src="https://img.icons8.com/?size=100&id=uoGIyWeJmHEc&format=png&color=000000"
        alt="AI Insight Lens"
        title="AI Insight Lens"
      />
      ${label}
    `;
  }

  // Parses raw AI-generated text and populates a target HTML list element with cleaned bullet items
  function renderInsightBullets(statementText, targetList) {
    // Clear existing insight list items
    targetList.innerHTML = "";

    // Render fallback list item if response text is empty or missing
    if (!statementText || statementText.trim().length === 0) {
      const li = document.createElement("li");
      li.textContent = "No AI insight is currently available.";
      targetList.appendChild(li);
      return;
    }

    // Split text by newlines and sanitize individual lines
    const lines = statementText
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(function (line) {
        return line.length > 0;
      });

    // Strip bullet prefix characters (hyphens or dots) and append each line as a <li> item
    lines.forEach(function (line) {
      const cleanText = line.replace(/^[-•]\s*/, "").trim();

      if (!cleanText) return;

      const li = document.createElement("li");
      li.textContent = cleanText;

      targetList.appendChild(li);
    });
  }

  // Binds click handlers to trigger asynchronous AI insight re-generation for specified button and target list IDs
  function setupRegenerateInsight(buttonId, listId, apiUrl) {
    const button = document.getElementById(buttonId);
    const targetList = document.getElementById(listId);

    // Guard clause: abort initialization if required DOM elements are absent
    if (!button || !targetList) return;

    // Async handler function to handle API request state and UI updates
    function regenerateInsight() {
      button.disabled = true;
      setRegenerateButtonLabel(button, "Generating...", "120px");

      fetch(apiUrl)
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Network response was not okay.");
          }

          return response.json();
        })
        .then(function (data) {
          if (!data.success) {
            throw new Error("AI insight generation failed.");
          }

          renderInsightBullets(data.statement, targetList);
        })
        .catch(function (error) {
          console.error("Error regenerating AI insight:", error);
          alert("Unable to regenerate AI insight. Please try again.");
        })
        .finally(function () {
          button.disabled = false;
          setRegenerateButtonLabel(button, "Generate", "100px");
        });
    }

    // Attach click event listener to the trigger button
    button.addEventListener("click", regenerateInsight);

    // Set default initial label and size for the trigger button
    setRegenerateButtonLabel(button, "Generate", "100px");
  }

  // Register AI insight regenerate handlers for Attainment Distribution section
  setupRegenerateInsight(
    "regenerateAttainmentInsightBtn",
    "attainmentInsightList",
    "/api/reports/external/ngrt/regenerate-attainment-insight"
  );

  // Register AI insight regenerate handlers for Progress Distribution section
  setupRegenerateInsight(
    "regenerateProgressInsightBtn",
    "progressInsightList",
    "/api/reports/external/ngrt/regenerate-progress-insight"
  );

  // Register AI insight regenerate handlers for Trends in Attainment section
  setupRegenerateInsight(
    "regenerateTrendsInsightBtn",
    "trendsInsightList",
    "/api/reports/external/ngrt/regenerate-trends-insight"
  );

  // Register AI insight regenerate handlers for Reading Literacy Thresholds section
  setupRegenerateInsight(
    "regenerateThresholdInsightBtn",
    "thresholdInsightList",
    "/api/reports/external/ngrt/regenerate-threshold-insight"
  );
});