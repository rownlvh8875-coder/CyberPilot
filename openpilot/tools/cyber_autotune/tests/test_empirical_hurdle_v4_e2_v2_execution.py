"""Synthetic V2 caller/qualification, no live private inputs."""

import importlib.util
from pathlib import Path
import unittest


class TestV2ImplementationPresent(unittest.TestCase):
  def test_additive_implementation_required(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_v2_qualification'))
    self.assertTrue((Path(__file__).parents[1] / 'empirical_hurdle_v4_e2_v2_execution.py').is_file())


import ast
import inspect
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_qualification as q
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_execution as runner
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as d
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as olddec
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as oldev
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e_evaluation import fixture_model


def population(candidate='HRI_D00_L01', n=1030):
  delay, length = d.frozen.m.parameters(candidate)
  tick = np.resize(np.array([0, 0, 1, 1, 1, 0, 1, 0], np.int64), n)
  segment = {'tick': tick, 'command': np.zeros(n), 'speed': np.ones(n), 'streak': np.arange(1, n + 1)}
  ix = np.arange(max(delay + length, length + 1) - 1, n - 1, dtype=np.int64)
  p = np.linspace(0.1, 0.9, len(ix), dtype=np.float64)
  y = tick[ix + 1] != tick[ix]
  prior = tick[ix] - tick[ix - 1]
  return [(segment, ix)], p, y, prior, fixture_model(length)[1]


def identity(candidate='HRI_D00_L01', fold='FOLD_A'):
  return {
    'job': [candidate, fold],
    'anchor_sha256': 'a' * 64,
    'stage2_receipts': dict.fromkeys(('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256'), 'b' * 64),
    'source_map_sha256': 'c' * 64,
  }


def proof(kind, job, status='BYTE_EXACT_PASS'):
  return {'kind': kind, 'job': list(job), 'status': status}


class TestNumericalPaths(unittest.TestCase):
  def setUp(self):
    self.blocks, self.p, self.y, self.prior, self.model = population()
    self.counters = {}
    self.cache = q.potentials(self.blocks, q.JOBS[0][0], self.model, self.p, self.y, self.prior, 0.5, self.counters)

  def call(self, kind='Q1', gate=None, **kwargs):
    return q.qualification(
      kind,
      self.blocks,
      q.JOBS[0][0],
      self.model,
      self.cache,
      self.cache['D0_gate'] if gate is None else gate,
      kwargs.get('identity', identity()),
      self.counters,
    )

  def test_original512_all_row_only(self):
    self.assertEqual(self.counters['TRAIN_counterfactual_Stage2_calls'], 3)
    self.assertEqual(self.counters['TRAIN_counterfactual_Stage2_calls_rows'], len(self.p))
    self.assertNotIn('D0_chunk_subset_qualification_calls', self.counters)

  def test_q1_whole_job_selected_one_call(self):
    row = self.call()
    self.assertEqual(row['status'], 'BYTE_EXACT_PASS')
    self.assertEqual(self.counters['D0_full_subset_qualification_calls'], 1)
    self.assertEqual(row['Q2'], 'NOT_EXECUTED_DIAGNOSTIC')

  def test_b_mismatch_c_pass_no_b_call(self):
    original = d.frozen.m.predict_delta
    sizes = []

    def batch(x, model):
      sizes.append(len(x))
      value = original(x, model)
      return np.nextafter(value, np.inf) if len(x) < 512 else value

    with patch.object(d.frozen.m, 'predict_delta', batch):
      self.assertEqual(self.call()['status'], 'BYTE_EXACT_PASS')
    self.assertEqual(sizes, [int(self.cache['D0_gate'].sum())])

  def test_c_mismatch_is_not_excused_by_unused_b(self):
    with patch.object(d.frozen.m, 'predict_delta', return_value=np.nextafter(self.cache['u'][self.cache['D0_gate']], np.inf)):
      self.assertEqual(self.call()['status'], 'BYTE_EXACT_MISMATCH')

  def test_q3_same_cache_new_selected_path(self):
    gate = np.arange(len(self.p)) % 3 == 0
    self.assertEqual(self.call('Q3', gate)['status'], 'BYTE_EXACT_PASS')
    self.assertEqual(self.counters['D2_full_subset_qualification_calls'], 1)

  def test_q3_one_ulp_mismatch_even_tick_equal(self):
    gate = self.cache['D0_gate']
    original = self.cache['u'][gate]
    changed = np.nextafter(original, np.inf)
    np.testing.assert_array_equal(d.frozen.m.project(original), d.frozen.m.project(changed))
    with patch.object(d.frozen.m, 'predict_delta', return_value=changed):
      self.assertEqual(self.call('Q3')['status'], 'BYTE_EXACT_MISMATCH')

  def test_signed_zero_mismatch(self):
    gate = self.cache['D0_gate']
    self.cache['u'][:] = 0.0
    with patch.object(d.frozen.m, 'predict_delta', return_value=np.full(int(gate.sum()), -0.0)):
      self.assertEqual(self.call()['status'], 'BYTE_EXACT_MISMATCH')

  def test_empty_gate_has_no_stage2_call(self):
    for kind in ('Q1', 'Q3'):
      with patch.object(d.frozen.m, 'predict_delta', side_effect=AssertionError('empty Stage2 call')):
        row = self.call(kind, np.zeros(len(self.p), bool))
      self.assertEqual(row['status'], 'VERIFIED_EMPTY_GATE_ORIGINAL_INTEGRATED_NOOP')
      self.assertEqual(row['numerical_calls'], 0)

  def test_all_move_calls_stage2(self):
    original = d.frozen.m.predict_delta
    with patch.object(d.frozen.m, 'predict_delta', wraps=original) as call:
      self.assertEqual(self.call(gate=np.ones(len(self.p), bool))['status'], 'BYTE_EXACT_PASS')
    call.assert_called_once()
    self.assertEqual(call.call_args.args[0].shape[0], len(self.p))

  def test_wrong_dtype_shape_and_nonfinite_result(self):
    for value in (np.ones(1), self.cache['u'][self.cache['D0_gate']].astype(np.float32), np.full(int(self.cache['D0_gate'].sum()), np.nan)):
      with patch.object(d.frozen.m, 'predict_delta', return_value=value):
        self.assertEqual(self.call()['status'], 'BYTE_EXACT_MISMATCH')

  def test_wrong_identity(self):
    for key, value in [('job', ['HRI_D05_L01', 'FOLD_A']), ('anchor_sha256', ''), ('stage2_receipts', {})]:
      v = identity()
      v[key] = value
      with self.assertRaises(ValueError):
        self.call(identity=v)

  def test_order_mismatch(self):
    self.blocks[0][0]['tick'][2] += 1
    with self.assertRaisesRegex(ValueError, 'ORDER'):
      self.call()

  def test_wrong_prior_label_or_dtype(self):
    for field in ('prior', 'y', 'p'):
      p, y, prior = self.p.copy(), self.y.copy(), self.prior.copy()
      if field == 'prior':
        prior[0] += 1
      if field == 'y':
        y[0] = not y[0]
      if field == 'p':
        p = p.astype(np.float32)
      with self.assertRaises(ValueError):
        q.potentials(self.blocks, q.JOBS[0][0], self.model, p, y, prior, 0.5, {})

  def test_invalid_static_potential_not_repaired(self):
    for output in (np.nan, 32768.0):
      with patch.object(d.frozen.m, 'predict_delta', side_effect=lambda x, model, output=output: np.full(len(x), output)), self.assertRaises(ValueError):
        q.potentials(self.blocks, q.JOBS[0][0], self.model, self.p, self.y, self.prior, 0.5, {})

  def test_input_arrays_unchanged(self):
    before = [a.tobytes() for a in (self.p, self.y, self.prior, self.model['coefficients'])]
    self.call()
    self.call('Q3')
    self.assertEqual(before, [a.tobytes() for a in (self.p, self.y, self.prior, self.model['coefficients'])])

  def test_q3_two_context_routing_and_equality(self):
    record = {'count': len(self.p), 'contexts': {name: {'decision': 0.5} for name in q.CONTEXTS}}
    np.testing.assert_array_equal(q.d2_gate(self.cache, record), self.p > 0.5)
    record['contexts']['PREVIOUS_STATIC']['decision'] = 1.0
    gate = q.d2_gate(self.cache, record)
    self.assertFalse(gate[self.prior == 0].any())


class TestGlobalBarrier(unittest.TestCase):
  def pre_q1(self):
    phase = q.Phase()
    phase.begin()
    for job in q.JOBS:
      phase.complete('D0', job)
    phase.advance('POTENTIALS')
    for job in q.JOBS:
      phase.complete('POTENTIALS', job)
    phase.advance('Q1')
    return phase

  def test_missing_d0_blocks_potentials(self):
    phase = q.Phase()
    phase.begin()
    with self.assertRaises(ValueError):
      phase.advance('POTENTIALS')

  def test_missing_potentials_blocks_q1(self):
    phase = q.Phase()
    phase.begin()
    for job in q.JOBS:
      phase.complete('D0', job)
    phase.advance('POTENTIALS')
    with self.assertRaises(ValueError):
      phase.advance('Q1')

  def test_q1_all32_before_selection(self):
    phase = self.pre_q1()
    for job in q.JOBS[:-1]:
      phase.record_qualification(job, proof('Q1', job))
    with self.assertRaises(ValueError):
      phase.advance('SELECTION')
    phase.record_qualification(q.JOBS[-1], proof('Q1', q.JOBS[-1]))
    phase.advance('SELECTION')
    with self.assertRaises(ValueError):
      phase.require_dev()

  def test_q1_fail_global_no_selection(self):
    phase = self.pre_q1()
    with self.assertRaisesRegex(ValueError, q.Q1_FAILURE):
      phase.record_qualification(q.JOBS[0], proof('Q1', q.JOBS[0], 'BYTE_EXACT_MISMATCH'))
    with self.assertRaises(ValueError):
      phase.advance('SELECTION')
    with self.assertRaises(ValueError):
      phase.authorize('V4', 'manifest.json', 'metadata')

  def test_wrong_order_and_duplicate(self):
    phase = self.pre_q1()
    with self.assertRaises(ValueError):
      phase.record_qualification(q.JOBS[1], proof('Q1', q.JOBS[1]))
    phase.record_qualification(q.JOBS[0], proof('Q1', q.JOBS[0]))
    with self.assertRaises(ValueError):
      phase.record_qualification(q.JOBS[0], proof('Q1', q.JOBS[0]))

  def test_q3_cannot_precede_selection(self):
    phase = self.pre_q1()
    with self.assertRaises(ValueError):
      phase.record_qualification(q.JOBS[0], proof('Q3', q.JOBS[0]))

  def test_no_source_reads_in_q1_q3_or_selection(self):
    phase = self.pre_q1()
    phase.job = q.JOBS[0]
    for stage in ('Q1', 'SELECTION', 'Q3'):
      phase.stage = stage
      with self.assertRaises(ValueError):
        phase.authorize('V4', 'candidates/HRI_D00_L01/FOLD_A/train/combined_probability.npy.gz', 'array')

  def test_stage2_forbidden_in_d0_and_score_forbidden_in_potentials(self):
    phase = q.Phase()
    phase.begin()
    phase.job = q.JOBS[0]
    with self.assertRaises(ValueError):
      phase.authorize('V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/coefficients.npy.gz', 'array')
    phase.stage = 'POTENTIALS'
    with self.assertRaises(ValueError):
      phase.authorize('V4', 'candidates/HRI_D00_L01/FOLD_A/train/combined_probability.npy.gz', 'array')

  def test_dev_gate_and_mixed_carrier_blocked(self):
    phase = q.Phase()
    phase.begin()
    phase.job = q.JOBS[0]
    for tail in ('one-step/p_move.npy.gz', 'train/receipt.json', 'train/STATIC_coefficients.npy.gz'):
      with self.assertRaises(ValueError):
        phase.authorize('V4', 'candidates/HRI_D00_L01/FOLD_A/' + tail, 'array')


class Provider:
  def __init__(self):
    self.stage2_cache = {}
    self.populations = [population(c, 120) for c, _ in q.JOBS]
    self.references = [{'stage2': dict.fromkeys(('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256'), 'b' * 64)} for _ in q.JOBS]

  def train(self, i):
    return self.populations[i][1:4]

  def train_blocks(self, i):
    return self.populations[i][0], 'a' * 64, len(self.populations[i][1])

  def stage2(self, i):
    self.stage2_cache[i] = self.populations[i][4]
    return self.stage2_cache[i]


class TestFreshTrainingSynthetic(unittest.TestCase):
  def run_train(self, phase=None):
    phase = phase or q.Phase()
    counters = {}
    jobs = [{'candidate_id': c, 'fold': f, 'fields': [{'anchor_sha256': 'a' * 64}]} for c, f in q.JOBS]
    records, d0, d1 = runner.train(Provider(), phase, d, q, oldev, olddec, jobs, counters, {'TRAIN_cache_bytes': 539105600}, 'c' * 64)
    return phase, counters, records, d0, d1

  def test_fresh_all32_all64_q3_and_no_dev_until_seal(self):
    phase, count, records, _, _ = self.run_train()
    self.assertEqual((len(phase.qualified), phase.decisions, len(phase.Q3_jobs)), (32, 64, 32))
    self.assertEqual(count['D0_TRAIN_reconstruction_calls'], 32)
    self.assertEqual(count['D2_context_decision_selection_calls'], 64)
    self.assertNotIn('D0_chunk_subset_qualification_calls', count)
    with self.assertRaises(ValueError):
      phase.require_dev()
    with self.assertRaises(ValueError):
      phase.unlock(records, 'a' * 64, 'b' * 64)
    phase.unlock(records, 'a' * 64, 'a' * 64)
    phase.require_dev()

  def test_repeat_train_canonical_exact(self):
    a = self.run_train()
    b = self.run_train()
    self.assertEqual(runner.canonical(a[1:]), runner.canonical(b[1:]))

  def test_q3_fail_no_reselection_or_dev(self):
    original = q.qualification
    phase = q.Phase()

    def fail(kind, *args):
      value = original(kind, *args)
      if kind == 'Q3':
        value['status'] = 'BYTE_EXACT_MISMATCH'
      return value

    with patch.object(q, 'qualification', fail), patch.object(d, 'select_job', wraps=d.select_job) as select:
      with self.assertRaisesRegex(ValueError, q.Q3_FAILURE):
        self.run_train(phase)
    self.assertEqual(select.call_count, 32)
    self.assertTrue(phase.aborted)
    self.assertEqual(phase.decisions, 64)
    with self.assertRaises(ValueError):
      phase.require_dev()

  def test_q1_fail_zero_d2_selection(self):
    original = q.qualification

    def fail(kind, *args):
      value = original(kind, *args)
      value['status'] = 'BYTE_EXACT_MISMATCH'
      return value

    with patch.object(q, 'qualification', fail), patch.object(d, 'select_job', side_effect=AssertionError('D2 too early')):
      with self.assertRaisesRegex(ValueError, q.Q1_FAILURE):
        self.run_train()

  def test_cache_resource_bound(self):
    jobs = [{'candidate_id': c, 'fold': f, 'fields': [{'anchor_sha256': 'a' * 64}]} for c, f in q.JOBS]
    with self.assertRaisesRegex(ValueError, 'RESOURCE'):
      runner.train(Provider(), q.Phase(), d, q, oldev, olddec, jobs, {}, {'TRAIN_cache_bytes': 1}, 'c' * 64)


class TestAuthorityAndStructure(unittest.TestCase):
  def test_never_calls_v1_potentials_or_run(self):
    tree = ast.parse(inspect.getsource(runner))
    names = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    self.assertTrue(names.isdisjoint({'legacy.run', 'legacy.preflight', 'dec.potentials', 'decision.potentials'}))

  def test_no_discovery_or_unsafe_deserialization(self):
    tree = ast.parse(inspect.getsource(runner) + inspect.getsource(q))
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    self.assertTrue(calls.isdisjoint({'glob', 'rglob', 'os.listdir', 'os.scandir', 'os.walk', 'np.load', 'pickle.load'}))

  def test_current_grant_distinct_from_v1(self):
    self.assertNotEqual(runner.MISSION, runner.legacy.MISSION)
    self.assertIn("gate['mission'] == MISSION", inspect.getsource(runner.preflight))

  def test_new_q3_failure_status(self):
    self.assertEqual(runner.failure_status(ValueError(q.Q3_FAILURE)), q.Q3_FAILURE)
    self.assertEqual(runner.failure_status(ValueError(q.Q1_FAILURE)), q.Q1_FAILURE)

  def test_stored_verify_does_not_load_scientific_sources(self):
    names = {ast.unparse(n.func) for n in ast.walk(ast.parse(inspect.getsource(runner.stored))) if isinstance(n, ast.Call)}
    self.assertTrue(names.isdisjoint({'frozen_sources', 'preflight', 'legacy.load_exact', 'run', 'train', 'q.potentials', 'ev.evaluate_job'}))

  def test_forbidden_operation_names(self):
    self.assertIn('rebatching_retry', runner.FORBIDDEN)
    self.assertIn('extra_tolerance', runner.FORBIDDEN)
    self.assertEqual(len(runner.FORBIDDEN), len(set(runner.FORBIDDEN)))

  def test_stdout_does_not_print_row_or_gate_telemetry(self):
    tree = ast.parse(inspect.getsource(runner))
    prints = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'print']
    for text in prints:
      self.assertNotIn('reader.summary()', text)
      self.assertNotIn('operation_counters', text)
      self.assertNotIn('numerical_calls', text)


class TestV2DurableLifecycle(unittest.TestCase):
  def boundary(self, failed_kind=None):
    import contextlib
    import io
    import tempfile
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_evaluation as ev
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_bootstrap as boot
    from openpilot.tools.cyber_autotune import empirical_s2_ri_policy

    protocol = runner.checked((runner.PUBLIC / runner.PROTOCOL).read_bytes())
    base = Provider

    class SyntheticProvider(base):
      def __init__(self, *args, **kwargs):
        super().__init__()

      def admit_train_sources(self):
        pass

    modules = {
      'empirical_hurdle_v4_e2_inputs': inp,
      'empirical_hurdle_v4_e2_decision': d,
      'empirical_hurdle_v4_e2_evaluation': ev,
      'empirical_hurdle_v4_e_evaluation': oldev,
      'empirical_hurdle_v4_e_decision': olddec,
      'empirical_hurdle_v4_e2_v2_qualification': q,
      'empirical_hurdle_v4_e_bootstrap': boot,
      'empirical_s2_ri_policy': empirical_s2_ri_policy,
    }
    jobs = [{'candidate_id': c, 'fold': f, 'fields': [{'anchor_sha256': 'a' * 64}]} for c, f in q.JOBS]
    original_private, original_q = runner.private, q.qualification
    dev_reads = []

    def private(path, cap=16 * 1024**2):
      if path.name == 'canonical-result.json':
        dev_reads.append(True)
        raise FileNotFoundError('synthetic post-barrier comparison unavailable')
      return original_private(path, cap)

    def qualification(kind, *args):
      record = original_q(kind, *args)
      if kind == failed_kind:
        record['status'] = 'BYTE_EXACT_MISMATCH'
      return record

    boot.warm_dependencies()
    with tempfile.TemporaryDirectory() as tmp:
      work = Path(tmp)
      work.chmod(0o700)
      roots = {k: str(work / k) for k in ('V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED')}
      args = (
        protocol,
        b'synthetic-V2',
        modules,
        runner.sealed({'E1_canonical_raw_sha256': 'a' * 64, 'E1_head': 'h', 'prior_lineage': {}}),
        roots,
        {'manifests': {'V4_REPEAT_1': {}, 'V1_REFERENCE': {}}, 'authorization': {'V1_REFERENCE': 'a' * 64}},
        {},
        jobs,
        (work.stat().st_dev, work.stat().st_ino),
        {'references': {'WORK': str(work / 'old')}},
      )
      with (
        patch.object(runner.resource, 'setrlimit'),
        patch.object(runner.signal, 'signal'),
        patch.object(runner.signal, 'alarm'),
        patch.object(runner, 'preflight', return_value=args),
        patch.object(inp, 'Provider', SyntheticProvider),
        patch.object(q, 'qualification', side_effect=qualification),
        patch.object(runner, 'private', side_effect=private),
        contextlib.redirect_stdout(io.StringIO()),
        self.assertRaises(SystemExit),
      ):
        runner.run(work, 'repeat-1')
      record = runner.checked((work / 'repeat-1/execution-envelope.json').read_bytes())
      if failed_kind:
        self.assertEqual(dev_reads, [])
        self.assertEqual(record['status'], q.Q1_FAILURE if failed_kind == 'Q1' else q.Q3_FAILURE)
        self.assertFalse((work / 'repeat-1/train-decisions.json').exists())
        self.assertEqual(record['operation_counters'].get('D2_context_decision_selection_calls', 0), 0 if failed_kind == 'Q1' else 64)
      else:
        self.assertEqual(dev_reads, [True])
        train = runner.checked((work / 'repeat-1/train-decisions.json').read_bytes())
        self.assertEqual(train['Q3_PASS_jobs'], 32)
        self.assertEqual(len(train['qualification_proofs']['Q1']), 32)
        self.assertEqual((work / 'repeat-1/train-decisions.json').stat().st_mode & 0o777, 0o600)
      self.assertEqual(record['source_writes'], 0)
      self.assertEqual(record['forbidden_attempts'], 0)

  def test_q1_abort_sealed_without_dev(self):
    self.boundary('Q1')

  def test_q3_abort_sealed_without_dev_or_reselection(self):
    self.boundary('Q3')

  def test_durable_readback_precedes_first_dev_read(self):
    self.boundary()

  def test_resource_plan_matches_frozen_caps(self):
    protocol = runner.checked((runner.PUBLIC / runner.PROTOCOL).read_bytes())
    self.assertEqual(runner.resource_plan(protocol)['analytical_live_bound_bytes'], 5574680630)

  def test_bad_resource_plan_blocks(self):
    protocol = runner.checked((runner.PUBLIC / runner.PROTOCOL).read_bytes())
    protocol['resources']['chunk_rows'] = 256
    with self.assertRaises(ValueError):
      runner.resource_plan(protocol)


class TestFrozenLocksAndGrant(unittest.TestCase):
  def test_additive_raw_source_lock(self):
    lock = runner.checked((runner.PUBLIC / runner.LOCK).read_bytes())
    for name, digest in lock['additive_source_sha256'].items():
      self.assertEqual(runner.sha((runner.SOURCE / name).read_bytes()), digest)

  def test_original_v1_d2_and_frozen_v2_unchanged(self):
    expected = {
      'empirical-hurdle-stage1-v4-e2-execution-protocol.json': '177925af0d9a70fecaeb2f8d848dbdee9c620f92047a9d8320e0ed6e1e7ef7db',
      runner.PROTOCOL: runner.PROTOCOL_SHA,
      'empirical-hurdle-stage1-v4-e2-numerical-qualification-v2.json': runner.AMENDMENT_SHA,
      'empirical-hurdle-stage1-v4-d2-loss-aware-policy.json': '51eea816f6f2d3f648a9030dc6cf2d1718fb456bf3d0e6e9903ac34ae2e6bba7',
      'empirical-hurdle-acceptance-gate-v1.json': '606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1',
    }
    for name, digest in expected.items():
      self.assertEqual(runner.sha((runner.PUBLIC / name).read_bytes()), digest)

  def gated_preflight(self, *, mission=None, success=True):
    import subprocess

    p = runner.checked((runner.PUBLIC / runner.PROTOCOL).read_bytes())
    gate = {
      'head': 'h',
      'mission': mission or runner.MISSION,
      'protocol_raw_sha256': runner.sha(b'protocol'),
      'implementation_lock_raw_sha256': runner.sha(b'lock'),
      'ci': {'head_sha': 'h', 'status': 'completed', 'conclusion': 'success' if success else 'failure'},
    }

    def git(*args):
      if args[0] == 'branch':
        return 'feature/cyber-autotune'
      if args[0] == 'status':
        return ''
      return 'h'

    reads = []

    def private(path, cap=0):
      reads.append(path.name)
      return runner.canonical(runner.sealed(gate))

    with (
      patch.object(runner, 'frozen_sources', return_value=(p, b'protocol', {'additive_source_sha256': {}}, b'lock', {})),
      patch.object(runner.legacy, 'git', side_effect=git),
      patch.object(subprocess, 'run'),
      patch.object(runner.legacy, 'private', side_effect=private),
      patch.object(runner.legacy, 'controls', side_effect=AssertionError('historical control read too early')),
      self.assertRaises(ValueError),
    ):
      runner.preflight(Path('synthetic-output'))
    self.assertEqual(reads, ['execution-gate.json'])

  def test_v1_grant_cannot_authorize_v2_control_reads(self):
    self.gated_preflight(mission=runner.legacy.MISSION)

  def test_failed_ci_blocks_before_historical_input(self):
    self.gated_preflight(success=False)

  def test_public_projection_unchanged_and_no_unsafe_cells(self):
    lock = runner.checked((runner.PUBLIC / runner.LOCK).read_bytes())
    self.assertTrue(lock['publication_projection']['three_arm_both_fold_joint_suppression'])
    self.assertEqual(lock['publication_projection']['minimum_support'], 201)
    self.assertEqual(lock['publication_projection']['onset_continuation_rare_exact_counts'], 'WITHHELD')

  def test_two_distinct_repeat_roots_required_by_cli(self):
    source = inspect.getsource(runner.main)
    self.assertIn("stored(work, 'repeat-1')", source)
    self.assertIn("need(a == b, 'E2_REPEATABILITY_FAILED')", source)
    self.assertIn('os.mkdir(destination, 0o700)', inspect.getsource(runner.run))

  def test_no_tolerance_or_retry_implementation(self):
    source = ast.parse(inspect.getsource(q))
    names = {ast.unparse(n.func) for n in ast.walk(source) if isinstance(n, ast.Call)}
    self.assertTrue(names.isdisjoint({'np.allclose', 'np.isclose'}))
    self.assertEqual(
      sum(isinstance(n, ast.Call) and ast.unparse(n.func) == 'decision.frozen.m.predict_delta' for n in ast.walk(source)), 2
    )  # A and shared whole-job qualification only.


class TestStoredV2Evidence(unittest.TestCase):
  def fixture(self):
    import copy
    from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_evaluation import stored_fixture
    protocol = runner.checked((runner.PUBLIC / runner.PROTOCOL).read_bytes())
    lock_raw = (runner.PUBLIC / runner.LOCK).read_bytes()
    lock = runner.checked(lock_raw)
    references = runner.public('empirical-hurdle-fit-cv-results-v1.json')['jobs']
    value = stored_fixture()
    value.pop('receipt_sha256')
    value.update(head='1' * 40, protocol_sha256=runner.PROTOCOL_SHA, execution_version='V2',
                 V2_forbidden_operation_counters=dict.fromkeys(runner.FORBIDDEN, 0),
                 V2_qualification={'Q1_jobs': 32, 'Q3_jobs': 32, 'decisions': 64, 'Q2': 'NOT_EXECUTED_DIAGNOSTIC', 'Q2_private_calls': 0})
    proofs = {'Q1': [], 'Q3': []}
    d0, d1 = [], []
    for index, row in enumerate(value['jobs']):
      ref = references[index]
      row['TRAIN']['anchor_sha256'] = ref['train_anchor_sha256']
      row['TRAIN']['count'] = ref['train_count']
      for k, size in zip(q.CONTEXTS, (ref['train_count'] // 2, ref['train_count'] - ref['train_count'] // 2), strict=True):
        row['TRAIN']['contexts'][k].update(count=size, positive=201, negative=size - 201)
      d0.append({'value': 0.5, 'count': ref['train_count']})
      d1.append({'candidate_id': row['candidate_id'], 'fold': row['fold'], 'anchor_sha256': ref['train_anchor_sha256'], 'contexts': {}})
      for kind in proofs:
        item = proof(kind, q.JOBS[index])
        item.update(identity={'job': list(q.JOBS[index]), 'anchor_sha256': ref['train_anchor_sha256'],
                             'source_map_sha256': runner.sha(runner.canonical(protocol['source_sha256'])),
                             'stage2_receipts': {k: ref['stage2'][k] for k in identity()['stage2_receipts']}},
                    dtype='<f8', Q2='NOT_EXECUTED_DIAGNOSTIC', nonempty=True, numerical_calls=1)
        proofs[kind].append(item)
    train = {'schema': 'V4_E2_V2_ALL64_TRAIN_DECISIONS_V1', 'protocol_sha256': runner.PROTOCOL_SHA,
             'qualification_PASS_jobs': 32, 'Q3_PASS_jobs': 32, 'qualification_proofs': proofs, 'Q2': 'NOT_EXECUTED_DIAGNOSTIC',
             'jobs': copy.deepcopy([row['TRAIN'] for row in value['jobs']]), 'D0_reconstruction': d0, 'D1_TRAIN_reproduction': d1}
    binding = runner.sealed({'schema': 'V4_E2_V2_FRESH_BINDING_V1', 'head': value['head'], 'baseline_head': runner.BASELINE,
                            'protocol_raw_sha256': runner.PROTOCOL_SHA, 'protocol_receipt_sha256': protocol['receipt_sha256'],
                            'implementation_lock_raw_sha256': runner.sha(lock_raw),
                            'source_sha256': {**protocol['source_sha256'], **lock['additive_source_sha256']},
                            'current_explicit_human_grant': runner.MISSION,
                            'F_AUTHORIZED': False, 'policy_adoption_authorized': False, 'V5_AUTHORIZED': False})
    return value, train, binding

  def call(self, value, train, binding):
    train = runner.sealed({k: v for k, v in train.items() if k != 'receipt_sha256'})
    value['TRAIN_seal_sha256'] = runner.sha(runner.canonical(train))
    value = runner.sealed({k: v for k, v in value.items() if k != 'receipt_sha256'})
    binding = runner.sealed({k: v for k, v in binding.items() if k != 'receipt_sha256'})
    envelope = runner.sealed({'schema': 'V4_E2_V2_EXECUTION_ENVELOPE_V1', 'replica': 'repeat-1', 'forbidden_attempts': 0,
                              'canonical_raw_sha256': runner.sha(runner.canonical(value)),
                              'binding_receipt_sha256': binding['receipt_sha256'], 'source_writes': 0})
    records = {'execution-envelope.json': envelope, 'execution-binding.json': binding, 'train-decisions.json': train, 'canonical-result.json': value}
    with patch.object(runner, 'private', side_effect=lambda path, *args: runner.canonical(records[path.name])), \
         patch.object(d.frozen.m, 'predict_delta', side_effect=AssertionError('resume inference')):
      return runner.stored(Path('synthetic'), 'repeat-1')

  def test_valid_stored_v2_no_inference(self):
    self.call(*self.fixture())

  def test_missing_proof_metadata_rejected(self):
    for key in ('identity', 'dtype', 'Q2', 'nonempty', 'numerical_calls'):
      value, train, binding = self.fixture()
      train['qualification_proofs']['Q1'][0].pop(key)
      with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)

  def test_contradictory_proof_metadata_rejected(self):
    for key, replacement in [('dtype', '<f4'), ('Q2', 'PASS'), ('nonempty', False), ('numerical_calls', 0), ('numerical_calls', True)]:
      value, train, binding = self.fixture()
      train['qualification_proofs']['Q3'][0][key] = replacement
      with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)

  def test_proof_identity_mutations_rejected(self):
    for key in ('job', 'anchor_sha256', 'source_map_sha256', 'stage2_receipts'):
      value, train, binding = self.fixture()
      train['qualification_proofs']['Q3'][0]['identity'][key] = [] if key == 'job' else {} if key == 'stage2_receipts' else 'f' * 64
      with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)

  def test_binding_lock_and_source_mutations_rejected(self):
    for key in ('implementation_lock_raw_sha256', 'source_sha256', 'current_explicit_human_grant'):
      value, train, binding = self.fixture()
      binding[key] = {} if key == 'source_sha256' else 'wrong'
      with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)

  def test_closed_authority_flags_required(self):
    for key in ('F_AUTHORIZED', 'policy_adoption_authorized', 'V5_AUTHORIZED'):
      for replacement in (None, True, 1):
        value, train, binding = self.fixture()
        if replacement is None:
          binding.pop(key)
        else:
          binding[key] = replacement
        with self.subTest(key=key, value=replacement), self.assertRaises((ValueError, KeyError)):
          self.call(value, train, binding)

  def test_envelope_source_writes_required_zero(self):
    for replacement in (None, True, 1):
      value, train, binding = self.fixture()
      original = runner.checked
      def checked(raw, original=original, replacement=replacement):
        record = original(raw)
        if record.get('schema') == 'V4_E2_V2_EXECUTION_ENVELOPE_V1':
          if replacement is None:
            record.pop('source_writes')
          else:
            record['source_writes'] = replacement
        return record
      with self.subTest(value=replacement), patch.object(runner, 'checked', side_effect=checked), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)

  def test_train_schema_q2_mutations_rejected(self):
    for key, replacement in [('schema', 'V1'), ('Q2', 'PASS'), ('Q3_PASS_jobs', True)]:
      value, train, binding = self.fixture()
      train[key] = replacement
      with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
        self.call(value, train, binding)


class TestReviewAndCompiledBytes(unittest.TestCase):
  def test_review_lock_cannot_be_omitted_or_changed(self):
    reviews = {name: runner.sealed({'reviewer': name, 'role': role, 'approval': 'APPROVED', 'protocol_raw_sha256': 'a' * 64,
                                  'source_sha256': {}, 'implementation_lock_raw_sha256': 'b' * 64})
               for name, role in [('science-review.json', 'SCIENTIFIC_NUMERICAL_CAUSAL'), ('authority-review.json', 'AUTHORITY_PRIVACY_SOURCE_INTEGRITY')]}
    def gate():
      return {'review_receipts': {name: row['receipt_sha256'] for name, row in reviews.items()}}
    runner.verify_reviews(gate(), reviews, 'a' * 64, {}, 'b' * 64)
    for change in (None, 'c' * 64):
      row = reviews['science-review.json']
      row.pop('receipt_sha256')
      if change is None:
        row.pop('implementation_lock_raw_sha256', None)
      else:
        row['implementation_lock_raw_sha256'] = change
      reviews['science-review.json'] = runner.sealed(row)
      with self.assertRaises(ValueError):
        runner.verify_reviews(gate(), reviews, 'a' * 64, {}, 'b' * 64)

  def test_compile_uses_verified_buffer_without_second_read(self):
    import types
    import sys
    name = q.__name__
    import openpilot.tools.cyber_autotune as package
    original = getattr(package, name.rsplit('.', 1)[-1])
    try:
      with patch.object(runner, 'public_locks', return_value=({}, b'p', {}, b'l', {'empirical_hurdle_v4_e2_v2_qualification.py': b'CHECKED_BUFFER = True'})), \
           patch.object(runner.legacy, 'load_exact', return_value={}), patch.object(Path, 'read_bytes', side_effect=AssertionError('second read')):
        modules = runner.frozen_sources()[-1]
        self.assertTrue(modules['empirical_hurdle_v4_e2_v2_qualification'].CHECKED_BUFFER)
    finally:
      sys.modules[name] = original
      setattr(package, name.rsplit('.', 1)[-1], original)
    self.assertIsInstance(original, types.ModuleType)


if __name__ == '__main__':
  unittest.main()
