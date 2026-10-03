"""Offline frozen-point TLS diagnostic, never a confidence or update authority.

Numerical formula adapted from MIT-licensed openpilot torqued. No estimator
construction, Params, random selection, raw-log reading or runtime integration.
Caller-supplied provenance and signal declarations are bindings, not authentication.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS


ALGORITHM = 'cyber-frozen-torqued-tls-v1'
SIGNAL_CONTRACT = 'torqued-v1:negative-applied-normalized-torque:calibrated-roll-corrected-mps2:lag-aligned-once'
MIN_POINTS = 3  # Algebraic minimum only, not independent samples or confidence.
MAX_POINTS = 12000  # Resource cap: upstream eight buckets * 1500 points.
FRICTION_FACTOR = 1.5  # Upstream residual-spread multiplier, not physical identification.
QUALIFICATION_BLOCKERS = ('RAW_SELECTION_ALIGNMENT_UNVERIFIED', 'INDEPENDENT_CONFIDENCE_UNAVAILABLE',
                         'PHYSICAL_FRICTION_NOT_IDENTIFIED', 'EVIDENCE_AND_CANDIDATE_ADMISSION_REQUIRED')


@dataclass(frozen=True)
class TorquePoint:
  sample_sha256: str
  time_ns: int
  normalized_command: float
  lateral_accel_mps2: float


@dataclass(frozen=True)
class TorqueFitInput:
  points: tuple[TorquePoint, ...]
  role: str
  provenance: tuple[tuple[str, str], ...]
  signal_contract: str


@dataclass(frozen=True)
class TorqueEstimate:
  lat_accel_factor: float
  lat_accel_offset_mps2: float
  native_residual_spread_coefficient: float
  residual_rmse_mps2: float


@dataclass(frozen=True)
class TorqueIdentificationReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  point_count: int = 0
  estimate: TorqueEstimate | None = None
  algorithm: str = field(default=ALGORITHM, init=False)
  confidence: None = field(default=None, init=False)
  independent_sample_count: None = field(default=None, init=False)
  parameter_identification_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_input(request):
  if (type(request) is not TorqueFitInput or type(request.role) is not str or request.role != 'development_fit' or
      type(request.signal_contract) is not str or request.signal_contract != SIGNAL_CONTRACT or
      type(request.provenance) is not tuple or len(request.provenance) != len(PROVENANCE_KEYS) or
      type(request.points) is not tuple or not MIN_POINTS <= len(request.points) <= MAX_POINTS):
    return False
  if any(type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str or
         type(pair[1]) is not str or not is_sha256(pair[1]) for pair in request.provenance):
    return False
  if {key for key, _ in request.provenance} != PROVENANCE_KEYS:
    return False
  seen = set()
  previous_time = -1
  for point in request.points:
    if (type(point) is not TorquePoint or type(point.sample_sha256) is not str or not is_sha256(point.sample_sha256) or
        point.sample_sha256 in seen or type(point.time_ns) is not int or not previous_time < point.time_ns < 2**63 or
        not finite_number(point.normalized_command) or not finite_number(point.lateral_accel_mps2) or
        not -.5 <= point.normalized_command < .5 or abs(point.normalized_command) <= .02 or abs(point.lateral_accel_mps2) > 1.):
      return False
    seen.add(point.sample_sha256)
    previous_time = point.time_ns
  return min(p.normalized_command for p in request.points) < 0 < max(p.normalized_command for p in request.points)


def identify_torque(request: TorqueFitInput) -> TorqueIdentificationReport:
  """Fit an entire fixed selection. Never infer reviewed evidence from its digest."""
  if not _valid_input(request):
    return TorqueIdentificationReport('BLOCKED', ('INVALID_FROZEN_FIT_INPUT',))
  payload = asdict(request)
  payload['provenance'] = sorted(request.provenance)
  payload['algorithm'] = ALGORITHM
  digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
  count = len(request.points)
  points = np.array([[p.normalized_command, 1., p.lateral_accel_mps2] for p in request.points], dtype=np.float64)
  try:
    with np.errstate(all='raise'):
      _, singular_values, vectors = np.linalg.svd(points, full_matrices=False)
      relative_tolerance = np.finfo(np.float64).eps * max(points.shape)
      tolerance = relative_tolerance * singular_values[0]
      if (singular_values[1] <= tolerance or singular_values[1] - singular_values[2] <= tolerance or
          abs(vectors[2, 2]) <= relative_tolerance):
        raise ValueError('DEGENERATE_TLS')
      slope, offset = -vectors[2, :2] / vectors[2, 2]
      if not np.isfinite(slope) or slope <= 0:
        raise ValueError('NONPOSITIVE_FACTOR')
      # Preserve the native positive-slope rotation exactly; no alternative OLS fit.
      sin = np.sqrt(slope ** 2 / (slope ** 2 + 1))
      cos = np.sqrt(1 / (slope ** 2 + 1))
      _, spread = (points[:, [0, 2]] @ np.array([[cos, -sin], [sin, cos]])).T
      coefficient = np.std(spread) * FRICTION_FACTOR
      residual = points[:, 2] - (slope * points[:, 0] + offset)
      rmse = np.sqrt(np.mean(residual ** 2))
      values = tuple(float(value) for value in (slope, offset, coefficient, rmse))
      if not all(finite_number(value) for value in values):
        raise ValueError('NONFINITE_TLS')
  except (np.linalg.LinAlgError, FloatingPointError, ValueError, OverflowError):
    return TorqueIdentificationReport('BLOCKED', ('NUMERICALLY_UNIDENTIFIABLE',), digest, count)
  return TorqueIdentificationReport('NUMERICAL_DIAGNOSTIC', QUALIFICATION_BLOCKERS, digest, count, TorqueEstimate(*values))
