// Render clustered bars: Male vs Female percentages by subject for a given threshold payload.
// Expects a JSON blob: [{subject:"English", male:%, female:%}, ...]
window.renderGenderThresholdBars = function (blobId, elId, labelSuffix = "") {
  // Safe reads
  const el = document.getElementById(elId);
  if (!el) return console.error(`[renderGenderThresholdBars] Missing #${elId}`);

  let data = [];
  try { data = JSON.parse(document.getElementById(blobId)?.textContent || "[]"); }
  catch { data = []; }

  // Map to fixed subject order
  const subjects = ["English","Maths","Science"];
  const idx = Object.fromEntries(subjects.map((s,i)=>[s,i]));
  const male = [0,0,0], female = [0,0,0];

  data.forEach(r => {
    const i = idx[r.subject];
    if (i !== undefined) {
      male[i] = Number(r.male ?? 0);
      female[i] = Number(r.female ?? 0);
    }
  });

  // Build traces (clustered side-by-side)
  const traces = [
    { x: subjects, y: male,   type:"bar", name:`Male ${labelSuffix}`,
      marker:{ color:"#4e79a7" },
      text: male.map(v => `${(Number.isFinite(v)?v:0).toFixed(1)}%`),
      textposition:"outside",
      offsetgroup:"male", legendgroup:"male"
    },
    { x: subjects, y: female, type:"bar", name:`Female ${labelSuffix}`,
      marker:{ color:"#f28e2b" },
      text: female.map(v => `${(Number.isFinite(v)?v:0).toFixed(1)}%`),
      textposition:"outside",
      offsetgroup:"female", legendgroup:"female"
    }
  ];

  // Layout
  Plotly.newPlot(elId, traces, {
    autosize:true,
    barmode:"stack",
    barnorm:"percent",
    // bargap:0.25,
    // bargroupgap:0.12,
    yaxis:{ title:"Percent of Gender Total", range:[0,110], ticksuffix:"%" },
    margin:{ t:20, r:20, b:60, l:60 },
    legend:{ orientation:"h" }
  }, { displayModeBar:false, responsive:true });

  // Keep responsive
  window.addEventListener("resize", () => Plotly.Plots.resize(el));
  new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
};
