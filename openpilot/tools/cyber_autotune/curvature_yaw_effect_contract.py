"""Offline controller/input factorial groundwork; no path quality authority."""
import copy
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,finite,_keys,_hex

ROLES=('SYNTHETIC_GENERATOR','RECORDED_CONTROLLER_OUTPUT','OFFLINE_MODEL_OUTPUT')


def input_manifest(frames,*,source_role,source_sha256):
  if source_role not in ROLES or not _hex(source_sha256,64) or type(frames) is not list or not 2<=len(frames)<=4096:
    raise ValueError('INVALID_INPUT_SOURCE')
  for i,row in enumerate(frames):
    _keys(row,('time_ns','speed_mps','desired_curvature_1pm'))
    if (type(row['time_ns']) is not int or row['time_ns']!=i*10_000_000
        or not finite(row['speed_mps']) or not 3<=row['speed_mps']<=27 or not finite(row['desired_curvature_1pm'])):
      raise ValueError('INVALID_INPUT_FRAME')
  result={'source_role':source_role,'source_sha256':source_sha256,'frames':copy.deepcopy(frames),
          'frames_sha256':digest(canonical(frames)),'timebase_sha256':digest(canonical([r['time_ns'] for r in frames])),
          'independent_lane_truth':False,'trajectory_source':None,'path_truth_status':'NOT_PROVIDED'}
  result['receipt_sha256']=digest(canonical(result))
  return result


def freeze_experiment(controller_identities,input_manifests):
  if (type(controller_identities) is not list or len(controller_identities)!=2
      or len(set(controller_identities))!=2 or not all(_hex(v,64) for v in controller_identities)
      or type(input_manifests) is not list or len(input_manifests)!=2):
    raise ValueError('EXACT_TWO_DISTINCT_CONTROLLERS_TWO_INPUTS_REQUIRED')
  for manifest in input_manifests:
    fresh=input_manifest(manifest['frames'],source_role=manifest['source_role'],source_sha256=manifest['source_sha256'])
    if canonical(fresh)!=canonical(manifest):
      raise ValueError('INPUT_PROVENANCE_DRIFT')
  if (input_manifests[0]['timebase_sha256']!=input_manifests[1]['timebase_sha256']
      or input_manifests[0]['frames_sha256']==input_manifests[1]['frames_sha256']):
    raise ValueError('ALIGNED_DISTINCT_INPUTS_REQUIRED')
  result={'contract':'OFFLINE_CONTROLLER_VS_INPUT_FACTORIAL_GROUNDWORK',
          'controller_identities':copy.deepcopy(controller_identities),'input_manifests':copy.deepcopy(input_manifests),
          'trials':[{'controller_sha256':c,'input_manifest_sha256':m['receipt_sha256']}
                    for c in controller_identities for m in input_manifests],
          'controller_effect':'same input, different controller; descriptive tracking and command dynamics',
          'input_effect':'same controller, different input; synthetic or model input effect, no real path quality inference',
          'execution_status':'STRUCTURAL_MANIFEST_ONLY_NOT_EXECUTED',
          'lane_quality_judgment_permitted':False,'path_truth_status':'NOT_PROVIDED',
          'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
          'physical_delay_owner':'PLANT','vehicle_status':['NOT_READY','REAL_VEHICLE_UNVERIFIED','VEHICLE_ACTIVATION_BLOCKED']}
  result['receipt_sha256']=digest(canonical(result))
  return result
