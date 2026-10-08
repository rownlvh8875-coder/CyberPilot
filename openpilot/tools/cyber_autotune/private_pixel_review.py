"""Loopback read-only private development viewer; holdout opening stays closed.

No annotation creation, inference, selection, model output, projection truth,
upload or promotion interface. This viewer does not satisfy human validation.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import argparse

from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Private pixel diagnostic</title>
<style>body{font:16px system-ui;background:#101825;color:#edf3f9;margin:24px;max-width:1100px}
button,select{font:inherit;margin:6px;padding:7px}canvas{max-width:100%;background:#273349}
.warn{color:#ffc469}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>
<h1>PRIVATE PIXEL DIAGNOSTIC ONLY</h1>
<p class="warn">NO PRIVATE GROUND TRUTH · NOT QUALIFICATION · NO SEALED REFERENCE</p>
<p>Frozen development predictions. Holdout remains independent and unopened.</p>
<button id="prev">Previous</button><select id="frames" aria-label="Frame selector"></select><button id="next">Next</button>
<label><input id="overlay" type="checkbox" checked>Detector overlay</label>
<canvas id="canvas"></canvas><p id="state"></p><pre id="details"></pre>
<h2>Future human holdout</h2><p>HOLDOUT NOT OPENED · PRIVATE_HUMAN_HOLDOUT_PENDING</p>
<p>Original-image blind-first annotation requires a separate materialization authorization.
No modelV2/candidate overlay. No labels are created by this tool.</p>
<ul><li>CLEAR_TWO_BOUNDARIES</li><li>ONE_BOUNDARY_VISIBLE</li><li>MARKING_AMBIGUOUS</li>
<li>INTERSECTION_MERGE</li><li>DETECTOR_MISS_SUSPECTED</li><li>DETECTOR_FALSE_POSITIVE_SUSPECTED</li><li>UNREVIEWABLE</li></ul>
<script>
let index=0,data,image,record;const select=document.querySelector('#frames'),canvas=document.querySelector('#canvas');
const context=canvas.getContext('2d');let generation=0;
function draw(){context.clearRect(0,0,canvas.width,canvas.height);if(!image)return;
context.drawImage(image,0,0);if(!document.querySelector('#overlay').checked)return;
const colors=['#ffce38','#24e6da','#ff65af','#b6ff74'];record.prediction.lanes.forEach((lane,i)=>{
 context.fillStyle=colors[i%colors.length];lane.points.forEach(([x,y])=>context.fillRect(x-1,y-1,2,2));});}
async function show(){const stamp=++generation;image=null;record=null;context.clearRect(0,0,canvas.width,canvas.height);
select.value=String(index);const frame=data.frames[index];
document.querySelector('#state').textContent=(index+1)+' / '+data.frames.length+' · '+frame.role+' · '+frame.status;
document.querySelector('#details').textContent=JSON.stringify(frame,null,2);
if(frame.role==='HOLDOUT'||frame.status==='NOT_RUN'){document.querySelector('#state').textContent+=' · NOT MATERIALIZED';return;}
const response=await fetch('/frame/'+index);if(!response.ok)throw new Error('Local frame unavailable');
const value=await response.json();if(stamp!==generation)return;record=value;
document.querySelector('#details').textContent=JSON.stringify(value.summary,null,2);
const loaded=new Image();loaded.onload=()=>{if(stamp!==generation)return;image=loaded;canvas.width=loaded.width;canvas.height=loaded.height;draw();};
loaded.onerror=()=>{document.querySelector('#state').textContent='Local image unavailable';};loaded.src='/image/'+index;}
document.querySelector('#overlay').onchange=draw;
select.onchange=()=>{index=Number(select.value);show().catch(report);};
document.querySelector('#prev').onclick=()=>{index=(index+data.frames.length-1)%data.frames.length;show().catch(report);};
document.querySelector('#next').onclick=()=>{index=(index+1)%data.frames.length;show().catch(report);};
function report(error){document.querySelector('#state').textContent=error.message;}
fetch('/data').then(r=>r.json()).then(value=>{data=value;value.frames.forEach((f,i)=>{
const option=document.createElement('option');option.value=i;option.textContent=(i+1)+' '+f.role+' '+f.sample_id.slice(0,12);
select.appendChild(option);});return show();}).catch(report);
</script></html>"""

CSP = "default-src 'none'; img-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"


def view_model(root):
  manifest, auth = [storage.read_json(root / name) for name in ('manifest.json', 'authorization.json')]
  p.require_execution(manifest, auth)
  rows = {}
  directory = root / 'receipts/rows'
  if directory.exists():
    for path in sorted(directory.glob('*.json')):
      row = storage.read_json(path)
      p.validate_frame(row, manifest, auth)
      if row['sample_id'] in rows:
        raise ValueError('DUPLICATE_VIEWER_FRAME')
      rows[row['sample_id']] = row
  frames = [{'sample_id': row['sample_id'], 'role': row['role'],
             'status': rows[row['sample_id']]['frame_status'] if row['sample_id'] in rows else 'NOT_RUN'}
            for row in manifest['selected']]
  return {'frames': frames, 'human_status': 'PRIVATE_HUMAN_HOLDOUT_PENDING',
          'qualification_allowed': False}, rows


@contextmanager
def server(root, *, bind='127.0.0.1', port=0):
  if bind != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  root = Path(root).absolute()
  if any(path.is_symlink() for path in (root, *root.parents)) or root.resolve().is_relative_to(p.ROOT):
    raise ValueError('PRIVATE_VIEWER_CACHE_OUTSIDE_REPO_REQUIRED')
  model, rows = view_model(root)

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def do_GET(self):
      if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
        self.send_error(403)
        return
      path = self.path
      if path == '/':
        content, kind = HTML.encode(), 'text/html; charset=utf-8'
      elif path == '/data':
        content, kind = canonical(model), 'application/json'
      elif path == '/favicon.ico':
        self.send_response(204)
        self.end_headers()
        return
      else:
        pieces = path.split('/')
        if len(pieces) != 3 or pieces[1] not in ('frame', 'image') or not pieces[2].isdigit():
          self.send_error(404)
          return
        ordinal = int(pieces[2])
        if not 0 <= ordinal < len(model['frames']):
          self.send_error(404)
          return
        frame = model['frames'][ordinal]
        if frame['role'] != 'DEVELOPMENT' or frame['sample_id'] not in rows:
          self.send_error(403)
          return
        row = rows[frame['sample_id']]
        if pieces[1] == 'frame':
          content = canonical({'prediction': row['prediction'], 'summary': {
            'sample_id': row['sample_id'], 'image_sha256': row['image_sha256'],
            'prediction_sha256': row['prediction_sha256'], 'lane_count': row['prediction']['lane_count'],
            'confidence': [lane['confidence'] for lane in row['prediction']['lanes']],
            'scope': 'PREDICTION_DIAGNOSTIC_ONLY_NO_TRUTH', 'human_label': None,
          }})
          kind = 'application/json'
        else:
          image_path = root / 'images' / (row['sample_id'] + '.png')
          if any(v.is_symlink() for v in (image_path, *image_path.parents)):
            self.send_error(403)
            return
          content = image_path.read_bytes()
          if digest(content) != row['image_sha256']:
            self.send_error(409)
            return
          kind = 'image/png'
      self.send_response(200)
      self.send_header('Content-Type', kind)
      self.send_header('Content-Length', str(len(content)))
      self.send_header('Content-Security-Policy', CSP)
      self.send_header('Cache-Control', 'no-store')
      self.send_header('X-Content-Type-Options', 'nosniff')
      self.end_headers()
      self.wfile.write(content)

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
    import threading
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'status': 'READ_ONLY_NONQUALIFYING'}), flush=True)
    try:
      input('Press Enter to stop: ')
    finally:
      httpd.shutdown()
      worker.join()


if __name__ == '__main__':
  main()
