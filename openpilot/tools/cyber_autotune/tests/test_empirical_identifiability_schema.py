import copy
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_identifiability_math as m
from openpilot.tools.cyber_autotune import empirical_identifiability_schema as s
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as e
from openpilot.tools.cyber_autotune import empirical_identifiability_publication as publication
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestExactAggregateSchema(unittest.TestCase):
  def setUp(self):
    self.data = {k: np.arange(50, dtype=float) for k in ('angle', 'rate', 'command', 'speed', 'raw', 'request')}
    self.data.update(streak=np.arange(1, 51), segment=np.zeros(50, int), causal=np.zeros(50, int),
                     state_time=np.arange(50)*10_000_000)
    x, names = m.features(self.data, np.arange(50), 'S1', 0)
    self.names = names
    self.rank = m.rank_diagnostic(x, names)
    self.rank.update(next_state_available=49, speed_bins_at_feature_endpoint=e.speed_counts(self.data['speed']),
                     feature_order_sha256=p.sha(p.canonical(names)))

  def test_exact_rank_schema(self):
    s.rank_scope(self.rank, self.names)

  def test_rank_unknown_private_samples(self):
    self.rank['individual_angle_samples'] = [1., 2.]
    with self.assertRaises(ValueError):
      s.rank_scope(self.rank, self.names)

  def test_rank_tolerance_drift(self):
    self.rank['numpy_default_tolerance'] = 10.
    with self.assertRaises(ValueError):
      s.rank_scope(self.rank, self.names)

  def test_rank_claim_drift(self):
    self.rank['numerical_rank'] = 5
    with self.assertRaises(ValueError):
      s.rank_scope(self.rank, self.names)

  def test_rank_order_drift(self):
    with self.assertRaises(ValueError):
      s.rank_scope(self.rank, self.names[::-1])

  def test_empty_envelope_rejected(self):
    for family in ('S1', 'S2'):
      with self.subTest(family=family), self.assertRaises(ValueError):
        s.forms([], family, ['A', 'B'])

  def test_duplicate_form_rejected(self):
    with self.assertRaises(ValueError):
      s.forms([{'lag': 0}]*21, 'S1', ['A', 'B'])

  def test_history_nullable_vectors(self):
    s.aggregate_shape(e.history_report(self.data), [s.HISTORY])

  def test_excitation_nested_unknown_rejected(self):
    value = e.excitation(self.data)
    value['angle']['private_values'] = [1.]
    with self.assertRaises(ValueError):
      s.aggregate_shape(value, s.EXCITATION)

  def test_no_false_zero_authority(self):
    with self.assertRaises(ValueError):
      s.shape(0, False)

  def test_source_static_contract_cannot_add_data(self):
    value = copy.deepcopy(policy.source_contract())
    value['samples'] = [1., 2.]
    with self.assertRaises(ValueError):
      publication.validate_public(p.seal({k: v for k, v in value.items() if k != 'receipt_sha256'}))

  def test_static_public_contracts(self):
    for value in (policy.policy(), policy.source_contract(), policy.leakage_reset()):
      publication.validate_public(value)

  def test_valid_schema_private_digest_rejected(self):
    row = p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_REPEATABILITY_V1', 'executions': 2, 'exact': True,
      'policy_sha256': policy.policy()['receipt_sha256'], 'result_sha256': '/'+'home/private/route/file',
      'readiness_sha256': 'b'*64, 'historical_inputs_byte_identical': True, 'array_read_only': True,
      'raw_logs_opened': 0, 'qlog_arrays_opened': 0, 'receipt_and_aggregate_bytes_exact': True, 'model_operations': 'NOT_RUN'})
    with self.assertRaisesRegex(ValueError, 'PRIVATE_PATH'):
      publication.validate_public(row)

  def test_invalid_digest_rejected(self):
    with self.assertRaisesRegex(ValueError, 'SHA256'):
      s.privacy({'snapshot_set_sha256': 'private-data-in-hash'})

  def test_condition_reason_enum(self):
    self.rank['condition_undefined_reason'] = 'private value'
    with self.assertRaises(ValueError):
      s.rank_scope(self.rank, self.names)
