"""Target-independent finite-matrix diagnostics, never parameter identification."""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

HISTORIES = tuple(range(1, 46))
LAGS = tuple(range(21))
MIN_SUPPORT = 201
DT_NS = 10_000_000


def support_gate(counts):
  return len(counts) == 2 and all(n >= MIN_SUPPORT for n in counts)


def streaks(mask, runs, within, grid):
  """Length of the admitted contiguous suffix. Call separately per segment."""
  n = len(mask)
  if any(len(a) != n for a in (runs, within, grid)) or mask.dtype.kind != 'b':
    raise ValueError('EXACT_ROW_LAYOUT_REQUIRED')
  result = np.zeros(n, dtype=np.int64)
  for k in range(n):
    if mask[k] and runs[k] >= 0:
      linked = (k > 0 and mask[k-1] and runs[k] == runs[k-1] and within[k] == within[k-1]+1
                and grid[k]-grid[k-1] == DT_NS)
      result[k] = result[k-1]+1 if linked else 1
  return result


def features(data, indices, family, parameter):
  """One frozen current/past X layout. No Y argument, future value or learned state."""
  if type(parameter) is not int or family not in ('S1', 'S2'):
    raise ValueError('PREDECLARED_FORM_REQUIRED')
  if family == 'S1' and parameter in LAGS:
    offsets = [parameter]
    names = ['angle_k', 'rate_native_k', f'command_lag_{parameter}', 'speed_k', 'intercept']
    if len(indices) and min(indices) < parameter:
      raise ValueError('PAST_HISTORY_REQUIRED')
    columns = [data['angle'][indices], data['rate'][indices], data['command'][indices-parameter],
               data['speed'][indices], np.ones(len(indices))]
  elif family == 'S2' and parameter in HISTORIES:
    offsets = list(range(parameter-1, -1, -1))
    if len(indices) and min(indices) < parameter-1:
      raise ValueError('PAST_HISTORY_REQUIRED')
    columns = [data[key][indices-offset] for key in ('command', 'angle') for offset in offsets]
    columns += [data['rate'][indices], data['speed'][indices]]
    names = [f'{key}_lag_{offset}' for key in ('command', 'angle') for offset in offsets] + ['rate_native_k', 'speed_k']
  else:
    raise ValueError('PREDECLARED_ENVELOPE_REQUIRED')
  return np.ascontiguousarray(np.column_stack(columns), dtype=np.float64), names


def rank_diagnostic(x, names):
  """Numerical rank of standardized X using NumPy's documented default tolerance.

  Constant features become zero; the explicitly named intercept remains one.
  No symbolic identifiability proof, state-space matrices, coefficients or cutoff.
  """
  if x.ndim != 2 or x.dtype != np.float64 or x.shape[1] != len(names) or len(set(names)) != len(names):
    raise ValueError('EXACT_FLOAT64_NAMED_X_REQUIRED')
  if not np.isfinite(x).all():
    raise ValueError('FINITE_INPUT_FEATURES_ONLY')
  n, columns = x.shape
  result = {'rows': n, 'columns': columns, 'feature_names': names, 'fitting_admission': False,
            'conditioning_status': 'CONDITION_NUMBER_REPORTED_NO_ACCEPTANCE_THRESHOLD',
            'rank_meaning': 'NUMERICAL_RANK_NOT_SYMBOLIC_STRUCTURAL_IDENTIFIABILITY_PROOF'}
  if not n:
    return {**result, 'numerical_rank': None, 'singular_values': [], 'condition_number': None,
            'status': 'NO_ADMITTED_FEATURE_ROWS', 'constant_columns': [], 'duplicate_columns': []}
  mean, std = np.mean(x, axis=0), np.std(x, axis=0, ddof=0)
  constant = np.ptp(x, axis=0) == 0
  z = np.zeros_like(x)
  varying = ~constant
  z[:, varying] = (x[:, varying]-mean[varying])/std[varying]
  if 'intercept' in names:
    i = names.index('intercept')
    if not np.all(x[:, i] == 1):
      raise ValueError('INTERCEPT_MUST_BE_EXACT_ONE')
    z[:, i] = 1
  hashes = [p.sha(np.ascontiguousarray(x[:, i]).tobytes()) for i in range(columns)]
  duplicate = [[names[i], names[j]] for i in range(columns) for j in range(i+1, columns) if hashes[i] == hashes[j]]
  singular = np.linalg.svd(z, full_matrices=False, compute_uv=False)
  tolerance = float(singular[0]*max(x.shape)*np.finfo(np.float64).eps) if singular.size else 0.
  rank = int(np.count_nonzero(singular > tolerance))
  condition = float(singular[0]/singular[-1]) if singular.size and singular[-1] > 0 else None
  if condition is not None and not np.isfinite(condition):
    condition = None
  covariance = (z.T @ z)/n
  # Correlation excludes all raw constant columns, including the retained intercept.
  pairs = [(abs(float(covariance[i, j])), i, j) for i in range(columns) for j in range(i+1, columns)
           if varying[i] and varying[j]]
  largest = max(pairs, default=None)
  return {**result, 'numerical_rank': rank, 'numpy_default_tolerance': tolerance,
    'singular_values': singular.tolist(), 'condition_number': condition,
    'condition_undefined_reason': 'ZERO_SMALLEST_SINGULAR_VALUE_OR_NONFINITE_RATIO' if condition is None else None,
    'status': 'FULL_RANK_DIAGNOSTIC' if rank == columns else 'RANK_DEFICIENT',
    'constant_columns': [names[i] for i in np.flatnonzero(constant)], 'duplicate_columns': duplicate,
    'population_feature_variances': np.square(std).tolist(),
    'standardized_input_second_moment_sha256': p.sha(covariance.tobytes()),
    'input_correlation_pair_count': len(pairs),
    'max_absolute_input_correlation': largest[0] if largest else None,
    'max_correlation_features': [names[largest[1]], names[largest[2]]] if largest else None,
    'constant_correlation': 'UNDEFINED_NOT_ZERO_FILLED'}


def correlation(a, b):
  if not len(a) or np.ptp(a) == 0 or np.ptp(b) == 0:
    return None
  return float(np.corrcoef(a, b)[0, 1])


def target_diagnostic(data, indices):
  """Next angle used only for counts, never feature construction or rank."""
  delta = data['angle'][indices+1]-data['angle'][indices]
  return {'count': len(indices), 'zero': int(np.count_nonzero(delta == 0)),
          'positive': int(np.count_nonzero(delta > 0)), 'negative': int(np.count_nonzero(delta < 0)),
          'unique_float_delta_levels': len(np.unique(delta)),
          'unique_source_grid_delta_codes': len(np.unique(np.rint(data['angle'][indices+1]/.1).astype(np.int64)
                                                         - np.rint(data['angle'][indices]/.1).astype(np.int64))),
          'usage': 'TARGET_AVAILABILITY_AND_EXCITATION_ONLY_NO_INPUT_RANK_OR_FEATURE_SELECTION'}


def rate_diagnostic(data, indices):
  dt = (data['state_time'][indices+1]-data['state_time'][indices]).astype(np.float64)/1e9
  if np.any(dt <= 0):
    raise ValueError('POSITIVE_SOURCE_TIME_DIFFERENCE_REQUIRED')
  delta = data['angle'][indices+1]-data['angle'][indices]
  fd = delta/dt
  rate = data['rate'][indices+1]
  valid = fd != 0
  ratios = rate[valid]/np.abs(fd[valid])
  quantiles = [float(v) for v in np.quantile(ratios, [.0, .5, .95, 1.])] if len(ratios) else None
  return {'status': 'EMPIRICAL_DIAGNOSTIC_ONLY_NOT_SOURCE_SEMANTIC_PROOF', 'source_semantics_promotable': False,
    'count': len(indices), 'rate_at': 'LATER_ADJACENT_STATE_SOURCE_TIME',
    'finite_difference_timebase': 'STRICTLY_POSITIVE_SELECTED_STATE_TIMESTAMP_DIFFERENCE',
    'rate_min': float(np.min(rate)) if len(rate) else None, 'rate_max': float(np.max(rate)) if len(rate) else None,
    'rate_negative': int(np.count_nonzero(rate < 0)), 'rate_zero': int(np.count_nonzero(rate == 0)),
    'rate_positive': int(np.count_nonzero(rate > 0)), 'fd_negative': int(np.count_nonzero(fd < 0)),
    'fd_zero': int(np.count_nonzero(fd == 0)), 'fd_positive': int(np.count_nonzero(fd > 0)),
    'correlation_signed_fd': correlation(rate, fd), 'correlation_absolute_fd': correlation(rate, np.abs(fd)),
    'rate_over_absolute_fd_quantiles_0_50_95_100': quantiles, 'ratio_count': len(ratios),
    'zero_rate_unchanged_angle': int(np.count_nonzero((rate == 0) & (delta == 0))),
    'zero_rate_changed_angle': int(np.count_nonzero((rate == 0) & (delta != 0))),
    'nonzero_rate_unchanged_angle': int(np.count_nonzero((rate != 0) & (delta == 0))),
    'nonzero_rate_changed_angle': int(np.count_nonzero((rate != 0) & (delta != 0)))}
