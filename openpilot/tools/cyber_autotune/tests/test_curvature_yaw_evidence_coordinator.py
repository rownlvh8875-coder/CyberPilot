import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car import structs

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import OfflineTorqueCommandContract
from openpilot.tools.cyber_autotune.contracts import MetricContract
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import (
  reference_evidence_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import (
  closed_loop_state_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator import (
  FrozenThreeArmEvidenceContract,
  build_declaration_manifest,
  declaration_manifest_sha256,
  run_frozen_three_arm_experiment,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import encode_request
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import (
  closed_loop_frames,
  initial_state,
)
from openpilot.tools.cyber_autotune.curvature_yaw_reference_input import (
  ReferenceEvidenceGrant,
  encode_reference_document,
  retain_reference_evidence,
)
from openpilot.tools.cyber_autotune.curvature_yaw_three_arm import (
  CurvatureYawArmDeclaration,
  CurvatureYawThreeArmExperiment,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import (
  ClosedLoopDomain,
  frames_sha256,
)
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA
from openpilot.tools.cyber_autotune.tests.test_curvature_yaw_comparison import (
  curved_request,
  reference_fixture,
)


def h(char):
  return char * 64


def with_factor(request, factor):
  changed = copy.deepcopy(request)
  raw = base64.b64decode(changed['native']['car_params_base64'])
  with structs.CarParams.from_bytes(raw) as reader:
    cp = reader.as_builder()
  cp.lateralTuning.torque.latAccelFactor = factor
  raw = cp.to_bytes()
  changed['native']['car_params_base64'] = base64.b64encode(raw).decode()
  changed['native']['car_params_sha256'] = hashlib.sha256(raw).hexdigest()
  return changed


def distinct_experiment():
  base = curved_request()
  requests = (
    with_factor(base, 2.5),
    with_factor(base, 3.0),
    with_factor(base, 3.5),
  )
  frames = closed_loop_frames(requests[0])
  reference = reference_fixture(len(frames))
  coverage = CoveragePolicy(
    h('b'), tuple(sorted((name, 1) for name in REQUIRED_STRATA)),
  )
  contract = MetricContract(
    pipeline_sha256=h('c'),
    configuration_sha256=h('d'),
    inputs_sha256=frames_sha256(frames),
    mask_sha256=h('e'),
    reset_policy_sha256=closed_loop_state_sha256(initial_state(requests[0])),
    reference_evidence_sha256=reference_evidence_sha256(reference),
    command=OfflineTorqueCommandContract(
      384, 3, 7, 0.01, 'frozen distinct-arm evidence test',
    ),
    alignment_delay_s=0.0,
    reversal_deadband_ratio_per_s=0.0,
  )
  arms = tuple(
    CurvatureYawArmDeclaration(arm, encode_request(request))
    for arm, request in zip(
      ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE'),
      requests,
      strict=True,
    )
  )
  experiment = CurvatureYawThreeArmExperiment(
    group_sha256=h('1'),
    review_sha256=h('2'),
    scenario_tags=('straight', 'gentle_curve'),
    arms=arms,
    domain=ClosedLoopDomain(h('5'), 0.01, 3.0, 7.0, 0.02, 'PLANT', 1.0),
    metric_contract=contract,
    coverage_policy=coverage,
    environment_sha256=h('f'),
    plant_calibration_sha256=h('6'),
    primary_minimum_improvement_m=0.00001,
  )
  return experiment, reference


class ReferenceFileFixture:
  def __init__(self, testcase, reference, coverage_policy):
    self.testcase = testcase
    self.reference = reference
    self.coverage_policy = coverage_policy
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.path = self.root / 'reference.json'
    self.manifest_sha256 = h('3')
    payload = encode_reference_document(
      reference,
      manifest_sha256=self.manifest_sha256,
      review_sha256=coverage_policy.review_sha256,
    )
    self.path.write_bytes(payload)
    self.file_sha256 = hashlib.sha256(payload).hexdigest()
    self.grant = ReferenceEvidenceGrant(
      root=str(self.root),
      path='reference.json',
      size_bytes=len(payload),
      file_sha256=self.file_sha256,
      evidence_sha256=reference_evidence_sha256(reference),
      manifest_sha256=self.manifest_sha256,
      review_sha256=coverage_policy.review_sha256,
    )

  def cleanup(self):
    self.temp.cleanup()


class TestCurvatureYawReferenceInput(unittest.TestCase):
  def setUp(self):
    experiment, reference = distinct_experiment()
    self.experiment = experiment
    self.fixture = ReferenceFileFixture(
      self, reference, experiment.coverage_policy,
    )

  def tearDown(self):
    self.fixture.cleanup()

  def test_regular_file_is_sealed_and_semantically_bound(self):
    sample_count = len(closed_loop_frames(
      json.loads(self.experiment.arms[0].request),
    ))
    with retain_reference_evidence(
      self.fixture.grant,
      sample_count=sample_count,
      coverage_policy=self.experiment.coverage_policy,
    ) as (evidence, receipt):
      self.assertEqual(evidence, self.fixture.reference)
      self.assertTrue(receipt.sealed)
      self.assertEqual(
        receipt.evidence_sha256,
        reference_evidence_sha256(self.fixture.reference),
      )
      self.assertFalse(receipt.runtime_accepted)
      self.assertFalse(receipt.promotable)
      self.assertFalse(receipt.vehicle_activation_allowed)

  def test_hash_size_symlink_and_provenance_tamper_fail_closed(self):
    sample_count = 20
    for changes in (
      {'file_sha256': h('0')},
      {'size_bytes': self.fixture.grant.size_bytes - 1},
    ):
      with self.subTest(changes=changes), self.assertRaises(ValueError):
        grant = ReferenceEvidenceGrant(
          **{**self.fixture.grant.__dict__, **changes},
        )
        with retain_reference_evidence(
          grant,
          sample_count=sample_count,
          coverage_policy=self.experiment.coverage_policy,
        ):
          self.fail('invalid reference yielded')

    link = self.fixture.root / 'link.json'
    link.symlink_to(self.fixture.path)
    link_grant = ReferenceEvidenceGrant(
      **{**self.fixture.grant.__dict__, 'path': 'link.json'},
    )
    with self.assertRaises((OSError, ValueError)):
      with retain_reference_evidence(
        link_grant,
        sample_count=sample_count,
        coverage_policy=self.experiment.coverage_policy,
      ):
        self.fail('symlink reference yielded')

    document = json.loads(self.fixture.path.read_text())
    document['candidate_outputs_used_for_reference'] = True
    payload = json.dumps(
      document, sort_keys=True, separators=(',', ':'),
    ).encode()
    tampered = self.fixture.root / 'tampered.json'
    tampered.write_bytes(payload)
    grant = ReferenceEvidenceGrant(
      **{
        **self.fixture.grant.__dict__,
        'path': 'tampered.json',
        'size_bytes': len(payload),
        'file_sha256': hashlib.sha256(payload).hexdigest(),
      },
    )
    with self.assertRaises(ValueError):
      with retain_reference_evidence(
        grant,
        sample_count=sample_count,
        coverage_policy=self.experiment.coverage_policy,
      ):
        self.fail('provenance-tampered reference yielded')


class TestFrozenThreeArmEvidenceCoordinator(unittest.TestCase):
  def setUp(self):
    self.experiment, reference = distinct_experiment()
    self.reference_fixture = ReferenceFileFixture(
      self, reference, self.experiment.coverage_policy,
    )
    manifest = build_declaration_manifest(self.experiment)
    self.manifest = manifest
    self.contract = FrozenThreeArmEvidenceContract(
      version=1,
      declaration_manifest_sha256=declaration_manifest_sha256(manifest),
      reference_file_sha256=self.reference_fixture.grant.file_sha256,
      reference_evidence_sha256=self.reference_fixture.grant.evidence_sha256,
      reference_manifest_sha256=self.reference_fixture.grant.manifest_sha256,
      review_sha256=self.reference_fixture.grant.review_sha256,
      require_distinct_arm_identities=True,
    )

  def tearDown(self):
    self.reference_fixture.cleanup()

  def test_manifest_has_three_distinct_requests_profiles_and_configurations(self):
    self.assertEqual(
      tuple(arm.arm for arm in self.manifest.arms),
      ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE'),
    )
    self.assertEqual(len({arm.request_sha256 for arm in self.manifest.arms}), 3)
    self.assertEqual(len({arm.profile_sha256 for arm in self.manifest.arms}), 3)
    self.assertEqual(
      len({arm.configuration_sha256 for arm in self.manifest.arms}), 3,
    )

  def test_manifest_mismatch_blocks_before_reference_or_native_execution(self):
    bad = FrozenThreeArmEvidenceContract(
      **{
        **self.contract.__dict__,
        'declaration_manifest_sha256': h('0'),
      },
    )
    with (
      patch(
        'openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator.retain_reference_evidence',
      ) as reference,
      patch(
        'openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator.run_three_arm_experiment',
      ) as runner,
    ):
      result = run_frozen_three_arm_experiment(
        self.experiment,
        bad,
        self.reference_fixture.grant,
        timeout_s=10.0,
      )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(
      result.blockers, ('DECLARATION_MANIFEST_BINDING_MISMATCH',),
    )
    self.assertEqual(result.executed_runs, 0)
    reference.assert_not_called()
    runner.assert_not_called()

  def test_identical_arm_requests_block_before_reference_or_native_execution(self):
    payload = self.experiment.arms[0].request
    identical = CurvatureYawThreeArmExperiment(
      **{
        **self.experiment.__dict__,
        'arms': tuple(
          CurvatureYawArmDeclaration(arm, payload)
          for arm in ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
        ),
      },
    )
    manifest = build_declaration_manifest(identical)
    contract = FrozenThreeArmEvidenceContract(
      **{
        **self.contract.__dict__,
        'declaration_manifest_sha256': declaration_manifest_sha256(manifest),
      },
    )
    with (
      patch(
        'openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator.retain_reference_evidence',
      ) as reference,
      patch(
        'openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator.run_three_arm_experiment',
      ) as runner,
    ):
      result = run_frozen_three_arm_experiment(
        identical,
        contract,
        self.reference_fixture.grant,
        timeout_s=10.0,
      )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.blockers, ('ARM_IDENTITIES_NOT_DISTINCT',))
    self.assertEqual(result.executed_runs, 0)
    reference.assert_not_called()
    runner.assert_not_called()

  def test_sealed_reference_failure_blocks_before_native_execution(self):
    bad_grant = ReferenceEvidenceGrant(
      **{
        **self.reference_fixture.grant.__dict__,
        'file_sha256': h('0'),
      },
    )
    contract = FrozenThreeArmEvidenceContract(
      **{
        **self.contract.__dict__,
        'reference_file_sha256': h('0'),
      },
    )
    with patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_evidence_coordinator.run_three_arm_experiment',
    ) as runner:
      result = run_frozen_three_arm_experiment(
        self.experiment,
        contract,
        bad_grant,
        timeout_s=10.0,
      )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.blockers, ('REFERENCE_EVIDENCE_ADMISSION_FAILED',))
    self.assertEqual(result.executed_runs, 0)
    runner.assert_not_called()

  def test_distinct_three_arm_end_to_end_runs_six_and_never_gains_authority(self):
    result = run_frozen_three_arm_experiment(
      self.experiment,
      self.contract,
      self.reference_fixture.grant,
      timeout_s=10.0,
    )
    self.assertEqual(result.status, 'COMPARISON_EVALUATED')
    self.assertEqual(result.executed_runs, 6)
    self.assertIsNotNone(result.reference_admission)
    self.assertTrue(result.reference_admission.sealed)
    self.assertIsNotNone(result.three_arm_result)
    self.assertEqual(len(result.three_arm_result.receipts), 6)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)
    self.assertFalse(result.vehicle_activation_allowed)

    lane_rmse = {
      receipt.arm: next(
        metric.rmse
        for metric in receipt.metrics.metrics
        if metric.name == 'lane_center_offset'
      )
      for receipt in result.three_arm_result.receipts[::2]
    }
    self.assertEqual(len(lane_rmse), 3)
    self.assertGreater(len(set(lane_rmse.values())), 1)


if __name__ == '__main__':
  unittest.main()
