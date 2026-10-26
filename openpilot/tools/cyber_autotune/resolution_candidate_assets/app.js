'use strict';
let report;
const el=id=>document.getElementById(id);
const colors={BASELINE:'#205ea6',CURRENT:'#205ea6',V1:'#14845c',V2:'#c33540'};
const num=v=>v===null||v===undefined?'unavailable':(v!==0&&Math.abs(v)<.001?v.toExponential(3):v.toFixed(4));
function table(target,heads,rows){target.replaceChildren();const t=document.createElement('table'),tr=document.createElement('tr');for(const h of heads){const th=document.createElement('th');th.textContent=h;tr.append(th);}t.append(tr);for(const row of rows){const r=document.createElement('tr');for(const v of row){const c=document.createElement('td');c.textContent=v;r.append(c);}t.append(r);}target.append(t);}
function draw(id,lines,band){const svg=el(id);svg.replaceChildren();const ns='http://www.w3.org/2000/svg';const put=(tag,attrs,text)=>{const p=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))p.setAttribute(k,v);if(text)p.textContent=text;svg.append(p);return p;};
const ys=lines.flatMap(l=>l.points.map(p=>p[1]));if(band)for(const e of report.envelopes)ys.push(e.maximum_p95_m,-e.maximum_p95_m);
let limit=Math.max(.001,...ys.map(Math.abs))*1.15;const x=d=>65+(d-5)*30,y=v=>155-v/limit*125;
for(const d of[5,10,15,20,25,30]){put('line',{x1:x(d),x2:x(d),y1:25,y2:280,stroke:'#e0e5ed'});put('text',{x:x(d)-10,y:305,'font-size':13},d+'m');}
for(const v of[-limit,0,limit])put('text',{x:3,y:y(v),'font-size':12},(100*v).toFixed(2)+'cm');
put('line',{x1:65,x2:815,y1:y(0),y2:y(0),stroke:'#8390a4'});
if(band)for(const[key,fill]of[['maximum_p95_m','#d7dce6'],['minimum_p95_m','#aeb9cb']]){const env=report.envelopes;const pts=env.map(e=>x(e.distance_m)+','+y(e[key])).concat([...env].reverse().map(e=>x(e.distance_m)+','+y(-e[key])));put('polygon',{points:pts.join(' '),fill,opacity:.65});}
for(const l of lines){put('polyline',{points:l.points.map(p=>x(p[0])+','+y(p[1])).join(' '),fill:'none',stroke:colors[l.name],'stroke-width':2});for(const p of l.points)put('circle',{cx:x(p[0]),cy:y(p[1]),r:3,fill:colors[l.name]});}}
function render(){const rs=report.rows.filter(r=>r.scenario===el('scenario').value);const env=new Map(report.envelopes.map(e=>[e.distance_m,e]));el('rows').replaceChildren();for(const r of rs){const tr=document.createElement('tr'),e=env.get(r.distance_m);for(const v of[r.distance_m,r.candidate,num(r.candidate_minus_baseline_m===undefined?null:r.candidate_minus_baseline_m*100),num(e.minimum_p95_m*100)+'–'+num(e.maximum_p95_m*100),num(r.effect_to_max_envelope_ratio),r.classification,r.phase||'unavailable']){const td=document.createElement('td');td.textContent=v;tr.append(td);}el('rows').append(tr);}
const available=rs.filter(r=>r.absolute_effect_m!==undefined);
const line=(name,key)=>({name,points:available.filter(r=>r.candidate===name).map(r=>[r.distance_m,r[key]])});
const base={name:'BASELINE',points:available.filter(r=>r.candidate==='CURRENT').map(r=>[r.distance_m,r.baseline_lateral_m])};
draw('trajectory',[base,...['CURRENT','V1','V2'].map(n=>line(n,'candidate_lateral_m'))],false);
draw('effect',['CURRENT','V1','V2'].map(n=>line(n,'candidate_minus_baseline_m')),true);
const phase=report.phase_context.find(r=>r.scenario===el('scenario').value);
el('historical').textContent=phase?'Original phase metric summary SHA: '+phase.historical_summary_sha256:'Historical phase context unavailable';}
(async()=>{report=await fetch('/api/candidate-resolution').then(r=>{if(!r.ok)throw Error('Receipt load failed');return r.json();});
el('status').textContent=report.status;
el('coverage').textContent='Reference both matched: '+report.coverage.both_matched+'/'+report.coverage.both_visible+' · center unavailable: '+report.coverage.center_unavailable+' · '+report.recovered_case_count+'/'+report.historical_case_count+' exact historical cases recovered';
el('verdicts').textContent=Object.entries(report.ledger).map(([n,v])=>n+': '+v.status).join(' · ')+' · V2 nominal violations: '+report.existing_v2_violations;
for(const name of [...new Set(report.rows.map(r=>r.scenario))].sort()){const o=document.createElement('option');o.value=name;o.textContent=name;el('scenario').append(o);}
table(el('summary'),['candidate','distance m','available/cases','max |effect| cm','max ratio'],report.nominal_summary.distance_summary.map(r=>[r.candidate,r.distance_m,r.available+'/'+r.cases,num(r.absolute_effect_m.maximum===null?null:100*r.absolute_effect_m.maximum),num(r.effect_to_max_envelope_ratio.maximum)]));
el('directions').textContent=Object.entries(report.nominal_summary.direction_consistency).map(([n,v])=>n+': '+v.status).join(' · ');
el('open').textContent=report.open_terms.join(' · ')+' · total physical bound: null · actual mapping: pending · independent calibration: pending';
el('receipts').textContent='Meter receipt: '+report.meter_sha256+' · audit: '+report.receipt_sha256;
el('scenario').addEventListener('change',render);render();
})().catch(e=>{el('status').textContent=e.message;throw e;});
