'use strict';
let data;
const el=id=>document.getElementById(id),num=v=>v===null||v===undefined?'unavailable':(v!==0&&Math.abs(v)<.001?v.toExponential(3):v.toFixed(5));
function table(id,heads,rows){const target=el(id);target.replaceChildren();const t=document.createElement('table');for(const [index,row]of[heads,...rows].entries()){const tr=document.createElement('tr');for(const v of row){const td=document.createElement(index?'td':'th');td.textContent=v;tr.append(td);}t.append(tr);}target.append(t);}
function plot(rows,signal){const svg=el('trace'),ns='http://www.w3.org/2000/svg';svg.replaceChildren();const put=(tag,attrs,text)=>{const p=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))p.setAttribute(k,v);if(text!==undefined)p.textContent=text;svg.append(p);};
const limit=Math.max(Number.MIN_VALUE,...rows.map(r=>Math.abs(r[signal+'_delta']))),maxT=Math.max(...rows.map(r=>r.time_s));const x=t=>75+790*t/maxT,y=v=>140-110*v/(limit||1);
put('line',{x1:75,x2:865,y1:140,y2:140,stroke:'#a0afc0'});for(const t of[0,1,2,3,4])put('text',{x:x(t),y:280,'font-size':13},t+'s');
for(const v of[-limit,0,limit])put('text',{x:2,y:y(v),'font-size':12},num(v));
for(const[name,color]of[['CURRENT','#296bb0'],['V1','#13825d'],['V2','#c23e4a']]){const points=rows.filter(r=>r.candidate===name).map(r=>x(r.time_s)+','+y(r[signal+'_delta']));put('polyline',{points:points.join(' '),fill:'none',stroke:color,'stroke-width':2});}}
function render(){const scenario=el('scenario').value,rows=data.stage.rows.filter(r=>r.scenario===scenario);
plot(data.stage.visual_samples.filter(r=>r.scenario===scenario),el('signal').value);
table('stages',['candidate','signal / units','max |delta|','signed integral','L1 integral','sign changes','max derivative /s'],rows.flatMap(r=>Object.entries(r.signals).map(([k,v])=>[r.candidate,k+' / '+v.units,num(v.maximum_absolute),num(v.signed_integral),num(v.absolute_integral),v.sign_changes,num(v.maximum_derivative_per_s)])));
table('ratios',['candidate','from → to','L1 output/input','units','status'],rows.flatMap(r=>r.stage_ratios.map(v=>[r.candidate,v.from+' → '+v.to,num(v.l1_output_per_input.value),v.units,v.l1_output_per_input.status])));
table('cancellation',['candidate','delay-aligned residual','torque cancellation','pose-increment cancellation','final Δy m','peak |Δy| m'],rows.map(r=>[r.candidate,num(r.delay_aligned_applied_residual_max),num(r.signals.requested_torque.cancellation_ratio),num(r.signals.pose_velocity.cancellation_ratio),num(r.final_pose_y_delta_m),num(r.maximum_pose_y_delta_m)]));
table('phase',['candidate','phase','samples','torque L1','curvature L1','pose-y signed integral'],rows.flatMap(r=>r.phases.map(p=>[r.candidate,p.phase,p.count,num(p.signals.requested_torque.absolute_integral),num(p.signals.curvature.absolute_integral),num(p.signals.pose_y.signed_integral)])));
table('distance',['candidate','distance m','Δy cm','status','scope'],data.stage.distances.filter(r=>r.scenario===scenario).map(r=>[r.candidate,num(r.distance_m),num(r.pose_y_delta_m===null?null:100*r.pose_y_delta_m),r.status,r.scope]));
}
(async()=>{const r=await fetch('/api/plant-authority');if(!r.ok)throw Error('Immutable receipt load failed');data=await r.json();
el('status').textContent=data.audit.status+' · '+data.audit.verdict;
el('verdicts').textContent=Object.entries(data.audit.historical_verdicts).map(([k,v])=>k+': '+v).join(' · ')+' · V2 violations: 37 unchanged';
el('coverage').textContent='Reference: 44/55 both matched · 11 center unavailable · no new candidate or detector execution';
for(const[k,v]of Object.entries(data.findings.hypotheses)){const div=document.createElement('div');div.className='finding';const title=document.createElement('b');title.textContent=k+': '+v.status;const evidence=document.createElement('p');evidence.textContent=v.evidence;const counter=document.createElement('p');counter.className='muted';counter.textContent='Limit / counterevidence: '+v.counterevidence;div.append(title,evidence,counter);el('findings').append(div);}
for(const name of[...new Set(data.stage.rows.map(r=>r.scenario))].sort()){const o=document.createElement('option');o.value=name;o.textContent=name;el('scenario').append(o);}
for(const name of Object.keys(data.stage.rows[0].signals)){if(name==='pose_velocity')continue;const o=document.createElement('option');o.value=name;o.textContent=name+' ('+data.stage.rows[0].signals[name].units+')';el('signal').append(o);}
el('controls').textContent='Exact repeat: '+data.control.exact_repeatability+' · zero control: '+data.control.negative_control_exact_zero+' · recurrence oracle: '+data.control.analytic_recurrence_all_pass+' · original geometry oracle: '+data.control.analytic_geometry_all_pass;
table('control-table',['speed m/s','input','amplitude normalized','final Δy m','oracle residual','query availability'],data.control.rows.map(r=>[r.speed_mps,r.mode,num(r.amplitude),num(r.final_state.pose_y_m),num(r.maximum_oracle_residual),r.queries.filter(q=>q.status==='AVAILABLE').length+'/6 · '+[...new Set(r.queries.map(q=>q.status))].join(', ')]));
table('oracles',['speed m/s','geometric curvature 1/m','position residual m','Euler bound m','heading residual rad','pass'],data.control.original_geometry_oracles.map(r=>[r.speed_mps,r.geometric_curvature_1pm,num(r.position_error_m),num(r.riemann_bound_m),num(r.heading_error_rad),r.within_discrete_bound]));
table('gain',['speed m/s','DC curvature magnitude','Nyquist magnitude','Nyquist/DC','pole time s'],data.findings.frequency_response.map(r=>[r.speed_mps,num(r.dc_curvature_gain),num(r.nyquist_curvature_gain),num(r.nyquist_to_dc_ratio),num(r.pole_time_constant_s)]));
table('chain',['stage','units','semantics','source SHA'],data.findings.signal_chain.map(r=>[r.stage,r.units,r.semantics,r.source_sha256]));
el('blockers').textContent='INDEPENDENT_REFERENCE_UNAVAILABLE · CALIBRATION_UNCERTAINTY_PENDING · INDEPENDENT_CALIBRATION_VALIDATION_PENDING · PIXEL_GEOMETRY_REGISTRATION_PENDING · METRIC_CALIBRATION_UNAVAILABLE · sealed reference NOT_GENERATED · NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED';
el('receipts').textContent='Audit: '+data.audit.receipt_sha256+' · policy: '+data.policy.receipt_sha256+' · total physical bound: null';
el('scenario').addEventListener('change',render);el('signal').addEventListener('change',render);render();
})().catch(e=>{el('status').textContent=e.message;throw e;});
