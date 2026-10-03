"""Descriptive native-planner/generic-plant measurements, NOT an acceptance gate.

Rows describe one interval: inputs/command at time_s, response at time_s+dt_s.
No native code, parameter writes, tuning search or vehicle transport is imported.
Content hashes identify inputs; they do not authenticate a producer or plant.
"""
import math

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


FLAGS = ('active', 'stop_demand', 'lead_present', 'cut_in_event')
NUMBERS = ('time_s', 'speed_mps', 'accel_mps2', 'position_m', 'lead_gap_m', 'lead_speed_mps',
           'planner_accel_mps2', 'requested_accel_mps2', 'applied_accel_mps2',
           'response_speed_mps', 'response_accel_mps2')
STOP_SPEED_MPS = .01  # Same standstill threshold as the synthetic feedback fixture.
RESTART_SPEED_MPS = .5  # Descriptive launch threshold, as in synthetic_metrics v2.
CUT_IN_REQUEST_DROP_MPS2 = .1  # Diagnostic command reduction; not a safety threshold.


def _validate(rows, dt_s):
  if (type(rows) not in (tuple, list) or not 4 <= len(rows) <= 60_000 or
      not finite_number(dt_s) or not .001 <= dt_s <= .1):
    raise ValueError('INVALID_FEEDBACK_TRACE')
  for i, row in enumerate(rows):
    if (type(row) is not dict or set(row) != set(FLAGS + NUMBERS) or
        any(type(row[key]) is not bool for key in FLAGS) or
        any(not finite_number(row[key]) or abs(row[key]) > 1e6 for key in NUMBERS)):
      raise ValueError('INVALID_FEEDBACK_ROW')
    if (not math.isclose(row['time_s'], i * dt_s, rel_tol=0, abs_tol=1e-10) or
        any(not 0 <= row[key] <= 80 for key in ('speed_mps', 'lead_speed_mps', 'response_speed_mps')) or
        (row['cut_in_event'] and (i == 0 or not row['lead_present'] or not row['active']))):
      raise ValueError('INVALID_FEEDBACK_DOMAIN')
    if i and any(not math.isclose(row[key], rows[i - 1]['response_' + key], rel_tol=0, abs_tol=1e-9)
                 for key in ('speed_mps', 'accel_mps2')):
      raise ValueError('DISCONTINUOUS_FEEDBACK_STATE')


def _rms(values):
  return math.sqrt(math.fsum(value * value for value in values) / len(values)) if values else None


def _jerk(rows, key, dt_s):
  return tuple((b[key] - a[key]) / dt_s for a, b in zip(rows, rows[1:], strict=False))


def summarize(rows, dt_s: float) -> dict:
  """All-frame metrics with explicit missing event coverage and no PASS verdict.

  Planner tracking uses interval-start acceleration, not a future response.
  Response jerk uses end-of-interval acceleration differences. Gap/TTC use
  simultaneous interval-start plant values; signed gaps are never clipped.
  No stop-position or desired-follow-distance truth is supplied by these fixtures.
  Cut-in is an explicit exogenous event, not inferred from lead availability.
  Stop success means a standstill sample within the demanded active episode;
  restart delay uses interval-end time, ending at the next stop/inactive interval.
  """
  _validate(rows, dt_s)
  lead = [row for row in rows if row['lead_present']]
  ttc = [0. if row['lead_gap_m'] <= 0 else row['lead_gap_m'] / (row['speed_mps'] - row['lead_speed_mps'])
         for row in lead if row['lead_gap_m'] <= 0 or row['speed_mps'] > row['lead_speed_mps']]
  episodes, restarts, cuts = [], [], []
  unresolved_restarts = unresolved_cuts = 0
  moving_releases = 0
  for i, row in enumerate(rows):
    if row['active'] and row['stop_demand'] and (i == 0 or not rows[i - 1]['active'] or not rows[i - 1]['stop_demand']):
      end = next((j for j in range(i + 1, len(rows)) if not rows[j]['active'] or not rows[j]['stop_demand']), len(rows))
      episodes.append(any(r['response_speed_mps'] <= STOP_SPEED_MPS for r in rows[i:end]))
    if i and rows[i - 1]['active'] and rows[i - 1]['stop_demand'] and row['active'] and not row['stop_demand']:
      if row['speed_mps'] > STOP_SPEED_MPS:
        moving_releases += 1  # A moving stopping-to-PID transition is not a launch.
      else:
        end = next((j for j in range(i + 1, len(rows)) if not rows[j]['active'] or rows[j]['stop_demand']), len(rows))
        response = next((r for r in rows[i:end] if r['response_speed_mps'] >= RESTART_SPEED_MPS), None)
        if response is None:
          unresolved_restarts += 1
        else:
          restarts.append(response['time_s'] + dt_s - row['time_s'])
    if row['cut_in_event']:
      end = next((j for j in range(i + 1, len(rows))
                  if not rows[j]['active'] or not rows[j]['lead_present'] or rows[j]['cut_in_event']), len(rows))
      threshold = rows[i - 1]['requested_accel_mps2'] - CUT_IN_REQUEST_DROP_MPS2
      response = next((r for r in rows[i:end] if r['requested_accel_mps2'] <= threshold), None)
      if response is None:
        unresolved_cuts += 1
      else:
        cuts.append(response['time_s'] - row['time_s'])
  inactive = [abs(row['requested_accel_mps2']) for row in rows if not row['active']]
  result = {
    'schema': 'planner-feedback-metrics-v1', 'status': 'DESCRIPTIVE_ONLY', 'readiness': 'NOT_READY',
    'truth_scope': 'GENERIC_SYNTHETIC_ONLY', 'trace_sha256': digest(canonical(rows)),
    'sample_count': len(rows), 'duration_s': len(rows) * dt_s, 'dt_s': dt_s,
    'planner_tracking_rms_mps2': _rms([r['accel_mps2'] - r['planner_accel_mps2'] for r in rows]),
    'request_to_applied_rms_mps2': _rms([r['requested_accel_mps2'] - r['applied_accel_mps2'] for r in rows]),
    'command_jerk_rms_mps3': _rms(_jerk(rows, 'requested_accel_mps2', dt_s)),
    'actual_jerk_rms_mps3': _rms(_jerk(rows, 'response_accel_mps2', dt_s)),
    'minimum_lead_gap_m': min(r['lead_gap_m'] for r in lead) if lead else None,
    'minimum_ttc_s': min(ttc) if ttc else None, 'nonpositive_gap_frames': sum(r['lead_gap_m'] <= 0 for r in lead),
    'stop_episode_count': len(episodes), 'stopped_episode_count': sum(episodes),
    'unresolved_stops': len(episodes) - sum(episodes), 'stopping_error_m': None, 'desired_follow_error_m': None,
    'restart_delay_s': max(restarts) if restarts and not unresolved_restarts and not moving_releases else None,
    'unresolved_restarts': unresolved_restarts,
    'release_without_standstill_count': moving_releases,
    'cut_in_event_count': sum(r['cut_in_event'] for r in rows),
    'cut_in_response_s': max(cuts) if cuts and not unresolved_cuts else None, 'unresolved_cut_ins': unresolved_cuts,
    'inactive_frame_count': len(inactive), 'inactive_max_abs_request_mps2': max(inactive) if inactive else None,
    **dict.fromkeys(('real_vehicle_verified', 'runtime_accepted', 'active_profile_enabled', 'vehicle_write_enabled',
                    'can_write_enabled', 'promotable_to_vehicle', 'vehicle_activation_allowed'), False),
  }
  canonical(result)
  return result
