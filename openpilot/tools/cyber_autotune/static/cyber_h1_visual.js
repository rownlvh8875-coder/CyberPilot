"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const diag = {javascriptErrors:0,networkErrors:0,externalRequests:0,pages:0,frames:0,renderCount:0};
  window.addEventListener("error", () => {diag.javascriptErrors++; diagnostics();});
  window.addEventListener("unhandledrejection", () => {diag.javascriptErrors++; diagnostics();});
  let frames=[],meta=null,index=0,playing=false,lastTick=null,elapsed=0,animationFrame=null;
  const NS="http://www.w3.org/2000/svg";
  const colors={desired:"#ffca79",pre:"#82adff",post:"#55d4bb"};
  const fmt = value => value===null ? "unavailable" : typeof value==="number" ? value.toPrecision(7) : String(value);
  const svg = (tag,attrs,text) => {const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;return el;};
  function diagnostics(){
    const resources=performance.getEntriesByType("resource");
    diag.externalRequests=resources.filter(r=>new URL(r.name,location.href).origin!==location.origin).length;
    $("diagnostics").textContent="JS errors "+diag.javascriptErrors+" · network errors "+diag.networkErrors+" · external requests "+diag.externalRequests;
  }
  async function get(path){
    if(!path.startsWith("/api/"))throw Error("Same-origin API only");
    try{const r=await fetch(path,{cache:"no-store",credentials:"omit"});if(!r.ok)throw Error("HTTP "+r.status);return await r.json();}
    catch(err){diag.networkErrors++;diagnostics();throw err;}
  }
  function dl(id,values){const box=$(id);box.replaceChildren();for(const [name,value] of Object.entries(values)){const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=name;dd.textContent=fmt(value);box.append(dt,dd);}}
  function plot(id,series){
    const box=$(id),W=900,H=235,L=65,R=20,T=18,B=38;
    box.replaceChildren();
    const all=series.flatMap(s=>frames.map(f=>f[s.field])).filter(v=>v!==null&&Number.isFinite(v));
    let low=Math.min(...all),high=Math.max(...all);if(high===low){low-=1;high+=1;}const pad=(high-low)*.1;low-=pad;high+=pad;
    const x=t=>L+t/8*(W-L-R),y=v=>H-B-(v-low)/(high-low)*(H-T-B);
    for(let n=0;n<=4;n++){let v=low+(high-low)*n/4;box.append(svg("line",{x1:L,y1:y(v),x2:W-R,y2:y(v),stroke:"#27384d"}),svg("text",{x:5,y:y(v)+4},v.toPrecision(3)));}
    for(let sec=0;sec<=8;sec+=2)box.append(svg("text",{x:x(sec),y:H-12},sec+" s"));
    for(const s of series){
      const points=frames.map(f=>[x(f[s.time]/1e9),y(f[s.field])]);
      const d=points.map((p,i)=>(i?"L":"M")+p[0]+","+p[1]).join(" ");
      const path=svg("path",{d,fill:"none",stroke:s.color,"stroke-width":1.6});
      path.append(svg("title",{},s.field+" · "+(s.time==="completion_time_ns"?"POST-STEP":s.time==="decision_time_ns"?"COMMAND":"PRE-STEP INPUT")+" · selected "+fmt(frames[index][s.field])));box.append(path);
    }
    const f=frames[index];
    for(const [time,color,label] of [[f.capture_time_ns,colors.pre,"PRE / COMMAND"],[f.completion_time_ns,colors.post,"POST"]]){
      box.append(svg("line",{x1:x(time/1e9),x2:x(time/1e9),y1:T,y2:H-B,stroke:color,"stroke-dasharray":"3 3"}));
      const title=svg("title",{},label+" · "+time+" relative ns");box.lastChild.append(title);
    }
    box.append(svg("text",{x:L,y:H-1},"Relative experiment time · POST shifted by +10 ms"));
  }
  function pose(){
    const box=$("pose"),W=450,H=300,P=38;
    box.replaceChildren();
    const xs=frames.map(f=>f.pose_x_post_step_m),ys=frames.map(f=>f.pose_y_post_step_m);
    const minX=Math.min(0,...xs),maxX=Math.max(1,...xs),minY=Math.min(-.5,...ys),maxY=Math.max(.5,...ys);
    const scale=Math.min((W-2*P)/(maxX-minX),(H-2*P)/(maxY-minY));
    const x=v=>W/2+(v-(minX+maxX)/2)*scale,y=v=>H/2-(v-(minY+maxY)/2)*scale;
    box.append(svg("path",{d:frames.map((f,i)=>(i?"L":"M")+x(f.pose_x_post_step_m)+","+y(f.pose_y_post_step_m)).join(" "),fill:"none",stroke:colors.post,"stroke-width":2}));
    const f=frames[index],cx=x(f.pose_x_post_step_m),cy=y(f.pose_y_post_step_m);
    box.append(svg("circle",{cx,cy,r:5,fill:colors.desired}),
      svg("line",{x1:cx,y1:cy,x2:cx+18*Math.cos(f.heading_post_step_rad),y2:cy-18*Math.sin(f.heading_post_step_rad),stroke:colors.desired,"stroke-width":3}),
      svg("text",{x:10,y:H-12},"x (m) → · y (m) ↑ · equal metric scale"),
      svg("text",{x:10,y:18},"x "+minX.toFixed(1)+"…"+maxX.toFixed(1)+" m / y "+minY.toFixed(1)+"…"+maxY.toFixed(1)+" m"));
    $("poseValue").textContent="POST completion "+(f.completion_time_ns/1e9).toFixed(2)+" s · heading "+fmt(f.heading_post_step_rad)+" rad · yaw "+fmt(f.yaw_rate_post_step_rad_s)+" rad/s";
  }
  function render(){
    if(!frames.length)return;
    const f=frames[index];$("frameIndex").value=index;$("scrubber").value=index;
    $("clock").textContent="Frame "+index+" / 799 · PRE "+(f.capture_time_ns/1e9).toFixed(2)+" s → POST "+(f.completion_time_ns/1e9).toFixed(2)+" s";
    plot("curvature",[{field:"desired_curvature_1pm",time:"capture_time_ns",color:colors.desired},
      {field:"actual_curvature_pre_step_1pm",time:"capture_time_ns",color:colors.pre},
      {field:"curvature_post_step_1pm",time:"completion_time_ns",color:colors.post}]);
    plot("torque",[{field:"controller_limited_torque",time:"decision_time_ns",color:colors.pre},
      {field:"final_requested_torque",time:"decision_time_ns",color:colors.post},
      {field:"applied_torque",time:"completion_time_ns",color:colors.desired}]);
    $("curvatureValue").textContent="INPUT desired "+fmt(f.desired_curvature_1pm)+" · PRE actual "+fmt(f.actual_curvature_pre_step_1pm)+" · POST plant "+fmt(f.curvature_post_step_1pm)+" 1/m";
    $("torqueValue").textContent="COMMAND limited/pre "+fmt(f.controller_limited_torque)+" · post/final "+fmt(f.final_requested_torque)+" · POST applied "+fmt(f.applied_torque)+" · applied ≠ EPS acknowledgement";
    pose();
    dl("state",{active:f.active,steeringPressed:f.steering_pressed,event:f.event,
      safety_limited:f.safety_limited,curvature_limited:f.curvature_limited,
      normalized_rail:f.normalized_rail_state,reset_events:f.reset_events.join(", ")||"none",
      speed_mps:f.speed_mps,roll_rad:f.roll_rad,capture_ns:String(f.capture_time_ns),decision_ns:String(f.decision_time_ns),completion_ns:String(f.completion_time_ns),phase:"LIMIT FLAGS = SYNTHETIC INPUT CONTEXT"});
    $("health").textContent=JSON.stringify(f.service_health,null,2);
    diag.renderCount++;diagnostics();
  }
  function setIndex(value){if(!Number.isInteger(value)||value<0||value>=frames.length)return;index=value;render();}
  function eventJump(direction){let next=index+direction;while(next>=0&&next<frames.length){if(frames[next].event!=="ORDINARY"){setIndex(next);return;}next+=direction;}}
  function tick(time){
    animationFrame=null;
    if(!playing)return;
    if(lastTick!==null)elapsed+=(time-lastTick)*Number($("speed").value);
    lastTick=time;
    const count=Math.floor(elapsed/10);
    if(count>0){elapsed-=count*10;setIndex(Math.min(799,index+count));}
    if(index===799){playing=false;$("play").textContent="Play";return;}
    animationFrame=requestAnimationFrame(tick);
  }
  $("play").addEventListener("click",()=>{playing=!playing;$("play").textContent=playing?"Pause":"Play";lastTick=null;elapsed=0;if(animationFrame!==null){cancelAnimationFrame(animationFrame);animationFrame=null;}if(playing){if(index===799)setIndex(0);animationFrame=requestAnimationFrame(tick);}});
  $("prev").addEventListener("click",()=>setIndex(Math.max(0,index-1)));
  $("next").addEventListener("click",()=>setIndex(Math.min(799,index+1)));
  $("prevEvent").addEventListener("click",()=>eventJump(-1));$("nextEvent").addEventListener("click",()=>eventJump(1));
  $("frameIndex").addEventListener("input",e=>setIndex(Number(e.target.value)));
  $("scrubber").addEventListener("input",e=>setIndex(Number(e.target.value)));
  async function start(){
    const catalog=await get("/api/catalog");if(catalog.runs.length!==1)throw Error("Single arm catalog required");
    const entry=catalog.runs[0];meta=await get("/api/runs/"+entry.run_id);
    if(meta.arm_count!==1||meta.arms[0]!=="UPSTREAM_BASELINE_CLOSED_LOOP"||meta.comparison_ready||meta.evidence_tier!=="T1_DESCRIPTIVE_COUNTERFACTUAL")throw Error("Evidence ceiling violation");
    for(let offset=0;offset<800;offset+=100){const page=await get("/api/runs/"+entry.run_id+"/frames?offset="+offset+"&limit=100");
      if(page.offset!==offset||page.count!==100||page.total!==800||page.frameset_receipt_sha256!==meta.receipt_sha256)throw Error("Page integrity");
      frames.push(...page.frames);diag.pages++;
    }
    if(frames.length!==800||frames.some((f,i)=>f.frame_index!==i||f.capture_time_ns!==i*10000000||f.completion_time_ns!==(i+1)*10000000))throw Error("Frame ordering");
    diag.frames=frames.length;
    $("runInfo").textContent=meta.arms[0]+" · 800 frames · 100 Hz · 8.00 s · SG_DISABLED";
    $("identity").textContent="trace "+meta.source_trace_sha256.slice(0,16)+"… | config "+meta.source_config_sha256.slice(0,16)+"… | "+Object.keys(meta.unavailable_fields).length+" unavailable fields";
    const box=$("availability");box.replaceChildren();
    for(const [field,reason] of Object.entries(meta.unavailable_fields)){const div=document.createElement("div"),title=document.createElement("strong"),why=document.createElement("small"),prov=document.createElement("small");
      div.className="unavailable";title.textContent=field+": unavailable";why.textContent=reason;prov.textContent="PROVENANCE: "+frames[0].provenance[field];div.append(title,why,prov);box.append(div);}
    dl("evidence",{tier:meta.evidence_tier,verdict:meta.verdict,source_trace_receipt:meta.source_receipt_sha256,
      frameset_receipt:meta.receipt_sha256,comparison:"BLOCKED · "+meta.comparison_reason,holdout:"CLOSED · opening_count 0"});
    for(const blocker of meta.blockers){const span=document.createElement("span");span.textContent=blocker;$("blockers").append(span);}
    $("status").textContent="Verified · read only";$("loaded").textContent="800 / 800 frames · 8 immutable pages";render();
  }
  start().catch(err=>{diag.javascriptErrors++;$("status").textContent="FAIL CLOSED: "+err.message;$("status").className="error";diagnostics();});
})();
