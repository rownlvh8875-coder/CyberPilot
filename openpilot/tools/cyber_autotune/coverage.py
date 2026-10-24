"""Conservative corpus coverage from reviewed labels, never from repeat counts.

Groups/labels must be bound to independently reviewed evidence by the caller.
This module does not classify raw samples or prove statistical independence.
"""
from dataclasses import dataclass

from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA


@dataclass(frozen=True)
class CoverageGroup:
  vehicle_group: str
  route_group: str
  day_group: str
  strata: tuple[str, ...]


def valid_group(group: CoverageGroup) -> bool:
  return (isinstance(group, CoverageGroup) and
          all(isinstance(value, str) and value.strip() for value in (group.vehicle_group, group.route_group, group.day_group)) and
          isinstance(group.strata, tuple) and bool(group.strata) and
          all(isinstance(name, str) and name in REQUIRED_STRATA for name in group.strata) and
          len(set(group.strata)) == len(group.strata))


@dataclass(frozen=True)
class CoverageReport:
  sufficient: bool
  counts: tuple[tuple[str, int], ...]
  blockers: tuple[str, ...]


def summarize_coverage(groups: tuple[CoverageGroup, ...], policy: CoveragePolicy) -> CoverageReport:
  """Count each vehicle/route/day at most once per condition across all windows.

Minimums here explicitly refer to distinct reviewed groups, not frame counts.
Do not infer review authority merely from a supplied policy's hash.
"""
  if (not isinstance(policy, CoveragePolicy) or not isinstance(groups, tuple) or not groups or
      not all(valid_group(group) for group in groups)):
    return CoverageReport(False, (), ('INVALID_COVERAGE_GROUPS',))
  memberships = {name: set() for name in REQUIRED_STRATA}
  for group in groups:
    for name in group.strata:
      memberships[name].add((group.vehicle_group, group.route_group, group.day_group))
  counts = tuple((name, len(memberships[name])) for name in sorted(REQUIRED_STRATA))
  blockers = tuple(f'REQUIRED_COVERAGE_MISSING:{name}' for name, minimum in policy.minimum_counts if len(memberships[name]) < minimum)
  return CoverageReport(not blockers, counts, blockers)
