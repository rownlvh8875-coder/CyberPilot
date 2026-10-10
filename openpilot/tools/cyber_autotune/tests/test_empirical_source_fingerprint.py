import unittest
from openpilot.tools.cyber_autotune import empirical_source_fingerprint as f


class TestFingerprint(unittest.TestCase):
  def test_dirty_source_rejected(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot', 'a'*40, True, True), 'SOURCE_DIRTY_BUILD_UNATTESTED')

  def test_exact_origin(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot.git', 'a'*40, False, True), 'SOURCE_COMMIT_PUBLICLY_AVAILABLE')

  def test_wrong_remote(self):
    self.assertEqual(f.origin_identity('https://evil.example/openpilot', 'a'*40, False, True), 'SOURCE_REMOTE_AMBIGUOUS')

  def test_unavailable(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot', 'a'*40, False, False), 'SOURCE_COMMIT_UNAVAILABLE')

  def test_invalid_commit(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot', 'latest', False, True), 'SOURCE_REMOTE_AMBIGUOUS')

  def test_python_comment_equality(self):
    self.assertEqual(f.normalized_source(b'x = 1 # hi\n', '.py'), f.normalized_source(b'x=1\n', '.py'))

  def test_semantic_sign_difference(self):
    self.assertNotEqual(f.normalized_source(b'x=1', '.py'), f.normalized_source(b'x=-1', '.py'))

  def test_schema_field_id_difference(self):
    self.assertNotEqual(f.normalized_source(b'v @1 :Float32;', '.capnp'), f.normalized_source(b'v @2 :Float32;', '.capnp'))

  def test_dbc_unit_preserved(self):
    self.assertNotEqual(f.normalized_source(b'SG_ Y : (0.01,-40.95) ""', '.dbc'), f.normalized_source(b'SG_ Y : (0.01,-40.95) "rad/s"', '.dbc'))

  def test_ast_and_source_hash(self):
    a = f.source_entry('a.py', b'def run():\n  return 1\n')
    self.assertIn('run:1', a['symbols'])

  def test_exact_class(self):
    a = {'origin_attested': True, 'dependency_closure_complete': True, 'complete': True, 'files': {'x': f.source_entry('x.py', b'x=1')}}
    self.assertEqual(f.compare(a, a), 'EXACT_RELEVANT_SOURCE_EQUIVALENT')

  def test_comments_require_review(self):
    a = {'origin_attested': True, 'dependency_closure_complete': True, 'complete': True, 'files': {'x': f.source_entry('x.py', b'x=1')}}
    b = {'origin_attested': True, 'dependency_closure_complete': True, 'complete': True, 'files': {'x': f.source_entry('x.py', b'x=1 # hi')}}
    self.assertEqual(f.compare(a, b), 'NOT_EQUIVALENT')
    self.assertEqual(f.compare(a, b, {'paths': ['x'], 'scope': 'COMMENTS_FORMATTING_ONLY_REVIEWED'}), 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT')

  def test_incomplete_not_equivalent(self):
    a = {'complete': False, 'files': {}}
    self.assertEqual(f.compare(a, a), 'SOURCE_AUDIT_PARTIAL')

  def test_different_role_set(self):
    a = {'origin_attested': True, 'dependency_closure_complete': True, 'complete': True, 'files': {}}
    b = {**a, 'files': {'a': {}}}
    self.assertEqual(f.compare(a, b), 'NOT_EQUIVALENT')

  def test_cpp_preprocessor_scale_difference_preserved(self):
    self.assertNotEqual(f.normalized_source(b'#define SCALE 1\nx=SCALE;', '.h'),
                        f.normalized_source(b'#define SCALE 409\nx=SCALE;', '.h'))

  def test_cpp_token_boundaries_preserved(self):
    self.assertNotEqual(f.normalized_source(b'x + ++y;', '.cc'), f.normalized_source(b'x++ + y;', '.cc'))

  def test_unknown_dirty_rejected(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot', 'a'*40, None, True), 'SOURCE_DIRTY_BUILD_UNATTESTED')

  def test_public_attestation_must_be_bool(self):
    self.assertEqual(f.origin_identity('https://github.com/ajouatom/openpilot', 'a'*40, False, 'false'), 'SOURCE_COMMIT_UNAVAILABLE')

  def test_python_bom_hashes_original_bytes(self):
    entry = f.source_entry('a.py', b'\xef\xbb\xbfvalue=1\n')
    self.assertEqual(entry['normalized_source_sha256'], f.source_entry('a.py', b'value=1\n')['normalized_source_sha256'])
    self.assertNotEqual(entry['file_sha256'], f.source_entry('a.py', b'value=1\n')['file_sha256'])

  def test_can_builder_difference_not_command_equivalent(self):
    roles = ('controller', 'controller_limits', 'controller_helpers', 'card', 'schema_car',
             'can_builder', 'canfd_builder', 'dbc', 'interface', 'interface_base')
    a = {'origin_attested': True, 'dependency_closure_complete': True, 'complete': True,
         'files': {k: f.source_entry(k+'.py', b'x=1') for k in roles}}
    b = {**a, 'files': {**a['files'], 'can_builder': f.source_entry('can_builder.py', b'x=-1')}}
    self.assertEqual(f.compare(a, b), 'NOT_EQUIVALENT')
