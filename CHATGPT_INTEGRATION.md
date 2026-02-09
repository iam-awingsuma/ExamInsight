# ChatGPT Integration for Student Performance Analysis

## Overview
This integration connects ExamInsight with OpenAI's ChatGPT to provide AI-powered interpretation and forecasting of student performance data for English, Maths, and Science.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure OpenAI API Key

#### Option A: Using .env file (Recommended)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Get your OpenAI API key from: https://platform.openai.com/api-keys

3. Edit `.env` and add your API key:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### Option B: Using Environment Variable
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Linux/Mac
export OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3. Restart Your Application
```bash
python run.py
```

## API Endpoint

### `/api/interpret_performance`
Generates AI interpretation of student performance data (maximum 5 sentences).

**Method:** `GET`

**Query Parameters:**
- `student_id` (optional): Specific student ID to analyze
- `yrgrp` (optional): Year group to analyze (e.g., "2-A", "3-B")
- If neither is provided, analyzes entire cohort

**Example Requests:**
```javascript
// Analyze specific student
fetch('/api/interpret_performance?student_id=12345')
  .then(response => response.json())
  .then(data => console.log(data.interpretation));

// Analyze year group
fetch('/api/interpret_performance?yrgrp=2-A')
  .then(response => response.json())
  .then(data => console.log(data.interpretation));

// Analyze entire cohort
fetch('/api/interpret_performance')
  .then(response => response.json())
  .then(data => console.log(data.interpretation));
```

**Response Format:**
```json
{
  "interpretation": "The student shows strong performance in Science with 78.5%, demonstrating consistent progress. English performance at 65.2% has improved by +5.3% from previous assessment, indicating positive momentum. Maths scores (62.8%) remain steady but below the 70% threshold, suggesting need for targeted intervention. Progress categories show 2 subjects meeting or exceeding expectations. Forecast: With continued support in Maths, the student is on track to achieve overall proficiency across all subjects by year end.",
  "data_summary": "Performance Analysis for Student ID 12345...",
  "student_id": "12345",
  "yrgrp": null
}
```

## Frontend Integration Examples

### Example 1: Add to Student Insights Page

Add this button to your student insights template:

```html
<div class="card">
    <div class="card-header">
        <h5>AI Performance Interpretation</h5>
    </div>
    <div class="card-body">
        <button id="ai-interpret-btn" class="btn btn-primary">
            <i class="fas fa-robot"></i> Generate AI Insights
        </button>
        <div id="ai-interpretation" class="mt-3" style="display:none;">
            <div class="alert alert-info">
                <strong>AI Analysis:</strong>
                <p id="interpretation-text"></p>
            </div>
        </div>
        <div id="ai-loading" class="mt-3" style="display:none;">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Analyzing...</span>
            </div>
            <span class="ml-2">Generating insights...</span>
        </div>
    </div>
</div>
```

### Example 2: JavaScript Implementation

```javascript
// Add to your existing JavaScript file (e.g., student_insights.js)

document.addEventListener('DOMContentLoaded', function() {
    const interpretBtn = document.getElementById('ai-interpret-btn');
    const interpretDiv = document.getElementById('ai-interpretation');
    const interpretText = document.getElementById('interpretation-text');
    const loadingDiv = document.getElementById('ai-loading');
    
    if (interpretBtn) {
        interpretBtn.addEventListener('click', function() {
            // Get current student_id or yrgrp from page
            const studentId = document.getElementById('student-select')?.value;
            const yrgrp = document.getElementById('year-select')?.value;
            
            // Build query string
            let queryParams = [];
            if (studentId) queryParams.push(`student_id=${studentId}`);
            if (yrgrp) queryParams.push(`yrgrp=${yrgrp}`);
            const queryString = queryParams.length ? '?' + queryParams.join('&') : '';
            
            // Show loading, hide previous results
            loadingDiv.style.display = 'block';
            interpretDiv.style.display = 'none';
            interpretBtn.disabled = true;
            
            // Fetch interpretation
            fetch(`/api/interpret_performance${queryString}`)
                .then(response => response.json())
                .then(data => {
                    loadingDiv.style.display = 'none';
                    interpretBtn.disabled = false;
                    
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        interpretText.textContent = data.interpretation;
                        interpretDiv.style.display = 'block';
                    }
                })
                .catch(error => {
                    loadingDiv.style.display = 'none';
                    interpretBtn.disabled = false;
                    alert('Failed to generate interpretation: ' + error);
                });
        });
    }
});
```

### Example 3: Automatic Loading on Page Load

```javascript
// Automatically load interpretation when page/filters change
function loadAIInterpretation() {
    const studentId = document.getElementById('student-select')?.value;
    const yrgrp = document.getElementById('year-select')?.value;
    
    if (!studentId && !yrgrp) return;
    
    let queryParams = [];
    if (studentId) queryParams.push(`student_id=${studentId}`);
    if (yrgrp) queryParams.push(`yrgrp=${yrgrp}`);
    
    fetch(`/api/interpret_performance?${queryParams.join('&')}`)
        .then(response => response.json())
        .then(data => {
            if (data.interpretation) {
                document.getElementById('ai-interpretation-box').innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-lightbulb"></i>
                        <strong>AI Insights:</strong><br>
                        ${data.interpretation}
                    </div>
                `;
            }
        });
}

// Call when filters change
document.getElementById('student-select')?.addEventListener('change', loadAIInterpretation);
document.getElementById('year-select')?.addEventListener('change', loadAIInterpretation);
```

## What the AI Analyzes

The ChatGPT integration analyzes:
1. **Current Performance**: Average scores for English, Maths, and Science
2. **Progress Tracking**: Comparison between previous and current assessment results
3. **Progress Categories**: Distribution of Below Expected, Expected, and Above Expected performance
4. **Strengths & Weaknesses**: Identifies highest and lowest performing subjects
5. **Trends**: Most improved subjects and areas needing attention
6. **Forecast**: Predictions about future performance based on current trajectory

## Sample AI Interpretations

**For Individual Student:**
> "The student demonstrates exceptional performance in Science (85%) and solid English skills (72%), both showing positive growth trajectories. Mathematics requires immediate intervention at 58%, despite a +3% improvement from last term. The student meets expected progress in 2 out of 3 subjects, indicating overall satisfactory development. With focused support in Maths through individualized tutoring and practice, the student is projected to achieve proficiency across all subjects within two terms."

**For Year Group:**
> "Year Group 2-A shows strong cohort performance with an overall average of 71.4% across all subjects. Science leads at 75.2%, followed closely by English at 72.1%, while Maths lags at 66.9%. Progress data reveals 68% of students meeting or exceeding expectations, a positive indicator of teaching effectiveness. The 5.2% average improvement from previous assessments suggests effective pedagogical strategies are in place. Focus areas should include targeted Maths interventions for students below the 60% threshold to elevate cohort-wide proficiency."

## Troubleshooting

### Error: "OpenAI API key not configured"
- Ensure you've added `OPENAI_API_KEY` to your `.env` file
- Restart your Flask application after adding the key

### Error: "No data found"
- Verify that the student_id or yrgrp exists in the database
- Ensure InternalExam records exist for the specified criteria

### Error: "OpenAI API error: Rate limit exceeded"
- You've exceeded your OpenAI API quota
- Check your usage at https://platform.openai.com/usage
- Consider upgrading your OpenAI plan or implementing caching

### Cost Considerations
- Each interpretation costs approximately $0.001-0.003 USD (using gpt-4o-mini)
- Consider caching interpretations to reduce API calls
- Monitor usage through OpenAI dashboard

## Security Best Practices

1. **Never commit your API key** to version control
2. Add `.env` to your `.gitignore` file
3. Use environment variables in production
4. Rotate API keys regularly
5. Set usage limits in OpenAI dashboard

## Advanced Customization

To customize the AI's analysis style, edit the system prompt in [routes.py](apps/home/routes.py):

```python
{
    "role": "system",
    "content": "Your custom instructions here..."
}
```

You can adjust:
- Tone (professional, casual, technical)
- Focus areas (more emphasis on specific subjects)
- Output format (bullet points, paragraphs)
- Length (though keep to 5 sentences max per requirement)
