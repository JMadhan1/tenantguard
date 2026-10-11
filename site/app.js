(function(){
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.kpi-value[data-count]').forEach(function(el){
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target)) return;
    var start = performance.now(), dur = 850;
    function step(now){
      var p = Math.min((now-start)/dur, 1);
      el.textContent = Math.round(target * (1-Math.pow(1-p,3)));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
})();
