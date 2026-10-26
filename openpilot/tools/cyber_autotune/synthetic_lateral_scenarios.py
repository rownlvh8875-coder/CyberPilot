"""Deterministic synthetic lateral scenario catalog with zero actuation authority.

The catalog supplies immutable offline inputs only. It does not run a controller,
plant, vehicle interface, CAN transport, profile writer, tuner, or promotion path.
"""
from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from itertools import pairwise

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.preflight import REQUIRED_STRATA


REQUIRED_STRESS_AXES = frozenset({
  's_curve', 'ramp', 'sensor_dropout', 'timebase_gap',
  'delay_high', 'friction_low', 'friction_high',
})
PROFILES = frozenset({
  'straight', 'left_curve', 'right_curve', 's_curve', 'ramp_curve',
  'lane_change', 'driver_override', 'saturation',
})
OUTCOMES = frozenset({'COMPLETED', 'REJECTED_INPUT'})


@dataclass(frozen=True)
class SyntheticScenario:
  scenario_id: str
  tags: tuple[str, ...]
  stress_axes: tuple[str, ...]
  profile: str
  duration_s: float
  dt_s: float
  speed_mps: float
  curvature_amplitude_1pm: float
  lateral_delay_s: float
  plant_friction_scale: float
  expected_outcome: str


@dataclass(frozen=True)
class SyntheticFrame:
  step_index: int
  time_s: float
  speed_mps: float
  desired_curvature_1pm: float
  lateral_delay_s: float
  plant_friction_scale: float
  active: bool
  steering_pressed: bool
  sensor_valid: bool


@dataclass(frozen=True)
class ScenarioMatrixAssessment:
  status: str
  blockers: tuple[str, ...]
  catalog_sha256: str | None = None
  scenario_count: int = 0
  nominal_scenario_count: int = 0
  fault_scenario_count: int = 0
  covered_strata: tuple[str, ...] = ()
  covered_stress_axes: tuple[str, ...] = ()
  structural_pass: bool = False
  controller_executed: bool = field(default=False, init=False)
  plant_executed: bool = field(default=False, init=False)
  vehicle_or_can_write: bool = field(default=False, init=False)
  performance_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _canonical(value) -> bytes:
  return json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()


def matrix_sha256(matrix: tuple[SyntheticScenario, ...]) -> str:
  return hashlib.sha256(_canonical([asdict(item) for item in matrix])).hexdigest()


def _scenario(
  scenario_id: str,
  tags: tuple[str, ...],
  profile: str,
  *,
  speed_mps: float,
  curvature_amplitude_1pm: float = 0.0,
  lateral_delay_s: float = 0.15,
  plant_friction_scale: float = 1.0,
  stress_axes: tuple[str, ...] = (),
  expected_outcome: str = 'COMPLETED',
  duration_s: float = 6.0,
  dt_s: float = 0.01,
) -> SyntheticScenario:
  return SyntheticScenario(
    scenario_id=scenario_id,
    tags=tags,
    stress_axes=stress_axes,
    profile=profile,
    duration_s=duration_s,
    dt_s=dt_s,
    speed_mps=speed_mps,
    curvature_amplitude_1pm=curvature_amplitude_1pm,
    lateral_delay_s=lateral_delay_s,
    plant_friction_scale=plant_friction_scale,
    expected_outcome=expected_outcome,
  )


def build_default_matrix() -> tuple[SyntheticScenario, ...]:
  """Return the frozen synthetic catalog; no runtime callbacks are invoked."""
  return (
    _scenario('straight_low', ('straight', 'low_speed'), 'straight', speed_mps=8.0),
    _scenario('straight_high', ('straight', 'high_speed'), 'straight', speed_mps=27.0),
    _scenario(
      'gentle_left',
      ('left_curve', 'gentle_curve', 'medium_speed', 'entry', 'apex', 'exit'),
      'left_curve', speed_mps=18.0, curvature_amplitude_1pm=0.006,
    ),
    _scenario(
      'gentle_right',
      ('right_curve', 'gentle_curve', 'medium_speed', 'entry', 'apex', 'exit'),
      'right_curve', speed_mps=18.0, curvature_amplitude_1pm=0.006,
    ),
    _scenario(
      'tight_left',
      ('left_curve', 'tight_curve', 'high_speed', 'entry', 'apex', 'exit', 'saturation'),
      'left_curve', speed_mps=24.0, curvature_amplitude_1pm=0.014,
    ),
    _scenario(
      'tight_right',
      ('right_curve', 'tight_curve', 'high_speed', 'entry', 'apex', 'exit', 'saturation'),
      'right_curve', speed_mps=24.0, curvature_amplitude_1pm=0.014,
    ),
    _scenario(
      's_curve',
      ('left_curve', 'right_curve', 'gentle_curve', 'medium_speed', 'entry', 'apex', 'exit'),
      's_curve', speed_mps=19.0, curvature_amplitude_1pm=0.009,
      stress_axes=('s_curve',),
    ),
    _scenario(
      'ramp_curve',
      ('right_curve', 'tight_curve', 'high_speed', 'entry', 'apex', 'exit', 'saturation'),
      'ramp_curve', speed_mps=25.0, curvature_amplitude_1pm=0.012,
      lateral_delay_s=0.30, stress_axes=('ramp', 'delay_high'),
    ),
    _scenario(
      'lane_change',
      ('lane_change', 'medium_speed', 'entry', 'apex', 'exit'),
      'lane_change', speed_mps=17.0, curvature_amplitude_1pm=0.010,
    ),
    _scenario(
      'driver_override',
      ('driver_override', 'steering_release', 'reengagement', 'medium_speed'),
      'driver_override', speed_mps=16.0, curvature_amplitude_1pm=0.005,
    ),
    _scenario(
      'friction_low',
      ('straight', 'low_speed'),
      'straight', speed_mps=10.0, plant_friction_scale=0.6,
      stress_axes=('friction_low',),
    ),
    _scenario(
      'friction_high',
      ('left_curve', 'gentle_curve', 'medium_speed', 'entry', 'apex', 'exit'),
      'left_curve', speed_mps=18.0, curvature_amplitude_1pm=0.006,
      plant_friction_scale=1.4, stress_axes=('friction_high',),
    ),
    _scenario(
      'sensor_dropout',
      ('straight', 'medium_speed'),
      'straight', speed_mps=15.0, stress_axes=('sensor_dropout',),
      expected_outcome='REJECTED_INPUT',
    ),
    _scenario(
      'timebase_gap',
      ('straight', 'medium_speed'),
      'straight', speed_mps=15.0, stress_axes=('timebase_gap',),
      expected_outcome='REJECTED_INPUT',
    ),
  )


def _curve_envelope(phase: float) -> float:
  if phase < 1.0 / 3.0:
    return 3.0 * phase
  if phase < 2.0 / 3.0:
    return 1.0
  return 3.0 * (1.0 - phase)


def _curvature(profile: str, amplitude: float, phase: float) -> float:
  if profile == 'straight':
    return 0.0
  if profile == 'left_curve':
    return amplitude * _curve_envelope(phase)
  if profile in ('right_curve', 'ramp_curve'):
    sign = -1.0 if profile == 'right_curve' else 1.0
    return sign * amplitude * _curve_envelope(phase)
  if profile in ('s_curve', 'lane_change'):
    return amplitude * math.sin(2.0 * math.pi * phase)
  if profile == 'driver_override':
    return amplitude * _curve_envelope(phase)
  if profile == 'saturation':
    return amplitude * _curve_envelope(phase)
  raise ValueError('UNKNOWN_PROFILE')


def generate_frames(scenario: SyntheticScenario) -> tuple[SyntheticFrame, ...]:
  """Generate deterministic synthetic inputs, including declared fault cases."""
  count = max(2, round(scenario.duration_s / scenario.dt_s))
  frames = []
  gap_index = count // 2
  for index in range(count):
    phase = index / (count - 1)
    time_s = index * scenario.dt_s
    if 'timebase_gap' in scenario.stress_axes and index >= gap_index:
      time_s += scenario.dt_s
    steering_pressed = (
      scenario.profile == 'driver_override' and 0.35 <= phase <= 0.55
    )
    active = not (
      scenario.profile == 'driver_override' and 0.35 <= phase <= 0.60
    )
    sensor_valid = not (
      'sensor_dropout' in scenario.stress_axes and 0.40 <= phase <= 0.60
    )
    frames.append(SyntheticFrame(
      step_index=index,
      time_s=time_s,
      speed_mps=scenario.speed_mps,
      desired_curvature_1pm=_curvature(
        scenario.profile, scenario.curvature_amplitude_1pm, phase,
      ),
      lateral_delay_s=scenario.lateral_delay_s,
      plant_friction_scale=scenario.plant_friction_scale,
      active=active,
      steering_pressed=steering_pressed,
      sensor_valid=sensor_valid,
    ))
  return tuple(frames)


def coverage_counts(
  matrix: tuple[SyntheticScenario, ...],
) -> tuple[tuple[str, int], ...]:
  counts = Counter(
    tag for scenario in matrix for tag in scenario.tags if tag in REQUIRED_STRATA
  )
  return tuple((name, counts[name]) for name in sorted(REQUIRED_STRATA))


def _valid_scenario(scenario) -> bool:
  if type(scenario) is not SyntheticScenario:
    return False
  if (
    type(scenario.scenario_id) is not str
    or not scenario.scenario_id
    or not scenario.scenario_id.replace('_', '').isalnum()
    or type(scenario.tags) is not tuple
    or not scenario.tags
    or len(scenario.tags) != len(set(scenario.tags))
    or not all(type(tag) is str and tag in REQUIRED_STRATA for tag in scenario.tags)
    or type(scenario.stress_axes) is not tuple
    or len(scenario.stress_axes) != len(set(scenario.stress_axes))
    or not all(axis in REQUIRED_STRESS_AXES for axis in scenario.stress_axes)
    or scenario.profile not in PROFILES
    or scenario.expected_outcome not in OUTCOMES
  ):
    return False
  numbers = (
    scenario.duration_s,
    scenario.dt_s,
    scenario.speed_mps,
    scenario.curvature_amplitude_1pm,
    scenario.lateral_delay_s,
    scenario.plant_friction_scale,
  )
  if not all(finite_number(value) for value in numbers):
    return False
  if not (
    0.1 <= scenario.duration_s <= 60.0
    and 0.005 <= scenario.dt_s <= 0.1
    and 2 <= round(scenario.duration_s / scenario.dt_s) <= 60_000
    and 0.0 <= scenario.speed_mps <= 40.0
    and 0.0 <= scenario.curvature_amplitude_1pm <= 0.05
    and 0.0 <= scenario.lateral_delay_s <= 1.0
    and 0.2 <= scenario.plant_friction_scale <= 2.0
  ):
    return False
  fault_axes = {'sensor_dropout', 'timebase_gap'} & set(scenario.stress_axes)
  if scenario.expected_outcome == 'COMPLETED' and fault_axes:
    return False
  if scenario.expected_outcome == 'REJECTED_INPUT' and len(fault_axes) != 1:
    return False
  return True


def _blocked(*reasons: str) -> ScenarioMatrixAssessment:
  return ScenarioMatrixAssessment('BLOCKED', tuple(reasons))


def _fault_semantics_valid(
  scenario: SyntheticScenario,
  frames: tuple[SyntheticFrame, ...],
) -> bool:
  if 'sensor_dropout' in scenario.stress_axes:
    return any(not frame.sensor_valid for frame in frames)
  if 'timebase_gap' in scenario.stress_axes:
    deltas = [
      right.time_s - left.time_s
      for left, right in pairwise(frames)
    ]
    return sum(abs(delta - scenario.dt_s) > 1e-12 for delta in deltas) == 1
  return False


def assess_scenario_matrix(matrix) -> ScenarioMatrixAssessment:
  """Validate structural coverage only; never execute controller or plant code."""
  if type(matrix) is not tuple or not matrix:
    return _blocked('INVALID_MATRIX')
  if not all(_valid_scenario(item) for item in matrix):
    return _blocked('INVALID_SCENARIO')
  scenario_ids = tuple(item.scenario_id for item in matrix)
  if len(scenario_ids) != len(set(scenario_ids)):
    return _blocked('DUPLICATE_SCENARIO_ID')

  counts = dict(coverage_counts(matrix))
  missing_strata = tuple(name for name in sorted(REQUIRED_STRATA) if counts[name] <= 0)
  covered_stress = tuple(sorted({axis for item in matrix for axis in item.stress_axes}))
  missing_stress = tuple(sorted(REQUIRED_STRESS_AXES - set(covered_stress)))
  if missing_strata:
    return _blocked(*(f'MISSING_STRATUM:{name}' for name in missing_strata))
  if missing_stress:
    return _blocked(*(f'MISSING_STRESS_AXIS:{name}' for name in missing_stress))

  for scenario in matrix:
    frames = generate_frames(scenario)
    if scenario.expected_outcome == 'COMPLETED':
      if not all(frame.sensor_valid for frame in frames):
        return _blocked(f'NOMINAL_SENSOR_INVALID:{scenario.scenario_id}')
      for left, right in pairwise(frames):
        if abs((right.time_s - left.time_s) - scenario.dt_s) > 1e-12:
          return _blocked(f'NOMINAL_TIMEBASE_INVALID:{scenario.scenario_id}')
    elif not _fault_semantics_valid(scenario, frames):
      return _blocked(f'FAULT_SEMANTICS_INVALID:{scenario.scenario_id}')

  nominal = sum(item.expected_outcome == 'COMPLETED' for item in matrix)
  faults = len(matrix) - nominal
  return ScenarioMatrixAssessment(
    status='SYNTHETIC_MATRIX_READY',
    blockers=('SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION',),
    catalog_sha256=matrix_sha256(matrix),
    scenario_count=len(matrix),
    nominal_scenario_count=nominal,
    fault_scenario_count=faults,
    covered_strata=tuple(sorted(REQUIRED_STRATA)),
    covered_stress_axes=covered_stress,
    structural_pass=True,
  )
