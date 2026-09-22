(() => {
  const responses = {
    health: ['Feeding studies','Encouraging for tested diets.','Direct monitoring offers useful evidence for some complete foods in healthy adult dogs.','Small samples and short follow-up cannot settle lifelong safety.','feeding-sources','Inspect the feeding studies ↗'],
    adequacy: ['Nutrient analysis + quality control','The exact formulation matters.','Laboratory testing checks composition. Formulation expertise and manufacturing controls support consistency.','A label or one successful study does not establish adequacy of every food.','quality-sources','Inspect reviews & food testing ↗'],
    superiority: ['Owner surveys + competing analyses','Association is not causation.','Some surveys report favourable health associations. Reanalyses disagree, and owners self-select into diets.','These data do not prove better health or longer life caused by a plant-based diet.','survey-sources','Compare the survey analyses ↗'],
    planet: ['Environmental modelling','Lower estimates in this sample.','A corrected UK dry-food model reports lower plant-based category means for emissions, land and freshwater.','Model assumptions, formulation and comparator matter. Environmental estimates do not establish health benefits.','environment','Explore the three measures ↓']
  };
  const panel = document.querySelector('.evidence-response');
  const controls = [...document.querySelectorAll('[data-question]')];
  controls.forEach(button => button.addEventListener('click', () => {
    const row = responses[button.dataset.question];
    controls.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    ['.response-type','.response-title','.response-body','.response-limit'].forEach((s,i) => panel.querySelector(s).textContent = row[i]);
    const link = panel.querySelector('.response-link'); link.href = '#' + row[4]; link.textContent = row[5];
    panel.classList.remove('route-animate');
    requestAnimationFrame(() => requestAnimationFrame(() => panel.classList.add('route-animate')));
  }));
  const motion = document.querySelector('.motion-toggle');
  const preference = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  motion.hidden = false;
  if(preference && preference.matches){document.documentElement.classList.add('reduce-motion');motion.setAttribute('aria-pressed','true');}
  motion.addEventListener('click', () => {const reduce = document.documentElement.classList.toggle('reduce-motion');motion.setAttribute('aria-pressed',String(reduce));});
  function openTarget(){if(!location.hash)return;const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(target && target.tagName==='DETAILS')target.open=true;}
  document.addEventListener('click', e=>{const a=e.target.closest('a[href^="#"]');if(!a)return;const t=document.getElementById(a.getAttribute('href').slice(1));if(t && t.tagName==='DETAILS')t.open=true;});
  addEventListener('hashchange',openTarget);openTarget();
  let printOpen=[];addEventListener('beforeprint',()=>{printOpen=[...document.querySelectorAll('details')].filter(d=>!d.open);printOpen.forEach(d=>d.open=true)});addEventListener('afterprint',()=>printOpen.forEach(d=>d.open=false));
})();
