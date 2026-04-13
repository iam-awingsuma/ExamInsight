function renderLineAttainment() {

    const data = window.avgByYearData || [];

    if (!data.length) return;

    const x = data.map(d => d.yrgrp);

    const engTrace = {
        x: x,
        y: data.map(d => d.eng_avg),
        mode: "lines+markers",
        name: "English",
        line: { color: "#0BA6DF", width: 3 },
        marker: { size: 8 },
        hovertemplate: "English: <b>%{y:.0f}%</b><extra></extra>",
    };

    const mathsTrace = {
        x: x,
        y: data.map(d => d.maths_avg),
        mode: "lines+markers",
        name: "Maths",
        line: { color: "#FCB53B", width: 3 },
        marker: { size: 8 },
        hovertemplate: "Maths: <b>%{y:.0f}%</b><extra></extra>",
    };

    const sciTrace = {
        x: x,
        y: data.map(d => d.sci_avg),
        mode: "lines+markers",
        name: "Science",
        line: { color: "#A7E399", width: 3 },
        marker: { size: 8 },
        hovertemplate: "Science: <b>%{y:.0f}%</b><extra></extra>",
    };

    const layout = {
        autosize: true,
        margin: { l: 70, r: 30, t: 20, b: 70 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",

        // xaxis: {
        //     title: "<b>Year Group</b>",
        //     categoryorder: "array",
        //     categoryarray: ["2-A", "2-B", "2-C", "2-D", "2-E", "2-F"]
        // },

        yaxis: {
            title: "Average Attainment (%)",
            range: [0, 100]
        },

        hovermode: "x unified",
        legend: { orientation: "h", y: -0.2 },
        font: { size: 13 }
    };

    Plotly.newPlot(
        "line_attainment_chart",
        [engTrace, mathsTrace, sciTrace],
        layout,
        { displayModeBar: false, responsive: true }
    );
}

// AUTO LOAD
document.addEventListener("DOMContentLoaded", renderLineAttainment);