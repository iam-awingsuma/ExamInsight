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
  
  // Arrays for percentages (y-values) and hover text
  const male = [0,0,0], female = [0,0,0];
  const maleHover = ["","",""], femaleHover = ["","",""];

  // Map rows
  data.forEach(r => {
    const i = idx[r.subject];
    if (i === undefined) return;

    // Prefer new *_pct fields; fall back to legacy male/female if present
    const mp = Number(r.male_pct ?? r.male ?? 0);
    const fp = Number(r.female_pct ?? r.female ?? 0);

    male[i] = Number.isFinite(mp) ? mp : 0;
    female[i] = Number.isFinite(fp) ? fp : 0;

    // Build rich hover with numerators/totals when available
    const mN = (r.male_n ?? null),   mT = (r.male_total ?? null);
    const fN = (r.female_n ?? null), fT = (r.female_total ?? null);

    maleHover[i] = (mN !== null && mT !== null)
      ? `${subjects[i]}<br><b>Male:</b> ${mN}/${mT} (${male[i].toFixed(1)}%)`
      : `${subjects[i]}<br><b>Male:</b> ${male[i].toFixed(1)}%`;

    femaleHover[i] = (fN !== null && fT !== null)
      ? `${subjects[i]}<br><b>Female:</b> ${fN}/${fT} (${female[i].toFixed(1)}%)`
      : `${subjects[i]}<br><b>Female:</b> ${female[i].toFixed(1)}%`;
  });

  // Build traces (clustered side-by-side)
  const traces = [
    { x: subjects, y: male, type:"bar", name:`Male ${labelSuffix}`,
      marker:{ color:"#F8DE22" },
      text: male.map(v => `${(Number.isFinite(v)?v:0).toFixed(1)}%`),
      textposition:"outside",
      hoverinfo:"text",
      hovertext: maleHover,
      offsetgroup:"male", legendgroup:"male"
    },
    { x: subjects, y: female, type:"bar", name:`Female ${labelSuffix}`,
      marker:{ color:"#FF6500" },
      text: female.map(v => `${(Number.isFinite(v)?v:0).toFixed(1)}%`),
      textposition:"outside",
      hoverinfo:"text",
      hovertext: femaleHover,
      offsetgroup:"female", legendgroup:"female"
    }
  ];

  // Layout
  Plotly.newPlot(elId, traces, {
    autosize:true,
    barmode:"group",
    bargap:0.25,
    bargroupgap:0.15,
    yaxis:{ title:"Percent of Gender Total", range:[0,110], ticksuffix:"%" },
    margin:{ t:20, r:20, b:60, l:60 },
    legend:{ orientation:"h" },
    hoverlabel:{ bgcolor:"#fff", bordercolor:"#ccc", align:"left" },
    hovermode:"x unified"
  }, { displayModeBar:false, responsive:true });

  // Keep the chart/graph responsive
  window.addEventListener("resize", () => Plotly.Plots.resize(el));
  new ResizeObserver(() => Plotly.Plots.resize(el)).observe(el);
};

// Tiny auto-init (a one-time hook)
// document.addEventListener("DOMContentLoaded", () => {
//   document.querySelectorAll('[data-render="gender-threshold-bars"]').forEach(node => {
//     // call the same function; args come from data-attributes
//     window.renderGenderThresholdBars(undefined, node.id, undefined);
//   });
// });
