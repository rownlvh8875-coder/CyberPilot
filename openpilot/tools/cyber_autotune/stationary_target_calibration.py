"""Stationary surveyed planar target diagnostics, never an independent validation authority.

Six labeled corners of the existing 7x5 inner-corner sheet are observed, not
interpolated: top-left/right, middle-left/right, bottom-left/right. Board x goes
right, y down. Its surveyed transform into the existing vehicle datum is required.
Normalized DLT plus a proper-rotation projection fits a pinhole pose. A planar fit
does not prove uniqueness, intrinsics, distortion, or physical measurement truth.
"""
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image
import io
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune.physical_calibration_wizard_ui import measurement_sheet
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

SCHEMA = 'STATIONARY_TARGET_CAPTURE_V1'
POLICY = {
  'schema': 'ONE_SHOT_PHYSICAL_CALIBRATION_V1',
  'method': 'NORMALIZED_PLANAR_DLT_PROPER_ROTATION_PROJECTION',
  'points': 'SIX_OBSERVED_LABELED_INNER_CORNERS_7x5_TOP_MIDDLE_BOTTOM_LEFT_RIGHT',
  'residual_rule': 'MAX_EUCLIDEAN_RESIDUAL_LE_SQRT2_TIMES_DECLARED_CORNER_AXIS_BOUND',
  'rule_scope': 'NECESSARY_OBSERVATION_CONSISTENCY_ONLY_NOT_METROLOGY_ACCEPTANCE',
  'conditioning': 'REPORT_POSE_JACOBIAN_SINGULAR_VALUES_NO_INVENTED_METROLOGY_THRESHOLD',
  'ambiguity': 'PLANAR_AMBIGUITY_REQUIRES_EXTERNAL_OR_MULTIVIEW_REVIEW',
  'distortion': 'UNVERIFIED_PINHOLE_DIAGNOSTIC_NO_IMPLICIT_ZERO_TRUTH',
  'admission': 'EXISTING_CAMERA_CALIBRATION_EVIDENCE_ONLY_NO_SOLVER_AUTO_ADMISSION',
}
POLICY_SHA = digest(canonical(POLICY))
CAPTURE_KEYS = (
  'schema', 'scope', 'camera', 'intrinsics_sha256', 'image_sha256', 'image_wh', 'target', 'corners_px',
  'corner_bound_px', 'height_repeats_m', 'height_absolute_bound_m', 'height_evidence_sha256',
  'ground_evidence_sha256', 'ground_slope_bound_rad', 'operator_id_sha256', 'timestamp',
  'provenance_role', 'model_outputs_used', 'candidate_outputs_used', 'physical_observation_acknowledged', 'distortion_state',
)


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'numpy': np.__version__,
                           'policy': POLICY_SHA, 'admission': c.identity(),
                           'ui': digest(Path(__file__).with_name('stationary_target_ui.py').read_bytes()),
                           'assets': {p.name: digest(p.read_bytes()) for p in sorted(
                             Path(__file__).with_name('stationary_target_assets').iterdir()) if p.is_file()}}))


def target_sheet():
  return measurement_sheet()


def object_points(width_m, height_m):
  for x in (width_m, height_m):
    c.number(x, positive=True)
  return np.array([[0., 0., 0.], [width_m, 0., 0.], [0., height_m / 2, 0.],
                   [width_m, height_m / 2, 0.], [0., height_m, 0.], [width_m, height_m, 0.]])


def height_summary(values, bound):
  if type(values) is not list or not 2 <= len(values) <= 5:
    raise ValueError('TWO_TO_FIVE_OBSERVED_HEIGHTS_REQUIRED')
  c.number(bound, positive=True)
  for v in values:
    c.number(v, positive=True)
  lo, hi = min(values), max(values)
  if lo <= bound or hi - lo > 2 * bound:
    raise ValueError('HEIGHT_REPEAT_INTERVAL_INCONSISTENT')
  return {'observations_m': values, 'minimum_m': lo, 'maximum_m': hi, 'spread_m': hi - lo,
          'midrange_m': (lo + hi) / 2, 'declared_absolute_bound_m': bound,
          'bound_source': 'OPERATOR_METROLOGY_DECLARATION_NOT_RESOLUTION_OR_SPREAD_INFERENCE'}


def rotation(value):
  r = np.asarray(value, dtype=float)
  if r.shape != (3, 3) or not np.all(np.isfinite(r)) or not np.allclose(r.T @ r, np.eye(3), rtol=0, atol=1e-9) or abs(np.linalg.det(r) - 1) > 1e-9:
    raise ValueError('RIGHT_HANDED_SURVEYED_ROTATION_REQUIRED')
  return r


def vector(value, positive=False):
  if type(value) is not list or len(value) != 3:
    raise ValueError('EXPLICIT_THREE_AXIS_VECTOR_REQUIRED')
  for x in value:
    c.number(x, positive=positive)
  return np.array(value, dtype=float)


def validate_capture(d, i):
  c.exact(d, CAPTURE_KEYS)
  canonical(d)
  if (d['schema'] != SCHEMA or d['scope'] not in c.SCOPES or d['provenance_role'] != 'INDEPENDENT_TARGET_OBSERVATION'
      or d['model_outputs_used'] is not False or d['candidate_outputs_used'] is not False
      or d['physical_observation_acknowledged'] is not True or d['distortion_state'] != 'DISTORTION_UNVERIFIED'):
    raise ValueError('EXPLICIT_PHYSICAL_NON_MODEL_CAPTURE_REQUIRED')
  unseal(i)
  if i != c.intrinsics(d['camera']) or d['intrinsics_sha256'] != i['receipt_sha256'] or d['image_wh'] != i['resolution_wh']:
    raise ValueError('EXACT_CAMERA_SOURCE_ORIGINAL_RESOLUTION_REQUIRED')
  for k in ('image_sha256', 'height_evidence_sha256', 'ground_evidence_sha256', 'operator_id_sha256'):
    c.sha(d[k])
  c.utc(d['timestamp'])
  hs = height_summary(d['height_repeats_m'], d['height_absolute_bound_m'])
  c.number(d['ground_slope_bound_rad'], positive=True)
  if d['ground_slope_bound_rad'] >= math.pi / 2:
    raise ValueError('NONDEGENERATE_GROUND_BOUND_REQUIRED')
  t = d['target']
  c.exact(t, ('width_m', 'height_m', 'dimension_bound_m', 'planarity_bound_m', 'source_sha256',
              'rotation_target_to_vehicle', 'origin_vehicle_m', 'placement_translation_bound_m',
              'placement_rotation_bound_rad', 'placement_evidence_sha256'))
  pts = object_points(t['width_m'], t['height_m'])
  for k in ('dimension_bound_m', 'planarity_bound_m'):
    c.number(t[k], positive=True)
  if t['dimension_bound_m'] >= min(t['width_m'], t['height_m']) / 2:
    raise ValueError('TARGET_DIMENSION_INTERVAL_DEGENERATE')
  for k in ('source_sha256', 'placement_evidence_sha256'):
    c.sha(t[k])
  r = rotation(t['rotation_target_to_vehicle'])
  origin = vector(t['origin_vehicle_m'])
  vector(t['placement_translation_bound_m'], True)
  ab = vector(t['placement_rotation_bound_rad'], True)
  if np.any(ab >= math.pi / 2):
    raise ValueError('TARGET_ORIENTATION_BOUND_DEGENERATE')
  uv = np.asarray(d['corners_px'], dtype=float)
  c.number(d['corner_bound_px'], positive=True)
  if uv.shape != (6, 2) or not np.all(np.isfinite(uv)) or np.any(uv < 0) or np.any(uv >= np.array(d['image_wh'])):
    raise ValueError('SIX_ORIGINAL_IMAGE_CORNERS_REQUIRED')
  if len(np.unique(uv, axis=0)) != 6 or np.linalg.matrix_rank(uv - uv.mean(axis=0)) != 2:
    raise ValueError('DEGENERATE_TARGET_IMAGE')
  return pts, uv, r, origin, hs


def normalized_points(points):
  mean = points.mean(axis=0)
  scale = math.sqrt(2) / np.sqrt(np.mean(np.sum((points - mean)**2, axis=1)))
  transform = np.array([[scale, 0, -scale * mean[0]], [0, scale, -scale * mean[1]], [0, 0, 1.]])
  return (np.c_[points, np.ones(len(points))] @ transform.T)[:, :2], transform


def fit_planar(points, uv, k):
  xy = (np.c_[uv, np.ones(len(uv))] @ np.linalg.inv(k).T)[:, :2]
  obj, to = normalized_points(points[:, :2])
  img, ti = normalized_points(xy)
  rows = []
  for (x, y), (u, v) in zip(obj, img, strict=True):
    rows.extend([[-x, -y, -1, 0, 0, 0, u*x, u*y, u], [0, 0, 0, -x, -y, -1, v*x, v*y, v]])
  a = np.array(rows)
  _, sv, vt = np.linalg.svd(a)
  if sv[-2] <= np.finfo(float).eps * sv[0] * max(a.shape):
    raise ValueError('RANK_DEFICIENT_TARGET')
  h = np.linalg.inv(ti) @ vt[-1].reshape(3, 3) @ to
  if h[2, 2] < 0:
    h = -h
  factor = 2 / (np.linalg.norm(h[:, 0]) + np.linalg.norm(h[:, 1]))
  raw = np.c_[h[:, 0] * factor, h[:, 1] * factor, np.cross(h[:, 0] * factor, h[:, 1] * factor)]
  u, _, vh = np.linalg.svd(raw)
  rot = u @ np.diag([1., 1., np.linalg.det(u @ vh)]) @ vh
  return rot, h[:, 2] * factor, float(sv[0] / sv[-2])


def project(points, k, r, center):
  cam = (points - center) @ r
  if np.any(cam[:, 2] <= 0):
    raise ValueError('TARGET_BEHIND_CAMERA')
  uv = cam @ k.T
  return uv[:, :2] / uv[:, 2:]


def solve(d, i):
  pts, uv, tr, origin, hs = validate_capture(d, i)
  k = np.array(i['matrix'])
  rt, trans, condition = fit_planar(pts, uv, k)
  r = tr @ rt.T
  if r[0, 2] <= 0:
    raise ValueError('NARROW_ROAD_OPTICAL_AXIS_MUST_POINT_VEHICLE_FORWARD')
  center = origin - r @ trans
  world = pts @ tr.T + origin
  error = project(world, k, r, center) - uv
  maximum = float(np.max(np.linalg.norm(error, axis=1)))
  if maximum > math.sqrt(2) * d['corner_bound_px']:
    raise ValueError('REPROJECTION_OBSERVATION_BOUND_EXCEEDED')
  if center[2] <= 0 or abs(center[2] - hs['midrange_m']) > hs['declared_absolute_bound_m']:
    raise ValueError('OBSERVED_CAMERA_HEIGHT_INCONSISTENT')
  # Pose Jacobian: small vehicle-axis rotation, translation normalized by target extent.
  eps = 1e-6  # Numeric central-difference step, not physical uncertainty.
  jac = []
  for axis in range(6):
    if axis < 3:
      from openpilot.tools.cyber_autotune.lane_projection_validation import _rotation
      plus, minus = project(world, k, _rotation(axis, eps) @ r, center), project(world, k, _rotation(axis, -eps) @ r, center)
    else:
      delta = np.eye(3)[axis - 3] * eps * max(d['target']['width_m'], d['target']['height_m'])
      plus, minus = project(world, k, r, center + delta), project(world, k, r, center - delta)
    jac.append(((plus - minus) / (2 * eps)).reshape(-1))
  values = np.linalg.svd(np.array(jac).T, compute_uv=False)
  if values[-1] <= np.finfo(float).eps * values[0] * 12:
    raise ValueError('POSE_NUMERICALLY_UNOBSERVABLE')
  e = r @ c.BASE_ROTATION.T
  pitch = math.asin(float(np.clip(-e[2, 0], -1, 1)))
  angles = {'pitch_rad': pitch, 'roll_rad': math.atan2(e[2, 1], e[2, 2]), 'yaw_rad': math.atan2(e[1, 0], e[0, 0])}
  return c.seal({
    'schema': 'SURVEYED_TARGET_POSE_SOLVE_V1', 'status': 'CALIBRATION_SOLVED', 'scope': d['scope'],
    'capture_sha256': digest(canonical(d)), 'image_sha256': d['image_sha256'], 'target_sha256': digest(canonical(d['target'])),
    'camera': d['camera'], 'intrinsics_sha256': i['receipt_sha256'], 'solver_source_sha256': identity(), 'policy_sha256': POLICY_SHA,
    'camera_to_vehicle': r.tolist(), 'camera_center_vehicle_m': center.tolist(), 'orientation_rad': angles,
    'point_count': len(pts), 'reprojection_rms_px': float(np.sqrt(np.mean(error**2))), 'reprojection_max_px': maximum,
    'homography_condition_nonnull': condition, 'pose_jacobian_singular_values': values.tolist(),
    'pose_condition': float(values[0] / values[-1]), 'height_observation': hs,
    'intrinsics_provenance': 'STATIC_INTRINSICS_PRIOR', 'intrinsics_validation': 'INTRINSICS_VALIDATION_PENDING',
    'extrinsics_provenance': 'INDEPENDENT_TARGET_DERIVED_CANDIDATE_NOT_VALIDATED',
    'distortion_status': d['distortion_state'], 'planar_ambiguity': 'UNRESOLVED_BY_SINGLE_PLANAR_FIT',
    'independent_validation': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
    'solved_pose_uncertainty': None, 'qualification_allowed': False, 'sealed_reference_allowed': False,
    'reference_promotable': False, 'vehicle_activation_allowed': False,
  })


def repeat_consistency(rows, translation_bound_m, angle_bound_rad, policy_evidence_sha256):
  if type(rows) is not list or not 2 <= len(rows) <= 5:
    raise ValueError('TWO_TO_FIVE_DISTINCT_CAPTURE_RESULTS_REQUIRED')
  c.number(translation_bound_m, positive=True)
  c.number(angle_bound_rad, positive=True)
  c.sha(policy_evidence_sha256)
  if any(len({row[key] for row in rows}) != len(rows) for key in ('capture_sha256', 'image_sha256', 'receipt_sha256')):
    raise ValueError('DISTINCT_OBSERVED_CAPTURES_REQUIRED')
  for row in rows:
    unseal(row)
    if row['schema'] != 'SURVEYED_TARGET_POSE_SOLVE_V1' or row['solver_source_sha256'] != identity():
      raise ValueError('CURRENT_SOLVER_RECEIPTS_REQUIRED')
    if row['camera'] != rows[0]['camera'] or row['intrinsics_sha256'] != rows[0]['intrinsics_sha256'] or row['scope'] != rows[0]['scope']:
      raise ValueError('REPEATED_CAPTURE_CAMERA_MISMATCH')
  centers = np.array([r['camera_center_vehicle_m'] for r in rows])
  rotations = [rotation(r['camera_to_vehicle']) for r in rows]
  translation = max(float(np.linalg.norm(a - b)) for a in centers for b in centers)
  angle = max(math.acos(float(np.clip((np.trace(a.T @ b) - 1) / 2, -1, 1))) for a in rotations for b in rotations)
  return c.seal({'schema': 'STATIONARY_CAPTURE_CONSISTENCY_V1', 'capture_receipts': [r['receipt_sha256'] for r in rows],
                 'translation_spread_m': translation, 'rotation_spread_rad': angle,
                 'within_declared_comparison_bounds': translation <= translation_bound_m and angle <= angle_bound_rad,
                 'bounds_source_sha256': policy_evidence_sha256, 'independent_calibration_validated': False,
                 'reference_promotable': False})


class CaptureSession:
  """Private crash-safe editable draft and content-addressed immutable capture/solve pairs."""

  def __init__(self, root, *, scope='INDEPENDENT_PHYSICAL'):
    if scope not in c.SCOPES:
      raise ValueError('EXPLICIT_CAPTURE_SCOPE_REQUIRED')
    self.scope = scope
    self.root = Path(root).absolute()
    if self.root.resolve() != self.root or self.root.is_relative_to(c.ROOT):
      raise ValueError('SEPARATE_PRIVATE_NONSYMLINK_ROOT_REQUIRED')
    s.durable_mkdir(self.root)
    os.chmod(self.root, 0o700)
    self.binding = c.seal({'schema': 'STATIONARY_CAPTURE_STORE_V1', 'scope': scope, 'source_sha256': identity()})
    self.root_id = (self.root.stat().st_dev, self.root.stat().st_ino)
    with s.writer_lease(self.root):
      p = self.root / 'binding.json'
      if p.exists():
        if s.read_json(p) != self.binding:
          raise ValueError('NEW_VERSION_REQUIRED_SOURCE_CHANGED')
      else:
        if {p.name for p in self.root.iterdir()} != {'writer.lock'}:
          raise ValueError('EMPTY_PRIVATE_CAPTURE_ROOT_REQUIRED')
        s.atomic_json(p, self.binding)

  def guard(self):
    if (self.root.resolve() != self.root or (self.root.stat().st_dev, self.root.stat().st_ino) != self.root_id
        or s.read_json(self.root / 'binding.json') != self.binding or self.binding['source_sha256'] != identity()):
      raise ValueError('CAPTURE_STORE_BINDING_CHANGED')

  def save_draft(self, draft):
    canonical(draft)
    if type(draft) is not dict:
      raise ValueError('EXPLICIT_DRAFT_OBJECT_REQUIRED')
    with s.writer_lease(self.root):
      self.guard()
      s.atomic_json(self.root / 'draft.json', c.seal({'binding_sha256': self.binding['receipt_sha256'], 'draft': draft}))
    return self.state()

  def completed(self):
    self.guard()
    rows = []
    for path in sorted(self.root.glob('*.json')):
      if path.name in ('binding.json', 'draft.json'):
        continue
      if len(path.stem) != 64:
        raise ValueError('UNKNOWN_CAPTURE_STORE_JSON')
      value = s.read_json(path)
      unseal(value)
      if value['receipt_sha256'] != path.stem or value['source_sha256'] != identity() or value['publish_this_package'] is not False:
        raise ValueError('IMMUTABLE_CAPTURE_BINDING_CHANGED')
      if value['capture']['scope'] != self.scope or value['solver_result'] != solve(value['capture'], value['intrinsics']):
        raise ValueError('CAPTURE_RESULT_OR_SCOPE_CHANGED')
      image = w.read_blob(self.root / (value['capture']['image_sha256'] + '.image'))
      if digest(image) != value['capture']['image_sha256']:
        raise ValueError('CAPTURE_IMAGE_CHANGED')
      rows.append(value)
    return rows

  def state(self):
    self.guard()
    draft = None
    if (self.root / 'draft.json').exists():
      value = unseal(s.read_json(self.root / 'draft.json'))
      if value['binding_sha256'] != self.binding['receipt_sha256']:
        raise ValueError('DRAFT_BINDING_CHANGED')
      draft = value['draft']
    rows = self.completed()
    return {'status': 'CALIBRATION_SOLVED' if rows else 'CALIBRATION_MEASUREMENT_PENDING',
            'measurement_admission': 'CALIBRATION_MEASUREMENT_PENDING', 'completed_captures': len(rows),
            'scope': self.scope, 'tool_state': 'CALIBRATION_TOOL_READY', 'draft': draft,
            'independent_validation': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING', 'qualification_allowed': False}

  def freeze(self, draft, intrinsic, image):
    if draft['scope'] != self.scope:
      raise ValueError('CAPTURE_SCOPE_BINDING_MISMATCH')
    if type(image) is not bytes or len(image) > w.MAX_ATTACHMENT_BYTES or digest(image) != draft['image_sha256']:
      raise ValueError('EXACT_RAW_IMAGE_BYTES_REQUIRED')
    with Image.open(io.BytesIO(image)) as im:
      if list(im.size) != draft['image_wh']:
        raise ValueError('ORIGINAL_IMAGE_DIMENSIONS_REQUIRED')
      im.verify()
    result = solve(draft, intrinsic)
    capture = c.seal({'schema': 'IMMUTABLE_STATIONARY_TARGET_CAPTURE_V1', 'capture': draft, 'intrinsics': intrinsic,
                      'solver_result': result, 'source_sha256': identity(), 'publish_this_package': False})
    with s.writer_lease(self.root):
      self.guard()
      name = self.root / (capture['receipt_sha256'] + '.json')
      if name.exists() or name.is_symlink():
        raise ValueError('DUPLICATE_IMMUTABLE_CAPTURE')
      raw = self.root / (draft['image_sha256'] + '.image')
      if raw.exists():
        if w.read_blob(raw) != image:
          raise ValueError('EXISTING_IMAGE_HASH_MISMATCH')
      else:
        w.atomic_blob(raw, image)
      s.atomic_json(name, capture)
    return capture
