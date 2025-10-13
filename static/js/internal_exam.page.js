(function () {
  function onReady(fn){ document.readyState!=='loading' ? fn() : document.addEventListener('DOMContentLoaded', fn, {once:true}); }
  function whenPlotlyReady(fn){
    if (window.Plotly) return fn();
    const t = setInterval(()=>{ if(window.Plotly){ clearInterval(t); fn(); } }, 50);
    setTimeout(()=>clearInterval(t), 5000);
  }
  function renderAll(){
    if (document.getElementById('chart_perf_over_time') && window.renderPerfOverTime) window.renderPerfOverTime();
    if (document.getElementById('chart_cohort_attainment') && window.renderCohortAttainment) window.renderCohortAttainment();
    if (document.getElementById('chart_cohort_progress') && window.renderCohortProgress) window.renderCohortProgress();
  }
  onReady(()=>{ if (window.lucide) window.lucide.createIcons(); });
  onReady(()=> whenPlotlyReady(renderAll));
})();
