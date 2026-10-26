"""Prospective public synthetic ownership contract; no runtime activation."""
import copy
import json
import unittest
from dataclasses import FrozenInstanceError, fields
from openpilot.tools.cyber_autotune import curvature_yaw_publication as publication
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import build_case
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

class TestOwnedDiagnosticPublication(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    case = build_case('sharp_mid_left', {'factor_high_fraction': 0.0, 'friction_high_fraction': 0.0}, role='STRESS')
    cls.request = canonical(case['requests'][0])
    cls.result = publication.produce_diagnostics(cls.request, offline_publication_v1=True)

  def test_complete_owned_packet_and_frozen_view(self):
    result = publication.admit_publication(self.result.packet, offline_publication_v1=True)
    self.assertEqual(len(result.observations), 401)
    self.assertEqual(result.request_payload, self.request)
    self.assertEqual(result.request_sha256, digest(self.request))
    for field in fields(result.observations[0]):
      with self.assertRaises(FrozenInstanceError):
        setattr(result.observations[0], field.name, 999.0)

  def test_projection_does_not_alias_checked_values(self):
    mutable = self.result.project()
    mutable['observations'][0]['kp'] = 999.0
    mutable['repetition_sha256'][0] = '0' * 64
    self.assertNotEqual(self.result.observations[0].kp, 999.0)
    self.assertNotEqual(self.result.repetition_sha256[0], '0' * 64)
    self.assertEqual(publication.admit_publication(self.result.packet, offline_publication_v1=True).packet, self.result.packet)

  def test_exact_source_tuple_not_version_only(self):
    packet = json.loads(self.result.packet)
    packet['sources']['curvature_yaw_diagnostics_offline_v1.py'] = '0' * 64
    packet['receipt_sha256'] = digest(canonical({k: v for k, v in packet.items() if k != 'receipt_sha256'}))
    with self.assertRaisesRegex(ValueError, 'PUBLICATION_SOURCE_OR_RECEIPT_MISMATCH'):
      publication.admit_publication(canonical(packet), offline_publication_v1=True)

  def test_immutable_request_required(self):
    for value in (False,None,0,1,'true','false'):
      with self.assertRaisesRegex(ValueError,'OFFLINE_PUBLICATION_OPT_IN_REQUIRED'):
        publication.produce_diagnostics(b'bad',offline_publication_v1=value)
    with self.assertRaisesRegex(ValueError,'OFFLINE_PUBLICATION_OPT_IN_REQUIRED'):
      publication.produce_diagnostics(b'bad')
    bad = json.loads(self.request)
    with self.assertRaisesRegex(ValueError, 'INVALID_REQUEST_SIZE'):
      publication.produce_diagnostics(bad, offline_publication_v1=True)

  def test_invalid_private_numeric_rejected(self):
    packet = json.loads(self.result.packet)
    bad = copy.deepcopy(packet)
    bad['payload']['request']['native']['frames'][0]['speed_mps'] = None
    bad['receipt_sha256'] = digest(canonical({k: v for k, v in bad.items() if k != 'receipt_sha256'}))
    with self.assertRaises(ValueError):
      publication.admit_publication(canonical(bad), offline_publication_v1=True)

  def test_publication_generation_cannot_reuse_stale_version(self):
    owner = publication.DiagnosticChannel(offline_publication_v1=True)
    first = owner.publish_request(self.request, expected_generation=0, offline_publication_v1=True)
    second = owner.publish_request(self.request, expected_generation=1, offline_publication_v1=True)
    self.assertEqual((first.generation, second.generation), (1, 2))
    self.assertEqual(first.publication.packet, second.publication.packet)
    with self.assertRaisesRegex(ValueError, 'PUBLICATION_STALE_GENERATION'):
      owner.publish_request(self.request, expected_generation=1, offline_publication_v1=True)
    self.assertIs(owner.read(offline_publication_v1=True), second)
