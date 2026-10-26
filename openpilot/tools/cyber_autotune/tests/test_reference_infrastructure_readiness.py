import copy
import unittest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

try:
  from openpilot.tools.cyber_autotune import reference_infrastructure_readiness as r
except ImportError:
  r = None


class TestReadiness(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(r, 'Missing reference critical-path readiness')

  def test_actual_state_pending_closed_unavailable(self):
    x = r.snapshot()
    self.assertEqual(
      x['states'],
      {
        'CALIBRATION': 'PENDING',
        'EGO_ASSOCIATION': 'VALIDATION_PENDING',
        'ROAD_REGISTRATION': 'BLOCKED',
        'PRIVATE_DIAGNOSTIC': 'PROPOSED_NOT_RUN',
        'REFERENCE': 'UNAVAILABLE',
      },
    )
    self.assertEqual(x['private_comma4'], 'NOT_OPENED')
    self.assertEqual(x['sealed_reference'], 'NOT_GENERATED')
    self.assertFalse(x['private_input_allowed'])
    self.assertFalse(x['reference_promotable'])

  def test_calibration_metric_road_center_critical_dependencies(self):
    nodes = {n['code']: n for n in r.snapshot()['nodes']}
    self.assertIn('CALIBRATION_MEASUREMENT_PENDING', nodes['INDEPENDENT_CALIBRATION_VALIDATION_PENDING']['dependencies'])
    self.assertIn('INDEPENDENT_CALIBRATION_VALIDATION_PENDING', nodes['METRIC_CALIBRATION_UNAVAILABLE']['dependencies'])
    self.assertIn('METRIC_CALIBRATION_UNAVAILABLE', nodes['ROAD_REGISTRATION_UNAVAILABLE']['dependencies'])
    self.assertIn('EGO_ASSOCIATION_VALIDATION_PENDING', nodes['ROAD_REGISTRATION_UNAVAILABLE']['dependencies'])
    self.assertIn('ROAD_REGISTRATION_UNAVAILABLE', nodes['INDEPENDENT_LANE_CENTER_REFERENCE_UNAVAILABLE']['dependencies'])
    self.assertIn('DESIRED_PATH_REFERENCE_UNAVAILABLE', nodes['INDEPENDENT_LANE_CENTER_REFERENCE_UNAVAILABLE']['dependencies'])

  def test_previous_blockers_never_disappear_or_turn_to_pass(self):
    x = r.snapshot()
    nodes = {n['code']: n for n in x['nodes']}
    for name in (
      'CULANE_OFFICIAL_REPRODUCTION_BLOCKED',
      'COMMA10K_LABEL_COMPLETENESS_UNVERIFIED',
      'PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED',
      'INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE',
    ):
      self.assertEqual(nodes[name]['status'], 'BLOCKED')
      self.assertEqual(len(nodes[name]['evidence_sha256']), 64)

  def test_deterministic_dag_has_no_unknown_or_cyclic_dependencies(self):
    x = r.snapshot()
    self.assertEqual(x, r.snapshot())
    order = {code: i for i, code in enumerate(x['dependency_order'])}
    for node in x['nodes']:
      for dep in node['dependencies']:
        self.assertLess(order[dep], order[node['code']])

  def test_all_undrivable_is_not_lane_absence_or_quality_pass(self):
    x = r.label_completeness_audit()
    self.assertEqual(x['status'], 'COMMA10K_LABEL_COMPLETENESS_UNVERIFIED')
    self.assertEqual(x['repeated_shared_mask_count'], 1400)
    self.assertFalse(x['lane_absence_verified'])
    self.assertFalse(x['filter_applied'])
    self.assertFalse(x['legacy_metric_invalidated'])

  def test_changed_readiness_or_seal_private_flag_rejected(self):
    for field, value in [('reference_promotable', True), ('private_input_allowed', True), ('sealed_reference', 'GENERATED')]:
      x = unseal(r.snapshot())
      x[field] = value
      with self.assertRaises(ValueError):
        r.validate_snapshot(seal(x))
    x = unseal(r.snapshot())
    x['states']['REFERENCE'] = 'SEALED'
    with self.assertRaises(ValueError):
      r.validate_snapshot(seal(x))

  def test_calibration_protocol_has_no_fake_measurement_defaults(self):
    x = r.snapshot()['calibration_protocol']
    for field in x['measurement_fields'].values():
      self.assertIsNone(field['value'])
      self.assertIsNone(field['uncertainty'])
      self.assertIsNone(field['method'])
      self.assertIsNone(field['provenance'])
    self.assertIsNone(x['actual_camera_identity'])

  def test_protocol_schema_identifier_is_not_overwritten(self):
    self.assertEqual(r.calibration_protocol()['schema'], 'PHYSICAL_CALIBRATION_SUBMISSION_PROTOCOL_V1')

  def test_returned_snapshot_mutation_cannot_change_current_states(self):
    before = copy.deepcopy(r.STATES)
    try:
      x = r.snapshot()
      x['states']['REFERENCE'] = 'SEALED'
      self.assertEqual(r.STATES, before)
    finally:
      r.STATES.clear()
      r.STATES.update(before)

  def test_all_pending_json_receipts_round_trip_exactly(self):
    import json
    from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
    from openpilot.tools.cyber_autotune.native_protocol import canonical

    for value in (r.calibration_protocol(), r.snapshot(), c.admit(None)):
      restored = json.loads(canonical(value))
      self.assertEqual(restored, value)
    r.validate_snapshot(json.loads(canonical(r.snapshot())))
