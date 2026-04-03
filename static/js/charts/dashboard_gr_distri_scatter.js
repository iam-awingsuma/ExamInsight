function renderInternalScatter() {

    const chartId = "internal_scatter_chart";
    const allStudents = window.internalScatterData || [];

    if (!allStudents.length) {
        Plotly.react(chartId, [], {});
        return;
    }

    const x = allStudents.map((_, i) => i + 1);
    const names = allStudents.map(s => `${s.forename} ${s.surname}`);

    const engTrace = {
        x: x,
        y: allStudents.map(s => s.eng_currGr),
        mode: "markers",
        type: "scatter",
        name: "English",
        text: names,
        hovertemplate:
            "<b>%{text}</b><br>English: %{y}<extra></extra>",
        marker: { size: 10, color: "#0BA6DF", opacity: 0.7 }
    };

    const mathsTrace = {
        x: x,
        y: allStudents.map(s => s.maths_currGr),
        mode: "markers",
        type: "scatter",
        name: "Maths",
        text: names,
        hovertemplate:
            "<b>%{text}</b><br>Maths: %{y}<extra></extra>",
        marker: { size: 10, color: "#FCB53B", opacity: 0.7 }
    };

    const sciTrace = {
        x: x,
        y: allStudents.map(s => s.sci_currGr),
        mode: "markers",
        type: "scatter",
        name: "Science",
        text: names,
        hovertemplate:
            "<b>%{text}</b><br>Science: %{y}<extra></extra>",
        marker: { size: 10, color: "#A7E399", opacity: 0.7 }
    };

    const layout = {
        autosize: true,
        margin: { l: 70, r: 30, t: 20, b: 70 },

        // xaxis: {
        //     title: "<b>Students</b>"
        // },

        yaxis: {
            title: "Grade",
            type: "category",
            categoryorder: "array",
            categoryarray: ["A*", "A", "B", "C", "D", "E"],
            autorange: "reversed",
        },

        hovermode: "closest",
        legend: { orientation: "h", y: -0.2 }
    };

    Plotly.react(chartId, [engTrace, mathsTrace, sciTrace], layout, {
        displayModeBar: false,
        responsive: true
    });
}