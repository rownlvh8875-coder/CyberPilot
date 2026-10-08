"""Dependency gates, not calibration/qualification facts invented by tests."""

import unittest

from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.tests.test_lane_tail_assisted_diagnostic import fixture
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_workflow import loader

try:
  from openpilot.tools.cyber_autotune import lane_tail_blocker_plan as p
except ImportError:
  p = None


class TestBlockerPlan(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(p, 'Missing typed remaining-evidence DAG')
    from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d
    from openpilot.tools.cyber_autotune import lane_tail_second_review as b

    m, export, ex, ai = fixture()
    self.diag = d.aggregate(m, export, ex, ai, loader(m))
    self.protocol = b.protocol(m)

  def test_root_blocked_and_dependencies_topologically_ordered(self):
    result = p.blocker_plan(self.diag, self.protocol)
    self.assertEqual(result['schema'], 'NEXT_BLOCKER_PLAN_V1')
    self.assertEqual(result['status'], 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE')
    order = {code: i for i, code in enumerate(result['dependency_order'])}
    for node in result['nodes']:
      self.assertEqual(len(node['evidence_sha256']), 64)
      self.assertTrue(node['resolution_condition'])
      for dep in node['dependencies']:
        self.assertLess(order[dep], order[node['code']])

  def test_assisted_pass_never_makes_blind_gate_pass(self):
    result = p.blocker_plan(self.diag, self.protocol)
    nodes = {n['code']: n for n in result['nodes']}
    self.assertEqual(nodes['COMMA10K_ASSISTED_HUMAN_REVIEW_COMPLETE']['status'], 'TEST_ONLY')
    self.assertEqual(nodes['INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE']['status'], 'BLOCKED')
    self.assertFalse(result['private_input_allowed'])
    self.assertFalse(result['sealed_reference_allowed'])

  def test_private_contract_is_design_only_never_an_execution_permit(self):
    contract = p.private_diagnostic_contract(self.diag)
    self.assertEqual(contract['schema'], 'PRIVATE_PIXEL_DIAGNOSTIC_ONLY_V1')
    self.assertFalse(contract['execution_authorized_this_increment'])
    self.assertFalse(contract['qualification_allowed'])
    self.assertFalse(contract['sealed_reference_allowed'])
    self.assertFalse(contract['detector_reselection_allowed'])
    self.assertFalse(contract['modelv2_path_or_lane_allowed'])
    self.assertFalse(contract['candidate_outputs_allowed'])

  def test_mutated_diagnostic_or_promoted_verdict_rejected(self):
    for field, value in [('reference_promotable', True), ('detector_verdict', 'FULLY_QUALIFIED'), ('private_input_allowed', True)]:
      core = unseal(self.diag)
      core[field] = value
      with self.subTest(field=field), self.assertRaises(ValueError):
        p.blocker_plan(seal(core), self.protocol)

  def test_test_scope_cannot_be_resealed_as_actual_human_diagnostic(self):
    core = unseal(self.diag)
    core['status'] = 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE'
    with self.assertRaises(ValueError):
      p.blocker_plan(seal(core), self.protocol)

  def test_broken_category_accounting_cannot_make_assisted_pass_node(self):
    import copy

    core = unseal(copy.deepcopy(self.diag))
    core['categories']['DETECTOR_MISS']['frame_count'] = 28
    with self.assertRaises(ValueError):
      p.blocker_plan(seal(core), self.protocol)

  def test_unknown_dependency_and_cycles_rejected(self):
    for nodes in (
      [{'code': 'A', 'dependencies': ['B']}],
      [{'code': 'A', 'dependencies': ['B']}, {'code': 'B', 'dependencies': ['A']}],
    ):
      with self.assertRaises(ValueError):
        p.dependency_order(nodes)

  def test_calibration_precedes_registration_desired_path_binds_registration(self):
    result = p.blocker_plan(self.diag, self.protocol)
    nodes = {n['code']: n for n in result['nodes']}
    self.assertIn('INDEPENDENT_EXTRINSICS_UNAVAILABLE', nodes['METRIC_CALIBRATION_UNAVAILABLE']['dependencies'])
    self.assertIn('METRIC_CALIBRATION_UNAVAILABLE', nodes['ROAD_REGISTRATION_UNAVAILABLE']['dependencies'])
    self.assertIn('ROAD_REGISTRATION_UNAVAILABLE', nodes['DESIRED_PATH_REFERENCE_UNAVAILABLE']['dependencies'])

  def test_plan_can_progress_software_without_opening_private_or_blind_reviewer(self):
    result = p.blocker_plan(self.diag, self.protocol)
    answers = result['answers']
    self.assertTrue(answers['software_work_without_blind_reviewer'])
    self.assertTrue(answers['public_validation_does_not_supply_ego_identity'])
    self.assertTrue(answers['independent_geometry_is_meter_critical_path'])
    self.assertEqual(answers['private_pixel_diagnostic'], 'WORTH_DESIGNING_NONQUALIFYING_ONLY_NOT_RUN')
    self.assertEqual(result, p.blocker_plan(self.diag, self.protocol))

  def test_reviewer_reproduction_stripped_resealed_receipt_rejected(self):
    core = unseal(self.diag)
    for key in ('categories', 'metrics', 'concordance', 'row_provenance', 'metric_trace_receipts', 'human_export_sha256', 'experiment_sha256'):
      core.pop(key)
    core['status'] = 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE'
    with self.assertRaises(ValueError):
      p.blocker_plan(seal(core), self.protocol)

  def test_corrupt_nested_receipt_or_accounting_rejected(self):
    import copy

    for target in ('concordance', 'relation', 'trace', 'availability', 'metric', 'scope'):
      core = unseal(copy.deepcopy(self.diag))
      if target == 'concordance':
        c = unseal(core['concordance'])
        c['exact_agreements'] = 28
        core['concordance'] = seal(c)
      elif target == 'relation':
        c = unseal(core['row_provenance'][0])
        c['blind_human_review'] = True
        core['row_provenance'][0] = seal(c)
      elif target == 'trace':
        core['metric_trace_receipts'][0]['trace_sha256'] = None
      elif target == 'availability':
        core['metric_availability']['pred_to_gt']['available_frames'] = 28
      elif target == 'metric':
        core['metrics']['pred_to_gt']['p95'] = -1
      elif target == 'scope':
        core['manifest_scope'] = 'PUBLIC_COMMA10K_HUMAN_REVIEW'
        core['status'] = 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE'
      with self.subTest(target=target), self.assertRaises(ValueError):
        p.blocker_plan(seal(core), self.protocol)

  def test_synthetic_rows_cannot_claim_frozen_public_manifest(self):
    import copy
    from openpilot.tools.cyber_autotune import lane_tail_second_review as b
    from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
    from openpilot.tools.cyber_autotune import lane_public_storage as s

    core = unseal(copy.deepcopy(self.diag))
    core['manifest_scope'] = 'PUBLIC_COMMA10K_HUMAN_REVIEW'
    core['manifest_sha256'] = w.MANIFEST_SHA
    core['status'] = 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE'
    for i, raw in enumerate(core['row_provenance']):
      relation = unseal(raw)
      relation['manifest_sha256'] = w.MANIFEST_SHA
      core['row_provenance'][i] = seal(relation)
    actual = s.read_json(p.ROOT / 'docs/cyberpilot/changes/comma10k-completed-full-human-review-manifest.json')
    with self.assertRaises(ValueError):
      p.blocker_plan(seal(core), b.protocol(actual))

  def test_actual_public_provenance_must_match_all_original_frame_hashes(self):
    import copy
    from collections import Counter
    from openpilot.tools.cyber_autotune import lane_public_storage as s
    from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d
    from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
    from openpilot.tools.cyber_autotune import lane_tail_review_contract as c

    docs = p.ROOT / 'docs/cyberpilot/changes'
    m = s.read_json(docs / 'comma10k-completed-full-human-review-manifest.json')
    human = s.read_json(docs / 'comma10k-assisted-human-review-v1.json')
    ai = s.read_json(docs / 'comma10k-ai-prereview-results-v1.json')
    rows, suggestions, bindings = d.validate_assisted(m, human, ai['experiment'], ai['suggestions'])
    core = {
      'human_export_sha256': human['receipt_sha256'],
      'experiment_sha256': ai['experiment']['receipt_sha256'],
      'row_provenance': bindings,
      'concordance': d.concordance(rows, suggestions),
      'categories': {},
    }
    for label in c.LABELS:
      members = [r for r in rows if r['reviewer_label'] == label]
      ids = [r['frame_id'] for r in members]
      frames = [f for f in m['frames'] if f['frame_id'] in ids]
      scores = Counter('UNAVAILABLE' if f['confidence']['median'] is None else t.confidence_bucket(f['confidence']['median']) for f in frames)
      core['categories'][label] = {
        'frame_ids': ids,
        'reviewable': sum(r['reviewable'] for r in members),
        'detector_confidence_distribution': dict(sorted(scores.items())),
        'y_region_distribution': {key: sum(f['regions'][key]['pred_to_gt']['sample_count'] for f in frames) for key in d.REGIONS},
      }
    d.validate_public_binding(core)
    for field in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256', 'human_annotation_sha256', 'first_exposure_sha256'):
      bad = copy.deepcopy(core)
      row = unseal(bad['row_provenance'][0])
      row[field] = 'f' * 64
      bad['row_provenance'][0] = seal(row)
      with self.subTest(field=field), self.assertRaises(ValueError):
        d.validate_public_binding(bad)

  def test_original_pooled_metric_values_cannot_be_resealed(self):
    import copy
    from openpilot.tools.cyber_autotune import lane_public_storage as s
    from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d

    frozen = s.read_json(p.ROOT / 'docs/cyberpilot/changes/comma10k-assisted-original-metric-summary-v1.json')['summary']
    core = {k: v for k, v in frozen.items() if k != 'category_metrics'}
    core['categories'] = copy.deepcopy(frozen['category_metrics'])
    d.validate_public_metric_binding(core)
    for target in ('median', 'category', 'availability', 'trace'):
      bad = copy.deepcopy(core)
      if target == 'median':
        bad['metrics']['pred_to_gt']['median'] = 0
      elif target == 'category':
        bad['categories']['DETECTOR_MISS']['metrics']['gt_to_pred']['p95'] = 0
      elif target == 'availability':
        bad['metric_availability']['pred_to_gt']['unavailable_frames'] = 0
      elif target == 'trace':
        bad['metric_trace_receipts'][0]['trace_sha256'] = 'f' * 64
      with self.subTest(target=target), self.assertRaises(ValueError):
        d.validate_public_metric_binding(bad)
