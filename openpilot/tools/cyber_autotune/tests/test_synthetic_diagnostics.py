import copy
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.synthetic_native_v2 import run_batch
from openpilot.tools.cyber_autotune.synthetic_pipeline import ARMS, evaluate, source_binding


class TestSyntheticDiagnostics(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    binding = source_binding()
    batches = {tune: {'schema': 'synthetic-arm-v2', 'status': 'COMPLETED_SYNTHETIC_ONLY', 'tune_id': tune,
                      'binding': binding, 'results': run_batch(tune), 'vehicle_activation_allowed': False}
               for tune in ('identity', 'gentle', 'firm')}
    # Real native-core fixtures, duplicated for parser tests only. Fresh-worker
    # repeatability is tested separately; this fixture does not establish it.
    arms = {name: [copy.deepcopy(batches[tune]), copy.deepcopy(batches[tune])] for name, tune in ARMS.items()}
    cls.report = {'evaluation': evaluate(arms), 'arms': arms}

  def test_native_zero_gain_is_reported_as_no_observed_change_not_improvement(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import diagnose
    result = diagnose(self.report)
    self.assertEqual(result['status'], 'DIAGNOSTIC_ONLY')
    for name in ('gentle', 'firm'):
      candidate = result['candidates'][name]
      self.assertEqual(candidate['gate_status'], 'REJECTED')
      long = candidate['axes']['longitudinal']
      self.assertEqual(long['completed_variants'], 17)
      self.assertEqual(long['changed_trace_variants'], 0)
      self.assertEqual(long['effect_status'], 'NO_OBSERVED_TRACE_CHANGE')
      self.assertEqual(long['regression_count'], 0)
    self.assertFalse(result['vehicle_activation_allowed'])

  def test_delay_variants_remain_separate_and_gate_reasons_are_preserved(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import diagnose
    before = canonical(self.report)
    result = diagnose(self.report)
    self.assertEqual(canonical(self.report), before)
    for name in ('gentle', 'firm'):
      candidate = result['candidates'][name]
      self.assertEqual(candidate['gate_reasons'], self.report['evaluation']['comparisons'][name]['reasons'])
      delays = [r['physical_delay_s'] for r in candidate['variants'] if r['case_id'] == 'lat_delay_sweep']
      self.assertEqual(delays, [0., .03, .15, .3])
      self.assertEqual(len(candidate['variants']), 50)
    self.assertEqual(result['candidates']['gentle']['axes']['lateral']['changed_trace_variants'], 25)

  def test_direction_zero_baseline_and_null_have_distinct_meaning(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import metric_delta
    self.assertEqual(metric_delta(2., 3., 'lower'),
                     {'baseline': 2., 'candidate': 3., 'oriented_delta': 1., 'relative_improvement': -.5, 'status': 'REGRESSION'})
    self.assertEqual(metric_delta(.9, .8, 'higher')['status'], 'REGRESSION')
    self.assertEqual(metric_delta(.8, .9, 'higher')['status'], 'IMPROVEMENT')
    self.assertEqual(metric_delta(0., 0., 'lower')['status'], 'UNCHANGED')
    self.assertIsNone(metric_delta(0., 0., 'lower')['relative_improvement'])
    self.assertIsNone(metric_delta(-.1, .1, 'higher')['relative_improvement'])
    self.assertEqual(metric_delta(None, None, 'lower')['status'], 'UNAVAILABLE')
    self.assertEqual(metric_delta(None, 0., 'lower')['status'], 'AVAILABILITY_CHANGED')

  def test_missing_corrupt_or_forged_evidence_fails_closed_without_partial_diagnostics(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import diagnose
    for mutate in (
      lambda r: r['evaluation'].update(status='PASS'),
      lambda r: r['arms']['gentle'].pop(),
      lambda r: r['arms']['firm'][1]['results'].pop(),
      lambda r: r['arms']['firm'][1]['results'][0]['metrics'].update(center_rms_m=float('nan')),
      lambda r: r['arms']['current'][0].update(vehicle_activation_allowed=True),
      lambda r: r['arms']['firm'][0]['results'][0].update(case_id='private-placeholder'),
      lambda r: r.update(unexpected='private-placeholder'),
    ):
      report = copy.deepcopy(self.report)
      mutate(report)
      with self.subTest(mutate=mutate):
        result = diagnose(report)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertNotIn('candidates', result)
        self.assertNotIn('private-placeholder', canonical(result).decode())
        self.assertFalse(result['vehicle_activation_allowed'])

  def test_cli_rejects_missing_input_without_echoing_path(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import main
    stream = io.StringIO()
    with redirect_stdout(stream):
      code = main(['/no-such-synthetic-input-private-placeholder.json'])
    self.assertEqual(code, 1)
    self.assertNotIn('private-placeholder', stream.getvalue())
    self.assertIn('BLOCKED', stream.getvalue())

  def test_recomputed_rejection_of_incomparable_plant_has_no_metric_diagnostics(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import diagnose
    report = copy.deepcopy(self.report)
    for arm in report['arms']['firm']:
      arm['results'][1]['plant_sha256'] = '0' * 64
    report['evaluation'] = evaluate(report['arms'])
    self.assertIn('lat_constant_left:COMPARISON_BINDING_MISMATCH', report['evaluation']['comparisons']['firm']['reasons'])
    result = diagnose(report)
    self.assertEqual(result['status'], 'BLOCKED')
    self.assertNotIn('candidates', result)

  def test_nonfinite_overflow_and_boolean_metric_values_are_rejected(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import metric_delta
    for a, b, direction in ((True, 1., 'lower'), (float('inf'), 1., 'lower'),
                            (-1e308, 1e308, 'higher'), (1., 2., 'unknown')):
      with self.subTest(a=a, b=b, direction=direction), self.assertRaises(ValueError):
        metric_delta(a, b, direction)

  def test_cli_reads_report_but_does_not_modify_it(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import main
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'input.json'
      raw = canonical(self.report)
      path.write_bytes(raw)
      stream = io.StringIO()
      with redirect_stdout(stream):
        code = main([str(path)])
      self.assertEqual(code, 0)
      self.assertIn('DIAGNOSTIC_ONLY', stream.getvalue())
      self.assertEqual(path.read_bytes(), raw)

  def test_cli_rejects_duplicate_keys_bad_encoding_oversize_and_symlink(self):
    from openpilot.tools.cyber_autotune.synthetic_diagnostics import MAX_REPORT_BYTES, main
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'input.json'
      for raw in (b'{"arms":{},"arms":{}}', b'\xff', b'{"private-placeholder":true}'):
        path.write_bytes(raw)
        stream = io.StringIO()
        with self.subTest(raw=raw), redirect_stdout(stream):
          self.assertEqual(main([str(path)]), 1)
        self.assertNotIn('private-placeholder', stream.getvalue())
      with path.open('wb') as output:
        output.truncate(MAX_REPORT_BYTES + 1)
      link = Path(directory) / 'symlink.json'
      link.symlink_to(path)
      for target in (path, link, Path(directory)):
        with self.subTest(target=target.name), redirect_stdout(io.StringIO()):
          self.assertEqual(main([str(target)]), 1)
