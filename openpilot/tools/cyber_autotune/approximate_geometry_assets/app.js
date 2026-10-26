'use strict';
const $=id=>document.getElementById(id);let state;
async function request(path,body){const opt=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Diagnostic-Token':state.token},body:JSON.stringify(body)};
const r=await fetch(path,opt),x=await r.json();if(!r.ok)throw Error(x.error);return x;}
function error(e){$('status').textContent='BLOCKED: '+e.message;}
function values(id){const raw=$(id).value.trim();if(!raw)throw Error('Explicit '+id+' required — no height/default imputation');
const result=raw.split(',').map(x=>{if(!x.trim())throw Error('Empty parameter');const n=Number(x);if(!Number.isFinite(n))throw Error('Non-finite parameter');return n;});return result;}
function table(rows){const t=document.createElement('table'),h=document.createElement('tr');
const cols=['height_parameter_m','rpy_deg','mount_y_parameter_m','forward_distance_m','normalized_optical_uv','lateral_sensitivity_m_per_normalized_u','height_sensitivity_at_fixed_ray_m_per_m'];
for(const key of cols){const th=document.createElement('th');th.textContent=key;h.append(th);}t.append(h);
for(const row of rows){const tr=document.createElement('tr');for(const k of cols){const td=document.createElement('td');td.textContent=JSON.stringify(row[k]);tr.append(td);}t.append(tr);}
$('table').replaceChildren(t);}
function coarseTable(target,rows,columns){const t=document.createElement('table'),head=document.createElement('tr');
for(const col of columns){const cell=document.createElement('th');cell.textContent=col;head.append(cell);}t.append(head);
for(const row of rows){const tr=document.createElement('tr');for(const col of columns){const td=document.createElement('td');td.textContent=JSON.stringify(row[col]);tr.append(td);}t.append(tr);}$(target).replaceChildren(t);}
function coarse(){const x=state.coarse;
$('coarse-summary').textContent='Vehicle: 2021 Santa Fe TM USER DECLARATION / official variant context; actual trim unverified. Camera height: 1.40 m COARSE PRIOR; sweep 1.33–1.47 m. Mount lateral: 0 m USER DECLARATION. Roll 0°, pitch 2.34°, yaw 0.2° MODEL-DERIVED PRIOR. NO PHYSICAL HEIGHT MEASUREMENT.';
for(const [id,grid,nominal] of [['coarse-height',x.policy.heights_m,1.4],['coarse-pitch',x.policy.pitches_deg,2.34]]){
for(const value of grid){const option=document.createElement('option');option.value=value;option.textContent=value;$(id).append(option);}$(id).value=nominal;}
const cols=['height_m','pitch_deg','nominal_forward_distance_m','forward_m','center_lateral_left_m','lateral_probe_left_m','lateral_sensitivity_m_per_normalized_u','reported_pitch_forward_sensitivity_m_per_rad'];
coarseTable('coarse-nominal',x.result.nominal_result.rows,cols);
const change=()=>{const height=Number($('coarse-height').value),pitch=Number($('coarse-pitch').value);
const selected=x.result.sensitivity_envelope.matrix.filter(r=>r.height_m===height&&r.pitch_deg===pitch);
coarseTable('coarse-selected',selected,cols);
$('coarse-ray').setAttribute('d','M270 '+(210-height*100)+'L'+(270+Math.min(200,selected[0].forward_m*20))+' 210');};
$('coarse-height').onchange=change;$('coarse-pitch').onchange=change;change();
coarseTable('coarse-envelope',x.result.sensitivity_envelope.distance_envelopes,['nominal_forward_distance_m','forward_m','lateral_probe_left_m','lateral_sensitivity_m_per_normalized_u','scope']);
coarseTable('coarse-rotation',x.result.sensitivity_envelope.orientation_1d,['axis','axis_value_deg','nominal_forward_distance_m','center_lateral_left_m','forward_m']);
$('coarse-comparison').textContent=JSON.stringify(x.comparison,null,2);
$('coarse-readiness').textContent=JSON.stringify(x.readiness,null,2);
}
async function start(){state=await request('/api/state');
$('summary').textContent='ORIGINAL HISTORICAL PRIOR — Mount: rear-view mirror lower area / centered by USER DECLARATION. Roll ~0°, pitch ~2.34°, yaw ~0.2° MODEL-DERIVED PRIOR. Camera height NOT PHYSICALLY MEASURED. Vehicle spec identity PENDING.';
$('orientation').textContent=JSON.stringify({reported:state.prior.orientation,effective_physical_euler_rad:state.effective_physical_euler_rad},null,2);
$('comparison').textContent=JSON.stringify(state.comparison,null,2);$('readiness').textContent=JSON.stringify(state.readiness,null,2);
$('symbolic').onclick=async()=>{try{const uv=[Number($('ray-u').value),Number($('ray-v').value)];
if(!$('ray-u').value||!$('ray-v').value||!uv.every(Number.isFinite))throw Error('Explicit finite normalized ray required');
$('symbolic-result').textContent=JSON.stringify(await request('/api/ray',{normalized_uv:uv,height_m:null}),null,2);$('status').textContent='SYMBOLIC ONLY — height UNKNOWN';}catch(e){error(e);}};
$('evaluate').onclick=async()=>{try{const heights=values('heights'),mounts=values('mounts'),pitches=values('pitches'),rolls=values('rolls'),yaws=values('yaws');
if(heights.length*mounts.length*pitches.length*rolls.length*yaws.length*4>256)throw Error('Bounded matrix: max256 rows');
const rpy=[];for(const r of rolls)for(const p of pitches)for(const y of yaws)rpy.push([r,p,y]);
if(heights.length*rpy.length*mounts.length*4>256)throw Error('Bounded matrix: max256 rows');
const x=await request('/api/sensitivity',{heights_m:heights,rpy_deg_choices:rpy,mount_y_m:mounts,rationale:$('rationale').value});
table(x.report.rows);$('policy').textContent=JSON.stringify({policy:x.policy,report_identity:x.report.receipt_sha256,qualification_allowed:x.report.qualification_allowed},null,2);
$('status').textContent=x.report.rows.length+' parameter rows — actual height UNKNOWN; NON-QUALIFYING';
const first=x.report.rows[0];$('ray-path').setAttribute('d','M300 90L'+(300+Math.min(200,first.forward_distance_m*5))+' 200');}catch(e){error(e);}};
coarse();window.geometryReady=true;}
start().catch(error);
