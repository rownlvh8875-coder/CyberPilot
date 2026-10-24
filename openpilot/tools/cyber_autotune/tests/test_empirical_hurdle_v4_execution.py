"""Public synthetic V4 execution and no-private authority tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f


def fixture():
  rows = []
  for state in (0, 1):
    for command in (-1.0, 1.0):
      for tick in (-1.0, 1.0):
        for speed in (9.0, 11.0):
          for delta in (0.0,) if state == 0 else (-1.0, 1.0):
            for _ in range(52):
              rows.extend([[1.0, command, delta, tick, speed]] * 2)
  x = np.array(rows, dtype=np.float64)
  y = np.tile(np.array([0, 1]), len(x) // 2)
  norm = {
    'mean': np.zeros(5),
    'std': np.array([0.0, 1.0, 1.0, 1.0, 1.0]),
    'constant': np.zeros(5, dtype=bool),
    'effective': np.arange(5),
    'constant_reference': np.zeros(5),
  }
  return x, y, norm


class TestExecution(unittest.TestCase):
  def test_fit_and_order(self):
    x, y, norm = fixture()
    fit = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))
    self.assertEqual(fit['status'], 'TRAIN_COMPLETE')
    self.assertEqual(fit['probabilities'].shape, y.shape)
    self.assertTrue(np.all(fit['probabilities'] == 0.5))
    self.assertEqual(fit['threshold']['value'], 1.0)
    for state in (0, 1):
      self.assertEqual(fit['heads'][state]['separation']['status'], 'NO_SEPARATION')

  def test_support_failure(self):
    x, y, norm = fixture()
    x = x[:100]
    y = y[:100]
    result = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))
    self.assertEqual(result['status'], 'V4_STAGE1_FIT_FAILED_CLOSED')
    self.assertFalse(result['fallback'])

  def test_rank_and_certificate_failure(self):
    x, y, norm = fixture()
    with patch.object(e.c, 'rank_generate', return_value={'status': 'RANK_CERTIFICATE_INCONCLUSIVE'}):
      self.assertEqual(e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))['status'], 'V4_STAGE1_FIT_FAILED_CLOSED')
    with patch.object(e.c, 'separation_generate', return_value={'status': 'SEPARATION_CERTIFICATE_INCONCLUSIVE'}):
      self.assertEqual(e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))['status'], 'V4_STAGE1_FIT_FAILED_CLOSED')

  def test_optimizer_failure(self):
    x, y, norm = fixture()
    with patch.object(e.m, 'newton', side_effect=ValueError('MOVE_GATE_LINE_SEARCH_FAILURE')):
      self.assertEqual(e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))['status'], 'V4_STAGE1_FIT_FAILED_CLOSED')

  def test_repeatability_resume(self):
    x, y, norm = fixture()
    with tempfile.TemporaryDirectory() as temp:
      first = e.synthetic_run(Path(temp) / 'repeat-1', x, y, norm)
      second = e.synthetic_run(Path(temp) / 'repeat-2', x, y, norm)
      self.assertEqual(first, second)
      for name in ('train', 'development', 'recursive', 'select'):
        with patch.object(e, name, side_effect=AssertionError('recompute')):
          self.assertEqual(e.resume(Path(temp) / 'repeat-1', first['receipt_sha256'], synthetic=True), first)

  def test_gate_is_not_state(self):
    norm = fixture()[2]
    model = {
      'normalizer': norm,
      'heads': {
        0: {'positions': [0, 1, 3, 4], 'coefficients': np.array([5.0, 0.0, 0.0, 0.0])},
        1: {'positions': [0, 1, 2, 3, 4], 'coefficients': np.array([5.0, 0.0, 0.0, 0.0, 0.0])},
      },
    }
    stage2 = {'normalizer': norm, 'coefficients': np.array([0.5, 0.0, 0.0, 0.0, 0.0])}
    path, gates, contexts = e.recursive(np.array([[0, 0]], dtype=np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, 0.5, stage2, 25)
    self.assertTrue(gates.all())
    self.assertTrue((path == 0).all())  # half-even 0+.5 holds.
    self.assertTrue((contexts == 0).all())

  def test_private_missing_auth(self):
    with patch.object(e.io, 'load_models', side_effect=AssertionError('private numeric open')):
      with self.assertRaisesRegex(ValueError, 'V4_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
        e.run(authorization=None, trusted_sha256=None, replica='repeat-1', roots=None)


def segment_fixture(n=5000):
  ix = np.arange(n)
  return {
    'tick': np.resize(np.array([0, 0, 1, 1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 1, 1, 1, 0], dtype=np.int64), n),
    'streak': ix + 1,
    'command': (ix % 7 - 3).astype(float) / 3,
    'speed': 9 + (ix % 11) / 10,
    'segment_sha256': 'a' * 64,
  }


class TestSyntheticOrchestrator(unittest.TestCase):
  def test_job_train_before_dev_and_saved_dependencies(self):
    from types import SimpleNamespace

    s = segment_fixture()
    candidate = 'HRI_D00_L01'
    _, anchor, x, current, target = e.data.design([s], candidate)
    historical = {
      'candidate_id': candidate,
      'fold': 'FOLD_A',
      'train_anchor_sha256': anchor,
      'train_count': len(x),
      'train_move_count': int(np.count_nonzero(target != current)),
      'one_step': {'anchor_sha256': anchor, 'count': len(x)},
      'stage2': {'synthetic': 'BYTE_IDENTICAL_FIXTURE'},
      'rollout': {
        str(h): {'overall': {'anchor_sha256': e.data.binding([s], candidate, h)[1], 'count': e.data.binding([s], candidate, h)[2]}} for h in e.m.HORIZONS
      },
    }
    norm = fixture()[2]
    models = {'stage1': {'normalizer': norm, 'normalizer_receipt_sha256': 'b' * 64}, 'stage2': {'normalizer': norm, 'coefficients': np.zeros(5)}}
    order = []
    with tempfile.TemporaryDirectory() as temp:
      permit = SimpleNamespace(
        roots={'output': Path(temp)},
        replica='repeat-1',
        trusted_sha256='c' * 64,
        authorization={'resource_budget': {'certificate_integer_bits': 4096}},
        pack=e.a.contracts(),
      )
      prefix = f'candidates/{candidate}/FOLD_A'

      def loader(*args, development=False, receipt=None):
        if development:
          self.assertTrue((Path(temp) / 'repeat-1' / prefix / 'train-finalized.json').is_file())
          self.assertIsNotNone(receipt)
        order.append('DEV' if development else 'TRAIN')
        return [s]

      with (
        e.store.synthetic_output(Path(temp) / 'repeat-1'),
        patch.object(e.io, 'job_valid', return_value=prefix),
        patch.object(e.io, 'load_models', return_value=models),
        patch.object(e.io, 'load_route', side_effect=loader),
        patch.object(e.io, 'finalized'),
      ):
        job = e.execute_job(permit, historical)
      self.assertEqual(order, ['TRAIN', 'DEV'])
      self.assertEqual(job['status'], 'EXECUTED_COMPLETE')
      self.assertEqual(len(job['gate']['clauses']), 32)
      self.assertEqual(set(job['rollout']), {'25', '50', '100', '200'})

  def test_support_other_head_no_partial_fit(self):
    x, y, norm = fixture()
    mask = x[:, -3] == 0
    x = np.ascontiguousarray(np.concatenate((x[mask], x[~mask][:100])))
    y = np.tile(np.array([0, 1]), len(x) // 2)
    with patch.object(e.m, 'newton', side_effect=AssertionError('must certify both heads first')):
      r = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))
      self.assertEqual(r['status'], e.FAIL)

  def test_complete_and_quasi_separation(self):
    x, y, norm = fixture()
    for quasi in (False, True):
      target = (x[:, 1] > 0).astype(np.int64)
      if quasi:
        target[x[:, 1] < 0] = y[x[:, 1] < 0]
      with patch.object(e.m, 'newton', side_effect=AssertionError('separated fit')):
        r = e.train(x, target, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))
        self.assertEqual(r['status'], e.FAIL)
        self.assertEqual(r['cause'], 'SEPARATION_PRESENT')

  def test_gate_selection_all32_bothfolds(self):
    clauses = e.a.contracts()['clauses']

    def metrics():
      return {
        'count': 201,
        'anchor_sha256': 'a' * 64,
        'comparator_anchor_sha256': 'a' * 64,
        'candidate': {'rmse': 0.0, 'mae': 0.0, 'p95': 0.0, 'exact_hit': 1.0, 'within_one_tick': 1.0},
        'comparator': {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0, 'exact_hit': 0.0, 'within_one_tick': 0.0},
      }

    jobs = []
    for candidate in e.m.CANDIDATES:
      for fold in ('FOLD_A', 'FOLD_B'):
        job = {
          'candidate_id': candidate,
          'fold': fold,
          'status': 'EXECUTED_COMPLETE',
          'one_step': metrics(),
          'true_move': metrics(),
          'rollout': {str(h): {'overall': metrics(), 'path_moved': metrics()} for h in e.m.HORIZONS},
        }
        job['gate'] = e.gates.fold_gate(job, clauses)
        self.assertTrue(job['gate']['pass'])
        jobs.append(job)
    self.assertEqual(e.select(jobs, clauses)['admissible_count'], 16)
    jobs[0]['status'] = e.FAIL
    jobs[0]['gate'] = e.gates.fold_gate(jobs[0], clauses)
    self.assertEqual(e.select(jobs, clauses)['admissible_count'], 15)
    self.assertEqual(len(jobs), 32)

  def test_initial_and_recursive_context(self):
    norm = fixture()[2]
    model = {
      'normalizer': norm,
      'heads': {
        0: {'positions': [0, 1, 3, 4], 'coefficients': np.array([5.0, 0.0, 0.0, 0.0])},
        1: {'positions': [0, 1, 2, 3, 4], 'coefficients': np.array([5.0, 0.0, 0.0, 0.0, 0.0])},
      },
    }
    stage2 = {'normalizer': norm, 'coefficients': np.array([1.0, 0.0, 0.0, 0.0, 0.0])}
    initial = np.array([[0, 1], [1, 1]], np.int64)
    path, gate, z = e.recursive(initial, np.zeros((2, 25)), np.ones((2, 25)), 'HRI_D00_L01', model, 0.5, stage2, 25)
    self.assertTrue(np.array_equal(z[:, 0], [True, False]))
    self.assertTrue(z[:, 1:].all())
    self.assertTrue(gate.all())
    self.assertTrue(np.all(np.diff(path, axis=1) == 1))

  def test_all32_run_two_independent_replicas(self):
    from types import SimpleNamespace

    s = segment_fixture(3000)
    pack = e.a.contracts()
    historical = []
    for candidate in e.m.CANDIDATES:
      _, anchor, x, current, target = e.data.design([s], candidate)
      for fold in ('FOLD_A', 'FOLD_B'):
        historical.append(
          {
            'candidate_id': candidate,
            'fold': fold,
            'train_anchor_sha256': anchor,
            'train_count': len(x),
            'train_move_count': int(np.count_nonzero(target != current)),
            'one_step': {'anchor_sha256': anchor, 'count': len(x)},
            'stage2': {'synthetic': 'UNCHANGED'},
            'rollout': {
              str(h): {'overall': {'anchor_sha256': e.data.binding([s], candidate, h)[1], 'count': e.data.binding([s], candidate, h)[2]}} for h in e.m.HORIZONS
            },
          }
        )

    def models(permit, job):
      _, length = e.m.parameters(job['candidate_id'])
      dim = 2 * length + 3
      norm = {
        'mean': np.zeros(dim),
        'std': np.r_[0.0, np.ones(dim - 1)],
        'constant': np.zeros(dim, dtype=bool),
        'effective': np.arange(dim),
        'constant_reference': np.zeros(dim),
      }
      return {'stage1': {'normalizer': norm, 'normalizer_receipt_sha256': 'b' * 64}, 'stage2': {'normalizer': norm, 'coefficients': np.zeros(dim)}}

    def prefix(permit, job):
      return f"candidates/{job['candidate_id']}/{job['fold']}"

    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      manifests = []
      for replica in ('repeat-1', 'repeat-2'):
        permit = SimpleNamespace(
          roots={'output': root},
          replica=replica,
          trusted_sha256='c' * 64,
          authorization={'resource_budget': {'certificate_integer_bits': 4096, 'metadata_bytes_per_job': 131072, 'reserve_bytes': 1048576}},
          pack={**pack, 'jobs': historical},
          lineage={'jobs': historical},
        )
        with (
          patch.object(e.a, 'preflight', return_value=permit),
          patch.object(e.a, 'valid', return_value=permit),
          patch.object(e.a.prior, 'free_bytes', return_value=2**50),
          patch.object(e.io, 'job_valid', side_effect=prefix),
          patch.object(e.io, 'load_models', side_effect=models),
          patch.object(e.io, 'load_route', return_value=[s]),
          patch.object(e.io, 'finalized'),
          patch.object(e.io, 'immutability', return_value={'source_writes': 0, 'source_bytes_unchanged': True}),
        ):
          manifest = e.run(authorization=e.p.seal({'schema': 'SYNTHETIC_AUTHORIZATION_ONLY'}), trusted_sha256='c' * 64, replica=replica, roots={'output': root})
        manifests.append(manifest)
        results = e.a.prior.read_json(root / replica / 'results.json')
        self.assertEqual(results['job_count'], 32)
        self.assertEqual(len(results['jobs']), 32)
        self.assertTrue(any(j['status'] == 'EXECUTED_COMPLETE' for j in results['jobs']))
        self.assertTrue(any(j['status'] == e.FAIL for j in results['jobs']))
        self.assertEqual(e.store.verify(root / replica, manifest['receipt_sha256']), manifest)
      self.assertEqual(manifests[0], manifests[1])


class TestResumeAndImmutability(unittest.TestCase):
  def test_actual_resume_requires_trusted_auth_hash(self):
    with tempfile.TemporaryDirectory() as tmp, patch.object(e.a.prior, 'read_json', side_effect=AssertionError('premature read')):
      with self.assertRaisesRegex(ValueError, 'V4_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
        e.resume(Path(tmp), 'a' * 64)

  def test_immutability_detects_metadata_change(self):
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      path = root / 'input-pins.json'
      path.write_text('synthetic original')
      expected = e.a.prior.digest(path)
      permit = SimpleNamespace(roots={'source': root}, lineage={'metadata_pins': {'source': {'input-pins.json': expected}}})
      path.write_text('synthetic changed')
      with patch.object(e.a, 'valid'), self.assertRaisesRegex(ValueError, 'V4_SOURCE_IMMUTABILITY_FAILURE'):
        e.io.immutability(permit)

  def test_resume_traps_all_computation(self):
    x, y, norm = fixture()
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      manifest = e.synthetic_run(root, x, y, norm)
      with (
        patch.object(e.c, 'rank_generate', side_effect=AssertionError('rank')),
        patch.object(e.c, 'separation_generate', side_effect=AssertionError('sep')),
        patch.object(e.io, 'load_models', side_effect=AssertionError('model')),
        patch.object(e.io, 'load_route', side_effect=AssertionError('source')),
        patch.object(e.m, 'threshold', side_effect=AssertionError('threshold')),
        patch.object(e.m, 'newton', side_effect=AssertionError('fit')),
      ):
        self.assertEqual(e.resume(root, manifest['receipt_sha256'], synthetic=True), manifest)
