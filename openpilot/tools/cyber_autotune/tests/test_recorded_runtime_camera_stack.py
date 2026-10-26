import copy
import unittest

from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q
from openpilot.tools.cyber_autotune import recorded_runtime_camera_stack as r
from openpilot.tools.cyber_autotune.native_protocol import digest

KERNEL = 'Linux device 4.9.103 (runner@docker) (gcc version 9.4.0 (Ubuntu 9.4.0-1ubuntu1~20.04.2) ) #1 SMP PREEMPT Thu Sep 17 03:41:40 UTC 2026\n'
BANNER = KERNEL.replace('Linux device ', 'Linux version ')
BUILD = 'f5b3f77e59f1917f95e0752630ca08050463eede\n2026-09-17T03:50:37'


class TestRecordedRuntimeCameraStack(unittest.TestCase):
  def test_evidence_audit_api_available(self):
    self.assertTrue(callable(getattr(r, "bind_runtime", None)), "runtime evidence binding API missing")

  def binding(self, **kw):
    args = {'kernel': KERNEL, 'public_banner': BANNER, 'build': BUILD,
            'os_version': '19.8-carrot-bt1', 'device': 'mici', 'kernel_sha256': digest(KERNEL.encode())}
    return r.bind_runtime(**(args | kw))

  def test_kernel_parser_preserves_build_identity(self):
    self.assertEqual(r.parse_kernel(KERNEL)['release'], '4.9.103')
    self.assertEqual(r.parse_kernel(KERNEL)['normalized_sha256'], r.parse_kernel(BANNER)['normalized_sha256'])

  def test_kernel_parser_does_not_publish_hostname(self):
    self.assertNotIn('device', str(r.parse_kernel(KERNEL)))
    self.assertNotIn('builder@docker', str(r.parse_kernel(KERNEL)))

  def test_malformed_kernel_rejected(self):
    for value in ('4.9.103', KERNEL + 'another line', KERNEL.replace('UTC', 'UNRECOGNIZED')):
      with self.subTest(value=value), self.assertRaises(ValueError):
        r.parse_kernel(value)

  def test_runtime_binding_is_build_only(self):
    x = self.binding()
    self.assertEqual(x['status'], 'RECORDED_KERNEL_BUILD_IDENTITY_BOUND')
    self.assertFalse(x['binary_attested'])
    self.assertEqual(x['kernel_base'], r.KERNEL_BASE)

  def test_stale_raw_kernel_digest_rejected(self):
    with self.assertRaises(ValueError):
      self.binding(kernel_sha256='0'*64)

  def test_mismatched_kernel_build_rejected(self):
    with self.assertRaises(ValueError):
      self.binding(public_banner=BANNER.replace('03:41:40', '03:41:41'))

  def test_same_version_different_compiler_rejected(self):
    with self.assertRaises(ValueError):
      self.binding(public_banner=BANNER.replace('9.4.0', '9.3.0'))

  def test_forged_matching_kernel_pair_rejected(self):
    invented = KERNEL.replace('4.9.103', '9.9.999')
    with self.assertRaises(ValueError):
      self.binding(kernel=invented, public_banner=invented.replace('Linux device ', 'Linux version '),
                   kernel_sha256=digest(invented.encode()))

  def test_wrong_builder_rejected(self):
    with self.assertRaises(ValueError):
      self.binding(build='0'*40)

  def test_wrong_os_or_device_rejected(self):
    for kw in ({'os_version': '19.6'}, {'device': 'tici'}):
      with self.subTest(kw=kw), self.assertRaises(ValueError):
        self.binding(**kw)

  def test_crop_layer_separation(self):
    x = r.crop_layers()
    self.assertEqual(x['codec_display_crop_lrtb'], [0, 2, 0, 6])
    self.assertIsNone(x['effective_native_crop'])
    self.assertEqual(x['visible_wh'], [526, 330])

  def test_codec_padding_cannot_supply_optical_crop(self):
    self.assertNotEqual(r.crop_layers()['codec_display_crop_lrtb'], r.crop_layers()['effective_native_crop'])
    self.assertFalse(r.crop_layers()['codec_padding_is_optical_crop'])

  def test_conditional_orientation(self):
    self.assertEqual(r.orient([[0, 0], [525, 329]], [526, 330], 180, False), [[525, 329], [0, 0]])
    self.assertEqual(r.orient([[0, 0]], [526, 330], 90, False), [[329, 0]])
    self.assertEqual(r.orient([[0, 0]], [526, 330], 0, True), [[525, 0]])

  def test_orientation_rejects_unknown_rule_and_outside_point(self):
    for angle, pts in ((45, [[0, 0]]), (0, [[526, 0]])):
      with self.subTest(angle=angle), self.assertRaises(ValueError):
        r.orient(pts, [526, 330], angle, False)

  def test_hypotheses_not_pruned_without_proof(self):
    self.assertEqual(r.hypotheses()['retained'], list(q.RULES))
    self.assertEqual(r.hypotheses()['pruned'], [])

  def test_claimed_phase_proof_not_admitted(self):
    with self.assertRaises(ValueError):
      r.hypotheses({'excluded': 'ZERO_ORIGIN', 'reason': 'firmware is probably center aligned'})

  def test_conditional_envelope_is_nonexhaustive(self):
    x = r.conditional_envelope([[0, 0], [525, 329]])
    self.assertFalse(x['exhaustive'])
    self.assertFalse(x['physical_uncertainty_bound'])
    self.assertEqual(x['minimum_native_xy'][0], [0, 0])
    self.assertGreater(x['maximum_native_xy'][0][0], 0)
    self.assertIsNone(x['residual_bound_native_px'])

  def test_envelope_deterministic(self):
    self.assertEqual(r.conditional_envelope([[123.5, 200.25]]), r.conditional_envelope([[123.5, 200.25]]))

  def test_envelope_rejects_nonfinite_and_outside_input(self):
    for pts in ([[float('nan'), 0]], [[526, 1]], [[0, -1]]):
      with self.subTest(pts=pts), self.assertRaises(ValueError):
        r.conditional_envelope(pts)

  def test_runtime_and_scaler_receipt_binding(self):
    x = r.readiness()
    self.assertEqual(x['runtime_sha256'], r.load_runtime()['receipt_sha256'])
    self.assertEqual(x['scaler_sha256'], r.load_scaler()['receipt_sha256'])

  def test_firmware_opaque_path_fail_closed(self):
    x = r.readiness()
    self.assertEqual(x['blockers']['HARDWARE_RESIZE_PHASE_PENDING']['status'], 'BLOCKED')
    self.assertIn('HARDWARE_RESIZE_PHASE_FIRMWARE_OPAQUE', x['blockers'])
    self.assertIsNone(x['actual_forward_mapping'])

  def test_distortion_unknown_blocks_registration(self):
    self.assertEqual(r.load_scaler()['distortion_status'], 'DISTORTION_TRANSFORM_UNKNOWN')
    self.assertEqual(r.readiness()['blockers']['DISTORTION_STAGE_ORDERING_PENDING']['status'], 'BLOCKED')

  def test_static_k_source_mapping_is_not_physical_applicability(self):
    x = r.load_scaler()
    self.assertEqual(x['static_intrinsics']['source_matrix'], [[1141.5, 0, 672], [0, 1141.5, 380], [0, 0, 1]])
    self.assertFalse(x['static_intrinsics']['physically_validated'])
    self.assertIsNone(r.readiness()['actual_qcamera_intrinsics'])

  def test_no_fake_residual_or_meter_result(self):
    x = r.readiness()
    self.assertIsNone(x['pixel_mapping_bound_native_px'])
    self.assertIsNone(x['numeric_meter_results'])
    self.assertFalse(x['validated'])

  def test_height_context_cannot_infer_phase(self):
    x = r.readiness()
    self.assertEqual(x['physical_height_context']['value_m'], 1.385)
    self.assertEqual(x['physical_height_context']['use'], 'CONTEXT_ONLY_NOT_SCALER_INPUT')
    self.assertIsNone(x['physical_height_context']['uncertainty_m'])
    self.assertIsNone(x['actual_forward_mapping'])

  def test_new_snapshot_cannot_clear_calibration_or_reference(self):
    x = r.readiness()
    for key in ('CALIBRATION_UNCERTAINTY_PENDING', 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
                'METRIC_CALIBRATION_UNAVAILABLE', 'INDEPENDENT_REFERENCE_UNAVAILABLE'):
      self.assertEqual(x['blockers'][key]['status'], 'BLOCKED')

  def test_receipt_tampering_rejected(self):
    x = copy.deepcopy(r.load_runtime())
    x['kernel_base'] = '0'*40
    with self.assertRaises(ValueError):
      r.validate_runtime(x)

  def test_resealed_claim_cannot_overpromote(self):
    x = copy.deepcopy(r.readiness())
    x.pop('receipt_sha256')
    x['validated'] = True
    x = c.seal(x)
    with self.assertRaises(ValueError):
      r.validate_readiness(x)

  def test_no_private_or_production_authority(self):
    x = r.readiness()
    for key in ('private_images_decoded', 'new_holdout_access', 'detector_inference_this_increment',
                'qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed'):
      self.assertIs(x[key], False)
    self.assertEqual(x['sealed_reference'], 'NOT_GENERATED')

  def test_historical_receipt_identity_preserved(self):
    self.assertEqual(q.source_registration()['source_audit_sha256'], q.AUDIT_SHA)
    self.assertEqual(r.readiness()['previous_readiness_sha256'], '708ad7256727e69cba61e9575ec6bbe3363465f48f9ba221dcbc963281b9d25c')


if __name__ == '__main__':
  unittest.main()
