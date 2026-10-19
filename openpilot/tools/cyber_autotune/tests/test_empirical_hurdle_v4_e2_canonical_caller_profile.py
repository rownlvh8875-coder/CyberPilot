"""Exact source checking and conservative caller measurements."""

import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as inputs


class TestCallerProfile(unittest.TestCase):
  def test_actual_fast_slow_hash_bytes_and_live_original_aliases(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as q

    n = 32
    arrays = {'tick': np.zeros(n, np.int64), 'command': np.ones(n), 'speed': np.ones(n), 'streak': np.arange(1, n + 1, dtype=np.int64)}
    block = inputs.SourceBlock(arrays, 'a' * 64)
    with q.CallerProfile() as probe:
      block.check(fast=True)
      block.check(fast=False)
    stats = probe.snapshot()
    self.assertEqual(stats['source_checks']['fast'], 1)
    self.assertEqual(stats['source_checks']['full'], 1)
    self.assertEqual(stats['source_checks']['live_original_arrays_observed'], 8)
    self.assertEqual(stats['hashing']['source_alias_array_bytes'], 2 * 4 * n * 8)
    self.assertEqual(stats['hashing']['source_snapshot_array_bytes'], 4 * n * 8)
    self.assertGreater(stats['hashing']['metadata_JSON_bytes'], 0)

  def test_original_mutation_detection_preserved_in_every_native_mode(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    for optimized in (False, True):
      p = provider()
      s = p._specs['TRAIN'][0]
      block = s['parts'][0][0]
      mutable = {k: v.copy() for k, v in block.arrays.items()}
      # This exact original SourceBlock owns immutable snapshots but must also
      # detect changes to the originally admitted external ndarray aliases.
      replacement = inputs.SourceBlock(mutable, block.identity)
      p2 = provider()
      p2._specs['TRAIN'][0]['parts'] = ((replacement, s['parts'][0][1]),)
      mutable['command'][0] += 1
      with self.assertRaisesRegex(ValueError, 'ALIAS_CHANGED'):
        replacement.check(fast=True)
      self.assertEqual(q.integrity_optimization_status(optimized), 'SOURCE_INTEGRITY_OPTIMIZATION_UNPROVEN')

  def test_profile_is_restored_and_never_a_capacity_grant(self):
    import sys
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as q

    before = sys.getprofile()
    with self.assertRaises(RuntimeError):
      with q.CallerProfile():
        raise RuntimeError('intentional')
    self.assertIs(sys.getprofile(), before)
    value = q.capacity_assessment({})
    self.assertEqual(value['runtime'], 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN')
    self.assertEqual(value['memory'], 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN')
    self.assertFalse(value['private_execution_authorized'])


class TestPublicBoundary(unittest.TestCase):
  def test_new_workflow_is_separate_source_only_and_keeps_all_old_pins(self):
    import yaml
    from tools.cyberpilot.run_canonical_native_bounded import ROOT, public_check

    contract = public_check()
    self.assertEqual(len(contract['frozen_source_sha256']), 231)
    self.assertFalse(contract['future_private_authority'])
    flow = yaml.safe_load((ROOT / '.github/workflows/cyberpilot-canonical-native-bounded.yaml').read_text())
    steps = flow['jobs']['native-bounded']['steps']
    commands = '\n'.join(step.get('run', '') for step in steps)
    self.assertNotIn('git lfs pull', commands)
    self.assertNotIn('tools/op.sh setup', commands)
    self.assertIn('run_canonical_runtime_feasibility.py', commands)
    self.assertIn('run_canonical_native_bounded.py', commands)
    checkout = next(s for s in steps if s.get('uses', '').startswith('actions/checkout@'))
    self.assertIs(checkout['with']['lfs'], False)
    self.assertIs(checkout['with']['submodules'], False)
    self.assertIs(checkout['with']['persist-credentials'], False)


class TestEvidenceCompleteness(unittest.TestCase):
  def test_missing_empty_zero_or_wrong_witness_cannot_pass(self):
    from tools.cyberpilot.run_canonical_native_bounded import validate_witness

    valid = {
      name: {'calls': count, 'ordered_raw_array_witness_sha256': 'a' * 64} for name, count in {'potential_cache': 32, 'recursive': 384, 'infer': 36096}.items()
    }
    envelope = {'fixture': 'primary', 'profile_enabled': False, 'scientific_audit_enabled': True, 'profile': valid}
    self.assertEqual(validate_witness(envelope), valid)
    for wrong in (
      None,
      {},
      {**valid, 'infer': {**valid['infer'], 'calls': 0}},
      {**valid, 'infer': {**valid['infer'], 'ordered_raw_array_witness_sha256': 'wrong'}},
    ):
      with self.assertRaises(ValueError):
        validate_witness({**envelope, 'profile': wrong})
    with self.assertRaises(ValueError):
      validate_witness({**envelope, 'scientific_audit_enabled': False})

  def test_fixed_output_member_symlink_and_fifo_denied_before_payload_read(self):
    import os
    from pathlib import Path
    import tempfile
    from tools.cyberpilot.run_canonical_native_bounded import scientific_output_digests
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_output as out

    for kind in ('symlink', 'fifo'):
      with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'sealed'
        with out.Store(root) as store:
          train = store.write('train.json', {'public_synthetic': True})
          result = store.write('result.json', {'public_synthetic': True})
          complete = store.write('complete.json', {'train_raw_sha256': train, 'result_raw_sha256': result})
        target = root / 'train.json'
        target.unlink()
        if kind == 'symlink':
          marker = Path(tmp) / 'public-marker'
          marker.write_bytes(b'NEVER_READ')
          target.symlink_to(marker)
        else:
          os.mkfifo(target, 0o600)
        with self.assertRaises((ValueError, OSError)):
          scientific_output_digests(root, complete)

  def test_child_environment_has_no_loader_or_personal_credentials(self):
    from tools.cyberpilot.run_canonical_native_bounded import child_environment

    value = child_environment()
    self.assertEqual(value['OPENBLAS_NUM_THREADS'], '1')
    self.assertEqual(value['PYTHONNOUSERSITE'], '1')
    self.assertFalse(any(name in value for name in ('PYTHONPATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'GITHUB_TOKEN', 'HF_TOKEN', 'HOME')))


class TestLabWallCap(unittest.TestCase):
  def test_parent_measurement_wall_guard_fails_and_restores_alarm(self):
    import signal
    import time
    from tools.cyberpilot.run_canonical_native_bounded import wall_guard

    previous = signal.getsignal(signal.SIGALRM)
    with self.assertRaises(TimeoutError):
      with wall_guard(0.01):
        time.sleep(0.1)
    self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
    self.assertIs(signal.getsignal(signal.SIGALRM), previous)


class TestGranularSourceCosts(unittest.TestCase):
  def test_complete_job_phase_chunk_records_and_missing_evidence_rejected(self):
    import copy
    from pathlib import Path
    import tempfile
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as bounded
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as q

    self.assertTrue(callable(q.validate_granularity))
    with tempfile.TemporaryDirectory() as tmp:
      with q.CallerProfile() as probe:
        bounded.run_synthetic(provider(), Path(tmp) / 'public', bounded.old.synthetic_binding('3' * 40))
      snapshot = probe.snapshot()
    summary = q.validate_granularity(snapshot, 'primary')
    self.assertEqual(summary['job_role_admission_records'], 64)
    self.assertEqual(summary['source_constructor_calls'], 64)
    self.assertEqual(summary['horizon_chunks'], 384)
    self.assertEqual(summary['array_hash_bytes'], snapshot['hashing']['array_bytes'])
    self.assertEqual(summary['metadata_JSON_bytes'], snapshot['hashing']['metadata_JSON_bytes'])
    self.assertTrue(all(v['row_count'] == 1 for v in snapshot['granularity']['horizon_chunks']))
    for key in ('job_source_admission', 'horizon_chunks', 'metadata_spec_by_job_phase'):
      wrong = copy.deepcopy(snapshot)
      wrong['granularity'][key].pop()
      with self.assertRaises(ValueError):
        q.validate_granularity(wrong, 'primary')
    wrong = copy.deepcopy(snapshot)
    wrong['granularity']['horizon_chunks'][0]['costs']['digest']['CPU_nanoseconds'] = None
    with self.assertRaises(ValueError):
      q.validate_granularity(wrong, 'primary')

    for key in ('horizon_chunks', 'horizon_nonchunk_costs'):
      for label in ('SourceBlock.check', 'digest', '_spec_stamp'):
        for field in q.COST_FIELDS:
          wrong = copy.deepcopy(snapshot)
          wrong['granularity'][key][0]['costs'][label][field] += 1
          with self.assertRaises(ValueError, msg=(key, label, field)):
            q.validate_granularity(wrong, 'primary')
      for mutation in ('missing', 'duplicate'):
        wrong = copy.deepcopy(snapshot)
        if mutation == 'missing':
          wrong['granularity'][key].pop()
        else:
          wrong['granularity'][key].append(copy.deepcopy(wrong['granularity'][key][0]))
        with self.assertRaises(ValueError):
          q.validate_granularity(wrong, 'primary')
    wrong = copy.deepcopy(snapshot)
    wrong['granularity']['horizon_event_totals']['CHUNK']['digest']['array_bytes'] += 1
    with self.assertRaises(ValueError):
      q.validate_granularity(wrong, 'primary')
    self.assertIn('GENERIC_DIGEST_INCLUDES_ARRAY_SOURCE', snapshot['granularity']['metadata_spec_scope'])
