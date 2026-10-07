"""Companion to the immutable 29-frame V1 human review tool, public diagnostics only."""

import argparse
from collections import Counter
import html
from pathlib import Path
import json

from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_public_batch as b
from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

MANIFEST_SHA = '82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10'
EXPECTED_PUBLIC_FRAMES = 29
GUIDE = {
  'DETECTOR_FALSE_POSITIVE': (
    'A detector line is clearly unsupported by the visible road marking. A gap between painted dashes is ' + 'not a painted-mask miss automatically.'
  ),
  'DETECTOR_MISS': (
    'A clearly visible relevant marking is not detected. All painted markings are GT, but the detector '
    + 'representation may target only lane boundaries; check representation first.'
  ),
  'DETECTOR_LOCALIZATION_ERROR': (
    'The same identifiable marking was detected, but the prediction is spatially displaced. No numerical ' + 'threshold is inferred from this review.'
  ),
  'GT_MASK_AMBIGUOUS': 'The image does not support an unambiguous mask judgment, or the GT is incomplete. Do not force a detector-failure label.',
  'GT_EXTRA_MARKING': 'The GT includes additional paint types that the detector output does not represent. This is not automatically an ego-boundary miss.',
  'COMPONENT_MATCHING_ERROR': 'Prediction and paint are individually plausible, but row/component association compares the wrong structures.',
  'REPRESENTATION_MISMATCH': (
    'Continuous polylines versus dashed/painted masks account for the discrepancy; absence of paint ' + 'between dashes is not automatically detector failure.'
  ),
  'FAR_FIELD_AMBIGUOUS': 'Distant/horizon geometry is not visually adjudicable. Image thirds are pixel regions, not calibrated distances.',
  'INTERSECTION_OR_MERGE': 'An intersection, split or merge prevents simple marking association. Do not infer an ego lane.',
  'MULTI_LANE_AMBIGUOUS': 'Several marking structures are plausible and assignment cannot be resolved from this frame.',
  'OTHER': 'A cause outside the frozen labels; explain it in the comment. It prevents a resolved causal verdict.',
  'UNRESOLVED': 'Evidence is insufficient. Use this for unreviewable frames; do not guess.',
}
POLICY = {
  'schema': 'FROZEN_29_FRAME_REVIEW_WORKFLOW_V1',
  'labels': list(c.LABELS),
  'public_manifest_sha256': MANIFEST_SHA,
  'public_frame_count': EXPECTED_PUBLIC_FRAMES,
  'complete': 'ALL_FROZEN_FRAMES_HAVE_VALID_IMMUTABLE_EXPLICIT_HUMAN_ROWS',
  'metrics': 'LINEAR_QUANTILES_OF_ORIGINAL_POOLED_SAMPLES_PX_NO_RECOMPUTATION',
  'dominance': 'STRICT_MAJORITY_OF_REVIEWED_SAMPLE_FRAMES_NOT_POPULATION_OR_CAUSAL_MAGNITUDE',
  'unresolved': 'ANY_UNRESOLVED_OTHER_UNREVIEWABLE_PREVENTS_RESOLVED_TAIL_VERDICT',
  'confidence': 'UNCHANGED_PUBLIC_SCORE_BINS_FRAME_MEDIAN_SCORE_NOT_THRESHOLD_SELECTION',
  'reviewer_confidence': 'NULL_NOT_RECORDED_IN_IMMUTABLE_V1_NO_INFERRED_CONFIDENCE',
  'detector_verdict': 'AT_MOST_PUBLIC_DIAGNOSTIC_RETAINED_NO_QUALIFICATION_THRESHOLD',
  'guide': GUIDE,
  'private_input_allowed': False,
  'reference_promotable': False,
}
POLICY_SHA = digest(canonical(POLICY))


def workflow_identity():
  return digest(
    canonical({'workflow_source_sha256': digest(Path(__file__).read_bytes()), 'legacy_tool_sha256': ui.tool_identity(), 'policy_sha256': POLICY_SHA})
  )


def require_manifest(manifest):
  core = c.validate_manifest(manifest)
  if core['scope'] == c.SCOPES[0] and (manifest['receipt_sha256'] != MANIFEST_SHA or len(core['frames']) != EXPECTED_PUBLIC_FRAMES):
    raise ValueError('EXACT_FROZEN_PUBLIC_29_MANIFEST_REQUIRED')
  return core


def ordered_rows(manifest, annotations):
  core = require_manifest(manifest)
  c.review_status(manifest, annotations)
  by_id = {a['frame_id']: a for a in annotations}
  return [by_id[f['frame_id']] for f in core['frames'] if f['frame_id'] in by_id]


def progress(manifest, annotations):
  rows = ordered_rows(manifest, annotations)
  old = c.review_status(manifest, rows)
  n = len(manifest['frames'])
  return seal(
    {
      'schema': 'FROZEN_REVIEW_WORKFLOW_PROGRESS_V1',
      'state': 'NOT_STARTED' if not rows else 'COMPLETE' if len(rows) == n else 'IN_PROGRESS',
      'status': old['status'],
      'manifest_frames': n,
      'reviewed': len(rows),
      'unreviewed': n - len(rows),
      'reviewable': sum(r['reviewable'] for r in rows),
      'unreviewable': sum(not r['reviewable'] for r in rows),
      'missing': old['missing'],
      'unresolved': [r['frame_id'] for r in rows if r['reviewer_label'] == 'UNRESOLVED'],
      'review_manifest_sha256': manifest['receipt_sha256'],
      'workflow_policy_sha256': POLICY_SHA,
      'workflow_source_sha256': workflow_identity(),
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def export_review(manifest, annotations):
  rows = ordered_rows(manifest, annotations)
  return seal(
    {
      'schema': 'FROZEN_PUBLIC_REVIEW_EXPORT_V1',
      'review_manifest_sha256': manifest['receipt_sha256'],
      'selection_policy_sha256': c.POLICY_SHA,
      'review_schema_sha256': c.SCHEMA_SHA,
      'review_tool_sha256': manifest['review_tool_sha256'],
      'workflow_source_sha256': workflow_identity(),
      'workflow_policy_sha256': POLICY_SHA,
      'completed_row_count': len(rows),
      'scope': manifest['scope'],
      'review_rows': [{'annotation': r, 'reviewer_confidence': None, 'confidence_status': 'NOT_RECORDED_V1_SCHEMA'} for r in rows],
      'progress': progress(manifest, rows),
      'raw_images_included': False,
      'reference_promotable': False,
      'private_input_allowed': False,
    }
  )


def descriptive_tail(counts, total):
  if (
    type(total) is not int
    or total <= 0
    or set(counts) - set(c.LABELS)
    or any(type(n) is not int or n < 0 for n in counts.values())
    or sum(counts.values()) != total
  ):
    raise ValueError('EXACT_CATEGORY_ACCOUNTING_REQUIRED')
  if counts.get('UNRESOLVED', 0) or counts.get('OTHER', 0):
    return 'TAIL_UNRESOLVED'
  groups = {
    'MATCHING': ('COMPONENT_MATCHING_ERROR',),
    'DETECTOR': ('DETECTOR_FALSE_POSITIVE', 'DETECTOR_MISS', 'DETECTOR_LOCALIZATION_ERROR'),
    'GT_AMBIGUITY': ('GT_MASK_AMBIGUOUS', 'GT_EXTRA_MARKING'),
  }
  for name, labels in groups.items():
    if sum(counts.get(k, 0) for k in labels) * 2 > total:
      return 'TAIL_EXPLAINED_' + name + '_DOMINANT'
  return 'TAIL_EXPLAINED_MIXED'


def aggregate(manifest, annotations, metric_loader):
  rows = ordered_rows(manifest, annotations)
  if len(rows) != len(manifest['frames']):
    raise ValueError('HUMAN_REVIEW_INCOMPLETE')
  export = export_review(manifest, rows)
  categories = {
    label: {
      'frame_count': 0,
      'pools': {k: [] for k in ('pred', 'gt', 'paired_spatial_pred')},
      'confidence': Counter(),
      'regions': Counter(),
      'representative_frame_ids': [],
    }
    for label in c.LABELS
  }
  score_buckets = {}
  traces = []
  frames = {f['frame_id']: f for f in manifest['frames']}
  for row in rows:
    frame = frames[row['frame_id']]
    raw = metric_loader(frame)
    trace = unseal(raw)
    if (
      set(trace) != {'schema', 'run_sha256', 'frame', 'original_row_sha256', 'pool'}
      or trace['schema'] != 'BOUND_REVIEW_METRIC_TRACE_V1'
      or trace['run_sha256'] != manifest['run_sha256']
      or trace['frame'] != frame
      or not is_sha256(trace['original_row_sha256'])
      or type(trace['pool']) is not dict
      or set(trace['pool']) != {'pred', 'gt', 'paired_spatial_pred'}
    ):
      raise ValueError('BOUND_ORIGINAL_REVIEW_METRIC_REQUIRED')
    for key, target in (('pred', 'pred_to_gt'), ('gt', 'gt_to_pred')):
      if t.distribution(trace['pool'][key]) != frame[target]:
        raise ValueError('ORIGINAL_METRIC_SUMMARY_MISMATCH')
    t.distribution(trace['pool']['paired_spatial_pred'])
    traces.append({'frame_id': frame['frame_id'], 'trace_sha256': raw['receipt_sha256'], 'original_row_sha256': trace['original_row_sha256']})
    cat = categories[row['reviewer_label']]
    cat['frame_count'] += 1
    for key in cat['pools']:
      cat['pools'][key].extend(trace['pool'][key])
    score = frame['confidence']['median']
    bucket = 'UNAVAILABLE' if score is None else t.confidence_bucket(score)
    cat['confidence'][bucket] += 1
    cat['regions'].update({name: value['pred_to_gt']['sample_count'] for name, value in frame['regions'].items()})
    cat['representative_frame_ids'].append(frame['frame_id'])
    score_buckets.setdefault(bucket, Counter())[row['reviewer_label']] += 1
  counts = {label: value['frame_count'] for label, value in categories.items()}
  n = len(rows)
  for value in categories.values():
    value['metrics'] = {key: t.distribution(samples) for key, samples in value.pop('pools').items()}
    value['percentage'] = 100.0 * value['frame_count'] / n
    value['confidence'] = dict(sorted(value['confidence'].items()))
    value['regions'] = dict(sorted(value['regions'].items()))
    value['representative_frame_ids'] = sorted(value['representative_frame_ids'])[:3]
  test = manifest['scope'] == c.SCOPES[1]
  verdict = 'TAIL_UNRESOLVED' if test or any(not r['reviewable'] for r in rows) else descriptive_tail(counts, n)
  return seal(
    {
      'schema': 'PUBLIC_REVIEW_SAMPLE_TAIL_ATTRIBUTION_V1',
      'status': 'TEST_ONLY_NOT_HUMAN_EVIDENCE' if test else 'HUMAN_REVIEW_COMPLETE_DIAGNOSTIC',
      'tail_verdict': verdict,
      'detector_verdict': 'TAIL_UNRESOLVED' if verdict == 'TAIL_UNRESOLVED' else 'PUBLIC_DIAGNOSTIC_RETAINED',
      'categories': categories,
      'confidence_category_counts': {key: dict(sorted(value.items())) for key, value in sorted(score_buckets.items())},
      'confidence_category_rates': {
        key: {label: value.get(label, 0) / sum(value.values()) for label in c.LABELS} for key, value in sorted(score_buckets.items())
      },
      'review_result_sha256': export['receipt_sha256'],
      'review_manifest_sha256': manifest['receipt_sha256'],
      'selection_policy_sha256': c.POLICY_SHA,
      'review_schema_sha256': c.SCHEMA_SHA,
      'review_tool_sha256': manifest['review_tool_sha256'],
      'workflow_policy_sha256': POLICY_SHA,
      'workflow_source_sha256': workflow_identity(),
      'metric_trace_receipts': traces,
      'scope': 'SELECTED_STRATIFIED_DIAGNOSTIC_SAMPLE_NOT_POPULATION',
      'metric_unit': 'px',
      'causal_metric_difference_computed': False,
      'full_result_changed': False,
      'ego_lane_identity': False,
      'meter_conversion': False,
      'official_benchmark': 'NOT_RUN_BLOCKED_CULANE_DATASET_UNAVAILABLE',
      'qualification': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def guide_html():
  text = ''.join('<h2>' + label + '</h2><p>' + html.escape(GUIDE[label]) + '</p>' for label in c.LABELS)
  return (
    '<!doctype html><html><head><meta charset="utf-8"><title>Marking reviewer guide</title>'
    + '<link rel="stylesheet" href="/style.css"></head><body><h1>PUBLIC COMMA10K / NO INDEPENDENT LANE TRUTH</h1>'
    + '<p>Inspect the original image, paint mask and prediction independently before selecting one primary label. '
    + 'Automatic stratum names are hypotheses. Inspect on/off overlays; do not copy a stratum as a label. '
    + 'Unreviewable requires UNRESOLVED. Optional comments explain uncertainty. Immutable rows cannot be overwritten. '
    + 'The detector represents continuous lines; GT contains all painted markings and no ego-left/right identity. '
    + 'Do not subtract directional p95 and same-point p95 as a matching-error magnitude. '
    + 'Scores are detector confidence, not reviewer confidence. V1 reviewer confidence is not recorded. '
    + '29 selected frames are not a random holdout or a population failure-rate sample.</p>'
    + text
    + '</body></html>'
  )


PAGE = ui.HTML.replace(
  '<div><button id="prev">',
  '<p id="progress"></p><a href="/guide" target="_blank" rel="noopener">Reviewer instructions</a> '
  + '<a id="export" href="/api/export" download="public-review-export.json">Export review JSON</a>'
  + '<button id="unresolved">Jump to unresolved / unreviewed</button><button id="worst">Jump to worst tail</button>'
  + '<div><button id="prev">',
)
SCRIPT = (
  ui.JS
  + """
let workflowProgress;
async function updateProgress(){workflowProgress=await request('/api/progress');
 $('progress').textContent=workflowProgress.reviewed+' / '+workflowProgress.manifest_frames+
 ' reviewed | '+workflowProgress.state+' | reviewable '+workflowProgress.reviewable+
 ' | unreviewable '+workflowProgress.unreviewable+' | '+workflowProgress.status;}
const legacyLoad=load;
load=async i=>{await legacyLoad(i);await updateProgress();};
$('unresolved').onclick=async()=>{try{await updateProgress();
 const targets=new Set([...workflowProgress.missing,...workflowProgress.unresolved]);
 for(let step=1;step<=config.frames.length;step++){const j=(index+step)%config.frames.length;
 if(targets.has(config.frames[j].frame_id)){await load(j);return;}}
 $('status').textContent='No unresolved or unreviewed frames';}catch(e){showError(e);}};
$('worst').onclick=()=>{const ranked=config.frames.map((f,i)=>({f,i})).filter(x=>x.f.pred_to_gt.p95!==null);
 ranked.sort((a,b)=>b.f.pred_to_gt.p95-a.f.pred_to_gt.p95||a.f.frame_id.localeCompare(b.f.frame_id));
 if(ranked.length)load(ranked[0].i).catch(showError);};
"""
)


class WorkflowSession:
  def __init__(self, legacy, metric_loader=None):
    require_manifest(legacy.manifest)
    self.legacy, self.metric_loader = legacy, metric_loader
    self.freeze = seal(
      {
        'schema': POLICY['schema'],
        'review_manifest_sha256': legacy.manifest['receipt_sha256'],
        'selection_policy_sha256': c.POLICY_SHA,
        'review_schema_sha256': c.SCHEMA_SHA,
        'legacy_tool_sha256': ui.tool_identity(),
        'workflow_source_sha256': workflow_identity(),
        'workflow_policy_sha256': POLICY_SHA,
      }
    )
    path = legacy.output / 'workflow-freeze.json'
    with s.writer_lease(legacy.output):
      if path.exists():
        if s.read_json(path) != self.freeze:
          raise ValueError('IMMUTABLE_WORKFLOW_FREEZE_REQUIRED')
      else:
        s.atomic_json(path, self.freeze)

  def guard(self):
    try:
      legacy_freeze = s.read_json(self.legacy.output / 'review-freeze.json')
      workflow_freeze = s.read_json(self.legacy.output / 'workflow-freeze.json')
    except (OSError, ValueError) as exc:
      raise ValueError('LEGACY_REVIEW_FREEZE_MISSING_OR_CORRUPT') from exc
    if legacy_freeze != self.legacy.manifest:
      raise ValueError('LEGACY_REVIEW_MANIFEST_DRIFT')
    if self.freeze['workflow_source_sha256'] != workflow_identity() or workflow_freeze != self.freeze:
      raise ValueError('WORKFLOW_IDENTITY_DRIFT')

  def progress(self):
    self.guard()
    return progress(self.legacy.manifest, self.legacy.annotations())

  def export(self):
    self.guard()
    return export_review(self.legacy.manifest, self.legacy.annotations())

  def finalize(self):
    self.guard()
    rows = self.legacy.annotations()
    if len(rows) != len(self.legacy.manifest['frames']):
      raise ValueError('HUMAN_REVIEW_INCOMPLETE')
    if self.metric_loader is None:
      raise ValueError('BOUND_METRIC_LOADER_REQUIRED')
    result = aggregate(self.legacy.manifest, rows, self.metric_loader)
    self.guard()
    return result


def make_server(session, *, host='127.0.0.1', port=0):
  server = ui.make_server(session.legacy, host=host, port=port)
  parent = server.RequestHandlerClass

  class Handler(parent):
    def do_GET(self):
      if not self.authorized():
        self.reply(403, {'error': 'LOOPBACK_HOST_REQUIRED'})
        return
      try:
        session.guard()
        if self.path == '/':
          self.reply(200, PAGE, 'text/html; charset=utf-8')
        elif self.path == '/app.js':
          self.reply(200, SCRIPT, 'text/javascript; charset=utf-8')
        elif self.path == '/guide':
          self.reply(200, guide_html(), 'text/html; charset=utf-8')
        elif self.path == '/api/progress':
          self.reply(200, session.progress())
        elif self.path == '/api/export':
          self.reply(200, session.export())
        elif self.path == '/api/final-attribution':
          self.reply(200, session.finalize())
        else:
          super().do_GET()
      except (ValueError, KeyError, TypeError, IndexError) as exc:
        self.reply(400, {'error': str(exc)})

    def do_POST(self):
      try:
        session.guard()
      except ValueError as exc:
        self.reply(400, {'error': str(exc)})
        return
      super().do_POST()

  server.RequestHandlerClass = Handler
  return server


def bound_metric_loader(run_dir, cache, manifest):
  """Uses completed index identities; reads public cached metadata, not images or inference."""
  run_dir, cache = Path(run_dir), Path(cache)
  run = s.read_json(run_dir / 'run-freeze.json')
  marker = s.read_json(run_dir / 'completed.json')
  unseal(marker)
  if marker['receipt_sha256'] != manifest['full_completion_sha256'] or marker['run_sha256'] != manifest['run_sha256']:
    raise ValueError('REVIEW_COMPLETION_BINDING_MISMATCH')
  index_path = run_dir / 'index.json'
  if digest(r.read_bound_bytes(index_path, marker['index_file_sha256'])) != marker['index_file_sha256']:
    raise ValueError('REVIEW_COMPLETED_INDEX_DRIFT')
  index = s.read_json(index_path)
  unseal(index)
  inputs = s.read_json(cache.parent / 'full-input-manifest.json')
  protocol = s.read_json(cache.parent / 'full-protocol.json')
  if (
    digest(r.read_bound_bytes(cache.parent / 'full-input-manifest.json', run['manifest_file_sha256'])) != run['manifest_file_sha256']
    or digest(r.read_bound_bytes(cache.parent / 'full-protocol.json', run['protocol_file_sha256'])) != run['protocol_file_sha256']
  ):
    raise ValueError('REVIEW_INPUT_FREEZE_DRIFT')
  pairs = protocol['pairs']
  by_id = {pair['image']: i for i, pair in enumerate(pairs)}
  identities = {f['path']: f for f in inputs['files']}

  def load(frame):
    ui.require_frozen_metric_sources(run)
    if s.read_json(run_dir / 'completed.json') != marker or digest(r.read_bound_bytes(index_path, marker['index_file_sha256'])) != marker['index_file_sha256']:
      raise ValueError('REVIEW_COMPLETED_INDEX_DRIFT')
    ordinal = by_id[frame['frame_id']]
    raw = s.read_json(run_dir / 'rows' / f'{ordinal:05d}.json')
    if raw['receipt_sha256'] != index['rows'][ordinal]['receipt_sha256']:
      raise ValueError('REVIEW_ORIGINAL_ROW_DRIFT')
    core = b.verify_resume(raw, run['receipt_sha256'], ordinal, pairs[ordinal], identities)
    if core['ledger']['receipt_sha256'] != frame['metric_result_sha256'] or digest(canonical(core['detector_record'])) != frame['prediction_sha256']:
      raise ValueError('REVIEW_METRIC_OR_PREDICTION_DRIFT')
    return seal(
      {
        'schema': 'BOUND_REVIEW_METRIC_TRACE_V1',
        'run_sha256': run['receipt_sha256'],
        'frame': frame,
        'original_row_sha256': raw['receipt_sha256'],
        'pool': {key: core['pool'][key] for key in ('pred', 'gt', 'paired_spatial_pred')},
      }
    )

  return load


def main():
  parser = argparse.ArgumentParser()
  for name in ('run', 'cache', 'manifest', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  manifest = s.read_json(args.manifest)
  require_manifest(manifest)
  legacy = ui.open_public_review(args.run, args.cache, manifest, args.output)
  session = WorkflowSession(legacy, bound_metric_loader(args.run, args.cache, manifest))
  server = make_server(session, port=args.port)
  print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port), 'progress': session.progress()}), flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
