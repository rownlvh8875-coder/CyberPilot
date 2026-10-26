"""Real immutable-model inference/rollout on synthetic private-shaped stores."""

from contextlib import ExitStack
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune.tests.hurdle_v3_fixtures import fixture
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m


class TestV3Execution(unittest.TestCase):
  def setUp(self):
    try:
      self.e = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_execution')
    except ImportError:
      self.fail('V3 private orchestrator not implemented')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.stack = ExitStack()
    self.addCleanup(self.stack.close)
    self.stack.enter_context(patch.object(io, 'prove_d'))
    self.stack.enter_context(patch.object(io, 'free_bytes', return_value=10**15))
    self.permit = fixture(self.root)
    self.original = self.permit.jobs[0]
    self.stack.enter_context(patch.object(self.e, 'comparison_history', return_value={**self.original, 'train_metrics': None}))

  def run_job(self, replica='repeat-1'):
    with io.firewall():
      return self.e.execute_job(self.permit, self.original, replica)

  def test_full_job_all_horizons_and_byte_exact_repeat(self):
    first, second = self.run_job(), self.run_job('repeat-2')
    self.assertEqual(first, second)
    self.assertEqual(first['status'], 'EXECUTED_COMPLETE')
    self.assertTrue(first['gate']['pass'])
    self.assertEqual(len(first['gate']['clauses']), 32)
    self.assertEqual(set(first['rollout']), {'25', '50', '100', '200'})
    self.assertEqual(first['threshold']['saved_probability_comparison'], 'BYTE_EXACT_PASS')
    self.assertEqual(first['threshold']['objective']['tp'], self.original['train_move_count'])
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_executor_publication as publication
    self.assertEqual(publication.public_job(first)['threshold']['objective']['tp'], self.original['train_move_count'])
    for path in (self.permit.roots['output'] / 'repeat-1').rglob('*'):
      if path.is_file():
        other = self.permit.roots['output'] / 'repeat-2' / path.relative_to(self.permit.roots['output'] / 'repeat-1')
        self.assertEqual(path.read_bytes(), other.read_bytes())

  def test_stage2_first_prediction_is_all_train_rows(self):
    original, counts = m.predict_delta, []

    def observe(x, model):
      counts.append(len(x))
      return original(x, model)

    with patch.object(m, 'predict_delta', side_effect=observe):
      self.run_job()
    self.assertEqual(counts[0], self.original['train_count'])
    self.assertGreater(counts[0], self.original['train_move_count'])

  def test_dev_load_requires_durable_threshold(self):
    with self.assertRaisesRegex(ValueError, 'V3_THRESHOLD_FINALIZATION_REQUIRED'):
      io.load_route(self.permit, self.original, development=True)
    original = io.load_route

    def observe(permit, job, **kwargs):
      if kwargs.get('development'):
        path = permit.roots['output'] / 'repeat-1/candidates' / job['candidate_id'] / job['fold'] / 'threshold/receipt.json'
        self.assertTrue(path.is_file())
      return original(permit, job, **kwargs)

    with patch.object(io, 'load_route', side_effect=observe):
      self.run_job()

  def test_direct_source_reader_cannot_open_dev_or_v1_threshold_early(self):
    for population, key in (('one-step', 'p_move'), ('rollout-25', 'projected_path'), ('threshold', 'threshold')):
      receipt = io.population(self.permit, self.original, population)
      with self.subTest(population=population, key=key), self.assertRaisesRegex(ValueError, 'V3_THRESHOLD_FINALIZATION_REQUIRED'):
        io.source_array(self.permit, self.original, population, receipt, key)

  def test_durable_but_incomplete_marker_does_not_authorize_dev(self):
    marker = io.p.seal({'schema': 'MARKER', 'status': 'V3_THRESHOLD_FINALIZED', 'candidate_id': self.original['candidate_id'],
                       'fold': self.original['fold'], 'authorization_sha256': self.permit.trusted_sha256,
                       'train_anchor_sha256': self.original['train_anchor_sha256']})
    path = self.permit.roots['output'] / 'repeat-1/candidates' / self.original['candidate_id'] / self.original['fold'] / 'threshold/receipt.json'
    store.write_json(path, marker)
    with self.assertRaisesRegex(ValueError, 'V3_THRESHOLD_FINALIZATION_REQUIRED'):
      io.load_route(self.permit, self.original, development=True, threshold_receipt=marker, replica='repeat-1')

  def test_saved_probability_byte_drift_hard_fails(self):
    original = m.probability

    def corrupt(x, model):
      value = original(x, model)
      value[0] = np.nextafter(value[0], 1.0)
      return value

    with patch.object(m, 'probability', side_effect=corrupt):
      with self.assertRaisesRegex(ValueError, 'V3_STAGE1_PREDICTION_IDENTITY_FAILURE'):
        self.run_job()

  def test_unregistered_permit_and_model_or_anchor_drift_rejected(self):
    forged = io.Permit(self.permit.roots, self.permit.authorization, self.permit.trusted_sha256, self.permit.pack,
                       self.permit.jobs, self.permit.records, self.permit.pins, self.permit.record_sha256)
    with self.assertRaisesRegex(ValueError, 'V3_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
      self.e.execute_job(forged, self.original, 'repeat-1')
    for field in ('train_anchor_sha256', 'stage1'):
      bad = deepcopy(self.original)
      if field == 'stage1':
        bad[field]['coefficient_sha256'] = '0' * 64
      else:
        bad[field] = '0' * 64
      with self.assertRaises(ValueError):
        self.e.execute_job(self.permit, bad, 'repeat-1')
    base = self.permit.roots['source'] / 'repeat-1/candidates' / self.original['candidate_id'] / self.original['fold'] / 'stage1/model'
    receipt = io.read_json(base / 'receipt.json')
    (base / receipt['arrays']['coefficients']['filename']).write_bytes(b'corrupt synthetic coefficient payload')
    with self.subTest(kind='compressed_model'), self.assertRaisesRegex(ValueError, 'V3_MODEL_IDENTITY_CONFLICT'):
      io.load_model(self.permit, self.original, 'stage1')
    base = self.permit.records[0][0] / 'arrays'
    (base / io.legacy.old.read.array_name('command.normalized')).write_bytes(b'corrupt synthetic feature payload')
    with self.subTest(kind='source_anchor'), self.assertRaisesRegex(ValueError, 'V3_ANCHOR_IDENTITY_CONFLICT'):
      io.load_route(self.permit, self.original)

  def test_no_feasible_has_receipt_and_never_opens_dev(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_threshold as threshold
    value = {'status': 'V3_NO_FEASIBLE_THRESHOLD', 'threshold': None, 'candidate_count': 4,
             'feasible_count': 0, 'objective': None, 'canonical_checks': 4}
    original, events = io.load_route, []

    def observe(permit, job, **kwargs):
      events.append(kwargs.get('development', False))
      return original(permit, job, **kwargs)

    with patch.object(threshold, 'sweep', return_value=value), patch.object(io, 'load_route', side_effect=observe):
      result = self.run_job()
    self.assertEqual(events, [False])
    self.assertEqual(result['status'], 'NO_FEASIBLE_THRESHOLD')
    self.assertFalse(result['gate']['pass'])
    self.assertEqual(len(result['gate']['clauses']), 32)

  def test_performance_gate_failure_does_not_skip_rollout(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
    original = data.one_step

    def fail_metric(*args):
      metrics, arrays = original(*args)
      metrics['one_step']['candidate']['exact_hit'] = 0.0
      return metrics, arrays

    with patch.object(data, 'one_step', side_effect=fail_metric):
      result = self.run_job()
    self.assertFalse(result['gate']['pass'])
    self.assertEqual(set(result['rollout']), {'25', '50', '100', '200'})


class TestV3CompleteRuns(unittest.TestCase):
  def test_32_jobs_two_independent_runs_and_trapped_resume(self):
    try:
      e = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_execution')
    except ImportError:
      self.fail('V3 private orchestrator not implemented')
    with tempfile.TemporaryDirectory() as name, patch.object(io, 'prove_d'), patch.object(io, 'free_bytes', return_value=10**15):
      permit = fixture(Path(name), all_jobs=True)
      history = {(j['candidate_id'], j['fold']): {**j, 'train_metrics': None} for j in permit.jobs}
      with patch.object(io, 'preflight', return_value=permit), patch.object(e, 'comparison_history', side_effect=lambda c, f: history[c, f]):
        first = e.run(authorization=permit.authorization, authorization_sha256=permit.trusted_sha256, replica='repeat-1')
        second = e.run(authorization=permit.authorization, authorization_sha256=permit.trusted_sha256, replica='repeat-2')
      self.assertEqual(first, second)
      self.assertEqual(first['job_count'], 32)
      self.assertEqual(e.trapped_resume(permit.roots['output'] / 'repeat-1', permit.trusted_sha256, first['receipt_sha256']), first)
      repeat = e.repeatability(permit.roots['output'], permit.trusted_sha256, first['receipt_sha256'], second['receipt_sha256'])
      self.assertEqual(repeat['status'], 'V3_EXACT_REPEATABILITY_PASS')
      eligible = e.cleanup_eligibility(permit.roots['output'], permit.trusted_sha256, first['receipt_sha256'], second['receipt_sha256'],
                                       {key: permit.roots[key] for key in ('source', 'causal', 'derived')})
      self.assertTrue(eligible['eligible'])
      self.assertTrue((permit.roots['output'] / 'repeat-2').exists())
      selected = io.read_json(permit.roots['output'] / 'repeat-1/selection.json')
      self.assertEqual(selected['selected_candidate'], 'HRI_D00_L01')
      jobpath = permit.roots['output'] / 'repeat-2/candidates/HRI_D00_L01/FOLD_A/receipt.json'
      jobpath.write_bytes(b'x')
      with self.assertRaisesRegex(ValueError, 'V3_REPEATABILITY_FAILURE'):
        e.repeatability(permit.roots['output'], permit.trusted_sha256, first['receipt_sha256'], second['receipt_sha256'])


class TestV3ResumeBoundary(unittest.TestCase):
  def test_wrong_expected_manifest_sha_rejects_before_member_hashing(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_execution as e
    with tempfile.TemporaryDirectory() as name:
      root = Path(name) / 'repeat-1'
      root.mkdir()
      manifest = io.p.seal({'schema': 'V3_RUN_MANIFEST', 'status': e.SUCCESS, 'job_count': 32,
                            'authorization_sha256': 'a' * 64, 'files': {'payload.npy.gz': 'b' * 64}})
      io.p.persist(root / 'manifest.json', manifest)
      with patch.object(store, 'verify_manifest', side_effect=AssertionError('payload hashing reached')):
        with self.assertRaisesRegex(ValueError, 'V3_RESUME_INTEGRITY_FAILURE'):
          e.resume(root, 'a' * 64, '0' * 64)


class TestV3FrozenBindings(unittest.TestCase):
  def test_gate_mutation_and_pooled_rescue_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
    clauses = io.contracts()['clauses']
    for mutation in ('epsilon', 'omission', 'operator'):
      changed = deepcopy(clauses)
      if mutation == 'epsilon':
        changed[0]['epsilon'] = 1e-9
      elif mutation == 'omission':
        changed.pop()
      else:
        changed[0]['operator'] = '<='
      with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'EXACT_32_GATE'):
        gates.fold_gate({'status': 'EXECUTED_COMPLETE'}, changed)
    with self.assertRaises(ValueError):
      gates.select([{'candidate_id': io.JOBS[0][0], 'fold': 'FOLD_A'}], clauses)

  def test_recursive_api_has_no_future_truth_input(self):
    horizon, n = 25, 3
    initial = np.zeros((n, 2), np.int64)
    commands = np.zeros((n, horizon), np.float64)
    speed = np.ones((n, horizon), np.float64)
    norm = {'mean': np.zeros(5), 'std': np.ones(5), 'constant': np.zeros(5, bool), 'constant_reference': np.zeros(5), 'effective': np.arange(5)}
    first = {'normalizer': norm, 'coefficients': np.array([-1., 0., 0., 0., 0.])}
    second = {'normalizer': norm, 'coefficients': np.zeros(5)}
    with self.assertRaises(TypeError):
      m.recursive(initial, commands, speed, 'HRI_D00_L01', first, .2, second, horizon, future_tick=np.ones((n, horizon)))
    # The same projected path can be scored against different future truths;
    # truth is absent from inference, including delta history updates.
    path, gate = m.recursive(initial, commands, speed, 'HRI_D00_L01', first, .2, second, horizon)
    again, again_gate = m.recursive(initial, commands, speed, 'HRI_D00_L01', first, .2, second, horizon)
    np.testing.assert_array_equal(path, again)
    np.testing.assert_array_equal(gate, again_gate)
