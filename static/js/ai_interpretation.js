/**
 * AI Performance Interpretation Module
 * Integrates ChatGPT analysis into student insights page of Internal Assmt Analytics.
 */
class AIPerformanceInterpreter {
    constructor(options = {}) { // Accept optional configuration parameters
        this.apiEndpoint = '/api/interpret_performance';
        this.loadingSelector = options.loadingSelector || '#ai-loading';
        this.resultSelector = options.resultSelector || '#ai-interpretation';
        this.buttonSelector = options.buttonSelector || '#ai-interpret-btn';
        this.textSelector = options.textSelector || '#interpretation-text';
    }

    /**
     * Generate AI interpretation for given parameters
     * @param {Object} params - Query parameters {student_id, yrgrp}
     * @returns {Promise}
     */
    async generateInterpretation(params = {}) {
        const queryString = this._buildQueryString(params);
        
        try { // Show loading indicator
            this._showLoading();
            
            const response = await fetch(`${this.apiEndpoint}${queryString}`);
            const data = await response.json();
            
            if (!response.ok) { // Handle API errors
                throw new Error(data.error || 'Failed to generate interpretation');
            }
            
            this._showResult(data.interpretation);
            return data;
            
        } catch (error) { // Display error message
            this._showError(error.message);
            throw error;
        } finally { // Hide loading indicator
            this._hideLoading();
        }
    }

    /**
     * Initialize button click handler
     */
    init() {
        const button = document.querySelector(this.buttonSelector);
        if (!button) return;

        button.addEventListener('click', async () => {
            // Get references to title and filter elements
            const title = document.getElementById("ai_title");
            const studentSelect = document.getElementById("student");
            const yrgrpSelect = document.getElementById("yrgrp");

            // Get current filter values from page
            const studentId = document.getElementById('student')?.value;
            const yrgrp = document.getElementById('yrgrp')?.value;
            
            const params = {};

            if (studentId && studentId !== "all") { // If a specific student is selected, set the student_id parameter
                params.student_id = studentId;

                let studentName = studentSelect?.selectedOptions[0]?.text;
                studentName = toTitleCase(studentName);
                
                if (title) {
                    title.textContent = `AI Analysis: ${studentName} ${yrgrp?.toUpperCase()}`;
                }
            }
            else if (yrgrp && yrgrp !== "all") { // If a specific year group is selected, set the yrgrp parameter
                params.yrgrp = yrgrp;
                if (title) {
                    title.textContent = `AI Analysis: Year ${yrgrp?.toUpperCase()} Performance`;
                }
            }
            else { // If no specific student or year group is selected, show a generic title
                if (title) {
                    title.textContent = `AI Analysis: Cohort Performance`;
                }
            }
            
            button.disabled = true;
            try {
                await this.generateInterpretation(params);
            } finally {
                button.disabled = false;
            }
        });
    }

    /**
     * Auto-load interpretation when filters change
     */
    initAutoLoad() { // Set up event listeners for student and year group filter changes
        const studentSelect = document.getElementById('student');
        const yearSelect = document.getElementById('yrgrp');
        
        const loadHandler = async () => { // Get current filter values from page
            const studentId = studentSelect?.value;
            const yrgrp = yearSelect?.value;
            
            if (!studentId && !yrgrp) return;
            
            const params = {};
            if (studentId) params.student_id = studentId;
            if (yrgrp) params.yrgrp = yrgrp;
            
            try {
                await this.generateInterpretation(params);
            } catch (error) {
                console.error('Auto-load failed:', error);
            }
        };
        
        // Attach event listeners to filter elements to trigger auto-load on change
        studentSelect?.addEventListener('change', loadHandler);
        yearSelect?.addEventListener('change', loadHandler);
    }

    // Private helper methods
    _buildQueryString(params) { // Build query string from parameters, filtering out empty values
        const queryParams = Object.entries(params)
            .filter(([_, value]) => value)
            .map(([key, value]) => `${key}=${encodeURIComponent(value)}`);
        
        return queryParams.length ? '?' + queryParams.join('&') : '';
    }

    _showLoading() { // Show loading indicator and hide result section
        const loading = document.querySelector(this.loadingSelector);
        const result = document.querySelector(this.resultSelector);
        
        if (loading) loading.style.display = 'block';
        if (result) result.style.display = 'none';
    }

    _hideLoading() { // Hide loading indicator
        const loading = document.querySelector(this.loadingSelector);
        if (loading) loading.style.display = 'none';
    }

    _showResult(interpretation) { // Display the AI interpretation result in the designated section
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);
        
        if (text) text.textContent = interpretation;
        if (result) result.style.display = 'block';
    }

    _showError(message) { // Display error message in the result section
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);
        
        if (text) {
            text.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> ${message}</span>`;
        }
        if (result) result.style.display = 'block';
    }
}

// Utility function to convert a string to Title Case
function toTitleCase(name) {
    return name
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Create interpreter instance
    const aiInterpreter = new AIPerformanceInterpreter();
    
    // Initialize button handler
    aiInterpreter.init();
});

// Export for use in modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIPerformanceInterpreter;
}
