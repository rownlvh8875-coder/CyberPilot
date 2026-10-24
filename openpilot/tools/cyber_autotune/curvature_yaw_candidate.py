"""Frozen offline factor/friction scheduling inside the native torque core.

No output scaling, command bias, parameter writer or physical-delay queue.
Existing A1 bounds apply to the entire schedule before any controller update.
Coordinates are synthetic software-test values, not vehicle tuning bounds.
"""
import base64

from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, SpeedTunePoint
from openpilot.tools.cyber_autotune.a1_schedule import prepare_schedule
from openpilot.tools.cyber_autotune.native_protocol import _keys, finite


IMPLEMENTATIONS = ('NATIVE', 'SPEED_SCHEDULE')
MAX_POINTS = 16  # bounded offline schema, no performance threshold


def validate_controller(spec):
  _keys(spec, ('implementation', 'config'))
  if type(spec['implementation']) is not str or spec['implementation'] not in IMPLEMENTATIONS:
    raise ValueError('UNSUPPORTED_OFFLINE_CONTROLLER')
  if spec['implementation'] == 'NATIVE':
    _keys(spec['config'], ())
    return
  _keys(spec['config'], ('points',))
  points = spec['config']['points']
  if type(points) is not list or not 2 <= len(points) <= MAX_POINTS:
    raise ValueError('INVALID_CANDIDATE_POINTS')
  if any(type(row) is not list or len(row) != 3 or not all(finite(v) for v in row) for row in points):
    raise ValueError('INVALID_CANDIDATE_POINTS')
  _table(spec)


def _table(spec):
  return SpeedAwareTuneTable(
    tuple(SpeedTunePoint(*point, 1.) for point in spec['config']['points']),
    'frozen-offline-curvature-yaw-speed-schedule-v1',
  )


def effective_parameters(request) -> tuple[tuple[float, float, float], ...]:
  """Immutable native-wire (factor, offset, friction), with whole-run admission."""
  from opendbc.car import structs
  spec = request['controller']
  validate_controller(spec)
  speeds = tuple(frame['speed_mps'] for frame in request['native']['frames'])
  raw = base64.b64decode(request['native']['car_params_base64'], validate=True)
  with structs.CarParams.from_bytes(raw) as cp:
    params = cp.lateralTuning.torque
    baseline = (float(params.latAccelFactor), float(params.latAccelOffset), float(params.friction))
  if not all(finite(v) for v in baseline):
    raise ValueError('INVALID_CANDIDATE_BASELINE')
  if spec['implementation'] == 'NATIVE':
    return (baseline,) * len(speeds)
  schedule = prepare_schedule(_table(spec), speeds, baseline[0], baseline[2])
  return tuple((row[3], baseline[1], row[4]) for row in schedule)
