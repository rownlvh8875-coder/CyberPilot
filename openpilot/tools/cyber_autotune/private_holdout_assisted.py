"""Separate raw-vision drafts and explicit assisted-human receipts.

This tier never becomes blind or independent truth. Source hashes attest bytes,
not semantic correctness or actual model execution; raw vision observations
require an honestly recorded native tool invocation by the authorized operator.
"""
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden

ACTIONS = ('ACCEPT_AI', 'MODIFY_AI', 'REJECT_AI', 'AMBIGUOUS')
POLICY = {
  'schema': 'RAW_VISION_ASSISTED_PIXEL_POLICY_V1',
  'input': 'EXACT_RAW_ORIGINAL_IMAGE_ONLY',
  'forbidden': ['CLRerNet', 'modelV2', 'planner', 'candidate', 'steering', 'chat_visibility_labels'],
  'coordinates': h.COORDINATES,
  'visible_span_only': True, 'extrapolation': False,
  'states': list(h.STATES), 'confidence': ['HIGH', 'MEDIUM', 'LOW'],
  'prompt': ('Inspect raw pixels only. Mark visible ego left/right boundaries with 3-12 original-pixel points ordered near-to-far. ' +
            'Do not extend invisible paint. Use ambiguous/unreviewable and no points when identity is uncertain. ' +
            'Provide a short observable reason; never use detector, model, planner or controller output.'),
  'privacy': 'USER_AUTHORIZED_CODEX_NATIVE_VISION_THIS_EXPERIMENT_ONLY_NO_OTHER_UPLOAD_OR_PUBLICATION',
  'human_final': 'EXPLICIT_ACCEPT_MODIFY_REJECT_AMBIGUOUS_IMMUTABLE_SEPARATE_RECEIPT',
  **h.FIREWALL,
}
MODEL = {'provider': 'OPENAI_CODEX_SESSION', 'model': 'SESSION_ASSISTANT',
         'version': 'EXACT_DEPLOYMENT_VERSION_NOT_EXPOSED',
         'vision_tool': 'NATIVE_VIEW_IMAGE', 'identity_limit': 'OPERATOR_ATTESTATION_NOT_REMOTE_EXECUTION_PROOF'}


def sources():
  names = ('private_holdout_assisted.py', 'private_holdout_assisted_review.py')
  return {name: h.digest((Path(__file__).parent / name).read_bytes()) for name in names}


def authorize(package, branch_sha, timestamp, *, acknowledged):
  hidden.validate_package(package)
  if acknowledged is not True or re.fullmatch('[0-9a-f]{40}', branch_sha or '') is None:
    raise ValueError('EXPLICIT_ASSISTED_RAW_VISION_AUTHORIZATION_REQUIRED')
  if h.c.utc(timestamp) < h.c.utc(package['authorization']['authorized_at']):
    raise ValueError('ASSISTED_AUTHORIZATION_MUST_FOLLOW_MATERIALIZATION_AUTHORIZATION')
  return h.seal({'schema': 'PRIVATE_ASSISTED_RAW_VISION_AUTHORIZATION_V1',
                 'materialization_sha256': package['receipt_sha256'],
                 'holdout_selection_sha256': package['authorization']['holdout_selection_sha256'],
                 'sample_ids': [im['sample_id'] for im in package['images']],
                 'branch_sha': branch_sha, 'authorized_at': timestamp,
                 'source_identity': sources(), 'policy_sha256': h.digest(h.canonical(POLICY)),
                 'model_identity': MODEL, 'detector_input_allowed': False,
                 'human_verified': False, 'blind_human': False, **h.FIREWALL})


def require_auth(package, auth):
  if type(auth) is not dict:
    raise ValueError('ASSISTED_AUTHORIZATION_REQUIRED')
  h.unseal(auth)
  expected = authorize(package, auth['branch_sha'], auth['authorized_at'], acknowledged=True)
  if h.canonical(expected) != h.canonical(auth):
    raise ValueError('EXACT_ASSISTED_AUTHORIZATION_AND_SOURCE_REQUIRED')


def geometry(image, body):
  if body['state'] not in h.STATES:
    raise ValueError('KNOWN_VISIBLE_STATE_REQUIRED')
  for side in ('left', 'right'):
    h.validate_points(body[side], image['width'], image['height'])
  sides = {'BOTH_EGO_BOUNDARIES_VISIBLE': (True, True), 'LEFT_ONLY_VISIBLE': (True, False),
           'RIGHT_ONLY_VISIBLE': (False, True)}.get(body['state'], (False, False))
  if tuple(bool(body[k]) for k in ('left', 'right')) != sides:
    raise ValueError('STATE_AND_OBSERVED_BOUNDARIES_REQUIRED')
  if all(sides):
    ys = h.common_rows(body['left'], body['right'])
    if not ys or any(l >= r for l, r in zip(h.interpolate(body['left'], ys), h.interpolate(body['right'], ys), strict=True)):
      raise ValueError('LEFT_RIGHT_CROSSING_OR_NO_COMMON_SUPPORT')


def ai_row(package, auth, ordinal, body, timestamp, *, observation_id):
  require_auth(package, auth)
  image = hidden.image(package, ordinal)
  h.c.exact(body, ('state', 'left', 'right', 'reason', 'confidence'))
  geometry(image, body)
  if body['confidence'] not in POLICY['confidence'] or not isinstance(body['reason'], str) or not 1 <= len(body['reason']) <= 1000:
    raise ValueError('OBSERVABLE_REASON_AND_DISCRETE_CONFIDENCE_REQUIRED')
  if not isinstance(observation_id, str) or not 1 <= len(observation_id) <= 160:
    raise ValueError('ACTUAL_RAW_VISION_TOOL_OBSERVATION_ID_REQUIRED')
  if h.c.utc(timestamp) < h.c.utc(auth['authorized_at']):
    raise ValueError('VISION_MUST_FOLLOW_AUTHORIZATION')
  return h.seal({'schema': 'PRIVATE_RAW_VISION_PIXEL_DRAFT_V1', 'sample_id': image['sample_id'],
                 'image_sha256': image['image_sha256'], 'image_receipt_sha256': image['receipt_sha256'],
                 'materialization_sha256': package['receipt_sha256'], 'ordinal': ordinal,
                 'authorization_sha256': auth['receipt_sha256'], 'policy_sha256': auth['policy_sha256'],
                 'source_identity': sources(), 'model_identity': MODEL, 'observation_id': observation_id,
                 'generated_at': timestamp, 'width': image['width'], 'height': image['height'],
                 'coordinate_policy': h.COORDINATES, 'generation_input_roles': ['RAW_ORIGINAL_IMAGE'],
                 'ai_generated': True, 'human_verified': False, 'blind_human': False, 'assisted_human': False,
                 'human_annotation': None, **body, **h.FIREWALL})


def validate_ai(package, auth, ordinal, row):
  h.unseal(row)
  body = {key: row[key] for key in ('state', 'left', 'right', 'reason', 'confidence')}
  expected = ai_row(package, auth, ordinal, body, row['generated_at'], observation_id=row['observation_id'])
  if h.canonical(row) != h.canonical(expected):
    raise ValueError('EXACT_RAW_VISION_DRAFT_REQUIRED')


def human_row(package, auth, ordinal, ai, body, timestamp):
  validate_ai(package, auth, ordinal, ai)
  h.c.exact(body, ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment'))
  image = hidden.image(package, ordinal)
  geometry(image, body)
  if body['action'] not in ACTIONS or body['acknowledged_assisted'] is not True:
    raise ValueError('EXPLICIT_ASSISTED_HUMAN_DECISION_REQUIRED')
  if re.fullmatch('[A-Za-z0-9_-]{1,48}', body['reviewer_id'] or '') is None or not isinstance(body['comment'], str) or len(body['comment']) > 1000:
    raise ValueError('OPAQUE_REVIEWER_AND_BOUNDED_COMMENT_REQUIRED')
  equal = all(body[k] == ai[k] for k in ('state', 'left', 'right'))
  if body['action'] == 'ACCEPT_AI' and not equal:
    raise ValueError('ACCEPT_CANNOT_HIDE_MODIFICATION')
  if body['action'] == 'MODIFY_AI' and equal:
    raise ValueError('MODIFY_REQUIRES_ACTUAL_CHANGE')
  if body['action'] in ('REJECT_AI', 'AMBIGUOUS') and (body['left'] or body['right']):
    raise ValueError('REJECT_OR_AMBIGUOUS_NOT_LOCALIZATION_REFERENCE')
  if h.c.utc(timestamp) < h.c.utc(ai['generated_at']):
    raise ValueError('HUMAN_MUST_FOLLOW_AI_DRAFT')
  return h.seal({'schema': 'PRIVATE_ASSISTED_HUMAN_PIXEL_DECISION_V1',
                 'sample_id': image['sample_id'], 'image_sha256': image['image_sha256'],
                 'image_receipt_sha256': image['receipt_sha256'], 'ordinal': ordinal,
                 'ai_receipt_sha256': ai['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256'],
                 'width': image['width'], 'height': image['height'], 'coordinate_policy': h.COORDINATES,
                 'ai_generated': True, 'human_verified': True, 'assisted_human': True, 'blind_human': False,
                 'ai_exposed_before_human': True, 'detector_exposed_before_human': False,
                 'source_identity': sources(), 'saved_at': timestamp, **body, **h.FIREWALL})


def validate_human(package, auth, ordinal, ai, row):
  h.unseal(row)
  body = {key: row[key] for key in ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment')}
  expected = human_row(package, auth, ordinal, ai, body, row['saved_at'])
  if h.canonical(row) != h.canonical(expected):
    raise ValueError('EXACT_SEPARATE_ASSISTED_HUMAN_RECEIPT_REQUIRED')


def freeze(package, auth, ai_rows, human_rows, timestamp):
  require_auth(package, auth)
  if len(ai_rows) != h.EXPECTED or len(human_rows) != h.EXPECTED:
    raise ValueError('SIXTY_AI_AND_EXPLICIT_HUMAN_DECISIONS_REQUIRED')
  for i, (ai, human) in enumerate(zip(ai_rows, human_rows, strict=True)):
    validate_human(package, auth, i, ai, human)
    if h.c.utc(timestamp) < h.c.utc(human['saved_at']):
      raise ValueError('SET_FREEZE_MUST_FOLLOW_HUMAN')
  return h.seal({'schema': 'AI_ASSISTED_HUMAN_PIXEL_REFERENCE_V1',
                 'status': 'ASSISTED_HUMAN_VERIFICATION_COMPLETE_QUALIFICATION_BLOCKED',
                 'materialization_sha256': package['receipt_sha256'],
                 'authorization_sha256': auth['receipt_sha256'], 'frozen_at': timestamp,
                 'ai_receipts': [r['receipt_sha256'] for r in ai_rows], 'annotations': human_rows,
                 'action_counts': {key: sum(r['action'] == key for r in human_rows) for key in ACTIONS},
                 'state_counts': {key: sum(r['state'] == key for r in human_rows) for key in h.STATES},
                 'blind_human': False, 'assisted_human': True,
                 'evaluation_policy': h.EVALUATION_POLICY, **h.FIREWALL})


def evaluate(package, auth, ai_rows, reference, detector_auth, predictions):
  """Same frozen pixel math; new assisted receipt, never a blind receipt."""
  from openpilot.tools.cyber_autotune import private_holdout_pixel_metrics as math
  h.unseal(reference)
  expected = freeze(package, auth, ai_rows, reference['annotations'], reference['frozen_at'])
  if h.canonical(reference) != h.canonical(expected) or len(predictions) != h.EXPECTED:
    raise ValueError('EXACT_COMPLETED_ASSISTED_SET_AND_SIXTY_DETECTOR_ROWS_REQUIRED')
  left, right, center = [], [], []
  unavailable = {'left': 0, 'right': 0}
  visible = {'left': 0, 'right': 0}
  both_visible, both_matched, evaluable, unmatched = 0, 0, 0, 0
  for i, (human, row) in enumerate(zip(reference['annotations'], predictions, strict=True)):
    hidden.validate_detector_row(package, detector_auth, i, row)
    if not human['left'] and not human['right']:
      continue
    evaluable += 1
    lanes = row['prediction']['lanes']
    matched = math.assignment(human, lanes)
    unmatched += len(lanes) - len(matched)
    for side, errors in (('left', left), ('right', right)):
      if human[side]:
        visible[side] += 1
        if side in matched:
          errors.extend(matched[side][1][2])
        else:
          unavailable[side] += 1
    if human['state'] == 'BOTH_EGO_BOUNDARIES_VISIBLE':
      both_visible += 1
      if set(matched) == {'left', 'right'}:
        both_matched += 1
        ls, rs = [lanes[matched[k][0]]['points'] for k in ('left', 'right')]
        detector_ys = h.common_rows(ls, rs, integer=True)
        detector_center = [[(l + r) / 2, y] for l, r, y in
                           zip(h.interpolate(ls, detector_ys), h.interpolate(rs, detector_ys), detector_ys, strict=True)]
        human_ys = h.common_rows(human['left'], human['right'], integer=True)
        human_center = [[(l + r) / 2, y] for l, r, y in
                        zip(h.interpolate(human['left'], human_ys), h.interpolate(human['right'], human_ys), human_ys, strict=True)]
        ys = h.common_rows(human_center, detector_center, integer=True)
        if ys:
          center.extend(abs(l - r) for l, r in zip(h.interpolate(human_center, ys), h.interpolate(detector_center, ys), strict=True))
  return h.seal({'schema': 'AI_ASSISTED_PRIVATE_HOLDOUT_EVALUATION_V1',
                 'status': 'DIAGNOSTIC_COMPLETE_QUALIFICATION_BLOCKED', 'total_frames': h.EXPECTED,
                 'human_assisted_reference_sha256': reference['receipt_sha256'],
                 'detector_receipts_sha256': h.digest(h.canonical([r['receipt_sha256'] for r in predictions])),
                 'evaluation_policy': h.EVALUATION_POLICY, 'source_identity': sources(),
                 'evaluable_visible_boundary_frames': evaluable, 'excluded_frames': h.EXPECTED - evaluable,
                 'visible_boundary_denominators': visible, 'both_visible_denominator': both_visible,
                 'both_boundary_geometry_match_frames': both_matched,
                 'both_boundary_geometry_coverage': both_matched / both_visible if both_visible else None,
                 'left_unavailable_visible_frames': unavailable['left'], 'right_unavailable_visible_frames': unavailable['right'],
                 'unmatched_detector_lanes_not_false_positive_truth': unmatched,
                 'matching_limitation': 'MAX_Y_OVERLAP_MATCH_COUNT_THEN_PIXEL_COST_NOT_SEMANTIC_ASSOCIATION_QUALIFICATION',
                 'left': math.distribution(left), 'right': math.distribution(right),
                 'combined': math.distribution(left + right), 'center': math.distribution(center),
                 'pooling': 'OBSERVED_COMMON_INTEGER_ROWS_POINT_WEIGHTED',
                 'state_counts': reference['state_counts'], 'action_counts': reference['action_counts'],
                 'threshold': 'UNJUSTIFIED_NO_ACCEPT_REJECT_VERDICT',
                 'blind_human': False, 'assisted_human': True, **h.FIREWALL})
