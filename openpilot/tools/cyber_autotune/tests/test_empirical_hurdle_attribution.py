import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as a


class TestAttributionMath(unittest.TestCase):
  def test_exact_hit_loss_distinguishes_gate_from_projected_motion(self):
    actual = np.array([0, 0, 0, 1, -2], dtype=np.int64)
    current = np.zeros(5, dtype=np.int64)
    delta = np.array([0.0, 0.2, 1.0, 0.0, -2.0])
    row = a.one_step(
      {
        'actual_delta_tick': actual,
        'current_tick': current,
        'target_next_tick': actual,
        'predicted_gate': np.array([False, True, True, False, True]),
        'projected_next_tick': np.array([0, 0, 1, 0, -2]),
        'integrated_delta': delta,
        'candidate_error': delta - actual,
        'comparator_error': -actual.astype(float),
        'true_move': actual != 0,
        'hold_last_next_tick': current,
        'stage2_oracle_move_prediction': np.array([1.0, -2.0]),
      }
    )
    self.assertEqual(row['confusion']['counts'], {'TN': 1, 'FP': 2, 'FN': 1, 'TP': 1})
    self.assertEqual(row['exact_hit']['static_hit_loss'], 1)
    self.assertEqual(row['exact_hit']['move_hit_gain'], 1)
    self.assertEqual(row['exact_hit']['net_hit_delta'], 0)
    self.assertEqual(row['fp']['projected_same_tick_count'], 1)
    self.assertEqual(row['fp']['projected_moved_count'], 1)
    self.assertTrue(row['fn']['integrated_equals_hold'])
    self.assertEqual(row['oracle']['oracle_to_integrated_delta_sse'], 1.0)
    self.assertEqual(row['classes']['MOVE']['count'], 2)

  def test_path_events_include_gate_perfect_residual_and_gate_only_error(self):
    truth = np.array([[0, 0, 0], [0, 1, 2], [0, 1, 1], [0, 0, 1], [0, 0, 0], [0, 1, 2]], dtype=np.int64)
    projected = np.array([[0, 0, 0], [0, 2, 4], [0, 0, 0], [0, 1, 1], [0, 0, 0], [0, 1, 1]], dtype=np.int64)
    gates = np.array([[1, 0], [1, 1], [0, 0], [0, 1], [0, 0], [1, 0]], dtype=bool)
    out = a.path_rows(truth, projected, gates)
    self.assertEqual(out['first_gate'].tolist(), [1, 0, 1, 0, 0, 2])
    self.assertEqual(out['first_divergence'].tolist(), [0, 1, 1, 1, 0, 2])
    self.assertEqual(out['gate_fp_count'].tolist(), [1, 0, 0, 0, 0, 0])
    self.assertEqual(out['gate_fn_count'].tolist(), [0, 0, 1, 0, 0, 1])
    self.assertEqual(out['gate_perfect'].tolist(), [False, True, False, True, True, False])

  def test_first_event_uses_one_based_steps_and_zero_for_none(self):
    self.assertEqual(a.first(np.array([[0, 0], [0, 1], [1, 1]], dtype=bool)).tolist(), [0, 2, 1])

  def test_empty_metrics_null_and_small_support_explicit(self):
    self.assertIsNone(a.metrics(np.array([])))
    self.assertEqual(a.pair(np.array([2.0]), np.array([1.0]))['support_status'], 'SMALL_SUPPORT_DESCRIPTIVE_ONLY')

  def test_confusion_transfer_is_from_counts_and_keeps_direction(self):
    train = a.confusion_counts({'TP': 2, 'TN': 6, 'FP': 2, 'FN': 0})
    dev = a.confusion_counts({'TP': 1, 'TN': 4, 'FP': 4, 'FN': 1})
    out = a.transfer(train, dev)
    self.assertEqual(out['dev_minus_train']['false_move_rate'], 0.25)
    self.assertEqual(out['dev_minus_train']['recall'], -0.5)
    self.assertEqual(train['true_move_fraction'], 0.2)

  def test_nonfinite_errors_fail_closed(self):
    with self.assertRaises(ValueError):
      a.metrics(np.array([float('nan')]))


class TestEvidenceBoundary(unittest.TestCase):
  def test_compressed_member_rejects_decoded_hash_drift(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      path, receipt = compressed_fixture(Path(tmp), np.arange(12, dtype=np.int64).reshape(4, 3))
      receipt['npy_sha256'] = '0' * 64
      with self.assertRaisesRegex(ValueError, 'CONFLICT'):
        list(io.array_chunks(path, receipt))

  def test_compressed_rows_keep_order_without_disk_extraction(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      path, receipt = compressed_fixture(Path(tmp), np.arange(18, dtype=np.int64).reshape(6, 3))
      chunks = list(io.array_chunks(path, receipt, chunk=2))
      self.assertEqual([v.shape for v in chunks], [(2, 3)] * 3)
      self.assertEqual(np.concatenate(chunks).tolist(), [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11], [12, 13, 14], [15, 16, 17]])
      self.assertEqual(len(list(Path(tmp).iterdir())), 1)

  def test_traversal_and_symlink_rejected_before_open(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      with self.assertRaises(ValueError):
        io.member(root, '../forbidden')
      (root / 'link').symlink_to(root, target_is_directory=True)
      with self.assertRaises(ValueError):
        io.member(root, 'link/x')

  def test_execution_firewall_traps_real_fitting_threshold_and_replay_entrypoints(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data

    with io.firewall():
      for call in [
        old.fit_stage1,
        old.fit_stage2,
        old.normalizer,
        old.threshold,
        old.probability,
        old.predict_delta,
        old.integrated,
        old.project,
        old.recursive,
        gates.select,
        data.load_route,
        np.linalg.solve,
        np.linalg.lstsq,
      ]:
        with self.subTest(call=call), self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          call()


def compressed_fixture(root, array):
  import gzip
  import io as streamio
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p

  data = streamio.BytesIO()
  np.save(data, array, allow_pickle=False)
  raw = data.getvalue()
  path = root / 'array.npy.gz'
  path.write_bytes(gzip.compress(raw, mtime=0))
  return path, {
    'filename': path.name,
    'storage_format': 'NPY_GZIP_V1',
    'dtype': array.dtype.str,
    'shape': list(array.shape),
    'order': 'C',
    'file_sha256': p.sha(path.read_bytes()),
    'npy_sha256': p.sha(raw),
    'array_sha256': p.sha(array.tobytes()),
    'lossless_roundtrip_verified': True,
  }


class TestAttributionContracts(unittest.TestCase):
  def test_six_first_event_relations_are_exhaustive(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    truth = np.array([[0, 0, 0, 0], [0, 1, 1, 1], [0, 1, 1, 1], [0, 0, 0, 0], [0, 1, 2, 2], [0, 0, 0, 0]], dtype=np.int64)
    predicted = np.array([[0, 0, 1, 1], [0, 0, 0, 0], [0, 2, 3, 3], [0, 0, 0, 0], [0, 2, 4, 4], [0, 0, 0, 0]], dtype=np.int64)
    gates = np.array([[1, 1, 0], [0, 0, 0], [1, 1, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0]], dtype=bool)
    rows = a.path_rows(truth, predicted, gates)
    out = a.rollout(rows, (predicted[:, -1] - truth[:, -1]).astype(float), -truth[:, -1].astype(float))
    self.assertEqual(set(out['first_event_relation'].values()), {1})
    self.assertEqual(out['classes']['GATE_PERFECT_PATH_MOVED']['count'], 1)
    self.assertEqual(out['classes']['GATE_PERFECT_PATH_MOVED']['delta_sse'], 0.0)
    self.assertEqual(out['classes']['GATE_ERROR_PATH_MOVED']['count'], 2)
    self.assertEqual(out['path_flat']['any_move_gate_count'], 2)
    self.assertEqual(out['path_flat']['any_projected_motion_count'], 1)
    self.assertEqual(sum(out['gate_confusion']['counts'].values()), 18)
    self.assertEqual(run.policy()['alternative_thresholds'], False)

  def test_true_gate_uses_consecutive_observation_not_displacement_from_start(self):
    rows = a.path_rows(np.array([[3, 4, 4, 3]], dtype=np.int64), np.array([[3, 4, 4, 3]], dtype=np.int64), np.array([[1, 0, 1]], dtype=bool))
    self.assertEqual(rows['observed_move_count'].tolist(), [2])
    self.assertEqual(rows['gate_perfect'].tolist(), [True])
    self.assertEqual(rows['path_moved'].tolist(), [True])

  def test_gate_perfect_does_not_mean_projected_path_correct(self):
    rows = a.path_rows(np.array([[0, 1, 2]], dtype=np.int64), np.array([[0, 2, 5]], dtype=np.int64), np.array([[1, 1]], dtype=bool))
    out = a.rollout(rows, np.array([3.0]), np.array([-2.0]))
    self.assertEqual(out['classes']['GATE_PERFECT_PATH_MOVED']['delta_sse'], 5.0)
    self.assertEqual(out['first_event_relation']['divergence_only'], 1)

  def test_empty_gate_perfect_subset_has_no_fabricated_zero_metric(self):
    rows = a.path_rows(np.array([[0, 1]], dtype=np.int64), np.array([[0, 0]], dtype=np.int64), np.array([[0]], dtype=bool))
    out = a.rollout(rows, np.array([-1.0]), np.array([-1.0]))
    self.assertIsNone(out['classes']['GATE_PERFECT_PATH_MOVED']['candidate'])

  def test_partition_rejects_overlap_and_missing_row(self):
    for masks in ([np.array([1, 1], bool), np.array([0, 1], bool)], [np.array([1, 0], bool), np.array([0, 0], bool)]):
      with self.subTest(masks=masks), self.assertRaises(ValueError):
        a.partition_accounting(np.ones(2), np.ones(2), masks)

  def test_partition_preserves_float_roundoff_instead_of_tolerance(self):
    out = a.partition_accounting(np.array([1e16, 1.0, 1.0]), np.zeros(3), [np.array([1, 0, 0], bool), np.array([0, 1, 1], bool)])
    self.assertTrue(out['row_partition_exact'])
    self.assertEqual(out['candidate']['sae']['partition_minus_original'], 2.0)

  def test_linear_p95_not_sum_of_subset_percentiles(self):
    self.assertAlmostEqual(a.metrics(np.array([0.0, 1.0, 2.0, 3.0]))['p95'], 2.85)
    self.assertEqual(a.metrics(np.array([0.0, 1.0, 2.0, 3.0]))['sse'], 14.0)

  def test_strict_trigger_requires_all_four_facts_in_all_jobs(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    facts = [{'move_protection_pass': True, 'exact_hit_fail': True, 'static_loss_exceeds_gain': True, 'projected_false_move': True} for _ in range(32)]
    value = run.mechanism(facts)
    self.assertEqual(value['stage1_design_review'], 'STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED')
    self.assertFalse(value['implementation_authorized'])
    self.assertFalse(value['fitting_authorized'])
    for key in facts[0]:
      changed = [dict(f) for f in facts]
      changed[17][key] = False
      with self.subTest(key=key):
        self.assertEqual(run.mechanism(changed)['stage1_design_review'], 'STAGE1_GATE_REDESIGN_REVIEW_NOT_FULLY_SUPPORTED')

  def test_trigger_rejects_partial_job_set(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    with self.assertRaisesRegex(ValueError, 'JOB_SET_CONFLICT'):
      run.mechanism([])

  def test_historical_reconciliation_has_no_epsilon(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    with self.assertRaisesRegex(ValueError, 'HISTORICAL_RECONCILIATION_FAILURE'):
      run.reconcile_metrics({'rmse': np.nextafter(1.0, 2.0)}, {'rmse': 1.0})

  def test_public_input_receipts_are_exact(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    self.assertEqual(len(io.public_inputs()['fit-cv-results']['jobs']), 32)

  def test_incomplete_context_fails_before_array_read(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    receipt = {'arrays': {k: {'shape': [1], 'order': 'C', 'storage_format': 'NPY_GZIP_V1', 'dtype': '<i8'} for k in (*run.CONTEXT, *run.PATH_FIELDS)}}
    for key in (*run.CONTEXT, *run.PATH_FIELDS):
      partial = {'arrays': {k: v for k, v in receipt['arrays'].items() if k != key}}
      with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'INPUT_INSUFFICIENT'):
        run.population_schema(partial, run.PATH_FIELDS, 1, horizon=25)

  def test_compressed_receipt_mutations_all_fail(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      path, receipt = compressed_fixture(Path(tmp), np.arange(4, dtype=np.int64))
      for key, bad in [
        ('file_sha256', '0' * 64),
        ('array_sha256', '0' * 64),
        ('npy_sha256', '0' * 64),
        ('dtype', '<f8'),
        ('shape', [3]),
        ('order', 'F'),
        ('storage_format', 'NPY'),
        ('lossless_roundtrip_verified', False),
      ]:
        with self.subTest(key=key), self.assertRaises(ValueError):
          list(io.array_chunks(path, {**receipt, key: bad}))

  def test_compressed_trailing_data_rejected_even_with_updated_file_hash(self):
    import gzip
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    with tempfile.TemporaryDirectory() as tmp:
      path, receipt = compressed_fixture(Path(tmp), np.arange(4, dtype=np.int64))
      path.write_bytes(path.read_bytes() + gzip.compress(b'extra', mtime=0))
      receipt['file_sha256'] = p.sha(path.read_bytes())
      with self.assertRaises(ValueError):
        list(io.array_chunks(path, receipt))

  def test_immutable_receipt_cannot_overwrite(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'receipt.json'
      io.write_json(path, p.seal({'count': 1}))
      before = path.read_bytes()
      with self.assertRaises(ValueError):
        io.write_json(path, p.seal({'count': 2}))
      self.assertEqual(path.read_bytes(), before)

  def test_resume_needs_no_source_decoder_or_analysis(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      root, saved = complete_resume_fixture(Path(tmp))
      with patch.object(io, 'load_array', io.forbidden), patch.object(io, 'array_chunks', io.forbidden), patch.object(a, 'one_step', io.forbidden):
        self.assertEqual(io.resume(root), saved)
      (root / 'summary.json').write_text('{}')
      with self.assertRaises(ValueError):
        io.resume(root)

  def test_minimal_resealed_manifest_cannot_claim_complete_resume(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      io.write_json(root / 'manifest.json', p.seal({'source_manifest_sha256': io.SOURCE_SHA, 'files': {}}))
      with self.assertRaisesRegex(ValueError, 'RESUME_CONFLICT'):
        io.resume(root)

  def test_stale_executor_rejected_on_resume_without_source_access(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    with tempfile.TemporaryDirectory() as tmp:
      root, _ = complete_resume_fixture(Path(tmp))
      with patch.object(run, 'source_code', return_value={'changed': '0' * 64}), self.assertRaisesRegex(ValueError, 'RESUME_CONFLICT'):
        io.resume(root)

  def test_legacy_normalizer_and_reconstruction_are_trapped(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as old
    from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as reconstruction

    with io.firewall():
      for call in (old.normalizer, old.recursive, reconstruction.one_step, reconstruction.recursive_path, reconstruction.rollout):
        with self.subTest(call=call), self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          call()

  def test_repeatability_cannot_bypass_d_output_boundary(self):
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run

    with self.assertRaisesRegex(ValueError, 'D_ONLY_EXTERNAL_OUTPUT'):
      run.repeatability(Path('/mnt/c/forbidden'), Path('/mnt/d/source'))

  def test_c_output_and_source_overlap_rejected(self):
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    source = Path('/mnt/d/synthetic-source')
    for target in [Path('/mnt/c/results'), source, source / 'output', source.parent]:
      with self.subTest(target=target), self.assertRaises(ValueError):
        io.output_root(target, source)


def complete_resume_fixture(output):
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p

  root = output / 'repeat-1'
  pol = run.policy()
  io.write_json(output / 'policy.json', pol)
  auth = p.seal(
    {
      'policy_sha256': pol['receipt_sha256'],
      'executor_sources': run.source_code(),
      'source_identity': {'source_manifest_sha256': io.SOURCE_SHA},
      'output_identity_sha256': p.sha(str(output).encode()),
    }
  )
  io.write_json(output / 'authorization.json', auth)
  actual = np.array([0, 0, 1, -2], dtype=np.int64)
  current = np.zeros(4, dtype=np.int64)
  delta = np.array([0.0, 1.0, 0.0, -2.0])
  one = a.one_step(
    {
      'actual_delta_tick': actual,
      'current_tick': current,
      'target_next_tick': actual,
      'predicted_gate': np.array([0, 1, 0, 1], bool),
      'projected_next_tick': delta.astype(np.int64),
      'integrated_delta': delta,
      'candidate_error': delta - actual,
      'comparator_error': -actual.astype(float),
      'true_move': actual != 0,
      'hold_last_next_tick': current,
      'stage2_oracle_move_prediction': np.array([1.0, -2.0]),
    }
  )
  one['oracle'].update(
    historical_grid_metrics={'exact_hit': 1.0, 'within_one_tick': 1.0}, grid_provenance='PINNED_ORIGINAL_JOB_AGGREGATE_NO_PROJECTION_EXECUTION'
  )
  one['transfer'] = {**a.transfer(one['confusion'], one['confusion']), 'threshold_receipt_sha256': 'a' * 64}
  one['historical_metric_reconciliation'] = 'EXACT'
  rollout = {}
  for h in io.HORIZONS:
    observed = np.zeros((2, h + 1), dtype=np.int64)
    projected = observed.copy()
    observed[1, 1:] = 1
    projected[1, 1:] = 2
    gates = np.zeros((2, h), dtype=bool)
    gates[1, 0] = True
    rollout[str(h)] = {
      **a.rollout(a.path_rows(observed, projected, gates), np.array([0.0, 1.0]), np.array([0.0, -1.0])),
      'historical_metric_reconciliation': 'EXACT',
    }
  names, jobs = [], []
  for index, (c, f) in enumerate(io.JOBS):
    name = f'jobs/{c}/{f}/receipt.json'
    failures = [k for k, v in run.EXPECTED_FAILURES.items() if index < v]
    job = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_FAILURE_ATTRIBUTION_JOB_V1',
        'candidate_id': c,
        'fold': f,
        'authorization_sha256': auth['receipt_sha256'],
        'original_job_receipt_sha256': 'b' * 64,
        'population_receipts': dict.fromkeys(('train', 'one-step', 'rollout-25', 'rollout-50', 'rollout-100', 'rollout-200'), 'a' * 64),
        'one_step': one,
        'rollout': rollout,
        'historical_gate': {
          'pass': False,
          'failures': failures,
          'clauses': [{'id': k, 'pass': k not in failures, 'evaluated': True} for k in run.EXPECTED_FAILURES],
        },
      }
    )
    io.write_json(root / name, job)
    jobs.append(job)
    names.append(name)
  summary = run.summarize(jobs)
  readiness = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_READINESS_V1',
      'status': run.SUCCESS,
      'job_count': 32,
      'one_step_populations': 32,
      'rollout_populations': 128,
      'states': [
        'READ_ONLY_ATTRIBUTION_COMPLETE',
        'NO_NEW_MODEL_FIT',
        'NO_THRESHOLD_RESELECTION',
        'NO_MODEL_REPLAY',
        'NO_MODEL_SELECTION',
        'NO_POLICY_CHANGE',
        'HURDLE_NO_ADMISSIBLE_CANDIDATE_PRESERVED',
      ],
      'source_manifest_sha256': io.SOURCE_SHA,
      'holdout': 'CLOSED',
      'opening_count': 0,
      'vehicle_authority': 'NONE',
      'summary_sha256': summary['receipt_sha256'],
      'execution_calls': run.ZERO_CALLS,
      'source_manifest_listed_bytes_unchanged': True,
      'source_write_count': 0,
      'source_fallback': False,
    }
  )
  io.write_json(root / 'summary.json', summary)
  io.write_json(root / 'readiness.json', readiness)
  manifest = io.finish(
    root,
    names + ['summary.json', 'readiness.json'],
    {
      'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_MANIFEST_V1',
      'status': run.SUCCESS,
      'source_manifest_sha256': io.SOURCE_SHA,
      'job_order': [list(j) for j in io.JOBS],
      'authorization_sha256': auth['receipt_sha256'],
      'policy_sha256': pol['receipt_sha256'],
      'summary_sha256': summary['receipt_sha256'],
      'readiness_sha256': readiness['receipt_sha256'],
    },
  )
  io.write_json(
    output / 'repeatability.json',
    p.seal(
      {
        'status': 'PASS',
        'manifest_sha256': manifest['receipt_sha256'],
        'trapped_resume_exact': True,
        'all_file_hashes_exact': True,
        'receipts_exact': True,
        'independent_runs': 2,
      }
    ),
  )
  return root, manifest


class TestPublication(unittest.TestCase):
  def test_private_threshold_and_row_fields_blocked_recursively(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    for field in pub.FORBIDDEN:
      with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'PRIVATE_FIELD'):
        pub.validate_public({'jobs': [{'candidate': {field: 0.31}}]})

  def test_private_paths_blocked(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    for path in ['/mnt/d/private', '/'.join(('', 'home', 'synthetic-user', 'fixture')), 'C:/private', 'D:/private']:
      with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'PRIVATE_PATH'):
        pub.validate_public({'command': path})

  def test_aggregate_counts_and_threshold_receipt_are_publishable(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    pub.validate_public({'threshold_receipt_sha256': 'a' * 64, 'train': {'counts': {'TP': 23, 'FP': 7}}, 'rmse': 2.4})

  def test_nan_cannot_be_published(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaises(ValueError):
      pub.validate_public({'rmse': float('nan')})


class TestInputAdmission(unittest.TestCase):
  def test_wrong_exact_manifest_fails_before_numeric_or_source_fallback(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      io.write_json(root / 'repeat-1/manifest.json', p.seal({'job_count': 32}))
      with patch.object(io, 'array_chunks', io.forbidden), io.firewall(), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
        io.admit(root)

  def test_modified_public_pin_rejected(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with patch.dict(io.PUBLIC_PINS, {'fit-cv-readiness': '0' * 64}), self.assertRaises(ValueError):
      io.public_inputs()

  def test_gate_history_mismatch_cannot_be_reinterpreted(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    jobs = [{'candidate_id': c, 'fold': f, 'historical_gate': {'failures': []}} for c, f in io.JOBS]
    with self.assertRaisesRegex(ValueError, 'HISTORICAL_RECONCILIATION_FAILURE'):
      run.summarize(jobs)

  def test_job_order_cannot_skip_or_rank_candidates(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as run
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    jobs = [{'candidate_id': c, 'fold': f} for c, f in io.JOBS]
    for broken in [jobs[:-1], jobs + [jobs[0]], list(reversed(jobs))]:
      with self.subTest(length=len(broken)), self.assertRaisesRegex(ValueError, 'JOB_SET_CONFLICT'):
        run.summarize(broken)


class TestReviewRegressions(unittest.TestCase):
  def test_embedded_private_path_in_validation_command_is_blocked(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'PRIVATE_PATH'):
      pub.validate_public({'checks': {'focused': {'command': 'python /mnt/d/private/script.py'}}})

  def test_candidate_error_rows_cannot_be_published(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'PRIVATE_FIELD'):
      pub.validate_public({'candidate_error': [1.25, 2.5]})

  def test_arbitrary_new_key_cannot_smuggle_private_values(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      pub.validate_public({'unknown_row_data': [1.25, 2.5]})

  def test_numeric_row_list_under_metric_key_is_blocked(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'ROW_VALUES'):
      pub.validate_public({'rmse': [1.25, 2.5]})

  def test_complete_synthetic_publication_is_aggregate_only(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with tempfile.TemporaryDirectory() as tmp:
      root, _ = complete_resume_fixture(Path(tmp))
      result = pub.bundle(root.parent, {'checks': {}, 'counts': {}, 'independent_review': {}, 'browser': 'NOT_APPLICABLE', 'storage': {}, 'limitations': []})
      self.assertEqual(len(result), 14)
      self.assertEqual(result['failure-attribution-readiness']['opening_count'], 0)

  def test_resealed_job_stub_with_matching_file_hash_is_not_complete(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      root, manifest = complete_resume_fixture(Path(tmp))
      name = 'jobs/HRI_D00_L01/FOLD_A/receipt.json'
      job = io.read_json(root / name)
      del job['one_step']
      job.pop('receipt_sha256')
      (root / name).write_bytes(p.canonical(p.seal(job)))
      manifest['files'][name] = io.digest(root / name)
      manifest.pop('receipt_sha256')
      (root / 'manifest.json').write_bytes(p.canonical(p.seal(manifest)))
      with self.assertRaisesRegex(ValueError, 'AGGREGATE_INCOMPLETE'):
        io.resume(root)

  def test_missing_rollout_horizon_rejected_even_if_receipt_resealed(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_schema as schema
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

    with tempfile.TemporaryDirectory() as tmp:
      root, _ = complete_resume_fixture(Path(tmp))
      job = io.read_json(root / 'jobs/HRI_D00_L01/FOLD_A/receipt.json')
      del job['rollout']['200']
      with self.assertRaisesRegex(ValueError, 'AGGREGATE_INCOMPLETE'):
        schema.job(job)


class TestPublicationNativeTypes(unittest.TestCase):
  def test_tuple_cannot_bypass_row_value_guard(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'NON_JSON_TYPE'):
      pub.validate_public({'rmse': (1.25, 2.5)})

  def test_nested_tuple_cannot_hide_private_field(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_publication as pub

    with self.assertRaisesRegex(ValueError, 'NON_JSON_TYPE'):
      pub.validate_public({'checks': ({'candidate_error': [1.25, 2.5]},)})


class TestNestedCompleteness(unittest.TestCase):
  def test_every_required_nested_job_leaf_is_required(self):
    import copy
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_schema as schema

    with tempfile.TemporaryDirectory() as tmp:
      root, _ = complete_resume_fixture(Path(tmp))
      job = io.read_json(root / 'jobs/HRI_D00_L01/FOLD_A/receipt.json')
      paths = [
        'one_step.oracle.tp_fn_accounting.candidate.sae.original_anchor_order',
        'one_step.accounting.hold_last.sse.contribution_bytes_exact',
        'one_step.transfer.dev_minus_train.recall',
        'one_step.transfer.train.fractions.TP',
        'one_step.fn.metrics.p95',
        'one_step.fn.actual_delta_magnitude.max',
        'one_step.classes.TP.continuous_sign_accuracy',
        'one_step.oracle.integrated.sse',
        'one_step.oracle.historical_grid_metrics.exact_hit',
        'population_receipts.train',
        'rollout.25.first_gate_mismatch.event_step_summary.count',
        'rollout.25.count_distributions.gate_fp_count.max',
      ]
      for path in paths:
        broken = copy.deepcopy(job)
        parent = broken
        keys = path.split('.')
        for key in keys[:-1]:
          parent = parent[key]
        del parent[keys[-1]]
        with self.subTest(path=path), self.assertRaises((ValueError, KeyError)):
          schema.job(broken)

  def test_required_summary_and_readiness_leaves(self):
    import copy
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
    from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_schema as schema

    with tempfile.TemporaryDirectory() as tmp:
      root, _ = complete_resume_fixture(Path(tmp))
      summary = io.read_json(root / 'summary.json')
      ready = io.read_json(root / 'readiness.json')
      for path in [
        'one_step.job_counts.projected_false_move',
        'one_step.implementation_authorized',
        'folds.FOLD_A.ranges.false_move_rate.min',
        'rollout.25.candidate_sse_greater_hold_jobs',
        'rollout.25.gate_mismatch_relations.neither',
      ]:
        broken = copy.deepcopy(summary)
        parent = broken
        keys = path.split('.')
        for key in keys[:-1]:
          parent = parent[key]
        del parent[keys[-1]]
        with self.subTest(path=path), self.assertRaises((ValueError, KeyError)):
          schema.summary(broken)
      for key in ('states', 'source_manifest_sha256', 'source_fallback', 'holdout', 'opening_count', 'vehicle_authority'):
        broken = copy.deepcopy(ready)
        del broken[key]
        with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
          schema.readiness(broken, summary)
