import math
import unittest
from dataclasses import replace


def h(char):
  return char * 64


class TestLateralClosedLoopAdmission(unittest.TestCase):
  def make_case(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import (
      ClosedLoopBinding,
      ClosedLoopDomain,
      ClosedLoopFrame,
      ClosedLoopReceipt,
      ClosedLoopSample,
      frames_sha256,
      timebase_sha256,
      trace_sha256,
    )

    domain = ClosedLoopDomain(h('a'), 0.01, 15.0, 27.0, 0.15, 'PLANT', 1.0)
    frames = tuple(
      ClosedLoopFrame(i, i * 0.01, 20.0, 0.0, 0.01, 0.001, True, False, 0.3)
      for i in range(4)
    )
    samples = tuple(
      ClosedLoopSample(i, i * 0.01, 0.1, 0.09, 0.2 + i * 0.01, 0.01, i * 0.001)
      for i in range(4)
    )
    binding = ClosedLoopBinding(
      software_sha256=h('b'),
      controller_sha256=h('c'),
      adapter_sha256=h('d'),
      plant_sha256=h('e'),
      domain_sha256=domain.identity_sha256,
      inputs_sha256=frames_sha256(frames),
      reset_sha256=h('f'),
      metric_sha256=h('1'),
      environment_sha256=h('2'),
      timebase_sha256=timebase_sha256(frames),
    )
    receipt = ClosedLoopReceipt(
      arm='CYBER_CANDIDATE',
      binding=binding,
      outcome='COMPLETED',
      samples=samples,
      trace_sha256=trace_sha256(samples),
      physical_delay_owners=('PLANT',),
      controller_delay_queue_present=False,
      sendcan_forwarded=False,
      live_can=False,
      vehicle_write=False,
      parameter_write=False,
      runtime_accepted=False,
      promotable=False,
    )
    return domain, frames, receipt
  def test_valid_receipt_is_structurally_admitted_without_authority(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    result = admit_closed_loop_receipt(domain, frames, receipt)

    self.assertEqual(result.status, 'STRUCTURAL_ADMISSION')
    self.assertTrue(result.structural_admission_pass)
    self.assertEqual(result.sample_count, 4)
    self.assertEqual(result.trace_sha256, receipt.trace_sha256)
    self.assertIn('PLANT_CALIBRATION_AUTHENTICITY_UNVERIFIED', result.blockers)
    self.assertIn('INDEPENDENT_REFERENCE_UNVERIFIED', result.blockers)
    self.assertIn('PERFORMANCE_GATE_NOT_EVALUATED', result.blockers)
    self.assertFalse(result.qualified_closed_loop)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_physical_delay_must_have_exactly_one_plant_owner(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    for owners in ((), ('CONTROLLER',), ('PLANT', 'CONTROLLER')):
      with self.subTest(owners=owners):
        result = admit_closed_loop_receipt(
          domain, frames, replace(receipt, physical_delay_owners=owners),
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_PHYSICAL_DELAY_OWNERSHIP', result.blockers)

    result = admit_closed_loop_receipt(
      domain, frames, replace(receipt, controller_delay_queue_present=True),
    )
    self.assertIn('DUPLICATE_ACTUATOR_DELAY_QUEUE', result.blockers)
  def test_domain_timebase_and_input_bindings_fail_closed(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    bad_domain = replace(domain, physical_delay_owner='CONTROLLER')
    self.assertIn(
      'INVALID_DOMAIN', admit_closed_loop_receipt(bad_domain, frames, receipt).blockers,
    )

    discontinuous = frames[:2] + (replace(frames[2], time_s=0.025),) + frames[3:]
    self.assertIn(
      'INVALID_FRAME_TIMEBASE',
      admit_closed_loop_receipt(domain, discontinuous, receipt).blockers,
    )

    out_of_domain = (replace(frames[0], speed_mps=14.9),) + frames[1:]
    self.assertIn(
      'FRAME_OUTSIDE_DOMAIN',
      admit_closed_loop_receipt(domain, out_of_domain, receipt).blockers,
    )

    bad_binding = replace(receipt.binding, inputs_sha256=h('3'))
    self.assertIn(
      'INPUT_BINDING_MISMATCH',
      admit_closed_loop_receipt(domain, frames, replace(receipt, binding=bad_binding)).blockers,
    )

  def test_trace_sample_and_authority_mutations_are_rejected(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    bad_sample = replace(receipt.samples[0], applied_normalized_torque=1.1)
    bad_samples = (bad_sample,) + receipt.samples[1:]
    result = admit_closed_loop_receipt(
      domain, frames, replace(receipt, samples=bad_samples),
    )
    self.assertIn('INVALID_TRACE_SAMPLE', result.blockers)
    result = admit_closed_loop_receipt(
      domain, frames, replace(receipt, trace_sha256=h('4')),
    )
    self.assertIn('TRACE_DIGEST_MISMATCH', result.blockers)

    for field in ('sendcan_forwarded', 'live_can', 'vehicle_write',
                  'parameter_write', 'runtime_accepted', 'promotable'):
      with self.subTest(field=field):
        result = admit_closed_loop_receipt(
          domain, frames, replace(receipt, **{field: True}),
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('FORBIDDEN_AUTHORITY', result.blockers)

  def test_frame_sample_cardinality_and_clock_must_match(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    self.assertIn(
      'TRACE_CARDINALITY_MISMATCH',
      admit_closed_loop_receipt(
        domain, frames, replace(receipt, samples=receipt.samples[:-1]),
      ).blockers,
    )
    shifted = (replace(receipt.samples[0], time_s=0.001),) + receipt.samples[1:]
    self.assertIn(
      'TRACE_TIMEBASE_MISMATCH',
      admit_closed_loop_receipt(
        domain, frames, replace(receipt, samples=shifted),
      ).blockers,
    )

  def test_nonfinite_and_invalid_outcome_are_blocked(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    bad = (replace(receipt.samples[0], yaw_rate_rps=math.nan),) + receipt.samples[1:]
    self.assertIn(
      'INVALID_TRACE_SAMPLE',
      admit_closed_loop_receipt(domain, frames, replace(receipt, samples=bad)).blockers,
    )
    result = admit_closed_loop_receipt(
      domain, frames, replace(receipt, outcome='FAILED'),
    )
    self.assertIn('RUN_NOT_COMPLETED', result.blockers)

  def test_digest_helpers_are_deterministic_and_order_sensitive(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import (
      frames_sha256,
      timebase_sha256,
      trace_sha256,
    )

    _domain, frames, receipt = self.make_case()
    self.assertEqual(frames_sha256(frames), frames_sha256(frames))
    self.assertEqual(timebase_sha256(frames), timebase_sha256(frames))
    self.assertEqual(trace_sha256(receipt.samples), trace_sha256(receipt.samples))
    self.assertNotEqual(frames_sha256(frames), frames_sha256(tuple(reversed(frames))))
    self.assertNotEqual(
      trace_sha256(receipt.samples), trace_sha256(tuple(reversed(receipt.samples))),
    )

  def test_invalid_types_fail_closed_without_exception(self):
    from openpilot.tools.cyber_autotune.lateral_closed_loop import admit_closed_loop_receipt

    domain, frames, receipt = self.make_case()
    for args in (
      (None, frames, receipt),
      (domain, list(frames), receipt),
      (domain, frames, None),
    ):
      with self.subTest(args=args):
        result = admit_closed_loop_receipt(*args)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertFalse(result.structural_admission_pass)
        self.assertFalse(result.runtime_accepted)
        self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
