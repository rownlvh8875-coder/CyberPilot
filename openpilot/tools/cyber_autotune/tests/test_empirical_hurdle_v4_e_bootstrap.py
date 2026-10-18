"""Fresh-process synthetic firewall checks; no original scientific inputs."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_bootstrap as bootstrap

ROOT = Path(__file__).resolve().parents[4]


class TestEBootstrap(unittest.TestCase):
  def cold(self, code):
    prefix = 'import sys\nsys.path.insert(0, ' + repr(str(ROOT)) + ')\n'
    return subprocess.run([sys.executable, '-I', '-B', '-c', prefix + code], capture_output=True, text=True, timeout=60)

  def test_unprepared_numpy_lazy_import_is_reproducibly_blocked(self):
    result = self.cold("""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_bootstrap as b
f = b.RuntimeFirewall()
sys.addaudithook(f)
try:
  np.unique(np.array([0.0, 1.0]))
except ValueError as exc:
  f.active = False
  assert str(exc) == 'E_FORBIDDEN_OPERATION_ATTEMPT'
  assert f.blocked_events == ['os.listdir']
  print('EXPECTED_COLD_IMPORT_BLOCK')
else:
  f.active = False
  raise AssertionError('cold import did not exercise the original defect')
""")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn('EXPECTED_COLD_IMPORT_BLOCK', result.stdout)

  def test_prepared_cold_numeric_path_passes_without_relaxing_firewall(self):
    result = self.cold("""
import json
from contextlib import ExitStack
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_bootstrap as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as d
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as e
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as inputs
b.warm_dependencies()
f = b.RuntimeFirewall()
sys.addaudithook(f)
def forbidden(*args, **kwargs):
  raise ValueError('SYNTHETIC_DESERIALIZATION_BLOCKED')
try:
  with ExitStack() as stack:
    b.trap_deserialization(stack, forbidden)
    p = np.array([0.1, 0.9, 0.2, 0.8])
    y = np.array([False, True, False, True])
    prior = np.array([0, 0, 1, 1], np.int64)
    selected = d.select_job(p, y, prior, candidate='HRI_D00_L01', fold='FOLD_A', anchor='a'*64, role='TRAIN')
    e.score_diagnostics(p, y, prior)
    norm = {'mean': np.zeros(5), 'std': np.ones(5), 'constant': np.zeros(5, bool),
            'effective': np.arange(5), 'constant_reference': np.zeros(5)}
    model = {'normalizer': norm, 'heads': {0: {'positions': [0, 1, 3, 4], 'coefficients': np.zeros(4)},
                                         1: {'positions': list(range(5)), 'coefficients': np.zeros(5)}}}
    stage2 = {'normalizer': norm, 'coefficients': np.array([0.25, 0., 0., 0., 0.])}
    decisions = tuple(selected['contexts'][c]['decision'] for c in ('PREVIOUS_STATIC', 'PREVIOUS_MOVE'))
    for h in (25, 50, 100, 200):
      path, gate, context = e.recursive(np.zeros((8, 2), np.int64), np.zeros((8, h)), np.ones((8, h)),
                                       'HRI_D00_L01', model, decisions, stage2, h, {})
      e.drift_chunk(np.zeros((8, 2), np.int64), np.zeros((8, h+1), np.int64), path, gate, context, 1)
    n = 804
    current = np.zeros(n, np.int64)
    target = np.tile(np.array([0, 1, 0, 1], np.int64), 201)
    prior = np.tile(np.array([0, 0, 1, 1], np.int64), 201)
    x = np.column_stack((np.ones(n), np.zeros(n), prior, current, np.ones(n))).astype(np.float64)
    output = e.integrated(x, current, model, decisions, stage2, {})
    e.tick_diagnostics(current, target, prior, output)
    pair = e.data.pair(output['delta'] - target, -target.astype(float), 'a'*64, output['projected'], target, current)
    clauses = json.loads((Path(e.__file__).resolve().parents[3] / 'docs/cyberpilot/changes/empirical-hurdle-acceptance-gate-v1.json').read_bytes())['clauses']
    job = {'status': 'EXECUTED_COMPLETE', 'one_step': pair, 'true_move': pair,
           'rollout': {str(h): {'overall': pair, 'path_moved': pair} for h in (25, 50, 100, 200)}}
    assert len(e.gates.fold_gate(job, clauses)['clauses']) == 32
    import pickle
    for operation in (lambda: pickle.loads(b'never-decoded'), lambda: np.load('never-opened'), lambda: np.save('never-created', p)):
      try:
        operation()
      except ValueError as exc:
        assert str(exc) == 'SYNTHETIC_DESERIALIZATION_BLOCKED'
      else:
        raise AssertionError('deserializer trap bypass')
    assert f.attempts == 0
finally:
  f.active = False
print('COLD_SYNTHETIC_FULL_NUMERIC_PATH_PASS')
""")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn('COLD_SYNTHETIC_FULL_NUMERIC_PATH_PASS', result.stdout)

  def test_directory_source_write_and_sensitive_import_still_blocked(self):
    for event, args in (
      ('os.listdir', ('synthetic',)),
      ('os.scandir', ('synthetic',)),
      ('open', ('synthetic', None, 577)),
      ('open', ('/mnt/e/unapproved', None, 0)),
      ('import', ('pickle',)),
      ('subprocess.Popen', ()),
    ):
      firewall = bootstrap.RuntimeFirewall()
      with self.assertRaises(ValueError):
        firewall(event, args)
      self.assertEqual(firewall.attempts, 1)
      self.assertEqual(firewall.blocked_events, [event])

  def test_v2_scientific_contract_identical_to_v1(self):
    public = ROOT / 'docs/cyberpilot/changes'
    old = json.loads((public / 'empirical-hurdle-stage1-v4-e-execution-protocol.json').read_bytes())
    new = json.loads((public / 'empirical-hurdle-stage1-v4-e-execution-protocol-v2.json').read_bytes())
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as e

    body = {k: v for k, v in new.items() if k != 'receipt_sha256'}
    self.assertEqual(e.sha(e.canonical(body)), new['receipt_sha256'])
    self.assertEqual(
      e.sha((ROOT / 'openpilot/tools/cyber_autotune/empirical_hurdle_v4_e_bootstrap.py').read_bytes()),
      new['source_sha256']['empirical_hurdle_v4_e_bootstrap.py'],
    )
    for key in (
      'jobs',
      'policy_arms',
      'selection',
      'input_scope',
      'resources',
      'causal_state',
      'acceptance',
      'validation_domains',
      'evaluation',
      'repeats',
      'publication',
      'forbidden_operations',
      'preserved',
    ):
      self.assertEqual(old[key], new[key])
    for name, digest in old['source_sha256'].items():
      self.assertEqual(new['source_sha256'][name], digest)
    self.assertEqual(set(new['source_sha256']) - set(old['source_sha256']), {'empirical_hurdle_v4_e_bootstrap.py'})


if __name__ == '__main__':
  unittest.main()
