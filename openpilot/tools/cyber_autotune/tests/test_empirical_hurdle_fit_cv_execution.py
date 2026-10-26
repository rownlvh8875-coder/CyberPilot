"""Synthetic executor, exact gate, immutable store and privacy adversaries."""

from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_execution as execution
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_publication as publication
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read


def pair():
  return {
    'count': 500,
    'anchor_sha256': 'a' * 64,
    'comparator_anchor_sha256': 'a' * 64,
    'candidate': {'rmse': 0.9, 'mae': 1.0, 'p95': 1.0, 'exact_hit': 0.5, 'within_one_tick': 0.9},
    'comparator': {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0, 'exact_hit': 0.5, 'within_one_tick': 0.9},
  }


def job(candidate='HRI_D00_L01', fold='FOLD_A'):
  return {
    'candidate_id': candidate,
    'fold': fold,
    'status': 'EXECUTED_COMPLETE',
    'one_step': pair(),
    'true_move': pair(),
    'rollout': {str(h): {'overall': pair(), 'path_moved': pair()} for h in m.HORIZONS},
  }


class TestHurdleGates(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.clauses = store.contracts()['acceptance-gate']['clauses']

  def test_exact_clause_count_and_all_pass(self):
    self.assertEqual(len(self.clauses), 32)
    self.assertTrue(gates.fold_gate(job(), self.clauses)['pass'])

  def test_each_clause_individually_blocks(self):
    for clause in self.clauses:
      with self.subTest(clause=clause['id']):
        j = job()
        if clause['population'] == 'ALL_ONE_STEP':
          value = j['one_step']
        elif clause['population'] == 'TRUE_MOVE_ONE_STEP_INTEGRATED':
          value = j['true_move']
        else:
          value = j['rollout'][str(clause['horizon_steps'])]['overall' if clause['population'] == 'OVERALL_ROLLOUT' else 'path_moved']
        metric = clause['metric'].lower()
        baseline = value['comparator'][metric]
        value['candidate'][metric] = np.nextafter(baseline, -np.inf if clause['operator'] == '>=' else np.inf)
        self.assertFalse(gates.fold_gate(j, self.clauses)['pass'])

  def test_one_step_rmse_equality_fails(self):
    j = job()
    j['one_step']['candidate']['rmse'] = 1.0
    self.assertFalse(gates.fold_gate(j, self.clauses)['pass'])

  def test_comparator_mismatch(self):
    j = job()
    j['true_move']['comparator_anchor_sha256'] = 'b' * 64
    with self.assertRaisesRegex(ValueError, 'COMPARATOR'):
      gates.fold_gate(j, self.clauses)

  def test_missing_horizon_and_undefined_precision(self):
    for mutation in ('horizon', 'precision'):
      j = job()
      if mutation == 'horizon':
        del j['rollout']['200']
      else:
        j['status'] = 'EXECUTION_FAILURE'
      self.assertFalse(gates.fold_gate(j, self.clauses)['pass'])

  def test_invalid_metric(self):
    for value in (-1.0, np.inf, np.nan):
      j = job()
      j['one_step']['candidate']['rmse'] = value
      with self.subTest(value=value), self.assertRaises(ValueError):
        gates.fold_gate(j, self.clauses)

  def jobs(self):
    result = [job(c, f) for c in m.CANDIDATES for f in ('FOLD_A', 'FOLD_B')]
    for j in result:
      j['gate'] = gates.fold_gate(j, self.clauses)
    return result

  def test_selection_zero_one_multiple(self):
    jobs = self.jobs()
    self.assertEqual(gates.select(jobs, self.clauses)['selected_candidate'], m.CANDIDATES[0])
    for j in jobs[2:]:
      j['status'] = 'EXECUTION_FAILURE'
      j['gate'] = gates.fold_gate(j, self.clauses)
    self.assertEqual(gates.select(jobs, self.clauses)['admissible_count'], 1)
    jobs[0]['status'] = 'EXECUTION_FAILURE'
    jobs[0]['gate'] = gates.fold_gate(jobs[0], self.clauses)
    self.assertIsNone(gates.select(jobs, self.clauses)['selected_candidate'])

  def test_missing_job(self):
    with self.assertRaisesRegex(ValueError, '32_ORDERED'):
      gates.select(self.jobs()[:-1], self.clauses)

  def test_primary_path_moved_key(self):
    jobs = self.jobs()
    for j in jobs[2:4]:
      for row in j['rollout'].values():
        row['path_moved']['candidate']['rmse'] = 0.8
      j['gate'] = gates.fold_gate(j, self.clauses)
    self.assertEqual(gates.select(jobs, self.clauses)['selected_candidate'], m.CANDIDATES[1])

  def test_key_order_secondary_tertiary_and_structure(self):
    jobs = [job(), job(fold='FOLD_B')]
    key = gates.selection_key('HRI_D20_L45', jobs)
    self.assertEqual(key[3:], (186, 45, 20, 'HRI_D20_L45'))
    for j in jobs:
      j['rollout']['25']['overall']['candidate']['rmse'] = 0.95
      j['one_step']['candidate']['p95'] = 0.8
    key = gates.selection_key('HRI_D20_L45', jobs)
    self.assertEqual(key[:3], (0.9, 0.95, 0.8))

  def test_ratio_edges(self):
    self.assertEqual(gates.ratio(0.0, 0.0), 1.0)
    self.assertEqual(gates.ratio(1.0, 0.0), np.inf)
    for args in ((-1.0, 1.0), (np.nan, 1.0), (1e308, 1e-308)):
      with self.subTest(args=args), self.assertRaises(ValueError):
        gates.ratio(*args)


class TestHurdleExecution(unittest.TestCase):
  def test_exact_policy_pins(self):
    self.assertEqual(len(store.contracts()), 13)
    with patch.dict(store.PINS, {'threshold-policy': '0' * 64}):
      with self.assertRaisesRegex(ValueError, 'BINDING_CONFLICT'):
        store.contracts()

  def test_environment_rejects_wrong_version(self):
    with patch.object(np, '__version__', '0'):
      with self.assertRaisesRegex(ValueError, 'ENVIRONMENT'):
        store.environment()

  def test_qlog_rejected_before_arrays(self):
    auth = p.seal({'retrospective_fit_cv_authorized': True, 'array_access_before_seal': False, 'routes': ['r'], 'qlog_deny_content_sha256': ['q']})
    with patch.object(read, 'read_array', side_effect=AssertionError('array open')):
      with self.assertRaisesRegex(ValueError, 'QLOG'):
        data.load_route([(None, {'segment_sha256': 'q'}, None, None)], 'r', auth)

  def test_seal_required_before_arrays(self):
    auth = p.seal({'retrospective_fit_cv_authorized': False})
    with patch.object(read, 'read_array', side_effect=AssertionError('array open')):
      with self.assertRaisesRegex(ValueError, 'SEALED'):
        data.load_route([], 'r', auth)

  def test_storage_no_overwrite_and_tamper(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      receipt = p.seal({'schema': 'SYNTHETIC'})
      store.write_json(root / 'receipt.json', receipt)
      store.finish(root, ['receipt.json'], {'schema': 'SYNTHETIC_MANIFEST'})
      store.verify_manifest(root)
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE'):
        store.write_json(root / 'receipt.json', p.seal({'schema': 'OTHER'}))
      (root / 'extra').write_bytes(b'forbidden')
      with self.assertRaisesRegex(ValueError, 'COMPLETE_FILE'):
        store.verify_manifest(root)

  def test_symlink_traversal_overlap(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'alias').symlink_to(root, target_is_directory=True)
      for value in (root / 'alias/file', root / 'a/../b', Path('relative')):
        with self.subTest(value=value), self.assertRaises(ValueError):
          storage.safe(value)
      with self.assertRaisesRegex(ValueError, 'OVERLAP'):
        storage.external(root / 'nested', [root])

  def test_public_private_values_rejected(self):
    for key in ('value', 'coefficients', 'mean', 'p_move', 'projected_path', 'command_current'):
      with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'PRIVATE'):
        publication.validate_public({'nested': [{key: [1, 2]}]})

  def test_public_paths_rejected(self):
    with self.assertRaisesRegex(ValueError, 'PRIVATE_PATH'):
      publication.validate_public({'location': '/'.join(('', 'home', 'private', 'store'))})

  def test_raw_optimizer_firewall(self):
    with execution.firewall():
      with self.assertRaisesRegex(ValueError, 'FORBIDDEN'):
        np.linalg.pinv(np.eye(2))
      for name in ('scipy.optimize', 'openpilot.tools.lib.logreader'):
        with self.subTest(name=name), self.assertRaises(ModuleNotFoundError):
          __import__(name)

  def test_full_path_recursion_without_future_truth(self):
    initial = np.array([[0, 1], [3, 3]], dtype=np.int64)
    command = np.zeros((2, 25))
    speed = np.full((2, 25), 20.0)
    seen = []

    def step(x, current, *args):
      seen.append(x.copy())
      new = current + 1
      return np.ones(2), new, np.ones(2), np.ones(2, dtype=bool)

    with patch.object(m, 'integrated', side_effect=step):
      path, gate = m.recursive(initial, command, speed, 'HRI_D00_L01', {}, 0.0, {}, 25)
    np.testing.assert_array_equal(path[:, -1], [26, 28])
    self.assertEqual(path.shape, (2, 26))
    self.assertTrue(gate.all())
    self.assertEqual(seen[1][0, -2], 2.0)
    self.assertEqual(seen[1][0, 2], 1.0)

  def test_rate_request_absence_and_arbitrary_overlays(self):
    base = {'tick': np.arange(30, dtype=np.int64), 'command': np.ones(30), 'speed': np.full(30, 20.0), 'streak': np.arange(1, 31)}
    ix = m.anchors(base, 'HRI_D00_L01', 1)
    expected = m.features(base, ix, 'HRI_D00_L01')
    changed = {**base, 'steeringRateDeg': np.full(30, np.nan), 'control.requested': np.full(30, 100000.0)}
    np.testing.assert_array_equal(expected, m.features(changed, ix, 'HRI_D00_L01'))

  def test_horizon_and_candidate_expansion_rejected(self):
    with self.assertRaises(ValueError):
      m.parameters('HRI_D01_L01')
    with self.assertRaises(ValueError):
      m.anchors({'streak': np.arange(30)}, 'HRI_D00_L01', 26)

  def test_prediction_error_uses_delta_primitive(self):
    # Adjacent float64 addition/subtraction can differ: retain the frozen primitive.
    current = np.full(500, 32760, dtype=np.int64)
    target = current.copy()
    fake = np.full((500, 5), 1.0)
    blocks = []
    with patch.object(data, 'design', return_value=(blocks, 'a' * 64, fake, current, target)):
      with self.assertRaisesRegex(ValueError, 'SUPPORT'):
        data.one_step([], 'HRI_D00_L01', {}, 0.0, {})


class TestCompleteSyntheticJob(unittest.TestCase):
  def setUp(self):
    # Synthetic fixtures need deterministic capacity, independent of CI host size.
    # Explicit low-space tests override this and exercise the real guard.
    capacity = type('Space', (), {'free': 100 * 1024**3})()
    space = patch.object(store.shutil, 'disk_usage', return_value=capacity)
    space.start()
    self.addCleanup(space.stop)

  @staticmethod
  def segment():
    n = 1208
    t = np.arange(n)
    tick = np.cumsum((t % 4) == 0).astype(np.int64)
    return {
      'route_id': 'a' * 64,
      'segment_sha256': 'b' * 64,
      'tick': tick,
      'streak': t + 1,
      'command': ((t % 17) - 8).astype(np.float64) / 10,
      'speed': 20.0 + (t % 7).astype(np.float64) / 10,
      'rail': np.zeros(n, bool),
      'eligible': np.ones(n, bool),
      'run': np.zeros(n, dtype=np.int64),
      'within': t,
    }

  def test_complete_job_two_runs_and_train_first(self):
    segment = self.segment()
    auth = p.seal({'synthetic': True})
    fold = {'fold': 'FOLD_A', 'train': 'a' * 64, 'development': 'c' * 64}
    clauses = store.contracts()['acceptance-gate']['clauses']
    order = []
    original_threshold = m.threshold

    def threshold(*args, **kwargs):
      order.append('THRESHOLD')
      return original_threshold(*args, **kwargs)

    def route(records, route_id, authorization):
      order.append(route_id)
      return [segment]

    with tempfile.TemporaryDirectory() as tmp, patch.object(data, 'load_route', side_effect=route), patch.object(m, 'threshold', side_effect=threshold):
      root = Path(tmp)
      first = execution.execute_job(root / 'r1', 'HRI_D00_L01', fold, [], auth, clauses)
      second = execution.execute_job(root / 'r2', 'HRI_D00_L01', fold, [], auth, clauses)
      self.assertEqual(first, second)
      self.assertEqual(order, [fold['train'], 'THRESHOLD', fold['development']] * 2)
      self.assertEqual(first['status'], 'EXECUTED_COMPLETE')
      self.assertEqual(len(first['gate']['clauses']), 32)
      self.assertEqual(set(first['rollout']), {'25', '50', '100', '200'})
      self.assertTrue(first['stage2_move_only_verified'])
      self.assertTrue(first['train_only_threshold_verified'])
      left = store.verify_manifest(root / 'r1/candidates/HRI_D00_L01/FOLD_A')
      right = store.verify_manifest(root / 'r2/candidates/HRI_D00_L01/FOLD_A')
      self.assertEqual(left, right)
      one = read.read_json(root / 'r1/candidates/HRI_D00_L01/FOLD_A/one-step/receipt.json')
      self.assertTrue({'current_tick', 'target_next_tick', 'p_move', 'candidate_error', 'rail'} <= set(one['arrays']))
      for h in m.HORIZONS:
        receipt = read.read_json(root / f'r1/candidates/HRI_D00_L01/FOLD_A/rollout-{h}/receipt.json')
        self.assertEqual(receipt['arrays']['projected_path']['shape'][1], h + 1)
        self.assertEqual(receipt['arrays']['predicted_gate_path']['shape'][1], h)
        self.assertEqual(receipt['arrays']['observed_path']['shape'], receipt['arrays']['projected_path']['shape'])
      publication.validate_public({'job': first})

  def test_oracle_failure_keeps_primary_evidence(self):
    segment = self.segment()
    _, _, x, current, target = data.design([segment], 'HRI_D00_L01')
    delta = (target - current).astype(np.float64)
    stage1 = m.fit_stage1(x, delta != 0, role='TRAIN')
    stage2 = m.fit_stage2(x, delta, role='TRAIN')
    with (
      patch.object(m, 'probability', return_value=np.zeros(len(x))),
      patch.object(m, 'predict_delta', side_effect=ValueError('HURDLE_NUMERICAL_FAILURE_NONFINITE')),
    ):
      result, arrays = data.one_step([segment], 'HRI_D00_L01', stage1, 1.0, stage2)
    self.assertEqual(result['stage2_oracle']['failure'], 'STAGE2_ORACLE_NUMERICAL_FAILURE')
    self.assertEqual(result['one_step']['count'], len(x))
    np.testing.assert_array_equal(arrays['candidate_error'], -delta)
    self.assertEqual(result['stage1_diagnostics']['status'], 'STAGE1_DIAGNOSTIC_UNDEFINED')

  def test_undefined_precision_still_all_rollouts(self):
    segment = self.segment()
    auth = p.seal({'synthetic': True})
    fold = {'fold': 'FOLD_A', 'train': 'a' * 64, 'development': 'c' * 64}
    original = m.threshold

    def all_static(*args, **kwargs):
      value = original(*args, **kwargs)
      return {**value, 'value': 1.0}

    with tempfile.TemporaryDirectory() as tmp, patch.object(data, 'load_route', return_value=[segment]), patch.object(m, 'threshold', side_effect=all_static):
      result = execution.execute_job(Path(tmp), 'HRI_D00_L01', fold, [], auth, store.contracts()['acceptance-gate']['clauses'])
    self.assertEqual(result['status'], 'EXECUTION_FAILURE')
    self.assertIn('STAGE1_DIAGNOSTIC_UNDEFINED', result['failures'])
    self.assertEqual(set(result['rollout']), {'25', '50', '100', '200'})
    self.assertTrue(all(c['evaluated'] for c in result['gate']['clauses']))

  def test_gate_mutations_rejected(self):
    original = store.contracts()['acceptance-gate']['clauses']
    for mutation in ('epsilon', 'order', 'population', 'operator'):
      clauses = deepcopy(original)
      if mutation == 'epsilon':
        clauses[0]['epsilon'] = 0.001
      elif mutation == 'order':
        clauses.reverse()
      elif mutation == 'population':
        clauses[0]['population'] = 'ORACLE'
      else:
        clauses[0]['operator'] = '<='
      with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'EXACT_32'):
        gates.fold_gate(job(), clauses)

  def test_repeat_failure_null_selection_receipt(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      store.write_json(root / 'authorization.json', p.seal({'synthetic': True}))
      with patch.object(execution, 'verify_run', side_effect=[{'receipt_sha256': 'a' * 64}, {'receipt_sha256': 'b' * 64}]):
        with self.assertRaisesRegex(ValueError, 'REPEATABILITY_FAILURE'):
          publication.repeated(root)
      receipt = read.read_json(root / 'execution-invalid.json')
      self.assertIsNone(receipt['selected_candidate'])
      self.assertFalse(receipt['selection_valid'])
      output = publication.bundle(root)
      self.assertIsNone(output['empirical-hurdle-selection-result-v1.json']['selected_candidate'])

  def test_verify_only_resume_traps_all_numeric_and_selection(self):
    # Saved synthetic receipts exercise the real hash verifier, without model execution.
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      auth = p.seal({'synthetic': True})
      store.write_json(root / 'authorization.json', auth)
      for repeat in ('repeat-1', 'repeat-2'):
        run = root / repeat
        jobs = []
        for candidate in m.CANDIDATES:
          for fold in ('FOLD_A', 'FOLD_B'):
            path = run / 'candidates' / candidate / fold
            row = p.seal({'candidate_id': candidate, 'fold': fold, 'authorization_sha256': auth['receipt_sha256']})
            jobs.append(row)
            store.write_json(path / 'receipt.json', row)
            store.finish(path, ['receipt.json'], {'receipt_sha256_binding': row['receipt_sha256']})
        selection = p.seal({'selected_candidate': None})
        result = p.seal({'authorization_sha256': auth['receipt_sha256'], 'job_count': 32, 'jobs': jobs, 'selection_sha256': selection['receipt_sha256']})
        store.write_json(run / 'results.json', result)
        store.write_json(run / 'selection.json', selection)
        names = [f.relative_to(run).as_posix() for f in run.rglob('*') if f.is_file()]
        store.finish(
          run,
          names,
          {
            'schema': 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1',
            'authorization_sha256': auth['receipt_sha256'],
            'results_sha256': result['receipt_sha256'],
            'selection_sha256': selection['receipt_sha256'],
          },
        )
      result = publication.repeated(root)
      self.assertTrue(result['trapped_resume_exact'])
      self.assertTrue(result['all_file_hashes_equal'])

  def test_exact_constant_reference_diagnostic(self):
    segment = self.segment()
    segment['command'] = np.full(len(segment['tick']), 0.1)
    _, _, x, current, target = data.design([segment], 'HRI_D00_L01')
    delta = (target - current).astype(np.float64)
    first = m.fit_stage1(x, delta != 0, role='TRAIN')
    second = m.fit_stage2(x, delta, role='TRAIN')
    self.assertNotEqual(first['normalizer']['mean'][1], 0.1)
    self.assertEqual(first['normalizer']['constant_reference'][1], 0.1)
    threshold = m.threshold(m.probability(x, first), delta != 0, role='TRAIN')['value']
    unchanged, original = data.one_step([segment], 'HRI_D00_L01', first, threshold, second)
    # The prior-delta column is constant on MOVE TRAIN but varies on ALL DEV.
    self.assertEqual(unchanged['development_constant_drift_columns'], {'stage1': 0, 'stage2': 1})
    segment['command'] = np.full(len(segment['tick']), np.nextafter(0.1, np.inf))
    changed, updated = data.one_step([segment], 'HRI_D00_L01', first, threshold, second)
    self.assertEqual(changed['development_constant_drift_columns'], {'stage1': 1, 'stage2': 2})
    self.assertEqual(original['integrated_delta'].tobytes(), updated['integrated_delta'].tobytes())
    self.assertEqual(original['p_move'].tobytes(), updated['p_move'].tobytes())
