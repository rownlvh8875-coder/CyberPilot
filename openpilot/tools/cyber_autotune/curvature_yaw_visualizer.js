"use strict";
const bundle = JSON.parse(document.getElementById("screening-data").textContent);
const colors = ["#9dacf9", "#81d3bd", "#ffb263"];
const ids = ["baseline", "current", "candidate"];
const choice = document.getElementById("scenario");
const cursor = document.getElementById("cursor");
bundle.reports.forEach((r, i) => {
  const option = document.createElement("option");
  option.value = String(i);
  option.textContent = r.manifest.scenario;
  choice.appendChild(option);
});
const fmt = x => Math.abs(x) < 1e-3 && x !== 0 ? x.toExponential(3) : x.toFixed(4);
function plot(id, series, xLabel, yLabel, events = []) {
  const svg = document.getElementById(id);
  const values = series.flatMap(s => s.points);
  if (!values.length) { svg.innerHTML = ""; return; }
  const xs = values.map(p => p[0]), ys = values.map(p => p[1]);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  let ymin = Math.min(0, ...ys), ymax = Math.max(0, ...ys);
  if (ymin === ymax) { ymin -= 1; ymax += 1; }
  const pad = (ymax - ymin) * .08; ymin -= pad; ymax += pad;
  const x = v => 75 + (v - xmin) / Math.max(xmax - xmin, 1e-12) * 760;
  const y = v => 202 - (v - ymin) / (ymax - ymin) * 176;
  let out = "";
  for (let i = 0; i < 5; i++) {
    const v = ymin + (ymax - ymin) * i / 4;
    out += '<line x1="75" x2="835" y1="'+y(v)+'" y2="'+y(v)+'" stroke="#354055"/>';
    out += '<text x="5" y="'+(y(v)+4)+'">'+fmt(v)+'</text>';
  }
  out += '<text x="75" y="223">'+fmt(xmin)+'</text><text x="770" y="223">'+fmt(xmax)+'</text>';
  out += '<text x="400" y="246">'+xLabel+'</text><text x="80" y="16">'+yLabel+'</text>';
  series.forEach(s => {
    const points = s.points.map(p => x(p[0])+","+y(p[1])).join(" ");
    out += '<polyline data-series="'+s.name+'" fill="none" stroke="'+s.color+'" stroke-width="2"'+
      (s.dash ? ' stroke-dasharray="'+s.dash+'"' : '')+' points="'+points+'"/>';
  });
  events.forEach(e => {
    out += '<circle cx="'+x(e.x)+'" cy="'+y(e.y)+'" r="'+e.radius+'" fill="'+e.color+'"><title>'+e.label+'</title></circle>';
  });
  svg.innerHTML = out;
}
function render() {
  const report = bundle.reports[Number(choice.value)];
  const step = Number(cursor.value);
  const selected = ids.map(id => document.getElementById(id).checked);
  const list = (field, xfield = "time_s", applied = false) => report.arms.flatMap((a,i) => selected[i] ? [{
    points:a.samples.map(s => [s[xfield],s[field]]), color:colors[i],
    dash:applied ? "7 4" : i === 1 ? "2 6" : "", name:ids[i]+"-"+field
  }] : []);
  plot("trajectory",list("pose_y_m","pose_x_m"),"Observer x (m) · SYNTHETIC","Observer y (m)");
  const desired = report.arms[0].samples.map(s => [s.time_s,s.desired_curvature_1pm]);
  plot("curvature",[{points:desired,color:"#ffffff",dash:"6 4",name:"desired"},...list("curvature_1pm")],"Time (s)","Curvature (1/m)");
  const markers = report.arms.flatMap((a,i) => selected[i] ? [
    ...a.diagnostics.zero_crossing_steps.map(n => ({...a.samples[n], label:"zero crossing"})),
    ...a.diagnostics.reversal_steps.map(n => ({...a.samples[n], label:"reversal"})),
    ...a.samples.filter(s => s.saturated).map(s => ({...s,label:"saturation"}))
  ].map(s => ({x:s.time_s,y:s.requested_torque,color:s.label==="saturation"?"#ee7787":colors[i],
               radius:s.label==="saturation"?1.8:3,label:s.label+" · "+ids[i]+" · "+s.time_s.toFixed(2)+" s"})) : []);
  plot("torque",[...list("requested_torque"),...list("applied_normalized_torque","time_s",true)],"Time (s)","Normalized torque",markers);
  plot("angle",list("steering_angle_deg"),"Time (s)","Pre-step steering angle (deg)");
  const a = report.arms[0].samples, b = report.arms[2].samples;
  plot("delta",[{points:b.map((s,i)=>[s.time_s,s.pose_y_m-a[i].pose_y_m]),color:colors[2],name:"candidate-minus-baseline"}],"Time (s)","Candidate − baseline y (m)");
  const row = report.arms[0].samples[step];
  document.getElementById("clock").textContent = row.time_s.toFixed(2)+" s";
  document.getElementById("cursor-readout").textContent = "Curve phase: "+row.phase+" · "+row.speed_mps.toFixed(2)+
    " m/s · active: "+row.active+" · steering pressed: "+row.steering_pressed+"\n"+
    report.arms.map((arm,i) => {
      const s=arm.samples[step], d=arm.diagnostics;
      return ids[i].toUpperCase()+": curvature "+s.curvature_1pm.toExponential(7)+", requested "+
        s.requested_torque.toFixed(9)+", applied "+s.applied_normalized_torque.toFixed(9)+
        ", saturation "+s.saturated+", zero crossing "+d.zero_crossing_steps.includes(step)+
        ", reversal "+d.reversal_steps.includes(step);
    }).join("\n");
  const metrics = [["Curvature RMSE (1/m)","curvature_tracking_rmse_1pm"],
    ["Command derivative RMS (/s)","command_derivative_rms_per_s"],
    ["Max command derivative (/s)","max_abs_command_derivative_per_s"],
    ["Command zero crossings","command_zero_crossings"],["Reversal events","command_reversals"],
    ["Reversal rate (Hz)","command_reversal_rate_hz"],["Saturation occupancy","saturation_occupancy"]];
  document.getElementById("diagnostics").innerHTML = "<table><thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Candidate</th></tr></thead><tbody>"+
    metrics.map(([label,key])=>"<tr><td>"+label+"</td>"+report.arms.map(arm=>"<td>"+fmt(arm.diagnostics[key])+"</td>").join("")+"</tr>").join("")+"</tbody></table>";
  document.getElementById("identity").textContent = JSON.stringify({artifact:bundle.artifact,
    receipt_sha256:report.receipt_sha256,manifest_sha256:report.manifest_sha256,
    candidate_difference:report.candidate_difference,manifest:report.manifest},null,2);
}
choice.addEventListener("change",()=>{cursor.value="0";render();});
cursor.addEventListener("input",render);
ids.forEach(id=>document.getElementById(id).addEventListener("change",render));
render();
