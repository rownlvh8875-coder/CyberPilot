import copy
import unittest
from unittest.mock import patch


class TestSyntheticPipeline(unittest.TestCase):
  def test_worker_real_batch_is_bounded_bound_and_repeatable(self):
    from openpilot.tools.cyber_autotune.synthetic_pipeline import run_arm, validate_arm
    first = run_arm('identity', timeout_s=60.)
    second = run_arm('identity', timeout_s=60.)
    self.assertEqual(first['status'], 'COMPLETED_SYNTHETIC_ONLY')
    self.assertEqual(first, second)
    self.assertEqual(len(first['results']), 50)
    self.assertEqual(sum(r['status'] == 'REJECTED_INPUT' for r in first['results']), 7)
    self.assertFalse(first['vehicle_activation_allowed'])
    for mutate in (
      lambda r: r['results'][0].pop('plant_sha256'),
      lambda r: r['results'][0]['metrics'].pop('center_rms_m'),
      lambda r: r['binding'].pop('files_sha256'),
      lambda r: r['results'][0].update(input_sha256='0' * 64),
      lambda r: r['results'][0].update(tune_sha256='0' * 64),
      lambda r: r['results'][0]['metrics'].update(center_rms_m=-1.),
      lambda r: r['results'][0]['metrics'].update(saturation_ratio=2.),
      lambda r: r['results'][0]['metrics'].update(command_zero_crossings=.5),
      lambda r: r['results'][0].update(scope='REAL_VEHICLE_VERIFIED'),
      lambda r: r['results'][0].update(time_semantics=None),
      lambda r: r['results'][0]['metrics'].update(lane_loss_recovery_s=0.),
    ):
      changed = copy.deepcopy(first)
      mutate(changed)
      with self.subTest(mutate=mutate), self.assertRaises(ValueError):
        validate_arm(changed, 'identity', changed['binding'])

  def test_real_timeout_reaps_worker(self):
    from openpilot.tools.cyber_autotune.synthetic_pipeline import run_arm
    result = run_arm('identity', timeout_s=.001)
    self.assertEqual(result['reason'], 'WORKER_TIMEOUT')
    self.assertFalse(result['vehicle_activation_allowed'])

  def test_worker_rejects_import_from_another_checkout_or_unbound_local_file(self):
    import sys
    from types import SimpleNamespace
    from openpilot.tools.cyber_autotune.synthetic_pipeline import ROOT, verify_worker_imports
    for file in ('/tmp/unbound-opendbc.py', str(ROOT / 'openpilot/system/unbound.py')):
      with self.subTest(file=file), patch.dict(sys.modules, {'opendbc.synthetic_unbound': SimpleNamespace(__file__=file)}):
        with self.assertRaises(ValueError):
          verify_worker_imports()

  def test_timeout_crash_empty_or_corrupt_worker_never_admitted(self):
    from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome
    from openpilot.tools.cyber_autotune.synthetic_pipeline import run_arm
    for result in (ProcessOutcome('TIMEOUT', -9, b'', 1), ProcessOutcome('EXITED', 1, b'', 1),
                   ProcessOutcome('EXITED', 0, b'{}', 1), ProcessOutcome('EXITED', 0, b'NaN', 1)):
      with self.subTest(result=result), patch('openpilot.tools.cyber_autotune.synthetic_pipeline._run_process', return_value=result):
        self.assertNotEqual(run_arm('identity', timeout_s=1.)['status'], 'COMPLETED_SYNTHETIC_ONLY')

  def test_bad_tune_timeout_and_boolean_rejected(self):
    from openpilot.tools.cyber_autotune.synthetic_pipeline import run_arm
    for tune, timeout in (('untrusted', 1.), ('identity', True), ('identity', 0.), ('identity', 121.)):
      with self.subTest(tune=tune, timeout=timeout), self.assertRaises(ValueError):
        run_arm(tune, timeout_s=timeout)

  def test_candidate_gate_fails_missing_nondeterminism_and_regression(self):
    from openpilot.tools.cyber_autotune.synthetic_pipeline import evaluate
    self.assertEqual(evaluate({})['status'], 'BLOCKED')
    # Real evidence is exercised separately; malformed responses cannot promote.
    arms = {k: [{'status': 'COMPLETED_SYNTHETIC_ONLY'}] * 2 for k in ('baseline', 'current', 'gentle', 'firm')}
    self.assertEqual(evaluate(arms)['status'], 'BLOCKED')
    altered = copy.deepcopy(arms)
    altered['baseline'][1]['arbitrary'] = True
    self.assertEqual(evaluate(altered)['status'], 'BLOCKED')
