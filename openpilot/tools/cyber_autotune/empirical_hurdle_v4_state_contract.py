"""Synthetic causal context witness, not a model, private loader or rollout executor.

One-step uses the admitted observed predecessor, never the preceding stored row.
After initialization the simulator accepts projected integer ticks only. Logged
future command/vEgo remain the existing exogenous replay contract, outside this bit.
"""

from dataclasses import dataclass

from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import require


@dataclass(frozen=True)
class Frame:
  route: str
  segment: str
  causal_run: str
  index: int
  within_index: int
  grid_ns: int
  eligible: bool
  streak: int


def tick(value):
  require(type(value) is int and -32768 <= value <= 32767, 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  return value


def observed_context(*, previous, current, previous_tick, current_tick, scope):
  require(scope == 'SYNTHETIC_ONLY', 'V4_TWO_CONTEXT_SYNTHETIC_ONLY_OR_SCHEMA_CONFLICT')
  require(type(previous) is Frame and type(current) is Frame, 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  require(all(type(v) is int for f in (previous, current) for v in (f.index, f.within_index, f.grid_ns, f.streak)),
          'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  require(all(f.index >= f.within_index >= 0 and f.grid_ns >= 0 and 1 <= f.streak <= f.within_index + 1 for f in (previous, current)),
          'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  require(all(type(v) is str and v for f in (previous, current) for v in (f.route, f.segment, f.causal_run)),
          'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  require(previous.eligible is True and current.eligible is True and previous.streak >= 1 and current.streak == previous.streak + 1,
          'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  require((previous.route, previous.segment, previous.causal_run) == (current.route, current.segment, current.causal_run)
          and current.index == previous.index + 1 and current.within_index == previous.within_index + 1
          and current.grid_ns == previous.grid_ns + 10_000_000, 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
  return int(tick(current_tick) - tick(previous_tick) != 0)


class ProjectedContext:
  """No sticky gate state; boundaries invalidate until a fresh observed pair exists."""

  def __init__(self, *, previous, current, previous_tick, current_tick, scope):
    self.bit = observed_context(previous=previous, current=current, previous_tick=previous_tick, current_tick=current_tick, scope=scope)
    self.current_tick = tick(current_tick)
    self.available = True

  def advance(self, *, projected_tick, provenance):
    require(self.available and provenance == 'PROJECTED_INFERENCE', 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
    next_tick = tick(projected_tick)
    self.bit = int(next_tick - self.current_tick != 0)
    self.current_tick = next_tick
    return self.bit

  def boundary(self, kind):
    require(kind in ('ROUTE', 'SEGMENT', 'CAUSAL_RUN', 'ELIGIBILITY', 'GRID'), 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
    self.available = False
    self.bit = None

  def context(self):
    require(self.available, 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT')
    return self.bit
