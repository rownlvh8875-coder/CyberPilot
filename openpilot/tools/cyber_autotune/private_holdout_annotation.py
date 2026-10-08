"""Local blind-first manual ego-boundary pixels, with immutable first decisions.

Raw image + user's points only. Entire sixty-decision freeze precedes any
detector comparison gate. No inference/AI/model/projection/remote asset path.
"""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import stat
from pathlib import Path
import secrets
import threading

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import private_pixel_executor as encoded
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

CSP = "default-src 'none'; img-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
MAX_BODY = 64 * 1024  # Bounded manual 2x12-point payload, not a quality threshold.

HTML = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>Blind private lane annotation</title>
<style>body{background:#101925;color:#eef4fa;font:16px system-ui;margin:20px}
button,select,input{font:inherit;padding:7px;margin:4px}canvas{background:#243044;max-width:100%;touch-action:none}
.warn{color:#ffc57e}fieldset{max-width:1080px}#status{white-space:pre-wrap}button:disabled{opacity:.4}</style>
<h1>BLIND-FIRST HUMAN PIXEL ANNOTATION</h1>
<p class="warn">LOCAL PRIVATE ONLY · PIXEL REFERENCE · NO METER / VEHICLE QUALIFICATION</p>
<p>현재 주행 lane의 보이는 좌/우 경계만 표시하세요. 인접 lane, shoulder, merge guide를 자동으로 ego 경계로 보지 마세요.
불확실하면 AMBIGUOUS를 선택하세요. 안 보이는 구간을 연장하지 마세요.</p>
<p>각 선은 아래쪽(가까운 곳)부터 위쪽(먼 곳)으로 3–12개 점. Detector/AI/model/geometry는 표시하지 않습니다.</p>
<button id="prev">Previous [←]</button><select id="frames" aria-label="Frame"></select><button id="next">Next [→]</button>
<button id="jump">Jump to unreviewed [J]</button><span id="progress"></span>
<fieldset><label>Opaque reviewer ID <input id="reviewer" placeholder="개인정보 없는 reviewer ID"></label>
<select id="state" aria-label="Human visibility state"><option value="">상태를 직접 선택하세요</option>
<option>BOTH_EGO_BOUNDARIES_VISIBLE</option><option>LEFT_ONLY_VISIBLE</option><option>RIGHT_ONLY_VISIBLE</option>
<option>EGO_BOUNDARIES_AMBIGUOUS</option><option>INTERSECTION_OR_MERGE</option>
<option>NO_CLEAR_LANE_MARKINGS</option><option>UNREVIEWABLE</option></select>
<label><input type="radio" name="side" value="left" checked>Left [L]</label>
<label><input type="radio" name="side" value="right">Right [R]</label>
<button id="undo">Undo last point [U]</button><button id="clear-left">Clear left</button><button id="clear-right">Clear right</button>
<label><input id="pan-mode" type="checkbox">Pan mode [P]</label>
<label>Zoom <input id="zoom" type="range" min="0.5" max="6" step="0.1" value="1"></label>
<p>Shift+drag 또는 오른쪽 버튼 drag로 pan. Zoom 후 클릭도 원본 좌표로 저장됩니다.</p></fieldset>
<canvas id="canvas" width="1100" height="680"></canvas><pre id="points"></pre>
<p><label><input id="ack" type="checkbox">I annotated this frame without viewing detector/AI/model output.</label></p>
<button id="draft">Save editable draft</button><button id="save">Save immutable first decision</button>
<button id="comparison" disabled>Detector comparison gate: 60/60 freeze required</button>
<p id="status"></p><p class="warn">저장 후 첫 판단은 수정 불가. 재검토는 별도 correction receipt이며 첫 blind 판단을 덮어쓰지 않습니다.</p>
<script>
const q=s=>document.querySelector(s),canvas=q('#canvas'),ctx=canvas.getContext('2d');
let data,index=0,image,body,scale=1,ox=0,oy=0,locked=false,generation=0,lastSide='left',pan=null,loadedIndex=-1,imageBinding=null;
const edits=['state','ack','draft','save','undo','clear-left','clear-right'];
function report(e){q('#status').textContent=e.message;}
async function request(path,payload){const options=payload===undefined?{}:{method:'POST',headers:{
'Content-Type':'application/json','X-Review-Token':data.token},body:JSON.stringify(payload)};
const r=await fetch(path,options);const value=await r.json();if(!r.ok)throw new Error(value.error||'Local request failed');return value;}
function form(){if(!image||loadedIndex!==index||locked)throw new Error('Bound raw image must finish loading before save');
return {state:q('#state').value,left:body.left,right:body.right,
acknowledged_blind:q('#ack').checked,reviewer_id:q('#reviewer').value};}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);if(!image)return;
ctx.save();ctx.translate(ox,oy);ctx.scale(scale,scale);ctx.drawImage(image,0,0);
['left','right'].forEach((side,i)=>{const points=body[side];ctx.strokeStyle=i?'#ffcf62':'#5be6df';ctx.fillStyle=ctx.strokeStyle;
ctx.lineWidth=2/scale;ctx.beginPath();points.forEach(([x,y],n)=>{if(n)ctx.lineTo(x,y);else ctx.moveTo(x,y);});ctx.stroke();
points.forEach(([x,y],n)=>{ctx.beginPath();ctx.arc(x,y,4/scale,0,Math.PI*2);ctx.fill();
ctx.font=12/scale+'px system-ui';ctx.fillText(n+1,x+6/scale,y);});});ctx.restore();
q('#points').textContent=JSON.stringify({original_width:image.naturalWidth,original_height:image.naturalHeight,
coordinate_units:'ORIGINAL IMAGE PIXELS',left:body.left,right:body.right},null,2);}
async function reloadData(){data=await request('/data');q('#progress').textContent=data.progress.reviewed+' / 60 · '+data.progress.status;
q('#comparison').disabled=data.progress.reviewed!==60;}
async function show(){const stamp=++generation;image=null;loadedIndex=-1;imageBinding=null;pan=null;
body={left:[],right:[],state:'',acknowledged_blind:false,reviewer_id:q('#reviewer').value};
q('#ack').checked=false;edits.forEach(id=>q('#'+id).disabled=true);q('#reviewer').disabled=true;
q('#status').textContent='LOADING RAW IMAGE — saving disabled';ctx.clearRect(0,0,canvas.width,canvas.height);
q('#frames').value=index;const value=await request('/annotation/'+index);if(stamp!==generation)return;
locked=!!value.first;body=value.first||value.draft||{left:[],right:[],state:'',acknowledged_blind:false,reviewer_id:q('#reviewer').value};
q('#state').value=body.state;q('#ack').checked=body.acknowledged_blind;q('#reviewer').value=body.reviewer_id;
imageBinding=value.image_receipt_sha256;
q('#status').textContent=locked?'IMMUTABLE FIRST DECISION — raw + human points only':'UNREVIEWED — original image only';
q('#zoom').value=1;scale=1;ox=oy=0;const img=new Image();img.onload=()=>{if(stamp!==generation)return;image=img;loadedIndex=index;
edits.forEach(id=>q('#'+id).disabled=locked);q('#reviewer').disabled=locked;draw();};
img.onerror=()=>report(new Error('Bound local raw image unavailable'));img.src='/image/'+index;}
function position(e){const rect=canvas.getBoundingClientRect();return [(e.clientX-rect.left)*canvas.width/rect.width,
(e.clientY-rect.top)*canvas.height/rect.height];}
canvas.oncontextmenu=e=>e.preventDefault();
canvas.onpointerdown=e=>{if(!image)return;const [x,y]=position(e);
if(e.shiftKey||e.button===2||q('#pan-mode').checked){pan={x,y,ox,oy};canvas.setPointerCapture(e.pointerId);return;}
if(locked||loadedIndex!==index)return;const side=q('input[name=side]:checked').value,point=[(x-ox)/scale,(y-oy)/scale];
if(point[0]<0||point[0]>image.naturalWidth-1||point[1]<0||point[1]>image.naturalHeight-1){report(new Error('Point outside original image'));return;}
if(body[side].length>=12){report(new Error('Maximum 12 visible control points'));return;}body[side].push(point);lastSide=side;draw();};
canvas.onpointermove=e=>{if(!pan)return;const [x,y]=position(e);ox=pan.ox+x-pan.x;oy=pan.oy+y-pan.y;draw();};
canvas.onpointerup=()=>{pan=null;};
q('#zoom').oninput=()=>{const next=Number(q('#zoom').value),cx=canvas.width/2,cy=canvas.height/2;
ox=cx-(cx-ox)*next/scale;oy=cy-(cy-oy)*next/scale;scale=next;draw();};
q('#undo').onclick=()=>{if(!locked){body[lastSide].pop();draw();}};
['left','right'].forEach(side=>q('#clear-'+side).onclick=()=>{if(!locked){body[side]=[];draw();}});
q('#prev').onclick=()=>{index=(index+59)%60;show().catch(report);};
q('#next').onclick=()=>{index=(index+1)%60;show().catch(report);};
q('#frames').onchange=()=>{index=Number(q('#frames').value);show().catch(report);};
q('#jump').onclick=()=>{const n=data.frames.findIndex(f=>!f.reviewed);if(n>=0){index=n;show().catch(report);}};
q('#draft').onclick=async()=>{try{await request('/draft/'+loadedIndex,
{image_receipt_sha256:imageBinding,annotation:form()});q('#status').textContent='DRAFT saved · not human completion';}catch(e){report(e);}};
q('#save').onclick=async()=>{try{await request('/save/'+loadedIndex,
{image_receipt_sha256:imageBinding,annotation:form()});await reloadData();await show();}catch(e){report(e);}};
q('#comparison').onclick=async()=>{try{const value=await request('/detector/'+index);q('#status').textContent=JSON.stringify(value);}catch(e){report(e);}};
document.onkeydown=e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;
const key=e.key.toLowerCase();if(key==='p')q('#pan-mode').checked=!q('#pan-mode').checked;
if(key==='l'||key==='r')q('input[name=side][value='+(key==='l'?'left':'right')+']').checked=true;
const map={arrowleft:'prev',arrowright:'next',u:'undo',j:'jump'};if(map[key]){e.preventDefault();q('#'+map[key]).click();}};
reloadData().then(()=>{data.frames.forEach((f,i)=>{const option=document.createElement('option');option.value=i;
option.textContent='Frame '+(i+1)+' · '+f.sample_id.slice(0,12);q('#frames').appendChild(option);});return show();}).catch(report);
</script></html>"""


class ReviewStore:
  def __init__(self, root):
    self.root = h.private_path(root)
    self.package = h.read(self.root / 'materialization.json')
    unseal(self.package)
    expected = h.materialization_complete(self.package['frozen_manifest'], self.package['authorization'], self.package['images'])
    if canonical(expected) != canonical(self.package):
      raise ValueError('EXACT_FROZEN_MATERIALIZATION_REQUIRED')
    self.recover_reference()

  def recover_reference(self):
    self.progress()  # Reject unknown rows even before recovery can create a set marker.
    with storage.writer_lease(self.root):
      rows = [self.first(i) for i in range(h.EXPECTED)]
      path = self.root / 'human-reference.json'
      if all(row is not None for row in rows):
        if not path.exists():
          h.write_immutable(path, h.freeze_reference(self.package, rows, encoded.utc()))
        reference = h.read(path)
        h.require_detector_gate(self.package, reference)
        if canonical(reference['annotations']) != canonical(rows):
          raise ValueError('FROZEN_SET_MUST_MATCH_IMMUTABLE_FIRST_ROWS')
      elif path.exists():
        raise ValueError('MISSING_FIRST_ROW_IN_FROZEN_SET')

  def image(self, ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < h.EXPECTED:
      raise ValueError('UNKNOWN_FRAME')
    return self.package['images'][ordinal]

  def first(self, ordinal):
    image = self.image(ordinal)
    path = self.root / 'annotations' / (image['sample_id'] + '.json')
    if not path.exists():
      return None
    row = h.read(path)
    unseal(row)
    body = {key: row[key] for key in ('state', 'left', 'right', 'reviewer_id', 'acknowledged_blind')}
    if canonical(row) != canonical(h.annotation(image, body, row['saved_at'])):
      raise ValueError('IMMUTABLE_FIRST_DECISION_BINDING_MISMATCH')
    return row

  def progress(self):
    expected = {i['sample_id'] + '.json' for i in self.package['images']}
    directory = self.root / 'annotations'
    h.private_path(directory)
    if directory.exists() and {p.name for p in directory.glob('*.json')} - expected:
      raise ValueError('UNKNOWN_OR_DUPLICATE_ANNOTATION')
    rows = [self.first(i) for i in range(h.EXPECTED)]
    count = sum(row is not None for row in rows)
    return {'reviewed': count, 'unreviewed': h.EXPECTED - count, 'total': h.EXPECTED,
            'status': 'PRIVATE_BLIND_HUMAN_HOLDOUT_COMPLETE' if count == h.EXPECTED else 'PRIVATE_HUMAN_HOLDOUT_READY_FOR_REVIEW'}

  def view(self):
    return {'progress': self.progress(), 'frames': [
      {'sample_id': image['sample_id'], 'image_sha256': image['image_sha256'],
       'width': image['width'], 'height': image['height'], 'image_receipt_sha256': image['receipt_sha256'], 'reviewed': self.first(i) is not None}
      for i, image in enumerate(self.package['images'])]}

  def load_draft(self, ordinal):
    image = self.image(ordinal)
    path = self.root / 'drafts' / (image['sample_id'] + '.json')
    if not path.exists():
      return None
    value = h.read(path)
    unseal(value)
    if value['image_sha256'] != image['image_sha256'] or value['image_receipt_sha256'] != image['receipt_sha256']:
      raise ValueError('STALE_DRAFT_IMAGE_BINDING')
    h.validate_body(image, value['body'], draft=True)
    return value['body']

  def draft(self, ordinal, body):
    image = self.image(ordinal)
    h.validate_body(image, body, draft=True)
    with storage.writer_lease(self.root):
      if self.first(ordinal) is not None:
        raise ValueError('FIRST_DECISION_ALREADY_IMMUTABLE')
      path = h.private_path(self.root / 'drafts' / (image['sample_id'] + '.json'))
      storage.atomic_json(path, seal({'schema': 'PRIVATE_PIXEL_DRAFT_V1', 'image_sha256': image['image_sha256'],
                                     'image_receipt_sha256': image['receipt_sha256'], 'body': body}))
    return {'status': 'DRAFT_NOT_COMPLETION'}

  def save(self, ordinal, body):
    image = self.image(ordinal)
    row = h.annotation(image, body, encoded.utc())
    with storage.writer_lease(self.root):
      existing = self.first(ordinal)
      if existing is not None:
        if {k: existing[k] for k in body} != body:
          raise ValueError('IMMUTABLE_FIRST_DECISION_NO_OVERWRITE')
        return existing
      h.write_immutable(self.root / 'annotations' / (image['sample_id'] + '.json'), row)
      rows = [self.first(i) for i in range(h.EXPECTED)]
      if all(r is not None for r in rows):
        h.write_immutable(self.root / 'human-reference.json', h.freeze_reference(self.package, rows, encoded.utc()))
    return row

  def correct(self, ordinal, body, reason):
    with storage.writer_lease(self.root):
      first = self.first(ordinal)
      if first is None:
        raise ValueError('FIRST_DECISION_REQUIRED_BEFORE_CORRECTION')
      row = h.correction(first, body, encoded.utc(), reason)
      h.write_immutable(self.root / 'corrections' / first['receipt_sha256'] / (row['receipt_sha256'] + '.json'), row)
    return row

  def require_comparison(self):
    self.progress()
    path = self.root / 'human-reference.json'
    if not path.exists():
      raise ValueError('ALL_SIXTY_BLIND_DECISIONS_REQUIRED_BEFORE_DETECTOR')
    reference = h.read(path)
    rows = [self.first(i) for i in range(h.EXPECTED)]
    if any(row is None for row in rows) or canonical(rows) != canonical(reference['annotations']):
      raise ValueError('ALL_CURRENT_IMMUTABLE_FIRST_ROWS_REQUIRED')
    h.require_detector_gate(self.package, reference)


@contextmanager
def server(root, *, bind='127.0.0.1', port=0):
  if bind != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  store = ReviewStore(root)
  token = secrets.token_hex(32)

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def respond(self, status, value, kind='application/json'):
      data = value if isinstance(value, bytes) else canonical(value)
      self.send_response(status)
      self.send_header('Content-Type', kind)
      self.send_header('Content-Length', str(len(data)))
      self.send_header('Content-Security-Policy', CSP)
      self.send_header('Cache-Control', 'no-store')
      self.send_header('X-Content-Type-Options', 'nosniff')
      self.end_headers()
      self.wfile.write(data)

    def allowed(self):
      return (self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
              and self.headers.get('Origin', f'http://127.0.0.1:{self.server.server_port}') == f'http://127.0.0.1:{self.server.server_port}')

    def do_GET(self):
      if not self.allowed():
        self.respond(403, {'error': 'LOCAL_ORIGIN_REQUIRED'})
        return
      try:
        if self.path == '/':
          self.respond(200, HTML.encode(), 'text/html; charset=utf-8')
        elif self.path == '/data':
          self.respond(200, {**store.view(), 'token': token})
        elif self.path == '/favicon.ico':
          self.respond(204, b'')
        else:
          parts = self.path.split('/')
          if len(parts) != 3 or not parts[2].isdigit():
            self.respond(404, {'error': 'UNKNOWN_ROUTE'})
            return
          index = int(parts[2])
          image = store.image(index)
          if parts[1] in ('ai', 'model', 'development', 'projection'):
            self.respond(403, {'error': 'NO_BIASING_OUTPUT_INTERFACE'})
          elif parts[1] == 'detector':
            try:
              store.require_comparison()
            except ValueError:
              self.respond(403, {'error': 'ALL_SIXTY_BLIND_FIRST_DECISIONS_AND_FREEZE_REQUIRED'})
              return
            self.respond(409, {'error': 'FROZEN_DETECTOR_INFERENCE_NOT_RUN_SEPARATE_POST_FREEZE_STEP'})
          elif parts[1] == 'annotation':
            self.respond(200, {'first': store.first(index), 'draft': store.load_draft(index), 'image_receipt_sha256': image['receipt_sha256']})
          elif parts[1] == 'image':
            path = h.private_path(store.root / 'images' / (image['sample_id'] + '.png'))
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
              if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('REGULAR_RAW_IMAGE_REQUIRED')
              content = stream.read(64 * 1024 * 1024 + 1)
            if len(content) > 64 * 1024 * 1024 or h.digest(content) != image['image_sha256']:
              raise ValueError('RAW_IMAGE_SHA_MISMATCH')
            self.respond(200, content, 'image/png')
          else:
            self.respond(404, {'error': 'UNKNOWN_ROUTE'})
      except (ValueError, KeyError, OSError, TypeError):
        self.respond(409, {'error': 'LOCAL_EVIDENCE_INTEGRITY_FAILURE'})

    def do_POST(self):
      if not self.allowed() or self.headers.get('X-Review-Token') != token:
        self.respond(403, {'error': 'LOCAL_REVIEW_TOKEN_REQUIRED'})
        return
      try:
        parts = self.path.split('/')
        size = int(self.headers.get('Content-Length', '0'))
        if (len(parts) != 3 or parts[1] not in ('draft', 'save') or not parts[2].isdigit()
            or self.headers.get('Content-Type') != 'application/json' or not 0 < size <= MAX_BODY):
          raise ValueError('BOUNDED_MANUAL_ANNOTATION_REQUEST_REQUIRED')
        body = json.loads(self.rfile.read(size))
        h.c.exact(body, ('image_receipt_sha256', 'annotation'))
        if body['image_receipt_sha256'] != store.image(int(parts[2]))['receipt_sha256']:
          raise ValueError('STALE_UI_FRAME_BINDING')
        value = getattr(store, parts[1])(int(parts[2]), body['annotation'])
        self.respond(200, value)
      except (ValueError, KeyError, OSError, TypeError):
        self.respond(409, {'error': 'INVALID_ANNOTATION_OR_IMMUTABLE_CONFLICT'})

  httpd = ThreadingHTTPServer((bind, port), Handler)
  try:
    yield httpd
  finally:
    httpd.server_close()


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--cache', type=Path, required=True)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  with server(args.cache, port=args.port) as httpd:
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'status': 'BLIND_HUMAN_RAW_IMAGE_ONLY'}), flush=True)
    try:
      input('Press Enter to stop: ')
    finally:
      httpd.shutdown()
      worker.join()


if __name__ == '__main__':
  main()
