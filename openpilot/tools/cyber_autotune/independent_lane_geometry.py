"""Independent proposal/registration contracts; only constructed fixtures yield meter points."""

import math
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.camera_calibration_evidence import seal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

FLAGS = ('modelv2_used', 'planner_used', 'candidate_used', 'steering_command_used')
CONTEXT = ('merge', 'split', 'intersection', 'markings_inconsistent', 'outside_validated_range')
POLICY = {
  'schema': 'INDEPENDENT_EGO_ASSOCIATION_POLICY_V1',
  'algorithm': 'EXPLICIT_INDEPENDENT_PROPOSALS_ONLY_NO_NEAREST_SIDE_RULE',
  'ambiguous_context': list(CONTEXT),
  'forbidden_sources': list(FLAGS),
  'interpolation': False,
  'previous_frame_carry': False,
  'validation': 'INDEPENDENT_EGO_GT_AND_DOMAIN_VALIDATION_PENDING',
  'reference_promotable': False,
}


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'calibration_source': c.identity(), 'policy': POLICY}))


def ego_contract():
  return seal(
    {
      'schema': 'INDEPENDENT_EGO_ASSOCIATION_V1',
      'status': 'ALGORITHM_DEFINED',
      'validation': 'VALIDATION_PENDING',
      'policy': POLICY,
      'tool_sha256': identity(),
      'ego_association_validated': False,
      'reference_promotable': False,
    }
  )


def clean_sources(value):
  for key in FLAGS:
    if value[key] is not False:
      raise ValueError('CONTAMINATED_ASSOCIATION_SOURCE')


def assess_pair(markings, evidence):
  c.exact(markings, ('scope', 'source_role', 'source_sha256', 'resolution_wh', 'markings', *FLAGS))
  c.exact(evidence, ('method', 'source_sha256', 'direction_evidence_sha256', 'pairs', 'context', *FLAGS))
  clean_sources(markings)
  clean_sources(evidence)
  if markings['scope'] not in ('TEST_ONLY', 'INDEPENDENT_IMAGE_DIAGNOSTIC') or markings['source_role'] != 'INDEPENDENT_DETECTOR':
    raise ValueError('INDEPENDENT_MARKING_DIAGNOSTIC_REQUIRED')
  if evidence['method'] not in ('INDEPENDENT_HUMAN_PROPOSAL', 'SURVEYED_ROAD_TOPOLOGY'):
    raise ValueError('EXPLICIT_INDEPENDENT_PROPOSAL_REQUIRED')
  for value in (markings['source_sha256'], evidence['source_sha256'], evidence['direction_evidence_sha256']):
    c.sha(value)
  wh = markings['resolution_wh']
  if type(wh) is not list or len(wh) != 2 or any(type(v) is not int or v <= 0 for v in wh):
    raise ValueError('EXACT_IMAGE_GEOMETRY_REQUIRED')
  if type(markings['markings']) is not list:
    raise ValueError('MARKING_LIST_REQUIRED')
  lines = {}
  for line in markings['markings']:
    c.exact(line, ('id', 'points'))
    if type(line['id']) is not str or not line['id'] or line['id'] in lines:
      raise ValueError('UNIQUE_MARKING_IDS_REQUIRED')
    points = p._array(line['points'], (len(line['points']), 2))
    if len(points) < 2 or any(x < 0 or x >= wh[0] or y < 0 or y >= wh[1] for x, y in points) or len(set(points[:, 1])) != len(points):
      raise ValueError('VALID_ORIGINAL_PIXEL_POLYLINE_REQUIRED')
    lines[line['id']] = {float(y): float(x) for x, y in points}
  c.exact(evidence['context'], CONTEXT)
  if any(type(v) is not bool for v in evidence['context'].values()):
    raise ValueError('EXPLICIT_CONTEXT_FLAGS_REQUIRED')
  if type(evidence['pairs']) is not list:
    raise ValueError('EXPLICIT_PAIR_PROPOSALS_REQUIRED')
  for pair in evidence['pairs']:
    c.exact(pair, ('left_id', 'right_id', 'proposal_sha256'))
    c.sha(pair['proposal_sha256'])
    if type(pair['left_id']) is not str or type(pair['right_id']) is not str:
      raise ValueError('STRING_BOUNDARY_IDENTITIES_REQUIRED')
  status, reason, pair = 'EGO_PAIR_UNAVAILABLE', 'NO_INDEPENDENT_TWO_SIDED_PROPOSAL', None
  if evidence['context']['outside_validated_range']:
    reason = 'GEOMETRY_OUTSIDE_DECLARED_DOMAIN'
  elif any(evidence['context'][key] for key in CONTEXT[:-1]) or len(evidence['pairs']) > 1:
    status, reason = 'EGO_PAIR_AMBIGUOUS', 'TOPOLOGY_OR_MULTIPLE_PLAUSIBLE_PAIRS'
  elif len(evidence['pairs']) == 1:
    candidate = evidence['pairs'][0]
    left = lines.get(candidate['left_id'])
    right = lines.get(candidate['right_id'])
    if left is not None and right is not None:
      common = sorted(set(left) & set(right))
      if len(common) < 2:
        reason = 'COMMON_VISIBLE_GEOMETRY_UNAVAILABLE'
      elif candidate['left_id'] == candidate['right_id'] or any(left[y] >= right[y] for y in common):
        status, reason = 'EGO_PAIR_AMBIGUOUS', 'LEFT_RIGHT_OR_MARKING_INCONSISTENCY'
      else:
        status, reason, pair = 'EGO_PAIR_AVAILABLE', 'UNIQUE_PROPOSED_PAIR_NOT_VALIDATED_TRUTH', candidate
  return seal(
    {
      'schema': 'EGO_PAIR_PROPOSAL_RESULT_V1',
      'status': status,
      'reason': reason,
      'pair': pair,
      'validation': 'VALIDATION_PENDING',
      'ego_association_validated': False,
      'reference_promotable': False,
      'tool_sha256': identity(),
      'contract_sha256': ego_contract()['receipt_sha256'],
      'markings': markings,
      'proposal_evidence': evidence,
    }
  )


def validate_pair(value):
  core = unseal(value)
  if value != assess_pair(core['markings'], core['proposal_evidence']):
    raise ValueError('EXACT_UNVALIDATED_PAIR_RECEIPT_REQUIRED')
  return core


def registration_gate(calibration, pair):
  unseal(calibration)
  if calibration['status'] == 'CALIBRATION_EVIDENCE_ADMITTED':
    c.validate_admitted(calibration)
  elif calibration != c.admit(None):
    raise ValueError('EXACT_PENDING_OR_ADMITTED_CALIBRATION_REQUIRED')
  if pair is not None:
    validate_pair(pair)
  return seal(
    {
      'schema': 'ROAD_FRAME_REGISTRATION_GATE_V1',
      'status': 'BLOCKED',
      'calibration_sha256': calibration['receipt_sha256'],
      'ego_pair_sha256': None if pair is None else pair['receipt_sha256'],
      'blockers': [
        'METRIC_CALIBRATION_UNAVAILABLE',
        'COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE',
        'PROJECTION_REMAINDER_UNVALIDATED',
        'INDEPENDENT_ROAD_TIME_REGISTRATION_PENDING',
      ],
      'structural_pose_available': calibration['status'] == 'CALIBRATION_EVIDENCE_ADMITTED',
      'meter_reference_allowed': False,
      'reference_promotable': False,
      'tool_sha256': identity(),
    }
  )


def rotation_z(angle):
  c.number(angle)
  if abs(angle) >= math.pi:
    raise ValueError('CANONICAL_RADIAN_YAW_REQUIRED')
  co, si = math.cos(angle), math.sin(angle)
  return np.array([[co, -si, 0.0], [si, co, 0.0], [0.0, 0.0, 1.0]])


def known_registration(
  k,
  rotation,
  center,
  pixels,
  road_transform,
  resolution_wh,
  *,
  angle_unit='rad',
  optical_frame=c.OPTICAL_FRAME,
  vehicle_frame=c.VEHICLE_FRAME,
  pixel_origin='TOP_LEFT',
):
  """A mathematical fixture, never an independent road reference or actual calibration."""
  if angle_unit != 'rad' or optical_frame != c.OPTICAL_FRAME or vehicle_frame != c.VEHICLE_FRAME or pixel_origin != 'TOP_LEFT':
    raise ValueError('EXACT_UNITS_HANDEDNESS_AND_ORIGIN_REQUIRED')
  if type(resolution_wh) is not list or len(resolution_wh) != 2 or any(type(v) is not int or v <= 0 for v in resolution_wh):
    raise ValueError('SUPPORTED_PIXEL_GEOMETRY_REQUIRED')
  if type(pixels) is not list or not pixels:
    raise ValueError('NONEMPTY_KNOWN_PIXEL_FIXTURE_REQUIRED')
  k = p._array(k, (3, 3))
  r = p._array(rotation, (3, 3))
  center = p._array(center, (3,))
  c.exact(road_transform, ('yaw_rad', 'origin_m', 'translation_bound_m', 'yaw_bound_rad', 'source_sha256'))
  c.sha(road_transform['source_sha256'])
  c.number(road_transform['yaw_bound_rad'], positive=True)
  origin = p._array(road_transform['origin_m'], (3,))
  bounds = p._array(road_transform['translation_bound_m'], (3,))
  if np.any(bounds <= 0):
    raise ValueError('SURVEY_UNCERTAINTY_REQUIRED')
  rr = rotation_z(road_transform['yaw_rad'])
  road_points = []
  vehicle_points = []
  camera_rays = []
  for pixel in pixels:
    uv = p._array(pixel, (2,))
    if not 0 <= uv[0] < resolution_wh[0] or not 0 <= uv[1] < resolution_wh[1]:
      raise ValueError('OUTSIDE_IMAGE_NO_CLIPPING')
    result = p.ground_projection(k, r, center, uv)
    point = np.array([result['forward_m'], result['lateral_left_m'], 0.0])
    vehicle_points.append(point.tolist())
    road_points.append((rr @ point + origin).tolist())
    camera_rays.append([(uv[0] - k[0, 2]) / k[0, 0], (uv[1] - k[1, 2]) / k[1, 1], 1.0])
  transforms = {
    'image': {'unit': 'px', 'origin': 'TOP_LEFT', 'axes': 'U_RIGHT_V_DOWN', 'resolution_wh': resolution_wh, 'source_sha256': digest(canonical(pixels))},
    'normalized_camera_ray': {
      'unit': 'dimensionless',
      'normalization': 'OPTICAL_Z_EQUALS_ONE_NOT_UNIT_LENGTH',
      'frame': optical_frame,
      'source_sha256': digest(canonical(k.tolist())),
    },
    'camera_to_vehicle': {
      'rotation': r.tolist(),
      'center_m': center.tolist(),
      'frame': vehicle_frame,
      'source_sha256': digest(canonical([r.tolist(), center.tolist()])),
    },
    'ground': {'unit': 'm', 'plane': 'Z_EQUALS_ZERO_KNOWN_BY_CONSTRUCTION_ONLY', 'uncertainty': 'NOT_PHYSICALLY_VALIDATED'},
    'vehicle_to_road': {'unit': 'm', 'rotation': rr.tolist(), 'origin_m': origin.tolist(), 'axes': 'RH_X_FORWARD_Y_LEFT_Z_UP', 'survey': road_transform},
  }
  transforms = {key: seal(value) for key, value in transforms.items()}
  return seal(
    {
      'schema': 'KNOWN_ROAD_REGISTRATION_FIXTURE_V1',
      'scope': 'KNOWN_BY_CONSTRUCTION_ONLY',
      'camera_rays': camera_rays,
      'vehicle_points_m': vehicle_points,
      'road_points_m': road_points,
      'transforms': transforms,
      'total_uncertainty_m': None,
      'reference_promotable': False,
      'tool_sha256': identity(),
    }
  )


def centerline_contract():
  return seal(
    {
      'schema': 'INDEPENDENT_LANE_CENTER_REFERENCE_CONTRACT_V1',
      'status': 'ALGORITHM_DEFINED',
      'validation': 'VALIDATION_PENDING',
      'definition': 'INDEPENDENT_LANE_CENTER_REFERENCE_NOT_OPTIMAL_DRIVING_PATH',
      'construction': 'EXACT_PAIRED_LONGITUDINAL_SAMPLES_MIDPOINT',
      'smoothing': 'NONE',
      'missing_side_extrapolation': False,
      'gap_interpolation': False,
      'previous_frame_carry': False,
      'forbidden_sources': list(FLAGS),
      'required': [
        'VALIDATED_METRIC_CALIBRATION',
        'INDEPENDENT_EGO_ASSOCIATION_GT',
        'INDEPENDENT_ROAD_TIME_REGISTRATION',
        'CERTIFIED_UNCERTAINTY_AND_COVERAGE',
        'REVIEWED_LANE_CENTER_REFERENCE_DEFINITION',
      ],
      'reference_promotable': False,
      'tool_sha256': identity(),
    }
  )


def midpoint_fixture(left, right, *, maximum_gap_m):
  c.number(maximum_gap_m, positive=True)
  out = {
    'schema': 'KNOWN_LANE_CENTER_MIDPOINT_FIXTURE_V1',
    'scope': 'KNOWN_BY_CONSTRUCTION_ONLY',
    'status': 'REFERENCE_UNAVAILABLE',
    'points_m': None,
    'optimal_driving_path': False,
    'reference_promotable': False,
    'maximum_gap_m': maximum_gap_m,
    'smoothing': 'NONE',
    'contract_sha256': centerline_contract()['receipt_sha256'],
  }
  if type(left) is not list or type(right) is not list:
    raise ValueError('EXACT_TWO_SIDED_POINT_LISTS_REQUIRED')
  if len(left) < 2 or len(left) != len(right):
    return seal({**out, 'reason': 'MISSING_OR_UNPAIRED_BOUNDARY'})
  l = p._array(left, (len(left), 2))
  r = p._array(right, (len(right), 2))
  if not np.array_equal(l[:, 0], r[:, 0]) or np.any(l[:, 0] <= 0) or np.any(np.diff(l[:, 0]) <= 0):
    return seal({**out, 'reason': 'UNPAIRED_OR_NONMONOTONIC_LONGITUDINAL_SAMPLES'})
  if np.any(np.diff(l[:, 0]) > maximum_gap_m):
    return seal({**out, 'reason': 'LONG_GAP_NO_INTERPOLATION'})
  if np.any(l[:, 1] <= r[:, 1]):
    return seal({**out, 'reason': 'RH_Y_LEFT_BOUNDARY_ORDER_VIOLATION'})
  return seal(
    {
      **out,
      'status': 'KNOWN_MIDPOINT_CONSTRUCTION_COMPLETE',
      'points_m': (l / 2 + r / 2).tolist(),
      'left_source_sha256': digest(canonical(left)),
      'right_source_sha256': digest(canonical(right)),
    }
  )


def lane_center_gate(registration):
  core = unseal(registration)
  if (
    core['schema'] != 'ROAD_FRAME_REGISTRATION_GATE_V1'
    or core['status'] != 'BLOCKED'
    or core['tool_sha256'] != identity()
    or core['meter_reference_allowed'] is not False
    or core['reference_promotable'] is not False
  ):
    raise ValueError('CURRENT_BLOCKED_REGISTRATION_REQUIRED')
  return seal(
    {
      'schema': 'INDEPENDENT_LANE_CENTER_READINESS_V1',
      'status': 'REFERENCE_UNAVAILABLE',
      'points_m': None,
      'registration_sha256': registration['receipt_sha256'],
      'contract_sha256': centerline_contract()['receipt_sha256'],
      'sealed_reference_allowed': False,
      'reference_promotable': False,
    }
  )
