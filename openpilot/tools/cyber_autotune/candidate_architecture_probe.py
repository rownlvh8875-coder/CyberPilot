"""Synthetic observer controls only. Implements no trajectory or smoothness algorithm."""
from dataclasses import asdict

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune.controller_plant_authority import arc, signal

# Frozen analytic fixtures, not candidate parameters or a search range.
CURVATURE_FIXTURE_1PM = (-.002, -.001, 0., .001, .002)
ARC_LENGTH_M = 10.
DT_S = .01
OSCILLATION_FIXTURE = (0., .25, -.25, .25, -.25, 0.)
CONSTANT_FIXTURE = (0.,) * len(OSCILLATION_FIXTURE)


def run():
  a.authorize_execution('ARCHITECTURE_PROBE')
  arcs = [(k, arc(k, ARC_LENGTH_M)) for k in CURVATURE_FIXTURE_1PM]
  sign_order = all(k * row['pose_y_m'] > 0 for k, row in arcs if k != 0)
  sign_order &= abs(arcs[-1][1]['pose_y_m']) > abs(arcs[-2][1]['pose_y_m'])
  observations = signal(OSCILLATION_FIXTURE, DT_S)
  negative = signal(CONSTANT_FIXTURE, DT_S)
  source = a.hash_object({'fixture': 'NOT_AN_EXECUTABLE_CANDIDATE'})
  intervention = c.InterventionInput(0., DT_S, True, False, False, False)
  governor = a.SmoothnessGovernor()
  first = [asdict(governor.update(c.GovernorCommand(x, source, source), intervention)) for x in OSCILLATION_FIXTURE]
  repeated = [asdict(a.SmoothnessGovernor().update(c.GovernorCommand(x, source, source), intervention)) for x in OSCILLATION_FIXTURE]
  return {'schema': 'CANDIDATE_ARCHITECTURE_PROBE_V1',
          'scope': 'FIXTURE_OBSERVABILITY_ONLY_NO_CANDIDATE_ALGORITHM',
          'fixture_policy': fixture_policy(), 'execution_environment': a.probe_environment(),
          'trajectory': {'arcs': arcs, 'analytic_sign_and_amplitude_order': sign_order,
                         'actual_trajectory_algorithm_tested': False},
          'smoothness': {'observations': observations, 'constant_control': negative,
                         'derivative_and_reversals_detected': observations['maximum_derivative_per_s'] > 0 and observations['sign_changes'] > 0,
                         'enabled_governor_tested': False, 'monotonic_shaping_and_phase_tradeoff': 'IMPLEMENTATION_PENDING'},
          'negative': {'disabled_passthrough_exact': all(r['final_requested_torque'] == v for r, v in zip(first, OSCILLATION_FIXTURE, strict=True)),
                       'identical_reset_exact': first == repeated,
                       'current_alias': dict(a.HISTORY)},
          'candidate_selection_allowed': False, 'performance_claim_allowed': False}


def fixture_policy():
  return {'curvatures_1pm': CURVATURE_FIXTURE_1PM, 'arc_length_m': ARC_LENGTH_M,
          'oscillation_normalized': OSCILLATION_FIXTURE, 'constant_normalized': CONSTANT_FIXTURE, 'dt_s': DT_S,
          'basis': 'EXACT_ANALYTIC_DIRECTION_AND_OBSERVER_NEGATIVE_CONTROL; NOT_PLANT_GAIN'}
