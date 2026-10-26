"""Stored causal context, never a temporal policy performance experiment."""

import unittest
import json
import copy
import tempfile
from unittest.mock import patch
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal_math as t
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal as audit


class TestTemporal(unittest.TestCase):
  def fixture(self):
    delta = np.array([0, 1, 1, 0, 0, -1, 0, 0], dtype=np.int64)
    prior = np.array([0, 0, 1, 1, 0, 0, -1, 0], dtype=np.int64)
    linked = np.array([False, True, True, True, False, True, True, True])
    return delta, prior, linked

  def test_transitions_use_stored_prior_even_at_fragment_start(self):
    delta, prior, linked = self.fixture()
    r = t.transitions(delta, prior, linked)
    self.assertEqual(r['counts'], {'SS': 3, 'SM': 2, 'MS': 2, 'MM': 1})
    self.assertEqual(r['previous_static']['denominator'], 5)
    self.assertEqual(r['previous_move']['numerator'], 1)

  def test_history_two_never_crosses_gap(self):
    r = t.transitions(*self.fixture())
    self.assertEqual(r['history_two']['support'], 6)
    self.assertEqual(r['history_two']['last_two_static']['denominator'], 2)

  def test_prior_identity_conflict_rejected(self):
    delta, prior, linked = self.fixture()
    prior[2] = 0
    with self.assertRaisesRegex(ValueError, 'PRIOR_CONTEXT_CONFLICT'):
      t.transitions(delta, prior, linked)

  def test_fragment_censored_runs(self):
    delta, _, linked = self.fixture()
    r = t.runs(delta, linked)
    self.assertEqual(r['STATIC']['count'], 4)
    self.assertEqual(r['MOVE']['count'], 2)
    self.assertEqual(r['MOVE']['max'], 2)
    self.assertEqual(r['STATIC']['boundary_censored_count'], 4)
    self.assertEqual(json.loads(json.dumps(r)), r)

  def test_continuity_breaks_on_every_identity_axis(self):
    n = 5
    arrays = {k: np.zeros(n, dtype=np.int64) for k in ('anchor_route_id', 'anchor_segment_sha', 's2_ri_run_id')}
    arrays.update(anchor_index=np.arange(n), within_run_index=np.arange(n))
    self.assertEqual(t.continuity(arrays).tolist(), [False, True, True, True, True])
    for key in arrays:
      changed = {k: v.copy() for k, v in arrays.items()}
      changed[key][2] += 2
      self.assertFalse(t.continuity(changed)[2], key)

  def test_threshold_free_onset_and_continuation(self):
    delta, prior, _ = self.fixture()
    p = np.array([0.1, 0.8, 0.9, 0.2, 0.3, 0.7, 0.4, 0.1])
    r = t.scores(p, delta, prior)
    self.assertEqual(r['onset']['auc'], 1)
    self.assertEqual(r['continuation']['auc'], 1)
    self.assertEqual(r['onset']['positive_count'], 2)
    self.assertEqual(r['continuation']['positive_count'], 1)

  def test_empty_ranking_is_undefined_not_chance(self):
    r = t.scores(np.array([0.1, 0.2]), np.zeros(2, dtype=np.int64), np.zeros(2, dtype=np.int64))
    self.assertIsNone(r['onset']['auc'])
    self.assertEqual(r['onset']['support_state'], 'EMPTY_CLASS')

  def test_tied_scores_exact_half(self):
    delta, prior, _ = self.fixture()
    r = t.scores(np.full(len(delta), 0.25), delta, prior)
    self.assertEqual(r['onset']['auc_num2'] * 2, r['onset']['auc_den2'])

  def test_trigger_requires_all_32_supported_jobs(self):
    rank = {'positive_count': 201, 'negative_count': 201, 'auc_num2': 3, 'auc_den2': 4}
    self.assertTrue(t.rank_trigger([rank.copy() for _ in range(32)]))
    self.assertFalse(t.rank_trigger([rank.copy() for _ in range(31)]))
    rows = [rank.copy() for _ in range(32)]
    rows[0]['positive_count'] = 200
    self.assertFalse(t.rank_trigger(rows))

  def test_probability_invalid_rejected(self):
    delta, prior, _ = self.fixture()
    with self.assertRaises(ValueError):
      t.scores(np.full(len(delta), np.nan), delta, prior)

  def test_fraction_comparison_no_epsilon(self):
    self.assertTrue(t.persistence({'previous_move': {'numerator': 102, 'denominator': 201}, 'previous_static': {'numerator': 101, 'denominator': 201}}))
    self.assertFalse(t.persistence({'previous_move': {'numerator': 101, 'denominator': 201}, 'previous_static': {'numerator': 101, 'denominator': 201}}))

  def test_noninteger_truth_rejected(self):
    delta, prior, linked = self.fixture()
    with self.assertRaises(ValueError):
      t.transitions(delta.astype(float) + 0.1, prior, linked)

  def test_public_chain_is_exact_and_private_free(self):
    with patch.object(audit.io, 'load_array', side_effect=AssertionError('private array')):
      self.assertEqual(len(audit.public_inputs()['public_inputs']), 104)

  def test_unauthorized_field_rejected_before_loader(self):
    with patch.object(audit.io, 'load_array', side_effect=AssertionError('loader')):
      with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
        audit.StoredReader().load(Path('/synthetic'), {}, 'projected_path')

  def test_audit_firewall_blocks_threshold_and_replay(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as th
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as replay

    with audit.v.firewall():
      for fn in (th.sweep, th.canonical, replay.load_model, np.linalg.solve, np.linalg.lstsq):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          fn(None, None)

  def test_output_must_be_external_d_and_nonoverlapping(self):
    for destination in ('/mnt/c/results', '/mnt/d/source/child', '/mnt/d/source/../output'):
      with self.assertRaises(ValueError):
        audit.io.output_root(Path(destination), Path('/mnt/d/source'))

  def test_incomplete_or_conflicting_saved_aggregate_rejected(self):
    delta, prior, linked = self.fixture()
    row = dict.fromkeys(('route_id', 'anchor_sha256', 'source_receipt_sha256', 'v2_reference_receipt_sha256', 'probability_sha256'), 'a' * 64)
    row.update(transitions=t.transitions(delta, prior, linked), runs=t.runs(delta, linked), scores=t.scores(np.full(len(delta), 0.3), delta, prior))
    audit.validate_population(row)
    for mutate in ('extra_score', 'missing_fragment', 'missing_interpretation'):
      changed = copy.deepcopy(row)
      if mutate == 'extra_score':
        changed['scores']['onset']['unexpected_rows'] = [123, 456]
      else:
        del changed['runs']['fragment_count' if mutate == 'missing_fragment' else 'interpretation']
      with self.subTest(mutation=mutate), self.assertRaisesRegex(ValueError, 'INCOMPLETE_AGGREGATE'):
        audit.validate_population(changed)
    for field in row:
      with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'INCOMPLETE_AGGREGATE'):
        audit.validate_population({k: v for k, v in row.items() if k != field})
    row['scores']['onset']['auc_num2'] += 1
    with self.assertRaisesRegex(ValueError, 'INCOMPLETE_AGGREGATE'):
      audit.validate_population(row)

  def test_authorization_requires_complete_schema_and_persisted_policy(self):
    with tempfile.TemporaryDirectory() as tmp:
      output = Path(tmp)
      auth = audit.p.seal(
        {
          'schema': 'HURDLE_STAGE1_V3_TEMPORAL_AUTHORIZATION',
          'baseline': audit.BASELINE,
          'scope': 'STORED_TEMPORAL_DIAGNOSTICS_ONLY_NO_V3_EXECUTION',
          'policy_sha256': audit.policy()['receipt_sha256'],
          'source_roots': ['a' * 64, 'b' * 64],
          'output_root': audit.p.sha(str(output).encode()),
          'executor_sources': audit.sources(),
          'v1_manifest_sha256': audit.io.SOURCE_SHA,
          'v2_manifest_sha256': audit.v.V2_SHA,
        }
      )
      with self.assertRaises(FileNotFoundError):
        audit.validate_authorization(auth, output)
      audit.io.write_json(output / 'policy.json', audit.policy())
      audit.validate_authorization(auth, output)
      for key in auth:
        with self.subTest(key=key), self.assertRaises(ValueError):
          audit.validate_authorization({k: v for k, v in auth.items() if k != key}, output)
      for field in ('baseline', 'scope', 'source_roots', 'output_root', 'v1_manifest_sha256', 'v2_manifest_sha256'):
        with self.subTest(field=field), self.assertRaises(ValueError):
          audit.validate_authorization({**auth, field: 'wrong'}, output)

  def test_public_nested_rows_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_publication as pub

    delta, prior, linked = self.fixture()
    row = dict.fromkeys(audit.POPULATION_FIELDS, 'a' * 64)
    row.update(transitions=t.transitions(delta, prior, linked), runs=t.runs(delta, linked), scores=t.scores(np.full(len(delta), 0.3), delta, prior))
    self.assertIn('scores', pub.public_population(row))
    row['scores']['onset']['unexpected_rows'] = [123, 456]
    with self.assertRaisesRegex(ValueError, 'INCOMPLETE_AGGREGATE'):
      pub.public_population(row)
