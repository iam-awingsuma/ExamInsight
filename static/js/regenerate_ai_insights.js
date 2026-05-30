document.addEventListener("DOMContentLoaded", function () {
  // ---------------------------------------------------------
  // Reusable button label with icon
  // ---------------------------------------------------------
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

  // ---------------------------------------------------------
  // Render AI statement as bullet points
  // ---------------------------------------------------------
  function renderInsightBullets(statementText, targetList) {
    // Clear existing insight content
    targetList.innerHTML = "";

    // Handle empty response safely
    if (!statementText || statementText.trim().length === 0) {
      const li = document.createElement("li");
      li.textContent = "No AI insight is currently available.";
      targetList.appendChild(li);
      return;
    }

    // Split AI response by lines
    const lines = statementText
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(function (line) {
        return line.length > 0;
      });

    // Add each line as a list item
    lines.forEach(function (line) {
      const cleanText = line.replace(/^[-•]\s*/, "").trim();

      if (!cleanText) return;

      const li = document.createElement("li");
      li.textContent = cleanText;

      targetList.appendChild(li);
    });
  }

  // ---------------------------------------------------------
  // Reusable regenerate function
  // ---------------------------------------------------------
  function setupRegenerateInsight(buttonId, listId, apiUrl) {
    const button = document.getElementById(buttonId);
    const targetList = document.getElementById(listId);

    // Stop if this button/list does not exist on the page
    if (!button || !targetList) return;

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

    button.addEventListener("click", regenerateInsight);

    // Initial button label
    setRegenerateButtonLabel(button, "Generate", "100px");
  }

  // ---------------------------------------------------------
  // Register regenerate buttons
  // ---------------------------------------------------------

  // Attainment Distribution
  setupRegenerateInsight(
    "regenerateAttainmentInsightBtn",
    "attainmentInsightList",
    "/api/reports/external/ngrt/regenerate-attainment-insight"
  );

  // Progress Distribution
  setupRegenerateInsight(
    "regenerateProgressInsightBtn",
    "progressInsightList",
    "/api/reports/external/ngrt/regenerate-progress-insight"
  );

  // Trends in Attainment
  setupRegenerateInsight(
    "regenerateTrendsInsightBtn",
    "trendsInsightList",
    "/api/reports/external/ngrt/regenerate-trends-insight"
  );

  // Reading Literacy Thresholds
  setupRegenerateInsight(
    "regenerateThresholdInsightBtn",
    "thresholdInsightList",
    "/api/reports/external/ngrt/regenerate-threshold-insight"
  );
});