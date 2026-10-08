"""V2 authority: compute frozen detector privately, reveal only after first save.

Existing materialization/first decisions and all-sixty metric freeze stay intact.
Computed-before does not imply exposed-before. Hashes bind declared provenance.
"""
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_pixel_metrics as metrics
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import lane_detector_runner as detector
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

POLICY = {'schema': 'PRIVATE_HOLDOUT_HIDDEN_OUTPUT_POLICY_V1',
          'computation': 'EXACT_FROZEN_DETECTOR_ON_ORIGINAL_SIXTY_ONLY',
          'reveal': 'THIS_FRAME_IMMUTABLE_BLIND_FIRST_DECISION_REQUIRED',
          'before_save': 'RAW_IMAGE_AND_HUMAN_DRAWING_ONLY_SERVER_SIDE_403',
          'evaluation': 'ALL_SIXTY_BLIND_FIRST_DECISIONS_AND_REFERENCE_FREEZE',
          'ai': 'OPTIONAL_ACTUAL_LOCAL_VISION_ONLY_NOT_METRIC_HEURISTIC',
          'tuning': 'FORBIDDEN', 'external_upload': False, **h.FIREWALL}
PROMPT = ('Observe the actual original image and detector overlay locally. Suggest only a frozen visibility state; ' +
          'if ambiguous use EGO_BOUNDARIES_AMBIGUOUS or UNREVIEWABLE. Report a short observable reason, ' +
          'not hidden reasoning. Do not generate human polylines, tuning, thresholds or qualification.')


def source_identity():
  return {name: digest((Path(__file__).parent / name).read_bytes()) for name in
          ('private_holdout_hidden.py', 'private_holdout_hidden_runner.py', 'private_holdout_hidden_review.py')}


def validate_package(package):
  unseal(package)
  expected = h.materialization_complete(package['frozen_manifest'], package['authorization'], package['images'])
  if canonical(package) != canonical(expected):
    raise ValueError('EXACT_HISTORICAL_MATERIALIZATION_REQUIRED')


def authorize(package, head, timestamp, *, acknowledged):
  validate_package(package)
  if acknowledged is not True or re.fullmatch('[0-9a-f]{40}', head or '') is None:
    raise ValueError('SEPARATE_HIDDEN_INFERENCE_AUTHORIZATION_REQUIRED')
  if h.c.utc(timestamp) < h.c.utc(package['authorization']['authorized_at']):
    raise ValueError('HIDDEN_AUTHORIZATION_AFTER_MATERIALIZATION_AUTHORITY_REQUIRED')
  return seal({'schema': 'PRIVATE_HOLDOUT_HIDDEN_INFERENCE_AUTHORIZATION_V1',
               'materialization_sha256': package['receipt_sha256'],
               'holdout_selection_sha256': package['authorization']['holdout_selection_sha256'],
               'branch_commit_sha': head, 'authorized_at': timestamp, 'expected': h.EXPECTED,
               'detector': package['authorization']['detector'], 'source_identity': source_identity(),
               'policy_sha256': digest(canonical(POLICY)), 'prompt_sha256': digest(PROMPT.encode()),
               'explicit_user_authorization': True, 'raw_publication': False, **h.FIREWALL})


def require_execution(package, auth):
  if type(auth) is not dict:
    raise ValueError('SEPARATE_HIDDEN_INFERENCE_AUTHORITY_REQUIRED')
  unseal(auth)
  if canonical(auth) != canonical(authorize(package, auth['branch_commit_sha'], auth['authorized_at'], acknowledged=True)):
    raise ValueError('HIDDEN_SOURCE_CONFIG_INPUT_POLICY_MISMATCH')


def image(package, ordinal):
  if type(ordinal) is not int or not 0 <= ordinal < h.EXPECTED:
    raise ValueError('ORIGINAL_HOLDOUT_ORDINAL_REQUIRED')
  return package['images'][ordinal]


def guarded_input(package, auth, ordinal, opener):
  require_execution(package, auth)
  image(package, ordinal)
  return opener()


def detector_row(package, auth, ordinal, first, second, timestamp):
  require_execution(package, auth)
  im = image(package, ordinal)
  if h.c.utc(timestamp) < h.c.utc(auth['authorized_at']):
    raise ValueError('INFERENCE_AFTER_AUTHORIZATION_REQUIRED')
  p.validate_prediction(first, [im['height'], im['width']])
  p.validate_prediction(second, [im['height'], im['width']])
  detector.require_repeatability(first, second)
  return seal({'schema': 'PRIVATE_HOLDOUT_HIDDEN_DETECTOR_ROW_V1',
               'sample_id': im['sample_id'], 'image_sha256': im['image_sha256'],
               'image_receipt_sha256': im['receipt_sha256'], 'ordinal': ordinal,
               'authorization_sha256': auth['receipt_sha256'], 'detector': auth['detector'],
               'computed_at': timestamp, 'prediction': first, 'prediction_sha256': digest(canonical(first)),
               'exact_repeatability': True, 'human_annotation': None,
               'evidence_role': 'HIDDEN_COMPARISON_ONLY_NOT_HUMAN_REFERENCE', **h.FIREWALL})


def validate_detector_row(package, auth, ordinal, row):
  unseal(row)
  expected = detector_row(package, auth, ordinal, row['prediction'], row['prediction'], row['computed_at'])
  if canonical(row) != canonical(expected):
    raise ValueError('HIDDEN_DETECTOR_ROW_BINDING_MISMATCH')


def complete(package, auth, rows):
  require_execution(package, auth)
  if type(rows) is not list or len(rows) != h.EXPECTED:
    raise ValueError('SIXTY_EXACT_HIDDEN_ROWS_REQUIRED')
  for ordinal, row in enumerate(rows):
    validate_detector_row(package, auth, ordinal, row)
  return seal({'schema': 'PRIVATE_HIDDEN_DETECTOR_COMPLETE_V1', 'status': 'HIDDEN_DETECTOR_INFERENCE_COMPLETE',
               'authorization_sha256': auth['receipt_sha256'], 'processed': h.EXPECTED,
               'row_receipt_sha256': [r['receipt_sha256'] for r in rows],
               'repeatability': 'PASS', 'human_evaluation': 'NOT_RUN', **h.FIREWALL})


def ai_row(package, auth, prediction, state, reason, confidence, model, timestamp):
  ordinal = prediction['ordinal']
  validate_detector_row(package, auth, ordinal, prediction)
  if state not in h.STATES or confidence not in ('HIGH', 'MEDIUM', 'LOW'):
    raise ValueError('FROZEN_VISIBILITY_STATE_AND_SUGGESTION_CONFIDENCE_REQUIRED')
  if type(reason) is not str or not 1 <= len(reason) <= 600:
    raise ValueError('SHORT_OBSERVABLE_VISUAL_SUMMARY_REQUIRED')
  h.c.exact(model, ('provider', 'model', 'version', 'weight_sha256', 'environment_sha256'))
  if model['provider'] != 'LOCAL_ONLY' or any(type(model[k]) is not str or not 1 <= len(model[k]) <= 120 for k in ('model', 'version')):
    raise ValueError('LOCAL_VERIFIED_VISION_IDENTITY_REQUIRED_NO_UPLOAD')
  for key in ('weight_sha256', 'environment_sha256'):
    h.c.sha(model[key])
  if h.c.utc(timestamp) < h.c.utc(prediction['computed_at']):
    raise ValueError('AI_REVIEW_AFTER_BOUND_PREDICTION_REQUIRED')
  return seal({'schema': 'PRIVATE_HOLDOUT_AI_PREREVIEW_V1',
               'sample_id': prediction['sample_id'], 'image_sha256': prediction['image_sha256'],
               'detector_prediction_sha256': prediction['receipt_sha256'],
               'suggested_state': state, 'observable_reason': reason, 'ai_confidence': confidence,
               'model_identity': model, 'prompt_sha256': auth['prompt_sha256'],
               'review_tool_sha256': source_identity()['private_holdout_hidden.py'], 'computed_at': timestamp,
               'human_annotation': None, 'evidence_role': 'DECLARATION_ONLY_EXECUTION_UNVERIFIED',
               'execution_status': 'AI_VISION_EXECUTION_UNVERIFIED',
               'actual_vision_input_required': True, **h.FIREWALL})


def validate_ai(package, auth, prediction, row):
  unseal(row)
  expected = ai_row(package, auth, prediction, row['suggested_state'], row['observable_reason'],
                    row['ai_confidence'], row['model_identity'], row['computed_at'])
  if canonical(row) != canonical(expected):
    raise ValueError('AI_SUGGESTION_BINDING_OR_NULL_HUMAN_REQUIRED')


def require_ai_execution(_row):
  # A declaration/hash is not proof that a local model saw the bound image.
  # No frozen local vision runner exists in this generation. A new versioned
  # experiment with verified runtime/input execution is required to open this gate.
  raise ValueError('AI_VISION_EXECUTION_UNVERIFIED')


def first_relation(package, auth, ordinal, first, prediction, ai):
  if type(first) is not dict:
    raise ValueError('IMMUTABLE_HUMAN_FIRST_DECISION_REQUIRED_BEFORE_REVEAL')
  unseal(first)
  body = {k: first[k] for k in ('state', 'left', 'right', 'acknowledged_blind', 'reviewer_id')}
  if canonical(first) != canonical(h.annotation(image(package, ordinal), body, first['saved_at'])):
    raise ValueError('EXACT_FIRST_DECISION_BINDING_REQUIRED')
  validate_detector_row(package, auth, ordinal, prediction)
  if ai is not None:
    validate_ai(package, auth, prediction, ai)
    require_ai_execution(ai)
  saved = h.c.utc(first['saved_at'])
  return seal({'schema': 'PRIVATE_BLIND_FIRST_HIDDEN_OUTPUT_RELATION_V1',
               'first_decision_sha256': first['receipt_sha256'], 'detector_row_sha256': prediction['receipt_sha256'],
               'ai_row_sha256': ai['receipt_sha256'] if ai is not None else None,
               'blind_human_review': True, 'detector_computed_before_human': h.c.utc(prediction['computed_at']) <= saved,
               'ai_computed_before_human': ai is not None and h.c.utc(ai['computed_at']) <= saved,
               'detector_exposed_before_human': False, 'ai_exposed_before_human': False,
               'ai_status': 'COMPUTED' if ai is not None else 'NOT_RUN',
               'provenance_scope': 'THIS_FRAME_FIRST_DECISION_NOT_SECOND_REVIEWER_VALIDATION',
               'review_wrapper_source_sha256': source_identity()['private_holdout_hidden_review.py'], **h.FIREWALL})


def evaluate(package, auth, reference, rows, ai_rows):
  # This path can never substitute suggestions/predictions for sixty human decisions.
  h.require_detector_gate(package, reference)
  completion = complete(package, auth, rows)
  if ai_rows:
    require_ai_execution(ai_rows)
  left, right, center = [], [], []
  unavailable = {'left': 0, 'right': 0}
  states = dict.fromkeys(h.STATES, 0)
  evaluable, both, unmatched, unsupported = 0, 0, 0, 0
  for human, row in zip(reference['annotations'], rows, strict=True):
    states[human['state']] += 1
    lanes = row['prediction']['lanes']
    if not human['left'] and not human['right']:
      continue
    evaluable += 1
    matches = metrics.assignment(human, lanes)
    unmatched += len(lanes) - len(matches)
    unsupported += sum(not any(h.common_rows(human[s], lane['points'], integer=True) for s in ('left', 'right') if human[s])
                       for lane in lanes)
    for side, pool in (('left', left), ('right', right)):
      if human[side]:
        if side in matches:
          pool.extend(matches[side][1][2])
        else:
          unavailable[side] += 1
    if human['state'] == 'BOTH_EGO_BOUNDARIES_VISIBLE' and set(matches) == {'left', 'right'}:
      both += 1
      a, b = [lanes[matches[s][0]]['points'] for s in ('left', 'right')]
      ys = h.common_rows(a, b, integer=True)
      detector_center = [[(l + r) / 2, y] for l, r, y in zip(h.interpolate(a, ys), h.interpolate(b, ys), ys, strict=True)] if ys else []
      human_center = h.pixel_center(human)
      common = h.common_rows(human_center, detector_center, integer=True)
      center.extend(abs(a - b) for a, b in zip(h.interpolate(human_center, common), h.interpolate(detector_center, common), strict=True))
  ai = {'status': 'AI_NOT_RUN'}
  if ai_rows:
    if len(ai_rows) != h.EXPECTED:
      raise ValueError('AI_COMPARISON_REQUIRES_ALL_SIXTY_BOUND_SUGGESTIONS')
    matrix = {s: dict.fromkeys(h.STATES, 0) for s in h.STATES}
    confidence = {s: {'count': 0, 'agree': 0} for s in ('HIGH', 'MEDIUM', 'LOW')}
    agreements = 0
    for human, prediction, suggestion in zip(reference['annotations'], rows, ai_rows, strict=True):
      validate_ai(package, auth, prediction, suggestion)
      agree = human['state'] == suggestion['suggested_state']
      agreements += agree
      matrix[human['state']][suggestion['suggested_state']] += 1
      confidence[suggestion['ai_confidence']]['count'] += 1
      confidence[suggestion['ai_confidence']]['agree'] += agree
    ai = {'status': 'BLIND_FIRST_HUMAN_AI_STATE_CONCORDANCE_DIAGNOSTIC', 'agreement_count': agreements,
          'agreement_rate': agreements / h.EXPECTED, 'confusion_matrix': matrix, 'confidence': confidence,
          'ai_accuracy_qualification': False}
  return seal({'schema': 'PRIVATE_HIDDEN_OUTPUT_HUMAN_PIXEL_DIAGNOSTIC_V1',
               'status': 'DIAGNOSTIC_COMPLETE_QUALIFICATION_BLOCKED', 'human_frames': h.EXPECTED,
               'human_reference_sha256': reference['receipt_sha256'], 'hidden_completion_sha256': completion['receipt_sha256'],
               'state_counts': states, 'evaluable_visible_boundary_frames': evaluable,
               'both_boundary_geometry_match_frames': both, 'left_unavailable_visible_frames': unavailable['left'],
               'right_unavailable_visible_frames': unavailable['right'], 'unmatched_lanes_not_false_positive_truth': unmatched,
               'unsupported_no_y_overlap_lanes': unsupported, 'left': metrics.distribution(left),
               'right': metrics.distribution(right), 'combined': metrics.distribution(left + right),
               'center': metrics.distribution(center), 'ai_comparison': ai, 'units': 'ORIGINAL_IMAGE_PIXELS',
               'pooling': 'COMMON_OBSERVED_INTEGER_ROWS_POINT_WEIGHTED', 'matching_policy': h.EVALUATION_POLICY,
               'public_comparison': 'DISTINCT_ALL_MARKING_AND_EGO_BOUNDARY_TARGETS', **h.FIREWALL})
