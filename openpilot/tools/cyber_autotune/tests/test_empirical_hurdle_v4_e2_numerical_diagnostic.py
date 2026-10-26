"""Only synthetic numerical differential and authority contracts."""
import inspect
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic as d


class TestNumericalDiagnostic(unittest.TestCase):
  def test_fixture_grid_is_predeclared(self):
    self.assertEqual(d.LENGTHS, (1, 5, 15, 45))
    self.assertEqual(len(d.MASKS) * len(d.SCALES) * len(d.LENGTHS), 60)
    self.assertEqual((d.ROWS, d.CHUNK, d.SEED), (1537, 512, 20261018))

  def test_fixture_deterministic_each_dimension_mask_scale(self):
    for length in d.LENGTHS:
      for mask in d.MASKS:
        a, gate, model = d.fixture(length, 1.0, mask)
        b, again, other = d.fixture(length, 1.0, mask)
        self.assertTrue(d.byte_equal(a, b))
        self.assertTrue(d.byte_equal(gate, again))
        self.assertTrue(d.byte_equal(model['coefficients'], other['coefficients']))
        self.assertEqual(a.shape, (1537, 2 * length + 3))
        self.assertTrue(a.flags.c_contiguous)
        np.testing.assert_array_equal(a[8], a[9])

  def test_ulp_one_is_byte_failure(self):
    a = np.array([1.0])
    result = d.compare(a, np.nextafter(a, np.inf), np.zeros(1, np.int64))
    self.assertEqual(result['max_ULP_distance'], 1)
    self.assertEqual(result['byte_qualification'], 'FAIL')
    self.assertEqual(result['projected_tick_mismatch_count'], 0)

  def test_signed_zero_is_not_byte_equality(self):
    result = d.compare(np.array([-0.0]), np.array([0.0]), np.zeros(1, np.int64))
    self.assertTrue(result['exact_float_equal'])
    self.assertFalse(result['raw_byte_equal'])
    self.assertEqual(result['signed_zero_difference_count'], 1)

  def test_negative_ulp_order(self):
    a = np.array([-1.0])
    self.assertEqual(d.compare(a, np.nextafter(a, -np.inf), np.zeros(1, np.int64))['max_ULP_distance'], 1)

  def test_projection_boundary_can_change_tick(self):
    a = np.array([0.5, 1.5, -0.5, -1.5])
    b = np.nextafter(a, np.inf)
    row = d.compare(a, b, np.zeros(4, np.int64))
    self.assertEqual(row['projected_tick_mismatch_count'], 2)
    np.testing.assert_array_equal(d.frozen.project(a), [0, 2, 0, -2])

  def test_projection_overflow_stays_fail_closed(self):
    with self.assertRaises(ValueError):
      d.compare(np.array([32768.0]), np.array([32768.0]), np.zeros(1, np.int64))

  def test_nonfinite_and_dtype_rejected(self):
    for value in (float('nan'), float('inf')):
      with self.assertRaises(ValueError):
        d.compare(np.array([value]), np.array([0.0]), np.zeros(1, np.int64))
    with self.assertRaises(ValueError):
      d.compare(np.array([0.0], np.float32), np.array([0.0]), np.zeros(1, np.int64))

  def test_three_paths_and_order(self):
    x, gate, model = d.fixture(1, 1.0, 'alternating')
    row = d.diagnose([x[:701].copy(), x[701:].copy()], gate, model, current=np.zeros(len(x), np.int64))
    self.assertTrue(row['transformed_rows_byte_equal'])
    self.assertEqual(row['calls']['all_chunk'], 4)
    self.assertEqual(row['calls']['whole_subset'], 1)
    self.assertEqual(set(row['comparisons']), {'B_vs_A', 'C_vs_A', 'B_vs_C', 'whole_all_vs_A'})

  def test_batch_sensitive_output_detected_without_repair(self):
    x, gate, model = d.fixture(1, 1.0, 'medium')
    original = d.frozen.predict_delta
    def changed(x, model):
      result = original(x, model)
      return np.nextafter(result, np.inf) if len(x) < 512 else result
    with patch.object(d.frozen, 'predict_delta', changed):
      row = d.diagnose([x], gate, model, current=np.zeros(len(x), np.int64))
    self.assertTrue(row['transformed_rows_byte_equal'])
    self.assertEqual(row['classification'], 'BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE')
    self.assertEqual(row['comparisons']['B_vs_A']['byte_qualification'], 'FAIL')

  def test_transform_change_is_separate_case(self):
    x, gate, model = d.fixture(1, 1.0, 'medium')
    original = d.frozen.transform
    def changed(x, norm):
      z = original(x, norm)
      if len(x) < 512:
        z[:, 1] = np.nextafter(z[:, 1], np.inf)
      return z
    with patch.object(d.frozen, 'transform', changed):
      row = d.diagnose([x], gate, model, current=np.zeros(len(x), np.int64))
    self.assertFalse(row['transformed_rows_byte_equal'])
    self.assertEqual(row['classification'], 'TRANSFORMED_ROW_CONFLICT')

  def test_empty_gate_and_wrong_count_blocked(self):
    x, gate, model = d.fixture(1, 1.0, 'medium')
    for wrong in (np.zeros(len(x), bool), gate[:-1]):
      with self.assertRaises(ValueError):
        d.diagnose([x], wrong, model, current=np.zeros(len(wrong), np.int64))

  def test_no_inputs_or_policy_execution_in_synthetic_entry(self):
    source = inspect.getsource(d)
    for forbidden in ('open(', 'glob(', 'listdir(', 'select_context(', 'select_job(', 'threshold(', 'rollout(', 'np.load(', 'np.save('):
      self.assertNotIn(forbidden, source)
    self.assertNotIn('allclose', source)
    self.assertNotIn('isclose', source)

  def test_no_private_values_in_differential_output(self):
    x, gate, model = d.fixture(1, 1.0, 'low')
    row = d.diagnose([x], gate, model, current=np.zeros(len(x), np.int64))
    for field in ('row_indices', 'coefficients', 'scores', 'ticks', 'decision', 'paths', 'predictions'):
      self.assertNotIn(field, row)


class TestDiagnosticAuthority(unittest.TestCase):
  def test_only_named_job_and_stage2_fields(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    phase = p.Phase()
    prefix = 'candidates/HRI_D00_L01/FOLD_B/'
    for owner, tail in [('V4', 'train/combined_probability.npy.gz'), ('V1', 'train/move_label.npy.gz'),
                        ('V1', 'stage2/model/coefficients.npy.gz')]:
      phase.authorize(owner, prefix + tail, 'array')
    for owner, tail in [('V4', 'train/receipt.json'), ('V4', 'train/STATIC_coefficients.npy.gz'),
                        ('V4', 'one-step/p_move.npy.gz'), ('V1', 'stage1/normalizer/mean.npy.gz')]:
      with self.assertRaises(ValueError):
        phase.authorize(owner, prefix + tail, 'array')
    with self.assertRaises(ValueError):
      phase.authorize('V4', prefix.replace('FOLD_B', 'FOLD_A') + 'train/combined_probability.npy.gz', 'array')
    with self.assertRaises(ValueError):
      phase.require_dev()

  def test_source_requires_exact_member_admission(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    phase = p.Phase()
    member = 'repeat-1/segments/' + 'a' * 64 + '/angle_tick.npy'
    with self.assertRaises(ValueError):
      phase.authorize('DERIVED', member, 'array')
    phase.source_members.add(('DERIVED', member, 'array'))
    phase.authorize('DERIVED', member, 'array')
    with self.assertRaises(ValueError):
      phase.authorize('DERIVED', member.replace('a' * 64, 'b' * 64), 'array')

  def test_no_discovery_or_execution_resume_in_adapter(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    source = inspect.getsource(p)
    for bad in ('glob(', 'rglob(', 'listdir(', 'scandir(', 'control.run(', 'control.preflight(', 'select_context(', 'select_job(', 'np.load('):
      self.assertNotIn(bad, source)
    self.assertIn("('select_context', 'select_job', 'potentials')", source)
    self.assertIn("'DEV_reads': 0", source)
    self.assertIn("'D2_decisions': 0", source)
    self.assertNotIn('d0[', source[source.index('payload = control.sealed'):])

  def test_old_grant_does_not_pass_new_gate(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    with self.assertRaises(ValueError):
      p.verify_gate({'mission': 'STAGE1_V4_E2_D0_D1_D2_OFFLINE_EVALUATION'}, {}, b'{}', {}, 'head')


class TestReviewRegression(unittest.TestCase):
  def test_auxiliary_difference_is_not_actual_failure(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    base = {'transformed_rows_byte_equal': True, 'target_failure_reproduced': False}
    self.assertEqual(p.diagnostic_status(base), 'E2_NUMERICAL_ROOT_CAUSE_UNRESOLVED')
    self.assertEqual(p.diagnostic_status({**base, 'target_failure_reproduced': True}), 'E2_NUMERICAL_ROOT_CAUSE_IDENTIFIED')
    self.assertEqual(p.diagnostic_status({**base, 'transformed_rows_byte_equal': False}), 'E2_NUMERICAL_INPUT_CONFLICT')

  def test_abort_cause_not_collapsed_to_authority(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    self.assertEqual(p.abort_status(MemoryError())[1], 'DIAGNOSTIC_RESOURCE_FAILURE')
    self.assertEqual(p.abort_status(ValueError('DIAGNOSTIC_RECORDED_ORDER_CONFLICT'))[0], 'E2_NUMERICAL_INPUT_CONFLICT')
    self.assertEqual(p.abort_status(ValueError('HURDLE_NUMERICAL_FAILURE_OVERFLOW'))[1], 'DIAGNOSTIC_NUMERICAL_FAILURE')

  def test_preflight_error_cannot_print_private_path(self):
    from contextlib import redirect_stdout, redirect_stderr
    import io
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    out, err = io.StringIO(), io.StringIO()
    with patch('sys.argv', ['diag', '--work', '/synthetic/output', '--prior-work', '/synthetic/prior']), \
         patch.object(p, 'run', side_effect=FileNotFoundError('/sensitive-sentinel/private')), \
         redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit):
      p.main()
    self.assertNotIn('sensitive-sentinel', out.getvalue() + err.getvalue())
    self.assertIn('FileNotFoundError', out.getvalue())

  def test_public_pins_precede_private_controls(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    s = inspect.getsource(p.run)
    self.assertLess(s.index('verify_public_pins(old)'), s.index('control.controls('))
    self.assertLess(s.index("old['source_policy_receipt_sha256']"), s.index('control.controls('))

  def test_same_alignment_copy_is_byte_exact(self):
    a = np.arange(55, dtype=np.float64).reshape(11, 5)
    b = d.aligned_copy(a)
    self.assertTrue(d.byte_equal(a, b))
    self.assertEqual(b.ctypes.data % 64, 0)


class TestDiagnosticAdapter(unittest.TestCase):
  def gate_fixture(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    pin = {'source.py': 'a' * 64}
    protocol = {'diagnostic_source_sha256': pin}
    raw = b'synthetic-protocol'
    reviews = {}
    for name, role in [('science-review.json', 'SCIENTIFIC_NUMERICAL_CAUSAL'),
                       ('authority-review.json', 'AUTHORITY_PRIVACY_SOURCE_INTEGRITY')]:
      reviews[name] = p.control.sealed({'role': role, 'reviewer': name, 'approval': 'APPROVED',
          'protocol_raw_sha256': p.control.sha(raw), 'source_sha256': pin})
    gate = {'mission': p.MISSION, 'head': 'head', 'protocol_raw_sha256': p.control.sha(raw),
        'ci': {'head_sha': 'head', 'status': 'completed', 'conclusion': 'success'},
        'review_receipts': {k: v['receipt_sha256'] for k, v in reviews.items()},
        'job': list(p.JOB), 'diagnostic_runs': 1, 'DEV_authorized': False, 'D2_selection_authorized': False}
    return gate, reviews, raw, protocol

  def test_positive_gate_and_negative_ci_review_scope(self):
    import copy
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    gate, reviews, raw, protocol = self.gate_fixture()
    p.verify_gate(gate, reviews, raw, protocol, 'head')
    for mutation in ('ci', 'review', 'DEV', 'job'):
      g, r = copy.deepcopy(gate), copy.deepcopy(reviews)
      if mutation == 'ci':
        g['ci']['conclusion'] = 'cancelled'
      if mutation == 'review':
        r['science-review.json']['approval'] = 'REQUEST_CHANGES'
      if mutation == 'DEV':
        g['DEV_authorized'] = True
      if mutation == 'job':
        g['job'][1] = 'FOLD_A'
      with self.subTest(mutation=mutation), self.assertRaises(ValueError):
        p.verify_gate(g, r, raw, protocol, 'head')

  def test_exclusive_one_shot_binding(self):
    from pathlib import Path
    import tempfile
    import os
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    with tempfile.TemporaryDirectory() as name:
      os.chmod(name, 0o700)
      folder = Path(name)
      row = p.control.sealed({'synthetic': True})
      p.control.persist(folder, 'execution-binding.json', row, 4096)
      with self.assertRaises(FileExistsError):
        p.control.persist(folder, 'execution-binding.json', row, 4096)
      self.assertEqual(p.control.checked(p.control.private(folder / 'execution-binding.json')), row)

  def test_abort_retains_sealed_binding_and_ledger_without_reread(self):
    from types import SimpleNamespace
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    binding = p.control.sealed({'head': 'h', 'protocol_raw_sha256': 'p'})
    reader = SimpleNamespace(events=[{'synthetic': True}], summary=lambda: {'files': 1})
    row = p.abort_payload(binding, reader, {'diagnostic_calls': 1}, 0, MemoryError())
    self.assertEqual(row['binding_receipt_sha256'], binding['receipt_sha256'])
    self.assertEqual(row['input_events'], reader.events)
    self.assertEqual(p.control.checked(p.control.canonical(row)), row)

  def test_provider_reads_only_named_train_route(self):
    from types import SimpleNamespace
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as e1
    route, other, identity = 'a' * 64, 'b' * 64, 'c' * 64
    others = [f'{i:064x}' for i in range(153)]
    all_ids = [identity, *others]
    phase = p.Phase()
    seen = []
    source = {'route_id': route, 'segment_sha256': identity, 'receipt_sha256': 'source',
              'arrays': {'state.speed_mps': {'shape': [4]}, 'command.normalized': {'shape': [4]}}}
    derived = {'source_receipt_sha256': 'source', 'policy_sha256': 'policy',
               'arrays': {name: {'shape': [4]} for name in e1.DERIVED_FIELDS}}
    def metadata(owner, member, **_kwargs):
      phase.authorize(owner, member, 'metadata')
      seen.append((owner, member))
      if member == 'repeat-1/manifest.json':
        return {'receipt_sha256': 'manifest'}
      if member == 'authorization.json':
        return {'segments': {route: [identity], other: others}}
      if member == 'repeat-1/derived-index.json':
        return {'segments': [{'content_sha256': i, 'receipt_sha256': 'derived'} for i in all_ids]}
      if member == 'repeat-1/results.json':
        return {'admission_sha256': 'admission'}
      if member == 'repeat-1/admission.json':
        return {'manifest_sha256': 'manifest'}
      if owner == 'CAUSAL' and identity in member:
        return source
      if owner == 'DERIVED' and identity in member:
        return derived
      raise AssertionError('UNAPPROVED_ROUTE_READ')
    def array(owner, member, _desc, *, shape, dtype, **_kwargs):
      phase.authorize(owner, member, 'array')
      seen.append((owner, member))
      self.assertIn(identity, member)
      return np.ones(shape, dtype=dtype)
    modules = {'empirical_hurdle_v4_e2_inputs': inp, 'empirical_hurdle_v4_e_inputs': e1}
    cls = p.provider_type(modules)
    provider = cls.__new__(cls)
    provider.reader = SimpleNamespace(phase=phase, metadata=metadata, array=array)
    provider.v4_auth = {'source_manifests': dict.fromkeys(('causal', 'derived_index', 'derived_result'), 'synthetic')}
    provider.source_policy = {'route_ids': [route, other], 'excluded_qlog_content_sha256': [], 'receipt_sha256': 'policy'}
    provider.references = [{}, {'train_route': route}]
    provider.segments = None
    provider.admit_train_sources()
    self.assertEqual(len(provider.segments), 1)
    self.assertEqual(sum(member.endswith('.npy') for _, member in seen), 8)
    self.assertFalse(any(other in member for _, member in seen))


class TestPublicInputDrift(unittest.TestCase):
  def test_mutated_public_input_stops_before_private_access(self):
    from pathlib import Path
    import tempfile
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic_private as p
    with tempfile.TemporaryDirectory() as name:
      path = Path(name) / 'public.json'
      raw = p.control.canonical(p.control.sealed({'synthetic': True}))
      path.write_bytes(raw)
      old = {'public_inputs': {'public.json': {'raw_sha256': p.control.sha(raw),
              'receipt_sha256': p.control.checked(raw)['receipt_sha256']}}}
      with patch.object(p.control, 'PUBLIC', Path(name)), patch.object(p.control, 'private', side_effect=AssertionError('NO_PRIVATE_READ')):
        p.verify_public_pins(old)
        path.write_bytes(raw + b' ')
        with self.assertRaisesRegex(ValueError, 'PUBLIC_INPUT_DRIFT'):
          p.verify_public_pins(old)
