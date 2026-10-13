import unittest
import gzip
import hashlib
import io as byteio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution_math as a
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution as execution
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io


class TestV2Attribution(unittest.TestCase):
  def test_auc_exhaustive_pairs(self):
    for scores in ([0, 0, 0, 0], [0, 1, 2, 3], [3, 2, 1, 0], [0, 1, 1, 2], [1, 0, 1, 0]):
      for labels in ([0, 0, 1, 1], [0, 1, 0, 1], [1, 0, 0, 1]):
        x, y = np.array(scores, dtype=float) / 3, np.array(labels, dtype=bool)
        expected = sum(2 * int(p > n) + int(p == n) for p in x[y] for n in x[~y])
        result = a.ranking(x, y)
        self.assertEqual(result['auc_num2'], expected)
        self.assertEqual(result['auc_den2'], 8)
        self.assertEqual(result['auc'], expected / 8)

  def test_brier_and_means(self):
    x, y = np.array([0.0, 0.5, 0.5, 1.0]), np.array([0, 0, 1, 1], dtype=bool)
    result = a.ranking(x, y)
    self.assertEqual(result['brier'], 0.125)
    self.assertEqual(result['calibration_bias'], 0.0)
    self.assertEqual(result['score_mean_gap'], 0.5)

  def test_invalid_scores(self):
    for x in ([0.0, float('nan')], [-0.1, 0.2], [0.1, 1.1]):
      with self.assertRaises(ValueError):
        a.ranking(np.array(x), np.array([False, True]))

  def test_class_missing(self):
    with self.assertRaises(ValueError):
      a.ranking(np.array([0.1, 0.2]), np.array([True, True]))

  def fixture(self):
    current = np.zeros(6, dtype=np.int64)
    target = np.array([0, 0, 1, 2, -1, -2], dtype=np.int64)
    gate = np.array([1, 0, 0, 0, 1, 1], dtype=bool)
    projected = np.array([2, 0, 0, 0, -1, -1], dtype=np.int64)
    delta = projected.astype(float)
    return current, target, gate, projected, delta, delta - target, -target.astype(float)

  def test_exact_and_move_partitions(self):
    r = a.one_step(*self.fixture())
    self.assertEqual(r['exact_hit']['static_hit_loss'], 1)
    self.assertEqual(r['exact_hit']['move_hit_gain'], 1)
    self.assertEqual(r['exact_hit']['net_hit_delta'], 0)
    self.assertEqual(r['move']['FN']['ONE_TICK_MOVE'], 1)
    self.assertEqual(r['move']['FN']['MULTI_TICK_MOVE'], 1)
    self.assertEqual(r['move']['TP']['MOVE_NEGATIVE'], 2)
    self.assertEqual(r['tp']['exact_count'], 1)
    self.assertEqual(r['tp']['exact_rate'], 0.5)
    self.assertEqual(r['within']['ONE_TICK_FN']['delta_count'], 0)
    self.assertEqual(r['within']['MULTI_TICK_FN']['delta_count'], 0)

  def test_fn_identity_reject(self):
    args = list(self.fixture())
    args[4][2] = 0.25
    with self.assertRaises(ValueError):
      a.one_step(*args)

  def test_static_gate_and_projected_motion_differ(self):
    args = list(self.fixture())
    args[3][0] = 0
    args[4][0] = 0.1
    args[5][0] = 0.1
    r = a.one_step(*args)
    self.assertEqual(r['confusion']['counts']['FP'], 1)
    self.assertEqual(r['exact_hit']['static_hit_loss'], 0)

  def test_path_partitions(self):
    observed = np.array([[0, 1, 1], [0, 0, 1], [0, 1, 2]], dtype=np.int64)
    projected = np.array([[0, 0, 0], [0, 1, 1], [0, 1, 2]], dtype=np.int64)
    gate = np.array([[0, 0], [1, 0], [1, 1]], dtype=bool)
    rows = a.path_rows(observed, projected, gate)
    self.assertEqual(rows['first_departure'].tolist(), [0, 1, 1])
    self.assertEqual(rows['first_gate'].tolist(), [1, 1, 0])
    r = a.rollout(rows, (projected[:, -1] - observed[:, -1]).astype(float), (observed[:, 0] - observed[:, -1]).astype(float))
    self.assertEqual(r['hold_last_identical_count'], 1)
    self.assertEqual(r['classes']['GATE_PERFECT_PATH_MOVED']['count'], 1)
    self.assertEqual(r['classes']['GATE_PERFECT_PATH_MOVED']['support_status'], 'SMALL_SUPPORT_DESCRIPTIVE_ONLY')
    self.assertEqual(r['classes']['NO_PREDICTED_MOVE']['delta_sse'], 0.0)

  def test_rank_transfer(self):
    train = a.ranking(np.array([0.0, 1.0]), np.array([False, True]))
    dev = a.ranking(np.array([0.5, 0.5]), np.array([False, True]))
    r = a.transfer(train, dev)
    self.assertEqual(r['rank_state'], 'RANK_AT_CHANCE')
    self.assertEqual(r['transfer_state'], 'RANK_TRANSFER_DECREASED')
    self.assertTrue(r['classifier_review_evidence'])

  def test_no_subjective_auc_trigger(self):
    train = {'auc_num2': 6, 'auc_den2': 8, 'auc': 0.75}
    dev = {'auc_num2': 5, 'auc_den2': 8, 'auc': 0.625}
    self.assertFalse(a.transfer(train, dev)['classifier_review_evidence'])

  def test_brier_original_order(self):
    x = np.linspace(0.0, 1.0, 3001)
    y = np.arange(len(x)) % 3 == 0
    self.assertEqual(a.ranking(x, y)['brier'], float(np.mean((x - y.astype(float)) ** 2)))

  def test_adjacent_scores_and_signed_zero(self):
    x = np.array([-0.0, 0.0, 0.5, np.nextafter(0.5, 1.0)])
    y = np.array([0, 1, 0, 1], dtype=bool)
    self.assertEqual(a.ranking(x, y)['auc_num2'], 5)

  def test_perfect_and_reverse(self):
    y = np.array([0, 0, 1, 1], dtype=bool)
    self.assertEqual(a.ranking(np.array([0.0, 0.2, 0.8, 1.0]), y)['auc'], 1.0)
    self.assertEqual(a.ranking(np.array([1.0, 0.8, 0.2, 0.0]), y)['auc'], 0.0)

  def test_suppression_boundary(self):
    move = np.ones(100, dtype=bool)
    gate = np.arange(100) < 5
    self.assertFalse(a.decisions(move, gate, gate)['extreme_move_suppression'])
    gate[4] = False
    self.assertTrue(a.decisions(move, gate, gate)['extreme_move_suppression'])

  def test_integer_chance_comparison_before_float_rounding(self):
    n = 10**20
    train = {'auc': 0.5, 'auc_num2': n + 1, 'auc_den2': 2 * n}
    dev = {'auc': 0.5, 'auc_num2': n, 'auc_den2': 2 * n}
    self.assertTrue(a.transfer(train, dev)['classifier_review_evidence'])
    self.assertEqual(a.transfer(train, dev)['transfer_state'], 'RANK_TRANSFER_DECREASED')

  def test_job_set_reject_missing(self):
    with self.assertRaisesRegex(ValueError, 'JOB_SET'):
      execution.require_jobs([])

  def test_job_order_reject(self):
    jobs = [{'candidate_id': c, 'fold': f} for c, f in io.JOBS]
    jobs.reverse()
    with self.assertRaisesRegex(ValueError, 'JOB_SET'):
      execution.require_jobs(jobs)

  def test_historical_clause_reject(self):
    jobs = [{'gate': {'clauses': [{'id': k, 'pass': True, 'evaluated': True} for k in execution.EXPECTED]}} for _ in range(32)]
    with self.assertRaisesRegex(ValueError, 'HISTORICAL_RECONCILIATION'):
      execution.counts(jobs)

  def test_fitting_firewall(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

    with execution.firewall():
      for fn in (m.fit_stage1, m.fit_stage2, m.normalizer, np.linalg.solve, np.linalg.lstsq):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          fn()

  def test_replay_threshold_selection_firewall(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as e
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as t
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

    with execution.firewall():
      for fn in (e.run, e.train_report, e.selection, t.sweep, t.canonical, m.probability, m.predict_delta, m.recursive):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          fn()

  def test_source_loader_firewall(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as source

    with execution.firewall():
      for fn in (source.load_model, source.load_route):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          fn()

  def test_source_byte_mutation(self):
    with TemporaryDirectory() as temp:
      root = Path(temp)
      (root / 'member').write_bytes(b'one')
      hashes = {'member': io.digest(root / 'member')}
      io.verify_files(root, hashes)
      (root / 'member').write_bytes(b'two')
      with self.assertRaises(ValueError):
        io.verify_files(root, hashes)

  def test_reference_mismatch(self):
    with self.assertRaises(ValueError):
      execution.reference({'source_reference': {'manifest_sha256': 'bad'}}, {})

  def test_output_c_rejected(self):
    with self.assertRaises(ValueError):
      io.output_root(Path('/mnt/c/result'), Path('/mnt/d/source'))

  def test_traversal_rejected(self):
    with self.assertRaises(ValueError):
      io.member(Path('/mnt/d/source'), '../other')

  def test_projection_in_static_path_rejected(self):
    with self.assertRaises(ValueError):
      a.path_rows(np.array([[0, 0]], dtype=np.int64), np.array([[0, 1]], dtype=np.int64), np.array([[False]]))

  def test_empty_gate_perfect_subset(self):
    rows = a.path_rows(np.array([[0, 1]], dtype=np.int64), np.array([[0, 0]], dtype=np.int64), np.array([[False]]))
    result = a.rollout(rows, np.array([-1.0]), np.array([-1.0]))
    self.assertEqual(result['classes']['GATE_PERFECT_PATH_MOVED']['support_status'], 'EMPTY')

  def test_resume_all_computation_trapped(self):
    with patch.object(execution, 'resume', return_value={'saved': True}) as saved:
      self.assertEqual(execution.trapped_resume(Path('/mnt/d/synthetic')), {'saved': True})
      saved.assert_called_once()

  def saved_fixture(self, output):
    p = execution.p
    auth = p.seal(
      {'executor_sources': execution.sources(), 'output_identity': p.sha(str(output).encode()), 'policy_sha256': execution.policy()['receipt_sha256']}
    )
    io.write_json(output / 'authorization.json', auth)
    io.write_json(output / 'policy.json', execution.policy())
    root = output / 'repeat-1'
    names, jobs = [], []
    current, target, gate, projected, delta, error, hold = self.fixture()
    one = a.one_step(current, target, gate, projected, delta, error, hold)
    one['ranking'] = a.ranking(np.array([0.6, 0.1, 0.2, 0.3, 0.7, 0.8]), target != current)
    one['v1_exact_hit'] = one['exact_hit']
    one['v1_to_v2'] = dict.fromkeys(('static_hit_loss', 'move_hit_gain', 'net_hit_delta', 'candidate_exact_hit_count'), 0)
    train = {
      'ranking': one['ranking'],
      'decision': one['confusion'],
      'exact_hit': one['exact_hit'],
      'feasibility_slack': {},
      'selected_objective': {},
      'lineage': {},
      'continuous_train_metrics': 'SAVED_SELECTED_AGGREGATES_ONLY',
    }
    paths = {}
    for h in io.HORIZONS:
      observed = np.zeros((6, h + 1), dtype=np.int64)
      observed[0, 1:] = 1
      gates = np.diff(observed, axis=1) != 0
      path = a.rollout(a.path_rows(observed, observed.copy(), gates), np.zeros(6), (observed[:, 0] - observed[:, -1]).astype(float))
      path['v1_event_comparison'] = {}
      paths[str(h)] = path
    for c, f in io.JOBS:
      name = f'jobs/{c}/{f}/receipt.json'
      job = p.seal(
        {
          'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_JOB',
          'candidate_id': c,
          'fold': f,
          'authorization_sha256': auth['receipt_sha256'],
          'v1_job_sha256': '0' * 64,
          'v2_job_sha256': '1' * 64,
          'train': train,
          'one': one,
          'ranking_transfer': a.transfer(train['ranking'], one['ranking']),
          'rollout': paths,
          'historical_gate_pass': True,
          'historical_clauses': dict.fromkeys(execution.EXPECTED, True),
        }
      )
      io.write_json(root / name, job)
      jobs.append(job)
      names.append(name)
    summary = execution.summarize(jobs)
    ready = execution.readiness(summary)
    io.write_json(root / 'summary.json', summary)
    io.write_json(root / 'readiness.json', ready)
    return io.finish(
      root,
      [*names, 'summary.json', 'readiness.json'],
      {
        'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_MANIFEST',
        'status': execution.SUCCESS,
        'authorization_sha256': auth['receipt_sha256'],
        'policy_sha256': execution.policy()['receipt_sha256'],
        'v1_manifest_sha256': io.SOURCE_SHA,
        'v2_manifest_sha256': execution.V2_SHA,
        'job_order': [list(j) for j in io.JOBS],
        'summary_sha256': summary['receipt_sha256'],
        'readiness_sha256': ready['receipt_sha256'],
      },
    )

  def test_real_saved_resume_without_source(self):
    with TemporaryDirectory() as temp:
      output = Path(temp)
      expected = self.saved_fixture(output)
      self.assertEqual(execution.trapped_resume(output / 'repeat-1'), expected)

  def test_incomplete_saved_job_rejected(self):
    with self.assertRaisesRegex(ValueError, 'AGGREGATE_INCOMPLETE'):
      execution.validate_job({'candidate_id': io.CANDIDATES[0], 'fold': 'FOLD_A', 'authorization_sha256': '0' * 64})

  def test_incomplete_saved_summary_rejected(self):
    with self.assertRaisesRegex(ValueError, 'AGGREGATE_INCOMPLETE'):
      execution.validate_summary({'missing_attribution_outputs': True})

  def test_resume_rejects_one_byte_change(self):
    with TemporaryDirectory() as temp:
      output = Path(temp)
      self.saved_fixture(output)
      with (output / 'repeat-1/summary.json').open('ab') as file:
        file.write(b' ')
      with self.assertRaises(ValueError):
        execution.trapped_resume(output / 'repeat-1')

  def compressed_fixture(self, root):
    values = np.array([0.1, 0.2, 0.3])
    buffer = byteio.BytesIO()
    np.save(buffer, values, allow_pickle=False)
    raw = buffer.getvalue()
    compressed = gzip.compress(raw, mtime=0)
    (root / 'data.npy.gz').write_bytes(compressed)
    return {
      'storage_format': 'NPY_GZIP_V1',
      'lossless_roundtrip_verified': True,
      'file_sha256': hashlib.sha256(compressed).hexdigest(),
      'npy_sha256': hashlib.sha256(raw).hexdigest(),
      'array_sha256': hashlib.sha256(values.tobytes()).hexdigest(),
      'shape': [3],
      'dtype': '<f8',
      'order': 'C',
    }

  def test_compressed_and_decoded_identity(self):
    with TemporaryDirectory() as temp:
      root = Path(temp)
      binding = self.compressed_fixture(root)
      self.assertEqual(np.concatenate(list(io.array_chunks(root / 'data.npy.gz', binding))).tolist(), [0.1, 0.2, 0.3])
      binding['npy_sha256'] = '0' * 64
      with self.assertRaisesRegex(ValueError, 'DECODED_CONFLICT'):
        list(io.array_chunks(root / 'data.npy.gz', binding))

  def test_compressed_mutation_rejected_before_decode(self):
    with TemporaryDirectory() as temp:
      root = Path(temp)
      binding = self.compressed_fixture(root)
      binding['file_sha256'] = '0' * 64
      with patch.object(gzip, 'open', side_effect=AssertionError('must not decode')):
        with self.assertRaisesRegex(ValueError, 'COMPRESSED_CONFLICT'):
          list(io.array_chunks(root / 'data.npy.gz', binding))

  def test_public_threshold_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v2_publication import privacy

    for obj in ({'threshold': 0.123}, {'actual_threshold': 0.123}, {'coefficients': [1.0]}, {'path': '/mnt/d/private'}):
      with self.assertRaises(ValueError):
        privacy(obj)

  def test_auc_repeatability(self):
    x = np.array([0.25, 0.25, 0.5, 0.5, 1.0])
    y = np.array([False, True, False, True, True])
    self.assertEqual(execution.p.canonical(a.ranking(x, y)), execution.p.canonical(a.ranking(x.copy(), y.copy())))
