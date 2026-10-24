"""Synthetic executor regression: real inference/sweep/rollout, no fitted data."""

from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as e
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_publication as publication
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as t
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates


class TestV2Execution(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.stack = ExitStack()
    self.addCleanup(self.stack.close)
    self.stack.enter_context(patch.object(io, 'output_path', side_effect=lambda path, excluded=(): io.safe(path)))
    self.stack.enter_context(patch.object(io, 'headroom'))
    self.stack.enter_context(patch.object(io, 'validate_seal'))
    n = 1300
    tick = np.arange(n, dtype=np.int64) // 3
    self.segment = {
      'route_id': 'a' * 64,
      'segment_sha256': 'b' * 64,
      'tick': tick,
      'streak': np.arange(1, n + 1),
      'command': np.r_[np.diff(tick), 0.0].astype(float),
      'speed': np.full(n, 15.0),
      'rail': np.zeros(n, bool),
      'eligible': np.ones(n, bool),
      'run': np.zeros(n, np.int64),
      'within': np.arange(n, dtype=np.int64),
    }
    norm = {'effective': np.arange(5), 'mean': np.zeros(5), 'std': np.ones(5), 'constant': np.zeros(5, bool), 'constant_reference': np.zeros(5)}
    self.models = {
      'stage1': {'normalizer': norm, 'coefficients': np.array([-1.0, 2.0, 0.0, 0.0, 0.0])},
      'stage2': {'normalizer': deepcopy(norm), 'coefficients': np.array([0.0, 1.0, 0.0, 0.0, 0.0])},
    }
    self.auth = p.seal({'schema': 'SYNTHETIC_AUTHORIZATION'})
    self.candidate, self.fold = 'HRI_D00_L01', 'FOLD_A'
    self.jobroot = self.root / 'source/repeat-1/candidates' / self.candidate / self.fold
    blocks, anchor, x, current, target = data.design([self.segment], self.candidate)
    pop = io.population(
      self.jobroot / 'train', {**data.context(blocks, self.candidate), 'actual_delta_tick': (target - current).astype(float)}, {'schema': 'SYNTHETIC_TRAIN'}
    )
    probabilities = m.probability(x, self.models['stage1'])
    threshold = io.population(self.jobroot / 'threshold', {'train_probability': probabilities, 'threshold': np.array([0.0])}, {'schema': 'SYNTHETIC_THRESHOLD'})
    self.historical = {
      'candidate_id': self.candidate,
      'fold': self.fold,
      'train_route': 'a' * 64,
      'development_route': 'c' * 64,
      'train_count': len(x),
      'train_move_count': int(np.count_nonzero(target - current)),
      'train_anchor_sha256': anchor,
      'population_receipts': {'train': pop['receipt_sha256']},
      'threshold': {'receipt_sha256': threshold['receipt_sha256']},
      'rollout': {},
      'status': 'EXECUTED_COMPLETE',
    }
    for stage in ('stage1', 'stage2'):
      normreceipt = io.population(self.jobroot / stage / 'normalizer', self.models[stage]['normalizer'], {'schema': 'SYNTHETIC_NORMALIZER'})
      modelreceipt = io.population(
        self.jobroot / stage / 'model',
        {'coefficients': self.models[stage]['coefficients']},
        {
          'schema': 'SYNTHETIC_MODEL',
          'normalizer_sha256': normreceipt['receipt_sha256'],
          'effective_x_sha256': io.old.array_digest(
            m.transform(x if stage == 'stage1' else np.ascontiguousarray(x[target != current]), self.models[stage]['normalizer'])
          ),
        },
      )
      self.historical[stage] = {
        'model_receipt_sha256': modelreceipt['receipt_sha256'],
        'normalizer_receipt_sha256': normreceipt['receipt_sha256'],
        'coefficient_sha256': modelreceipt['arrays']['coefficients']['array_sha256'],
      }
    metrics, arrays = data.one_step([self.segment], self.candidate, self.models['stage1'], 0.0, self.models['stage2'])
    self.historical.update(metrics)
    receipt = io.population(self.jobroot / 'one-step', arrays, {'schema': 'SYNTHETIC_ONE_STEP'})
    self.historical['population_receipts']['one-step'] = receipt['receipt_sha256']
    for h in m.HORIZONS:
      metrics, arrays = data.rollout([self.segment], self.candidate, self.models['stage1'], 0.0, self.models['stage2'], h)
      self.historical['rollout'][str(h)] = metrics
      receipt = io.population(self.jobroot / f'rollout-{h}', arrays, {'schema': 'SYNTHETIC_ROLLOUT'})
      self.historical['population_receipts'][f'rollout-{h}'] = receipt['receipt_sha256']
    self.clauses = io.old.contracts()['acceptance-gate']['clauses']
    self.historical['gate'] = gates.fold_gate(self.historical, self.clauses)

  def run_job(self, name='run', historical=None):
    events = []

    def load(records, route, auth):
      events.append(route)
      if route == self.historical['development_route']:
        e.finalized(self.root / name / 'candidates' / self.candidate / self.fold, auth, self.historical)
      return [self.segment]

    with patch.object(io, 'load_route', side_effect=load), io.firewall():
      result = e.execute_job(self.root / name, self.root / 'source', historical or self.historical, [], self.auth, self.clauses)
    self.assertEqual(events, [self.historical['train_route'], self.historical['development_route']])
    return result

  def test_full_job_two_independent_outputs(self):
    first = self.run_job('one')
    second = self.run_job('two')
    self.assertEqual(first, second)
    self.assertEqual(first['status'], 'EXECUTED_COMPLETE')
    self.assertEqual(len(first['gate']['clauses']), 32)
    self.assertEqual(set(first['rollout']), {'25', '50', '100', '200'})
    self.assertEqual(first['threshold']['saved_probability_comparison'], 'BYTE_EXACT_PASS')
    publication.privacy(first)
    for file in (self.root / 'one').rglob('*'):
      if file.is_file():
        self.assertEqual(file.read_bytes(), (self.root / 'two' / file.relative_to(self.root / 'one')).read_bytes())
    for pop in ('train', 'one-step', 'rollout-25'):
      receipt = io.read_json(self.root / 'one/candidates' / self.candidate / self.fold / pop / 'receipt.json')
      self.assertNotIn('observed_path', receipt['arrays'])
      self.assertNotIn('hold_last_path', receipt['arrays'])
      self.assertNotIn('coefficients', receipt['arrays'])

  def test_saved_probability_mismatch_rejected(self):
    original = m.probability

    def changed(*args):
      a = original(*args)
      a[0] = np.nextafter(a[0], 1.0)
      return a

    with patch.object(m, 'probability', side_effect=changed):
      with self.assertRaisesRegex(ValueError, 'PREDICTION_IDENTITY_FAILURE'):
        self.run_job()

  def test_model_identity_mismatch_rejected(self):
    for stage in ('stage1', 'stage2'):
      for key in ('model_receipt_sha256', 'normalizer_receipt_sha256', 'coefficient_sha256'):
        bad = deepcopy(self.historical[stage])
        bad[key] = '0' * 64
        with self.assertRaises(ValueError):
          io.load_model(self.jobroot, stage, bad, self.auth)

  def test_train_anchor_mismatch_rejected(self):
    bad = deepcopy(self.historical)
    bad['train_anchor_sha256'] = '0' * 64
    with patch.object(io, 'load_route', return_value=[self.segment]):
      with self.assertRaisesRegex(ValueError, 'ANCHOR_IDENTITY'):
        e.execute_job(self.root / 'wrong', self.root / 'source', bad, [], self.auth, self.clauses)

  def test_row_reorder_rejected(self):
    array = np.array([1.0, 2.0, 3.0])
    binding = {'dtype': array.dtype.str, 'shape': [3], 'array_sha256': io.old.array_digest(array)}
    with self.assertRaises(ValueError):
      e.require_same_array(array[::-1], binding)

  def test_no_refit_firewall(self):
    with io.firewall():
      for fn in (m.fit_stage1, m.fit_stage2, m.normalizer, m.newton, m.threshold, np.linalg.solve, np.linalg.lstsq):
        with self.assertRaisesRegex(ValueError, 'FORBIDDEN'):
          fn(None)

  def test_stage2_all_train_population(self):
    calls = []
    original = m.predict_delta

    def tracked(x, model):
      calls.append(len(x))
      return original(x, model)

    with patch.object(m, 'predict_delta', side_effect=tracked):
      self.run_job()
    self.assertEqual(calls[0], self.historical['train_count'])
    self.assertGreater(calls[0], self.historical['train_move_count'])

  def test_threshold_finalization_required(self):
    with self.assertRaises(OSError):
      e.finalized(self.root / 'empty', self.auth, self.historical)

  def test_comparator_and_gate_mutation_rejected(self):
    bad = deepcopy(self.historical)
    bad['one_step']['comparator_anchor_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      gates.fold_gate(bad, self.clauses)
    for mutation in (self.clauses[:-1], list(reversed(self.clauses))):
      with self.assertRaises(ValueError):
        gates.fold_gate(self.historical, mutation)

  def test_nonadmissible_selection_not_promoted(self):
    jobs = []
    for candidate, fold in io.JOBS:
      j = deepcopy(self.historical)
      j.update(candidate_id=candidate, fold=fold, status='NO_FEASIBLE_THRESHOLD')
      j['gate'] = gates.fold_gate(j, self.clauses)
      jobs.append(j)
    selected = e.selection(jobs, self.clauses)
    self.assertEqual(selected['status'], 'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE')
    self.assertIsNone(selected['selected_candidate'])

  def test_repeatability_single_byte_change(self):
    first = self.run_job('one')
    second = self.run_job('two')
    a = self.root / 'two/candidates' / self.candidate / self.fold / 'train/projected_next_tick.npy.gz'
    raw = bytearray(a.read_bytes())
    raw[-1] ^= 1
    a.write_bytes(raw)
    self.assertEqual(first, second)
    with self.assertRaises(ValueError):
      io.old.verify_manifest(a.parent.parent)

  def test_privacy_threshold_and_model_values(self):
    for payload in ({'threshold': 0.4}, {'coefficients': [1.0]}, {'mean': [1.0]}, {'path': '/mnt/d/private'}):
      with self.assertRaises(ValueError):
        publication.privacy(payload)

  def test_projection_range_and_lossless_storage(self):
    a = np.array([-32768, 0, 32767], np.int64)
    self.assertTrue(np.array_equal(io.compact_ticks(a).astype(np.int64), a))
    with self.assertRaises(ValueError):
      io.compact_ticks(np.array([32768]))
    first = io.array_write(self.root / 'a.npy.gz', a)
    second = io.array_write(self.root / 'b.npy.gz', a)
    self.assertEqual(first['file_sha256'], second['file_sha256'])
    with self.assertRaises(ValueError):
      io.array_write(self.root / 'a.npy.gz', a)

  def test_observer_cannot_change_selection(self):
    probability = np.array([1.0, 1.0, 1.0])
    delta = np.array([0.4, 0.6, 0.8])
    current = np.array([0, 2, 4])
    target = np.array([0, 2, 5])
    a = t.sweep(probability, delta, current, target, role='TRAIN')
    b = t.sweep(probability, delta, current, target, role='TRAIN', observer=lambda _, row: row.update(feasible=False))
    self.assertEqual(a, b)

  def saved_run(self, name):
    root = self.root / name
    jobs = []
    for candidate, fold in io.JOBS:
      path = root / 'candidates' / candidate / fold
      decision = p.seal(
        {
          'schema': 'HURDLE_STAGE1_V2_PRIVATE_THRESHOLD_RECEIPT',
          'authorization_sha256': self.auth['receipt_sha256'],
          'candidate_id': candidate,
          'fold': fold,
          'status': t.NO_FEASIBLE,
          'threshold': None,
          'candidate_count': 3,
          'feasible_count': 0,
          'objective': None,
          'canonical_checks': 3,
        }
      )
      io.write_json(path / 'threshold/receipt.json', decision)
      job = p.seal(
        {
          'candidate_id': candidate,
          'fold': fold,
          'status': 'NO_FEASIBLE_THRESHOLD',
          'failures': [t.NO_FEASIBLE],
          'authorization_sha256': self.auth['receipt_sha256'],
          'populations': {},
          'rollout': {},
          'threshold': {'receipt_sha256': decision['receipt_sha256']},
        }
      )
      io.write_json(path / 'receipt.json', job)
      io.old.finish(path, ['threshold/receipt.json', 'receipt.json'], {'schema': 'V2_JOB_MANIFEST', 'receipt_sha256_binding': job['receipt_sha256']})
      jobs.append(job)
    selected = p.seal({'schema': 'HURDLE_STAGE1_V2_SELECTION_RESULT', 'selected_candidate': None})
    result = p.seal(
      {
        'schema': 'HURDLE_STAGE1_V2_RESULTS',
        'jobs': jobs,
        'job_count': 32,
        'authorization_sha256': self.auth['receipt_sha256'],
        'selection_sha256': selected['receipt_sha256'],
      }
    )
    io.write_json(root / 'results.json', result)
    io.write_json(root / 'selection.json', selected)
    names = [f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()]
    manifest = io.old.finish(
      root,
      names,
      {
        'schema': 'HURDLE_STAGE1_V2_RUN_MANIFEST',
        'status': e.SUCCESS,
        'authorization_sha256': self.auth['receipt_sha256'],
        'job_count': 32,
        'results_sha256': result['receipt_sha256'],
        'selection_sha256': selected['receipt_sha256'],
      },
    )
    return root, manifest

  def test_verify_only_resume_all_computation_trapped(self):
    root, manifest = self.saved_run('resume')
    self.assertEqual(e.trapped_resume(root, self.auth), manifest)

  def test_resume_missing_job_rejected(self):
    root, _ = self.saved_run('resume')
    (root / 'candidates/HRI_D20_L45/FOLD_B/receipt.json').unlink()
    with self.assertRaises((OSError, ValueError)):
      e.trapped_resume(root, self.auth)

  def test_sweep_equivalence_failure_is_hard_failure(self):
    p, b, c, target = np.array([0.2, 0.8]), np.array([0.2, 0.9]), np.array([0, 0]), np.array([0, 1])
    original = t.canonical

    def wrong(*args):
      row = original(*args)
      row['all_rmse'] = np.nextafter(row['all_rmse'], np.inf)
      return row

    with patch.object(t, 'canonical', side_effect=wrong):
      with self.assertRaisesRegex(ValueError, 'EQUIVALENCE_FAILURE'):
        t.sweep(p, b, c, target, role='TRAIN')

  def test_normalized_feature_identity_rejected(self):
    original = io.load_model

    def wrong(*args):
      model = original(*args)
      model['effective_x_sha256'] = '0' * 64
      return model

    with patch.object(io, 'load_model', side_effect=wrong):
      with self.assertRaisesRegex(ValueError, 'FEATURE_IDENTITY_CONFLICT'):
        self.run_job()

  def test_development_anchor_mismatch_rejected(self):
    bad = deepcopy(self.historical)
    bad['one_step']['anchor_sha256'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'ANCHOR_IDENTITY_CONFLICT'):
      self.run_job(historical=bad)

  def test_rollout_anchor_mismatch_rejected(self):
    bad = deepcopy(self.historical)
    bad['rollout']['25']['overall']['anchor_sha256'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'ANCHOR_IDENTITY_CONFLICT'):
      self.run_job(historical=bad)

  def test_validation_publication_is_allowlisted(self):
    value = {k: {'status': 'PASS', 'tests': 0, 'subtests': 0} for k in publication.VALIDATION_CHECKS}
    publication.validate_checks(value)
    for key in ('command', 'threshold_value', 'private_path'):
      with self.assertRaises(ValueError):
        publication.validate_checks({**value, key: [0.5]})
    for invalid in ({'status': 'PASS', 'tests': 'D:/private', 'subtests': 0}, {'status': 'NOT_RUN', 'tests': 0, 'subtests': 0}):
      with self.assertRaises(ValueError):
        publication.validate_checks({**value, 'focused': invalid})

  def test_comparison_is_report_only(self):
    j = self.run_job()
    self.assertEqual(j['comparison']['authority'], 'REPORT_ONLY')
    self.assertEqual(j['train_comparison']['authority'], 'REPORT_ONLY')
    self.assertEqual(sum(len(v) for v in j['comparison']['clauses'].values()), 32)

  def test_soft_blending_and_forced_movement_absent(self):
    x = np.array([[1.0, 0.0, 0.0, 0.0, 15.0], [1.0, 1.0, 0.0, 2.0, 15.0]])
    stage2 = {**self.models['stage2'], 'coefficients': np.array([0.4, 0.0, 0.0, 0.0, 0.0])}
    delta, projected, probability, gate = m.integrated(x, np.array([0, 2]), self.models['stage1'], 0.5, stage2)
    self.assertFalse(gate[0])
    self.assertTrue(gate[1])
    np.testing.assert_array_equal(delta, [0.0, 0.4])
    np.testing.assert_array_equal(projected, [0, 2])
    self.assertNotEqual(delta[1], probability[1] * 0.4)

  def test_numerical_failure_is_accounted_without_development(self):
    with patch.object(io, 'load_route', return_value=[self.segment]) as loader:
      with patch.object(m, 'probability', side_effect=ValueError('HURDLE_NUMERICAL_FAILURE_NONFINITE')):
        job = e.execute_job(self.root / 'failed', self.root / 'source', self.historical, [], self.auth, self.clauses)
    self.assertEqual(job['status'], 'NUMERICAL_FAILURE')
    self.assertEqual(loader.call_count, 1)
    self.assertEqual(len(job['gate']['clauses']), 32)
    self.assertFalse(job['gate']['pass'])
    io.old.verify_manifest(self.root / 'failed/candidates' / self.candidate / self.fold)


class TestV2StorageBoundary(unittest.TestCase):
  def test_c_and_non_d_outputs_rejected(self):
    for path in ('/mnt/c/results', '/tmp/results', '/mnt/d/../c/results'):
      with self.assertRaises(ValueError):
        io.output_path(Path(path))

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      (root / 'alias').symlink_to(root, target_is_directory=True)
      with self.assertRaises(ValueError):
        io.safe(root / 'alias/child')

  def test_capacity_counts_both_payloads_and_reserve(self):
    j = {'train_count': 100, 'one_step': {'count': 100}, 'rollout': {str(h): {'overall': {'count': 100}} for h in m.HORIZONS}}
    cap = io.capacity([j] * 32)
    self.assertEqual(cap['run1_upper_bytes'], cap['run2_upper_bytes'])
    self.assertGreater(cap['atomic_upper_bytes'], 0)
    self.assertGreater(cap['safety_reserve_bytes'], 0)

  def test_private_forward_slash_path_rejected(self):
    with self.assertRaises(ValueError):
      publication.privacy({'private_path': 'D:/private/results'})

  def test_capacity_failure_before_any_numeric_read(self):
    with patch.object(io.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 0})()):
      with patch.object(io, 'output_path', return_value=Path('/tmp')):
        with patch.object(io.Path, 'stat', return_value=type('Stat', (), {'st_dev': 1})()):
          with self.assertRaisesRegex(ValueError, 'STORAGE_CAPACITY_BLOCKED'):
            io.headroom(Path('/tmp'), 1)

  def test_validate_seal_rejects_fit_authority(self):
    base = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_RETROSPECTIVE_EXECUTION_AUTHORIZATION',
        'prediction_only_authorized': True,
        'array_access_before_seal': False,
        'stage1_fitting_authorized': False,
        'stage2_fitting_authorized': False,
        'normalizer_fitting_authorized': False,
        'executor_sources': io.sources(),
      }
    )
    io.validate_seal(base)
    for field in ('stage1_fitting_authorized', 'stage2_fitting_authorized', 'normalizer_fitting_authorized'):
      invalid = p.seal({k: v for k, v in {**base, field: True}.items() if k != 'receipt_sha256'})
      with self.assertRaises(ValueError):
        io.validate_seal(invalid)
