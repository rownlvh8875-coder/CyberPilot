"use strict";
const rejection = bundle.rejection;
const clusterChoice = document.getElementById("violation-cluster");
const v1Choice = document.getElementById("v1-overlay");
let selectedViolation = null;
function violationTable() {
  const body = document.getElementById("violation-rows");
  body.innerHTML = "";
  const cluster = rejection.ledger.clusters.find(c=>c.cluster===clusterChoice.value);
  const rows = rejection.ledger.violations.filter(r=>!cluster || cluster.violation_ids.includes(r.violation_id));
  for (const row of rows) {
    const tr = document.createElement("tr");
    const cell = document.createElement("td");
    const button = document.createElement("button");
    button.textContent = row.scenario+" · "+row.speed_bucket+" · "+row.phase+" · "+row.metric;
    button.dataset.violationId = row.violation_id;
    button.addEventListener("click",()=>{
      choice.value=String(bundle.reports.findIndex(r=>r.manifest.scenario===row.scenario));
      cursor.value=String(row.step_indexes[0]);
      selectedViolation=row;
      render();
      renderRejection();
    });
    cell.appendChild(button); tr.appendChild(cell);
    for (const role of ["UPSTREAM_BASELINE","CYBER_CURRENT","CYBER_CANDIDATE_V1","CYBER_CANDIDATE_V2"]) {
      const td=document.createElement("td");td.textContent=fmt(row.values[role]);tr.appendChild(td);
    }
    for (const value of [row.delta_vs_baseline,row.delta_vs_v1,row.violation_magnitude]) {
      const td=document.createElement("td");td.textContent=fmt(value);tr.appendChild(td);
    }
    const td=document.createElement("td");td.textContent=row.rule;tr.appendChild(td);
    body.appendChild(tr);
  }
  document.getElementById("violation-count").textContent=rows.length+" / "+rejection.ledger.violation_count+" violations";
}
function renderRejection() {
  const report=bundle.reports[Number(choice.value)], n=Number(cursor.value);
  const arms=[report.arms[0],report.arms[1],report.attribution.v1_arm,report.arms[2]];
  const names=["baseline","current","v1","candidate"], palette=[colors[0],colors[1],"#d68eee",colors[2]];
  const checked=[document.getElementById("baseline").checked,document.getElementById("current").checked,
                 v1Choice.checked,document.getElementById("candidate").checked];
  const firstIndex=arms[3].samples.findIndex((s,i)=>s.requested_torque!==arms[2].samples[i].requested_torque);
  const first=firstIndex<0?null:firstIndex;
  const marker=field=>first===null || !checked[2] || !checked[3]?[]:[{x:arms[3].samples[first].time_s,y:arms[3].samples[first][field],
    radius:5,color:"#ffffff",label:"Exact requested divergence V2 − V1 at step "+first}];
  const series=(field,xfield="time_s",applied=false)=>arms.flatMap((a,i)=>checked[i]?[{
    points:a.samples.map(s=>[s[xfield],s[field]]),color:palette[i],name:names[i]+"-"+field,
    dash:applied?"7 4":i===1?"2 6":i===2?"6 4":""}]:[]);
  plot("trajectory",series("pose_y_m","pose_x_m"),"Observer x (m) · SYNTHETIC","Observer y (m)");
  const desired=arms[0].samples.map(s=>[s.time_s,s.desired_curvature_1pm]);
  plot("curvature",[{points:desired,color:"#ffffff",dash:"6 4",name:"desired"},...series("curvature_1pm")],
       "Time (s)","Curvature (1/m)",marker("curvature_1pm"));
  const events=arms.flatMap((a,i)=>checked[i]?[
    ...a.diagnostics.zero_crossing_steps.map(k=>({k,label:"zero crossing"})),
    ...a.diagnostics.reversal_steps.map(k=>({k,label:"reversal"})),
    ...a.samples.filter(s=>s.saturated).map(s=>({k:s.step_index,label:"saturation"}))
  ].map(e=>({x:a.samples[e.k].time_s,y:a.samples[e.k].requested_torque,color:e.label==="saturation"?"#ee7787":palette[i],
            radius:e.label==="saturation"?1.8:3,label:e.label+" "+names[i]+" step "+e.k})):[]);
  plot("torque",[...series("requested_torque"),...series("applied_normalized_torque","time_s",true)],
       "Time (s)","Native torque",events.concat(marker("requested_torque")));
  plot("angle",[{points:arms[0].samples.map(s=>[s.time_s,s.desired_steering_angle_deg]),color:"#ffffff",
       dash:"6 4",name:"desired-steering-angle"},...series("steering_angle_deg")],"Time (s)","Pre-step angle (deg)");
  plot("command-derivative",series("command_derivative_per_s"),"Time (s)","Requested derivative (/s)");
  plot("applied-derivative",series("torque_derivative_per_s"),"Time (s)","Applied delayed derivative (/s)");
  for (const [id,field] of [["requested-delta","requested_torque"],["applied-delta","applied_normalized_torque"],
      ["residual-delta","curvature_residual_1pm"],["derivative-delta","command_derivative_per_s"]]) {
    const lines=arms.flatMap((a,i)=>i>=2 && checked[i]?[{points:a.samples.map((s,k)=>[s.time_s,s[field]-arms[0].samples[k][field]]),
      color:palette[i],dash:i===2?"6 4":"",name:names[i]+"-minus-baseline-"+field}]:[]);
    plot(id,lines,"Time (s)",field+" Δ vs baseline");
  }
  for (const [id,index,label] of [["factor-schedule",0,"Factor Δ vs baseline"],["friction-schedule",2,"Friction Δ vs baseline"]]) {
    const lines=arms.flatMap((a,i)=>checked[i]?[{points:a.samples.map((s,k)=>[s.time_s,
      report.schedules[a.arm][k][index]-report.schedules[arms[0].arm][k][index]]),color:palette[i],name:names[i]+"-"+id}]:[]);
    plot(id,lines,"Time (s)",label);
  }
  for (const field of ["pid_p","pid_i","pid_f","pid_control"]) {
    const lines=arms.flatMap((a,i)=>checked[i] && report.passive_pid?[{
      points:report.passive_pid[a.arm].observations.map((r,k)=>[a.samples[k].time_s,r[field]]),
      color:palette[i],name:names[i]+"-"+field}]:[]);
    plot(field,lines,"Time (s)",field+" (m/s²)");
  }
  const row=arms[0].samples[n];
  const schedules=arms.map(a=>{
    const p=report.schedules[a.arm][n],pid=report.passive_pid?report.passive_pid[a.arm].observations[n]:null;
    return a.arm+": factor="+p[0]+" friction="+p[2]+(pid?" P="+pid.pid_p+" I="+pid.pid_i+
      " F="+pid.pid_f+" control="+pid.pid_control+" clipped="+pid.pid_limit_clipped:" · passive PID not supplied");
  }).join("\n");
  document.getElementById("rejection-readout").textContent=
    "SYNTHETIC / NO INDEPENDENT LANE TRUTH\n"+row.speed_bucket+" · "+row.phase+" · "+row.speed_mps+" m/s\n"+
    (first===null?"No V2/V1 requested divergence in this scenario":
      "Exact global requested divergence V2 − V1: step "+first+" / "+arms[3].samples[first].time_s+" s")+
    (selectedViolation && selectedViolation.scenario===report.manifest.scenario?
      "\nSelected violation: "+selectedViolation.metric+" · original steps "+selectedViolation.step_indexes[0]+".."+
      selectedViolation.step_indexes[selectedViolation.step_indexes.length-1]+" · "+selectedViolation.rule:"")+"\n"+schedules;
  document.getElementById("family-decision").textContent=rejection.family_decision?
    rejection.family_decision.verdict+" · V2 remains REJECTED · V3 not created · explanatory ablations only":
    "Family decision not supplied · frozen nominal V2 REJECTED";
}
const all=document.createElement("option");all.value="ALL";all.textContent="All violation clusters";clusterChoice.appendChild(all);
for(const c of rejection.ledger.clusters){const option=document.createElement("option");option.value=c.cluster;
  option.textContent=c.cluster+" ("+c.count+")";clusterChoice.appendChild(option);}
clusterChoice.value="ALL";clusterChoice.addEventListener("change",violationTable);
choice.addEventListener("change",()=>{selectedViolation=null;renderRejection();});
cursor.addEventListener("input",renderRejection);
for(const id of ["baseline","current","candidate"])document.getElementById(id).addEventListener("change",renderRejection);
v1Choice.addEventListener("change",renderRejection);
violationTable();renderRejection();
