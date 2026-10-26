"""SG-A standalone command-only projection. No core/plant/model imports or IO hooks."""

from dataclasses import dataclass
import math
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune.candidate_architecture import hash_object
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load
from openpilot.tools.cyber_autotune.smoothness_v0_baseline import BASELINE_IDENTITY


class InterventionTimeline:
  """EXPERIMENT-owned input audit, NOT SG command-shaping state or a delay queue."""

  def __init__(self):
    self.previous = None

  def check(self, row):
    if type(row) is not c.InterventionInput:
      raise ValueError('EXACT_INTERVENTION_INPUT_REQUIRED')
    old = self.previous
    if old is not None and not math.isclose(row.time_s - old.time_s, 0.01, rel_tol=0.0, abs_tol=1e-12):
      raise ValueError('CAUSAL_CONTIGUOUS_TIME_REQUIRED')
    release = old is not None and old.steering_pressed and not row.steering_pressed
    reengage = old is not None and not old.active and row.active
    if row.release != release or row.reengagement != reengage:
      raise ValueError('EXACT_INTERVENTION_TRANSITIONS_REQUIRED')
    events = ['EXPERIMENT_START'] if old is None else []
    if not row.active and (old is None or old.active):
      events.append('INACTIVE')
    if row.steering_pressed and (old is None or not old.steering_pressed):
      events.append('STEERING_PRESSED')
    if release:
      events.append('RELEASE')
    if reengage:
      events.append('REENGAGEMENT')
    return events

  def commit(self, row):
    self.previous = row


@dataclass(frozen=True)
class StandaloneOutput:
  """SG_STANDALONE_OUTPUT_V1: versioned enabled extension; old disabled schema unmodified."""

  pre_governor: float
  post_governor: float
  final_requested_torque: float
  governor_state: tuple
  saturation_reason: str
  core_source_sha256: str
  core_config_sha256: str
  governor_identity_sha256: str
  state_before: float | None
  state_after: float | None
  action: str
  reset_events: tuple
  core_input_saturated: bool
  governor_output_saturated: bool
  governor_limit_active: bool
  state_owner: str = 'SG'
  physical_delay_owner: str = 'PLANT'

  def __post_init__(self):
    for value in (self.pre_governor, self.post_governor, self.final_requested_torque):
      c.torque(value)
    for value in (self.core_source_sha256, self.core_config_sha256, self.governor_identity_sha256):
      c.sha(value)
    if (
      self.final_requested_torque != self.post_governor
      or abs(self.post_governor) > abs(self.pre_governor)
      or self.post_governor * self.pre_governor < 0
      or self.state_owner != 'SG'
      or self.physical_delay_owner != 'PLANT'
    ):
      raise ValueError('SG_OUTPUT_AUTHORITY_CONTRACT')
    for value in (self.state_before, self.state_after):
      if value is not None:
        c.torque(value)
    actions = ('INACTIVE_ZERO_RESET', 'DISABLED_EXACT_PASSTHROUGH', 'FRESH_CURRENT_COMMAND_REBASE', 'UNIT_DELTA_PROJECTED', 'UNITY_PASSTHROUGH')
    events = ('EXPERIMENT_START', 'INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT')
    if (
      self.action not in actions
      or self.saturation_reason != self.action
      or type(self.reset_events) is not tuple
      or any(e not in events for e in self.reset_events)
      or len(set(self.reset_events)) != len(self.reset_events)
    ):
      raise ValueError('EXACT_SG_ACTION_RESET_REASON_REQUIRED')
    if self.action == 'INACTIVE_ZERO_RESET':
      if self.pre_governor != 0.0 or self.post_governor != 0.0 or self.state_after is not None:
        raise ValueError('INACTIVE_ZERO_STATE_REQUIRED')
    elif self.state_after is None:
      raise ValueError('ACTIVE_SG_LAST_COMMAND_REQUIRED')
    if self.action in ('DISABLED_EXACT_PASSTHROUGH', 'FRESH_CURRENT_COMMAND_REBASE'):
      if self.post_governor != self.pre_governor:
        raise ValueError('EXACT_PASSTHROUGH_REQUIRED')
    if self.action in ('UNIT_DELTA_PROJECTED', 'UNITY_PASSTHROUGH'):
      if self.state_before is None or self.reset_events or self.post_governor != max(self.state_before - 1.0, min(self.state_before + 1.0, self.pre_governor)):
        raise ValueError('EXACT_ORDINARY_PROJECTION_REQUIRED')
      if (self.action == 'UNIT_DELTA_PROJECTED') != self.governor_limit_active:
        raise ValueError('EXACT_PROJECTOR_ACTION_REQUIRED')
    expected_state = () if self.state_after is None else (self.state_after,)
    if self.governor_state != expected_state or (self.state_after is not None and self.state_after != self.post_governor):
      raise ValueError('EXACT_SG_LAST_OUTPUT_STATE_REQUIRED')
    if (
      self.core_input_saturated != (abs(self.pre_governor) == 1.0)
      or self.governor_output_saturated != (abs(self.post_governor) == 1.0)
      or self.governor_limit_active != (self.post_governor != self.pre_governor)
    ):
      raise ValueError('EXACT_SATURATION_SEMANTICS_REQUIRED')
    if any(type(v) is not bool for v in (self.core_input_saturated, self.governor_output_saturated, self.governor_limit_active)):
      raise ValueError('BOOLEAN_REQUIRED')


class Governor:
  def __init__(self, mode, baseline_source_sha256, baseline_config_sha256):
    policy = load()
    if type(mode) is not str or mode not in policy['config']['allowed_configs']:
      raise ValueError('ONLY_CANONICAL_SG_CONFIGS_ALLOWED')
    c.sha(baseline_source_sha256)
    c.sha(baseline_config_sha256)
    if (baseline_source_sha256, baseline_config_sha256) != (BASELINE_IDENTITY['source_sha256'], BASELINE_IDENTITY['config_sha256']):
      raise ValueError('ONLY_SOURCE_PINNED_NATIVE_BASELINE_ALLOWED')
    self._mode = self._frozen_mode = mode
    self._source = baseline_source_sha256
    self._config = baseline_config_sha256
    self._last = None
    self.timeline = InterventionTimeline()
    self.identity = hash_object(
      {
        'role': 'SG_STANDALONE',
        'family': 'SG-A',
        'mode': mode,
        'source_sha256': digest(Path(__file__).read_bytes()),
        'config_sha256': policy['config']['receipt_sha256'],
        'core_source_sha256': self._source,
        'core_config_sha256': self._config,
      }
    )
    self._initial_identity = self.identity
    self._initial_core = (self._source, self._config)

  def update(self, command, intervention):
    if self._mode != self._frozen_mode or self.identity != self._initial_identity or (self._source, self._config) != self._initial_core:
      raise ValueError('RUNTIME_SG_CONFIG_MUTATION')
    if type(command) is not c.GovernorCommand:
      raise ValueError('EXACT_COMMAND_INPUT_REQUIRED')
    if (command.core_source_sha256, command.core_config_sha256) != self._initial_core:
      raise ValueError('UNCHANGED_BASELINE_CORE_IDENTITY_REQUIRED')
    events = self.timeline.check(intervention)
    u = command.normalized_torque
    if self._last is not None:
      c.torque(self._last)
    before = self._last
    if not intervention.active:
      if u != 0.0:
        raise ValueError('INACTIVE_BASELINE_COMMAND_MUST_BE_ZERO')
      y, after, action = u, None, 'INACTIVE_ZERO_RESET'
    elif self._mode == 'SG_DISABLED':
      y, after, action = u, u, 'DISABLED_EXACT_PASSTHROUGH'
    elif intervention.steering_pressed or events or before is None:
      y, after, action = u, u, 'FRESH_CURRENT_COMMAND_REBASE'
    else:
      # Radius1 is the minimum admitting zero for EVERY previous command in [-1,1].
      # Hence sign/magnitude preserving; not a physical slew rate or time constant.
      y = max(before - 1.0, min(before + 1.0, u))
      after = y
      action = 'UNIT_DELTA_PROJECTED' if y != u else 'UNITY_PASSTHROUGH'
    result = StandaloneOutput(
      u,
      y,
      y,
      () if after is None else (after,),
      action,
      self._source,
      self._config,
      self.identity,
      before,
      after,
      action,
      tuple(events),
      abs(u) == 1.0,
      abs(y) == 1.0,
      u != y,
    )
    self._last = after
    self.timeline.commit(intervention)
    return result
