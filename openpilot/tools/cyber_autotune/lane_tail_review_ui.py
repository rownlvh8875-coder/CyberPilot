"""Loopback-only public comma10k human review. No private reader or promotion."""

import argparse
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import secrets

import numpy as np
from PIL import Image

from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import lane_public_batch as batch
from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.lane_marking_metrics import category2_mask
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CyberPilot public marking review</title><link rel="stylesheet" href="/style.css"></head>
<body><h1>PUBLIC COMMA10K / NO INDEPENDENT LANE TRUTH</h1>
<p>Paint components are not ego lane identities. Automatic selection reasons are hypotheses.
Real human review is required. No qualification or private input access.</p>
<div><button id="prev">Previous</button><select id="frame"></select><button id="next">Next</button>
<label><input id="gt" type="checkbox" checked>GT paint components</label>
<label><input id="pred" type="checkbox" checked>Detector polylines</label></div>
<p>GT supported: green; unmatched GT: orange. Prediction supported: cyan; unmatched prediction: magenta.
Exact paint-cell support, many-to-many; no inferred association.</p>
<div id="view"><img id="image" alt="Public comma10k frame"><canvas id="overlay"></canvas></div>
<pre id="metrics"></pre><label>Taxonomy <select id="taxonomy"><option value="">Select human label</option></select></label>
<label>Reviewable <select id="reviewable"><option value="yes">yes</option><option value="no">no</option></select></label>
<label>Comment <textarea id="comment" maxlength="2000"></textarea></label>
<label><input id="ack" type="checkbox">I inspected this image, mask and prediction</label>
<button id="save">Save immutable human annotation</button><p id="status"></p>
<script src="/app.js"></script></body></html>"""

CSS = """body{font:15px system-ui;background:#101827;color:#eee;margin:24px}h1{font-size:21px}
button,select,textarea{margin:8px;padding:8px}label{display:inline-block;margin:6px}
#view{position:relative;max-width:1200px}#image{display:block;width:100%}
#overlay{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}
pre{white-space:pre-wrap;background:#182438;padding:16px}textarea{display:block;width:500px;max-width:90vw}"""

JS = """'use strict';
let config, current, index=0, loading=0;
const $=id=>document.getElementById(id);
async function request(path,options){const r=await fetch(path,options);const x=await r.json();if(!r.ok)throw Error(x.error||r.status);return x;}
function draw(){if(!current)return;const [h,w]=current.geometry,c=$('overlay');c.width=w;c.height=h;
 const ctx=c.getContext('2d');ctx.clearRect(0,0,w,h);
 const supportedGT=new Set(current.support_edges.map(e=>e[1]));
 const supportedPred=new Set(current.support_edges.map(e=>e[0]));
 if($('gt').checked){ctx.globalAlpha=.65;current.components.rows.forEach((runs,y)=>runs.forEach(([a,b,id])=>{
 ctx.fillStyle=supportedGT.has(id)?'#5cf080':'#ffad38';ctx.fillRect(a,y,b-a,1);}));}
 ctx.globalAlpha=1;if($('pred').checked)current.lanes.forEach((lane,i)=>{
 ctx.strokeStyle=supportedPred.has(i)?'#00e5ff':'#ff4ff0';ctx.lineWidth=2;ctx.beginPath();
 lane.forEach(([x,y],j)=>j?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.stroke();});}
async function load(i){const target=Math.max(0,Math.min(config.frames.length-1,i));const requestId=++loading;
 $('save').disabled=true;$('ack').checked=false;
 const value=await request('/api/frame/'+target);
 const image=new Image();image.id='image';image.alt='Public comma10k frame';image.src='/image/'+target;
 await image.decode();if(requestId!==loading)return;
 index=target;current=value;$('frame').value=String(index);$('image').replaceWith(image);
 $('view').dataset.frameId=current.frame.frame_id;draw();
 $('metrics').textContent=JSON.stringify({frame:current.frame, same_point_error:current.same_point_error,
 scores:current.scores, saved_annotation:current.annotation},null,2);
 const a=current.annotation;$('taxonomy').value=a?a.reviewer_label:'';$('reviewable').value=a&&!a.reviewable?'no':'yes';
 $('comment').value=a?a.comment:'';$('ack').checked=false;$('save').disabled=!!a;
 $('status').textContent=a?'Immutable annotation already saved':config.scope+' / TAIL_HUMAN_REVIEW_PENDING';}
async function start(){config=await request('/api/config');config.frames.forEach((f,i)=>{
 const o=document.createElement('option');o.value=String(i);o.textContent=f.frame_id+' | '+f.reasons.join(', ');$('frame').append(o);});
 config.labels.forEach(l=>{const o=document.createElement('option');o.value=l;o.textContent=l;$('taxonomy').append(o);});
 $('prev').onclick=()=>load(index-1).catch(showError);$('next').onclick=()=>load(index+1).catch(showError);
 $('frame').onchange=()=>load(Number($('frame').value)).catch(showError);$('gt').onchange=draw;$('pred').onchange=draw;
 $('save').onclick=async()=>{try{if(!$('taxonomy').value||!$('ack').checked)throw Error('Choose label and acknowledge human inspection');
 const x=await request('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
 index,label:$('taxonomy').value,reviewable:$('reviewable').value==='yes',comment:$('comment').value,human_ack:$('ack').checked,token:config.token})});
 await load(index);$('status').textContent='Saved / '+x.review_status.status;}catch(e){showError(e);}};
 await load(0);window.reviewReady=true;}
function showError(e){$('status').textContent='BLOCKED: '+e.message;}
start().catch(showError);
"""


HELPERS = (
  'lane_tail_review_contract.py',
  'lane_public_storage.py',
  'lane_detector_runner.py',
  'lane_tail_diagnostics.py',
  'lane_public_batch.py',
  'lane_marking_metrics.py',
  'lane_public_protocol.py',
  'lane_tail_report.py',
  'native_protocol.py',
  'contracts.py',
  'lane_detector_execution.py',
)


def helper_source_hashes():
  root = Path(__file__).parent
  return {name: digest((root / name).read_bytes()) for name in HELPERS}


def tool_identity():
  return digest(canonical({**helper_source_hashes(), 'lane_tail_review_ui.py': digest(Path(__file__).read_bytes())}))


def require_frozen_metric_sources(run):
  batch.require_active_run_sources(run, batch.durable_source_hashes())
  root = Path(__file__).parent
  names = ('lane_detector_runner.py', 'lane_detector_execution.py', 'lane_public_protocol.py', 'lane_marking_metrics.py', 'native_protocol.py', 'contracts.py')
  actual = digest(canonical({name: digest((root / name).read_bytes()) for name in names}))
  if actual != run['environment']['diagnostic_source_sha256']:
    raise ValueError('FROZEN_DIAGNOSTIC_OVERLAY_SOURCE_MISMATCH')


class ReviewSession:
  def __init__(self, manifest, loader, output):
    c.validate_manifest(manifest)
    if manifest['review_tool_sha256'] != tool_identity():
      raise ValueError('ACTIVE_REVIEW_TOOL_IDENTITY_MISMATCH')
    self.manifest, self.loader, self.output = manifest, loader, Path(output)
    self.token = secrets.token_hex(32)
    storage.durable_mkdir(self.output / 'annotations')
    freeze = self.output / 'review-freeze.json'
    with storage.writer_lease(self.output):
      if freeze.exists():
        if storage.read_json(freeze) != manifest:
          raise ValueError('IMMUTABLE_REVIEW_MANIFEST_REQUIRED')
      else:
        if any((self.output / 'annotations').iterdir()):
          raise ValueError('UNBOUND_ANNOTATIONS_FORBIDDEN')
        storage.atomic_json(freeze, manifest)
    with storage.writer_lease(self.output):
      rows = self.annotations()
      # Publish recovered row-before-index orphans under the same writer lease.
      # Later deletion must remain detectable after this successful recovery.
      self.write_index(rows)

  def write_index(self, rows):
    storage.atomic_json(
      self.output / 'review-index.json',
      seal(
        {'manifest_sha256': self.manifest['receipt_sha256'], 'rows': [a['receipt_sha256'] for a in rows], 'review_status': c.review_status(self.manifest, rows)}
      ),
    )

  def annotations(self):
    result = []
    for path in sorted((self.output / 'annotations').iterdir()):
      if path.name.startswith('.') and path.name.endswith('.tmp'):
        continue
      value = storage.read_json(path)
      c.validate_annotation(self.manifest, value)
      ordinal = next(i for i, f in enumerate(self.manifest['frames']) if f['frame_id'] == value['frame_id'])
      if path.name != f'{ordinal:05d}.json':
        raise ValueError('NONCANONICAL_ANNOTATION_FILENAME')
      result.append(value)
    c.review_status(self.manifest, result)
    path = self.output / 'review-index.json'
    if path.exists():
      indexed = unseal(storage.read_json(path))
      if (
        set(indexed) != {'manifest_sha256', 'rows', 'review_status'}
        or indexed['manifest_sha256'] != self.manifest['receipt_sha256']
        or type(indexed['rows']) is not list
        or len(set(indexed['rows'])) != len(indexed['rows'])
        or not set(indexed['rows']).issubset({row['receipt_sha256'] for row in result})
      ):
        raise ValueError('MISSING_OR_CORRUPT_INDEXED_HUMAN_ANNOTATION')
      prior = [row for row in result if row['receipt_sha256'] in indexed['rows']]
      if indexed['review_status'] != c.review_status(self.manifest, prior):
        raise ValueError('HUMAN_REVIEW_INDEX_STATE_MISMATCH')
    elif result:
      raise ValueError('ANNOTATION_INDEX_MISSING')
    return result

  def frame(self, ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < len(self.manifest['frames']):
      raise ValueError('UNKNOWN_REVIEW_FRAME')
    if self.manifest['review_tool_sha256'] != tool_identity():
      raise ValueError('ACTIVE_REVIEW_TOOL_IDENTITY_DRIFT')
    frame = self.manifest['frames'][ordinal]
    value = self.loader(frame)
    if type(value) is not dict or set(value) != {'png', 'data'} or digest(value['png']) != frame['image_sha256'] or value['data'].get('frame') != frame:
      raise ValueError('PUBLIC_REVIEW_FRAME_BINDING_MISMATCH')
    value['data']['annotation'] = next((a for a in self.annotations() if a['frame_id'] == frame['frame_id']), None)
    return value

  def save(self, body):
    if type(body) is not dict or set(body) != {'index', 'label', 'reviewable', 'comment', 'human_ack', 'token'} or body['token'] != self.token:
      raise ValueError('EXACT_AUTHORIZED_REVIEW_SAVE_REQUIRED')
    frame = self.frame(body['index'])['data']['frame']
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    row = c.make_annotation(
      self.manifest,
      frame['frame_id'],
      label=body['label'],
      reviewable=body['reviewable'],
      comment=body['comment'],
      timestamp=timestamp,
      human_ack=body['human_ack'],
      tool_sha256=tool_identity(),
    )
    with storage.writer_lease(self.output):
      existing = self.annotations()
      path = self.output / 'annotations' / f"{body['index']:05d}.json"
      if path.exists():
        raise FileExistsError('HUMAN_ANNOTATION_IS_IMMUTABLE')
      storage.atomic_json(path, row)
      status = c.review_status(self.manifest, [*existing, row])
      self.write_index(self.annotations())
      return {'annotation': row, 'review_status': status}


def make_server(session, *, host='127.0.0.1', port=0):
  if host != '127.0.0.1' or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_ONLY_REVIEW_SERVER_REQUIRED')

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def origin(self):
      return 'http://127.0.0.1:' + str(self.server.server_port)

    def authorized(self, post=False):
      return (
        self.client_address[0] == '127.0.0.1' and self.headers.get('Host') == self.origin()[7:] and (not post or self.headers.get('Origin') == self.origin())
      )

    def reply(self, code, body, mime='application/json'):
      data = canonical(body) if mime == 'application/json' else body if isinstance(body, bytes) else body.encode()
      self.send_response(code)
      self.send_header('Content-Type', mime)
      self.send_header('Content-Length', str(len(data)))
      self.send_header(
        'Content-Security-Policy',
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; "
        + "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
      )
      self.send_header('X-Content-Type-Options', 'nosniff')
      self.send_header('Cache-Control', 'no-store')
      self.end_headers()
      self.wfile.write(data)

    def ordinal(self, prefix):
      suffix = self.path[len(prefix) :]
      if not suffix.isascii() or not suffix.isdigit() or str(int(suffix)) != suffix:
        raise ValueError('CANONICAL_FRAME_INDEX_REQUIRED')
      return int(suffix)

    def do_GET(self):
      if not self.authorized():
        self.reply(403, {'error': 'LOOPBACK_HOST_REQUIRED'})
        return
      try:
        if self.path == '/':
          self.reply(200, HTML, 'text/html; charset=utf-8')
        elif self.path == '/app.js':
          self.reply(200, JS, 'text/javascript; charset=utf-8')
        elif self.path == '/style.css':
          self.reply(200, CSS, 'text/css; charset=utf-8')
        elif self.path == '/favicon.ico':
          self.reply(204, b'', 'image/x-icon')
        elif self.path == '/api/config':
          self.reply(
            200,
            {
              'frames': session.manifest['frames'],
              'scope': session.manifest['scope'],
              'labels': list(c.LABELS),
              'token': session.token,
              'review_status': c.review_status(session.manifest, session.annotations()),
            },
          )
        elif self.path.startswith('/api/frame/'):
          self.reply(200, session.frame(self.ordinal('/api/frame/'))['data'])
        elif self.path.startswith('/image/'):
          self.reply(200, session.frame(self.ordinal('/image/'))['png'], 'image/png')
        else:
          self.reply(404, {'error': 'UNKNOWN_LOCAL_REVIEW_ENDPOINT'})
      except (ValueError, KeyError, TypeError, IndexError) as exc:
        self.reply(400, {'error': str(exc)})

    def do_POST(self):
      if not self.authorized(post=True):
        self.reply(403, {'error': 'SAME_ORIGIN_REQUIRED'})
        return
      if self.path != '/api/save':
        self.reply(404, {'error': 'UNKNOWN_LOCAL_REVIEW_ENDPOINT'})
        return
      try:
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 16384 or self.headers.get('Content-Type') != 'application/json':
          raise ValueError('BOUNDED_JSON_BODY_REQUIRED')
        body = json.loads(self.rfile.read(length))
        if type(body) is not dict:
          raise ValueError('JSON_OBJECT_REQUIRED')
        if body.get('token') != session.token:
          self.reply(403, {'error': 'REVIEW_NONCE_REQUIRED'})
          return
        self.reply(200, session.save(body))
      except FileExistsError as exc:
        self.reply(409, {'error': str(exc)})
      except (ValueError, KeyError, TypeError, IndexError) as exc:
        self.reply(400, {'error': str(exc)})

  return HTTPServer((host, port), Handler)


def open_public_review(run_dir, cache, review_manifest, output):
  """Verify full store before exposing only selected public frames."""
  cache, output, run_dir = (batch.require_persistent_path(v) for v in (cache, output, run_dir))
  if any(v.is_relative_to(Path(__file__).resolve().parents[3]) for v in (cache, output)):
    raise ValueError('RAW_CACHE_AND_ANNOTATIONS_MUST_STAY_EXTERNAL')
  run = storage.read_json(run_dir / 'run-freeze.json')
  require_frozen_metric_sources(run)
  protocol = storage.read_json(cache.parent / 'full-protocol.json')
  inputs = storage.read_json(cache.parent / 'full-input-manifest.json')
  if (
    digest((cache.parent / 'full-protocol.json').read_bytes()) != run['protocol_file_sha256']
    or digest((cache.parent / 'full-input-manifest.json').read_bytes()) != run['manifest_file_sha256']
  ):
    raise ValueError('PUBLIC_REVIEW_INPUT_MANIFEST_MISMATCH')
  r.validate_protocol_pairs(protocol, inputs)
  pairs = protocol['pairs']
  identities = {f['path']: f for f in inputs['files']}

  def validator(row):
    return batch.verify_resume(row, run['receipt_sha256'], row['ordinal'], pairs[row['ordinal']], identities)

  durable = storage.DurableRun(run_dir, run, [p['image'] for p in pairs])
  marker = durable.verify_completed(validator)
  ledger = storage.read_json(run_dir / 'ledger.json')
  expected = c.freeze_review(ledger, marker, c.selection_policy(), tool_identity())
  if expected != review_manifest:
    raise ValueError('FROZEN_HUMAN_REVIEW_SELECTION_MISMATCH')
  by_id = {p['image']: i for i, p in enumerate(pairs)}

  def loader(frame):
    require_frozen_metric_sources(run)
    ordinal = by_id[frame['frame_id']]
    pair = pairs[ordinal]
    files = r.verify_inputs(cache, {**inputs, 'files': [identities[pair['image']], identities[pair['mask']]]})
    core = batch.verify_resume(storage.read_json(durable.row_path(ordinal)), run['receipt_sha256'], ordinal, pair, identities)
    entry = core['ledger']
    record = core['detector_record']
    if entry['receipt_sha256'] != frame['metric_result_sha256'] or digest(canonical(record)) != frame['prediction_sha256']:
      raise ValueError('REVIEW_METRIC_OR_PREDICTION_DRIFT')
    mask = category2_mask(np.asarray(Image.open(io.BytesIO(files[pair['mask']])).convert('RGB')))
    observed = [(lane, score) for lane, score in zip(record['lanes'], record['scores'], strict=True) if lane]
    return {
      'png': files[pair['image']],
      'data': {
        'frame': frame,
        'geometry': record['image_geometry'],
        'lanes': [lane for lane, _ in observed],
        'scores': [score for _, score in observed],
        'components': t.paint_components(mask),
        'support_edges': entry['support_edges'],
        'same_point_error': t.distribution(core['pool']['paired_spatial_pred']),
      },
    }

  return ReviewSession(review_manifest, loader, output)


def main():
  parser = argparse.ArgumentParser()
  for name in ('run', 'cache', 'manifest', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  session = open_public_review(args.run, args.cache, storage.read_json(args.manifest), args.output)
  server = make_server(session, port=args.port)
  print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port), 'status': 'TAIL_HUMAN_REVIEW_PENDING'}), flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
