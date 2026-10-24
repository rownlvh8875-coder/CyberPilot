"""Exact dyadic certificates. Floating active-set work proposes, never decides."""

from fractions import Fraction
from functools import reduce
from math import gcd, lcm

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f

UNKNOWN = 'SEPARATION_CERTIFICATE_INCONCLUSIVE'
RESOURCE = UNKNOWN + '_RESOURCE_BOUND'


def checked(x, y=None):
  f.matrix(x)
  return None if y is None else f.labels(y, len(x))


def binding(x, y=None):
  checked(x, y)
  return f.identity({'X': x, 'y': None if y is None else np.asarray(y, dtype=np.int64)})


def integers(values):
  """One common dyadic denominator; no text/decimal conversion."""
  pairs = [float(v).as_integer_ratio() for v in values]
  denominator = max((d for _, d in pairs), default=1)
  return [n * (denominator // d) for n, d in pairs], denominator


def determinant(a):
  """Fraction-free Bareiss, exact pivoting/divisibility."""
  a = [list(map(int, row)) for row in a]
  n, sign, previous = len(a), 1, 1
  f.need(n > 0 and all(len(row) == n for row in a))
  for k in range(n - 1):
    if not a[k][k]:
      pivot = next((i for i in range(k + 1, n) if a[i][k]), None)
      if pivot is None:
        return 0
      a[k], a[pivot], sign = a[pivot], a[k], -sign
    pivot = a[k][k]
    for i in range(k + 1, n):
      for j in range(k + 1, n):
        numerator = a[i][j] * pivot - a[i][k] * a[k][j]
        f.need(numerator % previous == 0, 'V4_EXACT_ARITHMETIC_CONFLICT')
        a[i][j] = numerator // previous
      a[i][k] = 0
    previous = pivot
  return sign * a[-1][-1]


def minor_determinant(x):
  rows = [integers(row) for row in x]
  numerator = determinant([row for row, _ in rows])
  denominator = reduce(lambda a, row: a * row[1], rows, 1)
  result = Fraction(numerator, denominator)
  return result.numerator, result.denominator


def rank_verify(x, certificate, *, binding=None):
  try:
    checked(x)
    p = x.shape[1]
    singular = np.linalg.svd(x, compute_uv=False)
    tol = float(singular[0] * max(x.shape) * np.finfo(np.float64).eps)
    f.need(np.isfinite(singular).all() and int(np.count_nonzero(singular > tol)) == p)
    f.need(
      certificate['status'] == 'RANK_CERTIFICATE_PASS'
      and certificate['rank'] == p
      and certificate['columns'] == p
      and certificate['count'] == len(x)
      and certificate['tolerance'] == tol
      and certificate['singular_values'] == singular.tolist()
    )
    f.need(certificate['matrix_sha256'] == globals()['binding'](x) and certificate['binding'] == (binding or {}))
    rows = certificate['rows']
    f.need(len(rows) == p and len(set(rows)) == p and all(type(i) is int and 0 <= i < len(x) for i in rows))
    num, den = minor_determinant(x[rows])
    f.need(num != 0 and certificate['determinant'] == [str(num), str(den)])
    f.need(certificate['determinant_sign'] == (1 if num > 0 else -1) and certificate['determinant_bits'] == abs(num).bit_length())
    f.need(certificate['certificate_sha256'] == f.identity({k: v for k, v in certificate.items() if k != 'certificate_sha256'}))
    return True
  except (ValueError, KeyError, TypeError, OverflowError, np.linalg.LinAlgError):
    return False


def rank_generate(x, *, binding=None, max_rows=None):
  checked(x)
  n, p = x.shape
  try:
    singular = np.linalg.svd(x, compute_uv=False)
    tolerance = float(singular[0] * max(x.shape) * np.finfo(np.float64).eps)
    rank = int(np.count_nonzero(singular > tolerance))
    if not np.isfinite(singular).all() or rank != p:
      return {'status': 'RANK_SVD_FAILURE'}
    if max_rows is not None and max_rows <= 0:
      return {'status': 'RANK_CERTIFICATE_INCONCLUSIVE'}
    # Exact incremental elimination finds first independent rows, at most P rows retained.
    pivots, rows = {}, []
    limit = n if max_rows is None else min(n, max_rows)
    for index in range(limit):
      q = [Fraction.from_float(float(v)) for v in x[index]]
      for pivot, row in sorted(pivots.items()):
        amount = q[pivot]
        if amount:
          q = [a - amount * b for a, b in zip(q, row, strict=True)]
      pivot = next((j for j, a in enumerate(q) if a), None)
      if pivot is not None:
        scale = q[pivot]
        pivots[pivot] = [a / scale for a in q]
        rows.append(index)
      if len(rows) == p:
        break
    if len(rows) != p:
      return {'status': 'RANK_EXACT_MINOR_NOT_FOUND' if limit == n else 'RANK_CERTIFICATE_INCONCLUSIVE'}
    num, den = minor_determinant(x[rows])
    result = {
      'status': 'RANK_CERTIFICATE_PASS',
      'matrix_sha256': globals()['binding'](x),
      'binding': binding or {},
      'rows': rows,
      'determinant': [str(num), str(den)],
      'determinant_sign': 1 if num > 0 else -1,
      'determinant_bits': abs(num).bit_length(),
      'rank': rank,
      'columns': p,
      'count': n,
      'tolerance': tolerance,
      'singular_values': singular.tolist(),
    }
    result['certificate_sha256'] = f.identity(result)
    f.need(rank_verify(x, result, binding=binding), 'V4_RANK_CERTIFICATE_CONFLICT')
    return result
  except (np.linalg.LinAlgError, ArithmeticError, ValueError):
    return {'status': 'RANK_CERTIFICATE_INCONCLUSIVE'}


def column_sums(a):
  """Exact sums, bounded column working memory, repeated values compressed exactly."""
  result = []
  for j in range(a.shape[1]):
    values, counts = np.unique(a[:, j], return_counts=True)
    nums, den = integers(values)
    result.append(Fraction(sum(v * int(c) for v, c in zip(nums, counts, strict=True)), den))
  return result


def canonical_integer(values):
  denominator = reduce(lcm, (v.denominator for v in values), 1)
  integers_ = [v.numerator * (denominator // v.denominator) for v in values]
  divisor = reduce(gcd, map(abs, integers_), 0) or 1
  return [v // divisor for v in integers_]


def solve_exact(a, b):
  """Small active rational system only; exact Gaussian elimination."""
  n = len(b)
  rows = [list(row) + [target] for row, target in zip(a, b, strict=True)]
  for k in range(n):
    pivot = next((i for i in range(k, n) if rows[i][k]), None)
    if pivot is None:
      raise ValueError('V4_ACTIVE_SET_DEPENDENT')
    rows[k], rows[pivot] = rows[pivot], rows[k]
    scale = rows[k][k]
    rows[k] = [v / scale for v in rows[k]]
    for i in range(n):
      if i != k and rows[i][k]:
        scale = rows[i][k]
        rows[i] = [v - scale * w for v, w in zip(rows[i], rows[k], strict=True)]
  return [row[-1] for row in rows]


def exact_proposal(a, sums, active):
  rows = [[Fraction.from_float(float(v)) for v in a[i]] for i in active]
  gram = [[sum((u * v for u, v in zip(row, other, strict=True)), Fraction()) for other in rows] for row in rows]
  rhs = [-sum((u * v for u, v in zip(row, sums, strict=True)), Fraction()) for row in rows]
  q = solve_exact(gram, rhs) if active else []
  residual = [v + sum((qj * row[j] for qj, row in zip(q, rows, strict=True)), Fraction()) for j, v in enumerate(sums)]
  return q, residual


def proof_payload(certificate):
  keys = ('matrix_sha256', 'kind', 'D', 'active') if certificate['kind'] == 'ABSENCE' else ('matrix_sha256', 'kind', 'direction')
  return {k: certificate[k] for k in keys}


def separation_verify(x, y, certificate):
  unknown = {'status': UNKNOWN}
  try:
    y = checked(x, y)
    f.need(type(certificate) is dict and certificate['matrix_sha256'] == binding(x, y))
    proof_sha = f.identity(proof_payload(certificate))
    f.need('certificate_sha256' not in certificate or certificate['certificate_sha256'] == proof_sha)
    a = np.ascontiguousarray(x * (2 * y - 1)[:, None])
    if certificate['kind'] == 'ABSENCE':
      d, active = certificate['D'], certificate['active']
      f.need(type(d) is int and d > 0 and len(active) <= x.shape[1])
      indices = [i for i, _ in active]
      f.need(indices == sorted(set(indices)) and all(type(i) is int and 0 <= i < len(x) for i in indices))
      f.need(all(type(q) is int and q > 0 for _, q in active) and reduce(gcd, [d] + [q for _, q in active]) == 1)
      sums = column_sums(a)
      for j, value in enumerate(sums):
        residual = d * value + sum((q * Fraction.from_float(float(a[i, j])) for i, q in active), Fraction())
        f.need(residual == 0)
      status = 'NO_SEPARATION'
      counts = {'exact_verification_rows': len(x), 'active_count': len(active)}
    elif certificate['kind'] == 'PRESENCE':
      direction = certificate['direction']
      f.need(len(direction) == x.shape[1] and all(type(v) is int for v in direction) and reduce(gcd, map(abs, direction), 0) == 1)
      # Compress equal signed rows, exactly, no approximate sign authority.
      used = [j for j, value in enumerate(direction) if value]
      f.need(bool(used))
      unique, counts_ = np.unique(a[:, used], axis=0, return_counts=True)
      positive, zero = 0, 0
      for row, count in zip(unique, counts_, strict=True):
        nums, _ = integers(row)
        margin = sum(v * direction[j] for v, j in zip(nums, used, strict=True))
        f.need(margin >= 0)
        if margin > 0:
          positive += int(count)
        else:
          zero += int(count)
      f.need(positive > 0)
      status = 'SEPARATION_PRESENT'
      counts = {'exact_verification_rows': len(x), 'positive_margin_count': positive, 'zero_margin_count': zero}
    else:
      return unknown
    return {'status': status, 'certificate_sha256': proof_sha, **counts}
  except (ValueError, TypeError, KeyError, OverflowError, ArithmeticError):
    return unknown


def separation_generate(x, y, *, max_iterations=None):
  """Deterministic NNLS active proposals; exactify/verify each, incomplete but sound."""
  y = checked(x, y)
  a = np.ascontiguousarray(x * (2 * y - 1)[:, None])
  n, p = x.shape
  sums, active, iterations, seen = column_sums(a), [], 0, set()
  limit = 4 * p * p if max_iterations is None else max_iterations  # Operational cap, never scientific verdict.
  active_max, passes = 0, 1
  base = {'matrix_sha256': binding(x, y)}
  while iterations < limit:
    iterations += 1
    try:
      q, residual = exact_proposal(a, sums, active)
      if all(v >= 0 for v in q):
        if not any(residual):
          values = canonical_integer([Fraction(1), *q])
          cert = {**base, 'kind': 'ABSENCE', 'D': values[0], 'active': [[i, v] for i, v in sorted(zip(active, values[1:], strict=True)) if v]}
        else:
          cert = {**base, 'kind': 'PRESENCE', 'direction': canonical_integer(residual)}
        verification = separation_verify(x, y, cert)
        passes += 1
        if verification['status'] != UNKNOWN:
          return {**cert, **verification, 'iterations': iterations, 'active_max': active_max, 'logical_full_row_passes': passes}
      # Floating point only proposes a different active set.
      target = -np.asarray([float(v) for v in sums])
      f.need(np.isfinite(target).all())
      if active:
        proposed, _, _, _ = np.linalg.lstsq(a[active].T, target, rcond=None)
        negative = [k for k, v in enumerate(proposed) if v <= 0]
        if negative:
          del active[min(negative, key=lambda k: active[k])]
          continue
        r = -target + a[active].T @ proposed
      else:
        r = -target
      costs = a @ r
      passes += 1
      f.need(np.isfinite(costs).all())
      order = np.argsort(costs, kind='stable')
      next_row = next((int(i) for i in order if int(i) not in active), None)
      if next_row is None or costs[next_row] >= 0 or len(active) >= p:
        break
      active.append(next_row)
      active_max = max(active_max, len(active))
      active.sort()
      key = tuple(active)
      if key in seen:
        break
      seen.add(key)
    except (ValueError, ArithmeticError, np.linalg.LinAlgError, OverflowError):
      break
  return {
    **base,
    'status': RESOURCE if iterations >= limit else UNKNOWN,
    'iterations': iterations,
    'active_max': active_max,
    'logical_full_row_passes': passes,
    'exact_verification_rows': 0,
  }
