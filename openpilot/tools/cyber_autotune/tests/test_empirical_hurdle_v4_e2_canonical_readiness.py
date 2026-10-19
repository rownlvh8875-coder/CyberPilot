"""Public synthetic tests: real role gates, arithmetic, durable I/O and subprocesses."""

import importlib
import unittest


def module(name):
  try:
    return importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_' + name)
  except ModuleNotFoundError as exc:
    raise AssertionError('CANONICAL_READINESS_NOT_IMPLEMENTED') from exc


class TestReadiness(unittest.TestCase):
  def test_private_entrypoint_blocks_before_any_path_or_grant(self):
    execution = module('execution')
    with self.assertRaisesRegex(ValueError, 'CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
      execution.execute_private({'grant': 'old_V2', 'path': object()})

  def test_future_members_exclude_model_extras_and_blas_payloads(self):
    inputs = module('inputs')
    for tail in (
      'stage2/model/nominal_coefficients.npy.gz',
      'stage2/model/singular_values.npy.gz',
      'one-step/integrated_delta.npy.gz',
      'rollout-25/candidate_error.npy.gz',
    ):
      with self.assertRaises(ValueError):
        inputs.member_allowed('TRAIN', 'V1', 'candidates/HRI_D00_L01/FOLD_A/' + tail, 'array')
    inputs.member_allowed('TRAIN', 'V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/coefficients.npy.gz', 'array')

  def test_continuous_errors_not_projected_tick_errors(self):
    import numpy as np

    evaluation = module('evaluation')
    pair = evaluation.pair(np.full(201, 0.25), np.ones(201), 'a' * 64)
    self.assertEqual(pair['candidate']['rmse'], 0.25)
    self.assertEqual(pair['hold_last']['rmse'], 1.0)
    self.assertIsNone(evaluation.pair(np.zeros(200), np.zeros(200), 'a' * 64))


class TestDurableAndBarriers(unittest.TestCase):
  def test_exclusive_durable_output_and_tamper(self):
    import tempfile
    from pathlib import Path

    out = module('output')
    with tempfile.TemporaryDirectory() as parent:
      with out.Store(Path(parent) / 'synthetic') as store:
        digest = store.write('sample.json', {'scope': 'SYNTHETIC_ONLY', 'n': 32})
        self.assertEqual(store.read('sample.json', digest)['n'], 32)
        with self.assertRaises((ValueError, FileExistsError)):
          store.write('sample.json', {'n': 33})
        (Path(parent) / 'synthetic/sample.json').write_text('{}')
        with self.assertRaises(ValueError):
          store.read('sample.json', digest)

  def test_symlink_parent_and_hardlink_result_denied(self):
    import os
    import tempfile
    from pathlib import Path

    out = module('output')
    with tempfile.TemporaryDirectory() as parent:
      link = Path(parent) / 'link'
      link.symlink_to(parent, target_is_directory=True)
      with self.assertRaises((ValueError, OSError)):
        out.Store(link / 'bad')
      with out.Store(Path(parent) / 'synthetic') as store:
        digest = store.write('sample.json', {'n': 32})
        os.link(Path(parent) / 'synthetic/sample.json', Path(parent) / 'copy')
        with self.assertRaises(ValueError):
          store.read('sample.json', digest)

  def test_duplicate_json_and_nan_rejected(self):
    out = module('output')
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{} trailing'):
      with self.subTest(raw=raw), self.assertRaises(ValueError):
        out.decode(raw)

  def test_resource_maximum_is_not_synthetic_capacity_claim(self):
    execution = module('execution')
    plan = execution.resource_plan()
    self.assertEqual(plan['status'], 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN')
    self.assertGreater(plan['known_buffer_scenario_bytes'], 8 * 1024**3)
    with self.assertRaises(ValueError):
      execution.resource_plan(n=336942)

  def test_dev_provider_cannot_open_before_training_readback(self):
    from tools.cyberpilot.canonical_readiness_fixture import provider

    p = provider()
    with self.assertRaises(ValueError):
      p.dev(0, None)
    self.assertEqual(p.counters.get('DEV_reads', 0), 0)

  def test_real_pipeline_seals_then_evaluates_all_arms(self):
    import tempfile
    from pathlib import Path
    from tools.cyberpilot.canonical_readiness_fixture import provider

    execution = module('execution')
    p = provider()
    with tempfile.TemporaryDirectory() as parent:
      result = execution.run_synthetic(p, Path(parent) / 'repeat', execution.synthetic_binding('a' * 40))
      self.assertEqual(result['coverage'], {'D0': 32, 'D1': 64, 'D2': 64, 'Q1': 32, 'Q3': 32, 'DEV_jobs': 32})
      self.assertEqual(set(result['jobs'][0]['arms']), {'D0', 'D1', 'D2'})
      self.assertFalse(result['empirical_acceptance'])
      self.assertIsNone(result['selected_candidate'])
      verified = execution.verify_synthetic(Path(parent) / 'repeat', result['binding'], result['completion_digest'])
      self.assertEqual(verified['scientific_recomputations'], 0)
      self.assertEqual(verified['source_rereads'], 0)

  def test_terminal_failure_never_enters_dev_or_retry(self):
    import tempfile
    from pathlib import Path
    from tools.cyberpilot.canonical_readiness_fixture import provider

    execution = module('execution')
    p = provider()
    p.train_jobs[0]['p'][0] = float('nan')
    with tempfile.TemporaryDirectory() as parent, self.assertRaises(ValueError):
      execution.run_synthetic(p, Path(parent) / 'repeat', execution.synthetic_binding('a' * 40))
    self.assertEqual(p.counters.get('DEV_reads', 0), 0)


class TestReadinessHardening(unittest.TestCase):
  def test_stale_or_offline_only_grant_cannot_enable_private(self):
    ex = module('execution')
    cases = (
      {},
      {'schema': 'V4_E2_V2_FRESH_BINDING_V1'},
      {
        'schema': 'FRESH_CANONICAL_E2_GRANT_V1',
        'scope': 'CANONICAL_E2_EXPLICIT_FUTURE_EXECUTION',
        'F_AUTHORIZED': False,
        'HOLDOUT': 'CLOSED',
        'vehicle_authority': 'NONE',
        'FULL_CI': {'scope': 'OFFLINE_STATIC_NUMERICAL_CI', 'status': 'completed', 'conclusion': 'success'},
      },
    )
    for case in cases:
      with self.subTest(case=case), self.assertRaises(ValueError):
        ex.validate_future_authority(case)

  def test_train_validator_rejects_incomplete_mutated_and_blas_reference(self):
    import copy
    import tempfile
    from pathlib import Path
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex, out = module('execution'), module('output')
    with tempfile.TemporaryDirectory() as parent, out.Store(Path(parent) / 'repeat') as store:
      run = ex.Run(provider(), store, ex.synthetic_binding('a' * 40))
      run.train()
      for kind in ('missing_job', 'duplicate', 'Q1', 'Q3', 'D1', 'D2', 'guard', 'baseline', 'head'):
        record = copy.deepcopy(run.train_record)
        if kind == 'missing_job':
          record['jobs'].pop()
        elif kind == 'duplicate':
          record['jobs'][1] = record['jobs'][0]
        elif kind in ('Q1', 'Q3'):
          record['jobs'][0].pop(kind)
        elif kind in ('D1', 'D2'):
          record['jobs'][0]['decisions'][kind].pop()
        elif kind == 'guard':
          record['jobs'][0]['details']['D2']['PREVIOUS_STATIC']['guards']['TRUE_MOVE_TP'] = False
        elif kind == 'baseline':
          record['guard_reference'] = 'HISTORICAL_BLAS_D0'
        else:
          record['binding'] = {**record['binding'], 'head': 'b' * 40}
        with self.subTest(kind=kind), self.assertRaises((ValueError, KeyError)):
          ex.validate_train(record, run.binding)

  def test_partial_fsync_blocks_dev(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex, out = module('execution'), module('output')
    with tempfile.TemporaryDirectory() as parent, out.Store(Path(parent) / 'repeat') as store:
      p = provider()
      run = ex.Run(p, store, ex.synthetic_binding('a' * 40))
      with patch.object(out.os, 'fsync', side_effect=OSError('SYNTHETIC_FSYNC_FAILURE')), self.assertRaises(OSError):
        run.train()
      self.assertEqual(run.phase, ex.Phase.FAILED)
      self.assertEqual(p.counters.get('DEV_reads', 0), 0)
      with self.assertRaises(ValueError):
        run.evaluate([])

  def test_winner_changed_after_seal_blocks_dev(self):
    import tempfile
    from pathlib import Path
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex, out = module('execution'), module('output')
    with tempfile.TemporaryDirectory() as parent, out.Store(Path(parent) / 'repeat') as store:
      p = provider()
      run = ex.Run(p, store, ex.synthetic_binding('a' * 40))
      run.train()
      old = run.pipeline.policies[0]['D2']
      run.pipeline.policies[0]['D2'] = (1.0 if old[0] != 1.0 else 0.0, old[1])
      with self.assertRaises(ValueError):
        run.evaluate([])
      self.assertEqual(p.counters.get('DEV_reads', 0), 0)

  def test_completion_symlink_is_rejected_without_follow(self):
    import tempfile
    from pathlib import Path

    ex = module('execution')
    with tempfile.TemporaryDirectory() as parent:
      root = Path(parent) / 'repeat'
      root.mkdir(mode=0o700)
      (root / 'complete.json').symlink_to(Path(parent) / 'absent')
      with self.assertRaises((OSError, ValueError)):
        ex.verify_synthetic(root, {}, 'a' * 64)

  def test_verify_only_does_not_construct_provider_or_infer(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex = module('execution')
    with tempfile.TemporaryDirectory() as parent:
      root = Path(parent) / 'repeat'
      result = ex.run_synthetic(provider(), root, ex.synthetic_binding('a' * 40))
      with (
        patch.object(ex, 'public_check', side_effect=AssertionError('SOURCE_REREAD')),
        patch.object(ex.b, 'infer', side_effect=AssertionError('INFERENCE')),
        patch.object(ex.b, 'ResearchPipeline', side_effect=AssertionError('RECOMPUTE')),
      ):
        verified = ex.verify_synthetic(root, result['binding'], result['completion_digest'])
      self.assertEqual(verified['inference_calls'], 0)
      with self.assertRaises(ValueError):
        ex.verify_synthetic(root, {**result['binding'], 'head': 'b' * 40}, result['completion_digest'])

  def test_repeat_comparison_rejects_partial_or_changed_payload(self):
    ex = module('execution')
    with self.assertRaises(ValueError):
      ex.compare_repeats(b'one', b'two', True, True)
    with self.assertRaises(ValueError):
      ex.compare_repeats(b'one', b'one', True, False)
    self.assertEqual(ex.compare_repeats(b'one', b'one', True, True), 'BYTE_EXACT_SYNTHETIC_REPEATS')


class TestSourceAndMetricIntegrity(unittest.TestCase):
  def test_rollout_payload_and_model_cannot_change_after_provider_binding(self):
    from tools.cyberpilot.canonical_readiness_fixture import provider

    for kind in ('command', 'anchor', 'model'):
      p = provider()
      p.unlock('a' * 64)
      if kind == 'command':
        p._paths[0]['horizons'][25]['command'][0, 0] += 100
      elif kind == 'anchor':
        p._paths[0]['horizons'][25]['anchor'] = 'not-a-hash'
      else:
        p._dev_jobs[0]['stage2']['coefficients'][0] += 1
      with self.subTest(kind=kind), self.assertRaises(ValueError):
        p.dev(0, 'a' * 64)

  def test_arbitrary_object_dtype_plan_is_not_exact_binding(self):
    inp = module('inputs')
    entry = {
      'role': 'TRAIN',
      'owner': 'V1',
      'member': 'candidates/HRI_D00_L01/FOLD_A/stage2/model/coefficients.npy.gz',
      'kind': 'array',
      'raw_sha256': 'a' * 64,
      'anchor': 'b' * 64,
      'root_identity': 'c' * 64,
      'count': 1,
      'dtype': 'object',
      'shape': [-1],
    }
    with self.assertRaises(ValueError):
      inp.validate_future_plan([entry])

  def test_supported_true_move_and_all_rollout_clauses_are_evaluated(self):
    from tools.cyberpilot.canonical_readiness_fixture import job

    ev, ex = module('evaluation'), module('execution')
    data, paths = job(0, 'DEV', n=416, rollout_n=201)
    protocol, _ = ex.public_check()
    module('inputs').validate_dev(data)
    result = ev.evaluate(data, paths, {'D0': (0.5,), 'D1': (0.5, 0.5), 'D2': (0.5, 0.5)}, protocol['acceptance']['clauses'], {})
    for arm in result['arms'].values():
      self.assertGreaterEqual(arm['true_move']['count'], 201)
      self.assertTrue(all(c['evaluated'] for c in arm['gate']['clauses']))
      for h in (25, 50, 100, 200):
        self.assertEqual(arm['rollout'][str(h)]['path_moved']['count'], 201)

  def test_return_to_origin_reference_still_path_moved(self):
    import numpy as np

    ev = module('evaluation')
    self.assertEqual(ev.b.path_moved(np.array([[0, 1, 0], [0, 0, 0]], np.int64)).tolist(), [True, False])


class TestReadinessBoundaryCoverage(unittest.TestCase):
  def test_observed_reference_and_exogenous_join_reject_inconsistent_source(self):
    from tools.cyberpilot.canonical_readiness_fixture import job

    inp = module('inputs')
    for field in ('observed', 'command', 'speed', 'row_ids'):
      data, paths = job(0, 'DEV')
      if field == 'row_ids':
        paths['horizons'][25][field][0] = 1
      else:
        paths['horizons'][25][field][0, 1] += 1
      with self.subTest(field=field), self.assertRaises(ValueError):
        inp.validate_paths(data, paths)

  def test_fifo_result_does_not_block_and_init_failure_does_not_leak(self):
    import os
    import tempfile
    from pathlib import Path

    out = module('output')
    with tempfile.TemporaryDirectory() as parent:
      root = Path(parent) / 'repeat'
      with out.Store(root) as store:
        os.mkfifo(root / 'result.json', 0o600)
        with self.assertRaises(ValueError):
          store.read('result.json', 'a' * 64)
      bad = Path(parent) / 'bad'
      bad.mkdir(mode=0o755)
      before = len(os.listdir('/proc/self/fd'))
      with self.assertRaises(ValueError):
        out.Store(bad, create=False)
      self.assertEqual(len(os.listdir('/proc/self/fd')), before)

  def test_bounded_decoder_hash_shape_and_trailing_payload(self):
    import io
    import gzip
    import hashlib
    import numpy as np

    inp = module('inputs')
    stream = io.BytesIO()
    array = np.array([0.0, -0.0, 1.0], np.float64)
    np.save(stream, array, allow_pickle=False)
    npy = stream.getvalue()
    raw = gzip.compress(npy, mtime=0)
    desc = {
      'dtype': '<f8',
      'shape': [3],
      'order': 'C',
      'file_sha256': hashlib.sha256(raw).hexdigest(),
      'array_sha256': hashlib.sha256(array.tobytes()).hexdigest(),
      'npy_sha256': hashlib.sha256(npy).hexdigest(),
    }
    values, _ = inp.decode_array(raw, desc, shape=(3,), dtype='<f8', compressed=True)
    self.assertEqual(values.tobytes(), array.tobytes())
    self.assertFalse(values.flags.writeable)
    for payload in (raw + b'x', gzip.compress(npy + b'x', mtime=0)):
      modified = {**desc, 'file_sha256': hashlib.sha256(payload).hexdigest()}
      with self.assertRaises(ValueError):
        inp.decode_array(payload, modified, shape=(3,), dtype='<f8', compressed=True)

  def test_private_publication_is_always_blocked(self):
    ex = module('execution')
    with self.assertRaises(ValueError):
      ex.public_projection({'evidence_scope': 'PRIVATE', 'private_reads': 0})

  def test_current_contract_pins_and_old91_preservation(self):
    import ast
    import hashlib
    import subprocess
    from tools.cyberpilot import run_numerical_offline as old

    ex = module('execution')
    protocol, _ = ex.public_check()
    self.assertEqual(protocol['version'], 'V4_E2_CANONICAL_PRIVATE_EXECUTION_PROTOCOL_V1')
    self.assertFalse(protocol['private_execution_authorized'])
    self.assertEqual(len(protocol['acceptance']['clauses']), 32)
    self.assertEqual(len(protocol['validation_domains']), 22)
    self.assertEqual(len(protocol['objective']), 5)
    self.assertEqual(len(protocol['guards']), 4)
    self.assertEqual(
      hashlib.sha256((ex.ROOT / 'tools/cyberpilot/run_numerical_offline.py').read_bytes()).hexdigest(),
      hashlib.sha256(
        subprocess.check_output(['git', 'show', 'df543777f71377938861f53ea2d369bd6324d2fe:tools/cyberpilot/run_numerical_offline.py'], cwd=ex.ROOT)
      ).hexdigest(),
    )
    self.assertEqual(unittest.defaultTestLoader.loadTestsFromNames(old.SUITES).countTestCases(), 91)
    old_source = subprocess.check_output(
      ['git', 'show', 'df543777f71377938861f53ea2d369bd6324d2fe:openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_bridge.py'],
      cwd=ex.ROOT,
    ).decode()
    new_source = (ex.ROOT / 'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_bridge.py').read_text()

    def methods(text):
      return [n.name for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]

    self.assertEqual(methods(old_source), methods(new_source))


class TestTrainRolePhase(unittest.TestCase):
  def test_train_needs_no_stage1_heads_and_qualifies_before_selection(self):
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex = module('execution')
    p = provider()
    self.assertTrue(all(j['stage1'] is None for j in p.train_jobs))
    pipeline = ex.TrainPipeline(p.train())
    pipeline.reconstruct_d0()
    pipeline.cache_potentials()
    with self.assertRaises(ValueError):
      pipeline.select_d2()
    self.assertEqual(pipeline.counters.get('D2_context_decision_selection_calls', 0), 0)
    pipeline.qualify_q1()
    pipeline.select_d1()
    pipeline.select_d2()
    pipeline.qualify_q3()
    self.assertEqual((len(pipeline.q1), len(pipeline.q3), pipeline.counters['D2_context_decision_selection_calls']), (32, 32, 64))

  def test_q1_byte_corruption_blocks_d2(self):
    import numpy as np
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex = module('execution')
    p = ex.TrainPipeline(provider().train())
    p.reconstruct_d0()
    p.cache_potentials()
    p.caches[0]['u'][0] = np.nextafter(p.caches[0]['u'][0], np.inf)
    with self.assertRaises(ValueError):
      p.qualify_q1()
    with self.assertRaises(ValueError):
      p.select_d2()
    self.assertEqual(p.counters.get('D2_context_decision_selection_calls', 0), 0)

  def test_q3_after_all64_rejects_corruption_without_reselection(self):
    import numpy as np
    from tools.cyberpilot.canonical_readiness_fixture import provider

    ex = module('execution')
    p = ex.TrainPipeline(provider().train())
    p.reconstruct_d0()
    p.cache_potentials()
    p.qualify_q1()
    p.select_d1()
    p.select_d2()
    p.caches[0]['u'][0] = np.nextafter(p.caches[0]['u'][0], np.inf)
    with self.assertRaises(ValueError):
      p.qualify_q3()
    self.assertEqual(p.counters['D2_context_decision_selection_calls'], 64)
