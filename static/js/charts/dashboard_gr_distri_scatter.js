// Render internal scatter plot for grade distribution
function renderInternalScatter() {

    // Get the chart container and student data
    const chartId = "internal_scatter_chart";
    const allStudents = window.internalScatterData || [];

    if (!allStudents.length) { // Exit if no student data is available
        Plotly.react(chartId, [], {});
        return;
    }

    const x = allStudents.map((_, i) => i + 1); // Create an array of student indices for the x-axis
    const names = allStudents.map(s => `${s.forename} ${s.surname}`); // Create an array of student names for hover text

    // Create traces for English subject with scatter plot markers
    const engTrace = {
        x: x,
        y: allStudents.map(s => s.eng_currGr),
        mode: "markers",
        type: "scatter",
        name: "English",
        text: names,
        hoverlabel: {font: { size: 11 }},
        hovertemplate:
            "<b>%{text}</b><br>English: %{y}<extra></extra>",
        marker: { size: 10, color: "#0BA6DF", opacity: 0.7 }
    };

    // Create traces for Maths subject with scatter plot markers
    const mathsTrace = {
        x: x,
        y: allStudents.map(s => s.maths_currGr),
        mode: "markers",
        type: "scatter",
        name: "Maths",
        text: names,
        hoverlabel: {font: { size: 11 }},
        hovertemplate:
            "<b>%{text}</b><br>Maths: %{y}<extra></extra>",
        marker: { size: 10, color: "#FCB53B", opacity: 0.7 }
    };

    // Create traces for Science subject with scatter plot markers
    const sciTrace = {
        x: x,
        y: allStudents.map(s => s.sci_currGr),
        mode: "markers",
        type: "scatter",
        name: "Science",
        text: names,
        hoverlabel: {font: { size: 11 }},
        hovertemplate:
            "<b>%{text}</b><br>Science: %{y}<extra></extra>",
        marker: { size: 10, color: "#A7E399", opacity: 0.7 }
    };

    // Define the layout for the Plotly scatter plot
    const layout = {
        autosize: true,
        margin: { l: 70, r: 30, t: 20, b: 70 },

        yaxis: {
            title: "Grade",
            type: "category",
            categoryorder: "array",
            categoryarray: ["A*", "A", "B", "C", "D", "E"],
            autorange: "reversed",
        },

        hovermode: "closest",
        legend: { orientation: "h", y: -0.2, font: { size: 11 } }
    };

    // Render the scatter plot using Plotly
    Plotly.react(chartId, [engTrace, mathsTrace, sciTrace], layout, {
        displayModeBar: false,
        responsive: true
    });
}