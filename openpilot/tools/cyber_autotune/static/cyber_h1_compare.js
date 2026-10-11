'use strict';
const $ = id => document.getElementById(id);
const ns = 'http://www.w3.org/2000/svg';
let catalog, campaign, run, frames = [], current = 0, timer = null, loadSequence = 0;
const colors = ['#d7e2ef','#6bb6ff','#f0b866','#8ce0c0','#e58ecd','#b8a7fa','#82d5e0','#dfcd8e'];
const fmt = v => v === null || v === undefined ? 'unavailable' : typeof v === 'number' ? Number(v.toPrecision(7)).toString() : String(v);
const show = (id, value) => { $(id).textContent = value; };
function node(tag, attributes) { const n = document.createElementNS(ns,tag); for(const [k,v] of Object.entries(attributes)) n.setAttribute(k,String(v)); return n; }
async function get(url) { const response = await fetch(url,{credentials:'same-origin',cache:'no-store'}); if(!response.ok) throw Error('Local resource '+response.status); return response.json(); }
function stop() { if(timer) clearInterval(timer); timer=null; show('play','Play'); }
function lineChart(id, series) {
  const svg=$(id); svg.replaceChildren(); const width=900,height=240,pad=42;
  const values=series.flatMap(s=>s.values.filter(v=>v!==null)); let lo=Math.min(...values),hi=Math.max(...values);
  if(lo===hi){lo-=.01;hi+=.01;}
  const duration=frames.at(-1).completion_time_ns;
  const x=time=>pad+time/duration*(width-2*pad), y=v=>height-pad-(v-lo)/(hi-lo)*(height-2*pad);
  const time=(i,phase)=>frames[i][phase==='COMPLETION'?'completion_time_ns':phase==='DECISION'?'decision_time_ns':'capture_time_ns'];
  for(let j=0;j<3;j++){const yy=pad+j*(height-2*pad)/2;svg.append(node('line',{x1:pad,x2:width-pad,y1:yy,y2:yy,class:'gridline'}));
    const text=node('text',{x:4,y:yy+4});text.textContent=fmt(hi-j*(hi-lo)/2);svg.append(text);}
  series.forEach((s,j)=>{const d=s.values.map((v,i)=>v===null?'':(i===0?'M':'L')+x(time(i,s.phase))+','+y(v)).join(' ');
    const path=node('path',{d,fill:'none',stroke:colors[j%colors.length],'stroke-width':1.4,'data-series':s.name});const title=node('title',{});title.textContent=s.name;path.append(title);svg.append(path);});
  ['CAPTURE','DECISION','COMPLETION'].forEach(phase=>svg.append(node('line',{
    x1:x(time(current,phase)),x2:x(time(current,phase)),y1:pad,y2:height-pad,stroke:'#ffffff',
    'stroke-width':1,'data-marker':'current','data-phase':phase})));
  const label=node('text',{x:pad,y:height-10});label.textContent='Capture k / completion k+1 · relative seconds 0 → '+fmt(frames.at(-1).completion_time_ns/1e9);svg.append(label);
  const legend=$(id+'Legend');if(legend){legend.replaceChildren();series.forEach((s,j)=>{const span=document.createElement('span');span.textContent=s.name;span.style.borderColor=colors[j%colors.length];legend.append(span);});}
}
function drawPose() {
  const svg=$('pose');svg.replaceChildren();const all=frames.flatMap(f=>[f.baseline,f.candidate]);
  const xs=all.map(a=>a.pose_x_post_step_m),ys=all.map(a=>a.pose_y_post_step_m);
  let xl=Math.min(...xs),xh=Math.max(...xs),yl=Math.min(...ys),yh=Math.max(...ys);
  if(xl===xh)xh=xl+1;if(yl===yh)yh=yl+1;
  const scale=Math.min(800/(xh-xl),220/(yh-yl)),x=v=>50+(v-xl)*scale,y=v=>260-(v-yl)*scale;
  ['baseline','candidate'].forEach((arm,j)=>{
    const d=frames.map((f,i)=>(i?'L':'M')+x(f[arm].pose_x_post_step_m)+','+y(f[arm].pose_y_post_step_m)).join(' ');
    svg.append(node('path',{d,fill:'none',stroke:colors[j+1],'stroke-width':2,'data-arm':arm}));
    const f=frames[current][arm],xx=x(f.pose_x_post_step_m),yy=y(f.pose_y_post_step_m);
    svg.append(node('circle',{cx:xx,cy:yy,r:5,fill:colors[j+1],'data-marker':arm}));
    svg.append(node('line',{x1:xx,y1:yy,x2:xx+20*Math.cos(f.heading_post_step_rad),y2:yy-20*Math.sin(f.heading_post_step_rad),stroke:colors[j+1],'stroke-width':3}));
  });
  const label=node('text',{x:25,y:290});label.textContent='x [m] '+fmt(xl)+'…'+fmt(xh)+' / y [m] '+fmt(yl)+'…'+fmt(yh)+' · same scale · completion phase';svg.append(label);
}
function render(index) {
  if(!frames.length)return;current=Math.max(0,Math.min(frames.length-1,Math.trunc(index)));
  const f=frames[current];$('index').value=current;$('scrubber').value=current;
  show('clock','Frame '+current+' / '+(frames.length-1)+' · capture PRE-STEP '+f.capture_time_ns+' ns · COMMAND '+f.decision_time_ns+' ns · POST-STEP '+f.completion_time_ns+' ns · dt '+f.dt_s+' s');
  lineChart('curvature',[
    {name:'Shared desired intent',phase:'CAPTURE',values:frames.map(x=>x.shared.desired_curvature_1pm)},
    ...['baseline','candidate'].flatMap(a=>[
      {name:a+' PRE-STEP',phase:'CAPTURE',values:frames.map(x=>x[a].actual_curvature_pre_step_1pm)},
      {name:a+' POST-STEP',phase:'COMPLETION',values:frames.map(x=>x[a].curvature_post_step_1pm)}]),
    {name:'Δ POST-STEP',phase:'COMPLETION',values:frames.map(x=>x.delta.curvature_post_step_1pm)}]);
  lineChart('torque',['baseline','candidate'].flatMap(a=>[
    {name:a+' controller-limited / pre-governor',phase:'DECISION',values:frames.map(x=>x[a].pre_governor_torque)},
    {name:a+' post-governor / final requested',phase:'DECISION',values:frames.map(x=>x[a].post_governor_torque)},
    {name:a+' applied POST-STEP descriptive',phase:'COMPLETION',values:frames.map(x=>x[a].applied_torque)}]));
  drawPose();
  show('curvatureValues','Current PRE Δ '+fmt(f.delta.actual_curvature_pre_step_1pm)+' · POST Δ '+fmt(f.delta.curvature_post_step_1pm));
  show('torqueValues','Current pre-governor Δ '+fmt(f.delta.pre_governor_torque)+' · post-governor Δ '+fmt(f.delta.post_governor_torque)+' · applied Δ '+fmt(f.delta.applied_torque)+' · pre-limit intent unavailable');
  show('poseValues','POST-STEP Δx '+fmt(f.delta.pose_x_post_step_m)+' m · Δy '+fmt(f.delta.pose_y_post_step_m)+' m · Δheading '+fmt(f.delta.heading_post_step_rad)+' rad');
  show('state',JSON.stringify({active:f.shared.active,steeringPressed:f.shared.steering_pressed,
    event:f.shared.event,reset_events:f.shared.reset_events,safety_limited:f.shared.safety_limited,
    curvature_limited:f.shared.curvature_limited,baseline_rail:f.baseline.normalized_rail_state,candidate_rail:f.candidate.normalized_rail_state},null,2));
  $('unavailable').replaceChildren();
  for(const arm of ['baseline','candidate'])for(const [field,reason] of Object.entries(f[arm].unavailable)){
    const div=document.createElement('div');div.className='null';div.textContent=arm+' · '+field+' = unavailable · '+reason+' · '+f[arm].provenance[field];$('unavailable').append(div);}
  show('health',JSON.stringify({baseline:f.baseline.service_health,candidate:f.candidate.service_health},null,2));
  $('deltas').replaceChildren();
  for(const [key,stats] of Object.entries(run.frameset.delta_statistics)){
    const row=document.createElement('tr');for(const value of [key,f.delta[key],stats.max_absolute,stats.p50_absolute,stats.p95_absolute,stats.final,stats.count+'/'+frames.length]){
      const td=document.createElement('td');td.textContent=fmt(value);row.append(td);} $('deltas').append(row);}
  show('verdict','Historical verdict: '+campaign.historical_verdict+' · '+(campaign.kind==='TA_B'?'saturation/derivative tradeoff':'smoothness/tracking tradeoff · COMPOSITION_NOT_RECOMMENDED'));
  show('identity',JSON.stringify({campaign_sha256:campaign.campaign_receipt_sha256,scenario_sha256:run.pair.scenario_sha256,
    baseline_arm:run.pair.baseline_arm,candidate_arm:run.pair.candidate_arm,
    baseline_trace_sha256:run.pair.baseline_trace_sha256,candidate_trace_sha256:run.pair.candidate_trace_sha256,
    shared_stimulus_sha256:f.shared_stimulus_sha256,pair_sha256:f.pair_sha256,pairing_sha256:run.pair.pairing_sha256,
    frameset_sha256:run.frameset.receipt_sha256,baseline_row_sha256:f.baseline_row_sha256,candidate_row_sha256:f.candidate_row_sha256,
    evidence_tier:f.evidence_tier,holdout:'CLOSED',opening_count:0},null,2));
  $('blockers').replaceChildren();campaign.blockers.forEach(b=>{const span=document.createElement('span');span.className='badge';span.textContent=b;$('blockers').append(span);});
}
function clearRun(){
  stop();frames=[];run=null;current=0;
  for(const id of ['play','prev','next','prevEvent','nextEvent','speed','index','scrubber'])$(id).disabled=true;
  for(const id of ['curvature','torque','pose','deltas','unavailable','blockers'])$(id).replaceChildren();
  for(const id of ['clock','curvatureValues','torqueValues','poseValues','state','health','identity','verdict'])show(id,'Unavailable while loading');
}
async function loadScenario(){
  const seq=++loadSequence;clearRun();show('status','Loading paired immutable pages…');
  const selectedCampaign=campaign,scenario=$('scenario').value;
  const prefix='/api/campaigns/'+selectedCampaign.campaign_id+'/scenarios/'+scenario;
  const loaded=await get(prefix);if(seq!==loadSequence)return;const collected=[];
  for(let offset=0;offset<loaded.frameset.frame_count;offset+=100){
    const page=await get(prefix+'/frames?offset='+offset+'&limit=100');
    if(seq!==loadSequence)return;collected.push(...page.frames);
  }
  if(seq!==loadSequence)return;
  if(collected.length!==loaded.frameset.frame_count)throw Error('Incomplete paired frames');
  run=loaded;frames=collected;for(const id of ['index','scrubber'])$(id).max=frames.length-1;
  for(const id of ['play','prev','next','prevEvent','nextEvent','speed','index','scrubber'])$(id).disabled=false;
  show('status',frames.length+' synchronized frames · '+frames.length*frames[0].dt_s+' s · '+run.pair.baseline_arm+' / '+run.pair.candidate_arm);
  render(0);
}
async function selectCampaign(){
  const seq=++loadSequence;clearRun();$('scenario').disabled=true;
  const selected=catalog.campaigns.find(x=>x.campaign_id===$('campaign').value);campaign=selected;
  show('status','Loading campaign catalog…');
  const list=await get('/api/campaigns/'+selected.campaign_id+'/scenarios');
  if(seq!==loadSequence)return;
  $('scenario').replaceChildren();list.scenarios.forEach(s=>{const opt=document.createElement('option');opt.value=s.scenario;opt.textContent=s.scenario;$('scenario').append(opt);});
  $('scenario').disabled=false;await loadScenario();
}
function jump(direction){for(let i=current+direction;i>=0&&i<frames.length;i+=direction)if(frames[i].shared.event!=='ORDINARY'){stop();render(i);return;}}
function play(){if(!frames.length)return;if(timer){stop();return;}if(current===frames.length-1)render(0);show('play','Pause');
  let previous=performance.now(),fraction=0;
  timer=setInterval(()=>{const now=performance.now();fraction+=(now-previous)/1000*100*Number($('speed').value);previous=now;
    const advance=Math.floor(fraction);fraction-=advance;if(advance)render(current+advance);if(current===frames.length-1)stop();},40);}
function fail(error){clearRun();show('status','Inspection blocked: '+error.message);}
$('campaign').addEventListener('change',()=>selectCampaign().catch(fail));
$('scenario').addEventListener('change',()=>loadScenario().catch(fail));
$('play').addEventListener('click',play);
$('prev').addEventListener('click',()=>{stop();render(current-1);});
$('next').addEventListener('click',()=>{stop();render(current+1);});
$('scrubber').addEventListener('input',e=>{stop();render(Number(e.target.value));});
$('index').addEventListener('input',e=>{stop();render(Number(e.target.value));});
$('prevEvent').addEventListener('click',()=>jump(-1));$('nextEvent').addEventListener('click',()=>jump(1));
async function start(){catalog=await get('/api/campaigns');catalog.campaigns.forEach(c=>{const opt=document.createElement('option');opt.value=c.campaign_id;opt.textContent=c.title;$('campaign').append(opt);});await selectCampaign();}
start().catch(fail);
