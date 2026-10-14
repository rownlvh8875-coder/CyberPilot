"""Small synthetic Cartesian oracle with external, declarative benchmark policy."""

from dataclasses import dataclass
import math
import operator

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_math as m

AUTHORITY = 'FEASIBILITY_BENCHMARK_ONLY_NO_V4_POLICY_AUTHORITY'
OPS = {'<': operator.lt, '<=': operator.le, '==': operator.eq, '>=': operator.ge, '>': operator.gt}
PATHS = set(m.COUNT_FIELDS) | {'counts.' + k for k in m.COUNT_FIELDS} | {
  group + '.' + metric for group in ('all', 'move', 'hold_all', 'hold_move') for metric in ('rmse', 'mae', 'p95')}


def value(row, path):
  m.require(path in PATHS, 'V4_TWO_CONTEXT_POLICY_CONFLICT')
  if path in m.COUNT_FIELDS:
    return row['counts'][path]
  group, field = path.split('.')
  return None if row[group] is None else row[group][field]


@dataclass(frozen=True)
class Feasibility:
  clauses: tuple

  def __post_init__(self):
    m.require(type(self.clauses) is tuple and all(type(c) is tuple and len(c) == 3 for c in self.clauses), 'V4_TWO_CONTEXT_POLICY_CONFLICT')
    for left, op, right in self.clauses:
      m.require(left in PATHS and op in OPS, 'V4_TWO_CONTEXT_POLICY_CONFLICT')
      m.require(right in PATHS if type(right) is str else type(right) in (int, float) and math.isfinite(right), 'V4_TWO_CONTEXT_POLICY_CONFLICT')

  def accepts(self, row):
    for left, op, right in self.clauses:
      a, b = value(row, left), value(row, right) if type(right) is str else right
      if a is None or b is None or not OPS[op](a, b):
        return False
    return True

  def tp_floor(self):
    floors = [b for a, op, b in self.clauses if a in ('TP', 'counts.TP') and op == '>=' and type(b) is int]
    return max(floors) if floors else None


@dataclass(frozen=True)
class Objective:
  terms: tuple

  def __post_init__(self):
    m.require(type(self.terms) is tuple and len(self.terms) > 0 and all(type(t) is tuple and len(t) == 2 for t in self.terms),
              'V4_TWO_CONTEXT_POLICY_CONFLICT')
    m.require(all(path in PATHS and type(sign) is int and sign in (-1, 1) for path, sign in self.terms), 'V4_TWO_CONTEXT_POLICY_CONFLICT')

  def key(self, row):
    vals = [value(row, path) for path, _ in self.terms]
    m.require(all(v is not None and math.isfinite(v) for v in vals), 'V4_TWO_CONTEXT_UNDEFINED_OBJECTIVE')
    return tuple(sign * val for (_, sign), val in zip(self.terms, vals, strict=True))

  def primary_count(self):
    path, sign = self.terms[0]
    path = path.removeprefix('counts.')
    return (path, sign) if path in m.COUNT_FIELDS else None


@dataclass(frozen=True)
class ParameterTie:
  axes: tuple
  directions: tuple

  def __post_init__(self):
    m.require(type(self.axes) is tuple and type(self.directions) is tuple and self.axes in ((0, 1), (1, 0)) and len(self.directions) == 2,
              'V4_TWO_CONTEXT_TOTAL_TIE_KEY_REQUIRED')
    m.require(all(type(x) is int and x in (-1, 1) for x in self.directions), 'V4_TWO_CONTEXT_TOTAL_TIE_KEY_REQUIRED')

  def key(self, pair):
    # A signed axis permutation is injective on the finite pair domain.
    return tuple(self.directions[c] * float(pair[c]) for c in self.axes)


@dataclass(frozen=True)
class Policy:
  feasibility: Feasibility
  objective: Objective
  tie: ParameterTie
  authority: str

  def __post_init__(self):
    m.require(self.authority == AUTHORITY, 'V4_TWO_CONTEXT_NO_V4_POLICY_AUTHORITY')
    m.require(type(self.feasibility) is Feasibility and type(self.objective) is Objective and type(self.tie) is ParameterTie,
              'V4_TWO_CONTEXT_POLICY_CONFLICT')

  @property
  def identity(self):
    return p.sha(p.canonical({'feasibility': self.feasibility.clauses, 'objective': self.objective.terms,
                             'tie_axes': self.tie.axes, 'tie_directions': self.tie.directions, 'authority': self.authority}))

  def key(self, pair, row):
    return self.objective.key(row) + self.tie.key(pair)


def exhaustive(population, policy):
  """Every pair, with O(N) numeric workspace; stores only the selected aggregate."""
  m.require(type(policy) is Policy, 'V4_TWO_CONTEXT_POLICY_CONFLICT')
  domain = m.threshold_sets(population)
  best, selected, selected_row, feasible = None, None, None, 0
  for t0 in domain[0]:
    for t1 in domain[1]:
      pair = [float(t0), float(t1)]
      row = m.evaluate_pair(population, pair)
      if policy.feasibility.accepts(row):
        feasible += 1
        key = policy.key(pair, row)
        if best is None or key > best:
          best, selected, selected_row = key, pair, row
  return {'status': 'SYNTHETIC_EXACT_OPTIMUM_CERTIFIED' if best is not None else 'SYNTHETIC_NO_FEASIBLE_PAIR',
          'selected_pair': selected, 'selected_metrics': selected_row, 'selected_key': list(best) if best is not None else None,
          'domain_size': int(len(domain[0])) * int(len(domain[1])), 'feasible_pair_count': feasible, 'policy_sha256': policy.identity}


def separable_integer_benchmark(population, policy):
  """A different, unconstrained additive-count policy; never inherits pooled constraints."""
  m.require(not policy.feasibility.clauses and all(path.removeprefix('counts.') in m.COUNT_FIELDS for path, _ in policy.objective.terms),
            'SEPARABLE_BENCHMARK_REQUIRES_UNCONSTRAINED_ADDITIVE_INTEGER_POLICY')
  table = m.IntegerTables(population)
  chosen = []
  for c in (0, 1):
    def key(i, c=c):
      row = table.rows[c][i]
      return tuple(sign * row[path.removeprefix('counts.')] for path, sign in policy.objective.terms) + (
        policy.tie.directions[c] * float(table.domain[c][i]),)
    chosen.append(max(range(len(table.domain[c])), key=key))
  pair = table.pair(chosen)
  return {'selected_pair': pair, 'selected_metrics': m.evaluate_pair(population, pair), 'authority': AUTHORITY}
