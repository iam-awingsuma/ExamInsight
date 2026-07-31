// Render line chart for average attainment by year group
function renderLineAttainment() {

    const data = window.avgByYearData || []; // Fallback to empty array if data is not available

    if (!data.length) return; // Exit if no data is available

    const x = data.map(d => d.yrgrp); // Extract year group labels for x-axis

    // Create traces for English trace
    const engTrace = {
        x: x,
        y: data.map(d => d.eng_avg),
        mode: "lines+markers",
        name: "English",
        line: { color: "#0BA6DF", width: 3 },
        marker: { size: 8 },
        hoverlabel: {font: { size: 11 }},
        hovertemplate: "English: <b>%{y:.0f}%</b><extra></extra>",
    };

    // Create traces for Maths trace
    const mathsTrace = {
        x: x,
        y: data.map(d => d.maths_avg),
        mode: "lines+markers",
        name: "Maths",
        line: { color: "#FCB53B", width: 3 },
        marker: { size: 8 },
        hoverlabel: {font: { size: 11 }},
        hovertemplate: "Maths: <b>%{y:.0f}%</b><extra></extra>",
    };

    // Create traces for Science trace
    const sciTrace = {
        x: x,
        y: data.map(d => d.sci_avg),
        mode: "lines+markers",
        name: "Science",
        line: { color: "#A7E399", width: 3 },
        marker: { size: 8 },
        hoverlabel: {font: { size: 11 }},
        hovertemplate: "Science: <b>%{y:.0f}%</b><extra></extra>",
    };

    // Define the layout for the Plotly chart
    const layout = {
        autosize: true,
        margin: { l: 70, r: 30, t: 20, b: 70 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",

        yaxis: {
            title: "Average Attainment (%)",
            range: [0, 100]
        },

        hovermode: "x unified",
        legend: { orientation: "h", y: -0.2, font: { size: 11 } },
        font: { size: 13 }
    };

    // Render the line chart using Plotly
    Plotly.newPlot(
        "line_attainment_chart",
        [engTrace, mathsTrace, sciTrace],
        layout,
        { displayModeBar: false, responsive: true }
    );
}

// AUTO LOAD
document.addEventListener("DOMContentLoaded", renderLineAttainment);