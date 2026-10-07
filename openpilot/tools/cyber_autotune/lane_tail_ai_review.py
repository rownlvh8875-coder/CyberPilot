"""Separate public vision suggestions; never write or synthesize a human annotation."""

import argparse
from datetime import datetime, UTC
import json
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

VIEWS = ('original', 'gt_overlay', 'prediction_overlay', 'gt_only', 'prediction_only')
QUESTIONS = (
  'marking_correspondence',
  'false_positive',
  'missed_marking',
  'localization_displacement',
  'dashed_vs_continuous',
  'gt_ambiguity',
  'component_association',
  'far_field',
  'merge_or_multi_lane',
)
ANSWERS = ('SUPPORTED', 'POSSIBLE', 'NOT_OBSERVED', 'UNRESOLVED')
CONFIDENCE = ('HIGH', 'MEDIUM', 'LOW')
MODEL = {'provider': 'OpenAI', 'model': 'GPT-6', 'version': None, 'invocation': 'CODEX_INTERACTIVE_VISION_VIEW_IMAGE'}
TEST_MODEL = {'provider': 'TEST_ONLY', 'model': 'TEST_ONLY', 'version': None, 'invocation': 'TEST_ONLY'}
POLICY = {
  'schema': 'AI_LANE_TAIL_PREREVIEW_POLICY_V1',
  'labels': list(c.LABELS),
  'required_views': list(VIEWS),
  'questions': list(QUESTIONS),
  'answers': list(ANSWERS),
  'confidence': list(CONFIDENCE),
  'confidence_meaning': 'UNCALIBRATED_SUGGESTION_CERTAINTY_NOT_DETECTOR_OR_QUALIFICATION_THRESHOLD',
  'confidence_rule': 'HIGH_ONLY_CLEAR_VISIBLE_SUPPORT_MEDIUM_PARTIAL_LOW_AMBIGUOUS_DEFAULT_UNRESOLVED',
  'prompt': 'Inspect all five public views. Report observable evidence only. Use the frozen taxonomy. '
  + 'Do not infer ego lanes, meters, calibration, human labels, or causal p95 subtraction. '
  + 'Separate visible support from pixel-mask/polyline semantics. If not adjudicable, use UNRESOLVED.',
  'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
  'human_label': None,
  'default': 'BLIND_HUMAN_FIRST_IMMUTABLE_SAVE_THEN_REVEAL',
  'before_save': 'DURABLE_ASSISTED_EXPOSURE_BEFORE_RETURNING_ANY_SUGGESTION',
  'assisted_storage': 'SEPARATE_FROM_LEGACY_HUMAN_COMPLETION_NO_BLIND_PROMOTION',
  'final_attribution': 'HUMAN_ONLY_ASSISTED_ROWS_BLOCK_BLIND_INDEPENDENT_FINALIZATION',
  'scope_limit': 'UI_RECORDED_EXPOSURE_CANNOT_PROVE_NO_EXTERNAL_AI_EXPOSURE',
  'private_input_allowed': False,
  'reference_promotable': False,
}
POLICY_SHA = digest(canonical(POLICY))


def tool_identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'workflow': w.workflow_identity(), 'policy': POLICY_SHA}))


def freeze_experiment(manifest, inputs, experiment_id):
  w.require_manifest(manifest)
  if not re.fullmatch(r'AI_REVIEW_[A-Z0-9_]{1,40}', experiment_id):
    raise ValueError('VERSIONED_AI_EXPERIMENT_REQUIRED')
  if type(inputs) is not list or len(inputs) != len(manifest['frames']):
    raise ValueError('EXACT_FIVE_VIEW_INPUTS_REQUIRED')
  for f, item in zip(manifest['frames'], inputs, strict=True):
    if (
      type(item) is not dict
      or set(item) != {'frame', 'views', 'same_point_error'}
      or item['frame'] != f
      or type(item['views']) is not dict
      or set(item['views']) != set(VIEWS)
      or not all(is_sha256(h) for h in item['views'].values())
      or type(item['same_point_error']) is not dict
    ):
      raise ValueError('EXACT_FIVE_VIEW_INPUTS_REQUIRED')
    c.public_frame_id(f['frame_id'])
  return seal(
    {
      'schema': 'AI_LANE_TAIL_EXPERIMENT_V1',
      'experiment_id': experiment_id,
      'review_manifest_sha256': manifest['receipt_sha256'],
      'selection_policy_sha256': c.POLICY_SHA,
      'review_schema_sha256': c.SCHEMA_SHA,
      'legacy_review_tool_sha256': manifest['review_tool_sha256'],
      'review_tool_sha256': tool_identity(),
      'prompt_policy_sha256': POLICY_SHA,
      'inputs': inputs,
      'model_identity': TEST_MODEL if manifest['scope'] == c.SCOPES[1] else MODEL,
      'scope': 'TEST_ONLY' if manifest['scope'] == c.SCOPES[1] else 'PUBLIC_COMMA10K',
      'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def validate_experiment(manifest, experiment):
  core = unseal(experiment)
  expected = freeze_experiment(manifest, core['inputs'], core['experiment_id'])
  if experiment != expected:
    raise ValueError('FROZEN_AI_EXPERIMENT_IDENTITY_MISMATCH')


def make_suggestion(manifest, experiment, index, *, label, secondary, confidence, reason, observations, answers, model, timestamp):
  validate_experiment(manifest, experiment)
  if type(index) is not int or not 0 <= index < len(manifest['frames']):
    raise ValueError('UNKNOWN_AI_FRAME')
  f = manifest['frames'][index]
  row = seal(
    {
      'schema': 'AI_LANE_TAIL_REVIEW_SUGGESTION_V1',
      'experiment_id': experiment['experiment_id'],
      'experiment_sha256': experiment['receipt_sha256'],
      'review_manifest_sha256': manifest['receipt_sha256'],
      **{k: f[k] for k in ('frame_id', 'image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256')},
      'suggested_label': label,
      'secondary_possible_labels': secondary,
      'ai_confidence': confidence,
      'reasoning_summary': reason,
      'visual_evidence': {'observations': observations, 'questions': answers},
      'vision_inputs': experiment['inputs'][index]['views'],
      'metric_context': {'pred_to_gt': f['pred_to_gt'], 'gt_to_pred': f['gt_to_pred'], 'same_point_error': experiment['inputs'][index]['same_point_error']},
      'model_identity': model,
      'timestamp': timestamp,
      'prompt_policy_sha256': POLICY_SHA,
      'review_tool_sha256': tool_identity(),
      'human_label': None,
      'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )
  validate_suggestion(manifest, experiment, row)
  return row


def validate_suggestion(manifest, experiment, row):
  validate_experiment(manifest, experiment)
  core = unseal(row)
  fields = {
    'schema',
    'experiment_id',
    'experiment_sha256',
    'review_manifest_sha256',
    'frame_id',
    'image_sha256',
    'mask_sha256',
    'prediction_sha256',
    'metric_result_sha256',
    'suggested_label',
    'secondary_possible_labels',
    'ai_confidence',
    'reasoning_summary',
    'visual_evidence',
    'vision_inputs',
    'metric_context',
    'model_identity',
    'timestamp',
    'prompt_policy_sha256',
    'review_tool_sha256',
    'human_label',
    'tier',
    'private_input_allowed',
    'reference_promotable',
  }
  if set(core) != fields:
    raise ValueError('EXACT_AI_SCHEMA_REQUIRED')
  f = next((f for f in manifest['frames'] if f['frame_id'] == core['frame_id']), None)
  if f is None:
    raise ValueError('UNKNOWN_AI_FRAME')
  item = experiment['inputs'][manifest['frames'].index(f)]
  expected = {
    'schema': 'AI_LANE_TAIL_REVIEW_SUGGESTION_V1',
    'experiment_id': experiment['experiment_id'],
    'experiment_sha256': experiment['receipt_sha256'],
    'review_manifest_sha256': manifest['receipt_sha256'],
    **{k: f[k] for k in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256')},
    'vision_inputs': item['views'],
    'model_identity': experiment['model_identity'],
    'prompt_policy_sha256': POLICY_SHA,
    'review_tool_sha256': tool_identity(),
    'human_label': None,
    'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
    'private_input_allowed': False,
    'reference_promotable': False,
    'metric_context': {'pred_to_gt': f['pred_to_gt'], 'gt_to_pred': f['gt_to_pred'], 'same_point_error': item['same_point_error']},
  }
  if any(core[k] != v for k, v in expected.items()):
    raise ValueError('AI_FRAME_OR_TIER_BINDING_MISMATCH')
  secondary = core['secondary_possible_labels']
  evidence = core['visual_evidence']
  if (
    core['suggested_label'] not in c.LABELS
    or core['ai_confidence'] not in CONFIDENCE
    or type(secondary) is not list
    or any(k not in c.LABELS or k == core['suggested_label'] for k in secondary)
    or len(set(secondary)) != len(secondary)
    or type(core['reasoning_summary']) is not str
    or not 1 <= len(core['reasoning_summary']) <= 600
    or type(evidence) is not dict
    or set(evidence) != {'observations', 'questions'}
    or type(evidence['observations']) is not list
    or not 1 <= len(evidence['observations']) <= 9
    or any(type(x) is not str or not 1 <= len(x) <= 400 for x in evidence['observations'])
    or type(evidence['questions']) is not dict
    or set(evidence['questions']) != set(QUESTIONS)
    or any(v not in ANSWERS for v in evidence['questions'].values())
  ):
    raise ValueError('OBSERVABLE_VISION_TAXONOMY_REQUIRED')
  try:
    if not core['timestamp'].endswith('Z') or datetime.fromisoformat(core['timestamp'].replace('Z', '+00:00')).utcoffset().total_seconds() != 0:
      raise ValueError()
  except (ValueError, TypeError, AttributeError) as exc:
    raise ValueError('UTC_AI_REVIEW_TIMESTAMP_REQUIRED') from exc
  return core


def indexed_rows(output, dirname, indexname, identity, validator):
  """Recover row-before-index orphans; a missing indexed row never passes."""
  rows = []
  for path in sorted((output / dirname).iterdir()):
    if path.name.startswith('.') and path.name.endswith('.tmp'):
      continue
    raw = s.read_json(path)
    ordinal = validator(raw)
    if path.name != f'{ordinal:05d}.json':
      raise ValueError('NONCANONICAL_COMPANION_ROW')
    rows.append(raw)
  path = output / indexname
  index = unseal(s.read_json(path))
  if set(index) != {'identity_sha256', 'rows'} or index['identity_sha256'] != identity or type(index['rows']) is not list:
    raise ValueError('COMPANION_INDEX_IDENTITY_MISMATCH')
  hashes = [r['receipt_sha256'] for r in rows]
  if len(set(index['rows'])) != len(index['rows']) or not set(index['rows']).issubset(hashes):
    raise ValueError('MISSING_INDEXED_COMPANION_ROW')
  return rows


def write_index(output, name, identity, rows):
  s.atomic_json(output / name, seal({'identity_sha256': identity, 'rows': [r['receipt_sha256'] for r in rows]}))


class SuggestionStore:
  def __init__(self, manifest, experiment, output):
    validate_experiment(manifest, experiment)
    self.manifest, self.experiment, self.output = manifest, experiment, Path(output).resolve()
    if self.output.is_relative_to(Path(__file__).resolve().parents[3]):
      raise ValueError('AI_WORKING_STORE_MUST_STAY_EXTERNAL')
    s.durable_mkdir(self.output / 'rows')
    with s.writer_lease(self.output):
      path = self.output / 'experiment-freeze.json'
      if path.exists():
        if s.read_json(path) != experiment:
          raise ValueError('IMMUTABLE_AI_EXPERIMENT_REQUIRED')
        write_index(self.output, 'index.json', experiment['receipt_sha256'], self.rows())
      else:
        if any((self.output / 'rows').iterdir()) or (self.output / 'index.json').exists():
          raise ValueError('UNBOUND_AI_ROWS_FORBIDDEN')
        s.atomic_json(path, experiment)
        write_index(self.output, 'index.json', experiment['receipt_sha256'], [])

  def guard(self):
    validate_experiment(self.manifest, self.experiment)
    if s.read_json(self.output / 'experiment-freeze.json') != self.experiment:
      raise ValueError('AI_FREEZE_DRIFT')

  def rows(self):
    self.guard()

    def validate(raw):
      f = validate_suggestion(self.manifest, self.experiment, raw)
      return next(i for i, frame in enumerate(self.manifest['frames']) if frame['frame_id'] == f['frame_id'])

    return indexed_rows(self.output, 'rows', 'index.json', self.experiment['receipt_sha256'], validate)

  def append(self, row):
    core = validate_suggestion(self.manifest, self.experiment, row)
    i = next(i for i, f in enumerate(self.manifest['frames']) if f['frame_id'] == core['frame_id'])
    with s.writer_lease(self.output):
      self.rows()
      path = self.output / 'rows' / f'{i:05d}.json'
      if path.exists():
        raise FileExistsError('AI_SUGGESTION_IMMUTABLE_NEW_EXPERIMENT_REQUIRED')
      s.atomic_json(path, row)
      write_index(self.output, 'index.json', self.experiment['receipt_sha256'], self.rows())

  def status(self):
    rows = self.rows()
    return seal(
      {
        'schema': 'AI_PREREVIEW_PROGRESS_V1',
        'status': 'AI_PREREVIEW_COMPLETE' if len(rows) == len(self.manifest['frames']) else 'AI_PREREVIEW_PENDING',
        'suggestions': len(rows),
        'expected': len(self.manifest['frames']),
        'human_label': None,
        'experiment_sha256': self.experiment['receipt_sha256'],
        'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
        'private_input_allowed': False,
        'reference_promotable': False,
      }
    )


class AIReviewSession:
  def __init__(self, workflow, store):
    self.workflow, self.store, self.legacy = workflow, store, workflow.legacy
    if store.manifest != self.legacy.manifest:
      raise ValueError('AI_HUMAN_MANIFEST_MISMATCH')
    self.freeze = seal(
      {'schema': 'AI_EXPOSURE_WORKFLOW_V1', 'manifest_sha256': store.manifest['receipt_sha256'], 'tool_sha256': tool_identity(), 'policy_sha256': POLICY_SHA}
    )
    out = self.legacy.output
    s.durable_mkdir(out / 'ai-exposures')
    s.durable_mkdir(out / 'ai-assisted-annotations')
    anchor_path = store.output / 'human-workflow-anchor.json'
    anchor = seal(
      {'schema': 'AI_HUMAN_ADMISSION_ANCHOR_V1', 'freeze_sha256': self.freeze['receipt_sha256'], 'human_store_path_sha256': digest(str(out.resolve()).encode())}
    )
    self.anchor = anchor
    with s.writer_lease(store.output):
      if anchor_path.exists():
        if s.read_json(anchor_path) != anchor or not (out / 'ai-exposure-freeze.json').exists():
          raise ValueError('AI_EXPOSURE_ANCHOR_LOST_OR_MISMATCH')
      else:
        if self.legacy.annotations() or any((out / 'ai-assisted-annotations').iterdir()) or any((out / 'ai-exposures').iterdir()):
          raise ValueError('EXISTING_HUMAN_ROWS_WITHOUT_AI_PROVENANCE_ANCHOR')
        s.atomic_json(anchor_path, anchor)
    with s.writer_lease(out):
      path = out / 'ai-exposure-freeze.json'
      if path.exists():
        if s.read_json(path) != self.freeze:
          raise ValueError('IMMUTABLE_AI_EXPOSURE_WORKFLOW_REQUIRED')
        write_index(out, 'ai-exposure-index.json', self.freeze['receipt_sha256'], self.exposures())
        write_index(out, 'ai-assisted-index.json', self.freeze['receipt_sha256'], self.assisted_rows())
      else:
        if any((out / 'ai-exposures').iterdir()) or (out / 'ai-exposure-index.json').exists():
          raise ValueError('UNBOUND_AI_EXPOSURES_FORBIDDEN')
        s.atomic_json(path, self.freeze)
        write_index(out, 'ai-exposure-index.json', self.freeze['receipt_sha256'], [])
        write_index(out, 'ai-assisted-index.json', self.freeze['receipt_sha256'], [])

  def guard(self):
    self.workflow.guard()
    self.store.guard()
    if s.read_json(self.store.output / 'human-workflow-anchor.json') != self.anchor:
      raise ValueError('AI_EXPOSURE_ANCHOR_LOST_OR_MISMATCH')
    if s.read_json(self.legacy.output / 'ai-exposure-freeze.json') != self.freeze:
      raise ValueError('AI_EXPOSURE_FREEZE_DRIFT')

  def exposures(self):
    self.guard()
    human = {r['frame_id']: r for r in self.legacy.annotations()}

    def validate(raw):
      core = unseal(raw)
      fields = {
        'schema',
        'frame',
        'manifest_sha256',
        'tool_sha256',
        'first_suggestion_sha256',
        'first_experiment_sha256',
        'human_annotation_sha256',
        'mode',
        'timestamp',
      }
      if (
        set(core) != fields
        or core['schema'] != 'AI_FIRST_EXPOSURE_V1'
        or core['manifest_sha256'] != self.legacy.manifest['receipt_sha256']
        or core['tool_sha256'] != tool_identity()
        or core['frame'] not in self.legacy.manifest['frames']
        or not is_sha256(core['first_suggestion_sha256'])
        or not is_sha256(core['first_experiment_sha256'])
        or core['mode'] not in ('BLIND_HUMAN_REVIEW', 'ASSISTED_HUMAN_REVIEW')
      ):
        raise ValueError('AI_EXPOSURE_BINDING_MISMATCH')
      if core['mode'] == 'ASSISTED_HUMAN_REVIEW':
        if core['human_annotation_sha256'] is not None or core['frame']['frame_id'] in human:
          raise ValueError('ASSISTED_PROVENANCE_MISMATCH')
      elif human.get(core['frame']['frame_id'], {}).get('receipt_sha256') != core['human_annotation_sha256']:
        raise ValueError('BLIND_HUMAN_ROW_BINDING_MISMATCH')
      return self.legacy.manifest['frames'].index(core['frame'])

    return indexed_rows(self.legacy.output, 'ai-exposures', 'ai-exposure-index.json', self.freeze['receipt_sha256'], validate)

  def assisted_rows(self):
    self.guard()
    exposure = {r['frame']['frame_id']: r for r in self.exposures()}
    canonical_ids = {r['frame_id'] for r in self.legacy.annotations()}

    def validate(raw):
      c.validate_annotation(self.legacy.manifest, raw)
      if raw['frame_id'] in canonical_ids or exposure.get(raw['frame_id'], {}).get('mode') != 'ASSISTED_HUMAN_REVIEW':
        raise ValueError('ASSISTED_ROW_MUST_BE_ISOLATED_AND_EXPOSED')
      return next(i for i, f in enumerate(self.legacy.manifest['frames']) if f['frame_id'] == raw['frame_id'])

    return indexed_rows(self.legacy.output, 'ai-assisted-annotations', 'ai-assisted-index.json', self.freeze['receipt_sha256'], validate)

  def all_human_rows(self):
    rows = self.legacy.annotations() + self.assisted_rows()
    return w.ordered_rows(self.legacy.manifest, rows)

  def export(self):
    return seal(
      {
        'schema': 'AI_AWARE_HUMAN_EXPORT_V1',
        'blind_human_export': self.workflow.export(),
        'assisted_human_rows': self.assisted_rows(),
        'provenance': self.provenance(),
        'ai_progress': self.store.status(),
        'review_manifest_sha256': self.legacy.manifest['receipt_sha256'],
        'blind_independent_complete': len(self.legacy.annotations()) == len(self.legacy.manifest['frames']) and not self.assisted_rows(),
        'private_input_allowed': False,
        'reference_promotable': False,
      }
    )

  def save(self, body):
    self.guard()
    if type(body) is not dict or set(body) != {'index', 'label', 'reviewable', 'comment', 'human_ack', 'token'} or body['token'] != self.legacy.token:
      raise ValueError('EXACT_AUTHORIZED_REVIEW_SAVE_REQUIRED')
    f = self.legacy.frame(body['index'])['data']['frame']
    with s.writer_lease(self.legacy.output):
      if any(r['frame_id'] == f['frame_id'] for r in self.all_human_rows()):
        raise FileExistsError('HUMAN_ANNOTATION_IS_IMMUTABLE')
      exposure = next((r for r in self.exposures() if r['frame'] == f), None)
      assisted = exposure is not None and exposure['mode'] == 'ASSISTED_HUMAN_REVIEW'
      timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
      row = c.make_annotation(
        self.legacy.manifest,
        f['frame_id'],
        label=body['label'],
        reviewable=body['reviewable'],
        comment=body['comment'],
        timestamp=timestamp,
        human_ack=body['human_ack'],
        tool_sha256=ui.tool_identity(),
      )
      directory = 'ai-assisted-annotations' if assisted else 'annotations'
      s.atomic_json(self.legacy.output / directory / f"{body['index']:05d}.json", row)
      if assisted:
        write_index(self.legacy.output, 'ai-assisted-index.json', self.freeze['receipt_sha256'], self.assisted_rows())
      else:
        self.legacy.write_index(self.legacy.annotations())
      return {
        'annotation': row,
        'provenance': 'ASSISTED_HUMAN_REVIEW' if assisted else 'NO_UI_AI_EXPOSURE_BEFORE_SAVE',
        'review_status': c.review_status(self.legacy.manifest, self.legacy.annotations()),
      }

  def public_state(self):
    return {
      'ai_progress': self.store.status(),
      'exposure': self.provenance(),
      'default': 'BLIND_HUMAN_FIRST',
      'suggestions_hidden': True,
      'human_counts': {
        'blind_canonical': len(self.legacy.annotations()),
        'assisted': len(self.assisted_rows()),
        'total': len(self.all_human_rows()),
        'expected': len(self.legacy.manifest['frames']),
      },
    }

  def provenance(self):
    return seal(
      {
        'schema': 'AI_HUMAN_PROVENANCE_V1',
        'review_manifest_sha256': self.legacy.manifest['receipt_sha256'],
        'exposures': self.exposures(),
        'scope_limit': POLICY['scope_limit'],
        'reference_promotable': False,
      }
    )

  def reveal(self, body):
    if (
      type(body) is not dict
      or set(body) != {'index', 'allow_assisted', 'token'}
      or body['token'] != self.legacy.token
      or type(body['allow_assisted']) is not bool
      or type(body['index']) is not int
      or not 0 <= body['index'] < len(self.legacy.manifest['frames'])
    ):
      raise ValueError('AUTHORIZED_EXPLICIT_AI_REVEAL_REQUIRED')
    self.guard()
    f = self.legacy.manifest['frames'][body['index']]
    row = next((r for r in self.store.rows() if r['frame_id'] == f['frame_id']), None)
    if row is None:
      raise ValueError('AI_SUGGESTION_UNAVAILABLE')
    with s.writer_lease(self.legacy.output):
      exposures = self.exposures()
      old = next((r for r in exposures if r['frame'] == f), None)
      if old is None:
        human = next((r for r in self.legacy.annotations() if r['frame_id'] == f['frame_id']), None)
        if human is None and not body['allow_assisted']:
          raise ValueError('ASSISTED_WARNING_ACK_REQUIRED')
        old = seal(
          {
            'schema': 'AI_FIRST_EXPOSURE_V1',
            'frame': f,
            'manifest_sha256': self.legacy.manifest['receipt_sha256'],
            'tool_sha256': tool_identity(),
            'first_suggestion_sha256': row['receipt_sha256'],
            'first_experiment_sha256': self.store.experiment['receipt_sha256'],
            'human_annotation_sha256': None if human is None else human['receipt_sha256'],
            'mode': 'ASSISTED_HUMAN_REVIEW' if human is None else 'BLIND_HUMAN_REVIEW',
            'timestamp': datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
          }
        )
        s.atomic_json(self.legacy.output / 'ai-exposures' / f"{body['index']:05d}.json", old)
      write_index(self.legacy.output, 'ai-exposure-index.json', self.freeze['receipt_sha256'], self.exposures())
    return {'suggestion': row, 'provenance': old, 'tier': 'SUPPORTING_DIAGNOSTIC_ONLY'}

  def comparison(self):
    self.guard()
    human = self.all_human_rows()
    ai = self.store.rows()
    provenance = self.provenance()
    if len(human) != len(self.legacy.manifest['frames']) or len(ai) != len(human):
      return seal(
        {
          'schema': 'AI_HUMAN_COMPARISON_V1',
          'status': 'TAIL_HUMAN_REVIEW_PENDING' if len(human) != len(self.legacy.manifest['frames']) else 'AI_PREREVIEW_PENDING',
          'human_reviewed': len(human),
          'ai_suggestions': len(ai),
          'reference_promotable': False,
        }
      )
    by_id = {r['frame_id']: r for r in ai}
    exposure = {r['frame']['frame_id']: r['mode'] for r in provenance['exposures']}
    matrix = {h: dict.fromkeys(c.LABELS, 0) for h in c.LABELS}
    frames = []
    for h in human:
      suggestion = by_id[h['frame_id']]
      agree = h['reviewer_label'] == suggestion['suggested_label']
      matrix[h['reviewer_label']][suggestion['suggested_label']] += 1
      frames.append(
        {
          'frame_id': h['frame_id'],
          'human_label': h['reviewer_label'],
          'ai_label': suggestion['suggested_label'],
          'human_sha256': h['receipt_sha256'],
          'ai_sha256': suggestion['receipt_sha256'],
          'agreement': agree,
          'ai_confidence': suggestion['ai_confidence'],
          'provenance': exposure.get(h['frame_id'], 'NO_UI_AI_EXPOSURE_RECORDED'),
        }
      )
    count = sum(r['agreement'] for r in frames)
    return seal(
      {
        'schema': 'AI_HUMAN_COMPARISON_V1',
        'status': 'SUPPORTING_DIAGNOSTIC_ONLY',
        'frames': frames,
        'confusion_matrix': matrix,
        'exact_agreements': count,
        'exact_agreement_rate': count / len(human),
        'high_confidence_disagreements': [r['frame_id'] for r in frames if not r['agreement'] and r['ai_confidence'] == 'HIGH'],
        'unresolved_disagreements': [r['frame_id'] for r in frames if not r['agreement'] and 'UNRESOLVED' in (r['human_label'], r['ai_label'])],
        'provenance_sha256': provenance['receipt_sha256'],
        'review_manifest_sha256': self.legacy.manifest['receipt_sha256'],
        'experiment_sha256': self.store.experiment['receipt_sha256'],
        'human_replacement_allowed': False,
        'private_input_allowed': False,
        'reference_promotable': False,
        'scope': self.store.experiment['scope'],
      }
    )

  def finalize(self):
    if any(r['mode'] == 'ASSISTED_HUMAN_REVIEW' for r in self.exposures()):
      raise ValueError('ASSISTED_HUMAN_NOT_BLIND_INDEPENDENT_ATTRIBUTION')
    return self.workflow.finalize()


PAGE = w.PAGE.replace(
  '<script src="/app.js">',
  """<section>
<p>AI_REVIEW_SUGGESTION != HUMAN_REVIEW. Default: BLIND_HUMAN_FIRST.
AI is supporting diagnostic only; not truth or a human replacement.</p>
<p id="ai-counts"></p><button id="ai-show">Show AI pre-review</button>
<div id="ai-warning" hidden><p>AI suggestion을 먼저 보면 이 frame의 review는 independent blind-human evidence가
아니라 assisted-human evidence로 기록됩니다. This immutable exposure cannot be undone.</p>
<button id="ai-continue">Continue as assisted review</button><button id="ai-cancel">Keep blind review</button></div>
<pre id="ai-panel" hidden></pre></section><script src="/app.js">""",
)
SCRIPT = (
  w.SCRIPT
  + """
async function revealAI(allow,indexAtRequest=index,version=loading){
 const x=await request('/api/ai-reveal',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({index:indexAtRequest,allow_assisted:allow,token:config.token})});
 if(indexAtRequest!==index||version!==loading)return;
 $('ai-warning').hidden=true;$('ai-panel').hidden=false;
 $('ai-panel').textContent=JSON.stringify({tier:x.tier,mode:x.provenance.mode,
 suggested_label:x.suggestion.suggested_label,secondary_possible_labels:x.suggestion.secondary_possible_labels,
 confidence:x.suggestion.ai_confidence,reason:x.suggestion.reasoning_summary,
 evidence:x.suggestion.visual_evidence,human_label:null,suggestion_sha256:x.suggestion.receipt_sha256},null,2);
}
const workflowLoad=load;
load=async i=>{const expected=Math.max(0,Math.min(config.frames.length-1,i));
 $('ai-panel').hidden=true;$('ai-panel').textContent='';$('ai-warning').hidden=true;
 await workflowLoad(i);if(index!==expected)return;
 const aiState=await request('/api/ai-state');if(index!==expected)return;
 $('ai-counts').textContent='Canonical human '+aiState.human_counts.blind_canonical+' | Assisted human '+
 aiState.human_counts.assisted+' | Total '+aiState.human_counts.total+'/'+aiState.human_counts.expected+
 ' | Assisted rows excluded from blind final attribution';
 if(current.annotation){try{await revealAI(false);}catch(e){$('ai-panel').hidden=true;showError(e);}}};
$('ai-show').onclick=()=>{if(current.annotation)revealAI(false).catch(showError);else $('ai-warning').hidden=false;};
$('ai-continue').onclick=()=>revealAI(true).catch(showError);
$('ai-cancel').onclick=()=>{$('ai-warning').hidden=true;};
"""
)


def make_server(session, *, host='127.0.0.1', port=0):
  server = w.make_server(session.workflow, host=host, port=port)
  parent = server.RequestHandlerClass

  class Handler(parent):
    def do_GET(self):
      if not self.authorized():
        self.reply(403, {'error': 'LOOPBACK_HOST_REQUIRED'})
        return
      try:
        session.assisted_rows()
        if self.path == '/':
          self.reply(200, PAGE, 'text/html; charset=utf-8')
        elif self.path == '/app.js':
          self.reply(200, SCRIPT, 'text/javascript; charset=utf-8')
        elif self.path == '/api/ai-state':
          self.reply(200, session.public_state())
        elif self.path == '/api/export':
          self.reply(200, session.export())
        elif self.path.startswith('/api/frame/'):
          ordinal = self.ordinal('/api/frame/')
          value = session.legacy.frame(ordinal)['data']
          value['annotation'] = next((r for r in session.all_human_rows() if r['frame_id'] == value['frame']['frame_id']), None)
          self.reply(200, value)
        elif self.path == '/api/ai-comparison':
          self.reply(200, session.comparison())
        elif self.path == '/api/final-attribution':
          self.reply(200, session.finalize())
        else:
          super().do_GET()
      except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        self.reply(400, {'error': str(exc)})

    def do_POST(self):
      if not self.authorized(post=True):
        self.reply(403, {'error': 'SAME_ORIGIN_REQUIRED'})
        return
      try:
        session.assisted_rows()
        if self.path not in ('/api/ai-reveal', '/api/save'):
          super().do_POST()
          return
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 16384 or self.headers.get('Content-Type') != 'application/json':
          raise ValueError('BOUNDED_JSON_BODY_REQUIRED')
        body = json.loads(self.rfile.read(length))
        if type(body) is not dict or body.get('token') != session.legacy.token:
          self.reply(403, {'error': 'REVIEW_NONCE_REQUIRED'})
          return
        self.reply(200, session.reveal(body) if self.path == '/api/ai-reveal' else session.save(body))
      except FileExistsError as exc:
        self.reply(409, {'error': str(exc)})
      except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        self.reply(400, {'error': str(exc)})

  server.RequestHandlerClass = Handler
  return server


def main():
  parser = argparse.ArgumentParser()
  for name in ('run', 'cache', 'manifest', 'output', 'ai'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  manifest = s.read_json(args.manifest)
  legacy = ui.open_public_review(args.run, args.cache, manifest, args.output)
  workflow = w.WorkflowSession(legacy, w.bound_metric_loader(args.run, args.cache, manifest))
  experiment = s.read_json(args.ai / 'experiment-freeze.json')
  session = AIReviewSession(workflow, SuggestionStore(manifest, experiment, args.ai))
  server = make_server(session, port=args.port)
  print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port), 'ai': session.store.status(), 'human': workflow.progress()}), flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
