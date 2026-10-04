"""Fixed synthetic native A1 experiments. No real-data admission or live writer.

Trusted checkout code only; not a hostile-code sandbox. Requested torque evidence
is neither applied torque nor centering/comfort/vehicle qualification.
"""
import base64
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

from openpilot.tools.cyber_autotune.native_protocol import (
  FINGERPRINT, MAX_REQUEST_BYTES, SOURCE_FILES, TIMESTEP_NS, _hex, _keys, _unique_pairs, canonical, digest, finite,
)
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _run_process, validate_response as validate_v1


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ('disabled', 'identity', 'factor', 'friction', 'combined')
FRAME_COUNT = 601
BASELINE_FACTOR, BASELINE_FRICTION = 4., .125  # software fixture, NOT a Hyundai tune
OVERLAY_FILES = tuple('openpilot/tools/cyber_autotune/' + name for name in (
  'a1_experiment.py', 'a1_schedule.py', 'a1_worker.py', 'native_worker.py', 'native_runner.py',
  'native_protocol.py', 'source_imports.py', 'worker_resources.py',
)) + ('openpilot/selfdrive/controls/lib/cyber_lateral/speed_aware_tune.py',
      'openpilot/common/constants.py', 'opendbc_repo/opendbc/car/structs.py',
      'opendbc_repo/opendbc/car/hyundai/values.py', 'opendbc_repo/opendbc/car/torque_data/params.toml',
      'opendbc_repo/opendbc/car/torque_data/override.toml', 'opendbc_repo/opendbc/car/torque_data/substitute.toml')
AUTHORITIES = ('runtime_accepted', 'promotable', 'vehicle_authority', 'profile_authority', 'can_authority')
UNAVAILABLE = ['center_deviation', 'lane_edge_margin', 'physical_steering_jerk']
PASS = 'SOFTWARE_NATIVE_A1_INTEGRATION_PASS'


def build_request(fixture):
  def revision(directory):
    return subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True, timeout=5).strip()

  request = {'version': 1, 'fixture': fixture, 'source': {
    'root': str(ROOT), 'head': revision(ROOT), 'opendbc_head': revision(ROOT / 'opendbc_repo'),
    'files': {name: digest((ROOT / name).read_bytes()) for name in SOURCE_FILES}},
    'overlay': {name: digest((ROOT / name).read_bytes()) for name in OVERLAY_FILES}}
  encode_request(request)
  return request


def encode_request(request):
  _keys(request, ('version', 'fixture', 'source', 'overlay'))
  if type(request['version']) is not int or request['version'] != 1 or request['fixture'] not in FIXTURES:
    raise ValueError('UNSUPPORTED_A1_FIXTURE')
  source = request['source']
  _keys(source, ('root', 'head', 'opendbc_head', 'files'))
  if type(source['root']) is not str or source['root'] != str(ROOT):
    raise ValueError('A1_REQUIRES_OWNED_CHECKOUT')
  if not _hex(source['head'], 40) or not _hex(source['opendbc_head'], 40):
    raise ValueError('INVALID_A1_SOURCE')
  for values, names in ((source['files'], SOURCE_FILES), (request['overlay'], OVERLAY_FILES)):
    _keys(values, names)
    if not all(_hex(value, 64) for value in values.values()):
      raise ValueError('INVALID_A1_BINDING')
  payload = canonical(request)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('A1_REQUEST_TOO_LARGE')
  return payload


def decode_request(payload):
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_A1_REQUEST_SIZE')
  try:
    request = json.loads(payload, object_pairs_hook=_unique_pairs)
    encode_request(request)
    return request
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_A1_JSON') from exc


def _verify_bindings(request):
  from openpilot.tools.cyber_autotune.native_worker import _verify_source
  _verify_source(request['source'])
  for name, expected in request['overlay'].items():
    path = (ROOT / name).resolve(strict=True)
    if not path.is_relative_to(ROOT) or digest(path.read_bytes()) != expected:
      raise ValueError('A1_OVERLAY_CHANGED')


def make_fixture(request):
  """Generate owned synthetic inputs; never read Params/logs/current settings."""
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.values import CAR
  from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, SpeedTunePoint
  encode_request(request)
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
  cp.lateralTuning.torque.latAccelFactor = BASELINE_FACTOR
  cp.lateralTuning.torque.friction = BASELINE_FRICTION
  raw = cp.to_bytes()
  frames = []
  for index in range(FRAME_COUNT):
    frames.append({'time_ns': index * TIMESTEP_NS, 'speed_mps': min(index, 600 - index) / 10,
                   'active': index >= 20 and not 300 <= index < 310, 'safety_limited': 200 <= index < 210,
                   'curvature_limited': 250 <= index < 260, 'steering_pressed': 150 <= index < 160,
                   'accel_mps2': 0., 'angle_deg': 0., 'rate_deg_s': 0., 'driver_torque': 0., 'roll_rad': 0.,
                   'angle_offset_deg': 0., 'stiffness_factor': 1., 'steer_ratio': 16., 'lateral_delay_s': .15,
                   'desired_curvature_1pm': 0. if index < 20 else .00005 * math.sin(index / 30)})
  variant = request['fixture']
  table = SpeedAwareTuneTable(tuple(
    SpeedTunePoint(speed, BASELINE_FACTOR + (factor if variant in ('factor', 'combined') else 0.),
                   BASELINE_FRICTION + (friction if variant in ('friction', 'combined') else 0.), 1.)
    for speed, factor, friction in zip((0., 10., 20., 30.), (0., 1/64, 1/32, 0.), (0., 1/1024, 1/512, 0.), strict=True)),
    'repository-owned-synthetic-a1-v1')
  native = {'version': 1, 'source': request['source'], 'fingerprint': FINGERPRINT,
            'car_params_base64': base64.b64encode(raw).decode(), 'car_params_sha256': digest(raw), 'frames': frames}
  return native, table


def _manifest(request, native, table):
  import capnp
  import numpy
  return {'fixture_kind': 'SYNTHETIC_NOT_VEHICLE_CALIBRATION', 'cp_sha256': native['car_params_sha256'],
          'frames_sha256': digest(canonical(native['frames'])), 'table_sha256': digest(canonical(asdict(table))),
          'source_sha256': digest(canonical(request['source'])), 'overlay_sha256': digest(canonical(request['overlay'])),
          'environment': {'python': platform.python_version(), 'numpy': numpy.__version__, 'capnp': capnp.__version__,
                          'machine': platform.machine(), 'platform': sys.platform, 'byteorder': sys.byteorder},
          'parameter_policy': {'owner': 'synthetic-fixture-only', 'class': 'OFFLINE_ONLY',
                               'factor_unit': '(m/s^2)/normalized_command', 'friction_unit': 'normalized_command',
                               'baseline_factor': BASELINE_FACTOR, 'baseline_friction': BASELINE_FRICTION},
          'measurement_boundary': 'requested_torque_before_vehicle_controller'}


def execute_experiment(request):
  """Internal synchronous worker entry, not an active-loop API."""
  from openpilot.tools.cyber_autotune.native_worker import _execute_request
  from openpilot.tools.cyber_autotune.source_imports import source_only_imports
  request = decode_request(encode_request(request))
  _verify_bindings(request)
  with source_only_imports():
    native, table = make_fixture(request)
    baseline = _execute_request(native, _capture_state=True)
    candidate = _execute_request(native, _capture_state=True, _a1_table=None if request['fixture'] == 'disabled' else table)
    result = {'status': PASS, 'fixture': request['fixture'], 'request_sha256': digest(encode_request(request)),
              'manifest': _manifest(request, native, table), 'baseline': baseline, 'candidate': candidate,
              'unavailable_metrics': UNAVAILABLE.copy(), **dict.fromkeys(AUTHORITIES, False)}
    validate_response(request, result)
  _verify_bindings(request)
  if len(canonical(result)) > MAX_RESPONSE_BYTES:
    raise ValueError('A1_RESPONSE_TOO_LARGE')
  return result


def validate_response(request, result):
  from openpilot.tools.cyber_autotune.a1_schedule import prepare_schedule
  _keys(result, ('status', 'fixture', 'request_sha256', 'manifest', 'baseline', 'candidate', 'unavailable_metrics', *AUTHORITIES))
  if (result['status'] != PASS or result['fixture'] != request['fixture'] or
      result['request_sha256'] != digest(encode_request(request)) or result['unavailable_metrics'] != UNAVAILABLE or
      any(result[name] is not False for name in AUTHORITIES)):
    raise ValueError('INVALID_A1_RESULT_BINDING')
  native, table = make_fixture(request)
  if canonical(result['manifest']) != canonical(_manifest(request, native, table)):
    raise ValueError('A1_MANIFEST_MISMATCH')
  speeds = tuple(frame['speed_mps'] for frame in native['frames'])
  from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, SpeedTunePoint
  identity = SpeedAwareTuneTable((SpeedTunePoint(0., BASELINE_FACTOR, BASELINE_FRICTION, 1.),
                                  SpeedTunePoint(30., BASELINE_FACTOR, BASELINE_FRICTION, 1.)), 'synthetic-baseline')
  for name, tune in (('baseline', identity), ('candidate', table)):
    arm = result[name]
    if type(arm) is not dict or 'a1' not in arm:
      raise ValueError('MISSING_A1_STATE')
    legacy = {key: value for key, value in arm.items() if key != 'a1'}
    validate_v1(native, legacy)
    state = arm['a1']
    _keys(state, ('state_schema', 'reset', 'invariants_sha256', 'schedule', 'schedule_sha256', 'states', 'states_sha256'))
    if state['state_schema'] != 'native-torque-state-v1' or state['reset'] != 'fresh-controller-once':
      raise ValueError('A1_STATE_SCHEMA_MISMATCH')
    expected = [list(row) for row in prepare_schedule(tune, speeds, BASELINE_FACTOR, BASELINE_FRICTION)]
    if canonical(state['schedule']) != canonical(expected) or state['schedule_sha256'] != digest(canonical(expected)):
      raise ValueError('A1_EFFECTIVE_SCHEDULE_MISMATCH')
    if not _hex(state['invariants_sha256'], 64) or type(state['states']) is not list or len(state['states']) != FRAME_COUNT:
      raise ValueError('INVALID_A1_STATES')
    for row, scheduled in zip(state['states'], expected, strict=True):
      _keys(row, ('state_sha256', 'factor', 'friction', 'pid_i', 'history_sha256'))
      if (not _hex(row['state_sha256'], 64) or not _hex(row['history_sha256'], 64) or not finite(row['pid_i']) or
          not finite(row['factor']) or not finite(row['friction']) or row['factor'] != scheduled[3] or row['friction'] != scheduled[4]):
        raise ValueError('INVALID_A1_STATE_RECEIPT')
    if state['states_sha256'] != digest(canonical(state['states'])):
      raise ValueError('A1_STATES_DIGEST_MISMATCH')
  baseline, candidate = result['baseline'], result['candidate']
  if baseline['a1']['invariants_sha256'] != candidate['a1']['invariants_sha256']:
    raise ValueError('A1_INVARIANTS_MISMATCH')
  if request['fixture'] in ('identity', 'disabled'):
    if canonical(baseline) != canonical(candidate):
      raise ValueError('A1_BASELINE_PARITY_FAILED')
  elif baseline['ordered_trace_sha256'] == candidate['ordered_trace_sha256']:
    raise ValueError('A1_TUNING_WAS_NOOP')


def run_experiment(request, *, timeout_s):
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  request = decode_request(payload)

  def failure(status):
    return {'status': status, 'request_sha256': digest(payload), **dict.fromkeys(AUTHORITIES, False)}

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  try:
    observed = _run_process([sys.executable, '-I', str(Path(__file__).with_name('a1_worker.py'))], payload, timeout_s)
  except OSError:
    return failure('WORKER_UNAVAILABLE')
  if observed.status == 'TIMEOUT':
    return failure('TIMEOUT')
  if observed.status != 'EXITED' or observed.returncode != 0:
    return failure('WORKER_FAILED')
  if not 0 < len(observed.stdout) <= MAX_RESPONSE_BYTES:
    return failure('INVALID_RESPONSE')
  try:
    result = json.loads(observed.stdout, object_pairs_hook=_unique_pairs)
    validate_response(request, result)
    _verify_bindings(request)
  except (ValueError, OSError, UnicodeError, RecursionError):
    return failure('INVALID_RESPONSE')
  return result
