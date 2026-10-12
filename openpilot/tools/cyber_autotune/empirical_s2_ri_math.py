"""S2-RI source-grid coordinates and causal X only. No model or prediction."""
import numpy as np

FORMS = ((0, 1, 1), (0, 45, 45), (20, 1, 1), (20, 45, 45))
SCOPES = ('SCOPE_ALL_ACTIVE_NO_OVERRIDE', 'SCOPE_NON_RAIL_ACTIVE_NO_OVERRIDE')
DT = 10_000_000
AGE = 20_000_000
MIN_SUPPORT = 201


def grid_ticks(values):
  """Candidate nearest code is accepted ONLY after exact Float32 reconstruction.

  Zero is an internal invalid-coordinate sentinel; the returned validity mask
  must accompany coordinates. Never fill a missing observation with this zero.
  """
  values = np.asarray(values)
  if values.dtype != np.float64 or values.ndim != 1:
    raise ValueError('EXACT_FLOAT64_SOURCE_CACHE_REQUIRED')
  finite = np.isfinite(values)
  candidate = np.zeros(len(values), dtype=np.float64)
  candidate[finite] = np.rint(values[finite]/.1)
  valid = finite & (candidate >= -32768) & (candidate <= 32767)
  decoded = (candidate[valid]*.1).astype(np.float32).astype(np.float64)
  valid[np.flatnonzero(valid)] &= decoded == values[valid]
  ticks = np.zeros(len(values), dtype=np.int64)
  ticks[valid] = candidate[valid].astype(np.int64)
  return ticks, valid


def target_indices(data):
  """Only adjacent eligible samples in one contiguous admitted streak."""
  s = data['streak']
  return np.flatnonzero((s[:-1] > 0) & (s[1:] == s[:-1]+1))


def history_required(form):
  if tuple(form) not in FORMS or any(type(x) is not int for x in form):
    raise ValueError('PREDECLARED_BOUNDARY_FORM_REQUIRED')
  d, lu, ld = form
  return max(d+lu, ld+1)


def feature_indices(data, form):
  ids = target_indices(data)
  return ids[data['streak'][ids] >= history_required(form)]


def feature_matrix(data, indices, form):
  """Past observed increments j>=1; next angle and target values never accessed."""
  required = history_required(form)
  if indices.ndim != 1 or indices.dtype.kind not in 'iu':
    raise ValueError('EXACT_HISTORY_INDICES_REQUIRED')
  if len(indices) and (np.any(indices < required-1) or np.any(indices >= len(data['streak']))
                       or np.any(data['streak'][indices] < required)):
    raise ValueError('ELIGIBLE_CONTIGUOUS_HISTORY_REQUIRED_NO_PADDING')
  d, lu, ld = form
  columns = [np.ones(len(indices))]
  names = ['intercept']
  for i in range(lu):
    offset = d+i
    columns.append(data['command'][indices-offset])
    names.append(f'command_offset_{offset}')
  for j in range(1, ld+1):
    columns.append(data['tick'][indices-j+1]-data['tick'][indices-j])
    names.append(f'past_increment_{j}')
  columns.extend((data['tick'][indices], data['speed'][indices]))
  names.extend(('angle_tick_k', 'speed_k'))
  return np.ascontiguousarray(np.column_stack(columns), dtype=np.float64), names
