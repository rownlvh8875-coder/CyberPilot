import unittest
from importlib import import_module
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestS2RIPublication(unittest.TestCase):
  def module(self):
    return import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_schema')

  def test_unknown_schema_and_rows_rejected(self):
    for key in ('raw_samples', 'targets', 'coefficients', 'future_angle', 'private_path'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.module().public(p.seal({'schema': 'TEST', key: [1.2]}))

  def test_static_contract_drift_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_policy import contracts
    value = dict(contracts()['signal'])
    value['steering_rate_dependency'] = 'REQUIRED'
    with self.assertRaises(ValueError):
      self.module().public(p.seal({k: v for k, v in value.items() if k != 'receipt_sha256'}))

  def test_exact_contract_accepted(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_policy import contracts
    for value in contracts().values():
      self.module().public(value)

  def test_empty_fake_ready_rejected(self):
    with self.assertRaises(ValueError):
      self.module().validate_result(p.seal({'schema': 'EMPIRICAL_S2_RI_AUDIT_RESULTS_V1', 'forms': [],
                                         'rate_dependency': 'NONE'}), {}, {})

  def test_model_spec_future_and_extra_features_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_policy import validate_model_spec
    for value in ('angle[k+1]', 'command[k+1]', 'target', 'driver_torque', 'request', 'command*speed'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        validate_model_spec({'features': [value], 'target': 'MEASURED_ANGLE_GRID_INCREMENT_PER_SAMPLE'})

  def test_derived_proof_exact_fields_and_source(self):
    import tempfile
    import numpy as np
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
    from openpilot.tools.cyber_autotune.empirical_s2_ri_admission import derive
    from openpilot.tools.cyber_autotune.tests.test_empirical_s2_ri_admission import fixture
    from openpilot.tools.cyber_autotune import empirical_s2_ri_math as m
    s = self.module()
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      data = derive(fixture())
      for label, key in (('all', 'streak_all'), ('non_rail', 'streak_non_rail')):
        ix = m.target_indices({'streak': data[key]})
        mask = np.zeros(100, bool)
        mask[ix] = True
        delta = np.zeros(100, dtype=np.int64)
        delta[ix] = data['angle_tick'][ix+1]-data['angle_tick'][ix]
        data['target_available_'+label], data['delta_tick_'+label] = mask, delta
      bindings = {k: storage.array_write(root/(k+'.npy'), v) for k, v in data.items()}
      local = p.seal({'schema': 'EMPIRICAL_S2_RI_DERIVED_SEGMENT_V1', 'policy_sha256': 'a'*64,
        'source_receipt_sha256': 'b'*64, 'arrays': bindings, 'rate_and_request_adversarial_exact': True})
      s.validate_derived(local, root, 'a'*64, 'b'*64, 100)
      for mutate in ('source', 'missing', 'shape', 'flag'):
        bad = {k: v for k, v in local.items() if k != 'receipt_sha256'}
        bad['arrays'] = {k: dict(v) for k, v in bindings.items()}
        if mutate == 'source':
          bad['source_receipt_sha256'] = 'c'*64
        elif mutate == 'missing':
          bad['arrays'].pop('model_eligible')
        elif mutate == 'shape':
          bad['arrays']['model_eligible']['shape'] = [99]
        else:
          bad['rate_and_request_adversarial_exact'] = False
        with self.subTest(mutate=mutate), self.assertRaises(ValueError):
          s.validate_derived(p.seal(bad), root, 'a'*64, 'b'*64, 100)

  def test_complete_aggregate_bundle_mutations_fail_closed(self):
    import copy
    import json
    from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as policy
    # Published aggregate diagnostics are permitted test inputs. Admission metadata
    # here is synthetic; publication.build separately demands the real policy.
    pol = policy.policy()
    support = json.loads((p.PUBLIC/'empirical-s2-ri-support-v1.json').read_bytes())
    structure = json.loads((p.PUBLIC/'empirical-s2-ri-structural-diagnostics-v1.json').read_bytes())
    segments = []
    for rid, count in zip(pol['route_ids'], (70, 84), strict=True):
      for i in range(count):
        segments.append({'route_id': rid, 'rows': 6000, 'content_sha256': p.sha((rid+str(i)).encode()),
                         'receipt_sha256': p.sha(('receipt'+rid+str(i)).encode())})
    pol['source_segment_sets'] = {rid: {'count': sum(v['route_id'] == rid for v in segments),
      'set_sha256': p.sha(p.canonical(sorted(v['content_sha256'] for v in segments if v['route_id'] == rid)))}
      for rid in pol['route_ids']}
    pol = p.seal({k: v for k, v in pol.items() if k != 'receipt_sha256'})
    admission = p.seal({'schema': 'EMPIRICAL_S2_RI_INPUT_ADMISSION_V1', 'policy_sha256': pol['receipt_sha256'],
      'manifest_sha256': pol['resolution']['rlog_dataset_manifest_sha256'],
      'segment_receipts': [v['receipt_sha256'] for v in segments], 'segment_bindings': segments,
      'input_file_set_sha256': 'a'*64, 'array_access_before_admission': False})
    result = {'schema': 'EMPIRICAL_S2_RI_AUDIT_RESULTS_V1', 'policy_sha256': pol['receipt_sha256'],
      'admission_sha256': admission['receipt_sha256'], 'derived_receipt_set_sha256': 'b'*64, 'stream_count': 154,
      'counts': support['counts'], 'support': support['scopes'], 'forms': structure['forms'],
      'rate_dependency': 'NONE', 'request_dependency': 'NONE',
      'rate_views': ['ORIGINAL', 'DELETED', 'ALL_NAN_UNAVAILABLE', 'ARBITRARY_FINITE_AVAILABLE'],
      'generic_id_and_snapshot_overlays': 'EXACT_INVARIANT_NOT_GATES',
      'adversarial_derived_arrays_and_X_bytes_exact': True, 'adversarial_rank_executions_per_form': 3,
      'input_bytes_unchanged': True, 'qlog_arrays_opened': 0, 'raw_logs_opened': 0, 'authority': policy.AUTHORITY}
    self.module().validate_result(p.seal(result), pol, admission)
    mutations = (('forms', []), ('input_bytes_unchanged', False), ('qlog_arrays_opened', 1),
                 ('raw_logs_opened', 1), ('stream_count', 153), ('rate_dependency', 'AUXILIARY_REQUIRED'),
                 ('adversarial_derived_arrays_and_X_bytes_exact', False), ('private_samples', [1.2]))
    for key, value in mutations:
      bad = copy.deepcopy(result)
      bad[key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.module().validate_result(p.seal(bad), pol, admission)
    bad = copy.deepcopy(result)
    bad['forms'][0]['diagnostics'][pol['route_ids'][0]]['numerical_rank'] = 0
    with self.assertRaises(ValueError):
      self.module().validate_result(p.seal(bad), pol, admission)
