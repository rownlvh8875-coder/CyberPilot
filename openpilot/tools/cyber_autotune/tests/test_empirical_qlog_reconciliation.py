"""Source cadence, exact exclusions and immutable reconciliation regressions."""
import copy
import unittest

from openpilot.tools.cyber_autotune import empirical_qlog_source_audit as audit
from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation_policy as policy


class TestQlogAdmission(unittest.TestCase):
  def setUp(self):
    self.routes = [{'route_id': 'a', 'excluded_sources': []},
                   {'route_id': 'b', 'excluded_sources': [{'source_sha256': 'x', 'kind': 'qlog.zst', 'ordinal': 1},
                                                        {'source_sha256': 'y', 'kind': 'qlog.zst', 'ordinal': 2}]}]
    self.history = {'a': [{'source_sha256': 'r', 'kind': 'rlog.zst', 'ordinal': 0}],
                    'b': [{'source_sha256': 's', 'kind': 'rlog.zst', 'ordinal': 0},
                          {'source_sha256': 'x', 'kind': 'qlog.zst', 'ordinal': 1},
                          {'source_sha256': 'y', 'kind': 'qlog.zst', 'ordinal': 2}]}

  def test_exact_exclusions_only(self):
    self.assertEqual([(r['route_id'], s['source_sha256']) for r, s in policy.resolve_exclusions(self.routes, self.history)],
                     [('b', 'x'), ('b', 'y')])

  def test_extra_qlog_rejected(self):
    self.history['b'].append({'source_sha256': 'z', 'kind': 'qlog.zst', 'ordinal': 3})
    with self.assertRaises(ValueError):
      policy.resolve_exclusions(self.routes, self.history)

  def test_wrong_ordinal_rejected(self):
    self.history['b'][1]['ordinal'] = 9
    with self.assertRaises(ValueError):
      policy.resolve_exclusions(self.routes, self.history)

  def test_duplicate_exclusion_rejected(self):
    self.routes[1]['excluded_sources'][1] = copy.deepcopy(self.routes[1]['excluded_sources'][0])
    with self.assertRaises(ValueError):
      policy.resolve_exclusions(self.routes, self.history)

  def test_missing_exclusion_rejected(self):
    self.routes[1]['excluded_sources'].pop()
    with self.assertRaises(ValueError):
      policy.resolve_exclusions(self.routes, self.history)


class TestSourcePolicy(unittest.TestCase):
  def test_parse_literal_policy_without_execution(self):
    text = '_services = {"carState": (True, 100., 10), "gyroscope": (True, 104., 104), "modelV2": (True, 20.)}'
    x = audit.service_policy(text)
    self.assertEqual(x['carState'], {'should_log': True, 'frequency': 100., 'decimation': 10})
    self.assertEqual(x['gyroscope']['decimation'], 104)
    self.assertIsNone(x['modelV2']['decimation'])

  def test_annotated_literal_policy(self):
    self.assertEqual(audit.service_policy('_services: dict = {"carState": (True, 100., 10)}')['carState']['decimation'], 10)

  def test_constant_frequency_arithmetic(self):
    self.assertEqual(audit.service_policy('_services = {"x": (True, 1/60., 1)}')['x']['frequency'], 1/60.)

  def test_integral_float_decimation(self):
    self.assertEqual(audit.service_policy('_services = {"x": (True, 2., 4.)}')['x']['decimation'], 4)

  def test_fractional_decimation_rejected(self):
    with self.assertRaises(ValueError):
      audit.service_policy('_services = {"x": (True, 2., 1.5)}')

  def test_dynamic_policy_rejected(self):
    with self.assertRaises(ValueError):
      audit.service_policy('_services = get_policy()')

  def test_invalid_decimation_rejected(self):
    with self.assertRaises(ValueError):
      audit.service_policy('_services = {"carState": (True, 100., 0)}')

  def test_unknown_source_rejected(self):
    with self.assertRaises(ValueError):
      audit.require_source('unknown', {})


class TestDecoderGate(unittest.TestCase):
  def setUp(self):
    self.auth = {'segments': [{'route_id': 'b', 'source_sha256': 'x', 'kind': 'qlog.zst'},
                             {'route_id': 'b', 'source_sha256': 'y', 'kind': 'qlog.zst'}]}

  def test_exact_segment_admitted(self):
    policy.require_segment(self.auth, 'b', 'x', 'qlog.zst')

  def test_other_qlog_rejected(self):
    with self.assertRaises(ValueError):
      policy.require_segment(self.auth, 'b', 'z', 'qlog.zst')

  def test_other_route_rejected(self):
    with self.assertRaises(ValueError):
      policy.require_segment(self.auth, 'a', 'x', 'qlog.zst')

  def test_rlog_reopening_rejected(self):
    with self.assertRaises(ValueError):
      policy.require_segment(self.auth, 'b', 'x', 'rlog.zst')

  def test_duplicate_authorization_rejected(self):
    self.auth['segments'][1] = self.auth['segments'][0]
    with self.assertRaises(ValueError):
      policy.require_segment(self.auth, 'b', 'x', 'qlog.zst')


class TestAdditiveAccounting(unittest.TestCase):
  def test_overlay_preserves_old_origin(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation as execution
    records = [{'ordinal': 0, 'segment_sha256': 'a', 'route_global_start': 0,
                'coverage': {'total_grid_samples': 4}, 'receipt_sha256': 'p'},
               {'ordinal': 1, 'segment_sha256': 'b', 'route_global_start': 0,
                'coverage': {'total_grid_samples': 2}, 'receipt_sha256': 'q'},
               {'ordinal': 2, 'segment_sha256': 'c', 'route_global_start': 4,
                'coverage': {'total_grid_samples': 3}, 'receipt_sha256': 'r'}]
    result = execution.origin_overlay(records, {'b'})
    self.assertEqual([x['original_route_global_start'] for x in result], [0, 0, 4])
    self.assertEqual([x['reconciled_route_global_start'] for x in result], [0, 4, 6])
    self.assertEqual([x['store_key'] for x in result], ['historical_rlog', 'new_qlog', 'historical_rlog'])

  def test_missing_ordinal_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation as execution
    with self.assertRaises(ValueError):
      execution.origin_overlay([{'ordinal': 1}], set())


class TestDownsampledCausalRows(unittest.TestCase):
  def build(self):
    from openpilot.tools.cyber_autotune.tests.test_empirical_causal_dataset import streams
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as a
    s = streams(80)
    for name in ('state', 'command', 'control'):
      s[name] = s[name][::10]
    return a.build(s, 'a'*64, 20, 0)

  def test_original_integer_grid_preserved(self):
    a, c = self.build()
    self.assertEqual(c['total_grid_samples'], 71)
    self.assertEqual(set(a['grid_time_ns'][1:]-a['grid_time_ns'][:-1]), {10000000})

  def test_downsampled_age_not_relaxed(self):
    import numpy as np
    a, _ = self.build()
    self.assertFalse(a['state.rate.available'][3])
    self.assertTrue(np.isnan(a['state.rate'][3]))

  def test_no_contiguous_support_fabricated(self):
    _, c = self.build()
    self.assertEqual(c['bins']['LOW']['common_design_rows'], 0)

  def test_actual_rate_values_preserved(self):
    a, _ = self.build()
    self.assertEqual(a['state.rate'][0], 4.)
    self.assertEqual(a['state.rate'][10], 4.)

  def test_no_model_calls(self):
    from unittest.mock import patch
    with patch('numpy.linalg.lstsq', side_effect=AssertionError('fit')):
      self.build()

  def test_exact_downsampled_repeatability(self):
    a, ca = self.build()
    b, cb = self.build()
    self.assertEqual(ca, cb)
    for key in a:
      self.assertEqual(a[key].tobytes(), b[key].tobytes())

  def test_legacy_and_causal_runs_separate(self):
    a, _ = self.build()
    self.assertIn('legacy_run_id', a)
    self.assertIn('causal_run_id', a)

  def test_forbidden_union_bodies_not_read(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_reader as reader
    class Event:
      def __init__(self, kind):
        self.kind = kind
      def which(self):
        return self.kind
      def __getattr__(self, name):
        raise AssertionError('forbidden union body')
    result = reader.numeric([Event(k) for k in (
      'modelV2', 'lateralPlan', 'longitudinalPlan', 'gpsLocationExternal', 'cameraOdometry',
      'liveLocationKalman', 'liveCalibration', 'roadEncodeData', 'thumbnail')])
    self.assertEqual(result['state'], [])


class TestImmutableQlogArrays(unittest.TestCase):
  def setUp(self):
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation as execution
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
    import numpy as np
    self.directory = TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.path = Path(self.directory.name)/'x.npy'
    self.binding = storage.array_write(self.path, np.arange(4, dtype='<f8'))
    self.execution = execution

  def test_array_full_identity(self):
    self.assertEqual(self.execution.validate_array(self.path, self.binding).tolist(), [0., 1., 2., 3.])

  def test_wrong_dtype_rejected(self):
    self.binding['dtype'] = '<i8'
    with self.assertRaises(ValueError):
      self.execution.validate_array(self.path, self.binding)

  def test_wrong_shape_rejected(self):
    self.binding['shape'] = [2, 2]
    with self.assertRaises(ValueError):
      self.execution.validate_array(self.path, self.binding)

  def test_wrong_payload_hash_rejected(self):
    self.binding['array_sha256'] = '0'*64
    with self.assertRaises(ValueError):
      self.execution.validate_array(self.path, self.binding)

  def test_wrong_file_hash_rejected(self):
    self.binding['file_sha256'] = '0'*64
    with self.assertRaises(ValueError):
      self.execution.validate_array(self.path, self.binding)

  def test_immutable_write_conflict(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
    with self.assertRaises(ValueError):
      storage.atomic_bytes(self.path, b'conflict')

  def test_symlink_array_rejected(self):
    alias = self.path.with_name('alias.npy')
    alias.symlink_to(self.path)
    with self.assertRaises(ValueError):
      self.execution.validate_array(alias, self.binding)

  def test_overlap_old_store_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
    with self.assertRaises(ValueError):
      storage.external('/tmp/prior-causal/new', ['/tmp/prior-causal'])

  def test_relative_path_rejected(self):
    with self.assertRaises(ValueError):
      self.execution.validate_array('x.npy', self.binding)


class TestQlogPublicationFirewall(unittest.TestCase):
  def check(self, value):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as publication
    return publication.validate_public(p.seal(value))

  def test_aggregate_allowed(self):
    self.check({'schema': 'TEST', 'count': 11989, 'source_sha256': 'a'*64})

  def test_row_origins_rejected(self):
    with self.assertRaises(ValueError):
      self.check({'segment_origins': []})

  def test_raw_values_rejected(self):
    with self.assertRaises(ValueError):
      self.check({'rows': [{'raw_command': 1}]})

  def test_private_location_rejected(self):
    with self.assertRaises(ValueError):
      self.check({'location': {'root': 'x'}})

  def test_private_path_rejected(self):
    with self.assertRaises(ValueError):
      self.check({'value': '/private/store'})

  def test_timestamp_rejected(self):
    with self.assertRaises(ValueError):
      self.check({'grid_time_ns': 1})

  def test_source_file_path_allowed(self):
    self.check({'files': {'logger': {'path': 'openpilot/system/loggerd/logger.cc'}}})

  def test_historical_public_chain_immutable(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as historical
    self.assertEqual(historical.load()['empirical-causal-train-dev-readiness-v1.json']['status'],
                     'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED')

  def test_policy_keeps_no_authority(self):
    p = policy.policy()
    self.assertFalse(p['production_authority'])
    self.assertFalse(p['ta_execution'])
    self.assertFalse(p['sg_execution'])
    self.assertFalse(p['composition_authorized'])
    self.assertEqual(p['model_fitting'], 'NOT_RUN')
    self.assertEqual(p['holdout'], 'HOLDOUT_OPENING_CLOSED')

  def test_scope_and_whitelist_pinned(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
    p = policy.policy()
    self.assertEqual(p['signal_whitelist'], base.WHITELIST)
    self.assertEqual(p['max_age_ns'], 20000000)
    self.assertEqual(p['dt_ns'], 10000000)

  def test_invalid_artifact_set_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as publication
    with self.assertRaises(ValueError):
      publication.validate_chain({})


def public_fixture():
  from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub, empirical_plant_policy as p
  from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
  rows = {n: {'schema': 'TEST'} for n in pub.FILES}
  from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as historical
  ids = [s['source_sha256'] for r in historical.load()['empirical-causal-train-dev-route-set-v1.json']['routes']
         for s in r['excluded_sources']]
  rows[pub.FILES[0]] = policy.policy()
  rows[pub.FILES[1]].update(count=2, identities=[
    {'route_id': base.resolve_routes()[1]['route_id'], 'source_sha256': ids[0]},
    {'route_id': base.resolve_routes()[1]['route_id'], 'source_sha256': ids[1]}])
  rows[pub.FILES[2]].update(status='QLOG_SOURCE_SEMANTICS_COMPLETE')
  rows[pub.FILES[3]].update(source_audit_sha256=p.seal(rows[pub.FILES[2]])['receipt_sha256'])
  rows[pub.FILES[4]].update(count=2, source_audit_sha256=p.seal(rows[pub.FILES[2]])['receipt_sha256'],
    policy_sha256=rows[pub.FILES[0]]['receipt_sha256'], segment_set_sha256=p.sha(p.canonical(sorted(ids))))
  rows[pub.FILES[5]].update(segments=[{'segment_sha256': ids[0]}, {'segment_sha256': ids[1]}])
  rows[pub.FILES[6]].update(status='LEGACY_ALIGNMENT_REPRODUCED')
  rows[pub.FILES[7]].update(manifest_sha256='m', rlog_reference_count=154, new_qlog_count=2, routes=[
    {'route_id': r['route_id'], 'rlog_count': count, 'qlog_count': qcount,
     'segment_count': count+qcount, 'legacy_checks': {'exact': True},
     'bridge': {'status': 'ROUTE_COMMAND_BRIDGE_CONFIRMED'}}
    for r, count, qcount in zip(base.resolve_routes(), (70, 84), (0, 2), strict=True)])
  rows[pub.FILES[8]].update(manifest_sha256='m', exact=True, repeats=2, new_qlog_count=2,
    historical_trees_before={'a': 'b'}, historical_trees_after={'a': 'b'}, exact_qlog_hashes_before_after=True)
  rows[pub.FILES[9]].update(manifest_sha256='m', status='RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY',
    route_count=2, rlog_reference_count=154, qlog_count=2, holdout='HOLDOUT_OPENING_CLOSED',
    opening_count=0, reservation='NONE', model_fitting='MODEL_FITTING_NOT_RUN', model_selection='NOT_RUN',
    stage_b='STAGE_B_SIGNAL_ADMISSION_BLOCKED', calibration_blockers=p.BLOCKERS,
    qualification_allowed=False, production_authority=False)
  return reseal_public(rows)


def reseal_public(rows):
  from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub, empirical_plant_policy as p
  result = {n: p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}) for n, row in rows.items()}
  ready = {k: v for k, v in result[pub.FILES[-1]].items() if k != 'receipt_sha256'}
  ready['artifacts'] = {n: r['receipt_sha256'] for n, r in result.items() if n != pub.FILES[-1]}
  result[pub.FILES[-1]] = p.seal(ready)
  return result


class TestPublicationCrossLinks(unittest.TestCase):
  def check_change(self, index, key, value):
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub
    rows = public_fixture()
    rows[pub.FILES[index]][key] = value
    with self.assertRaises(ValueError):
      pub.validate_chain(reseal_public(rows))

  def test_valid_chain(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub
    pub.validate_chain(public_fixture())

  def test_repeat_manifest_drift(self):
    self.check_change(8, 'manifest_sha256', 'other')

  def test_merge_manifest_drift(self):
    self.check_change(7, 'manifest_sha256', 'other')

  def test_source_audit_link_drift(self):
    self.check_change(4, 'source_audit_sha256', 'other')

  def test_equivalence_source_link_drift(self):
    self.check_change(3, 'source_audit_sha256', 'other')

  def test_exact_two_qlogs_required(self):
    self.check_change(4, 'count', 3)

  def test_exact_154_rlogs_required(self):
    self.check_change(7, 'rlog_reference_count', 155)

  def test_two_executions_required(self):
    self.check_change(8, 'repeats', 1)

  def test_historical_mutation_rejected(self):
    self.check_change(8, 'historical_trees_after', {'a': 'c'})

  def test_raw_source_preservation_required(self):
    self.check_change(8, 'exact_qlog_hashes_before_after', False)

  def test_route_set_drift_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub
    rows = public_fixture()
    rows[pub.FILES[7]]['routes'][0]['route_id'] = 'third'
    with self.assertRaises(ValueError):
      pub.validate_chain(reseal_public(rows))

  def test_authorization_segment_set_drift(self):
    self.check_change(4, 'segment_set_sha256', 'other')

  def test_consistent_wrong_identity_set_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_publication as pub, empirical_plant_policy as p
    rows = public_fixture()
    rows[pub.FILES[1]]['identities'][0]['source_sha256'] = 'other'
    rows[pub.FILES[5]]['segments'][0]['segment_sha256'] = 'other'
    ids = sorted(x['source_sha256'] for x in rows[pub.FILES[1]]['identities'])
    rows[pub.FILES[4]]['segment_set_sha256'] = p.sha(p.canonical(ids))
    with self.assertRaises(ValueError):
      pub.validate_chain(reseal_public(rows))


class TestFinalCausalCompleteness(unittest.TestCase):
  def test_full_history_does_not_promote_sparse_qlogs(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_assessment as assessment
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
    segments = [{'coverage': {'required_field_coverage': dict.fromkeys(alignment.REQUIRED, 1),
                              'causal_required_valid': 0, 'causal_runs': 0}} for _ in range(2)]
    segments[0]['coverage']['required_field_coverage']['control.requested'] = 0
    result = assessment.causal_completeness(segments)
    self.assertEqual(result['status'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
    self.assertEqual(result['added_causal_valid_rows'], 0)

  def test_missing_required_field_remains_missing(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_assessment as assessment
    result = assessment.causal_completeness([{'coverage': {'required_field_coverage': {}, 'causal_required_valid': 0, 'causal_runs': 0}}]*2)
    self.assertIn('state.rate', result['missing_required_fields'])

  def test_other_segment_count_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_assessment as assessment
    with self.assertRaises(ValueError):
      assessment.causal_completeness([])

  def test_field_presence_without_joint_support_not_ready(self):
    from openpilot.tools.cyber_autotune import empirical_qlog_assessment as assessment
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
    segments = [{'coverage': {'required_field_coverage': dict.fromkeys(alignment.REQUIRED, 10),
                              'causal_required_valid': 0, 'causal_runs': 0}}]*2
    self.assertEqual(assessment.causal_completeness(segments)['status'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')


if __name__ == '__main__':
  unittest.main()
