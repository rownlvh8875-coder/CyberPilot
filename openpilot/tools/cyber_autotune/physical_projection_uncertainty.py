"""Conditional pinhole interval diagnostics; quantiles never become absolute bounds.

Actual numeric use requires the unchanged structural physical admission receipt,
explicit road/annotation bounds, and independently evidenced pixel-camera mapping.
This module neither certifies those declarations nor produces a sealed reference.
"""
import itertools
import math
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

DISTANCES_M = (5., 10., 15., 20., 25., 30.)
PIXEL_RECEIPT = '6e15a7caf6af342696906da5add686d775578844058e6eb8dd0df10dacb14562'
PIXEL_FILE = c.ROOT / 'docs/cyberpilot/changes/private-assisted-holdout-final-aggregate-v1.json'
SOURCE_GEOMETRY_FILE = c.ROOT / 'docs/cyberpilot/changes/private-holdout-ai-assisted-pixels.md'


def pixel_input():
  import json
  x = json.loads(PIXEL_FILE.read_bytes())
  unseal(x)
  if x['receipt_sha256'] != PIXEL_RECEIPT or x['human_verified'] != 60 or x['blind_human'] is not False:
    raise ValueError('FROZEN_ASSISTED_PIXEL_INPUT_CHANGED')
  return c.seal({'schema': 'FROZEN_ASSISTED_PIXEL_UNCERTAINTY_INPUT_V1', 'source_sha256': PIXEL_RECEIPT,
                 'source_wh': [526, 330], 'geometry_source_sha256': digest(SOURCE_GEOMETRY_FILE.read_bytes()),
                 'evaluation_sha256': x['evaluation_sha256'], 'groups': x['groups'], 'center': x['center'],
                 'failure_counts': x['failure_counts'], 'kind': 'ASSISTED_MATCHED_POINT_QUANTILES_NOT_ABSOLUTE_BOUND',
                 'reference_promotable': False})


class Interval:
  """Outward-rounded arithmetic box; contains parameter dependency overestimation."""

  def __init__(self, lo, hi=None):
    self.lo, self.hi = float(lo), float(lo if hi is None else hi)
    if not math.isfinite(self.lo) or not math.isfinite(self.hi) or self.lo > self.hi:
      raise ValueError('FINITE_ORDERED_INTERVAL_REQUIRED')

  def __add__(self, other):
    b = other if isinstance(other, Interval) else Interval(other)
    return Interval(math.nextafter(self.lo + b.lo, -math.inf), math.nextafter(self.hi + b.hi, math.inf))

  __radd__ = __add__

  def __neg__(self):
    return Interval(-self.hi, -self.lo)

  def __sub__(self, other):
    return self + (-other if isinstance(other, Interval) else -float(other))

  def __rsub__(self, other):
    return -self + other

  def __mul__(self, other):
    b = other if isinstance(other, Interval) else Interval(other)
    vals = [a * v for a in (self.lo, self.hi) for v in (b.lo, b.hi)]
    return Interval(math.nextafter(min(vals), -math.inf), math.nextafter(max(vals), math.inf))

  __rmul__ = __mul__

  def __truediv__(self, other):
    b = other if isinstance(other, Interval) else Interval(other)
    if b.lo <= 0 <= b.hi:
      raise ValueError('PROJECTION_INTERVAL_CROSSES_HORIZON_OR_ZERO_FOCAL')
    return self * Interval(math.nextafter(1 / b.hi, -math.inf), math.nextafter(1 / b.lo, math.inf))


def trig(x, cosine=False):
  if not isinstance(x, Interval):
    return math.cos(x) if cosine else math.sin(x)
  lo, hi = x.lo, x.hi
  if hi - lo >= 2 * math.pi:
    return Interval(-1, 1)
  function = math.cos if cosine else math.sin
  vals = [function(lo), function(hi)]
  extremum_origin = 0. if cosine else math.pi / 2
  for n in range(math.ceil((lo - extremum_origin) / math.pi), math.floor((hi - extremum_origin) / math.pi) + 1):
    vals.append((-1.)**n)
  return Interval(math.nextafter(min(vals), -math.inf), math.nextafter(max(vals), math.inf))


def project_state(s):
  # Rz Ry Rx applied to optical ray through the existing BASE_ROTATION.
  x, y, z = 1., -(s['u_px'] - s['cx_px']) / s['fx_px'], -(s['v_px'] - s['cy_px']) / s['fy_px']
  cr, sr = trig(s['roll_rad'], True), trig(s['roll_rad'])
  cp, sp = trig(s['pitch_rad'], True), trig(s['pitch_rad'])
  cy, sy = trig(s['yaw_rad'], True), trig(s['yaw_rad'])
  y, z = cr*y - sr*z, sr*y + cr*z
  x, z = cp*x + sp*z, -sp*x + cp*z
  x, y = cy*x - sy*y, sy*x + cy*y
  grade = trig(s['grade_rad']) / trig(s['grade_rad'], True)
  camber = trig(s['camber_rad']) / trig(s['camber_rad'], True)
  den = z - grade*x - camber*y
  numerator = s['ground_z_m'] + grade*s['mount_x_m'] + camber*s['mount_y_m'] - s['height_m']
  if isinstance(den, Interval):
    if den.hi >= 0 or numerator.hi >= 0:
      raise ValueError('PROJECTION_BOX_NOT_ENTIRELY_FORWARD_DOWNWARD')
  elif den >= 0 or numerator >= 0:
    raise ValueError('NONFORWARD_GROUND_INTERSECTION')
  scale = numerator / den
  forward = s['mount_x_m'] + scale*x
  if (forward.lo if isinstance(forward, Interval) else forward) <= 0:
    raise ValueError('NONFORWARD_GROUND_INTERSECTION')
  return s['mount_y_m'] + scale*y


def query(calibration, distance, lateral):
  core = c.validate_admitted(calibration)
  c.number(distance, positive=True)
  c.number(lateral)
  m = core['measurement']
  obs = m['observations']
  r, center, rz, ry = c.pose(m)
  k = np.array(core['intrinsics']['matrix'])
  ray = r.T @ (np.array([distance, lateral, 0.]) - center)
  if ray[2] <= 0:
    raise ValueError('QUERY_POINT_BEHIND_CAMERA')
  uv = k @ ray
  uv = uv[:2] / uv[2]
  state = {key: v['value'] for key, v in obs.items()}
  state.update(u_px=float(uv[0]), v_px=float(uv[1]), grade_rad=0., camber_rad=0., ground_z_m=0.)
  if not 0 <= uv[0] < core['intrinsics']['resolution_wh'][0] or not 0 <= uv[1] < core['intrinsics']['resolution_wh'][1]:
    raise ValueError('QUERY_OUTSIDE_CALIBRATED_IMAGE')
  jac = p.ground_projection(k, r, center, uv)['jacobian']
  angular = np.array([jac['roll_world_x_rad'], jac['pitch_world_y_rad'], jac['yaw_world_z_rad']])
  derivatives = {key: jac[key] for key in ('u_px', 'v_px', 'fx_px', 'fy_px', 'cx_px', 'cy_px')}
  derivatives.update(height_m=jac['camera_height_m'], mount_y_m=1., mount_x_m=0.,
                     roll_rad=float(angular @ (rz @ ry @ np.array([1., 0., 0.]))),
                     pitch_rad=float(angular @ (rz @ np.array([0., 1., 0.]))), yaw_rad=jac['yaw_world_z_rad'],
                     ground_z_m=-jac['camera_height_m'],
                     grade_rad=-jac['camera_height_m'] * distance, camber_rad=-jac['camera_height_m'] * lateral)
  return {'nominal': state, 'derivatives': derivatives, 'distance_m': distance, 'lateral_m': lateral}


def mapping_check(mapping, calibration):
  from openpilot.tools.cyber_autotune import qcamera_pixel_registration as registration
  if type(mapping) is not dict or mapping.get('schema') != 'REGISTERED_PIXEL_CAMERA_MAPPING_V1':
    raise ValueError('VALIDATED_PIXEL_GEOMETRY_REGISTRATION_REQUIRED')
  expected = registration.projection_mapping(mapping.get('registration'), calibration)
  if canonical(mapping) != canonical(expected):
    raise ValueError('REGISTERED_PIXEL_MAPPING_IDENTITY_MISMATCH')


def envelope(q, calibration, bounds, mapping):
  c.validate_admitted(calibration)
  c.exact(bounds, ('grade_rad', 'camber_rad', 'nonplanarity_m', 'annotation_px', 'source_sha256'))
  c.sha(bounds['source_sha256'])
  for key in ('grade_rad', 'camber_rad', 'nonplanarity_m', 'annotation_px'):
    c.number(bounds[key], positive=True)
  mapping_check(mapping, calibration)
  m = calibration['measurement']
  delta = {key: o['uncertainty']['value'] for key, o in m['observations'].items()}
  distortion = m['distortion']['residual']['uncertainty']['value']
  delta.update(
    u_px=distortion + bounds['annotation_px'] * mapping['scale_x'] + mapping['mapping_residual_bound_px'],
    v_px=distortion + bounds['annotation_px'] * mapping['scale_y'] + mapping['mapping_residual_bound_px'],
    ground_z_m=m['ground_surface']['vertical_deviation']['uncertainty']['value'] + bounds['nonplanarity_m'],
    grade_rad=bounds['grade_rad'], camber_rad=bounds['camber_rad'],
  )
  # Residual image terms include annotation/distortion/mapping, not detector quantiles.
  terms = {key: abs(q['derivatives'][key]) * value for key, value in delta.items()}
  nominal = q['nominal']
  base = project_state(nominal)
  box = {key: Interval(value) + Interval(-delta[key], delta[key]) for key, value in nominal.items()}
  out = project_state(box)
  sampled, remainder = [], []
  # Two full box corners plus each axis endpoint: deterministic diagnostic, never exhaustive certification.
  perturbations = [{key: sign * d for key, d in delta.items()} for sign in (-1, 1)]
  perturbations += [{key: sign * delta[key]} for key, sign in itertools.product(delta, (-1, 1))]
  for change in perturbations:
    actual = project_state({key: value + change.get(key, 0.) for key, value in nominal.items()}) - base
    linear = sum(q['derivatives'][key] * value for key, value in change.items())
    sampled.append(abs(actual))
    remainder.append(abs(actual - linear))
  return {
    'first_order_terms_m': terms, 'first_order_subtotal_m': sum(terms.values()),
    'separate_image_terms_m': {
      'annotation': abs(q['derivatives']['u_px']) * bounds['annotation_px'] * mapping['scale_x']
                    + abs(q['derivatives']['v_px']) * bounds['annotation_px'] * mapping['scale_y'],
      'distortion': (abs(q['derivatives']['u_px']) + abs(q['derivatives']['v_px'])) * distortion,
      'pixel_mapping': (abs(q['derivatives']['u_px']) + abs(q['derivatives']['v_px'])) * mapping['mapping_residual_bound_px'],
    },
    'separate_ground_terms_m': {
      'survey_vertical': abs(q['derivatives']['ground_z_m']) * m['ground_surface']['vertical_deviation']['uncertainty']['value'],
      'nonplanarity': abs(q['derivatives']['ground_z_m']) * bounds['nonplanarity_m'],
      'grade': terms['grade_rad'], 'camber': terms['camber_rad'],
    },
    'interval_includes': ['INTRINSICS', 'EXTRINSICS', 'DISTORTION', 'PIXEL_MAPPING', 'ANNOTATION', 'GROUND'],
    'nonlinear_remainder_interval_bound_m': max(abs(out.lo - base), abs(out.hi - base)) + sum(terms.values()),
    'remainder_interval_scope': 'TRIANGLE_ENCLOSURE_CONDITIONAL_DECLARED_BOX_NOT_PHYSICAL_CERTIFICATION',
    'calibration_interval_envelope_m': max(abs(out.lo - base), abs(out.hi - base)),
    'calibration_corner_max_m': max(sampled), 'sampled_nonlinear_remainder_m': max(remainder),
    'nonlinear_sampling_scope': 'AXIS_ENDPOINTS_NOT_CERTIFICATE',
    'corner_scope': 'TWO_FULL_CORNERS_PLUS_AXIS_ENDPOINTS_NOT_EXHAUSTIVE',
    'interval_scope': 'CONDITIONAL_PINHOLE_DECLARED_BOX_NOT_PHYSICAL_CERTIFICATION',
  }


def report(calibration, bounds, mapping):
  pix = pixel_input()
  base = {
    'schema': 'PIXEL_TO_METER_PREPARATION_V1',
    'source_sha256': digest(Path(__file__).read_bytes()), 'pixel_input_sha256': pix['receipt_sha256'],
    'status': 'CALIBRATION_MEASUREMENT_PENDING', 'scope': 'NOT_RUN', 'meter_results': None,
    'center_availability': {'matched': 44, 'evaluable': 55, 'unavailable': 11},
    'independent_ground_truth': False, 'qualification_allowed': False, 'reference_promotable': False,
    'sealed_reference_allowed': False, 'vehicle_activation_allowed': False,
    'blockers': ['INDEPENDENT_REFERENCE_UNAVAILABLE', 'CALIBRATION_MEASUREMENT_PENDING',
                 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING', 'METRIC_CALIBRATION_UNAVAILABLE',
                 'PIXEL_GEOMETRY_REGISTRATION_PENDING'],
  }
  if calibration is None:
    if bounds is not None or mapping is not None:
      raise ValueError('MEASUREMENT_REQUIRED_BEFORE_NUMERIC_METER_DIAGNOSTIC')
    return c.seal(base)
  c.validate_admitted(calibration)
  if type(mapping) is dict and mapping.get('schema') == 'PIXEL_CAMERA_REGISTRATION_PENDING_V1':
    from openpilot.tools.cyber_autotune import qcamera_pixel_registration as registration
    expected = registration.projection_mapping(mapping.get('registration'), calibration)
    if canonical(mapping) != canonical(expected):
      raise ValueError('PENDING_REGISTRATION_IDENTITY_MISMATCH')
    return c.seal({**base, 'status': 'PIXEL_GEOMETRY_REGISTRATION_PENDING',
                   'registration_sha256': mapping['registration']['receipt_sha256']})
  mapping_check(mapping, calibration)
  rows = []
  for distance in DISTANCES_M:
    q = query(calibration, distance, 0.)
    row = envelope(q, calibration, bounds, mapping)
    source_u = (q['nominal']['u_px'] - mapping['offset_x_px']) / mapping['scale_x']
    source_v = (q['nominal']['v_px'] - mapping['offset_y_px']) / mapping['scale_y']
    if not 0 <= source_u < pix['source_wh'][0] or not 0 <= source_v < pix['source_wh'][1]:
      raise ValueError('QUERY_OUTSIDE_OBSERVED_PIXEL_STREAM_SUPPORT')
    scale = abs(q['derivatives']['u_px']) * mapping['scale_x']
    rows.append({**row, 'distance_m': distance, 'nominal_reference_lateral_m': 0.,
                 'query_scope': 'DEFINED_GROUND_QUERY_NOT_OBSERVED_LANE_POINT',
                 'detector_equivalent_center_median_m': scale * pix['center']['median'],
                 'detector_equivalent_center_p95_m': scale * pix['center']['p95'],
                 'detector_group_equivalent_m': {
                   group: {side: {'median': None if data[side]['median'] is None else scale * data[side]['median'],
                                 'p95': None if data[side]['p95'] is None else scale * data[side]['p95']}
                           for side in ('left', 'right')} for group, data in pix['groups'].items()},
                 'detector_quantile_scope': 'CONDITIONAL_MATCHED_ASSISTED_PIXEL_QUANTILE_FIXED_Y_NOT_ABSOLUTE_BOUND',
                 'total_detector_plus_calibration_absolute_bound_m': None})
  return c.seal({**base, 'schema': 'PRIVATE_ASSISTED_PIXEL_TO_METER_DIAGNOSTIC_V1', 'scope': calibration['admission_scope'],
                 'status': 'CONDITIONAL_METER_DIAGNOSTIC_NOT_QUALIFIED',
                 'calibration_sha256': calibration['receipt_sha256'], 'mapping_sha256': digest(canonical(mapping)),
                 'road_annotation_bounds_sha256': digest(canonical(bounds)), 'meter_results': rows})
