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
            this._showResult(data.interpretation);

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
            const studentId = document.getElementById("student")?.value;
            const yrgrp = document.getElementById("yrgrp")?.value;
            const params = {};

            if (studentId) params.student_id = studentId;
            if (yrgrp) params.yrgrp = yrgrp;

            button.disabled = true;

            try {
                await this.generateInterpretation(params);
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
    }


    _hideLoading() {
        const loading = document.querySelector(this.loadingSelector);

        if (loading) loading.style.display = "none";
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


// Initialize automatically
document.addEventListener("DOMContentLoaded", function () {
    // AI interpretation of cohort performance upon page load
    // window.aiInterpreter = new AIExternalPerformanceInterpreter();
    // window.aiInterpreter.init();

    const aiInterpreter = new AIExternalPerformanceInterpreter();
    aiInterpreter.init();
    // Optional auto load
    // aiInterpreter.initAutoLoad();
});

// Export for modules if needed
if (typeof module !== "undefined" && module.exports) {
    module.exports = AIExternalPerformanceInterpreter;
}