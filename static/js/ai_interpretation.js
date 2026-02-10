/**
 * AI Performance Interpretation Module
 * Integrates ChatGPT analysis into student insights pages
 */

class AIPerformanceInterpreter {
    constructor(options = {}) {
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
        
        try {
            this._showLoading();
            
            const response = await fetch(`${this.apiEndpoint}${queryString}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate interpretation');
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

    /**
     * Initialize button click handler
     */
    init() {
        const button = document.querySelector(this.buttonSelector);
        if (!button) return;

        button.addEventListener('click', async () => {
            // Get current filter values from page
            const studentId = document.getElementById('student')?.value;
            const yrgrp = document.getElementById('yrgrp')?.value;
            
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

    /**
     * Auto-load interpretation when filters change
     */
    initAutoLoad() {
        const studentSelect = document.getElementById('student');
        const yearSelect = document.getElementById('yrgrp');
        
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
                console.error('Auto-load failed:', error);
            }
        };
        
        studentSelect?.addEventListener('change', loadHandler);
        yearSelect?.addEventListener('change', loadHandler);
    }

    // Private helper methods
    _buildQueryString(params) {
        const queryParams = Object.entries(params)
            .filter(([_, value]) => value)
            .map(([key, value]) => `${key}=${encodeURIComponent(value)}`);
        
        return queryParams.length ? '?' + queryParams.join('&') : '';
    }

    _showLoading() {
        const loading = document.querySelector(this.loadingSelector);
        const result = document.querySelector(this.resultSelector);
        
        if (loading) loading.style.display = 'block';
        if (result) result.style.display = 'none';
    }

    _hideLoading() {
        const loading = document.querySelector(this.loadingSelector);
        if (loading) loading.style.display = 'none';
    }

    _showResult(interpretation) {
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);
        
        if (text) text.textContent = interpretation;
        if (result) result.style.display = 'block';
    }

    _showError(message) {
        const result = document.querySelector(this.resultSelector);
        const text = document.querySelector(this.textSelector);
        
        if (text) {
            text.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> ${message}</span>`;
        }
        if (result) result.style.display = 'block';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Create interpreter instance
    const aiInterpreter = new AIPerformanceInterpreter();
    
    // Initialize button handler
    aiInterpreter.init();
    
    // Optional: Enable auto-load functionality
    // Uncomment the line below to auto-load interpretations when filters change
    // aiInterpreter.initAutoLoad();
});

// Export for use in modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIPerformanceInterpreter;
}
