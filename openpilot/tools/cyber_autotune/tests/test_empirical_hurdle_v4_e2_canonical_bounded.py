"""Independent eager reference and bounded lifetime regression."""

import gc
import tempfile
from pathlib import Path
import unittest
import weakref
import numpy as np


class TestBounded(unittest.TestCase):
  def test_one_materialization_released_and_source_order_unchanged(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from tools.cyberpilot.canonical_readiness_fixture import job
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

    p = provider()
    with p.features(0) as data:
      ref = weakref.ref(data['x'])
      self.assertEqual(data['binding'], b._hash(job(0, 'TRAIN')[0]))
      self.assertEqual(data['x'].tobytes(), job(0, 'TRAIN')[0]['x'].tobytes())
    gc.collect()
    self.assertIsNone(ref())
    self.assertEqual(p.lifetime.snapshot()['live_counts'].get('feature', 0), 0)
    self.assertEqual(p.lifetime.snapshot()['peak_counts']['feature'], 1)

  def test_retained_feature_alias_blocks_next_job(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider

    p = provider()
    with self.assertRaises(ValueError):
      with p.features(0) as data:
        alias = data['x']
    del alias
    with self.assertRaises(ValueError):
      with p.features(1):
        pass

  def test_owner_base_and_immutable_bytes_aliases_block_retirement(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_resources as mem
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_bounded_inputs import immutable

    for raw_bytes in (False, True):
      life = mem.Lifetime()
      a = immutable(np.arange(8, dtype=np.int64))
      token = life.add('train_vectors', a)
      alias = a.base.base if raw_bytes else a.base
      del a
      with self.assertRaisesRegex(ValueError, 'RETAINED'):
        life.release(token)
      del alias
      life.release(token)
      self.assertEqual(life.snapshot()['live_owner_bytes'], 0)
    life = mem.Lifetime()
    owner = immutable(np.arange(8, dtype=np.int64))
    retained = life.add('indices_models', owner)
    view = owner[1:3]
    temporary = life.add('horizon', view)
    del view
    life.release(temporary)
    self.assertGreater(life.snapshot()['live_owner_bytes'], 0)
    del owner
    life.release(retained)

  def test_memory_budget_below_live_owner_is_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_resources import Lifetime

    life = Lifetime(byte_limit=8)
    with self.assertRaises(ValueError):
      life.add('feature', np.zeros(2, np.float64))

  def test_no_private_run(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    with self.assertRaisesRegex(ValueError, 'PRIVATE_EXECUTION_NOT_AUTHORIZED'):
      q.execute_private(object())

  def test_reference_train_result_complete_bytes_and_lifetimes(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from tools.cyberpilot.canonical_readiness_fixture import provider as eager
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as old
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    binding = old.synthetic_binding('1' * 40)
    with tempfile.TemporaryDirectory() as tmp:
      a, b = Path(tmp) / 'eager', Path(tmp) / 'bounded'
      original = old.run_synthetic(eager(), a, binding)
      result = q.run_synthetic(provider(), b, binding)
      for name in ('train.json', 'result.json', 'complete.json'):
        self.assertEqual((a / name).read_bytes(), (b / name).read_bytes(), name)
      self.assertEqual(result['coverage'], {'D0': 32, 'D1': 64, 'D2': 64, 'Q1': 32, 'Q3': 32, 'DEV_jobs': 32})
      self.assertEqual(result['completion_digest'], original['completion_digest'])
      census = result['lifetime']
      for kind in ('feature', 'selected', 'horizon', 'trace', 'cache', 'train_vectors'):
        self.assertEqual(census['live_counts'].get(kind, 0), 0)
        self.assertLessEqual(census['peak_counts'][kind], 32 if kind in ('cache', 'train_vectors') else 1)
      self.assertEqual(old.verify_synthetic(b, binding, result['completion_digest'])['scientific_recomputations'], 0)
      envelope = {'scope': 'PUBLIC_SYNTHETIC_BOUNDED_ONLY', 'reference_binding': binding, 'private_authority': False}
      digest = q.seal_execution(b, envelope, result)
      from unittest.mock import patch

      with (
        patch.object(q.old, 'public_check', side_effect=AssertionError('source reread')),
        patch.object(q.b, 'infer', side_effect=AssertionError('inference')),
      ):
        self.assertEqual(q.verify_bounded(b, envelope, digest)['scientific_recomputations'], 0)
      with self.assertRaises(ValueError):
        q.verify_bounded(b, envelope, 'f' * 64)
      (b / 'complete.json').write_bytes(b'{}')
      with self.assertRaises(ValueError):
        q.verify_bounded(b, envelope, digest)

  def test_static_resource_graph_is_not_a_capacity_grant(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_resources as q

    value = q.resource_contract()
    self.assertEqual(value['runtime_status'], 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN')
    self.assertFalse(value['private_execution_ready'])
    self.assertEqual(value['worst_case']['recursive_row_steps'], 32 * 3 * 336941 * 375)
    self.assertEqual(value['lease_limits']['feature'], 1)
    for phase, buffers in value['phase_buffers'].items():
      self.assertEqual(value['phase_totals'][phase], sum(value['retained'].values()) + sum(buffers.values()))
    with self.assertRaises(ValueError):
      q.Lifetime(byte_limit=q.AS_CAP + 1)

  def test_final_public_source_and_capability_resource_contracts(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    lock = q.public_check()
    self.assertFalse(lock['private_execution_authorized'])
    cap = q.out.checked(q.out.decode((q.old.PUBLIC / 'empirical-hurdle-stage1-v4-e2-canonical-exact-input-capability-v1.json').read_bytes()))
    self.assertEqual(cap['actual_binding'], q.inputs.PENDING)
    resource = q.out.checked(q.out.decode((q.old.PUBLIC / 'empirical-hurdle-stage1-v4-e2-canonical-bounded-resource-contract.json').read_bytes()))
    self.assertEqual(resource['calculation'], q.resources.resource_contract())

  def test_additive_workflow_retains_all120_and_separate_full_scope(self):
    import yaml
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    path = q.old.ROOT / '.github/workflows/cyberpilot-canonical-bounded.yaml'
    flow = yaml.safe_load(path.read_text())
    steps = flow['jobs']['bounded']['steps']
    runs = '\n'.join(step.get('run', '') for step in steps)
    self.assertIn('run_numerical_offline.py', runs)
    self.assertIn('run_canonical_readiness.py', runs)
    self.assertIn('run_canonical_bounded.py', runs)
    self.assertNotIn('git lfs pull', runs)
    self.assertNotIn('tools/op.sh setup', runs)
    checkout = next(step for step in steps if step.get('uses', '').startswith('actions/checkout@'))
    self.assertIs(checkout['with']['lfs'], False)
    self.assertIs(checkout['with']['submodules'], False)

  def test_admission_couples_train_metadata_model_identity_and_source(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    for field in ('stage2', 'fold', 'anchor', 'source_id', 'binding', 'stage1', 'current'):
      p = provider()
      train = p._specs['TRAIN']
      dev = p._specs['DEV']
      meta = train[0]['train_meta']
      if field == 'stage2':
        wrong = {**train[0]['stage2'], 'coefficients': train[0]['stage2']['coefficients'] + 0.125}
        train[0]['stage2'] = q.immutable(wrong)
        dev[0]['stage2'] = q.immutable(wrong)
      elif field == 'stage1':
        meta[field] = dev[0]['stage1']
      elif field == 'fold':
        meta[field] = 'FOLD_B'
      elif field == 'current':
        meta[field] = q.immutable(meta[field] + 1)
      else:
        meta[field] = 'f' * 64
      with self.subTest(field=field), self.assertRaises(ValueError):
        q.BoundedSyntheticProvider(train, dev)

  def test_fresh_rebound_target_cannot_contradict_source(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    p = provider()
    train = p._specs['TRAIN']
    dev = p._specs['DEV']
    s = train[0]
    meta = s['train_meta']
    target = meta['target'].copy()
    target[0] += 1
    meta['target'] = q.immutable(target)
    meta['y'] = q.immutable(target != meta['current'])
    x = q.assemble(s['parts'], s['candidate'])
    identity = q.digest({k: v for k, v in {**meta, 'x': x}.items() if k != 'binding'})
    meta['binding'] = identity
    s['expected_binding'] = identity
    with self.assertRaisesRegex(ValueError, 'TRAIN_SOURCE_JOIN'):
      q.BoundedSyntheticProvider(train, dev)

  def test_retired_train_model_owner_cannot_be_replaced(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    p = provider()
    with tempfile.TemporaryDirectory() as tmp:
      with q.out.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, q.old.synthetic_binding('1' * 40))
        run.train()
        p.unlock(run.train_digest, store.read('train.json', run.train_digest))
        p.retire_train()
        p._specs['TRAIN'][0]['stage2'] = q.inputs.immutable(p._specs['TRAIN'][0]['stage2'])
        with self.assertRaises(ValueError):
          with p.dev_job(0, run.train_digest):
            pass

  def test_dev_unlock_requires_durable_complete_train_proof(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider

    p = provider()
    with self.assertRaises(ValueError):
      p.unlock('a' * 64)

  def test_supported_multichunk_horizons_match_original_aggregation(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from tools.cyberpilot.canonical_readiness_fixture import job
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as old

    p = provider(n=1024, rollout_n=513)
    binding = old.synthetic_binding('2' * 40)
    with tempfile.TemporaryDirectory() as tmp:
      with old.output.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, binding)
        run.train()
        loaded = store.read('train.json', run.train_digest)
        p.unlock(run.train_digest, loaded)
        policies = {arm: tuple(run.train_record['jobs'][0]['decisions'][arm]) for arm in q.b.ARMS}
        ref_data, ref_paths = job(0, 'DEV', 1024, 513)
        expected = old.evaluation.evaluate(ref_data, ref_paths, policies, old.public_check()[0]['acceptance']['clauses'], {})
        with p.dev_job(0, run.train_digest) as data:
          with p.features(0, 'DEV') as active:
            arms = q.one_step(active, policies, {})
          for arm in q.b.ARMS:
            for h in q.b.HORIZONS:
              arms[arm]['rollout'][str(h)] = q.rollout(p, 0, data, policies[arm], arm, h, {})
            arms[arm]['gate'] = q.metrics.e1.gates.fold_gate(arms[arm], old.public_check()[0]['acceptance']['clauses'])
          self.assertEqual(old.output.canonical(arms), old.output.canonical(expected['arms']))
        self.assertEqual(p.lifetime.snapshot()['live_counts'].get('dev_vectors', 0), 0)
        self.assertEqual(p.lifetime.snapshot()['live_counts'].get('dev_score', 0), 0)

  def test_horizon_specific_tail_anchors_are_not_h200_prefix(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as old

    rows = {h: np.array([0, 416 - h], np.int64) for h in q.b.HORIZONS}
    p = provider(n=416, horizon_rows=rows)
    with tempfile.TemporaryDirectory() as tmp:
      with old.output.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, old.synthetic_binding('1' * 40))
        run.train()
        p.unlock(run.train_digest, store.read('train.json', run.train_digest))
        with p.dev_job(0, run.train_digest):
          for h in q.b.HORIZONS:
            with p.horizon_chunk(0, h, 0) as chunk:
              self.assertEqual(chunk['row_ids'].tolist(), [0, 416 - h])
              self.assertEqual(chunk['available_steps'].tolist(), [200, h])
              self.assertEqual(chunk['observed'].shape, (2, h + 1))

  def test_duplicate_source_parts_and_inconsistent_resource_scenario(self):
    from tools.cyberpilot.canonical_bounded_fixture import spec
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_resources as mem

    train = [spec(i, 'TRAIN') for i in range(32)]
    dev = [spec(i, 'DEV') for i in range(32)]
    train[0]['parts'] = train[0]['parts'] * 2
    with self.assertRaisesRegex(ValueError, 'DUPLICATE_SOURCE'):
      q.BoundedSyntheticProvider(train, dev)
    with self.assertRaises(ValueError):
      mem.resource_contract(n=336941, p=93, source_rows=1)

  def test_multisegment_explicit_populations_keep_global512_and_all_metrics(self):
    from tools.cyberpilot.canonical_bounded_fixture import segmented_provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as old

    p = segmented_provider()
    binding = old.synthetic_binding('1' * 40)
    with tempfile.TemporaryDirectory() as tmp:
      with old.output.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, binding)
        run.train()
        p.unlock(run.train_digest, store.read('train.json', run.train_digest))
        policies = {arm: tuple(run.train_record['jobs'][0]['decisions'][arm]) for arm in q.b.ARMS}
        reference, paths = eager_job(p._specs['DEV'][0])
        self.assertEqual([len(paths['horizons'][h]['row_ids']) for h in q.b.HORIZONS], [784, 734, 634, 434])
        expected = old.evaluation.evaluate(reference, paths, policies, old.public_check()[0]['acceptance']['clauses'], {})
        with p.dev_job(0, run.train_digest) as data:
          with p.features(0, 'DEV') as active:
            arms = q.one_step(active, policies, {})
          for arm in q.b.ARMS:
            for h in q.b.HORIZONS:
              arms[arm]['rollout'][str(h)] = q.rollout(p, 0, data, policies[arm], arm, h, {})
            arms[arm]['gate'] = q.metrics.e1.gates.fold_gate(arms[arm], old.public_check()[0]['acceptance']['clauses'])
          self.assertEqual(old.output.canonical(arms), old.output.canonical(expected['arms']))
          self.assertTrue(all(c['evaluated'] for arm in arms.values() for c in arm['gate']['clauses']))

  def test_q1_corruption_blocks_selection_and_allocation_failure_is_terminal(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q
    from unittest.mock import patch

    p = provider()
    with patch.object(q.inputs, 'assemble', side_effect=MemoryError('synthetic allocation failure')):
      with self.assertRaises(MemoryError):
        with p.features(0):
          pass
    self.assertTrue(p.failed)
    with self.assertRaises(ValueError):
      with p.features(1):
        pass
    p = provider()
    with tempfile.TemporaryDirectory() as tmp:
      with q.out.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, q.old.synthetic_binding('1' * 40))
        run.pipeline = q.BoundedTrainPipeline(p)
        run.advance(q.Phase.PREFLIGHT, q.Phase.D0, run.pipeline.reconstruct_d0)
        run.advance(q.Phase.D0, q.Phase.CACHE, run.pipeline.cache_potentials)
        run.pipeline.caches[0]['u'][0] += 1.0
        with self.assertRaises(ValueError):
          run.advance(q.Phase.CACHE, q.Phase.Q1, run.pipeline.qualify_q1)
        self.assertEqual(run.phase, q.Phase.FAILED)
        self.assertEqual(run.pipeline.counters.get('D2_context_decision_selection_calls', 0), 0)
        with self.assertRaises(ValueError):
          run.evaluate(q.old.public_check()[0]['acceptance']['clauses'])

  def test_signed_zero_selected_comparison_is_not_projection_tolerance(self):
    from tools.cyberpilot.canonical_readiness_fixture import job
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    j = job(0, 'TRAIN')[0]
    j['stage2']['coefficients'][:] = 0.0
    j = q.b.make_job(j)
    cache = q.b.potential_cache(j, {})
    cache['u'][0] = -0.0
    cache['cache_sha256'] = q.b._hash((cache['u'], cache['move_tick']))
    life = q.resources.Lifetime()
    with self.assertRaisesRegex(ValueError, 'CANONICAL_Q1_QUALIFICATION_FAILED'):
      q.qualify(j, cache, np.ones(len(j['p']), bool), 'Q1', {}, life)
    self.assertEqual(life.snapshot()['live_counts'].get('selected', 0), 0)

  def test_sealed_d2_mutation_cannot_reselect_or_enter_dev(self):
    from tools.cyberpilot.canonical_bounded_fixture import provider
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q

    p = provider()
    with tempfile.TemporaryDirectory() as tmp:
      with q.out.Store(Path(tmp) / 'run') as store:
        run = q.BoundedRun(p, store, q.old.synthetic_binding('1' * 40))
        run.train()
        count = run.pipeline.counters['D2_context_decision_selection_calls']
        run.pipeline.policies[0]['D2'] = (0.123, 0.456)
        with self.assertRaises(ValueError):
          run.evaluate(q.old.public_check()[0]['acceptance']['clauses'])
        self.assertEqual(run.phase, q.Phase.FAILED)
        self.assertEqual(run.pipeline.counters['D2_context_decision_selection_calls'], count)
        self.assertIsNone(p._dev_key)


def eager_job(spec):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
  from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_inputs import output_anchor

  x = np.concatenate([b.original.m.features(block.arrays, ix, spec['candidate']) for block, ix in spec['parts']])
  current = np.concatenate([block.arrays['tick'][ix] for block, ix in spec['parts']])
  target = np.concatenate([block.arrays['tick'][ix + 1] for block, ix in spec['parts']])
  prior = np.concatenate([block.arrays['tick'][ix] - block.arrays['tick'][ix - 1] for block, ix in spec['parts']])
  stops = np.cumsum([len(ix) for _, ix in spec['parts']])
  n = len(current)
  data = {k: spec[k] for k in ('candidate', 'fold', 'role', 'source_id', 'anchor', 'stage1', 'stage2')}
  data.update(
    scope=b.SCOPE,
    row_ids=np.arange(n, dtype=np.int64),
    segment_stops=tuple(stops.tolist()),
    x=x,
    p=b.original.probability(np.ascontiguousarray(x), spec['stage1']),
    current=current,
    target=target,
    prior=prior,
    y=target != current,
  )
  assert b._hash(data) == spec['expected_binding']
  paths = {'binding': b._hash(data), 'horizons': {}}
  delay, length = b.original.m.parameters(spec['candidate'])
  for h, rows in spec['horizon_rows'].items():
    segments = np.searchsorted(stops, rows, side='right').astype(np.int64)
    initial, command, speed, observed = [], [], [], []
    for i, (block, ix) in enumerate(spec['parts']):
      positions = rows[segments == i] - (0 if i == 0 else stops[i - 1])
      origin = ix[positions]
      initial.append(block.arrays['tick'][origin[:, None] + np.arange(-length, 1)])
      command.append(block.arrays['command'][origin[:, None] + np.arange(-delay - length + 1, h - delay)])
      speed.append(block.arrays['speed'][origin[:, None] + np.arange(h)])
      observed.append(block.arrays['tick'][origin[:, None] + np.arange(h + 1)])
    paths['horizons'][h] = {
      'initial': np.concatenate(initial),
      'command': np.concatenate(command),
      'speed': np.concatenate(speed),
      'observed': np.concatenate(observed),
      'row_ids': rows,
      'segment_ids': segments,
      'available_steps': np.minimum(200, stops[segments] - rows).astype(np.int64),
      'anchor': output_anchor(spec['anchor'], h, rows, segments),
    }
  return data, paths
