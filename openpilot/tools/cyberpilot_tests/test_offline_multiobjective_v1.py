"""F7 diagnostics tests; standalone Unit discovery, no historical Native execution claim."""

import copy
import gzip
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

PLANT = {
  'command_gain_1pm': 0.004,
  'command_inv_speed_gain_per_s': 0.002,
  'command_limit': 1.0,
  'command_speed_gain_s_per_m2': 0.0002,
  'curvature_ar': 0.92,
  'curvature_intercept_1pm': 0.0,
  'delay_steps': 2,
  'dt_s': 0.01,
  'max_speed_mps': 30.0,
  'min_speed_mps': 2.5,
  'roll_gain_1pm_per_rad': 0.001,
  'yaw_ar': 0.75,
  'yaw_bias_rad_s': 0.0,
}


def engine():
  return importlib.import_module('tools.cyberpilot.offline_multiobjective_v1')


def gates():
  return importlib.import_module('tools.cyberpilot.offline_multiobjective_gates_v1')


def metrics():
  return importlib.import_module('tools.cyberpilot.offline_multiobjective_metrics_v1')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def reseal(rows):
  prior = '0' * 64
  for row in rows:
    row['previous_receipt_sha256'] = prior
    row['input_sha256'] = sha(canonical(row['input']))
    row['receipt_sha256'] = sha(canonical({k: v for k, v in row.items() if k != 'receipt_sha256'}))
    prior = row['receipt_sha256']


def fresh_native_state(reason='EXPERIMENT_START'):
  return {
    'jerk_filter_initialized': True,
    'jerk_filter_x': 0.0,
    'pending_events': [reason],
    'pid': [0.0] * 5,
    'prior_input': None,
    'reference_buffer': [0.0] * 100,
    'sat_time': 0.0,
  }


def fixture_rows(n=32):
  """Mathematical straight-line parser fixture, not a real controller transcript."""
  rows = []
  x = 0.0
  for i in range(n):
    before = [x, 0.0, 0.0]
    x += 0.075
    inp = {
      'sequence': i,
      'time_ns': i * 10000000,
      'speed_mps': 7.5,
      'actual_curvature_1pm': 0.0,
      'desired_curvature_1pm': 0.0,
      'roll_rad': 0.0,
      'active': True,
      'steering_pressed': False,
      'safety_limited': False,
      'curvature_limited': False,
    }
    ni = {k: v for k, v in inp.items() if k not in ('sequence', 'time_ns')}
    ni.update(dt_s=0.01, time_s=i * 0.01)
    ps = {'curvature_1pm': 0.0, 'yaw_rate_rad_s': 0.0, 'command_history': [0.0, 0.0]}
    rows.append(
      {
        'sequence': i,
        'input': inp,
        'native_input': ni,
        'native_request': 0.0,
        'raw_candidate': 0.0,
        'delivered': 0.0,
        'applied': 0.0,
        'actual_applied_before': 0.0,
        'plant_before': copy.deepcopy(ps),
        'plant_after': copy.deepcopy(ps),
        'native_state_before': fresh_native_state() if i == 0 else {**fresh_native_state(), 'pending_events': []},
        'native_state_after': {**fresh_native_state(), 'pending_events': []},
        'pose_before': before,
        'pose_after': [x, 0.0, 0.0],
        'reference_pose': [x, 0.0, 0.0],
        'curvature_error_1pm': 0.0,
        'heading_error_rad': 0.0,
        'reference_normal_deviation_m': 0.0,
        'reset_events': ['EXPERIMENT_START'] if i == 0 else [],
        'explicit_controller_reset': False,
        'policy_measured_yaw_rad_s': 0.0,
        'policy_sha256': 'b' * 64,
        'source_sha256': 'a' * 64,
        'candidate_state_after': None,
        'previous_candidate_before': None,
        'delivery_gate': 'ACTIVE',
        't_start_s': i * 0.01,
        't_end_s': (i + 1) * 0.01,
        'source_result': {'valid': True, 'live_actuator_authority': False},
        'curvature_times_speed2_mps2': 0.0,
        'yaw_times_speed_mps2': 0.0,
      }
    )
  reseal(rows)
  return rows


def item_for(rows):
  return {
    'arm': 'A0',
    'case_id': 'entry_step',
    'frames': len(rows),
    'plant': dict(PLANT),
    'source_sha256': 'a' * 64,
    'policy_sha256': 'b' * 64,
    'final_frame_receipt': rows[-1]['receipt_sha256'],
  }


class TestOfflineEvaluatorDiscovery(unittest.TestCase):
  def test_engine_is_available(self):
    self.assertIsNotNone(importlib.util.find_spec('tools.cyberpilot.offline_multiobjective_v1'))


class TestOfflineEvaluatorInput(unittest.TestCase):
  def test_duplicate_key(self):
    with self.assertRaises(gates().EvidenceError):
      engine().strict_json(b'{"x":1,"x":2}')

  def test_nonfinite_json(self):
    for text in (b'NaN', b'Infinity', b'-Infinity', b'1e400'):
      with self.subTest(text=text), self.assertRaises(gates().EvidenceError):
        engine().strict_json(text)

  def test_malformed_json(self):
    for raw in (b'{', b'\xff', b'{"x":}'):
      with self.subTest(raw=raw), self.assertRaises(gates().EvidenceError):
        engine().strict_json(raw)

  def test_bool_is_not_number(self):
    with self.assertRaises(gates().EvidenceError):
      gates().number(True)

  def test_signed_zero_preserved(self):
    self.assertTrue(np.signbit(engine().strict_json(b'-0.0')))

  def test_symlink_and_special_file_rejected(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      (root / 'file').write_bytes(b'{}')
      (root / 'link').symlink_to(root / 'file')
      with self.assertRaises(gates().EvidenceError):
        engine().read_regular(root / 'link')
      with self.assertRaises(gates().EvidenceError):
        engine().read_regular(root)

  def test_read_size_bound(self):
    with tempfile.TemporaryDirectory() as td:
      f = Path(td) / 'large'
      f.write_bytes(b'ab')
      with self.assertRaises(gates().EvidenceError):
        engine().read_regular(f, 1)

  def test_compressed_size_bound(self):
    with self.assertRaises(gates().EvidenceError):
      engine().decode_trace(gzip.compress(b' ' * 100), limit=20)

  def test_malformed_gzip(self):
    with self.assertRaises(gates().EvidenceError):
      engine().decode_trace(b'not gzip')

  def test_pinned_contract(self):
    c = engine().load_contract()
    self.assertEqual(len(c['metrics']), 28)
    self.assertEqual(len(c['hard_gates']), 10)
    self.assertIs(c['effective'], False)
    self.assertTrue(all(m['acceptance_threshold'] is None for m in c['metrics']))

  def test_contract_has_no_runtime_permissions(self):
    c = engine().load_contract()
    self.assertIsNone(c['selected_candidate'])
    self.assertIsNone(c['selected_policy'])
    self.assertFalse(c['promotion_enabled'])


class TestOfflineFrameGates(unittest.TestCase):
  def test_valid_mathematical_fixture(self):
    r = fixture_rows()
    self.assertEqual(len(gates().verify_frames(r, item_for(r))), 32)

  def test_resealed_frame_mutations(self):
    # Recomputing the receipts must not bypass source-derived arithmetic/event checks.
    mutations = {
      'sequence': lambda r: r[4].update(sequence=3),
      'input_sequence_bool': lambda r: r[0]['input'].update(sequence=False),
      'timestamp': lambda r: r[4]['input'].update(time_ns=30000000),
      'missing': lambda r: r.pop(4),
      'duplicate': lambda r: r.insert(4, copy.deepcopy(r[4])),
      'speed_domain': lambda r: r[4]['input'].update(speed_mps=31.0),
      'command_range': lambda r: r[4].update(native_request=1.1),
      'bool_command': lambda r: r[4].update(native_request=True),
      'feedback': lambda r: r[4]['input'].update(actual_curvature_1pm=0.01),
      'native_feedback': lambda r: r[4]['native_input'].update(actual_curvature_1pm=0.01),
      'queue': lambda r: r[4]['plant_after']['command_history'].__setitem__(0, 0.1),
      'curvature': lambda r: r[4]['plant_after'].update(curvature_1pm=0.01),
      'yaw': lambda r: r[4]['plant_after'].update(yaw_rate_rad_s=0.01),
      'pose': lambda r: r[4]['pose_after'].__setitem__(1, 0.1),
      'heading': lambda r: r[4]['pose_after'].__setitem__(2, 0.1),
      'metric': lambda r: r[4].update(reference_normal_deviation_m=0.1),
      'source': lambda r: r[4].update(source_sha256='c' * 64),
      'policy': lambda r: r[4].update(policy_sha256='c' * 64),
      'invented_reset': lambda r: r[4].update(reset_events=['EXPERIMENT_START']),
      'invented_explicit_reset': lambda r: r[4].update(explicit_controller_reset=True),
      'truthy_explicit_reset': lambda r: r[4].update(explicit_controller_reset=1),
      'bool_active': lambda r: r[4]['input'].update(active=1),
      'unexpected_key': lambda r: r[4].update(private_value='never echo'),
    }
    for label, mutate in mutations.items():
      with self.subTest(label=label):
        r = fixture_rows()
        item = item_for(r)
        mutate(r)
        reseal(r)
        item['final_frame_receipt'] = r[-1]['receipt_sha256']
        with self.assertRaises(gates().EvidenceError):
          gates().verify_frames(r, item)

  def test_rate_fall_before_reversal(self):
    self.assertEqual(gates().rate_step(-1.0, 0.01), 0.0)
    self.assertGreater(gates().rate_step(-1.0, 0.5), 0.0)

  def test_a2_static_gate_is_not_general_plant_gate(self):
    self.assertGreater(gates().required_static_command(0.025, 7.5, 0.0, PLANT), 0.25)
    self.assertLess(gates().required_static_command(0.025, 7.5, 0.0, PLANT), 1.0)


class TestOfflineMetrics(unittest.TestCase):
  def frames(self, n=20):
    return gates().verify_frames(fixture_rows(n), item_for(fixture_rows(n)))

  def test_exact_28_slots(self):
    out = metrics().calculate(self.frames(), PLANT, 'A0', engine().load_contract()['metrics'])
    self.assertEqual(list(out), [m['name'] for m in engine().load_contract()['metrics']])
    self.assertEqual(len(out), 28)
    self.assertEqual(out['normal_position']['value']['rms'], 0.0)
    self.assertEqual(out['euclidean_position']['value']['rms'], 0.0)
    self.assertEqual(out['settling_time']['status'], 'METRIC_UNAVAILABLE')
    self.assertEqual(out['settling_time']['reason'], 'THRESHOLD_APPROVAL_REQUIRED')
    self.assertTrue(all(m['threshold_status'] == 'THRESHOLD_APPROVAL_REQUIRED' for m in out.values()))

  def test_signed_cancellation_does_not_reduce_rms(self):
    a = metrics().area(np.array([1.0, -1.0] * 10), 0.01)
    self.assertEqual(a['net'], 0.0)
    self.assertEqual(a['absolute'], 0.2)
    self.assertEqual(a['cancellation_fraction'], 1.0)
    self.assertEqual(metrics().rms(np.array([1.0, -1.0] * 10)), 1.0)

  def test_events_are_not_frames(self):
    x = metrics().saturation(np.array([0.0, 1.0, 1.0, -1.0, -1.0, 0.0, 1.0]), 0.01)
    self.assertEqual(x['events'], 3)
    self.assertEqual(x['frames'], 5)
    self.assertEqual(x['occupancy'], 5 / 7)

  def test_zero_bridge_direction_reversals(self):
    self.assertEqual(metrics().reversals(np.array([1.0, 0.0, -1.0, 0.0, 1.0])), 2)

  def test_spectrum_even_and_odd_parseval(self):
    for n in (1000, 1001):
      x = 0.3 * np.sin(2 * np.pi * 3 * np.arange(n) / 100.0)
      s = metrics().spectrum(x, 0.01)
      self.assertAlmostEqual(sum(s['bin_power']), np.var(x), places=12)

  def test_known_sine_peak(self):
    s = metrics().spectrum(np.sin(2 * np.pi * 3 * np.arange(1000) / 100.0), 0.01)
    self.assertEqual(s['peak_hz'], 3.0)

  def test_position_definitions(self):
    actual = np.array([[1.0, 0.3, 0.0], [2.0, 0.3, 0.0]])
    reference = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    p = metrics().position_components(actual, reference)
    self.assertAlmostEqual(p['normal']['rms'], 0.3)
    self.assertAlmostEqual(p['euclidean']['rms'], np.hypot(1.0, 0.3))

  def test_polyline_distance(self):
    actual = np.array([[0.5, 0.3, 0.0], [1.5, 0.3, 0.0]])
    reference = np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    self.assertAlmostEqual(metrics().polyline_distance(actual, reference)['rms'], 0.3)

  def test_prefix_crossings(self):
    # Equal prefix length, later RMS ordering reverses. No candidate is selected.
    crossing = metrics().prefix_crossings(np.array([0.0, 2.0, 2.0]), np.array([1.0, 0.0, 0.0]), 0.01)
    self.assertEqual(crossing, [0.02])

  def test_no_future_reference_or_controller_import(self):
    root = Path(engine().__file__).parent
    import ast

    forbidden = {'socket', 'requests', 'urllib', 'subprocess', 'openpilot', 'cereal', 'opendbc'}
    for name in ('offline_multiobjective_v1.py', 'offline_multiobjective_gates_v1.py', 'offline_multiobjective_metrics_v1.py'):
      tree = ast.parse((root / name).read_text())
      for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
          names = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module or '']
          self.assertFalse(any(n.split('.')[0] in forbidden for n in names))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
          self.assertNotIn(node.func.id, ('eval', 'exec', 'compile'))


class TestOfflineOutput(unittest.TestCase):
  def test_output_is_exclusive(self):
    with tempfile.TemporaryDirectory() as td:
      directory = Path(td) / 'new'
      report = {'structural_status': 'STRUCTURALLY_BLOCKED', 'selected_candidate': None}
      engine().write_report(directory, report)
      first = (directory / 'diagnostics.json').read_bytes()
      with self.assertRaises(gates().EvidenceError):
        engine().write_report(directory, report)
      self.assertEqual((directory / 'diagnostics.json').read_bytes(), first)

  def test_wrong_request_hash_is_redacted(self):
    with tempfile.TemporaryDirectory() as td:
      f = Path(td) / 'private-name.json'
      f.write_text('{}')
      report = engine().evaluate(f, '0' * 64)
      self.assertEqual(report['structural_status'], 'STRUCTURALLY_BLOCKED')
      self.assertNotIn(str(f), json.dumps(report))
      self.assertEqual(report['performance_status'], 'PERFORMANCE_NOT_QUALIFIED')
      self.assertIs(report['effective'], False)
      self.assertIsNone(report['selected_candidate'])

  def test_unknown_input_is_not_f6_evidence(self):
    with tempfile.TemporaryDirectory() as td:
      f = Path(td) / 'request.json'
      f.write_text('{"schema":"UNAPPROVED"}')
      report = engine().evaluate(f, sha(f.read_bytes()))
      self.assertEqual(report['structural_status'], 'STRUCTURALLY_BLOCKED')

  def test_cli_does_not_echo_input(self):
    with patch('sys.stdout', new_callable=io.StringIO) as out:
      status = engine().main(['--request', '/does-not-exist/private', '--request-sha256', '0' * 64, '--output-dir', '/does-not-exist/output'])
    self.assertNotEqual(status, 0)
    self.assertNotIn('private', out.getvalue())


def miniature_archive(root):
  """Test-only mathematical archive. Patching its root hash is never a CLI capability."""
  e = engine()
  rows = fixture_rows()
  source = root / 'fixture.txt'
  source.write_bytes(b'mathematical parser fixture, not a Native producer')
  identity = {'F5_runtime_sources': {'fixture.txt': sha(source.read_bytes())}, 'original_sources': {'fixture.txt': sha(source.read_bytes())}}
  policy = {'scope': 'PARSER_UNIT_FIXTURE_ONLY'}
  for row in rows:
    row['source_sha256'] = sha(canonical(identity))
    row['policy_sha256'] = sha(canonical(policy))
  reseal(rows)
  item = item_for(rows)
  item.update(
    source_identity=identity,
    source_sha256=sha(canonical(identity)),
    policy=policy,
    policy_sha256=sha(canonical(policy)),
    trace_file='entry_step.json.gz',
    native_identity={'scope': 'PARSER_FIXTURE_NOT_EXECUTION_PROOF'},
    runtime_active=False,
    selected_candidate=None,
    selected_policy=None,
    source_function_calls={'native_update': len(rows), 'latcontrol_torque_update': len(rows), 'original_plant': len(rows)},
  )
  exogenous = ('sequence', 'speed_mps', 'desired_curvature_1pm', 'roll_rad', 'active', 'steering_pressed', 'safety_limited', 'curvature_limited')
  item['input_sha256'] = sha(canonical([{k: r['input'][k] for k in exogenous} for r in rows]))
  item['initial_state_sha256'] = sha(
    canonical(
      {
        'plant': rows[0]['plant_before'],
        'pose': rows[0]['pose_before'],
        'applied_last': 0.0,
        'native_state': rows[0]['native_state_before'],
        'candidate_state': None,
      }
    )
  )
  item['command_trace_sha256'] = sha(canonical([{k: r[k] for k in ('sequence', 'native_request', 'raw_candidate', 'delivered', 'applied')} for r in rows]))
  item['feedback_trace_sha256'] = sha(
    canonical(
      [{k: r[k] for k in ('sequence', 'plant_before', 'plant_after', 'pose_before', 'pose_after', 'native_state_before', 'native_state_after')} for r in rows]
    )
  )
  compressed = gzip.compress(canonical(rows), mtime=0)
  item.update(compressed_sha256=sha(compressed), trace_sha256=sha(canonical(rows)))
  item['result_receipt_sha256'] = sha(canonical(item))
  payload = {
    'schema': 'F5_REAL_OWN_FEEDBACK_PREDECLARED_V1',
    'source_head': e.BASE_HEAD,
    'CAN_access': False,
    'Params_write': False,
    'runtime_policy_activation': False,
    'results': [item],
  }
  files = {}
  for rep in (1, 2):
    for name, raw in [('result.json', canonical(payload)), ('entry_step.json.gz', compressed)]:
      key = f'results/test-a0-r{rep}/{name}'
      path = root / f'r{rep}-{name}'
      path.write_bytes(raw)
      files[key] = path
  manifest = {'files': [{'path': key, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for key, path in files.items()]}
  manifest_path = root / 'manifest.json'
  manifest_path.write_bytes(canonical(manifest))
  request = {
    'schema': 'CYBERPILOT_OFFLINE_EVALUATION_REQUEST_V1',
    'scope': 'PUBLIC_SYNTHETIC_ONLY',
    'manifest': {'path': str(manifest_path)},
    'artifacts': [{'id': k, 'path': str(v)} for k, v in files.items()],
    'source_files': [{'id': 'runtime:fixture.txt', 'path': str(source)}, {'id': 'original:fixture.txt', 'path': str(source)}],
    'traces': [
      {
        'result_id': 'results/test-a0-r1/result.json',
        'repeat_result_id': 'results/test-a0-r2/result.json',
        'case_id': 'entry_step',
        'trace_id': 'results/test-a0-r1/entry_step.json.gz',
        'repeat_trace_id': 'results/test-a0-r2/entry_step.json.gz',
      }
    ],
  }
  request_path = root / 'request.json'
  request_path.write_bytes(canonical(request))
  return request_path, sha(manifest_path.read_bytes()), files, source


class TestOfflineEvidenceLoader(unittest.TestCase):
  def test_production_root_rejects_self_attestation(self):
    with tempfile.TemporaryDirectory() as td:
      path, _, _, _ = miniature_archive(Path(td))
      report = engine().evaluate(path, sha(path.read_bytes()))
      self.assertEqual(report['structural_status'], 'STRUCTURALLY_BLOCKED')
      self.assertEqual(report['error_code'], 'E_MANIFEST_SHA')

  def test_checked_loader_and_repeat_receipt(self):
    with tempfile.TemporaryDirectory() as td:
      path, root_sha, _, _ = miniature_archive(Path(td))
      with patch.object(engine(), 'F5_MANIFEST_SHA256', root_sha):
        first = engine().evaluate(path, sha(path.read_bytes()))
        second = engine().evaluate(path, sha(path.read_bytes()))
      self.assertEqual(first['structural_status'], 'STRUCTURALLY_VALID')
      self.assertEqual(first, second)
      self.assertEqual(len(first['traces'][0]['metrics']), 28)
      self.assertTrue(all(g['status'] == 'STRUCTURALLY_VALID' for g in first['traces'][0]['gates']))
      self.assertEqual(first['new_controller_executions'], 0)
      self.assertEqual(first['performance_status'], 'PERFORMANCE_NOT_QUALIFIED')

  def test_artifact_and_source_tamper(self):
    for kind in ('source', 'trace', 'repeat', 'metadata'):
      with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
        path, root_sha, files, source = miniature_archive(Path(td))
        target = (
          source
          if kind == 'source'
          else files['results/test-a0-r2/entry_step.json.gz']
          if kind == 'repeat'
          else files['results/test-a0-r1/result.json']
          if kind == 'metadata'
          else files['results/test-a0-r1/entry_step.json.gz']
        )
        target.write_bytes(target.read_bytes() + b' ')
        with patch.object(engine(), 'F5_MANIFEST_SHA256', root_sha):
          report = engine().evaluate(path, sha(path.read_bytes()))
        self.assertEqual(report['structural_status'], 'STRUCTURALLY_BLOCKED')
        self.assertEqual(report['error_code'], 'E_SOURCE_SHA' if kind == 'source' else 'E_ARTIFACT_SHA')

  def test_cli_success_is_structural_only(self):
    with tempfile.TemporaryDirectory() as td:
      archive = Path(td) / 'inputs'
      archive.mkdir()
      path, root_sha, _, _ = miniature_archive(archive)
      output = Path(td) / 'diagnostic'
      with patch.object(engine(), 'F5_MANIFEST_SHA256', root_sha), patch('sys.stdout', new_callable=io.StringIO):
        code = engine().main(['--request', str(path), '--request-sha256', sha(path.read_bytes()), '--output-dir', str(output)])
      self.assertEqual(code, 0)
      report = json.loads((output / 'diagnostics.json').read_bytes())
      self.assertIs(report['effective'], False)
      self.assertIsNone(report['selected_candidate'])
      self.assertEqual(report['performance_status'], 'PERFORMANCE_NOT_QUALIFIED')


class TestOfflineReviewRegressions(unittest.TestCase):
  def test_no_write_inside_historical_tree_even_for_blocked_report(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      path, root_sha, _, _ = miniature_archive(root)
      output = root / 'forbidden'
      with patch.object(engine(), 'F5_MANIFEST_SHA256', root_sha), patch('sys.stdout', new_callable=io.StringIO):
        code = engine().main(['--request', str(path), '--request-sha256', sha(path.read_bytes()), '--output-dir', str(output)])
      self.assertEqual(code, 2)
      self.assertFalse(output.exists())

  def test_symlink_loop_redacted(self):
    with tempfile.TemporaryDirectory() as td:
      loop = Path(td) / 'private-loop'
      loop.symlink_to(loop)
      report = engine().evaluate(loop, '0' * 64)
      self.assertEqual(report['structural_status'], 'STRUCTURALLY_BLOCKED')
      self.assertNotIn('private-loop', json.dumps(report))

  def test_explicit_reset_rejects_stale_native_state(self):
    rows = fixture_rows(801)
    item = item_for(rows)
    item['case_id'] = 'controller_reset'
    rows[800]['explicit_controller_reset'] = True
    rows[800]['reset_events'] = ['CONTROLLER_RESET']
    rows[800]['native_state_before'] = copy.deepcopy(rows[799]['native_state_after'])
    reseal(rows)
    item['final_frame_receipt'] = rows[-1]['receipt_sha256']
    with self.assertRaises(gates().EvidenceError):
      gates().verify_frames(rows, item)

  def test_explicit_reset_accepts_source_fresh_state(self):
    rows = fixture_rows(801)
    item = item_for(rows)
    item['case_id'] = 'controller_reset'
    rows[800]['explicit_controller_reset'] = True
    rows[800]['reset_events'] = ['CONTROLLER_RESET']
    rows[800]['native_state_before'] = fresh_native_state('SCENARIO_BOUNDARY')
    reseal(rows)
    item['final_frame_receipt'] = rows[-1]['receipt_sha256']
    self.assertEqual(len(gates().verify_frames(rows, item)), 801)

  def test_spectral_amplitude_odd_and_nyquist(self):
    for n, bin_index, amplitude in ((999, 17, 0.3), (1000, 500, 0.4)):
      a = amplitude * np.cos(2 * np.pi * bin_index * np.arange(n) / n)
      result = metrics().spectrum(a, 0.01)
      self.assertAlmostEqual(result['amplitude'][bin_index], amplitude, places=12)

  def test_output_symlink_loop_redacted(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      archive = root / 'inputs'
      archive.mkdir()
      path, root_sha, _, _ = miniature_archive(archive)
      loop = root / 'private-loop'
      loop.symlink_to(loop)
      with patch.object(engine(), 'F5_MANIFEST_SHA256', root_sha), patch('sys.stdout', new_callable=io.StringIO) as output:
        code = engine().main(['--request', str(path), '--request-sha256', sha(path.read_bytes()), '--output-dir', str(loop)])
      self.assertEqual(code, 2)
      self.assertNotIn('private-loop', output.getvalue())

  def test_cli_large_integer_json_is_redacted(self):
    with tempfile.TemporaryDirectory() as td:
      path = Path(td) / 'private-request.json'
      path.write_bytes(b'{"schema":' + b'9' * 4301 + b'}')
      with patch('sys.stdout', new_callable=io.StringIO) as output:
        code = engine().main(['--request', str(path), '--request-sha256', sha(path.read_bytes()), '--output-dir', str(Path(td) / 'output')])
      self.assertEqual(code, 2)
      self.assertEqual(json.loads(output.getvalue())['error_code'], 'E_JSON')
      self.assertNotIn('private-request', output.getvalue())

  def test_spectral_amplitude(self):
    a = 0.3 * np.sin(2 * np.pi * 3 * np.arange(1000) / 100.0)
    result = metrics().spectrum(a, 0.01)
    self.assertAlmostEqual(result['amplitude'][30], 0.3, places=12)
    self.assertEqual(result['sample_count'], 1000)

  def test_rail_reversals(self):
    result = metrics().saturation(np.array([1.0, 1.0, 0.0, -1.0, -1.0, 0.0, 1.0]), 0.01)
    self.assertEqual(result['rail_sign_reversals'], 2)

  def test_vector_comparisons_do_not_duplicate_spectra(self):
    left = {'oscillation_spectrum': {'status': 'METRIC_COMPUTED', 'value': {'mean': 1.0, 'amplitude': [1.0, 2.0]}}}
    right = {'oscillation_spectrum': {'status': 'METRIC_COMPUTED', 'value': {'mean': 2.0, 'amplitude': [2.0, 3.0]}}}
    comparison = metrics().compare_metrics(left, right)['oscillation_spectrum']
    self.assertEqual(comparison['status'], 'METRIC_COMPUTED')
    self.assertEqual(set(comparison['fields']), {'.mean'})
    self.assertEqual(left['oscillation_spectrum']['value']['amplitude'], [1.0, 2.0])

  def test_horizon_comparison_is_not_unavailable(self):
    definition = {'horizon_sensitivity': {'status': 'METRIC_COMPUTED', 'value': {'prefixes': [{'horizon_s': 10.0, 'normal_rms': 1.0}]}}}
    other = {'horizon_sensitivity': {'status': 'METRIC_COMPUTED', 'value': {'prefixes': [{'horizon_s': 10.0, 'normal_rms': 2.0}]}}}
    out = metrics().compare_metrics(definition, other)
    self.assertEqual(out['horizon_sensitivity']['status'], 'METRIC_COMPUTED')
    self.assertTrue(out['horizon_sensitivity']['fields'])


if __name__ == '__main__':
  unittest.main()
