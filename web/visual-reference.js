/* Progressive enhancement: all evidence and default charts exist without JS. */
(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let manualReduce = false;
  const motionOff = () => reduced.matches || manualReduce;
  const animateChange = (el, from, to) => {
    if (!motionOff() && typeof el.animate === 'function') {
      el.getAnimations().forEach(a => a.cancel());
      el.animate([{transform:`scaleX(${from})`},{transform:`scaleX(${to})`}],
        {duration:420,easing:'cubic-bezier(.16,1,.3,1)'});
    }
  };
  document.querySelectorAll('[data-comparison-chart]').forEach(chart => {
    const buttons = [...chart.querySelectorAll('[data-metric]')];
    const rows = [...chart.querySelectorAll('.vr-chart-row')];
    const comparator = chart.querySelector('.vr-comparator');
    const result = chart.querySelector('.vr-comparison-result');
    let data;
    try { data=JSON.parse(chart.querySelector('.vr-chart-data').textContent); } catch { return; }
    const metrics=data.metrics,names=data.labels;
    if (!metrics || !Array.isArray(names) || names.length!==rows.length ||
        Object.values(metrics).some(m=>!Array.isArray(m.values)||m.values.length!==rows.length||
          !Number.isFinite(m.max)||m.max<=0||m.values.some(v=>!Number.isFinite(v)||v<0||v>m.max))||
        buttons.some(b=>!metrics[b.dataset.metric])) return;
    let selected = buttons.find(b=>b.getAttribute('aria-pressed')==='true')?.dataset.metric || buttons[0].dataset.metric;
    function update() {
      const m=metrics[selected],c=Number(comparator.value);
      chart.querySelector('.vr-chart-unit').textContent=`${m.name} · ${m.unit} ${data.functionalUnit}`;
      chart.querySelector('.vr-axis-max').textContent=`${m.max} ${m.unit}`;
      chart.querySelectorAll('.vr-track').forEach(t=>t.style.background='none');
      rows.forEach((row,i)=>{
        const bar=row.querySelector('.vr-bar');
        const previous=parseFloat(bar.dataset.fraction || (parseFloat(bar.style.getPropertyValue('--value'))/100));
        const fraction=m.values[i]/m.max;
        bar.style.width='100%';bar.style.transform=`scaleX(${fraction})`;bar.dataset.fraction=String(fraction);
        row.querySelector('b').textContent=m.values[i].toFixed(2);
        row.classList.toggle('is-comparator',i===c);
        row.classList.toggle('is-muted',i!==0&&i!==c);
        animateChange(bar,previous,fraction);
      });
      buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.metric===selected)));
      const difference=Math.round((1-m.values[0]/m.values[c])*100);
      result.textContent=m.values[c]===0?'Relative comparison unavailable for a zero baseline.':`${data.comparisonLabel}: ${Math.abs(difference)}% ${difference>=0?'lower':'higher'} than ${names[c]} in this model.`;
      result.hidden=false;
    }
    buttons.forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.metric;update();}));
    comparator.addEventListener('change',update);
    chart.querySelector('.vr-explorer-controls').hidden=false;
    update();
  });
  // Explicit, silent playback explains the three claims; never auto-starts.
  const play=document.querySelector('.vr-play');
  const frames=[...document.querySelectorAll('[data-story]')];
  const status=document.querySelector('.vr-story-status');
  let timer=null,step=0;
  function stop(){clearInterval(timer);timer=null;frames.forEach(f=>f.classList.remove('is-playing'));if(play)play.textContent='Play 12-second overview';}
  function show(){frames.forEach((f,i)=>f.classList.toggle('is-playing',i===step));status.textContent=`${step+1} of 3 · ${frames[step].querySelector('h3').textContent}`;}
  if(play&&frames.length){
    document.querySelector('.vr-story-controls').hidden=false;
    play.addEventListener('click',()=>{if(timer){stop();status.textContent='Overview stopped.';return;}step=0;show();play.textContent='Stop overview';timer=setInterval(()=>{step++;if(step===frames.length){stop();status.textContent='Overview complete. Explore the sources below.';}else show();},4000);});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();status.textContent='Overview paused. Play to restart.';}});
  }
  const motion=document.querySelector('.vr-motion');
  function syncMotion(){document.body.classList.toggle('vr-reduced-motion',motionOff());if(motion){motion.setAttribute('aria-pressed',String(motionOff()));motion.textContent=reduced.matches?'Reduced motion (system)':manualReduce?'Motion reduced':'Reduce motion';}if(motionOff()&&typeof document.getAnimations==='function')document.getAnimations().forEach(a=>a.cancel());}
  if(motion)motion.addEventListener('click',()=>{manualReduce=!manualReduce;syncMotion();});
  if(reduced.addEventListener)reduced.addEventListener('change',syncMotion);else if(reduced.addListener)reduced.addListener(syncMotion);syncMotion();
  function revealHash(){const id=decodeURIComponent(location.hash.slice(1));const target=id&&document.getElementById(id);if(target&&target.tagName==='DETAILS')target.open=true;}
  addEventListener('hashchange',revealHash);revealHash();
  let printClosed=[];
  addEventListener('beforeprint',()=>{stop();printClosed=[...document.querySelectorAll('details:not([open])')];printClosed.forEach(d=>d.open=true);});
  addEventListener('afterprint',()=>{printClosed.forEach(d=>d.open=false);printClosed=[];});
})();
