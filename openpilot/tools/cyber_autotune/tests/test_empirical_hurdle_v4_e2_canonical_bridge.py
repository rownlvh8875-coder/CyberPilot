"""Public synthetic canonical research; no private source or policy admission."""

import ast
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import subprocess
from pathlib import Path
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as frozen_d2
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as frozen_d1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as frozen_v4
from openpilot.tools.cyber_autotune.tests import test_empirical_hurdle_v4_e2_deterministic_numerics_design as oracle

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_bridge'
ROOT = Path(__file__).resolve().parents[4]
SCOPE = 'PUBLIC_SYNTHETIC_CANONICAL_RESEARCH_ONLY'
SEED = 20261019
ROWS_PER_SEGMENT = 520


def bridge():
  if importlib.util.find_spec(MODULE) is None:
    raise AssertionError('CANONICAL_RESEARCH_BRIDGE_NOT_IMPLEMENTED')
  return importlib.import_module(MODULE)


def models(length):
  dim = 2 * length + 3
  norm = {
    'mean': np.zeros(dim),
    'std': np.ones(dim),
    'constant': np.zeros(dim, bool),
    'effective': np.arange(dim, dtype=np.int64),
    'constant_reference': np.zeros(dim),
  }
  static = [i for i in range(dim) if i != dim - 3]
  stage1 = {'normalizer': copy.deepcopy(norm), 'heads': {}}
  for state, positions in ((0, static), (1, list(range(dim)))):
    coefficients = np.zeros(len(positions))
    coefficients[0] = -0.2 if state == 0 else 0.1
    coefficients[positions.index(length)] = 0.8 if state == 0 else 0.7
    stage1['heads'][state] = {'positions': positions, 'coefficients': coefficients}
  beta = np.zeros(dim)
  beta[0], beta[length], beta[-3] = 0.25, 0.75, 0.25
  return stage1, {'normalizer': norm, 'coefficients': beta}


def raw_job(index=0, rows_per_segment=ROWS_PER_SEGMENT):
  candidate, fold = frozen_d1.JOBS[index]
  delay, length = frozen_v4.m.parameters(candidate)
  stage1, stage2 = models(length)
  blocks, current, target = [], [], []
  rng = np.random.default_rng(SEED + index)
  pattern = np.array([0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, -2, -2, -2, -1], np.int64)
  for segment in range(2):
    first = max(delay + length, length + 1) - 1
    size = first + rows_per_segment + 1
    tick = np.resize(np.roll(pattern, segment), size)
    source = {'tick': tick, 'command': rng.normal(0.0, 1.0, size), 'speed': np.full(size, 10.0), 'streak': np.arange(1, size + 1)}
    indices = np.arange(first, first + rows_per_segment, dtype=np.int64)
    blocks.append(frozen_v4.m.features(source, indices, candidate))
    current.append(tick[indices])
    target.append(tick[indices + 1])
  x, c, t = np.concatenate(blocks), np.concatenate(current), np.concatenate(target)
  token = hashlib.sha256(f'PUBLIC_SYNTHETIC:{SEED}:{index}:{rows_per_segment}'.encode()).hexdigest()
  return {
    'candidate': candidate,
    'fold': fold,
    'scope': SCOPE,
    'role': 'TRAIN',
    'source_id': token,
    'anchor': token,
    'row_ids': np.arange(len(x), dtype=np.int64),
    'segment_stops': (rows_per_segment, 2 * rows_per_segment),
    'x': x,
    'p': frozen_v4.probability(np.ascontiguousarray(x), stage1),
    'prior': x[:, -3].astype(np.int64),
    'current': c,
    'target': t,
    'y': t != c,
    'stage1': stage1,
    'stage2': stage2,
  }


def job(index=0, rows_per_segment=ROWS_PER_SEGMENT):
  return bridge().make_job(raw_job(index, rows_per_segment))


def recursive_inputs(j):
  _, length = frozen_v4.m.parameters(j['candidate'])
  past = j['x'][0, length + 1 : 2 * length + 1].astype(np.int64)
  history = np.r_[0, np.cumsum(past)]
  history += j['current'][0] - history[-1]
  return {
    'binding': j['binding'],
    'initial': history[None, :],
    'command': np.linspace(-0.5, 0.5, length + 199)[None, :],
    'speed': np.full((1, 200), 10.0),
    'available_steps': np.array([200], np.int64),
  }


def small_pipeline():
  return bridge().ResearchPipeline([job(i, 16) for i in range(32)])


def through_q1():
  p = small_pipeline()
  p.reconstruct_d0()
  p.cache_potentials()
  p.qualify_q1()
  return p


def through_selection():
  p = through_q1()
  p.select_d1()
  p.select_d2()
  return p


def scalar_tree(values):
  width = 1 << (len(values) - 1).bit_length()
  rows = [list(map(float, r)) for r in values] + [[0.0] * 4 for _ in range(width - len(values))]
  while len(rows) > 1:
    rows = [[a[k] + b[k] for k in range(4)] for a, b in zip(rows[::2], rows[1::2], strict=True)]
  return np.array(rows[0], np.float64)


class TestCanonicalBridgeNumerics(unittest.TestCase):
  def test_module_and_public_scope(self):
    self.assertEqual(bridge().STATUS, 'EXPERIMENTAL_CANONICAL_RESEARCH_NON_WIRED')
    data = raw_job()
    data['scope'] = 'PRIVATE'
    with self.assertRaises(ValueError):
      bridge().make_job(data)

  def test_fixed512_segment_cache_matches_kernel_and_independent_oracle(self):
    for i in (0, 2, 4, 6):
      j = job(i)
      counters = {}
      cache = bridge().potential_cache(j, counters)
      expected = oracle.scalar_reference(j['x'], j['stage2'])
      self.assertTrue(frozen_d2.byte_equal(cache['u'], expected))
      self.assertEqual(counters['canonical_all_row_calls'], 4)
      self.assertTrue(np.array_equal(cache['move_tick'], frozen_v4.m.project(j['current'].astype(float) + expected)))
      f = copy.deepcopy(j)
      f['x'] = np.asfortranarray(f['x'])
      self.assertTrue(frozen_d2.byte_equal(cache['u'], bridge().potential_cache(f, {})['u']))

  def test_d0_exact_combined_ba_ties_and_equality(self):
    out = bridge().reconstruct_d0(np.array([0.0, 0.5, 0.5, 1.0]), np.array([0, 1, 0, 1], bool), {})
    self.assertEqual((out['value'], out['BA_NUM'], out['TN']), (0.5, 6, 2))
    self.assertIs(type(out['BA_NUM']), int)
    self.assertTrue(np.array_equal(bridge().apply_gate(np.array([0.5, 1.0]), np.array([0, 1], np.int64), (0.5,), 'D0'), [False, True]))
    tied = bridge().reconstruct_d0(np.full(4, 0.5), np.array([0, 1, 0, 1], bool), {})
    self.assertEqual(tied['value'], 1.0)

  def test_unapproved_model_objects_rejected_before_copy_hooks(self):
    class UnsupportedModel:
      def __deepcopy__(self, memo):
        raise AssertionError('UNEXPECTED_MODEL_COPY_HOOK')

    raw = raw_job()
    raw['stage2'] = UnsupportedModel()
    with self.assertRaises(ValueError):
      bridge().make_job(raw)

  def test_missing_context_class_and_nonfinite_fail_closed(self):
    data = raw_job()
    data['p'][0] = np.nan
    with self.assertRaises(ValueError):
      bridge().make_job(data)
    data = raw_job()
    mask = data['prior'] == 0
    data['target'][mask] = data['current'][mask]
    data['y'] = data['target'] != data['current']
    with self.assertRaises(ValueError):
      bridge().ResearchPipeline([bridge().make_job(data)] + [job(i) for i in range(1, 32)])

  def test_byte_qualification_rejects_signed_zero_and_one_ulp(self):
    for a, b in ((np.array([0.0]), np.array([-0.0])), (np.array([1.0]), np.array([np.nextafter(1.0, 2.0)]))):
      with self.assertRaisesRegex(ValueError, 'QUALIFICATION'):
        bridge().require_bytes(a, b, 'CANONICAL_Q1_QUALIFICATION_FAILED')
    self.assertEqual(frozen_v4.m.project(np.array([0.25]))[0], frozen_v4.m.project(np.array([np.nextafter(0.25, 1.0)]))[0])

  def test_float32_equal_bytes_are_not_float64_qualification(self):
    with self.assertRaises(ValueError):
      bridge().require_bytes(np.array([1.0], np.float32), np.array([1.0], np.float32), 'CANONICAL_Q1_QUALIFICATION_FAILED')

  def test_signed16_derived_prior_and_full_history_domain(self):
    raw = raw_job()
    raw['prior'][0] = 2**53 + 1
    raw['x'][0, -3] = float(2**53 + 1)
    with self.assertRaisesRegex(ValueError, 'HISTORY_DOMAIN'):
      bridge().make_job(raw)
    raw = raw_job(2)
    raw['x'][0, 6] = 0.5
    with self.assertRaisesRegex(ValueError, 'HISTORY_DOMAIN'):
      bridge().make_job(raw)
    raw = raw_job()
    raw['x'][0, -3] = float(2**53 + 1)
    with self.assertRaisesRegex(ValueError, 'HISTORY_DOMAIN'):
      bridge().infer(raw['x'], raw['current'], raw['stage1'], raw['stage2'], (1.0,), 'D0', {}, scope=SCOPE, p_move=raw['p'])

  def test_full_signed16_prior_boundary_is_valid(self):
    stage1, stage2 = models(1)
    x = np.array([[1.0, 0.0, 65535.0, 32767.0, 1.0], [1.0, 0.0, -65535.0, -32768.0, 1.0]])
    current = np.array([32767, -32768], np.int64)
    counters = {}
    result = bridge().infer(x, current, stage1, stage2, (1.0,), 'D0', counters, scope=SCOPE)
    self.assertTrue(np.array_equal(result['projected'], current))
    self.assertTrue(np.all(result['delta'].view(np.uint64) == 0))
    self.assertEqual(counters.get('canonical_branch_stage2_calls', 0), 0)

  def test_source_model_normalizer_and_order_conflicts(self):
    original = job()
    cache = bridge().potential_cache(original, {})
    for change in ('source', 'anchor', 'model', 'normalizer', 'order'):
      changed = copy.deepcopy(original)
      if change == 'source':
        changed['source_id'] = '0' * 64
      elif change == 'anchor':
        changed['anchor'] = '1' * 64
      elif change == 'model':
        changed['stage2']['coefficients'][0] += 1.0
      elif change == 'normalizer':
        changed['stage2']['normalizer']['mean'][1] += 1.0
      else:
        changed['row_ids'][[0, 1]] = changed['row_ids'][[1, 0]]
      with self.subTest(change=change), self.assertRaises(ValueError):
        bridge().qualify_selected(changed, cache, changed['p'] > 0.5, 'Q1', {})

  def test_empty_gate_explicit_noop_and_all_move_actual_call(self):
    j = job()
    cache = bridge().potential_cache(j, {})
    counters = {}
    result = bridge().qualify_selected(j, cache, np.zeros(len(j['p']), bool), 'Q1', counters)
    self.assertEqual(result['mode'], 'EXPLICIT_EMPTY_GATE_NOOP')
    self.assertEqual(result['selected_stage2_calls'], 0)
    self.assertEqual(counters.get('Q1_selected_calls', 0), 0)
    result = bridge().qualify_selected(j, cache, np.ones(len(j['p']), bool), 'Q3', counters)
    self.assertEqual(result['selected_stage2_calls'], 1)
    self.assertEqual(counters['Q3_selected_calls'], 1)

  def test_stage2_nonfinite_projection_and_subnormal(self):
    raw = raw_job()
    raw['stage2']['coefficients'][0] = np.inf
    with self.assertRaises(ValueError):
      bridge().potential_cache(bridge().make_job(raw), {})
    raw = raw_job()
    raw['stage2']['coefficients'][0] = 40000.0
    with self.assertRaises(ValueError):
      bridge().potential_cache(bridge().make_job(raw), {})
    raw = raw_job()
    raw['stage2']['coefficients'][:] = 0.0
    raw['stage2']['coefficients'][0] = float.fromhex('0x0.0000000000001p-1022')
    j = bridge().make_job(raw)
    self.assertTrue(np.all(bridge().potential_cache(j, {})['u'].view(np.uint64) == 1))

  def test_no_readers_fitting_or_global_monkeypatch(self):
    tree = ast.parse(inspect.getsource(bridge()))
    for node in ast.walk(tree):
      if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
        self.assertNotIn(name, ('open', 'load', 'loadtxt', 'glob', 'rglob', 'walk', 'fit', 'fit_stage2', 'normalizer', 'run_execution', 'setattr', 'allclose'))
    self.assertNotIn('target', inspect.signature(bridge().infer).parameters)
    self.assertNotIn('observed', inspect.signature(bridge().recursive).parameters)


class TestCanonicalBridgeBarriers(unittest.TestCase):
  def test_exact32_manifest_and_q1_precedes_selection(self):
    with self.assertRaises(ValueError):
      bridge().ResearchPipeline([job()])
    p = small_pipeline()
    with self.assertRaisesRegex(ValueError, 'PHASE'):
      p.select_d2()
    self.assertEqual(p.phase, 'FAILED')
    self.assertEqual(p.counters.get('D2_context_decision_selection_calls', 0), 0)

  def test_q1_corruption_blocks_all_d2(self):
    p = small_pipeline()
    p.reconstruct_d0()
    p.cache_potentials()
    p.caches[2]['u'][0] = np.nextafter(p.caches[2]['u'][0], np.inf)
    with self.assertRaises(ValueError):
      p.qualify_q1()
    self.assertEqual(p.phase, 'FAILED')
    self.assertEqual(p.counters.get('D2_context_decision_selection_calls', 0), 0)

  def test_final_winner_cannot_change_between_selection_and_q3(self):
    p = through_selection()
    old = p.policies[0]['D2']
    p.policies[0]['D2'] = (1.0 if old[0] != 1.0 else 0.0, old[1])
    with self.assertRaisesRegex(ValueError, 'WINNER'):
      p.qualify_q3()
    self.assertEqual(p.phase, 'FAILED')
    self.assertEqual(p.counters['D2_context_decision_selection_calls'], 64)

  def test_d0_guard_reference_cannot_be_replaced_after_q1(self):
    p = through_q1()
    old = p.policies[0]['D0'][0]
    p.policies[0]['D0'] = (1.0 if old != 1.0 else 0.0,)
    with self.assertRaisesRegex(ValueError, 'REFERENCE'):
      p.select_d1()
    self.assertEqual(p.phase, 'FAILED')

  def test_recursive_input_binding_must_match_job(self):
    p = through_selection()
    p.qualify_q3()
    p.compare_one_step()
    supplied = [recursive_inputs(j) for j in p.jobs]
    supplied[0]['binding'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'RECURSIVE_SOURCE'):
      p.smoke_recursive(supplied)
    self.assertEqual(p.phase, 'FAILED')

  def test_selector_performs_no_stage2_reinference(self):
    p = through_q1()
    p.select_d1()
    before = {k: v for k, v in p.counters.items() if 'canonical_' in k}
    p.select_d2()
    self.assertEqual(before, {k: v for k, v in p.counters.items() if 'canonical_' in k})
    self.assertEqual(p.counters['D2_context_decision_selection_calls'], 64)

  def test_q3_failure_blocks_readiness_and_reselection(self):
    p = through_selection()
    p.caches[0]['u'][0] = np.nextafter(p.caches[0]['u'][0], np.inf)
    with self.assertRaises(ValueError):
      p.qualify_q3()
    self.assertEqual(p.phase, 'FAILED')
    with self.assertRaises(ValueError):
      p.select_d2()
    with self.assertRaises(ValueError):
      p.summary()
    self.assertEqual(p.counters['D2_context_decision_selection_calls'], 64)

  def test_d1_uses_only_context_ba_and_d2_matches_independent_small_sweep(self):
    p = through_selection()
    for j, cache, details, policies in zip(p.jobs, p.caches, p.details, p.policies, strict=True):
      for state, name in enumerate(frozen_d2.CONTEXTS):
        mask = (j['prior'] != 0) == state
        scores, y = j['p'][mask], j['y'][mask]
        positive, negative = int(y.sum()), int((~y).sum())
        candidates = sorted({0.0, 1.0, *map(float, scores)})
        ba = []
        keys = []
        d0_gate = scores > policies['D0'][0]
        actual = (j['target'][mask] - j['current'][mask]).astype(float)
        u, c, t, movement = cache['u'][mask], j['current'][mask], j['target'][mask], cache['move_tick'][mask]

        def measures(gate, u=u, actual=actual, y=y, movement=movement, c=c, t=t):
          delta = np.where(gate, u, 0.0)
          residual = delta - actual
          leaves = np.column_stack((residual * residual, np.abs(residual), np.where(y, residual * residual, 0.0), np.where(y, np.abs(residual), 0.0)))
          loss = scalar_tree(leaves)
          harm = int(np.count_nonzero(gate & ~y & (movement != c)))
          tp = int(np.count_nonzero(gate & y))
          predicted = np.where(gate, movement, c)
          gain = int(np.count_nonzero(predicted == t)) - int(np.count_nonzero(c == t))
          return loss, harm, tp, gain

        old_loss, old_harm, old_tp, _ = measures(d0_gate)
        for value in candidates:
          gate = scores > value
          tp, tn = int(np.count_nonzero(gate & y)), int(np.count_nonzero(~gate & ~y))
          ba.append((tp * negative + tn * positive, tn, value))
          loss, harm, tp, gain = measures(gate)
          if tp >= old_tp and loss[2] <= old_loss[2] and loss[3] <= old_loss[3] and harm <= old_harm:
            keys.append((gain, -float(loss[0]), -float(loss[1]), -harm, value))
        self.assertEqual(policies['D1'][state], max(ba)[2])
        self.assertEqual(policies['D2'][state], max(keys)[4])
        self.assertTrue(all(details['D2'][name]['guards'].values()))
        self.assertTrue(details['D2'][name]['witness_verified'])
        self.assertEqual(details['D2'][name]['D0_reference']['TRUE_MOVE_SSE'], float(old_loss[2]))


class TestCanonicalBridgePipeline(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.pipeline = bridge().ResearchPipeline([job(i) for i in range(32)])
    cls.result = cls.pipeline.run([recursive_inputs(j) for j in cls.pipeline.jobs])

  def test_readiness_rechecks_source_cache_and_final_winner(self):
    for change in ('source', 'cache', 'winner'):
      p = copy.deepcopy(self.pipeline)
      if change == 'source':
        p.jobs[0]['source_id'] = '0' * 64
      elif change == 'cache':
        p.caches[0]['u'][0] = np.nextafter(p.caches[0]['u'][0], np.inf)
      else:
        old = p.policies[0]['D2']
        p.policies[0]['D2'] = (1.0 if old[0] != 1.0 else 0.0, old[1])
      with self.subTest(change=change), self.assertRaises(ValueError):
        p.summary()

  def test_all32_64decisions_q1_q3_and_no_admission(self):
    r = self.result
    self.assertEqual((r['Q1_jobs'], r['D2_decisions'], r['Q3_jobs']), (32, 64, 32))
    self.assertEqual(r['scope'], SCOPE)
    self.assertIsNone(r['selected_candidate'])
    self.assertIsNone(r['selected_policy'])
    self.assertFalse(r['empirical_acceptance_executed'])
    self.assertEqual(r['Q2_private_calls'], 0)

  def test_one_step_shared_scores_cache_and_original_order(self):
    p = self.pipeline
    for j, cache, arms, policy in zip(p.jobs, p.caches, p.one_steps, p.policies, strict=True):
      for name in ('D0', 'D1', 'D2'):
        out = arms[name]
        self.assertTrue(frozen_d2.byte_equal(out['p_move'], j['p']))
        self.assertTrue(np.array_equal(out['row_ids'], j['row_ids']))
        gate = bridge().apply_gate(j['p'], j['prior'], policy[name], name)
        self.assertTrue(np.array_equal(out['gate'], gate))
        self.assertTrue(frozen_d2.byte_equal(out['delta'], np.where(gate, cache['u'], 0.0)))
        self.assertTrue(np.array_equal(out['projected'], np.where(gate, cache['move_tick'], j['current'])))
        self.assertTrue(np.array_equal(out['realized_movement'], out['projected'] != j['current']))
        self.assertTrue(frozen_d2.byte_equal(out['loss'], scalar_tree(frozen_d2.leaf_losses(out['delta'], (j['target'] - j['current']).astype(float), j['y']))))

  def test_all_horizons_three_arms_reset_and_projected_context(self):
    self.assertEqual(len(self.pipeline.recursive_results), 32)
    for result in self.pipeline.recursive_results:
      for arm in ('D0', 'D1', 'D2'):
        for horizon in (25, 50, 100, 200):
          row = result[arm][horizon]
          self.assertEqual(row['path'].shape, (1, horizon + 1))
          self.assertTrue(np.array_equal(row['context'][:, 1:], np.diff(row['path'], axis=1)[:, :-1] != 0))
          self.assertTrue(np.array_equal(row['path'], result[arm][200]['path'][:, : horizon + 1]))


class TestCanonicalBridgeCausality(unittest.TestCase):
  def args(self, length=5, horizon=25):
    stage1, stage2 = models(length)
    for state, head in stage1['heads'].items():
      head['coefficients'][:] = 0.0
      head['coefficients'][0] = np.log(3.0) if state else -np.log(3.0)
    stage2['coefficients'][:] = 0.0
    stage2['coefficients'][0] = 0.25
    initial = np.r_[0, np.cumsum(np.resize([1, 1, 0, 1, 1], length))][None, :].astype(np.int64)
    return {
      'initial': initial,
      'command': np.zeros((1, length + horizon - 1)),
      'speed': np.ones((1, horizon)),
      'candidate': f'HRI_D00_L{length:02}',
      'stage1': stage1,
      'stage2': stage2,
      'decisions': (0.5, 0.5),
      'arm': 'D2',
      'horizon': horizon,
      'available_steps': np.array([horizon], np.int64),
      'counters': {},
      'scope': SCOPE,
    }

  def test_gate_move_projected_hold_switches_context_and_entire_history(self):
    args = self.args()
    r = bridge().recursive(**args)
    self.assertTrue(r['gate'][0, 0])
    self.assertFalse(r['gate'][0, 1])
    self.assertTrue(r['context'][0, 0])
    self.assertFalse(r['context'][0, 1])
    self.assertTrue(np.array_equal(r['history_before'][0, 1], [1, 0, 1, 1, 0]))
    self.assertTrue(np.all(r['path'] == args['initial'][0, -1]))

  def test_segment_boundary_shape_and_scope_fail_closed(self):
    for change in ('boundary', 'command', 'scope'):
      a = self.args()
      if change == 'boundary':
        a['available_steps'][0] -= 1
      elif change == 'command':
        a['command'] = a['command'][:, :-1]
      else:
        a['scope'] = 'PRIVATE'
      with self.subTest(change=change), self.assertRaises(ValueError):
        bridge().recursive(**a)

  def test_exogenous_command_indexing_and_no_truth_argument(self):
    a = self.args(length=1)
    a['stage1']['heads'][0]['coefficients'][0] = np.log(3.0)
    a['stage2']['coefficients'][:] = 0.0
    a['stage2']['coefficients'][1] = 1.0
    a['command'][0] = np.arange(25) / 16.0
    r = bridge().recursive(**a)
    self.assertTrue(frozen_d2.byte_equal(r['delta'][0], a['command'][0]))
    self.assertTrue(np.array_equal(bridge().path_moved(np.array([[0, 0, 0], [0, 1, 0]], np.int64)), [False, True]))


class TestCanonicalBridgeContract(unittest.TestCase):
  def test_existing61_and_io_import_guards_are_preserved(self):
    from tools.cyberpilot import run_numerical_offline as runner

    required = (
      'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_stage2',
      'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_deterministic_numerics_design',
      'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_numerical_diagnostic.TestNumericalDiagnostic',
    )
    self.assertEqual(runner.SUITES[:3], required)
    self.assertEqual(runner.SUITES[3:], (__name__,))
    old = subprocess.check_output(['git', 'show', '99cd6aa62d00bfb2a27b8d5fcf08cf06cdb129cb:tools/cyberpilot/run_numerical_offline.py'], cwd=ROOT).decode()
    old_tree = ast.parse(old)
    for name in ('PublicImports', 'public_boundary'):
      original = next(n for n in old_tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name)
      self.assertEqual(ast.get_source_segment(old, original), inspect.getsource(getattr(runner, name)).rstrip())
    previous = subprocess.check_output(
      ['git', 'show', '99cd6aa62d00bfb2a27b8d5fcf08cf06cdb129cb:openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_stage2.py'], cwd=ROOT
    ).decode()
    current = (ROOT / 'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_stage2.py').read_text()

    def methods(text):
      return [n.name for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]

    self.assertEqual(methods(current), methods(previous))
    self.assertEqual(len(methods(current)), 26)

  def test_new_contract_lock_and_no_historical_mutation(self):
    public = ROOT / 'docs/cyberpilot/changes'
    contract_path = public / 'empirical-hurdle-stage1-v4-e2-canonical-source-guard-contract.json'
    lock_path = public / 'empirical-hurdle-stage1-v4-e2-canonical-bridge-lock.json'
    self.assertTrue(contract_path.is_file())
    self.assertTrue(lock_path.is_file())
    for path in (contract_path, lock_path):
      d = json.loads(path.read_text())
      seal = d.pop('receipt_sha256')
      self.assertEqual(seal, hashlib.sha256(json.dumps(d, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest())
      for mapping in ('source_sha256', 'frozen_source_sha256'):
        for name, digest in d.get(mapping, {}).items():
          raw = (ROOT / name).read_bytes()
          extensions = {
            '.github/workflows/cyberpilot-numerical-offline.yaml',
            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_bridge.py',
          }
          if path == lock_path and name in extensions:
            raw = subprocess.check_output(['git', 'show', 'df543777f71377938861f53ea2d369bd6324d2fe:' + name], cwd=ROOT)
          self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
      for name, identity in d.get('public_identity', {}).items():
        raw = (public / name).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), identity['raw_sha256'])
        record = json.loads(raw)
        self.assertEqual(record.pop('receipt_sha256'), identity['receipt_sha256'])
        self.assertEqual(
          hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(), identity['receipt_sha256']
        )
    d = json.loads(contract_path.read_text())
    self.assertEqual(d['version'], 'V4_E2_CANONICAL_D0_D1_D2_RESEARCH_CONTRACT_V1')
    self.assertEqual(d['guard_reference'], 'NEW_CANONICAL_D0_TRAIN_REFERENCE')
    self.assertFalse(d['authority']['private_access'])
    self.assertFalse(d['authority']['E2_execution'])
    self.assertEqual(d['acceptance']['clauses'], 32)
    self.assertEqual(d['acceptance']['epsilon'], 0)
    self.assertEqual(d['acceptance']['support'], 201)
    self.assertEqual(len(d['validation_domains']), 22)
    previous = json.loads((public / 'empirical-hurdle-stage1-v4-d2-evaluation-contract.json').read_text())
    self.assertEqual(d['validation_domains'], previous['validation_domains'])
    self.assertEqual(d['acceptance']['families'], [5, 3, 24])
    self.assertFalse(d['Stage1_batch_independence_claimed'])
