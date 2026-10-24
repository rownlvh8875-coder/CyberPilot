"""Structural physical-measurement admission, never calibration truth certification."""

import json

from datetime import datetime
import math
from pathlib import Path
import numpy as np
from openpilot.common.transformations.camera import DEVICE_CAMERAS
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune import lane_projection_validation as v
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal as _seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
VEHICLE_FRAME = 'RH_X_FORWARD_Y_LEFT_Z_UP_ORIGIN_SURVEYED_VEHICLE_DATUM'
OPTICAL_FRAME = 'RH_X_RIGHT_Y_DOWN_Z_FORWARD_ORIGIN_OPTICAL_CENTER'
SCOPES = ('INDEPENDENT_PHYSICAL', 'TEST_ONLY')
UNITS = {
  'height_m': 'm',
  'mount_x_m': 'm',
  'mount_y_m': 'm',
  'pitch_rad': 'rad',
  'roll_rad': 'rad',
  'yaw_rad': 'rad',
  'fx_px': 'px',
  'fy_px': 'px',
  'cx_px': 'px',
  'cy_px': 'px',
}
METHODS = ('SURVEYED_STATIONARY_TARGET', 'SURVEYED_CHECKERBOARD', 'SURVEYED_APRILTAG', 'OPTICAL_CENTER_SURVEY')
CAMERA_SOURCE = 'openpilot/common/transformations/camera.py'
CAMERA_SHA = '1de3f9e6147f28195c71673ae5c8ec38e65ede997ac98d2e1e3b114eda873ec4'
HARDWARE_SOURCE = 'openpilot/common/hardware/comma/hardware.py'
HARDWARE_SHA = 'd357b90f878ef7b8ea1df5a537cdf986df2243bc4b20b37c7ed88175020cadd8'
BASE_ROTATION = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
SCHEMA = {
  'schema': 'INDEPENDENT_PHYSICAL_CAMERA_MEASUREMENT_V1',
  'units': UNITS,
  'methods': METHODS,
  'uncertainty': 'POSITIVE_INDEPENDENT_ABSOLUTE_BOUND_NOT_STATISTICAL_QUANTILE',
  'physical_protocol_sha256': digest((ROOT / 'docs/cyberpilot/changes/lane-reference-independent-physical-calibration.md').read_bytes()),
  'frames': [OPTICAL_FRAME, VEHICLE_FRAME],
  'angles': 'Rz(yaw)Ry(pitch)Rx(roll)_RADIANS',
  'admission': 'STRUCTURE_AND_DECLARED_PROVENANCE_ONLY_NOT_PHYSICAL_OR_METROLOGY_VALIDATION',
}
SCHEMA_SHA = digest(canonical(SCHEMA))


def seal(value):
  """Detach caller state before hashing; receipts never alias mutable inputs."""
  return _seal(json.loads(canonical(value)))


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'schema': SCHEMA_SHA, 'projection': digest(Path(p.__file__).read_bytes())}))


def exact(value, keys):
  if type(value) is not dict or set(value) != set(keys):
    raise ValueError('EXACT_EVIDENCE_FIELDS_REQUIRED')


def number(value, *, positive=False):
  if type(value) not in (float, int) or not math.isfinite(value) or (positive and value <= 0):
    raise ValueError('FINITE_DIMENSIONAL_VALUE_REQUIRED')
  return value


def sha(value):
  if not is_sha256(value):
    raise ValueError('SHA256_PROVENANCE_REQUIRED')
  return value


def utc(value):
  if type(value) is not str or not value.endswith('Z'):
    raise ValueError('CANONICAL_UTC_REQUIRED')
  out = datetime.fromisoformat(value[:-1] + '+00:00')
  if out.isoformat().replace('+00:00', 'Z') != value:
    raise ValueError('CANONICAL_UTC_REQUIRED')
  return out


def intrinsics(camera):
  exact(camera, ('device', 'hardware_generation', 'sensor', 'view', 'unit_id_sha256', 'hardware_evidence_sha256'))
  if (
    camera['device'] != 'mici'
    or camera['hardware_generation'] != 'comma4'
    or camera['view'] != 'narrow_road'
    or camera['sensor'] not in ('ar0231', 'ox03c10', 'os04c10')
  ):
    raise ValueError('EXPLICIT_SUPPORTED_COMMA4_NARROW_SENSOR_REQUIRED')
  sha(camera['unit_id_sha256'])
  sha(camera['hardware_evidence_sha256'])
  if digest((ROOT / CAMERA_SOURCE).read_bytes()) != CAMERA_SHA or digest((ROOT / HARDWARE_SOURCE).read_bytes()) != HARDWARE_SHA:
    raise ValueError('PINNED_STATIC_HARDWARE_SOURCE_CHANGED')
  conf = DEVICE_CAMERAS[(camera['device'], camera['sensor'])].narrow_road
  return seal(
    {
      'schema': 'STATIC_CAMERA_INTRINSICS_V1',
      'camera': camera,
      'resolution_wh': [conf.width, conf.height],
      'matrix': conf.intrinsics.tolist(),
      'provenance_role': 'STATIC_INTRINSICS',
      'source_file': CAMERA_SOURCE,
      'source_sha256': CAMERA_SHA,
      'hardware_mapping_source_file': HARDWARE_SOURCE,
      'hardware_mapping_source_sha256': HARDWARE_SHA,
      'distortion_model': 'UNKNOWN_NOT_ASSUMED_ZERO',
      'per_unit_intrinsics_validated': False,
      'reference_promotable': False,
    }
  )


def observation(value, unit, *, static=False):
  exact(value, ('value', 'unit', 'method', 'provenance', 'uncertainty'))
  number(value['value'])
  if value['unit'] != unit or value['method'] not in (('PINNED_HARDWARE_NOMINAL',) if static else METHODS):
    raise ValueError('INDEPENDENT_METHOD_AND_EXACT_UNIT_REQUIRED')
  prov = value['provenance']
  exact(prov, ('role', 'source_sha256', 'instrument_sha256', 'model_outputs_used', 'candidate_outputs_used'))
  if (
    prov['role'] != ('STATIC_INTRINSICS' if static else 'INDEPENDENT_PHYSICAL')
    or prov['model_outputs_used'] is not False
    or prov['candidate_outputs_used'] is not False
  ):
    raise ValueError('MODEL_OR_CANDIDATE_DERIVED_NOT_PHYSICAL')
  sha(prov['source_sha256'])
  sha(prov['instrument_sha256'])
  if static and prov['source_sha256'] != CAMERA_SHA:
    raise ValueError('STATIC_VALUE_SOURCE_MISMATCH')
  bound = value['uncertainty']
  exact(bound, ('kind', 'value', 'unit', 'method', 'provenance_sha256'))
  if bound['kind'] != 'ABSOLUTE_BOUND' or bound['unit'] != unit or bound['method'] != 'METROLOGY_REVIEW':
    raise ValueError('INDEPENDENT_ABSOLUTE_UNCERTAINTY_REQUIRED')
  number(bound['value'], positive=True)
  sha(bound['provenance_sha256'])


def validate_measurement(m, i):
  exact(
    m,
    (
      'schema',
      'scope',
      'measurement_id_sha256',
      'camera',
      'timestamp',
      'operator_id_sha256',
      'method',
      'human_acknowledgement',
      'intrinsics_sha256',
      'schema_sha256',
      'tool_sha256',
      'observations',
      'mounting_reference',
      'ground_surface',
      'distortion',
    ),
  )
  if (
    m['schema'] != SCHEMA['schema']
    or m['scope'] not in SCOPES
    or m['schema_sha256'] != SCHEMA_SHA
    or m['tool_sha256'] != identity()
    or m['method'] not in METHODS
    or m['human_acknowledgement'] is not True
  ):
    raise ValueError('FROZEN_EXPLICIT_PHYSICAL_MEASUREMENT_REQUIRED')
  sha(m['measurement_id_sha256'])
  sha(m['operator_id_sha256'])
  utc(m['timestamp'])
  unseal(i)
  if i != intrinsics(m['camera']) or m['intrinsics_sha256'] != i['receipt_sha256']:
    raise ValueError('INTRINSICS_DEVICE_SOURCE_BINDING_MISMATCH')
  obs = m['observations']
  exact(obs, UNITS)
  for key, unit in UNITS.items():
    observation(obs[key], unit, static=key.endswith('_px'))
  if obs['height_m']['value'] <= obs['height_m']['uncertainty']['value']:
    raise ValueError('NONPOSITIVE_HEIGHT_INTERVAL')
  for key in ('pitch_rad', 'roll_rad', 'yaw_rad'):
    limit = math.pi / 2 if key == 'pitch_rad' else math.pi
    if abs(obs[key]['value']) + obs[key]['uncertainty']['value'] >= limit:
      raise ValueError('CANONICAL_NONDEGENERATE_RADIAN_POSE_REQUIRED')
  for key, (row, col) in {'fx_px': (0, 0), 'fy_px': (1, 1), 'cx_px': (0, 2), 'cy_px': (1, 2)}.items():
    if obs[key]['value'] != i['matrix'][row][col] or obs[key]['value'] <= obs[key]['uncertainty']['value']:
      raise ValueError('NOMINAL_INTRINSIC_VALUE_AND_POSITIVE_INTERVAL_REQUIRED')
  mount = m['mounting_reference']
  exact(mount, ('definition', 'convention', 'evidence_sha256'))
  if mount['definition'] != 'SURVEYED_VEHICLE_ORIGIN_TO_OPTICAL_CENTER' or mount['convention'] != VEHICLE_FRAME:
    raise ValueError('SURVEYED_MOUNT_DATUM_REQUIRED')
  sha(mount['evidence_sha256'])
  ground = m['ground_surface']
  exact(ground, ('assumption', 'vertical_deviation'))
  if ground['assumption'] != 'LOCALLY_SURVEYED_PLANAR_GROUND':
    raise ValueError('INDEPENDENT_GROUND_SURVEY_REQUIRED')
  observation(ground['vertical_deviation'], 'm')
  if ground['vertical_deviation']['value'] != 0:
    raise ValueError('GROUND_DATUM_MUST_BE_ZERO_BY_DEFINITION')
  distortion = m['distortion']
  exact(distortion, ('state', 'residual'))
  if distortion['state'] != 'INDEPENDENTLY_BOUNDED_UNDISTORTED_RESIDUAL':
    raise ValueError('UNDISTORTION_RESIDUAL_EVIDENCE_REQUIRED')
  observation(distortion['residual'], 'px')
  if distortion['residual']['value'] != 0:
    raise ValueError('RESIDUAL_BOUND_NOT_BIAS_CORRECTION_REQUIRED')


def admit(measurement, intrinsic=None):
  base = {
    'schema': 'PHYSICAL_CALIBRATION_ADMISSION_V1',
    'schema_sha256': SCHEMA_SHA,
    'tool_sha256': identity(),
    'measurement': None,
    'intrinsics': None,
    'measurement_sha256': None,
    'status': 'CALIBRATION_MEASUREMENT_PENDING',
    'provenance_role': 'INDEPENDENT_PHYSICAL_EXTRINSICS',
    'metrology_validation': 'PENDING_EXTERNAL_PHYSICAL_REVIEW',
    'metric_calibration_validated': False,
    'reference_promotable': False,
  }
  if measurement is None:
    return seal(base)
  try:
    validate_measurement(measurement, intrinsic)
    return seal(
      {
        **base,
        'measurement': measurement,
        'intrinsics': intrinsic,
        'measurement_sha256': digest(canonical(measurement)),
        'status': 'CALIBRATION_EVIDENCE_ADMITTED',
        'admission_scope': measurement['scope'],
      }
    )
  except (ValueError, TypeError, KeyError, OverflowError) as exc:
    return seal({**base, 'status': 'CALIBRATION_EVIDENCE_REJECTED', 'reason': str(exc)})


def validate_admitted(value):
  core = unseal(value)
  if core.get('status') != 'CALIBRATION_EVIDENCE_ADMITTED' or value != admit(core.get('measurement'), core.get('intrinsics')):
    raise ValueError('EXACT_CURRENT_STRUCTURAL_CALIBRATION_RECEIPT_REQUIRED')
  return core


class ImmutableCalibrationStore:
  """One immutable measured snapshot; a different measurement needs a separate versioned store."""

  def __init__(self, root):
    self.root = Path(root).absolute()
    if self.root.resolve() != self.root.absolute():
      raise ValueError('SYMLINK_STORE_FORBIDDEN')
    s.durable_mkdir(self.root)
    stat = self.root.stat()
    self.root_identity = (stat.st_dev, stat.st_ino)
    self.binding = seal({'schema': 'CALIBRATION_STORE_V1', 'schema_sha256': SCHEMA_SHA, 'tool_sha256': identity()})
    with s.writer_lease(self.root):
      path = self.root / 'binding.json'
      if path.exists():
        if s.read_json(path) != self.binding:
          raise ValueError('CALIBRATION_STORE_BINDING_CHANGED')
      elif {p.name for p in self.root.iterdir()} != {'writer.lock'}:
        raise ValueError('SEPARATE_EMPTY_CALIBRATION_STORE_REQUIRED')
      else:
        s.atomic_json(path, self.binding)

  def guard(self):
    if self.root.resolve() != self.root or not self.root.is_dir():
      raise ValueError('CALIBRATION_STORE_ROOT_CHANGED')
    stat = self.root.stat()
    if (stat.st_dev, stat.st_ino) != self.root_identity:
      raise ValueError('CALIBRATION_STORE_ROOT_CHANGED')

  def read(self):
    self.guard()
    if s.read_json(self.root / 'binding.json') != self.binding:
      raise ValueError('CALIBRATION_STORE_BINDING_CHANGED')
    value = s.read_json(self.root / 'measurement.json')
    validate_admitted(value)
    return value

  def save(self, measurement, intrinsic):
    value = admit(measurement, intrinsic)
    validate_admitted(value)
    self.guard()
    with s.writer_lease(self.root):
      self.guard()
      if s.read_json(self.root / 'binding.json') != self.binding:
        raise ValueError('CALIBRATION_STORE_BINDING_CHANGED')
      if (self.root / 'measurement.json').exists() or (self.root / 'measurement.json').is_symlink():
        raise ValueError('DUPLICATE_OR_CONFLICTING_IMMUTABLE_MEASUREMENT')
      s.atomic_json(self.root / 'measurement.json', value)
    return value


def pose(measurement):
  o = measurement['observations']
  rz = v._rotation(2, o['yaw_rad']['value'])
  ry = v._rotation(1, o['pitch_rad']['value'])
  rx = v._rotation(0, o['roll_rad']['value'])
  return rz @ ry @ rx @ BASE_ROTATION, np.array([o['mount_x_m']['value'], o['mount_y_m']['value'], o['height_m']['value']]), rz, ry


def projection_budget(calibration, localization):
  unseal(calibration)
  pending = calibration['status'] == 'CALIBRATION_MEASUREMENT_PENDING'
  if pending and localization is not None:
    raise ValueError('CALIBRATION_REQUIRED_BEFORE_NUMERIC_BUDGET')
  if pending and calibration != admit(None):
    raise ValueError('EXACT_PENDING_CALIBRATION_REQUIRED')
  rows = []
  if not pending:
    validate_admitted(calibration)
    exact(localization, ('u_px', 'v_px', 'source_sha256', 'kind'))
    sha(localization['source_sha256'])
    if localization['kind'] != 'ABSOLUTE_BOUND':
      raise ValueError('PIXEL_QUANTILE_NOT_DETERMINISTIC_BOUND')
    for key in ('u_px', 'v_px'):
      if number(localization[key]) < 0:
        raise ValueError('NONNEGATIVE_PIXEL_BOUND_REQUIRED')
    m = calibration['measurement']
    o = m['observations']
    r, center, rz, ry = pose(m)
    k = np.array(calibration['intrinsics']['matrix'])
  terms = ('detector', 'intrinsic', 'height', 'pitch', 'roll', 'yaw', 'mount_lateral', 'ground_plane', 'distortion')
  for distance in v.DISTANCE_BUCKETS_M:
    row = {
      'distance_m': distance,
      'query_semantics': 'CAMERA_RAY_TO_DEFINED_ROAD_ORIGIN_LATERAL_ZERO_NOT_A_LANE_TRUTH_POINT',
      **{key + '_term_m': None for key in terms},
      'first_order_subtotal_m': None,
      'projection_remainder_m': None,
      'total_conservative_uncertainty_m': None,
    }
    if not pending:
      ray = r.T @ (np.array([distance, 0.0, 0.0]) - center)
      uv = k @ ray
      if uv[2] <= 0:
        raise ValueError('SENSITIVITY_QUERY_BEHIND_CAMERA')
      q = p.ground_projection(k, r, center, uv[:2] / uv[2])
      j = q['jacobian']
      angular = np.array([j['roll_world_x_rad'], j['pitch_world_y_rad'], j['yaw_world_z_rad']])
      row.update(
        {
          'detector_term_m': abs(j['u_px']) * localization['u_px'] + abs(j['v_px']) * localization['v_px'],
          'intrinsic_term_m': sum(abs(j[key]) * o[key]['uncertainty']['value'] for key in ('fx_px', 'fy_px', 'cx_px', 'cy_px')),
          'height_term_m': abs(j['camera_height_m']) * o['height_m']['uncertainty']['value'],
          'roll_term_m': abs(float(angular @ (rz @ ry @ np.array([1.0, 0.0, 0.0])))) * o['roll_rad']['uncertainty']['value'],
          'pitch_term_m': abs(float(angular @ (rz @ np.array([0.0, 1.0, 0.0])))) * o['pitch_rad']['uncertainty']['value'],
          'yaw_term_m': abs(j['yaw_world_z_rad']) * o['yaw_rad']['uncertainty']['value'],
          'mount_lateral_term_m': o['mount_y_m']['uncertainty']['value'],
          'ground_plane_term_m': abs(j['camera_height_m']) * m['ground_surface']['vertical_deviation']['uncertainty']['value'],
          'distortion_term_m': (abs(j['u_px']) + abs(j['v_px'])) * m['distortion']['residual']['uncertainty']['value'],
        }
      )
      row['first_order_subtotal_m'] = sum(row[key + '_term_m'] for key in terms)
      if not math.isfinite(row['first_order_subtotal_m']):
        raise ValueError('NONFINITE_FIRST_ORDER_BUDGET')
    rows.append(row)
  return seal(
    {
      'schema': 'CALIBRATION_BOUND_PROJECTION_BUDGET_V1',
      'status': 'PENDING' if pending else 'BLOCKED_PROJECTION_REMAINDER_UNVALIDATED',
      'calibration_sha256': calibration['receipt_sha256'],
      'localization': localization,
      'rows': rows,
      'formula': 'sum(abs(J_i(query))*independent_absolute_bound_i)+certified_nonlinear_ground_distortion_remainder',
      'scope': 'FIRST_ORDER_DIAGNOSTIC_NOT_CONSERVATIVE_CERTIFICATE',
      'reference_promotable': False,
    }
  )
