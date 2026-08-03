(function () {
  // Safely executes a callback when the DOM is fully loaded or already ready
  function onReady(fn){ document.readyState!=='loading' ? fn() : document.addEventListener('DOMContentLoaded', fn, {once:true}); }
  // Polls every 50ms until Plotly is available on window, timing out after 5 seconds
  function whenPlotlyReady(fn){
    if (window.Plotly) return fn();
    const t = setInterval(()=>{ if(window.Plotly){ clearInterval(t); fn(); } }, 50);
    setTimeout(()=>clearInterval(t), 5000);
  }
  // Executes dashboard chart rendering functions if their corresponding DOM elements exist
  function renderAll(){
    if (document.getElementById('chart_perf_over_time') && window.renderPerfOverTime) window.renderPerfOverTime();
    if (document.getElementById('chart_cohort_attainment') && window.renderCohortAttainment) window.renderCohortAttainment();
    if (document.getElementById('chart_cohort_progress') && window.renderCohortProgress) window.renderCohortProgress();
  }
  // Initialize Lucide icons and invoke chart rendering once DOM and Plotly dependencies are ready
  onReady(()=>{ if (window.lucide) window.lucide.createIcons(); });
  onReady(()=> whenPlotlyReady(renderAll));
})();
