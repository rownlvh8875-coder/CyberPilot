"""C-only seven-field saved numeric diagnostics; no model or decision execution.

The reviewed private caller authenticates current human authorization, B0/B1
controls, exact host/volume/output and frozen protocol/code. Prior B1 results
pin each raw/NPY/payload hash and recorded original order. This is an exact
reader boundary, not a process-wide OS sandbox. No other source is opened.
"""

import struct
import zlib
import math as scalar

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b0_metadata as b0
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_evidence as b1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_train_score as train
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_c_math as math

SUCCESS = 'C_DIAGNOSTIC_AGGREGATION_COMPLETE'
COUNTERS = (
  'model_refit_calls',
  'normalizer_refit_calls',
  'stage2_refit_calls',
  'calibration_fit_calls',
  'threshold_readings',
  'threshold_application_calls',
  'threshold_reselection_calls',
  'train_gate_reconstruction_calls',
  'prediction_replay_calls',
  'rollout_regeneration_calls',
  'candidate_search_calls',
  'selection_calls',
  'holdout_openings',
  'holdout_discovery',
  'raw_log_openings',
  'qlog_openings',
  'mixed_carrier_openings',
  'vehicle_activation_calls',
  'source_writes',
)


def need(condition, code='C_INPUT_CONFLICT'):
  if not condition:
    raise ValueError(code)


def inputs(previous, completion):
  """Authenticate both prior scopes; preserve recorded order, never infer from N."""
  need(set(completion) == {'binding', 'result', 'resume'})
  bind, result, resume = (completion[k] for k in ('binding', 'result', 'resume'))
  for value in (bind, result, resume):
    train.check_seal(value)
  request = {**bind['request'], 'binding_sha256': bind['receipt_sha256']}
  train.catalog(request, previous)
  need(bind['schema'] == 'CYBERPILOT_V4_B1_TRAIN_PRIVATE_BINDING_V1')
  train.verify_only(result, b1.sha(b0._canonical(result)), bind['receipt_sha256'])
  need(resume['status'] == 'B1_TRAIN_VERIFY_ONLY_PASS' and resume['source_file_openings'] == resume['recompute_calls'] == 0)
  need(resume['result_raw_sha256'] == b1.sha(b0._canonical(result)) and resume['binding_sha256'] == bind['receipt_sha256'])
  need(result['previous_binding_sha256'] == previous['binding']['receipt_sha256'])
  need(result['previous_result_receipt_sha256'] == previous['result']['receipt_sha256'])
  old = previous['binding']['request']
  old_paths, new_paths = b1.paths(old), train.paths(request)
  jobs = []
  for index, job in enumerate(old['jobs']):
    fields = []
    trained = result['fields'][index]
    need((trained['candidate_id'], trained['fold']) == (job['candidate_id'], job['fold']) and trained['status'] == 'PASS')
    for offset, (role, owner, field) in enumerate(b1.FIELDS):
      count = job['train_count' if role == 'TRAIN' else 'dev_count']
      anchor = job['train_anchor' if role == 'TRAIN' else 'dev_anchor']
      dtype = '<i8' if field == 'prior_delta_tick' else ('<f8' if field in ('p_move', 'combined_probability') else '|b1')
      if offset == 0:
        proof = trained['replicas'][0]
        need(proof['replica'] == 'V4_REPEAT_1' and proof['original_descriptor_compared'] is False)
        hashes = {'file_sha256': proof['compressed_sha256'], 'npy_sha256': proof['npy_sha256'], 'array_sha256': proof['payload_sha256']}
      else:
        row = previous['result']['fields'][index * 7 + offset]
        need(
          (row['candidate_id'], row['fold'], row['role'], row['owner'], row['field'], row['status'])
          == (job['candidate_id'], job['fold'], role, owner, field, 'PASS')
        )
        proof = row['replicas'][0]
        need(proof['replica'] == ('V4_REPEAT_1' if owner == 'V4' else 'V1_REFERENCE'))
        need(proof['hash_schema_shape_dtype'] == 'PASS')
        if owner == 'V1_REFERENCE':
          need(proof['population_receipt_sha256'] == job['v1_train_receipt' if role == 'TRAIN' else 'v1_dev_receipt'])
        hashes = {k: proof[k] for k in ('file_sha256', 'npy_sha256', 'array_sha256')}
      need(proof['anchor_sha256'] == anchor and proof['row_alignment'] == 'RECORDED_ORIGINAL_ORDER_PROVENANCE_VERIFIED', 'C_ALIGNMENT_NOT_PROVEN')
      need(proof['shape'] == [count] and proof['dtype'] == dtype and proof['order'] == 'C')
      root = old['roots']['V4_REPEAT_1' if owner == 'V4' else 'V1_REFERENCE']
      path = root + '/candidates/' + job['candidate_id'] + '/' + job['fold'] + ('/train/' if role == 'TRAIN' else '/one-step/') + field + '.npy.gz'
      cap = b1.byte_caps(count, dtype)[0]
      need((old_paths | new_paths).get(path) == (cap, 'array'), 'C_ALLOWLIST_CONFLICT')
      desc = dict(dtype=dtype, shape=[count], order='C', filename=field + '.npy.gz', storage_format='NPY_GZIP_V1', lossless_roundtrip_verified=True, **hashes)
      b1.descriptor(desc, count=count, dtype=dtype, field=field)
      fields.append(
        {'role': role, 'owner': owner, 'field': field, 'path': path, 'descriptor': desc, 'cap': cap, 'n': count, 'dtype': dtype, 'anchor_sha256': anchor}
      )
    jobs.append({'candidate_id': job['candidate_id'], 'fold': job['fold'], 'fields': fields})
  need(tuple((j['candidate_id'], j['fold']) for j in jobs) == b1.JOBS)
  paths = [v['path'] for j in jobs for v in j['fields']]
  need(len(paths) == len(set(paths)) == 224, 'C_ALIAS_CONFLICT')
  return jobs


def decode(raw, desc, count, dtype):
  """Full B1 hashes/header validation before approved C numeric interpretation."""
  b1.inspect_array(raw, desc, count=count, dtype=dtype)
  decoder = zlib.decompressobj(wbits=31)
  npy = decoder.decompress(raw, b1.byte_caps(count, dtype)[1] + 1)
  need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail)
  prefix = 10 if npy[6] == 1 else 12
  length = struct.unpack('<H' if prefix == 10 else '<I', npy[8:prefix])[0]
  payload = npy[prefix + length :]
  if dtype == '|b1':
    need(bool(np.all(np.frombuffer(payload, dtype='u1') <= 1)), 'C_BINARY_ENCODING_CONFLICT')
  values = np.frombuffer(payload, dtype=dtype)
  need(not values.flags.writeable and values.shape == (count,))
  return values


def run(request, previous, completion):
  report = {
    'schema': 'CYBERPILOT_V4_C_DIAGNOSTICS_V1',
    'status': 'C_DIAGNOSTIC_PARTIAL_INPUT_INSUFFICIENT',
    'binding_sha256': request.get('binding_sha256'),
    'protocol_sha256': request.get('protocol_sha256'),
    'jobs': [],
    'reads': dict.fromkeys(('array_file_openings', 'metadata_file_openings', 'array_bytes_read', 'metadata_bytes_read'), 0),
    'role_reads': {r: {'file_openings': 0, 'bytes_read': 0} for r in ('TRAIN', 'DEV')},
    'authorized_C_aggregation_calls': 0,
    'operation_counters': dict.fromkeys(COUNTERS, 0),
    'train_rowwise_gate': 'NOT_SAVED',
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
  reader = None
  try:
    need(request.get('authorized') is True, 'C_AUTHORIZATION_OR_PROTOCOL_BLOCKED')
    need(b0._digest(request.get('binding_sha256')) and b0._digest(request.get('protocol_sha256')))
    jobs = inputs(previous, completion)
    allowlist = {v['path']: (v['cap'], 'array') for j in jobs for v in j['fields']}
    with b1.GuardedReader(request['mount_root'], request['mount_identity'], allowlist) as reader:
      for job in jobs:
        role_arrays = {'TRAIN': {}, 'DEV': {}}
        for value in job['fields']:
          raw = reader.read(value['path'], value['cap'], 'array')
          counter = report['role_reads'][value['role']]
          counter['file_openings'] += 1
          counter['bytes_read'] += len(raw)
          role_arrays[value['role']][value['field']] = decode(raw, value['descriptor'], value['n'], value['dtype'])
          del raw
        tr, dev = role_arrays['TRAIN'], role_arrays['DEV']
        train_result = math.analyze(tr['combined_probability'], tr['move_label'], tr['prior_delta_tick'])
        dev_result = math.analyze(dev['p_move'], dev['true_move'], dev['prior_delta_tick'], gate=dev['predicted_gate'])
        report['jobs'].append(
          {
            'candidate_id': job['candidate_id'],
            'fold': job['fold'],
            'TRAIN': train_result,
            'DEV': dev_result,
            'transfer': math.transfer(train_result, dev_result),
          }
        )
        report['authorized_C_aggregation_calls'] += 1
        del tr, dev, role_arrays
      report['status'] = SUCCESS
  except (ValueError, KeyError, TypeError, AttributeError, OSError, zlib.error) as error:
    report['status'] = (
      'C_DIAGNOSTIC_AUTHORIZATION_OR_PROTOCOL_BLOCKED' if str(error) == 'C_AUTHORIZATION_OR_PROTOCOL_BLOCKED' else 'C_DIAGNOSTIC_INPUT_CONFLICT_FAIL_CLOSED'
    )
    report['error_code'] = error.code if isinstance(error, (b1.B1Error, b0.B0Error)) else 'C_VALIDATION_FAILED'
  finally:
    if reader is not None:
      report['reads'] = dict(reader.counters)
      role_by_path = {v['path']: v['role'] for j in jobs for v in j['fields']}
      for role in ('TRAIN', 'DEV'):
        events = [e for e in reader.events if role_by_path[str(reader.root) + '/' + e['member']] == role]
        report['role_reads'][role] = {'file_openings': sum(e['file_openings'] for e in events), 'bytes_read': sum(e['bytes_read'] for e in events)}
  return b1.sealed(report)


def compare_public(report, ranking, confusion):
  """Same saved one-step populations only; exact integer AUC/count comparison.

  2e-15 is an arithmetic roundoff allowance for the prior NumPy reduction versus
  the frozen C math.fsum reduction. It is not a performance acceptance margin.
  No historical aggregate substitutes for the current numeric computation.
  """
  for rows in (ranking['jobs'], confusion['jobs']):
    need(tuple((j['candidate_id'], j['fold']) for j in rows) == b1.JOBS)
  names = {'OVERALL': 'OVERALL', 'PREVIOUS_STATIC': 'PREV_STATIC', 'PREVIOUS_MOVE': 'PREV_MOVE'}
  transitions = dict(
    zip(math.TRANSITIONS, ('PREV_STATIC_TRUE_STATIC', 'PREV_STATIC_MOVE_ONSET', 'PREV_MOVE_TRUE_STATIC', 'PREV_MOVE_MOVE_CONTINUATION'), strict=True)
  )
  for current, old, gate in zip(report['jobs'], ranking['jobs'], confusion['jobs'], strict=True):
    for role, old_role in (('TRAIN', 'train'), ('DEV', 'development')):
      for context, old_context in names.items():
        new, prior = current[role]['scores'][context], old[old_role][old_context]
        need((new['n'], new['positives'], new['negatives']) == (prior['count'], prior['positive_count'], prior['negative_count']), 'C_PRIOR_SUPPORT_CONFLICT')
        need((new['auc']['numerator'], new['auc']['denominator']) == (prior['auc_num2'], prior['auc_den2']), 'C_PRIOR_AUC_CONFLICT')
        for name, prior_name in (
          ('brier', 'brier'),
          ('mean_probability', 'mean_probability'),
          ('prevalence', 'true_move_prevalence'),
          ('calibration_bias', 'calibration_bias'),
        ):
          need(scalar.isclose(new[name], prior[prior_name], rel_tol=0, abs_tol=2e-15), 'C_PRIOR_FLOAT_CONFLICT')
    need(current['DEV']['gates']['OVERALL']['counts'] == gate['confusion']['counts'], 'C_PRIOR_GATE_CONFLICT')
    for context, prior_context in transitions.items():
      row, prior = current['DEV']['transitions'][context], gate['contexts'][prior_context]
      need(
        row['n'] == prior['count'] and row['move_gate'] == prior['confusion']['counts']['TP'] + prior['confusion']['counts']['FP'],
        'C_PRIOR_TRANSITION_CONFLICT',
      )
  return {
    'status': 'MATCHING_ONE_STEP_POPULATIONS_AGREE',
    'jobs': 32,
    'auc_pair_counts': 'EXACT',
    'gate_counts': 'EXACT',
    'score_reduction_roundoff_allowance': 2e-15,
    'rollout_comparison': 'NOT_PERFORMED_DIFFERENT_POPULATION',
  }


def public_summary(report):
  train.check_seal(report)
  need(report['status'] == SUCCESS and tuple((j['candidate_id'], j['fold']) for j in report['jobs']) == b1.JOBS)
  need(report['authorized_C_aggregation_calls'] == 32 and report['reads']['array_file_openings'] == 224 and report['reads']['metadata_file_openings'] == 0)
  need(report['operation_counters'] == dict.fromkeys(COUNTERS, 0))
  need(report['train_rowwise_gate'] == 'NOT_SAVED' and report['replica_payload_equality'] == 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED')
  need(all(report[k] is False for k in (*b0.AUTHORITY_KEYS, 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED')))
  return {
    'status': SUCCESS,
    'processed_jobs': 32,
    'approved_fields': 224,
    'protocol_sha256': report['protocol_sha256'],
    'folds': math.public_folds(report['jobs']),
    'reads': report['reads'],
    'role_reads': report['role_reads'],
    'authorized_C_aggregation_calls': 32,
    'operation_counters': report['operation_counters'],
    'train_rowwise_gate': 'NOT_SAVED',
    'replica_payload_equality': report['replica_payload_equality'],
    'statistical_unit': 'CORRELATED_JOB_LEVEL_MEDIAN_MIN_MAX; NOT_POOLED',
    'public_bins': 'WITHHELD; NO_PUBLIC_CELL_TOTALS',
    'policy_effect': 'NOT_IDENTIFIABLE',
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }


def verify_only(report, expected_raw_sha256, binding_sha256):
  need(b1.sha(b0._canonical(report)) == expected_raw_sha256 and report['binding_sha256'] == binding_sha256, 'C_RESUME_CONFLICT')
  train.check_seal(report)
  need(report['schema'] == 'CYBERPILOT_V4_C_DIAGNOSTICS_V1' and report['status'] == SUCCESS)
  need(tuple((j['candidate_id'], j['fold']) for j in report['jobs']) == b1.JOBS)
  need(report['authorized_C_aggregation_calls'] == 32 and report['reads']['array_file_openings'] == 224)
  need(report['operation_counters'] == dict.fromkeys(COUNTERS, 0))
  need(all(report[k] is False for k in (*b0.AUTHORITY_KEYS, 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED')))
  return b1.sealed(
    {
      'schema': 'CYBERPILOT_V4_C_VERIFY_ONLY_V1',
      'status': 'C_VERIFY_ONLY_PASS',
      'result_raw_sha256': expected_raw_sha256,
      'binding_sha256': binding_sha256,
      'source_file_openings': 0,
      'recompute_calls': 0,
    }
  )
