"""Public fake capabilities never authorize a private file open."""

import copy
import unittest
from unittest.mock import patch
import numpy as np
from tools.cyberpilot.canonical_bounded_fixture import capability_fixture


class TestCapability(unittest.TestCase):
  def test_exact_numeric_role_and_metadata_separation(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    plan = capability_fixture()
    with patch('builtins.open', side_effect=AssertionError('filesystem forbidden')):
      self.assertEqual(q.validate_capability(plan), 'STRUCTURE_VALIDATED_NO_PRIVATE_AUTHORITY')
    for member in ('nominal_coefficients', 'singular_values'):
      bad = copy.deepcopy(plan)
      bad['entries'][0]['member'] = bad['entries'][0]['member'].replace('coefficients.npy', member + '.npy')
      bad = q.seal_capability(bad)
      with self.assertRaises(ValueError):
        q.validate_capability(bad)

  def test_duplicate_wrong_role_anchor_and_hash_fail(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    plan = capability_fixture()
    mutations = (
      lambda p: p['entries'].append(copy.deepcopy(p['entries'][0])),
      lambda p: p['entries'][0].update(role='HOLDOUT'),
      lambda p: p['entries'][0].update(anchor='wrong'),
      lambda p: p['entries'][0]['descriptor'].update(dtype='<f4'),
      lambda p: p['entries'][0].update(candidate='HRI_D99_L99'),
      lambda p: p['entries'][0]['descriptor'].update(shape=[False]),
      lambda p: p['grant'].update(head='bad'),
      lambda p: p['entries'][0].update(member='../raw/qlog'),
      lambda p: p['entries'][0].update(member='candidates/*/stage2/model/coefficients.npy.gz'),
      lambda p: p['entries'][0].update(unapproved_field=True),
      lambda p: p['grant'].update(private_authority=True),
    )
    for change in mutations:
      bad = copy.deepcopy(plan)
      change(bad)
      with self.assertRaises(ValueError):
        q.validate_capability(q.seal_capability(bad))
    bad = copy.deepcopy(plan)
    bad['entries'][0]['descriptor']['content_sha256'] = 'f' * 64
    with self.assertRaises(ValueError):
      q.validate_capability(bad)

  def test_durable_plan_before_numeric_and_dev_train_barrier(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_output import Store
    import tempfile
    from pathlib import Path

    plan = capability_fixture()
    session = q.SyntheticCapabilitySession(plan)
    with self.assertRaises(ValueError):
      session.permit(0)
    session = q.SyntheticCapabilitySession(plan)
    session.grant()
    session.root()
    session.metadata(plan['metadata_receipt'])
    with self.assertRaises(ValueError):
      session.enable_numeric()
    session = q.SyntheticCapabilitySession(plan)
    session.grant()
    session.root()
    session.metadata(plan['metadata_receipt'])
    with tempfile.TemporaryDirectory() as tmp:
      with Store(Path(tmp) / 'cap') as store:
        session.seal_plan(store)
      session.enable_numeric()
      self.assertEqual(session.permit(0)['member'], plan['entries'][0]['member'])
      from tools.cyberpilot.canonical_bounded_fixture import provider
      from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as bounded
      from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as reference

      with Store(Path(tmp) / 'train') as train_store:
        run = bounded.BoundedRun(provider(), train_store, reference.synthetic_binding('1' * 40))
        run.train()
        session.train_sealed(run.train_digest, train_store.read('train.json', run.train_digest))
      self.assertEqual(session.permit(1)['role'], 'DEV')

  def test_source_snapshot_alias_and_changed_original_are_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    a = {'tick': np.arange(250, dtype=np.int64), 'command': np.ones(250), 'speed': np.ones(250), 'streak': np.arange(1, 251, dtype=np.int64)}
    block = q.SourceBlock(a, 'a' * 64)
    self.assertFalse(block.arrays['tick'].flags.writeable)
    with self.assertRaises(ValueError):
      block.arrays['tick'].setflags(write=True)
    altered = block.arrays['tick'].copy()
    altered[0] = 17
    with self.assertRaises(ValueError):
      block.verify_array('tick', altered)
    a['tick'][0] = 1
    with self.assertRaises(ValueError):
      block.check()

  def test_no_private_authority_even_with_fake_valid_plan(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    class Bomb:
      def __fspath__(self):
        raise AssertionError('private path inspected')

    with self.assertRaisesRegex(ValueError, 'PRIVATE_EXECUTION_NOT_AUTHORIZED'):
      q.execute_private(Bomb(), capability_fixture())

  def test_failed_capability_phase_is_terminal(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    s = q.SyntheticCapabilitySession(capability_fixture())
    with self.assertRaises(ValueError):
      s.enable_numeric()
    self.assertEqual(s.phase, 'FAILED_TERMINAL')
    with self.assertRaises(ValueError):
      s.grant()

  def test_equal_bytes_replacement_does_not_preserve_owner_identity(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    a = {'tick': np.zeros(250, np.int64), 'command': np.ones(250), 'speed': np.ones(250), 'streak': np.arange(1, 251, dtype=np.int64)}
    block = q.SourceBlock(a, 'a' * 64)
    block.arrays['tick'] = q.immutable(block.arrays['tick'].copy())
    with self.assertRaises(ValueError):
      block.check()

  def test_raw_source_npy_and_cross_role_physical_identity(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    p = capability_fixture()
    a = p['entries'][0]
    a.update(owner='CAUSAL', member='repeat-1/routes/' + 'c' * 64 + '/segments/' + 'd' * 64 + '/arrays/command.normalized.npy')
    a['descriptor'].update(storage='npy', shape=[208], row_count=208)
    p['entries'][1] = copy.deepcopy(a)
    p['entries'][1].update(role='DEV', fold='FOLD_B')

    def reseal(plan):
      plan['metadata_receipt'] = q.out.sealed(
        {'schema': 'SYNTHETIC_METADATA_ONLY', 'entries_sha256': q.out.sha(q.out.canonical(plan['entries'])), 'root_receipt': plan['root']['receipt']}
      )
      return q.seal_capability(plan)

    self.assertEqual(q.validate_capability(reseal(p)), 'STRUCTURE_VALIDATED_NO_PRIVATE_AUTHORITY')
    p['entries'][1]['descriptor']['content_sha256'] = '9' * 64
    with self.assertRaisesRegex(ValueError, 'PHYSICAL_MEMBER_CONFLICT'):
      q.validate_capability(reseal(p))

  def test_hash_only_train_proof_cannot_enable_dev(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    s = q.SyntheticCapabilitySession(capability_fixture())
    s.phase = 'SYNTHETIC_NUMERIC_DESCRIPTORS_ENABLED'
    with self.assertRaises(ValueError):
      s.train_sealed('a' * 64)

  def test_v1_v4_job_vector_cap_is_separate_from_source_cap(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q

    p = capability_fixture()
    e = p['entries'][0]
    e.update(owner='V4', member='candidates/' + e['candidate'] + '/' + e['fold'] + '/train/combined_probability.npy.gz')
    e['descriptor'].update(shape=[336942], row_count=336942)
    p['metadata_receipt'] = q.out.sealed(
      {'schema': 'SYNTHETIC_METADATA_ONLY', 'entries_sha256': q.out.sha(q.out.canonical(p['entries'])), 'root_receipt': p['root']['receipt']}
    )
    with self.assertRaisesRegex(ValueError, 'JOB_ROW_CAP'):
      q.validate_capability(q.seal_capability(p))
