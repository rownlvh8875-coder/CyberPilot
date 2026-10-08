'use strict';
const $=id=>document.getElementById(id);let cfg,state,draft,index=0,staticReceipt=null;
const fields=new Map();
async function request(path,body,binary=false){const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':binary?'application/octet-stream':'application/json','X-Wizard-Token':cfg.token},body:binary?body:JSON.stringify(body)};
 const r=await fetch(path,options),x=await r.json();if(!r.ok)throw Error(x.error);return x;}
function showError(e){$('status').textContent='BLOCKED: '+e.message;}
function field(parent,path,label,type='text',choices=[]){const l=document.createElement('label');l.textContent=label;
 const el=document.createElement(type==='select'?'select':type==='textarea'?'textarea':'input');el.id=path.join('-');el.dataset.path=path.join('.');
 if(type==='select'){for(const choice of ['',...choices]){const o=document.createElement('option');o.value=choice;o.textContent=choice||'UNKNOWN / PENDING';el.append(o);}}
 else if(type!=='textarea'){el.type=type;if(type==='number')el.step='any';}l.append(el);$(parent).append(l);fields.set(path.join('.'),{el,type,path});return el;}
function collect(){const d=structuredClone(draft);for(const {el,type,path} of fields.values()){let t=d;for(const k of path.slice(0,-1))t=t[k];
 t[path.at(-1)]=type==='checkbox'?el.checked:el.value===''?null:type==='number'?Number(el.value):el.value;}
 d.general.note=d.general.note||'';for(const o of Object.values(d.observations))o.note=o.note||'';d.general.independence_confirmed=$('ack').checked;return d;}
function fill(d){draft=structuredClone(d);for(const {el,type,path} of fields.values()){let v=d;for(const k of path)v=v[k];if(type==='checkbox')el.checked=v===true;else el.value=v??'';}
 $('ack').checked=d.general.independence_confirmed===true;conversion();}
function conversion(){const d=collect();$('angle-conversion').textContent=JSON.stringify(Object.fromEntries(['pitch_rad','roll_rad','yaw_rad'].map(k=>{
 const o=d.observations[k],factor=o.unit==='deg'?Math.PI/180:o.unit==='rad'?1:null;return [k,{original:o.value,unit:o.unit,radians:factor===null||o.value===null?null:o.value*factor,
 uncertainty_radians:factor===null||o.uncertainty===null?null:o.uncertainty*factor}];})),null,2);}
function navigate(i){index=Math.max(0,Math.min(7,i));document.querySelectorAll('.stage').forEach((el,j)=>el.classList.toggle('active',j===index));
 $('stages').querySelectorAll('button').forEach((el,j)=>el.classList.toggle('active',j===index));}
function build(){cfg.stages.forEach((label,i)=>{const b=document.createElement('button');b.textContent=label;b.onclick=()=>navigate(i);$('stages').append(b);});
 for(const [k,choices] of Object.entries({device:['mici'],hardware_generation:['comma4'],sensor:['ar0231','ox03c10','os04c10'],view:['narrow_road']}))field('device',['camera',k],k,'select',choices);
 field('device',['camera','unit_id'],'확인한 device opaque ID');
 field('device',['camera','hardware_evidence_id'],'hardware evidence','select');
 field('mount',['mount','datum_description'],'surveyed datum/origin 설명','textarea');
 field('mount',['mount','evidence_id'],'datum evidence','select');field('mount',['mount','convention_confirmed'],'X forward / Y left / Z up 확인','checkbox');
 for(const k of ['version_id','operator_id','timestamp'])field('general',['general',k],k);
 const now=document.createElement('button');now.textContent='관측 timestamp에 현재 UTC 명시 입력';now.onclick=()=>{$('general-timestamp').value=new Date().toISOString().replace(/\.\d{3}Z$/,'Z');};$('general').append(now);
 field('general',['general','method'],'실제 survey method','select',cfg.methods);field('general',['general','note'],'측정 note (local/private)','textarea');
 for(const k of cfg.target_keys)field('target',['target',k],k,k.endsWith('_m')?'number':k.endsWith('_id')?'select':'textarea');
 field('ground',['ground','surface_method'],'ground survey method');field('ground',['ground','slope_bound_deg'],'observed slope bound deg','number');
 field('ground',['ground','evidence_id'],'ground survey evidence','select');field('distortion',['distortion','state'],'distortion state','select',['INDEPENDENTLY_BOUNDED_UNDISTORTED_RESIDUAL']);
 field('distortion',['distortion','evidence_id'],'independent distortion residual evidence','select');
 for(const key of cfg.observation_keys){const parent=key==='ground_vertical_m'?'ground-obs':key==='distortion_residual_px'?'distortion-obs':key.endsWith('_m')?'position-obs':key.endsWith('_rad')?'angle-obs':'intrinsic-obs';
 const f=document.createElement('fieldset');f.id='row-'+key;const title=document.createElement('legend');title.textContent=key;f.append(title);$(parent).append(f);
 const options={unit:key.endsWith('_rad')?['deg','rad']:[key.endsWith('_m')?'m':'px'],uncertainty_unit:key.endsWith('_rad')?['deg','rad']:[key.endsWith('_m')?'m':'px'],
 instrument_type:[...cfg.instruments,'PHONE_IMU','INFORMAL'],method:[...cfg.methods,'PINNED_HARDWARE_NOMINAL'],source_kind:['PHYSICAL_OBSERVATION','STATIC_SOURCE',...cfg.forbidden],tier:['TIER_A','TIER_B','TIER_C'],instrument_unit:['m','mm','rad','deg','px'],uncertainty_method:['METROLOGY_REVIEW']};
 for(const k of cfg.observation_fields){const type=['value','uncertainty','instrument_resolution'].includes(k)?'number':options[k]||k.endsWith('_id')?'select':k==='note'?'textarea':'text';
 field(f.id,['observations',key,k],k,type,options[k]||[]);}}
 fields.get('observations.pitch_rad.value').el.addEventListener('input',conversion);
 document.querySelectorAll('#angle-obs input,#angle-obs select').forEach(el=>el.addEventListener('change',conversion));
}
function evidenceOptions(){for(const {el,path} of fields.values()){if(!path.at(-1).endsWith('_evidence_id')&&!['evidence_id','hardware_evidence_id'].includes(path.at(-1)))continue;
 const old=el.value;el.replaceChildren();for(const value of ['',...state.attachments.map(a=>a.opaque_id)]){const o=document.createElement('option');o.value=value;o.textContent=value?value.slice(0,16)+'…':'UNKNOWN / PENDING';el.append(o);}el.value=old;}
 $('attachments').textContent=JSON.stringify(state.attachments,null,2);}
function update(s){state=s;evidenceOptions();fill(s.draft);const locked=s.status!=='DRAFT_MEASUREMENT';
 for(const {el} of fields.values())el.disabled=locked;$('ack').disabled=locked;
 for(const id of ['save-draft','admit','upload','use-static'])$(id).disabled=locked;
 $('recover').disabled=s.status!=='ADMISSION_INTERRUPTED_PENDING_RECOVERY';
 $('readiness').textContent=s.scope+' / '+s.status+' / '+s.readiness+' / INDEPENDENT_REFERENCE_UNAVAILABLE';
 $('status').textContent='Loaded — '+s.status;}
async function start(){cfg=await request('/api/config');draft=cfg.state.draft;build();update(cfg.state);navigate(0);
 $('source').textContent=JSON.stringify(cfg.static_sources,null,2);
 $('prev').onclick=()=>navigate(index-1);$('next').onclick=()=>navigate(index+1);
 $('save-draft').onclick=async()=>{try{update(await request('/api/draft',collect()));$('status').textContent='Editable draft saved locally';}catch(e){showError(e);}};
 $('reload').onclick=async()=>{try{update(await request('/api/state'));}catch(e){showError(e);}};
 $('upload').onclick=async()=>{try{const d=collect();for(const f of $('attachment').files)await request('/api/attachment',await f.arrayBuffer(),true);
 state=await request('/api/state');evidenceOptions();fill(d);$('status').textContent='Evidence local/private; filenames not sent';}catch(e){showError(e);}};
 $('static-preview').onclick=async()=>{try{staticReceipt=await request('/api/intrinsics',collect().camera);$('intrinsics').textContent=JSON.stringify(staticReceipt,null,2);}catch(e){showError(e);}};
 $('use-static').onclick=()=>{if(!staticReceipt)return showError(Error('먼저 실제 device/source를 확인하세요'));const d=collect(),m=staticReceipt.matrix;
 for(const [k,v] of Object.entries({fx_px:m[0][0],fy_px:m[1][1],cx_px:m[0][2],cy_px:m[1][2]}))Object.assign(d.observations[k],{value:v,unit:'px',uncertainty_unit:'px',method:'PINNED_HARDWARE_NOMINAL',source_kind:'STATIC_SOURCE'});fill(d);};
 $('preflight').onclick=async()=>{try{const d=collect(),x=await request('/api/preflight',d);
 $('preview').textContent=JSON.stringify({explicit_original_input:d,attachments:state.attachments,result:x},null,2);
 $('status').textContent=x.valid?'STRUCTURAL PREFLIGHT PASS — independent validation PENDING':'PREFLIGHT BLOCKED: '+x.errors.join(', ');}catch(e){showError(e);}};
 $('admit').onclick=async()=>{try{if(!$('ack').checked)throw Error('물리 관측/non-model 확인이 필요합니다');
 await request('/api/draft',collect());const p=await request('/api/admit',{});$('preview').textContent=JSON.stringify(p,null,2);update(await request('/api/state'));}catch(e){showError(e);}};
 $('recover').onclick=async()=>{try{await request('/api/recover',{});update(await request('/api/state'));}catch(e){showError(e);}};
 window.wizardReady=true;}
start().catch(showError);
