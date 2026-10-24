"""Frozen S2-RI numerical primitives. No filesystem, controller or raw-log API."""
import numpy as np

CANDIDATES = tuple(f'S2RI_D{d:02d}_L{length:02d}' for d in (0,5,10,20) for length in (1,5,15,45))
HORIZONS = (25,50,100,200)
MIN_SUPPORT = 201


def parameters(candidate):
  if candidate not in CANDIDATES:
    raise ValueError('EXACT_FROZEN_CANDIDATE_REQUIRED')
  return int(candidate[6:8]), int(candidate[10:12])


def finite(*arrays):
  if any(not np.all(np.isfinite(x)) for x in arrays):
    raise ValueError('CANDIDATE_FOLD_NUMERICAL_FAILURE_NONFINITE')


def anchors(data, candidate, horizon):
  d, length = parameters(candidate)
  if type(horizon) is not int or horizon not in (1,*HORIZONS):
    raise ValueError('EXACT_FROZEN_HORIZON_REQUIRED')
  streak = data['streak']
  required = max(d+length,length+1)
  if len(streak) <= horizon:
    return np.array([],dtype=np.int64)
  return np.flatnonzero((streak[:-horizon] >= required) & (streak[horizon:] == streak[:-horizon]+horizon))


def features(data, indices, candidate):
  d, length = parameters(candidate)
  required = max(d+length,length+1)
  if (indices.ndim != 1 or indices.dtype.kind not in 'iu'
      or np.any(np.diff(indices) <= 0) or np.any(indices < required-1)
      or np.any(indices >= len(data['streak']))):
    raise ValueError('ORDERED_UNIQUE_CAUSAL_ANCHORS_REQUIRED')
  if np.any(data['streak'][indices] < required):
    raise ValueError('FULL_ELIGIBLE_HISTORY_REQUIRED_NO_PADDING')
  columns = [np.ones(len(indices))]
  columns.extend(data['command'][indices-offset] for offset in range(d+length-1,d-1,-1))
  columns.extend(data['tick'][indices-offset+1]-data['tick'][indices-offset] for offset in range(length,0,-1))
  columns.extend((data['tick'][indices],data['speed'][indices]))
  x = np.ascontiguousarray(np.column_stack(columns),dtype=np.float64)
  finite(x)
  return x


def project(next_tick):
  finite(next_tick)
  projected = np.rint(next_tick)
  if np.any((projected < -32768) | (projected > 32767)):
    raise ValueError('CANDIDATE_FOLD_NUMERICAL_FAILURE_SIGNED16_RANGE')
  return projected.astype(np.int64)


def normalizer(x, *, role):
  if role != 'TRAIN':
    raise ValueError('TRAIN_ONLY_NORMALIZATION_REQUIRED')
  if x.dtype != np.float64 or x.ndim != 2 or not len(x) or not np.all(x[:,0] == 1):
    raise ValueError('FLOAT64_DESIGN_UNSCALED_INTERCEPT_REQUIRED')
  finite(x)
  mean, std = x.mean(axis=0), x.std(axis=0,ddof=0)
  finite(mean,std)
  constant = std == 0
  constant[0] = False
  effective = np.flatnonzero(~constant)
  return {'mean':mean,'std':std,'constant':constant,'effective':effective}


def transform(x,norm):
  finite(x)
  idx = norm['effective']
  z = np.ones((len(x),len(idx)),dtype=np.float64)
  z[:,1:] = (x[:,idx[1:]]-norm['mean'][idx[1:]])/norm['std'][idx[1:]]
  finite(z)
  return z


def fit(x,y,*,role,on_solve=None):
  finite(y)
  if y.dtype != np.float64 or y.shape != (len(x),):
    raise ValueError('FLOAT64_TARGET_SHAPE_REQUIRED')
  norm = normalizer(x,role=role)
  z = transform(x,norm)
  rank = int(np.linalg.matrix_rank(z))
  if rank != z.shape[1]:
    raise ValueError('FIT_PRECONDITION_RANK_FAILURE')
  if on_solve is not None:
    on_solve()
  coeff, _, returned_rank, singular = np.linalg.lstsq(z,y,rcond=None)
  if returned_rank != rank:
    raise ValueError('NUMERICAL_RANK_CONFLICT')
  finite(coeff,singular)
  nominal = np.zeros(x.shape[1],dtype=np.float64)
  nominal[norm['effective']] = coeff
  condition = float(singular[0]/singular[-1])
  finite(np.array([condition]))
  return {'normalizer':norm,'coefficients':coeff,'nominal_coefficients':nominal,
          'rank':rank,'condition':condition,'effective_x':z}


def predict(x,model):
  finite(model['coefficients'])
  value = transform(x,model['normalizer']) @ model['coefficients']
  finite(value)
  return value


def metrics(error):
  if error.dtype != np.float64 or error.ndim != 1 or len(error) < MIN_SUPPORT:
    raise ValueError('CANDIDATE_FOLD_INSUFFICIENT_SUPPORT')
  finite(error)
  absolute = np.abs(error)
  value = {'rmse':float(np.sqrt(np.mean(error*error))), 'mae':float(np.mean(absolute)),
           'p95':float(np.percentile(absolute,95,method='linear'))}
  finite(np.array(list(value.values())))
  return value


def one_step(x,current,target,model):
  delta = predict(x,model)
  next_tick = current.astype(np.float64)+delta
  projected = project(next_tick)
  observed_delta = (target-current).astype(np.float64)
  # User clarification preserves the original frozen binary64 error primitive.
  error = delta-observed_delta
  baseline_error = -observed_delta
  candidate, comparator = metrics(error), metrics(baseline_error)
  for result, observation in ((candidate,projected),(comparator,current)):
    distance = np.abs(observation-target)
    result['exact_hit'] = float(np.count_nonzero(distance == 0)/len(distance))
    result['within_one_tick'] = float(np.count_nonzero(distance <= 1)/len(distance))
  return {'candidate':candidate,'comparator':comparator}, {
    'prediction':delta,'projected':projected,'error':error,'comparator_error':baseline_error}


def recursive(initial_ticks, command, speed, candidate, model, horizon):
  """No future measured-state input exists. All rows are pre-admitted anchors.

  command[:,0] is u[k-d-L+1], speed[:,0] is v[k]. Only initial observed
  tick[k-L..k] is admitted; subsequent ticks are exclusively projected state.
  """
  d, length = parameters(candidate)
  n = len(initial_ticks)
  if (horizon not in HORIZONS or initial_ticks.shape != (n,length+1)
      or command.shape != (n,length+horizon-1) or speed.shape != (n,horizon)):
    raise ValueError('EXACT_ROLLOUT_HISTORY_AND_HORIZON_REQUIRED')
  finite(initial_ticks,command,speed)
  current = initial_ticks[:,-1].copy()
  past = np.diff(initial_ticks,axis=1)
  for h in range(horizon):
    x = np.column_stack((np.ones(n),command[:,h:h+length],past,current,speed[:,h])).astype(np.float64)
    new = project(current.astype(np.float64)+predict(x,model))
    past[:,:-1] = past[:,1:]
    past[:,-1] = new-current
    current = new
  return current
