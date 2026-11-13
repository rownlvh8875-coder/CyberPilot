'use strict';
const $ = id => document.getElementById(id);
let token = '';
try { token = sessionStorage.getItem('cyberpilot-token') || ''; } catch (_) { /* session only in memory */ }
let lastSuccess = 0, lastPayload = null, lastReceiptWall = null, expiryTimer = null;
let pending = false, generation = 0;
const labels = {live:'최신 메시지', stale:'오래된 메시지 · 값 숨김', invalid:'유효하지 않은 메시지', missing:'메시지 없음'};
const show = (id, value) => { $(id).textContent = value ?? '—'; };
const bool = (value, yes, no) => typeof value === 'boolean' ? (value ? yes : no) : '—';
function clearValues() {
  for (const id of ['active','can','memory','disk','load','started','temperature','alert','branch','commit']) show(id,'—');
  for (const id of ['selfdrive-status','car-status','device-status','processes']) show(id,'최신 상태를 확인할 수 없음');
}
function disconnected() {
  clearTimeout(expiryTimer); lastPayload=null; lastSuccess=0;
  clearValues();
  show('connection','연결 끊김'); $('connection').className='badge stale';
  show('received','서버 응답 없음 · 마지막 값을 숨겼습니다');
}
function render(data) {
  show('connection','서버 연결됨'); $('connection').className='badge live';
  show('source',data.source === 'openpilot' ? '오픈파일럿 수신 모드' : '개발 호스트 모드 · 차량 데이터 없음');
  show('received','상태 수신 '+lastReceiptWall.toLocaleTimeString('ko-KR'));
  const topics=data.topics;
  const car=topics.carState, sd=topics.selfdriveState, device=topics.deviceState, manager=topics.managerState;
  show('active',bool(sd.data?.active,'활성','비활성'));
  show('can',bool(car.data?.can_valid,'연결됨','유효하지 않음'));
  for (const [id,topic] of [['selfdrive-status',sd],['car-status',car],['device-status',device]]) {
    show(id,labels[topic.status]+(topic.age_s === null ? '' : ' · '+Math.floor(topic.age_s)+'초 전'));
  }
  const host=data.host;
  show('memory',host?.memory_usage_percent == null ? '—' : host.memory_usage_percent.toFixed(1)+'%');
  show('disk',host?.disk_free_bytes == null ? '—' : (host.disk_free_bytes/1073741824).toFixed(1)+' GiB');
  show('load',host?.load_1m == null ? '—' : host.load_1m.toFixed(2));
  show('host-source',host ? `${host.platform} / ${host.architecture} · 서버 호스트의 실제 관측값` : '호스트 상태 수신 없음');
  show('started',bool(device.data?.started,'시작됨','대기'));
  const temps=device.data?.cpu_temp_c;
  show('temperature',temps?.length ? Math.max(...temps).toFixed(1)+' °C' : '—');
  show('alert',sd.data ? [sd.data.alert_text_1,sd.data.alert_text_2].filter(Boolean).join('\n') || '수신된 경고 없음' : '경고 상태 미확인');
  const procs=manager.data?.processes;
  const failed=procs?.filter(p=>p.should_be_running === true && p.running === false);
  show('processes',procs ? failed.length ? '실행 필요 프로세스 중지: '+failed.map(p=>p.name || '이름 미상').join(', ') : '수신된 중지 프로세스 없음' : labels[manager.status]);
  show('collector-error',data.collector_error ? '오픈파일럿 소스 연결 불가 · 메시지 수신을 확인하세요.' : '');
  show('branch',data.identity.branch); show('commit',data.identity.commit);
}
function ageSnapshot(data, elapsed) {
  const topics={};
  for (const [name, record] of Object.entries(data.topics)) {
    const age=record.age_s === null ? null : record.age_s+elapsed;
    const expired=record.status === 'live' && age !== null && age>=5;
    topics[name]={...record,age_s:age,status:expired ? 'stale' : record.status,data:expired ? null : record.data};
  }
  const hostAge=data.host_age_s === null ? null : data.host_age_s+elapsed;
  return {...data,topics,host_age_s:hostAge,host:hostAge !== null && hostAge<5 ? data.host : null};
}
function refreshView() {
  clearTimeout(expiryTimer);
  if (!lastPayload || !lastSuccess) return;
  const elapsed=(performance.now()-lastSuccess)/1000;
  if (elapsed>=5) { disconnected(); return; }
  render(ageSnapshot(lastPayload,elapsed));
  const remaining=[5-elapsed];
  for (const record of Object.values(lastPayload.topics)) {
    if (record.status === 'live' && record.age_s !== null && record.age_s+elapsed<5) remaining.push(5-record.age_s-elapsed);
  }
  if (lastPayload.host && lastPayload.host_age_s !== null && lastPayload.host_age_s+elapsed<5) remaining.push(5-lastPayload.host_age_s-elapsed);
  expiryTimer=setTimeout(refreshView,Math.max(1,Math.min(...remaining)*1000));
}
function logout() {
  generation++; token=''; lastSuccess=0; lastPayload=null; clearTimeout(expiryTimer);
  try { sessionStorage.removeItem('cyberpilot-token'); } catch (_) { /* optional storage */ }
  $('dashboard').hidden=true; $('login').hidden=false; $('token').value=''; clearValues();
  show('connection','연결 대기'); $('connection').className='badge';
}
async function poll() {
  if (!token || pending) return;
  pending=true; const current=generation; const requestedAt=performance.now();
  try {
    const response=await fetch('/api/status',{headers:{Authorization:'Bearer '+token},cache:'no-store',signal:AbortSignal.timeout(4000)});
    if (current!==generation) return;
    if (response.status===401) { logout(); show('login-error','토큰을 확인해주세요.'); return; }
    if (!response.ok) throw new Error('unavailable');
    const data=await response.json();
    if (current!==generation) return;
    // Whole round-trip time overestimates transit age conservatively; never
    // claim a sample is fresher just because response delivery was slow.
    const receivedAt=performance.now(), transit=(receivedAt-requestedAt)/1000;
    for (const record of Object.values(data.topics)) if (record.age_s !== null) record.age_s+=transit;
    if (data.host_age_s !== null) data.host_age_s+=transit;
    lastPayload=data; lastSuccess=receivedAt; lastReceiptWall=new Date(); refreshView();
    $('login').hidden=true; $('dashboard').hidden=false; show('login-error','');
  } catch (_) {
    if (current===generation) { disconnected(); show('login-error','연결할 수 없습니다. 서버와 주소를 확인해주세요.'); }
  } finally { pending=false; }
}
$('login').addEventListener('submit',event=>{
  event.preventDefault(); generation++; token=$('token').value.trim();
  try { sessionStorage.setItem('cyberpilot-token',token); } catch (_) { /* memory fallback */ }
  $('token').value=''; poll();
});
$('logout').addEventListener('click',logout);
// Optional fragment pairing avoids putting credentials in HTTP paths/access logs.
if (location.hash.startsWith('#token=')) {
  token=location.hash.slice(7); history.replaceState(null,'',location.pathname);
  try { sessionStorage.setItem('cyberpilot-token',token); } catch (_) { /* memory fallback */ }
}
setInterval(poll,1000);
document.addEventListener('visibilitychange',refreshView);
poll();
