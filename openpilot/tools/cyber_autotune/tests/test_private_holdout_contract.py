import copy
import io
from PIL import Image
import tempfile
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


def manifest():
  rows = [{'route_id': SHA, 'segment_id': f'{i:064x}', 'source_sha256': SHA, 'source_bytes': 100,
           'frame_count': 100, 'width': 526, 'height': 330, 'fps': 20., 'codec': 'h264',
           'camera_role': 'NARROW_ROAD', 'source_key': f'segment-{i}/qcamera.ts'} for i in range(60)]
  return p.freeze_manifest(rows, p.sampling_policy(STAMP), SHA, STAMP)


def setup_package(root):
  m = manifest()
  auth = h.authorize(m, 'a' * 40, STAMP, acknowledged=True)
  data = None
  if root is not None:
    output = io.BytesIO()
    Image.new('RGB', (526, 330), '#426078').save(output, format='PNG')
    data = output.getvalue()
    (root / 'images').mkdir()
  images = [h.image_receipt(m, auth, r['sample_id'], p.digest(data) if data else SHA) for r in h.holdouts(m)]
  if data:
    for image in images:
      (root / 'images' / (image['sample_id'] + '.png')).write_bytes(data)
  package = h.materialization_complete(m, auth, images)
  return m, auth, package


def payload(state='BOTH_EGO_BOUNDARIES_VISIBLE'):
  return {'state': state, 'left': [[100., 300.], [110., 200.], [120., 100.]],
          'right': [[400., 300.], [390., 200.], [380., 100.]],
          'acknowledged_blind': True, 'reviewer_id': 'reviewer-opaque-1'}


class TestHoldoutContract(unittest.TestCase):
  def setUp(self):
    self.m = manifest()
    self.auth = h.authorize(self.m, SHA[:40], STAMP, acknowledged=True)
    self.samples = h.holdouts(self.m)
    self.image = h.image_receipt(self.m, self.auth, self.samples[0]['sample_id'], SHA)

  def test_exact_sixty_original_holdout_ids(self):
    self.assertEqual(len(self.samples), 60)
    self.assertEqual(self.auth['holdout_selection_sha256'], p.digest(p.canonical(self.samples)))
    self.assertEqual(self.samples, [r for r in self.m['selected'] if r['role'] == 'HOLDOUT'])

  def test_authorization_required(self):
    with self.assertRaises(ValueError):
      h.authorize(self.m, SHA[:40], STAMP, acknowledged=False)
    with self.assertRaises(ValueError):
      h.require_materialization(self.m, None, self.samples[0]['sample_id'])

  def test_development_cannot_materialize(self):
    with self.assertRaises(ValueError):
      h.require_materialization(self.m, self.auth, self.m['selected'][0]['sample_id'])

  def test_resealed_auth_drift_rejected(self):
    changed = {**self.auth, 'holdout_selection_sha256': 'b' * 64}
    with self.assertRaises(ValueError):
      h.require_materialization(self.m, seal({k: v for k, v in changed.items() if k != 'receipt_sha256'}), self.samples[0]['sample_id'])

  def test_incomplete_and_duplicate_materialization_rejected(self):
    for rows in ([self.image], [self.image] * 60):
      with self.assertRaises(ValueError):
        h.materialization_complete(self.m, self.auth, rows)

  def test_pixel_point_order_and_bounds(self):
    for bad in ([[-1., 300.], [10., 200.], [20., 100.]],
                [[10., 100.], [10., 200.], [10., 300.]],
                [[10., 300.], [10., 300.], [20., 100.]],
                [[float('nan'), 300.], [10., 200.], [20., 100.]]):
      body = payload()
      body['left'] = bad
      with self.assertRaises(ValueError):
        h.annotation(self.image, body, STAMP)

  def test_crossing_rejected(self):
    body = payload()
    body['right'][1][0] = 105.
    with self.assertRaises(ValueError):
      h.annotation(self.image, body, STAMP)

  def test_one_side_visible(self):
    body = payload('LEFT_ONLY_VISIBLE')
    body['right'] = []
    row = h.annotation(self.image, body, STAMP)
    self.assertEqual(row['right'], [])
    self.assertEqual(h.pixel_center(row), [])

  def test_ambiguous_requires_empty_and_no_center(self):
    body = payload('EGO_BOUNDARIES_AMBIGUOUS')
    with self.assertRaises(ValueError):
      h.annotation(self.image, body, STAMP)
    body['left'] = body['right'] = []
    row = h.annotation(self.image, body, STAMP)
    self.assertEqual(h.pixel_center(row), [])

  def test_center_only_common_observed_support(self):
    body = payload()
    body['right'] = [[400., 250.], [390., 175.], [380., 125.]]
    center = h.pixel_center(h.annotation(self.image, body, STAMP))
    self.assertTrue(all(125. <= y <= 250. for _, y in center))
    self.assertEqual(center[0][1], 250.)

  def test_exposure_flags_cannot_enter_human_request(self):
    body = {**payload(), 'ai_suggestion_exposed_before_save': True}
    with self.assertRaises(ValueError):
      h.annotation(self.image, body, STAMP)

  def test_ack_required(self):
    body = {**payload(), 'acknowledged_blind': False}
    with self.assertRaises(ValueError):
      h.annotation(self.image, body, STAMP)

  def test_schema_units_and_no_promotion(self):
    row = h.annotation(self.image, payload(), STAMP)
    self.assertFalse(row['detector_prediction_exposed_before_save'])
    self.assertFalse(row['ai_suggestion_exposed_before_save'])
    self.assertFalse(row['model_output_exposed_before_save'])
    self.assertFalse(row['sealed_reference_allowed'])
    self.assertEqual(row['coordinate_policy'], h.COORDINATES)

  def test_correction_preserves_first_receipt(self):
    first = h.annotation(self.image, payload(), STAMP)
    correction = h.correction(first, payload('BOTH_EGO_BOUNDARIES_VISIBLE'), STAMP, 'Point placement recheck')
    self.assertEqual(correction['first_decision_sha256'], first['receipt_sha256'])
    self.assertEqual(correction['provenance'], 'POST_DECISION_CORRECTION_NOT_NEW_BLIND_FIRST_DECISION')
    self.assertEqual(first['schema'], 'PRIVATE_BLIND_PIXEL_FIRST_DECISION_V1')

  def test_display_coordinate_conversion(self):
    self.assertEqual(h.original_point(75., 50., 50., 25., 2.), [12.5, 12.5])

  def test_no_reference_before_sixty_decisions(self):
    _, _, package = setup_package(None)
    row = h.annotation(package['images'][0], payload(), STAMP)
    with self.assertRaises(ValueError):
      h.freeze_reference(package, [row], STAMP)

  def test_complete_reference_and_detector_gate(self):
    _, _, package = setup_package(None)
    rows = [h.annotation(image, payload(), STAMP) for image in package['images']]
    reference = h.freeze_reference(package, rows, STAMP)
    h.require_detector_gate(package, reference)
    self.assertEqual(len(reference['annotations']), 60)
    self.assertFalse(reference['qualification_allowed'])

  def test_changed_image_and_annotation_rejected(self):
    _, _, package = setup_package(None)
    rows = [h.annotation(image, payload(), STAMP) for image in package['images']]
    rows[0] = {**rows[0], 'image_sha256': 'b' * 64}
    with self.assertRaises(ValueError):
      h.freeze_reference(package, rows, STAMP)

  def test_immutable_atomic_save(self):
    with tempfile.TemporaryDirectory(dir=Path.home()) as temp:
      path = Path(temp) / 'row.json'
      row = h.annotation(self.image, payload(), STAMP)
      h.write_immutable(path, row)
      h.write_immutable(path, copy.deepcopy(row))
      with self.assertRaises(ValueError):
        h.write_immutable(path, {**row, 'image_sha256': 'b' * 64})
      self.assertEqual(h.read(path), row)


  def test_human_pixel_reference_cannot_enter_sealed_meter_admission(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_reference_input import _decode_payload
    _, _, package = setup_package(None)
    rows = [h.annotation(image, payload(), STAMP) for image in package['images']]
    reference = h.freeze_reference(package, rows, STAMP)
    with self.assertRaises(ValueError):
      _decode_payload(h.canonical(reference), grant=None, sample_count=60, coverage_policy=None)


  def test_duplicated_package_images_do_not_satisfy_reference_gate(self):
    _, _, package = setup_package(None)
    forged = seal({k: ([package['images'][0]] * 60 if k == 'images' else v)
                   for k, v in package.items() if k != 'receipt_sha256'})
    row = h.annotation(package['images'][0], payload(), STAMP)
    with self.assertRaises(ValueError):
      h.freeze_reference(forged, [row] * 60, STAMP)

  def test_reference_freeze_cannot_predate_human_decisions(self):
    _, _, package = setup_package(None)
    rows = [h.annotation(image, payload(), '2026-10-10T00:00:00Z') for image in package['images']]
    with self.assertRaises(ValueError):
      h.freeze_reference(package, rows, STAMP)

  def test_symlink_store_rejected(self):
    with tempfile.TemporaryDirectory(dir=Path.home()) as temp:
      target = Path(temp) / 'target'
      target.mkdir()
      link = Path(temp) / 'link'
      link.symlink_to(target, target_is_directory=True)
      with self.assertRaises(ValueError):
        h.write_immutable(link / 'row.json', self.image)
