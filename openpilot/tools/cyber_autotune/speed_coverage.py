"""Pure descriptive speed coverage; no log access, learner or tuning authority.

Caller owns exact schema/provenance and route/segment boundaries. Histogram bins
are display resolution, not tune knots. Counts are not independent observations.
"""
from collections.abc import Iterable
from dataclasses import dataclass
import math

BIN_WIDTH_MPS = 1
OVERFLOW_MPS = 60
BIN_COUNT = OVERFLOW_MPS + 1
MAX_GAP_NS = 200_000_000  # Descriptive continuity marker, not a vehicle/learner limit.
MAX_SAMPLES = 2_000_000  # Bound processing, never silently truncate an input.


@dataclass(frozen=True)
class SegmentCoverage:
  counts: tuple[int, ...]
  total: int
  accepted: int
  invalid: int
  duplicate: int
  backward: int
  gaps: int
  observed_interval_ns: int
  interval_min_ns: int | None
  interval_max_ns: int | None
  minimum_mps: float | None
  maximum_mps: float | None


def summarize_segment(samples: Iterable[tuple[int, bool, float]]) -> SegmentCoverage:
  """Process file order, without sorting or continuity across segments.

  An invalid observation or non-forward timestamp breaks adjacent-valid duration.
  After a reset, the reset observation is excluded; subsequent timestamps use the
  new epoch. Positive inter-message deltas include gaps and invalid-speed events.
  No timestamps or raw samples are retained in the returned summary.
  """
  counts = [0] * BIN_COUNT
  total = accepted = invalid = duplicate = backward = gaps = duration = 0
  previous_time = interval_min = interval_max = minimum = maximum = None
  previous_valid = False
  for timestamp, valid, speed in samples:
    total += 1
    if total > MAX_SAMPLES:
      raise ValueError('SAMPLE_LIMIT')
    if type(timestamp) is not int or not 0 <= timestamp < 2**64:
      invalid += 1
      previous_time, previous_valid = None, False
      continue
    delta = timestamp - previous_time if previous_time is not None else None
    previous_time = timestamp
    if delta is not None and delta <= 0:
      duplicate += delta == 0
      backward += delta < 0
      previous_valid = False
      continue
    if delta is not None:
      interval_min = delta if interval_min is None else min(interval_min, delta)
      interval_max = delta if interval_max is None else max(interval_max, delta)
      gaps += delta > MAX_GAP_NS
    if valid is not True or type(speed) not in (float, int) or not math.isfinite(speed) or speed < 0:
      invalid += 1
      previous_valid = False
      continue
    counts[min(math.floor(speed / BIN_WIDTH_MPS), OVERFLOW_MPS)] += 1
    accepted += 1
    minimum = float(speed) if minimum is None else min(minimum, float(speed))
    maximum = float(speed) if maximum is None else max(maximum, float(speed))
    if previous_valid and delta is not None and delta <= MAX_GAP_NS:
      duration += delta
    previous_valid = True
  return SegmentCoverage(tuple(counts), total, accepted, invalid, duplicate, backward,
                         gaps, duration, interval_min, interval_max, minimum, maximum)


def _validate(segment: SegmentCoverage) -> None:
  if not isinstance(segment, SegmentCoverage):
    raise ValueError('INVALID_SEGMENT_SUMMARY')
  counters = (segment.total, segment.accepted, segment.invalid, segment.duplicate,
              segment.backward, segment.gaps, segment.observed_interval_ns)
  if (any(type(value) is not int or value < 0 for value in counters) or
      type(segment.counts) is not tuple or len(segment.counts) != BIN_COUNT or
      any(type(value) is not int or value < 0 for value in segment.counts) or
      sum(segment.counts) != segment.accepted or segment.total > MAX_SAMPLES or
      segment.accepted + segment.invalid + segment.duplicate + segment.backward != segment.total or
      segment.gaps > max(0, segment.total - 1) or
      segment.observed_interval_ns > max(0, segment.accepted - 1) * MAX_GAP_NS):
    raise ValueError('INVALID_SEGMENT_SUMMARY')
  for low, high in ((segment.minimum_mps, segment.maximum_mps), (segment.interval_min_ns, segment.interval_max_ns)):
    if low is None and high is None:
      continue
    if (type(low) not in (int, float) or type(high) not in (int, float) or
        not math.isfinite(low) or not math.isfinite(high) or not 0 <= low <= high):
      raise ValueError('INVALID_SEGMENT_SUMMARY')
  if (segment.accepted == 0) != (segment.minimum_mps is None):
    raise ValueError('INVALID_SEGMENT_SUMMARY')


def summarize_routes(routes: tuple[tuple[SegmentCoverage, ...], ...]) -> dict:
  """Equal-weight nonempty routes; pilot routes represent selected segments only.

  This trusted in-process summary is not an authenticated evidence importer.
  Quality/empty counts remain visible. Completeness is descriptive input quality,
  never statistical confidence, operational-domain sufficiency or qualification.
  """
  if type(routes) is not tuple or any(type(route) is not tuple for route in routes):
    raise ValueError('INVALID_ROUTES')
  segments = [segment for route in routes for segment in route]
  for segment in segments:
    _validate(segment)
  counts = tuple(sum(segment.counts[i] for segment in segments) for i in range(BIN_COUNT))
  route_counts = [tuple(sum(segment.counts[i] for segment in route) for i in range(BIN_COUNT)) for route in routes]
  nonempty = [row for row in route_counts if sum(row)]
  accepted = sum(counts)
  invalid = sum(segment.invalid + segment.duplicate + segment.backward for segment in segments)
  empty_segments = sum(segment.accepted == 0 for segment in segments)
  return {
    'schema_version': 1,
    'status': 'DESCRIPTIVE_COMPLETE' if nonempty and len(nonempty) == len(routes) and not invalid and not empty_segments
              else 'DESCRIPTIVE_INCOMPLETE',
    'bin_width_mps': BIN_WIDTH_MPS, 'overflow_lower_mps': OVERFLOW_MPS,
    'gap_marker_ns': MAX_GAP_NS, 'counts': counts,
    'route_count': len(routes), 'nonempty_route_count': len(nonempty), 'empty_route_count': len(routes) - len(nonempty),
    'segment_count': len(segments), 'empty_segment_count': empty_segments,
    'total': sum(segment.total for segment in segments), 'accepted': accepted,
    'invalid': sum(segment.invalid for segment in segments),
    'duplicate': sum(segment.duplicate for segment in segments), 'backward': sum(segment.backward for segment in segments),
    'gaps': sum(segment.gaps for segment in segments),
    'observed_interval_ns': sum(segment.observed_interval_ns for segment in segments),
    'interval_min_ns': min((segment.interval_min_ns for segment in segments if segment.interval_min_ns is not None), default=None),
    'interval_max_ns': max((segment.interval_max_ns for segment in segments if segment.interval_max_ns is not None), default=None),
    'minimum_mps': min((segment.minimum_mps for segment in segments if segment.minimum_mps is not None), default=None),
    'maximum_mps': max((segment.maximum_mps for segment in segments if segment.maximum_mps is not None), default=None),
    'sample_proportions': tuple(count / accepted for count in counts) if accepted else None,
    'route_balanced_proportions': tuple(math.fsum(row[i] / sum(row) for row in nonempty) / len(nonempty)
                                      for i in range(BIN_COUNT)) if nonempty else None,
    'candidate_generation_allowed': False, 'confidence_qualified': False, 'runtime_accepted': False, 'promotable': False,
  }
