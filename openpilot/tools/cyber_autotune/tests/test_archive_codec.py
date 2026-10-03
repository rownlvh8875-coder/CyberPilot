from dataclasses import replace
import hashlib
import json
import unittest

from openpilot.tools.cyber_autotune.archive_codec import decode_audit, decode_proposal, encode_audit, encode_proposal
from openpilot.tools.cyber_autotune.audit import append_event
from openpilot.tools.cyber_autotune.profiles import inspect_proposal
from openpilot.tools.cyber_autotune.tests.test_audit import started, terminal
from openpilot.tools.cyber_autotune.tests.test_profiles import proposal


def resign(document):
  content = {key: value for key, value in document.items() if key != 'content_sha256'}
  packed = json.dumps(content, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  document['content_sha256'] = hashlib.sha256(packed).hexdigest()
  return json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class TestArchiveCodec(unittest.TestCase):
  def test_proposal_roundtrip_revalidates_identity_without_authority(self):
    original = proposal()
    payload = encode_proposal(original)
    self.assertEqual(decode_proposal(payload), original)
    document = json.loads(payload)
    self.assertEqual(document['profile_sha256'], inspect_proposal(original).profile_sha256)
    self.assertFalse(document['runtime_accepted'])
    self.assertFalse(document['offline_evaluable'])
    self.assertEqual(encode_proposal(decode_proposal(payload)), payload)

  def test_canonical_numeric_profile_identity_is_distinct_from_archive_bytes(self):
    original = proposal()
    equivalent = replace(original, sample_count=100, review=replace(original.review, minimum=2))
    first, second = encode_proposal(original), encode_proposal(equivalent)
    self.assertEqual(json.loads(first)['profile_sha256'], json.loads(second)['profile_sha256'])
    self.assertNotEqual(first, second)
    self.assertNotEqual(json.loads(first)['content_sha256'], json.loads(second)['content_sha256'])

  def test_disallowed_proposals_cannot_be_serialized(self):
    original = proposal()
    for invalid in (None, replace(original, name='steer_max'), replace(original, name='unknown'),
                    replace(original, unit='Nm'), replace(original, proposed_value=3.),
                    replace(original, sample_count=True), replace(original, confidence=float('nan'))):
      with self.subTest(value=type(invalid)), self.assertRaises(ValueError):
        encode_proposal(invalid)

  def test_resigned_envelope_cannot_bypass_proposal_or_authority_validation(self):
    changes = [lambda d: d.update(runtime_accepted=True), lambda d: d.update(offline_evaluable=1),
               lambda d: d.update(extra='field'), lambda d: d.update(profile_sha256='0' * 64),
               lambda d: d['proposal'].update(unit='Nm'), lambda d: d['proposal'].update(confidence=True),
               lambda d: d['proposal']['binding'].update(extra='unknown'),
               lambda d: d['proposal']['review'].update(minimum_samples=0)]
    for change in changes:
      document = json.loads(encode_proposal(proposal()))
      change(document)
      with self.subTest(change=changes.index(change)), self.assertRaises(ValueError):
        decode_proposal(resign(document))

  def test_bad_byte_payloads_are_rejected_before_becoming_contracts(self):
    valid = encode_proposal(proposal())
    corrupt = json.loads(valid)
    corrupt['proposal']['proposed_value'] = 2.32
    cases = [None, bytearray(valid), b'', valid[:-1], b'null', b'{"a":1,"a":2}', b'{"x":NaN}',
             b'x' * (1048576 + 1), valid + b'\n', json.dumps(corrupt).encode()]
    for payload in cases:
      for decoder in (decode_proposal, decode_audit):
        with self.subTest(decoder=decoder.__name__, payload=type(payload)), self.assertRaises(ValueError):
          decoder(payload)

  def test_audit_start_and_terminal_roundtrip_preserves_incomplete_distinction(self):
    first = append_event((), started())
    completed = append_event(first, terminal(first))
    for chain in (first, completed):
      decoded = decode_audit(encode_audit(chain))
      self.assertEqual(decoded, chain)
      self.assertEqual(len(decoded), len(chain))
      document = json.loads(encode_audit(chain))
      self.assertFalse(document['runtime_accepted'])
      self.assertEqual(document['run_sha256'], '1' * 64)
    with self.assertRaises(ValueError):
      encode_audit(())
    with self.assertRaises(ValueError):
      encode_audit(list(first))

  def test_changed_audit_history_is_rejected_even_with_resigned_envelope(self):
    first = append_event((), started())
    completed = append_event(first, terminal(first))
    changes = [lambda d: d.update(runtime_accepted=True), lambda d: d.update(run_sha256='9' * 64),
               lambda d: d['chain'][1]['event'].update(profile_sha256='9' * 64),
               lambda d: d['chain'][0]['event'].update(reasons='STRING'),
               lambda d: d['chain'][0].update(extra=1), lambda d: d.update(chain=[])]
    for change in changes:
      document = json.loads(encode_audit(completed))
      change(document)
      with self.subTest(change=changes.index(change)), self.assertRaises(ValueError):
        decode_audit(resign(document))


if __name__ == '__main__':
  unittest.main()
