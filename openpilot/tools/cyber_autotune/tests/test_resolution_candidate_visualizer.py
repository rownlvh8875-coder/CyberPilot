import copy
import json
import threading
import unittest
import urllib.error
import urllib.request

from openpilot.tools.cyber_autotune import resolution_candidate_visualizer as v
from openpilot.tools.cyber_autotune import resolution_candidate_evidence as e
from openpilot.tools.cyber_autotune import resolution_candidate_audit as a


class TestResolutionCandidatePublication(unittest.TestCase):
  def test_exact_public_receipts(self):
    for suffix in ('audit', 'summary', 'readiness'):
      data = json.loads((e.PUBLIC / f'measurement-resolution-candidate-{suffix}-v1.json').read_bytes())
      self.assertEqual(e.validate_public(data), data)

  def test_resealed_nested_fields_rejected(self):
    base = v.load()
    for field, val in [('human_polyline', [[1, 2]]), ('private_path', '/private/test')]:
      bad = copy.deepcopy(base)
      bad['rows'][0][field] = val
      with self.assertRaises(ValueError):
        e.validate_public(a.seal(bad))

  def test_resealed_numeric_tamper_rejected(self):
    bad = copy.deepcopy(v.load())
    bad['rows'][0]['absolute_effect_m'] = 99
    with self.assertRaises(ValueError):
      e.validate_public(a.seal(bad))

  def test_resealed_source_tamper_rejected(self):
    bad = copy.deepcopy(v.load())
    bad['source_identity']['audit_source_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      e.validate_public(a.seal(bad))

  def test_policy_immutable(self):
    data = json.loads((e.PUBLIC / 'measurement-resolution-candidate-execution-policy-v1.json').read_bytes())
    e.validate_plan(data)
    data['basis']['distance'] = 'TIME'
    with self.assertRaises(ValueError):
      e.validate_plan(a.seal(data))

  def test_firewall_and_alias(self):
    data = v.load()
    self.assertEqual(data['ledger']['CURRENT']['alias_of'], 'BASELINE')
    self.assertEqual(data['ledger']['V2']['status'], 'REJECTED')
    self.assertEqual(len(data['historical_v2_violation_context']['violations']), 37)
    self.assertTrue(all(data[k] is False for k in a.FIREWALL))
    self.assertIsNone(data['total_physical_bound_m'])

  def test_exact_70_cases_and_198_nominal_rows(self):
    data = v.load()
    self.assertEqual(data['recovered_case_count'], 70)
    self.assertEqual(len(data['rows']), 198)
    self.assertEqual(sum(data['nominal_summary']['classification_counts'].values()), 198)

  def test_all_phases_historical_context_separate(self):
    data = v.load()
    self.assertEqual(len(data['phase_context']), 11)
    self.assertTrue(all(x['historical_tracking_smoothness_groups'] for x in data['phase_context']))
    self.assertTrue(all(y['classification'] is None for x in data['phase_context'] for y in x['effects']))

  def test_family_config_not_selected_v2(self):
    data = v.load()
    dev = [r for r in data['family_context'] if r['role'] == 'DEVELOPMENT']
    self.assertEqual(len(dev), 9)
    self.assertTrue(all(r['fourth_arm_semantics'] == 'ARCHIVED_FAMILY_MEMBER_DIAGNOSTIC_ONLY' for r in dev))

  def test_loopback_only(self):
    with self.assertRaises(ValueError):
      v.make_server(host='0.0.0.0')

  def test_assets_no_external_dependencies(self):
    for data in v.ASSET_BYTES.values():
      self.assertNotIn(b'https://', data)
      # The SVG namespace is an identifier, not a network resource.
      self.assertNotIn(b'http://', data.replace(b'http://www.w3.org/2000/svg', b''))
    self.assertIn(b'NOT A PERFORMANCE ACCEPTANCE TEST', v.ASSET_BYTES['index.html'])
    self.assertIn(b'CURRENT is the exact BASELINE alias', v.ASSET_BYTES['index.html'])

  def test_http_and_shutdown(self):
    server = v.make_server()
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
      for path in ('/candidate-resolution', '/candidate-resolution.js', '/candidate-resolution.css', '/meter', '/api/candidate-resolution'):
        with urllib.request.urlopen(base + path) as result:
          self.assertEqual(result.status, 200)
          result.read()
      request = urllib.request.Request(base + '/api/candidate-resolution', headers={'Origin': 'https://external.invalid'})
      with self.assertRaises(urllib.error.HTTPError) as result:
        urllib.request.urlopen(request)
      self.assertEqual(result.exception.code, 403)
    finally:
      server.shutdown()
      worker.join(5)
      server.server_close()
    self.assertFalse(worker.is_alive())
