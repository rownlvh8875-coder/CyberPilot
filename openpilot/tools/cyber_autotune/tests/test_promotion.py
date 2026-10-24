from dataclasses import FrozenInstanceError, replace
import hashlib
import unittest

from openpilot.tools.cyber_autotune.promotion import (
  FaultObservation, GateReceipt, PromotionBinding, advance, apply_fault, assess, new_rehearsal,
)


STAGES = ('SIMULATION_SCREEN', 'REPLAY', 'CALIBRATED_SIMULATION', 'SHADOW')
FAULTS = ('REGRESSION', 'UNEXPECTED_SATURATION', 'PARAMETER_CORRUPTION', 'CONTROLLER_EXCEPTION',
          'CONFIDENCE_LOSS', 'INVALID_VEHICLE_STATE', 'ROLLBACK_UNAVAILABLE')


def sha(label):
  return hashlib.sha256(label.encode()).hexdigest()


def binding():
  return PromotionBinding('HYUNDAI_SANTA_FE_2022', sha('software'), sha('config'), sha('parameter'),
                          sha('candidate'), sha('baseline'), sha('baseline'), sha('evaluator'), sha('policy'))


def receipt(index, status='PASS'):
  return GateReceipt(STAGES[index], status, sha('artifact' + str(index)), ('DECLARED_RESULT',), binding())


class TestPromotion(unittest.TestCase):
  def test_complete_ordered_rehearsal_never_grants_vehicle_authority(self):
    state = new_rehearsal(binding())
    previous = []
    for index in range(4):
      previous.append(state)
      state = advance(state, receipt(index))
    result = assess(state)
    self.assertEqual(result['contract_status'], 'AWAITING_SEPARATE_VEHICLE_APPROVAL')
    self.assertEqual(result['recorded_stages'], list(STAGES))
    self.assertFalse(result['runtime_accepted'])
    self.assertFalse(result['promotable'])
    self.assertFalse(result['rollback_executed'])
    self.assertEqual(result['vehicle_readiness'], 'NOT_READY')
    self.assertEqual(result['missing_authority'], 'QUALIFIED_EVIDENCE_AND_RUNTIME_INTEGRATION')
    self.assertEqual(assess(state), result)
    self.assertEqual([len(item.receipts) for item in previous], [0, 1, 2, 3])
    with self.assertRaises(FrozenInstanceError):
      state.fault = None
    with self.assertRaises(ValueError):
      advance(state, receipt(3))

  def test_bad_binding_and_exact_types_rejected(self):
    valid = binding()
    class DerivedBinding(PromotionBinding):
      pass
    invalid = [None, replace(valid, fingerprint=''), replace(valid, fingerprint=' HYUNDAI'),
               replace(valid, fingerprint='A\nB'), replace(valid, software_sha256=True),
               replace(valid, configuration_sha256='A' * 64), replace(valid, policy_sha256='missing'),
               replace(valid, rollback_profile_sha256=sha('wrong')), replace(valid, candidate_profile_sha256=valid.baseline_profile_sha256),
               DerivedBinding(**valid.__dict__)]
    for item in invalid:
      with self.subTest(item=type(item)), self.assertRaises(ValueError):
        new_rehearsal(item)

  def test_skip_reuse_cross_binding_and_wrong_scope_rejected(self):
    state = new_rehearsal(binding())
    valid = receipt(0)
    invalid = [None, receipt(1), replace(valid, stage='ACTIVE'), replace(valid, status=True),
               replace(valid, reasons=[]), replace(valid, reasons=()), replace(valid, reasons=('X', 'X')),
               replace(valid, reasons=('private path',)), replace(valid, artifact_sha256='x'),
               replace(valid, scope='LATERAL_ONLY')]
    for field in ('fingerprint', 'software_sha256', 'configuration_sha256', 'candidate_profile_sha256'):
      invalid.append(replace(valid, binding=replace(binding(), **{field: 'OTHER' if field == 'fingerprint' else sha('other')})))
    for item in invalid:
      with self.subTest(item=type(item)), self.assertRaises(ValueError):
        advance(state, item)
    one = advance(state, valid)
    with self.assertRaises(ValueError):
      advance(one, replace(receipt(1), artifact_sha256=valid.artifact_sha256))
    with self.assertRaises(ValueError):
      advance(one, valid)

  def test_forced_history_cannot_bypass_validation_at_any_public_entry(self):
    valid = new_rehearsal(binding())
    invalid = [None, replace(valid, receipts=[receipt(0)]), replace(valid, receipts=(receipt(1),)),
               replace(valid, receipts=(receipt(0, 'FAIL'), receipt(1))),
               replace(valid, binding=replace(binding(), rollback_profile_sha256=sha('wrong'))),
               replace(valid, fault=FaultObservation('UNKNOWN', None, None))]
    for state in invalid:
      with self.subTest(state=type(state)):
        with self.assertRaises(ValueError):
          assess(state)
        with self.assertRaises(ValueError):
          advance(state, receipt(0))
        with self.assertRaises(ValueError):
          apply_fault(state, FaultObservation('REGRESSION', None, None))

  def test_failed_and_revalidation_receipts_cannot_be_replaced_by_pass(self):
    for declared, expected in (('FAIL', 'FAILED'), ('REVALIDATION_REQUIRED', 'REVALIDATION_REQUIRED')):
      with self.subTest(declared=declared):
        state = advance(new_rehearsal(binding()), receipt(0, declared))
        result = assess(state)
        self.assertEqual(result['contract_status'], expected)
        self.assertIn('DECLARED_RESULT', result['reasons'])
        with self.assertRaises(ValueError):
          advance(state, receipt(1))
        faulted = apply_fault(state, FaultObservation('REGRESSION', binding().baseline_profile_sha256, None))
        self.assertEqual(faulted.receipts[0].status, declared)
        self.assertEqual(assess(faulted)['contract_status'], 'FAULTED')

  def test_every_fault_quarantines_explicit_inactive_candidate_at_every_stage(self):
    state = new_rehearsal(binding())
    for index in range(5):
      for code in FAULTS:
        with self.subTest(index=index, code=code):
          result = assess(apply_fault(state, FaultObservation(code, binding().baseline_profile_sha256, None)))
          self.assertEqual(result['action'], 'QUARANTINE_CANDIDATE')
          self.assertFalse(result['promotable'])
          self.assertFalse(result['rollback_executed'])
      if index < 4:
        state = advance(state, receipt(index))

  def test_fault_rollback_advice_requires_explicit_matching_active_and_rollback(self):
    identity = binding()
    state = new_rehearsal(identity)
    cases = [
      (FaultObservation('REGRESSION', identity.candidate_profile_sha256, identity.rollback_profile_sha256), 'REQUEST_ROLLBACK'),
      (FaultObservation('CONFIDENCE_LOSS', identity.candidate_profile_sha256, None), 'STOP_AND_REQUIRE_OPERATOR'),
      (FaultObservation('PARAMETER_CORRUPTION', identity.candidate_profile_sha256, sha('wrong')), 'STOP_AND_REQUIRE_OPERATOR'),
      (FaultObservation('ROLLBACK_UNAVAILABLE', identity.candidate_profile_sha256, identity.rollback_profile_sha256), 'STOP_AND_REQUIRE_OPERATOR'),
      (FaultObservation('INVALID_VEHICLE_STATE', None, identity.rollback_profile_sha256), 'STOP_AND_REQUIRE_OPERATOR'),
      (FaultObservation('CONTROLLER_EXCEPTION', sha('unknown'), identity.rollback_profile_sha256), 'STOP_AND_REQUIRE_OPERATOR'),
    ]
    for fault, expected in cases:
      with self.subTest(expected=expected):
        terminal = apply_fault(state, fault)
        result = assess(terminal)
        self.assertEqual(result['action'], expected)
        self.assertEqual(result['rollback_target_sha256'], identity.rollback_profile_sha256 if expected == 'REQUEST_ROLLBACK' else None)
        self.assertFalse(result['rollback_executed'])
        with self.assertRaises(ValueError):
          advance(terminal, receipt(0))
        with self.assertRaises(ValueError):
          apply_fault(terminal, fault)

  def test_history_digest_binds_every_stage_and_fault_observation(self):
    state = new_rehearsal(binding())
    first = advance(state, receipt(0))
    second = advance(state, replace(receipt(0), artifact_sha256=sha('different')))
    self.assertNotEqual(assess(first)['state_sha256'], assess(second)['state_sha256'])
    fault = FaultObservation('REGRESSION', None, None)
    self.assertNotEqual(assess(first)['state_sha256'], assess(apply_fault(first, fault))['state_sha256'])
    for invalid in (None, {}, FaultObservation('REGRESSION', True, None), FaultObservation('REGRESSION', None, 'bad')):
      with self.subTest(invalid=type(invalid)), self.assertRaises(ValueError):
        apply_fault(first, invalid)

  def test_fault_report_preserves_each_prior_gate_outcome_and_reasons(self):
    for declared in ('PASS', 'FAIL', 'REVALIDATION_REQUIRED'):
      with self.subTest(declared=declared):
        state = advance(new_rehearsal(binding()), receipt(0))
        state = advance(state, receipt(1, declared))
        terminal = apply_fault(state, FaultObservation('REGRESSION', binding().candidate_profile_sha256,
                                                       binding().rollback_profile_sha256))
        result = assess(terminal)
        self.assertEqual(result['contract_status'], 'FAULTED')
        self.assertEqual(result['gate_results'], [
          {'stage': 'SIMULATION_SCREEN', 'status': 'PASS', 'artifact_sha256': sha('artifact0'), 'reasons': ['DECLARED_RESULT']},
          {'stage': 'REPLAY', 'status': declared, 'artifact_sha256': sha('artifact1'), 'reasons': ['DECLARED_RESULT']},
        ])
        result['gate_results'][1]['reasons'].append('MUTATED_REPORT')
        self.assertEqual(assess(terminal)['gate_results'][1]['reasons'], ['DECLARED_RESULT'])


if __name__ == '__main__':
  unittest.main()
