/**
 * ---------------------------------------------------------
 * AI External Performance Interpreter
 * Supports NGRT-A, NGRT-B, NGRT-C datasets
 * ---------------------------------------------------------
 */
class AIExternalPerformanceInterpreter {

    constructor(options = {}) {

        this.apiEndpoint = options.apiEndpoint || '/api/interpret_external_performance';
        this.loadingSelector = options.loadingSelector || '#ai-loading';
        this.resultSelector = options.resultSelector || '#ai-interpretation';
        this.buttonSelector = options.buttonSelector || '#ai-interpret-btn';
        this.textSelector = options.textSelector || '#interpretation-text';

        // detect dataset from HTML container
        const main = document.getElementById("extl_si_analytics");
        this.dataset = main?.getAttribute("data-ngrt") || "ngrta";
    }

    // Generate AI interpretation
    async generateInterpretation(params = {}) {
        params.dataset = this.dataset;
        const queryString = this._buildQueryString(params);

        try {
            this._showLoading();
            const response = await fetch(`${this.apiEndpoint}${queryString}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Failed to generate interpretation");
            }

            // Show AI analysis/interpretation result
            this._showResult(data.interpretation);

            // Update the reading profile card
            const profileCategory = document.getElementById("rdg_profile_category");
            const profileDescription = document.getElementById("rdg_profile_description");
            const profileAI = document.getElementById("rdg_profile_ai_recommendations");
            const profileResult = document.getElementById("rdg_profile_result");

            if (data.student_id) {
                if (profileCategory) {
                    const noProfile = !data.reader_profile;
                    // reset previous badge styles
                    profileCategory.classList.remove(
                        "badge",
                        "bg-gradient-danger",
                        "bg-gradient-info"
                    );
                    if (!noProfile && (this.dataset === "ngrtb" || this.dataset === "ngrtc")) {
                        // profile exists for NGRT-B or NGRT-C
                        profileCategory.textContent = data.reader_profile;
                        profileCategory.classList.add("badge", "bg-gradient-info", "px-2","py-1", "text-sm", "text-capitalize");
                    } else { // no profile for NGRT-A or missing reader profile
                        profileCategory.textContent = "No reading profile available for NGRT-A";
                        profileCategory.classList.add("badge", "bg-gradient-danger", "px-2","py-1", "text-sm", "text-capitalize");
                    }
                }

                if (profileDescription) {
                    profileDescription.textContent = data.profile_description || "No profile description available";
                }

                if (profileAI) {
                    profileAI.textContent = data.profile_ai_interpretation || "No AI interpretation available for this reading profile";
                }

                if (profileResult) {
                    profileResult.style.display = "block";
                }
            }

            return data;

        } catch (error) {
            this._showError(error.message);
            throw error;
        } finally {
            this._hideLoading();
        }
    }

    // Button click handler
    init() {
        const button = document.querySelector(this.buttonSelector);
        if (!button) return;

        button.addEventListener("click", async () => {

            const title = document.getElementById("ai_title");

            const studentSelect = document.getElementById("student");
            const yrgrpSelect = document.getElementById("yrgrp");

            const studentId = studentSelect?.value;
            const yrgrp = yrgrpSelect?.value;

            const params = {};

            // dataset always included
            params.dataset = this.dataset;

            const datasetName =
                this.dataset.slice(0, -1).toUpperCase() + "-" + this.dataset.slice(-1).toUpperCase();

            // Student selected
            if (studentId && studentId !== "all") {
                params.student_id = studentId;
                let studentName = studentSelect?.selectedOptions[0]?.text;
                studentName = toTitleCase(studentName);
                if (title) {
                    title.textContent = `AI Analysis: ${studentName} (${datasetName})`;
                }
            }
            // Year group selected
            else if (yrgrp && yrgrp !== "all") {
                params.yrgrp = yrgrp;
                if (title) {
                    title.textContent = `AI Analysis: Year ${yrgrp} Performance (${datasetName})`;
                }
            }
            // Cohort (All Year Groups)
            else {
                if (title) {
                    title.textContent = `AI Analysis: Cohort Performance (${datasetName})`;
                }
            }

            button.disabled = true;

            try {
                await this.generateInterpretation(params);
            } catch (error) {
                console.error("AI analysis failed.", error);
            } finally {
                button.disabled = false;
            }
        });
    }

    // Auto-load when filters change
    initAutoLoad() {
        const studentSelect = document.getElementById("student");
        const yearSelect = document.getElementById("yrgrp");

        const loadHandler = async () => {
            const studentId = studentSelect?.value;
            const yrgrp = yearSelect?.value;

            if (!studentId && !yrgrp) return;

            const params = {};

            if (studentId) params.student_id = studentId;
            if (yrgrp) params.yrgrp = yrgrp;

            try {
                await this.generateInterpretation(params);
            } catch (error) {
                console.error("AI auto-load failed:", error);
            }
        };
        studentSelect?.addEventListener("change", loadHandler);
        yearSelect?.addEventListener("change", loadHandler);
    }

    // Helper Methods
    _buildQueryString(params) {
        const queryParams = Object.entries(params)
            .filter(([_, value]) => value)
            .map(([key, value]) => `${key}=${encodeURIComponent(value)}`);

        return queryParams.length ? "?" + queryParams.join("&") : "";
    }

    _showLoading() {
        const loading = document.querySelector(this.loadingSelector);
        const result = document.querySelector(this.resultSelector);

        if (loading) loading.style.display = "block";
        if (result) result.style.display = "none";

        const profileLoading = document.getElementById("rdg_profile_loading");
        const profileResult = document.getElementById("rdg_profile_result");

        if (profileLoading) profileLoading.style.display = "block";
        if (profileResult) profileResult.style.display = "none";
    }

    _hideLoading() {
        const loading = document.querySelector(this.loadingSelector);
        if (loading) loading.style.display = "none";

        const profileLoading = document.getElementById("rdg_profile_loading");
        if (profileLoading) profileLoading.style.display = "none";
    }

    _showResult(interpretation) {
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);

        if (text) text.textContent = interpretation;

        if (result) result.style.display = "block";
    }

    _showError(message) {
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);

        if (text) {
            text.innerHTML = `
                <span class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${message}
                </span>
            `;
        }
        if (result) result.style.display = "block";
    }
}

function toTitleCase(name) {
    return name
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

// Initialize automatically
document.addEventListener("DOMContentLoaded", function () {
    // AI interpretation of cohort performance upon page load
    const aiInterpreter = new AIExternalPerformanceInterpreter();
    aiInterpreter.init();
});

// Export for modules if needed
if (typeof module !== "undefined" && module.exports) {
    module.exports = AIExternalPerformanceInterpreter;
}