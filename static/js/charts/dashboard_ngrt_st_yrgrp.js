async function renderClasswiseAvgNGRTStanineChart() {
    const res = await fetch("/api/classwise_avg_ngrt_stanine");
    const data = await res.json();

    const x = data.year_groups;
    const series = data.series || [];

    const ngrta = series.find(s => s.name === "NGRT-A");
    const ngrtb = series.find(s => s.name === "NGRT-B");
    const ngrtc = series.find(s => s.name === "NGRT-C");

    const ngrtaTrace = {
        x: x,
        y: ngrta ? ngrta.data : [],
        mode: "lines+markers",
        name: "NGRT-A",
        line: { color: "#0BA6DF", width: 3 },
        marker: { size: 8 },
        hovertemplate: "NGRT-A Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
    };

    const ngrtbTrace = {
        x: x,
        y: ngrtb ? ngrtb.data : [],
        mode: "lines+markers",
        name: "NGRT-B",
        line: { color: "#FCB53B", width: 3 },
        marker: { size: 8 },
        hovertemplate: "NGRT-B Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
    };

    const ngrtcTrace = {
        x: x,
        y: ngrtc ? ngrtc.data : [],
        mode: "lines+markers",
        name: "NGRT-C",
        line: { color: "#A7E399", width: 3 },
        marker: { size: 8 },
        hovertemplate: "NGRT-C Avg Stanine: <b>%{y:.2f}</b><extra></extra>",
    };

    const layout = {
        autosize: true,
        width: null,
        margin: { l: 70, r: 30, t: 20, b: 70 },
        yaxis: {
            title: "Average Stanine",
            range: [0, 9]
        },
        hovermode: "x unified",
        legend: { orientation: "h", y: -0.2 },
        font: { size: 13 }
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    const el = document.getElementById("chart-classwise-avg-ngrt-stanine");

    if (el) {
        Plotly.newPlot(el, [ngrtaTrace, ngrtbTrace, ngrtcTrace], layout, config);

        setTimeout(() => Plotly.Plots.resize(el), 100);
        window.addEventListener("resize", () => Plotly.Plots.resize(el));

        const ro = new ResizeObserver(() => Plotly.Plots.resize(el));
        ro.observe(el);
    }
}

document.addEventListener("DOMContentLoaded", renderClasswiseAvgNGRTStanineChart);