"""Public fixed runtime model tests; no scientific private inputs."""

import importlib
import importlib.util
import unittest

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_runtime_model'


class TestRuntimeModel(unittest.TestCase):
  def model(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'RUNTIME_MODEL_NOT_IMPLEMENTED')
    return importlib.import_module(MODULE)

  def test_frozen_worst_case_counts(self):
    q = self.model().workload()
    self.assertEqual(q['recursive_row_steps'], 12129876000)
    self.assertEqual(q['Stage2_terms_upper'], 1128078468000)
    self.assertEqual(q['recursive_bridge_calls'], 23724000)
    self.assertEqual(q['Stage1_head_calls_upper'], 47448000)

  def test_zero_native_cost_does_not_erase_caller(self):
    q = self.model().amdahl(100.0, 40.0, 1000.0)
    self.assertAlmostEqual(q['accelerated_CPU_seconds'], 60.04)
    self.assertEqual(q['infinite_Stage2_speedup_floor_seconds'], 60.0)
    self.assertFalse(q['full_runtime_certified'])

  def test_invalid_workload_not_silently_reduced(self):
    for n in (0, -1, 336942, True):
      with self.subTest(n=n), self.assertRaises(ValueError):
        self.model().workload(n=n)

  def test_source_pins_and_authority(self):
    q = self.model().public_check()
    self.assertFalse(q['private_execution_authorized'])
    self.assertFalse(q['native_integration_authorized'])
    self.assertGreaterEqual(q['frozen_pins'], 220)

  def test_lab_recursive_matches_frozen_full_state(self):
    from tools.cyberpilot import run_canonical_runtime_feasibility as lab
    from tools.cyberpilot.canonical_readiness_fixture import models
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
    import numpy as np

    n, h, length = 8, 25, 45
    stage1, stage2 = models(length)
    stage2['coefficients'] *= 0.125
    initial = np.zeros((n, length + 1), np.int64)
    command = np.resize(np.array([-0.75, 0.75, -0.25, 0.25]), (n, length + h - 1))
    expected = b.recursive(
      initial, command, np.full((n, h), 10.0), 'HRI_D00_L45', stage1, stage2, (0.5, 0.5), 'D2', h, np.full(n, h, np.int64), {}, scope=b.SCOPE
    )
    result = lab.recursive_probe(b.canonical.canonical_predict_delta, n=n, horizon=h, arm='D2')
    for key in ('path', 'delta'):
      self.assertEqual(result[key].tobytes(), expected[key].tobytes())

  def test_runtime_workflow_cannot_enable_LFS_or_private_execution(self):
    import copy
    import yaml

    module = self.model()
    workflow = yaml.safe_load((module.ROOT / '.github/workflows/cyberpilot-canonical-runtime-lab.yaml').read_bytes())
    module.validate_workflow(workflow)
    for command in ('git lfs pull', './tools/op.sh setup', 'python runner.py --execute-private'):
      bad = copy.deepcopy(workflow)
      bad['jobs']['runtime']['steps'].append({'run': command})
      with self.subTest(command=command), self.assertRaises(ValueError):
        module.validate_workflow(bad)
    bad = copy.deepcopy(workflow)
    bad['jobs']['runtime']['steps'][0]['with']['lfs'] = True
    with self.assertRaises(ValueError):
      module.validate_workflow(bad)

  def test_measured_partial_cost_never_becomes_whole_runtime_proof(self):
    q = self.model()
    timing = [{'user_CPU_seconds': 0.001, 'system_CPU_seconds': 0.0}, {'user_CPU_seconds': 0.003, 'system_CPU_seconds': 0.0}]
    sample = {'Stage1': [{'N': 512, 'P': 93, 'measurements': timing}], 'boundary': [{'N': 512, 'results': {'Native_wrapper': {'measurements': timing}}}]}
    result = q.estimated_runtime(sample)
    self.assertEqual(result['conditional_original_alias_fast_checks'], 506112)
    self.assertEqual(result['Stage1_measured_call_cost_extrapolation_CPU_seconds'], 71172.0)
    self.assertIsNone(result['full_CPU_upper_bound_seconds'])
    self.assertIsNone(result['full_wall_upper_bound_seconds'])
    self.assertIsNone(result['actual_live_original_alias_bytes'])
    self.assertFalse(result['certified'])
    with self.assertRaises(ValueError):
      q.estimated_runtime({})
