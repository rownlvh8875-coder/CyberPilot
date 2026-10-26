"""Frozen numerical replay; added context and paths never enter model features."""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import sys
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates

CHUNK = 512  # Historical execution grouping, part of byte-exact replay.


def forbidden(*args, **kwargs):
  raise ValueError('ATTRIBUTION_RECONSTRUCTION_REFIT_FORBIDDEN')


@contextmanager
def firewall():
  """Live execution traps; no solver/normalizer/selector/raw reader fallback."""
  with ExitStack() as stack:
    for obj, names in ((np.linalg,('lstsq','solve','pinv')), (m,('fit','normalizer')), (gates,('select',))):
      for name in names:
        stack.enter_context(patch.object(obj,name,forbidden))
    # Block importing optimization and raw-decoder entry points in this process.
    stack.enter_context(patch.dict(sys.modules,dict.fromkeys((
      'scipy.optimize','openpilot.tools.lib.logreader','tools.lib.logreader',
      'openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_execution'),None)))
    yield


def exact(actual, expected, label):
  if (actual.dtype != expected.dtype or actual.shape != expected.shape
      or not actual.flags.c_contiguous or not expected.flags.c_contiguous
      or actual.tobytes() != expected.tobytes()):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_'+label+'_DIVERGENCE')


def binding(segments,candidate,horizon):
  blocks=[(s,m.anchors(s,candidate,horizon)) for s in segments]
  digest=p.sha(p.canonical([{'segment_sha256':s['segment_sha256'],'count':len(ix),
                            'indices_sha256':p.sha(ix.tobytes())} for s,ix in blocks]))
  return blocks,digest,sum(len(ix) for _,ix in blocks)


def require_anchor(segments,candidate,horizon,historical):
  blocks,digest,count=binding(segments,candidate,horizon)
  if digest != historical['anchor_sha256'] or digest != historical['comparator_anchor_sha256'] or count != historical['count']:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_ANCHOR_DIVERGENCE')
  return blocks


def context(blocks,candidate):
  d,length=m.parameters(candidate)
  items=[]
  for s,ix in blocks:
    speed=s['speed'][ix]
    items.append({
      'anchor_route_id':np.full(len(ix),s['route_id'],dtype='S64'),
      'anchor_segment_sha':np.full(len(ix),s['segment_sha256'],dtype='S64'),
      'anchor_index':ix.astype(np.int64),
      'speed_mps':speed,
      'speed_bin_code':np.where(speed<15,1,np.where(speed<25,2,3)).astype(np.int8),
      'rail':s['rail'][ix],'model_eligible':s['eligible'][ix],
      'prior_delta_tick':s['tick'][ix]-s['tick'][ix-1],
      's2_ri_run_id':s['run'][ix],'within_run_index':s['within'][ix],
      'command_current':s['command'][ix],
      'command_feature_newest':s['command'][ix-d],
      'command_history':s['command'][ix[:,None]+np.arange(-d-length+1,-d+1)],
    })
  result={k:np.ascontiguousarray(np.concatenate([v[k] for v in items])) for k in items[0]}
  result['anchor_order_index']=np.arange(len(result['anchor_index']),dtype=np.int64)
  return result


def one_step(blocks,candidate,model):
  x=np.concatenate([m.features(s,ix,candidate) for s,ix in blocks])
  current=np.concatenate([s['tick'][ix] for s,ix in blocks])
  target=np.concatenate([s['tick'][ix+1] for s,ix in blocks])
  metrics,buffers=m.one_step(x,current,target,model)
  return {**context(blocks,candidate),**buffers,'current_tick':current,
          'target_next_tick':target,'actual_delta_tick':target-current,
          'predicted_next_tick_continuous':current.astype(np.float64)+buffers['prediction'],
          'hold_last_next_tick':current.copy()},metrics


def recursive_path(initial_ticks,command,speed,candidate,model,horizon):
  """Exact historical operations, retaining every projected recursive state.

  No observed future angle argument exists. Observed paths are copied separately.
  """
  _,length=m.parameters(candidate)
  n=len(initial_ticks)
  if (horizon not in m.HORIZONS or initial_ticks.dtype != np.int64
      or initial_ticks.shape != (n,length+1) or command.shape != (n,length+horizon-1)
      or speed.shape != (n,horizon)):
    raise ValueError('EXACT_ROLLOUT_HISTORY_AND_HORIZON_REQUIRED')
  m.finite(initial_ticks,command,speed)
  path=np.empty((n,horizon+1),dtype=np.int64)
  current=initial_ticks[:,-1].copy()
  path[:,0]=current
  past=np.diff(initial_ticks,axis=1)
  for h in range(horizon):
    x=np.column_stack((np.ones(n),command[:,h:h+length],past,current,speed[:,h])).astype(np.float64)
    new=m.project(current.astype(np.float64)+m.predict(x,model))
    past[:,:-1]=past[:,1:]
    past[:,-1]=new-current
    current=new
    path[:,h+1]=current
  return path


def rollout(blocks,candidate,model,horizon):
  d,length=m.parameters(candidate)
  predicted,observed=[],[]
  for s,indices in blocks:
    for start in range(0,len(indices),CHUNK):
      ix=indices[start:start+CHUNK]
      ticks=s['tick'][ix[:,None]+np.arange(-length,1)]
      command=s['command'][ix[:,None]+np.arange(-d-length+1,horizon-d)]
      speed=s['speed'][ix[:,None]+np.arange(horizon)]
      predicted.append(recursive_path(ticks,command,speed,candidate,model,horizon))
      observed.append(s['tick'][ix[:,None]+np.arange(horizon+1)])
  path,truth=map(np.concatenate,(predicted,observed))
  initial,target=truth[:,0].copy(),truth[:,-1].copy()
  endpoint=path[:,-1].copy()
  error=(endpoint-target).astype(np.float64)
  baseline=(initial-target).astype(np.float64)
  return {**context(blocks,candidate),'initial_tick':initial,'target_endpoint_tick':target,
    'observed_path':truth,'projected_path':path,'hold_last_path':np.repeat(initial[:,None],horizon+1,axis=1),
    'projected':endpoint,'error':error,'comparator_error':baseline}, {
      'candidate':m.metrics(error),'comparator':m.metrics(baseline)}
