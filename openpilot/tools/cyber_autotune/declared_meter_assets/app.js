'use strict';
let report;
const el = id => document.getElementById(id);
const cm = x => x === null || x === undefined ? 'unavailable' : (100*x).toFixed(3);
function row(parent, values) {
  const tr = document.createElement('tr');
  for (const value of values) {
    const td = document.createElement('td'); td.textContent = value; tr.appendChild(td);
  }
  parent.appendChild(tr);
}
function draw() {
  const group = el('group').value, view = el('view').value;
  const rows = report[view].filter(r => r.group === group);
  const nominal = report.scenarios.find(s => s.height_m === 1.385);
  const flat = view === 'fixed_distance' ? rows.map(r => ({...r,distance_m:r.distance_query_m})) :
    rows.flatMap(r => r.bins.map(b => ({...b,mapping:r.mapping,scenario_id:r.scenario_id,unavailable:b.unavailable_count,out:r.out_of_domain})));
  el('nominal').replaceChildren(); el('envelope').replaceChildren();
  for (const d of [5,10,15,20,25,30]) {
    for (const r of flat.filter(x => x.distance_m === d && x.scenario_id === nominal.scenario_id)) {
      row(el('nominal'),[d,r.mapping,cm(r.lateral_m.median),cm(r.lateral_m.p95),
        (view==='fixed_distance' ? r.lateral_m.count : r.lateral_m.count+'/'+r.candidate_count)+(r.small_sample ? ' (small sample)' : ''),
        view === 'fixed_distance' ? r.unavailable_samples : r.unavailable+' total / '+r.out+' outside domain']);
    }
    const candidates = flat.filter(r => r.distance_m === d && r.lateral_m.p95 !== null);
    candidates.sort((a,b) => a.lateral_m.p95-b.lateral_m.p95);
    if (candidates.length) {
      const low=candidates[0], high=candidates[candidates.length-1];
      row(el('envelope'),[d,cm(low.lateral_m.p95),cm(high.lateral_m.p95),
        low.scenario_id+' '+low.mapping+' / '+high.scenario_id+' '+high.mapping]);
    } else row(el('envelope'),[d,'unavailable','unavailable','no observed support']);
  }
  const c=report.coverage;
  el('coverage').textContent='Frame coverage: '+c.both_matched+'/'+c.both_visible+' both boundaries matched; '+
    c.center_unavailable+' unavailable centers; '+c.total_frames+' total frames. AI-assisted human reference, not blind GT.';
  el('semantics').textContent=view === 'fixed_distance' ?
    'Synthetic nominal ground queries held fixed across scenarios. All frozen matched pixel residuals applied at each query. These are not observed point distances.' :
    'Human and detector rays independently intersected. Human projected distance selects bin; 5–30m domain only. No extrapolation or unavailable-value filling.';
}
fetch('/api/meter').then(r=>{if(!r.ok)throw new Error('local report unavailable');return r.json();}).then(r=>{
  report=r;
  for(const term of report.open_terms) {const li=document.createElement('li');li.textContent=term;el('open').appendChild(li);}
  el('status').textContent=r.status+' · TOTAL_PHYSICAL_BOUND_UNAVAILABLE · INDEPENDENT_METER_VALIDATION_NOT_RUN';
  el('group').onchange=draw;el('view').onchange=draw;draw();
}).catch(e=>{el('status').textContent=e.message;});
