"""Authority-free torque TLS from frozen sufficient statistics.

The Gram matrix represents rows ``[normalized_command, 1, lateral_accel]``.
This module never opens raw logs, constructs the live learner, writes Params,
or grants confidence, candidate, runtime, or promotion authority.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.torque_identification import TorqueEstimate


ALGORITHM = 'cyber-torqued-gram-tls-v1'
MIN_POINTS = 3
MAX_POINTS = 10_000_000
FRICTION_FACTOR = 1.5


@dataclass(frozen=True)
class TorqueGramInput:
  point_count: int
  gram_xtx: tuple[tuple[float, ...], ...]
  bucket_counts: tuple[int, ...]
  source_sha256: str


@dataclass(frozen=True)
class TorqueGramReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  point_count: int = 0
  estimate: TorqueEstimate | None = None
  algorithm: str = field(default=ALGORITHM, init=False)
  parameter_identification_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_request(request) -> bool:
  if (type(request) is not TorqueGramInput or type(request.point_count) is not int or
      not MIN_POINTS <= request.point_count <= MAX_POINTS or
      type(request.gram_xtx) is not tuple or len(request.gram_xtx) != 3 or
      any(type(row) is not tuple or len(row) != 3 for row in request.gram_xtx) or
      type(request.bucket_counts) is not tuple or len(request.bucket_counts) != 8 or
      any(type(count) is not int or count < 0 for count in request.bucket_counts) or
      sum(request.bucket_counts) != request.point_count or not is_sha256(request.source_sha256)):
    return False
  values = tuple(value for row in request.gram_xtx for value in row)
  if any(not finite_number(value) for value in values):
    return False
  gram = np.array(request.gram_xtx, dtype=np.float64)
  scale = max(1., float(np.max(np.abs(gram))))
  symmetry_tolerance = np.finfo(np.float64).eps * max(request.point_count, 3) * scale * 8.
  if not np.allclose(gram, gram.T, rtol=0., atol=symmetry_tolerance):
    return False
  count_tolerance = np.finfo(np.float64).eps * max(request.point_count, 3) * 8.
  return abs(float(gram[1, 1]) - request.point_count) <= count_tolerance


def _digest(request: TorqueGramInput) -> str:
  payload = asdict(request)
  payload['algorithm'] = ALGORITHM
  return hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()


def _blocked(reason: str, digest=None, count=0) -> TorqueGramReport:
  return TorqueGramReport('BLOCKED', (reason,), digest, count)


def fit_torque_gram(request: TorqueGramInput) -> TorqueGramReport:
  """Fit the complete frozen Gram matrix; never infer confidence or authority."""
  if not _valid_request(request):
    return _blocked('INVALID_GRAM_INPUT')
  digest = _digest(request)
  gram = np.array(request.gram_xtx, dtype=np.float64)
  count = request.point_count
  try:
    with np.errstate(all='raise'):
      eigenvalues, eigenvectors = np.linalg.eigh(gram)
      largest = max(1., float(eigenvalues[-1]))
      relative_tolerance = np.finfo(np.float64).eps * max(count, 3)
      psd_tolerance = relative_tolerance * largest * 8.
      if float(eigenvalues[0]) < -psd_tolerance:
        raise ValueError('INDEFINITE_GRAM')
      eigenvalues = np.maximum(eigenvalues, 0.)
      singular = np.sqrt(eigenvalues[::-1])
      tolerance = relative_tolerance * singular[0]
      vector = eigenvectors[:, 0]
      if (singular[1] <= tolerance or singular[1] - singular[2] <= tolerance or
          abs(vector[2]) <= relative_tolerance):
        raise ValueError('DEGENERATE_TLS')
      slope, offset = -vector[:2] / vector[2]
      if not np.isfinite(slope) or slope <= 0 or not np.isfinite(offset):
        raise ValueError('NONPOSITIVE_FACTOR')

      x2, sum_x, xy = gram[0]
      _, n, sum_y = gram[1]
      _, _, y2 = gram[2]
      sin = np.sqrt(slope ** 2 / (slope ** 2 + 1.))
      cos = np.sqrt(1. / (slope ** 2 + 1.))
      spread_sum = -sin * sum_x + cos * sum_y
      spread_square_sum = sin ** 2 * x2 - 2. * sin * cos * xy + cos ** 2 * y2
      spread_variance = spread_square_sum / n - (spread_sum / n) ** 2
      variance_tolerance = relative_tolerance * max(1., abs(spread_square_sum / n)) * 16.
      if spread_variance < -variance_tolerance:
        raise ValueError('NEGATIVE_VARIANCE')
      spread_variance = max(0., float(spread_variance))

      coefficient = np.sqrt(spread_variance) * FRICTION_FACTOR
      residual_square_sum = (
        y2 + slope ** 2 * x2 + n * offset ** 2 - 2. * slope * xy -
        2. * offset * sum_y + 2. * slope * offset * sum_x
      )
      residual_tolerance = relative_tolerance * max(1., abs(y2), abs(slope ** 2 * x2)) * 32.
      if residual_square_sum < -residual_tolerance:
        raise ValueError('NEGATIVE_RESIDUAL_ENERGY')
      rmse = np.sqrt(max(0., float(residual_square_sum)) / n)
      values = tuple(float(value) for value in (slope, offset, coefficient, rmse))
      if not all(finite_number(value) for value in values):
        raise ValueError('NONFINITE_TLS')
  except (np.linalg.LinAlgError, FloatingPointError, ValueError, OverflowError):
    return _blocked('NUMERICALLY_UNIDENTIFIABLE', digest, count)

  return TorqueGramReport(
    status='NUMERICAL_DIAGNOSTIC',
    blockers=('CONFIDENCE_NOT_ESTABLISHED', 'CANDIDATE_GENERATION_NOT_AUTHORIZED'),
    input_sha256=digest,
    point_count=count,
    estimate=TorqueEstimate(*values),
  )
