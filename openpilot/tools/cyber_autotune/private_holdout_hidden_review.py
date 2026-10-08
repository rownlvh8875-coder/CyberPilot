"""Per-frame immutable-save gate around original raw-only annotation UI.

Inference artifacts cannot be accessed through UI/API before that exact frame's
first decision. Existing first decisions remain unchanged; all-sixty metrics
still require a whole human-reference freeze. No inference or AI invocation here.
"""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import threading

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_annotation as original
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
from openpilot.tools.cyber_autotune import private_pixel_execution as p

HTML = original.HTML.replace('Detector/AI/model/geometry는 표시하지 않습니다.',
                             '저장 전 Detector/AI/model/geometry는 표시하지 않습니다.')
HTML = HTML.replace('<p id="status">', '<pre id="comparison-panel" hidden></pre><p id="status">')
HTML = HTML.replace("let data,index=0", "let hiddenComparison=null;let data,index=0")
HTML = HTML.replace("ctx.restore();\nq('#points')", """ctx.restore();
if(hiddenComparison&&locked&&loadedIndex===index){ctx.save();ctx.translate(ox,oy);ctx.scale(scale,scale);
ctx.strokeStyle='#fa69dc';ctx.lineWidth=2/scale;ctx.setLineDash([5/scale,4/scale]);
hiddenComparison.detector.lanes.forEach(lane=>{ctx.beginPath();lane.points.forEach(([x,y],i)=>{
if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y);});ctx.stroke();});ctx.restore();}
q('#points')""")
HTML = HTML.replace("q('#comparison').disabled=data.progress.reviewed!==60;", "")
HTML = HTML.replace("async function show(){const stamp=++generation;", """async function show(){const stamp=++generation;
hiddenComparison=null;q('#comparison-panel').hidden=true;q('#comparison-panel').textContent='';
q('#comparison').disabled=true;""")
HTML = HTML.replace("q('#reviewer').disabled=locked;draw();", "q('#reviewer').disabled=locked;q('#comparison').disabled=!locked;draw();")
HTML = HTML.replace('Detector comparison gate: 60/60 freeze required', 'Show detector / AI comparison after this first save')
HTML = HTML.replace(
  "q('#comparison').onclick=async()=>{try{const value=await request('/detector/'+index);" +
  "q('#status').textContent=JSON.stringify(value);}catch(e){report(e);}};",
"""q('#comparison').onclick=async()=>{const stamp=generation,ordinal=loadedIndex;
try{const value=await request('/comparison/'+ordinal);
if(stamp!==generation||ordinal!==loadedIndex||!locked)return;
hiddenComparison=value;q('#comparison-panel').hidden=false;
q('#comparison-panel').textContent=JSON.stringify({provenance:value.provenance,
confidence:value.detector.lanes.map(l=>l.confidence),ai:value.ai},null,2);draw();}catch(e){
if(stamp===generation)report(e);}};""")


class ComparisonStore:
  def __init__(self, raw, output):
    raw, self.output = p.private_directories(raw, output)
    self.human = original.ReviewStore(raw)

  def bind(self, ordinal):
    first = self.human.first(ordinal)
    if first is None:
      raise ValueError('THIS_FRAME_FIRST_DECISION_REQUIRED_BEFORE_OUTPUT_OPEN')
    auth = h.read(self.output / 'authorization.json')
    package = self.human.package
    im = hidden.image(package, ordinal)
    prediction = h.read(self.output / 'rows' / (im['sample_id'] + '.json'))
    hidden.validate_detector_row(package, auth, ordinal, prediction)
    ai_path = h.private_path(self.output / 'ai' / (im['sample_id'] + '.json'))
    ai = h.read(ai_path) if ai_path.exists() else None
    relation = hidden.first_relation(package, auth, ordinal, first, prediction, ai)
    h.write_immutable(self.output / 'relations' / first['receipt_sha256'] / (relation['receipt_sha256'] + '.json'), relation)
    return prediction, ai, relation

  def pending(self, first):
    h.write_immutable(self.output / 'relation-pending' / (first['receipt_sha256'] + '.json'),
                      h.seal({'schema': 'PRIVATE_FIRST_HIDDEN_RELATION_PENDING_V1',
                              'first_decision_sha256': first['receipt_sha256'],
                              'status': 'PRIVATE_FIRST_DECISION_SAVED_HIDDEN_RELATION_PENDING',
                              **h.FIREWALL}))

  def visible(self, ordinal):
    prediction, ai, relation = self.bind(ordinal)
    # Never publish other frames' output, global diagnostics or source paths.
    return {'schema': 'PRIVATE_SAVED_FRAME_COMPARISON_V1', 'provenance': relation,
            'detector': prediction['prediction'], 'ai': ai}


@contextmanager
def server(raw, output, *, bind='127.0.0.1', port=0):
  store = ComparisonStore(raw, output)
  with original.server(raw, bind=bind, port=port) as httpd:
    base = httpd.RequestHandlerClass

    class Handler(base):
      def respond(self, status, value, kind='application/json'):
        parts = self.path.split('/')
        if (status == 200 and len(parts) == 3 and parts[1] == 'save'
            and type(value) is dict and value.get('schema') == 'PRIVATE_BLIND_PIXEL_FIRST_DECISION_V1'):
          # The original handler has already durably saved the first decision.
          # Missing comparison artifacts cannot fabricate or erase human evidence.
          try:
            store.bind(int(parts[2]))
          except (ValueError, KeyError, OSError, TypeError):
            try:
              store.pending(value)
            except (ValueError, KeyError, OSError, TypeError):
              # The original first receipt is already durable and authoritative.
              # Keep comparison closed; no fabricated provenance or hints.
              pass
        super().respond(status, value, kind)

      def do_GET(self):
        if not self.allowed():
          self.respond(403, {'error': 'LOCAL_ORIGIN_REQUIRED'})
          return
        if self.path == '/':
          self.respond(200, HTML.encode(), 'text/html; charset=utf-8')
          return
        parts = self.path.split('/')
        if len(parts) == 3 and parts[1] in ('comparison', 'detector', 'ai') and parts[2].isdigit():
          ordinal = int(parts[2])
          try:
            if store.human.first(ordinal) is None:
              self.respond(403, {'error': 'THIS_FRAME_IMMUTABLE_FIRST_DECISION_REQUIRED'})
              return
            self.respond(200, store.visible(ordinal))
          except (ValueError, KeyError, OSError, TypeError):
            self.respond(409, {'error': 'BOUND_HIDDEN_COMPARISON_UNAVAILABLE'})
          return
        super().do_GET()
    httpd.RequestHandlerClass = Handler
    yield httpd


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--raw-cache', type=Path, required=True)
  parser.add_argument('--hidden-cache', type=Path, required=True)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  with server(args.raw_cache, args.hidden_cache, port=args.port) as httpd:
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'status': 'BLIND_RAW_ONLY_UNTIL_THIS_FRAME_SAVE'}), flush=True)
    try:
      input('Press Enter to stop: ')
    finally:
      httpd.shutdown()
      worker.join()


if __name__ == '__main__':
  main()
