"""Source-defined software arithmetic; never physical calibration evidence."""
import copy
import math
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import physical_projection_uncertainty as u
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
try:
  from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q
except ImportError:
  q = None


def registered_fixture(cal):
  r = q.source_registration()
  r['scope'] = 'TEST_ONLY'
  r['status'] = 'PIXEL_GEOMETRY_REGISTRATION_VALIDATED'
  r['crop_rectangle'] = [0, 0, 1344, 760]
  r['resize_rule'] = 'ZERO_ORIGIN'
  r['affine'] = q.affine([1344, 760], [526, 330], r['crop_rectangle'], r['resize_rule'])
  r['residual_bound_native_px'] = .1
  r['checks'] = {key: {'status': 'PASS_TEST_ONLY', 'evidence_sha256': 'a' * 64} for key in r['checks']}
  r['distortion_status'] = 'PRESERVED_TEST_ONLY'
  r = c.seal({k: v for k, v in r.items() if k != 'receipt_sha256'})
  return q.projection_mapping(r, cal)


class TestQcameraRegistration(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(q, 'qcamera registration module missing')

  def test_recorded_source_distinct_from_current_source(self):
    r = q.source_registration()
    self.assertEqual(r['recording_commit'], '5a970f1ad25d9f07d055955d7a7c14603b6b7813')
    self.assertEqual(r['native_wh'], [1344, 760])
    self.assertEqual(r['raw_sensor_wh'], [2688, 1520])
    self.assertEqual(r['source_wh'], [526, 330])
    self.assertEqual(r['sensor'], 'os04c10')

  def test_hardware_phase_and_residual_not_invented(self):
    r = q.source_registration()
    self.assertEqual(r['status'], 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL')
    self.assertIsNone(r['affine'])
    self.assertIsNone(r['resize_rule'])
    self.assertIsNone(r['residual_bound_native_px'])
    self.assertFalse(r['qualification_allowed'])

  def test_historical_pipeline_file_hashes_bound(self):
    # Recording commit is not an ancestor of this branch. The completed source
    # audit is pinned, rather than depending on an unreferenced local Git object
    # or fetching network data during an offline regression.
    r = q.source_registration()
    self.assertEqual(digest(canonical(r['recorded_source_files'])),
                     '1b6f40aaac9a42bac92e401349b35628d9a5760bd132ff78faafb91e993685f4')
    self.assertEqual(len(r['recorded_source_files']),16)
    for value in r['recorded_source_files'].values():
      c.sha(value)

  def test_current_pipeline_file_hashes_bound(self):
    for path, sha in q.source_registration()['current_source_files'].items():
      self.assertEqual(digest((c.ROOT / path).read_bytes()), sha, path)

  def test_center_aligned_known_points(self):
    a = q.affine([1344, 760], [526, 330], [0, 0, 1344, 760], 'CENTER_ALIGNED')
    p = np.array([[0., 0.], [262.5, 164.5], [525., 329.]])
    got = q.forward(p, a)
    np.testing.assert_allclose(got[1], [671.5, 379.5], atol=1e-12)
    np.testing.assert_allclose(got[0], [.5 * 1344 / 526 - .5, .5 * 760 / 330 - .5], atol=1e-12)

  def test_crop_offset_and_anisotropy(self):
    a = q.affine([100, 80], [10, 10], [8, 6, 60, 40], 'ZERO_ORIGIN')
    np.testing.assert_array_equal(q.forward([[2, 3]], a), [[20, 18]])
    self.assertEqual(a['scale_x'], 6)
    self.assertEqual(a['scale_y'], 4)

  def test_half_pixel_is_not_zero_origin(self):
    args = ([1344, 760], [526, 330], [0, 0, 1344, 760])
    a, b = q.affine(*args, 'CENTER_ALIGNED'), q.affine(*args, 'ZERO_ORIGIN')
    self.assertGreater(abs(a['offset_x_px'] - b['offset_x_px']), .5)

  def test_fixed_grid_exact_round_trip(self):
    a = q.affine([1344, 760], [526, 330], [0, 0, 1344, 760], 'CENTER_ALIGNED')
    p = [[float(x), float(y)] for y in np.linspace(0, 329, 9) for x in np.linspace(0, 525, 11)]
    np.testing.assert_allclose(q.inverse(q.forward(p, a), a), p, atol=2e-13, rtol=0)

  def test_corner_aligned_distinct_hypothesis(self):
    a = q.affine([1344, 760], [526, 330], [0, 0, 1344, 760], 'CORNER_ALIGNED')
    np.testing.assert_allclose(q.forward([[525, 329]], a), [[1343, 759]], atol=1e-12)

  def test_principal_point_intrinsics_transform(self):
    a = q.affine([100, 80], [10, 10], [8, 6, 60, 40], 'CENTER_ALIGNED')
    k = [[90., 0, 50.], [0, 80., 40.], [0, 0, 1.]]
    out = q.intrinsics(k, a)
    self.assertEqual(out['provenance'], 'STATIC_INTRINSICS_PRIOR_PLUS_CONDITIONAL_IMAGE_TRANSFORM')
    np.testing.assert_allclose(out['matrix'], [[15, 0, (50-10.5)/6], [0, 20, (40-7.5)/4], [0, 0, 1]])
    self.assertFalse(out['independently_calibrated'])

  def test_nonfinite_bad_crop_or_rule_rejected(self):
    for crop, rule in [([-1,0,1344,760],'ZERO_ORIGIN'),([0,0,1345,760],'ZERO_ORIGIN'),([0,0,1344,760],'UNKNOWN')]:
      with self.assertRaises(ValueError):
        q.affine([1344,760],[526,330],crop,rule)
    with self.assertRaises(ValueError):
      q.forward([[math.nan, 5]], q.affine([1344,760],[526,330],[0,0,1344,760],'ZERO_ORIGIN'))

  def test_unknown_sensor_dimensions_or_distortion_rejected(self):
    m, i = fixture()
    cal = c.admit(m, i)
    mapping = registered_fixture(cal)
    for key, value in [('sensor', 'ar0231'), ('native_wh', [1928,1208]), ('distortion_status', 'UNKNOWN')]:
      bad = copy.deepcopy(mapping['registration'])
      bad[key] = value
      bad = c.seal({k:v for k,v in bad.items() if k!='receipt_sha256'})
      with self.assertRaises(ValueError):
        q.projection_mapping(bad, cal)

  def test_partial_registration_meter_results_null(self):
    m, i = fixture()
    cal = c.admit(m, i)
    mapping = q.projection_mapping(q.source_registration(), cal)
    out = u.report(cal, {'grade_rad':.001,'camber_rad':.001,'nonplanarity_m':.002,'annotation_px':.5,'source_sha256':'a'*64}, mapping)
    self.assertEqual(out['status'], 'PIXEL_GEOMETRY_REGISTRATION_PENDING')
    self.assertIsNone(out['meter_results'])

  def test_legacy_boolean_mapping_cannot_enable_meter(self):
    m, i = fixture()
    cal = c.admit(m, i)
    old = {'schema':'OBSERVED_PIXEL_CAMERA_MAPPING_V1','source_wh':[526,330],'target_wh':[1344,760],
           'scale_x':1344/526,'scale_y':760/330,'offset_x_px':0.,'offset_y_px':0.,
           'verified_same_camera':True,'verified_crop_resize':True,'evidence_sha256':'b'*64,
           'mapping_residual_bound_px':.1}
    with self.assertRaises(ValueError):
      u.mapping_check(old, cal)
    with self.assertRaises(ValueError):
      u.envelope(u.query(cal,20.,0.), cal,
                 {'grade_rad':.001,'camber_rad':.001,'nonplanarity_m':.002,'annotation_px':.5,'source_sha256':'a'*64}, old)

  def test_registered_test_scope_cannot_be_physical(self):
    m, i = fixture()
    cal = c.admit(m, i)
    mapping = registered_fixture(cal)
    self.assertEqual(mapping['registration']['scope'], 'TEST_ONLY')
    # Constructed admission-scope negative control, not an actual measurement.
    m['scope'] = 'INDEPENDENT_PHYSICAL'
    other_scope = c.admit(m, i)
    self.assertEqual(other_scope['status'], 'CALIBRATION_EVIDENCE_ADMITTED')
    with self.assertRaisesRegex(ValueError, 'TEST_REGISTRATION_CANNOT_BIND_PHYSICAL_CALIBRATION'):
      q.projection_mapping(mapping['registration'], other_scope)
    with self.assertRaisesRegex(ValueError, 'TEST_REGISTRATION_CANNOT_BIND_PHYSICAL_CALIBRATION'):
      u.report(other_scope, None, mapping)
    other_m, other_i = fixture('ar0231')
    with self.assertRaises(ValueError):
      q.projection_mapping(q.source_registration(), c.admit(other_m, other_i))

  def test_historical_pixels_unchanged(self):
    p = u.pixel_input()
    self.assertEqual(p['source_sha256'], u.PIXEL_RECEIPT)
    self.assertEqual(p['center']['available_frames'], 44)
    self.assertEqual(p['center']['unavailable_frames'], 11)

  def test_normalized_detector_contract_round_trip(self):
    points = [[0.,0.],[.5,.75],[525/526,329/330]]
    restored = q.detector_restore(points)
    np.testing.assert_allclose(restored, [[0,0],[263,247.5],[525,329]], atol=1e-12)
    np.testing.assert_allclose(q.detector_normalize(restored), points, atol=1e-15)

  def test_detector_resize_center_rule_separate_from_normalized_output(self):
    d = q.detector_contract()
    self.assertEqual(d['canonical_wh'], [1640,590])
    self.assertEqual(d['crop_xyxy'], [0,270,1640,590])
    self.assertEqual(d['model_wh'], [800,320])
    self.assertEqual(d['restoration'], 'NORMALIZED_SPLINE_X_TIMES_SOURCE_WIDTH_Y_ROWS_DIV_SOURCE_HEIGHT')
    self.assertFalse(d['resampling_inverse_proven'])

  def test_canvas_css_dpr_zoom_pan_round_trip(self):
    point = [123.25, 210.75]
    for rect, zoom, pan in [([20.,30.,550.,340.],1.,[0.,0.]),([17.,80.,330.,204.],1.5,[22.,-13.])]:
      # DPR is not multiplied: PointerEvent coordinates are CSS pixels.
      client = [rect[0]+(point[0]*zoom+pan[0])*rect[2]/1100,
                rect[1]+(point[1]*zoom+pan[1])*rect[3]/680]
      np.testing.assert_allclose(q.canvas_to_original(client,rect,[1100,680],zoom,pan),point,atol=1e-12)

  def test_registration_alone_not_calibration(self):
    out = u.report(None,None,None)
    self.assertEqual(out['status'],'CALIBRATION_MEASUREMENT_PENDING')
    self.assertIsNone(out['meter_results'])

  def test_visualizer_label_and_no_external_assets(self):
    text=q.visualizer(q.source_registration())
    self.assertIn('SOFTWARE COORDINATE REGISTRATION',text)
    self.assertIn('NOT PHYSICAL CALIBRATION',text)
    self.assertIn('id="qimage"',text)
    self.assertIn('id="qprincipal"',text)
    self.assertIn('HARDWARE RESIZE PHASE PENDING',text)
    self.assertNotIn('https://',text)

  def test_h264_visible_crop_not_native_optical_crop(self):
    # Baseline SPS: 33x21 macroblocks, progressive4:2:0, right1/bottom3 crop units.
    def ue(v):
      bits=bin(v+1)[2:]
      return '0'*(len(bits)-1)+bits
    bits=f'{66:08b}'+'0'*16+ue(0)+ue(0)+ue(0)+ue(0)+ue(1)+'0'+ue(32)+ue(20)+'1'+'1'+'1'
    bits+=ue(0)+ue(1)+ue(0)+ue(3)+'1'
    bits+='0'*((-len(bits))%8)
    payload=int(bits,2).to_bytes(len(bits)//8,'big')
    out=q.sps_layout(payload)
    self.assertEqual(out['coded_wh'],[528,336])
    self.assertEqual(out['visible_wh'],[526,330])
    self.assertEqual(out['display_crop_lrtb_px'],[0,2,0,6])
    self.assertFalse(out['proves_native_crop'])

  def test_h264_truncated_rejected(self):
    with self.assertRaises(ValueError):
      q.sps_layout(b'\x42')

  def test_no_real_native_derivative_without_registration(self):
    with self.assertRaises(ValueError):
      q.native_derivative([[250,250]],q.source_registration())

  def test_self_declared_real_validation_rejected(self):
    m, i = fixture()
    cal = c.admit(m, i)
    r = registered_fixture(cal)['registration']
    r['scope'] = 'INDEPENDENT_PHYSICAL'
    r = c.seal({k:v for k,v in r.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      q.validate_registration(r, numeric=True)

  def test_tampered_mapping_receipt_rejected(self):
    r = q.source_registration()
    r['resize_rule'] = 'CENTER_ALIGNED'
    with self.assertRaises(ValueError):
      q.validate_registration(r)

  def test_pending_cannot_smuggle_affine_or_residual(self):
    for key, value in [('affine', {}), ('residual_bound_native_px', 0.), ('qualification_allowed', True)]:
      r = q.source_registration()
      r[key] = value
      r = c.seal({k:v for k,v in r.items() if k!='receipt_sha256'})
      with self.assertRaises(ValueError):
        q.validate_registration(r)

  def test_pending_envelope_extra_field_rejected(self):
    m, i = fixture()
    cal = c.admit(m, i)
    mapping = q.projection_mapping(q.source_registration(), cal)
    mapping['meter_override'] = 0.
    with self.assertRaises(ValueError):
      u.report(cal, None, mapping)

  def test_bad_canvas_bounds_rejected(self):
    for rect in ([0,0,0,680], [0,0,1100,math.inf]):
      with self.assertRaises(ValueError):
        q.canvas_to_original([50,50], rect, [1100,680], 1, [0,0])

  def test_anisotropic_lateral_error_uses_x_jacobian(self):
    a = q.affine([1344,760],[526,330],[0,0,1344,760],'CENTER_ALIGNED')
    delta = q.forward([[100,200],[105,200]],a)
    self.assertAlmostEqual(delta[1,0]-delta[0,0], 5*1344/526)
    self.assertNotAlmostEqual(a['scale_x'], a['scale_y'])
    self.assertAlmostEqual(delta[1,1]-delta[0,1], 0.)

  def test_native_derivative_separate_test_only_receipt(self):
    m, i = fixture()
    r = registered_fixture(c.admit(m,i))['registration']
    values = [[100.,200.],[200.,250.]]
    before = copy.deepcopy(values)
    out = q.native_derivative(values,r)
    self.assertEqual(values,before)
    self.assertFalse(out['original_modified'])
    self.assertEqual(out['scope'],'TEST_ONLY')
    self.assertFalse(out['sealed_reference_allowed'])

  def test_frozen_source_receipt_repeatability(self):
    self.assertEqual(q.source_registration(),q.source_registration())
    self.assertEqual(q.audit()['receipt_sha256'],q.AUDIT_SHA)
    import json
    stored = json.loads((c.ROOT/'docs/cyberpilot/changes/qcamera-pixel-registration-v1.json').read_bytes())
    self.assertEqual(stored, q.source_registration())
    from openpilot.tools.cyber_autotune.lane_tail_report import unseal
    origin = json.loads((c.ROOT/'docs/cyberpilot/changes/qcamera-recording-origin-binding-v1.json').read_bytes())
    unseal(origin)
    self.assertEqual(origin['registration_sha256'], stored['receipt_sha256'])
    self.assertEqual(origin['source_audit_sha256'], q.AUDIT_SHA)
    self.assertEqual(origin['public_recording_repository_counts'], {'https://github.com/ajouatom/openpilot.git':60})
    self.assertFalse(origin['image_decode'])
    self.assertFalse(origin['new_holdout_access'])
