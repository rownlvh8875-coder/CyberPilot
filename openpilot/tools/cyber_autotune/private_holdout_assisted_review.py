"""Local-only assisted verification; never writes the original blind store."""
import argparse
from contextlib import contextmanager
import json
import os
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading

from openpilot.tools.cyber_autotune import private_holdout_assisted as a
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_annotation as original
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import private_pixel_executor as encoded

HTML = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>Assisted lane verification</title>
<style>body{background:#101925;color:#eef4fa;font:16px system-ui;margin:16px}button,select,input{font:inherit;padding:7px;margin:3px}
canvas{background:#253044;max-width:100%;touch-action:none}.warn{color:#ffc57e}pre{white-space:pre-wrap}button:disabled{opacity:.4}</style>
<h1>AI-ASSISTED HUMAN PIXEL REFERENCE</h1>
<p class="warn">LOCAL PRIVATE ONLY · NOT BLIND · NON-QUALIFYING · NO INDEPENDENT GROUND TRUTH / METERS</p>
<p>AI 초안은 오류가 있을 수 있습니다. 실제로 보이는 현재 주행 차선의 경계만 직접 확인하세요.
안 보이는 구간은 연장하지 마세요. 불확실하면 AMBIGUOUS로 남기세요. 이전 blind 기록은 별도로 보존됩니다.</p>
<button id="prev">Previous [←]</button><select id="frames"></select><button id="next">Next [→]</button>
<button id="jump">Unverified [J]</button><span id="progress"></span>
<p><input id="reviewer" placeholder="Opaque reviewer ID"><select id="action"><option value="">직접 결정</option>
<option>ACCEPT_AI</option><option>MODIFY_AI</option><option>REJECT_AI</option><option>AMBIGUOUS</option></select>
<select id="state"></select></p>
<p><label><input type="radio" name="side" value="left" checked>Left [L]</label>
<label><input type="radio" name="side" value="right">Right [R]</label>
<select id="mode"><option value="add">Add point</option><option value="move">Move point</option><option value="delete">Delete point</option>
<option value="pan">Pan</option></select><button id="undo">Undo [U]</button><button id="clear-left">Clear left</button>
<button id="clear-right">Clear right</button><label>Zoom <input id="zoom" type="range" min=".5" max="6" step=".1" value="1"></label></p>
<canvas id="canvas" width="1100" height="680"></canvas><pre id="ai-info"></pre><pre id="points"></pre>
<p><input id="comment" maxlength="1000" placeholder="Optional comment">
<label><input id="ack" type="checkbox">I personally verified the AI-assisted pixels; this is NOT blind evidence.</label></p>
<button id="draft">Save editable draft</button><button id="save">Save immutable human verification</button>
<button id="comparison" disabled>Reveal frozen detector after human save</button><pre id="status"></pre>
<script>
const q=s=>document.querySelector(s),canvas=q('#canvas'),ctx=canvas.getContext('2d');
let data,index=0,loaded=-1,generation=0,image,body,ai,locked=false,saving=false,scale=1,ox=0,oy=0,drag=null,history=[],comparison=null;
const states=['BOTH_EGO_BOUNDARIES_VISIBLE','LEFT_ONLY_VISIBLE','RIGHT_ONLY_VISIBLE','EGO_BOUNDARIES_AMBIGUOUS',
'INTERSECTION_OR_MERGE','NO_CLEAR_LANE_MARKINGS','UNREVIEWABLE'];
states.forEach(s=>{const o=document.createElement('option');o.textContent=s;q('#state').append(o);});
function error(e){q('#status').textContent=e.message;}
async function req(path,payload){const opts=payload===undefined?{}:{method:'POST',
headers:{'Content-Type':'application/json','X-Review-Token':data.token},body:JSON.stringify(payload)};
const r=await fetch(path,opts),value=await r.json();if(!r.ok)throw new Error(value.error);return value;}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);if(!image)return;ctx.save();ctx.translate(ox,oy);ctx.scale(scale,scale);
ctx.drawImage(image,0,0);['left','right'].forEach((s,i)=>{ctx.strokeStyle=i?'#ffcf62':'#5be6df';ctx.fillStyle=ctx.strokeStyle;
ctx.lineWidth=2/scale;ctx.beginPath();body[s].forEach(([x,y],n)=>{if(n)ctx.lineTo(x,y);else ctx.moveTo(x,y);});ctx.stroke();
body[s].forEach(([x,y])=>{ctx.beginPath();ctx.arc(x,y,4/scale,0,Math.PI*2);ctx.fill();});});
if(comparison&&locked){ctx.strokeStyle='#fa69dc';ctx.setLineDash([5/scale,4/scale]);
comparison.prediction.lanes.forEach(l=>{ctx.beginPath();l.points.forEach(([x,y],n)=>{if(n)ctx.lineTo(x,y);else ctx.moveTo(x,y);});ctx.stroke();});}
ctx.restore();q('#points').textContent=JSON.stringify({units:'ORIGINAL IMAGE PIXELS',width:image.naturalWidth,height:image.naturalHeight,
left:body.left,right:body.right},null,2);}
function form(){if(loaded!==index||!image||locked)throw new Error('Bound image required; saved decisions immutable');
return {action:q('#action').value,state:q('#state').value,left:body.left,right:body.right,reviewer_id:q('#reviewer').value,
acknowledged_assisted:q('#ack').checked,comment:q('#comment').value};}
async function refresh(){data=await req('/data');q('#progress').textContent='AI '+data.progress.ai_generated+'/60 · Human '+
data.progress.human_verified+'/60 · '+data.progress.status;}
async function show(){const stamp=++generation;loaded=-1;image=null;comparison=null;drag=null;history=[];saving=false;
q('#comparison').disabled=true;['save','draft','undo','clear-left','clear-right','state','action','ack','reviewer','comment','mode'].forEach(id=>q('#'+id).disabled=true);
ctx.clearRect(0,0,canvas.width,canvas.height);q('#frames').value=index;q('#ai-info').textContent='Loading bound raw image / AI draft';
q('#status').textContent='';const v=await req('/annotation/'+index);if(stamp!==generation)return;ai=v.ai;locked=!!v.first;
if(!ai){q('#ai-info').textContent='AI draft unavailable; no invented annotation';return;}
body=structuredClone(v.first||v.draft||{left:ai.left,right:ai.right,state:ai.state,action:'',reviewer_id:q('#reviewer').value,
acknowledged_assisted:false,comment:''});
q('#state').value=body.state;q('#action').value=body.action;q('#ack').checked=body.acknowledged_assisted;
q('#reviewer').value=body.reviewer_id;q('#comment').value=body.comment;
q('#ai-info').textContent='AI DRAFT · '+ai.confidence+' · '+ai.reason+' · NOT HUMAN VERIFIED';
scale=1;ox=oy=0;q('#zoom').value=1;const img=new Image();img.onload=()=>{if(stamp!==generation)return;image=img;loaded=index;
['save','draft','undo','clear-left','clear-right','state','action','ack','reviewer','comment','mode'].forEach(id=>q('#'+id).disabled=locked);
q('#comparison').disabled=!locked;q('#status').textContent=locked?'IMMUTABLE ASSISTED HUMAN DECISION':'VERIFY AI DRAFT PERSONALLY';draw();};
img.onerror=()=>error(new Error('Raw image binding/load failure'));img.src='/image/'+index;}
function side(){return q('input[name=side]:checked').value;}
function pos(e){const r=canvas.getBoundingClientRect();return [(e.clientX-r.left)*canvas.width/r.width,(e.clientY-r.top)*canvas.height/r.height];}
function point(e){const [x,y]=pos(e);return [(x-ox)/scale,(y-oy)/scale];}
function checkpoint(){history.push(structuredClone({left:body.left,right:body.right}));q('#action').value='MODIFY_AI';}
function bounded([x,y]){return x>=0&&y>=0&&x<=image.naturalWidth-1&&y<=image.naturalHeight-1;}
function sort(){body[side()].sort((a,b)=>b[1]-a[1]);}
canvas.oncontextmenu=e=>e.preventDefault();
canvas.onpointerdown=e=>{if(!image||loaded!==index)return;const [sx,sy]=pos(e);
if(e.shiftKey||e.button===2||q('#mode').value==='pan'){drag={pan:true,sx,sy,ox,oy};canvas.setPointerCapture(e.pointerId);return;}
if(locked||saving)return;const p=point(e);if(!bounded(p))return;const pts=body[side()],mode=q('#mode').value;
if(mode==='add'){if(pts.length>=12)return;checkpoint();pts.push(p);sort();draw();return;}
let n=-1,d=12/scale;pts.forEach((v,i)=>{const dist=Math.hypot(v[0]-p[0],v[1]-p[1]);if(dist<d){d=dist;n=i;}});
if(n<0)return;checkpoint();if(mode==='delete'){pts.splice(n,1);draw();}else{drag={pan:false,n,side:side()};canvas.setPointerCapture(e.pointerId);}};
canvas.onpointermove=e=>{if(!drag)return;if(drag.pan){const [x,y]=pos(e);ox=drag.ox+x-drag.sx;oy=drag.oy+y-drag.sy;}
else{const p=point(e);if(bounded(p))body[drag.side][drag.n]=p;}draw();};
canvas.onpointerup=()=>{if(drag&&!drag.pan)body[drag.side].sort((a,b)=>b[1]-a[1]);drag=null;draw();};
q('#undo').onclick=()=>{if(!locked&&!saving&&history.length){Object.assign(body,history.pop());draw();}};
['left','right'].forEach(s=>q('#clear-'+s).onclick=()=>{if(!locked&&!saving){checkpoint();body[s]=[];draw();}});
q('#zoom').oninput=()=>{const z=Number(q('#zoom').value),cx=canvas.width/2,cy=canvas.height/2;ox=cx-(cx-ox)*z/scale;oy=cy-(cy-oy)*z/scale;scale=z;draw();};
q('#action').onchange=()=>{const action=q('#action').value;if(['REJECT_AI','AMBIGUOUS'].includes(action)){
checkpoint();body.left=[];body.right=[];q('#state').value='EGO_BOUNDARIES_AMBIGUOUS';q('#action').value=action;draw();}};
q('#prev').onclick=()=>{index=(index+59)%60;show().catch(error);};q('#next').onclick=()=>{index=(index+1)%60;show().catch(error);};
q('#frames').onchange=()=>{index=Number(q('#frames').value);show().catch(error);};
q('#jump').onclick=()=>{const i=data.frames.findIndex(v=>!v.reviewed);if(i>=0){index=i;show().catch(error);}};
['draft','save'].forEach(action=>q('#'+action).onclick=async()=>{const stamp=generation,ordinal=loaded;
try{const payload={image_receipt_sha256:ai.image_receipt_sha256,annotation:form()};
saving=true;drag=null;
['save','draft','undo','clear-left','clear-right','state','action','ack','reviewer','comment','mode'].forEach(id=>q('#'+id).disabled=true);
await req('/'+action+'/'+ordinal,payload);await refresh();
if(stamp===generation&&ordinal===loaded)await show();}catch(e){if(stamp===generation)error(e);}
finally{if(stamp===generation&&!locked&&loaded===index){saving=false;
['save','draft','undo','clear-left','clear-right','state','action','ack','reviewer','comment','mode'].forEach(id=>q('#'+id).disabled=false);}}});
q('#comparison').onclick=async()=>{const stamp=generation,ordinal=loaded;try{const value=await req('/detector/'+ordinal);
if(stamp!==generation||ordinal!==loaded||!locked)return;comparison=value;
q('#status').textContent='FROZEN DETECTOR COMPARISON · NOT QUALIFICATION';draw();}catch(e){if(stamp===generation)error(e);}};
document.onkeydown=e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;
const k=e.key.toLowerCase();if(k==='l'||k==='r')q('input[name=side][value='+(k==='l'?'left':'right')+']').checked=true;
const map={arrowleft:'prev',arrowright:'next',u:'undo',j:'jump'};if(map[k]){e.preventDefault();q('#'+map[k]).click();}};
refresh().then(()=>{data.frames.forEach((v,i)=>{const o=document.createElement('option');o.value=i;
o.textContent='Frame '+(i+1);q('#frames').append(o);});return show();}).catch(error);
</script></html>"""


class Store:
  def __init__(self, raw, output, detector=None):
    self.raw, self.output = p.private_directories(raw, output)
    self.package = h.read(self.raw / 'materialization.json')
    self.auth = h.read(self.output / 'authorization.json')
    a.require_auth(self.package, self.auth)
    self.detector = h.private_path(detector) if detector else None
    self.progress()

  def image(self, ordinal):
    return hidden.image(self.package, ordinal)

  def path(self, kind, ordinal):
    return self.output / kind / (self.image(ordinal)['sample_id'] + '.json')

  def ai(self, ordinal):
    path = self.path('ai', ordinal)
    if not path.exists():
      return None
    row = h.read(path)
    a.validate_ai(self.package, self.auth, ordinal, row)
    return row

  def first(self, ordinal):
    path = self.path('human', ordinal)
    if not path.exists():
      return None
    row = h.read(path)
    ai = self.ai(ordinal)
    if ai is None:
      raise ValueError('AI_DRAFT_REQUIRED')
    a.validate_human(self.package, self.auth, ordinal, ai, row)
    return row

  def progress(self):
    expected = {im['sample_id'] + '.json' for im in self.package['images']}
    for kind in ('ai', 'human', 'drafts'):
      directory = h.private_path(self.output / kind)
      if directory.exists() and {p.name for p in directory.glob('*.json')} - expected:
        raise ValueError('UNKNOWN_OR_DUPLICATE_ASSISTED_ROW')
    ai = [self.ai(i) for i in range(h.EXPECTED)]
    human = [self.first(i) for i in range(h.EXPECTED)]
    count = sum(r is not None for r in human)
    return {'ai_generated': sum(r is not None for r in ai), 'human_verified': count,
            'total': h.EXPECTED, 'status': 'ASSISTED_HUMAN_COMPLETE' if count == h.EXPECTED else 'ASSISTED_HUMAN_VERIFICATION_PENDING',
            'action_counts': {key: sum(r is not None and r['action'] == key for r in human) for key in a.ACTIONS},
            'state_counts': {key: sum(r is not None and r['state'] == key for r in human) for key in h.STATES}}

  def view(self, ordinal):
    path = self.path('drafts', ordinal)
    draft = h.read(path) if path.exists() else None
    if draft:
      h.unseal(draft)
      if draft['image_receipt_sha256'] != self.image(ordinal)['receipt_sha256']:
        raise ValueError('STALE_DRAFT')
    return {'ai': self.ai(ordinal), 'first': self.first(ordinal), 'draft': draft['body'] if draft else None}

  def draft(self, ordinal, body):
    ai = self.ai(ordinal)
    if ai is None:
      raise ValueError('AI_REQUIRED')
    h.c.exact(body, ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment'))
    for side in ('left', 'right'):
      h.validate_points(body[side], ai['width'], ai['height'], draft=True)
    with storage.writer_lease(self.output):
      if self.first(ordinal):
        raise ValueError('IMMUTABLE_ASSISTED_FIRST')
      storage.atomic_json(self.path('drafts', ordinal),
                          h.seal({'schema': 'PRIVATE_ASSISTED_EDITABLE_DRAFT_V1', 'body': body,
                                  'image_receipt_sha256': self.image(ordinal)['receipt_sha256']}))
    return {'status': 'EDITABLE_NOT_HUMAN_VERIFIED'}

  def save(self, ordinal, body):
    ai = self.ai(ordinal)
    if ai is None:
      raise ValueError('AI_REQUIRED')
    with storage.writer_lease(self.output):
      existing = self.first(ordinal)
      if existing:
        if any(existing[k] != body[k] for k in body) or set(body) != {'action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment'}:
          raise ValueError('IMMUTABLE_ASSISTED_FIRST')
        return existing
      row = a.human_row(self.package, self.auth, ordinal, ai, body, encoded.utc())
      h.write_immutable(self.path('human', ordinal), row)
    return row

  def reference(self):
    self.progress()
    rows = [self.first(i) for i in range(h.EXPECTED)]
    if any(r is None for r in rows):
      raise ValueError('ALL_SIXTY_EXPLICIT_ASSISTED_HUMANS_REQUIRED')
    with storage.writer_lease(self.output):
      path = self.output / 'human-assisted-reference.json'
      if not path.exists():
        h.write_immutable(path, a.freeze(self.package, self.auth, [self.ai(i) for i in range(h.EXPECTED)], rows, encoded.utc()))
      row = h.read(path)
      expected = a.freeze(self.package, self.auth, [self.ai(i) for i in range(h.EXPECTED)], rows, row['frozen_at'])
      if h.canonical(row) != h.canonical(expected):
        raise ValueError('ASSISTED_SET_FREEZE_MISMATCH')
    return row

  def comparison(self, ordinal):
    if self.first(ordinal) is None:
      raise PermissionError('ASSISTED_HUMAN_FIRST_REQUIRED')
    if self.detector is None:
      raise ValueError('FROZEN_DETECTOR_CACHE_UNAVAILABLE')
    auth = h.read(self.detector / 'authorization.json')
    row = h.read(self.detector / 'rows' / (self.image(ordinal)['sample_id'] + '.json'))
    hidden.validate_detector_row(self.package, auth, ordinal, row)
    return row


@contextmanager
def server(raw, output, detector=None, *, bind='127.0.0.1', port=0):
  if bind != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY')
  store = Store(raw, output, detector)
  token = secrets.token_hex(32)

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def allowed(self):
      host = f'127.0.0.1:{self.server.server_port}'
      return self.headers.get('Host') == host and self.headers.get('Origin', 'http://' + host) == 'http://' + host

    def respond(self, status, value, kind='application/json'):
      data = value if isinstance(value, bytes) else h.canonical(value)
      self.send_response(status)
      for key, val in (('Content-Type', kind), ('Content-Length', str(len(data))),
                       ('Content-Security-Policy', original.CSP), ('Cache-Control', 'no-store'),
                       ('X-Content-Type-Options', 'nosniff')):
        self.send_header(key, val)
      self.end_headers()
      self.wfile.write(data)

    def do_GET(self):
      if not self.allowed():
        self.respond(403, {'error': 'LOCAL_ORIGIN_REQUIRED'})
        return
      try:
        if self.path == '/':
          self.respond(200, HTML.encode(), 'text/html; charset=utf-8')
        elif self.path == '/data':
          self.respond(200, {'token': token, 'progress': store.progress(),
                            'frames': [{'reviewed': store.first(i) is not None} for i in range(h.EXPECTED)]})
        elif self.path == '/favicon.ico':
          self.respond(204, b'')
        else:
          parts = self.path.split('/')
          if len(parts) != 3 or not parts[2].isdigit():
            self.respond(404, {'error': 'UNKNOWN_ROUTE'})
            return
          ordinal = int(parts[2])
          store.image(ordinal)
          if parts[1] == 'image':
            im = store.image(ordinal)
            path = h.private_path(store.raw / 'images' / (im['sample_id'] + '.png'))
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
              if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('REGULAR_RAW_IMAGE_REQUIRED')
              content = stream.read(64 * 1024 * 1024 + 1)
            if len(content) > 64 * 1024 * 1024 or h.digest(content) != im['image_sha256']:
              raise ValueError('RAW_IMAGE_SHA_MISMATCH')
            self.respond(200, content, 'image/png')
          elif parts[1] == 'annotation':
            self.respond(200, store.view(ordinal))
          elif parts[1] == 'detector':
            self.respond(200, store.comparison(ordinal))
          else:
            self.respond(403, {'error': 'NO_MODEL_CANDIDATE_OR_BLIND_INTERFACE'})
      except PermissionError:
        self.respond(403, {'error': 'EXPLICIT_ASSISTED_HUMAN_FIRST_REQUIRED'})
      except (ValueError, KeyError, TypeError, OSError):
        self.respond(409, {'error': 'ASSISTED_EVIDENCE_INTEGRITY_FAILURE'})

    def do_POST(self):
      if not self.allowed() or self.headers.get('X-Review-Token') != token:
        self.respond(403, {'error': 'LOCAL_REVIEW_TOKEN_REQUIRED'})
        return
      try:
        parts = self.path.split('/')
        size = int(self.headers.get('Content-Length', '0'))
        if (len(parts) != 3 or parts[1] not in ('draft', 'save') or not parts[2].isdigit()
            or self.headers.get('Content-Type') != 'application/json' or not 0 < size <= original.MAX_BODY):
          raise ValueError('BOUNDED_ASSISTED_REQUEST_REQUIRED')
        payload = json.loads(self.rfile.read(size))
        h.c.exact(payload, ('image_receipt_sha256', 'annotation'))
        ordinal = int(parts[2])
        if payload['image_receipt_sha256'] != store.image(ordinal)['receipt_sha256']:
          raise ValueError('STALE_IMAGE')
        self.respond(200, getattr(store, parts[1])(ordinal, payload['annotation']))
      except (ValueError, KeyError, TypeError, OSError):
        self.respond(409, {'error': 'INVALID_ASSISTED_INPUT_OR_IMMUTABLE_CONFLICT'})
  httpd = ThreadingHTTPServer((bind, port), Handler)
  try:
    yield httpd
  finally:
    httpd.server_close()

def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--raw-cache', type=Path, required=True)
  parser.add_argument('--assisted-cache', type=Path, required=True)
  parser.add_argument('--detector-cache', type=Path)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  with server(args.raw_cache, args.assisted_cache, args.detector_cache, port=args.port) as httpd:
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'status': 'AI_ASSISTED_NOT_BLIND'}), flush=True)
    try:
      input('Press Enter to stop: ')
    finally:
      httpd.shutdown()
      worker.join()


if __name__ == '__main__':
  main()
