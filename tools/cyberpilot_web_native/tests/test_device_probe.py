import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.cyberpilot_web_native.device_probe import collect
from tools.cyberpilot_web_native.device_probe_bundle import build_bundle, export_release

ROOT = Path(__file__).resolve().parents[3]


class DeviceProbeTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.model = self.root / 'sys/firmware/devicetree/base/model'
    self.model.parent.mkdir(parents=True)

  def test_missing_facts_are_unavailable_and_never_qualify(self):
    result = collect(self.root)
    self.assertEqual(result['model']['status'], 'MISSING')
    self.assertIsNone(result['model']['value'])
    self.assertIsNone(result['hardware_code_hint'])
    self.assertEqual(result['source']['status'], 'NOT_PROVIDED')
    self.assertFalse(result['device_installation_qualified'])
    self.assertFalse(result['actual_activation_allowed'])

  def test_fixture_mici_is_labelled_without_becoming_device_evidence(self):
    self.model.write_bytes(b'comma mici\x00')
    (self.root / 'VERSION').write_text('19.9\n')
    (self.root / 'AGNOS').touch()
    with patch('platform.machine', return_value='aarch64'):
      result = collect(self.root)
    self.assertEqual(result['observation_scope'], 'FILESYSTEM_FIXTURE')
    self.assertEqual(result['hardware_code_hint'], 'mici')
    self.assertEqual(result['product_hint'], 'comma four')
    self.assertEqual(result['model']['sha256'], hashlib.sha256(b'comma mici\x00').hexdigest())
    self.assertFalse(result['device_installation_qualified'])
    self.assertFalse(result['actual_activation_allowed'])

  def test_other_model_not_relabelled_as_comma4(self):
    self.model.write_bytes(b'comma tizi\x00')
    result = collect(self.root)
    self.assertEqual(result['hardware_code_hint'], 'tizi')
    self.assertIsNone(result['product_hint'])

  def test_empty_model_has_no_hint(self):
    self.model.write_bytes(b'\x00')
    result = collect(self.root)
    self.assertEqual(result['model']['status'], 'EMPTY')
    self.assertIsNone(result['hardware_code_hint'])

  def test_invalid_utf8_and_oversized_files_are_not_returned(self):
    for data, status in ((b'\xff\xfe', 'UNREADABLE'), (b'x' * 4097, 'TOO_LARGE')):
      self.model.write_bytes(data)
      result = collect(self.root)
      self.assertEqual(result['model']['status'], status)
      self.assertIsNone(result['model']['value'])

  def test_final_symlink_cannot_capture_unrelated_bytes(self):
    other = self.root / 'unrelated-private-file'
    other.write_text('DO_NOT_CAPTURE')
    self.model.symlink_to(other)
    result = collect(self.root)
    self.assertEqual(result['model']['status'], 'UNREADABLE')
    self.assertNotIn('DO_NOT_CAPTURE', json.dumps(result))

  def test_fifo_is_rejected_without_waiting(self):
    os.mkfifo(self.model)
    self.assertEqual(collect(self.root)['model']['status'], 'UNREADABLE')

  def test_observation_does_not_change_files(self):
    self.model.write_bytes(b'comma mici\x00')
    (self.root / 'VERSION').write_bytes(b'19.9\n')
    before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    collect(self.root)
    after = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    self.assertEqual(after, before)

  def test_inherited_git_trace_destinations_do_not_modify_files(self):
    for key in ('GIT_TRACE', 'GIT_TRACE2', 'GIT_TRACE2_PERF', 'GIT_TRACE2_EVENT'):
      with self.subTest(trace=key):
        trace = self.root / (key + '.log')
        trace.write_bytes(b'preserve trace sentinel\n')
        with patch.dict(os.environ, {key: str(trace)}):
          result = collect(self.root, source_root=ROOT)
        self.assertEqual(result['source']['status'], 'OBSERVED_METADATA_ONLY')
        self.assertEqual(trace.read_bytes(), b'preserve trace sentinel\n')

  def test_git_global_trace2_config_cannot_enable_file_writes(self):
    targets = [self.root / (name + '.log') for name in ('normal', 'perf', 'event')]
    config = self.root / 'trace-global.gitconfig'
    config.write_text('[trace2]\n' + ''.join('  ' + name + 'Target = ' + str(path) + '\n' for name, path in zip(('normal', 'perf', 'event'), targets, strict=True)))
    for path in targets:
      path.write_bytes(b'preserve configured trace\n')
    with patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(config)}):
      result = collect(self.root, source_root=ROOT)
    self.assertEqual(result['source']['status'], 'OBSERVED_METADATA_ONLY')
    for path in targets:
      self.assertEqual(path.read_bytes(), b'preserve configured trace\n')

  def test_cyclic_source_path_still_produces_observation_json(self):
    loop = self.root / 'source-loop'
    loop.symlink_to(loop.name)
    result = subprocess.run([sys.executable, '-S', '-B', str(ROOT/'tools/cyberpilot_web_native/device_probe.py'), '--source-root', str(loop)],
                            cwd=self.root, env={**os.environ, 'PYTHONPATH': ''}, capture_output=True, text=True, timeout=8)
    self.assertEqual(result.returncode, 0, result.stderr)
    data = json.loads(result.stdout)
    self.assertEqual(data['source']['status'], 'UNAVAILABLE')
    self.assertFalse(data['device_installation_qualified'])

  def test_public_file_descriptor_read_budget_is_bounded(self):
    self.model.write_bytes(b'x' * 20000)
    positions = []
    original = os.fdopen
    class ObserveClose:
      def __init__(self, stream):
        self.stream = stream
      def __enter__(self):
        return self.stream
      def __exit__(self, *args):
        positions.append(os.lseek(self.stream.fileno(), 0, os.SEEK_CUR))
        self.stream.close()
    def observe(*args, **kwargs):
      return ObserveClose(original(*args, **kwargs))
    with patch('os.fdopen', observe):
      result = collect(self.root)
    self.assertEqual(result['model']['status'], 'TOO_LARGE')
    self.assertTrue(positions)
    self.assertLessEqual(max(positions), 4097)

  def test_unresolvable_optional_source_is_unavailable(self):
    result = collect(self.root, source_root=self.root / ('x' * 5000))
    self.assertEqual(result['source']['status'], 'UNAVAILABLE')
    self.assertIsNone(result['source']['commit'])

  def test_parent_repository_is_not_attributed_to_subdirectory(self):
    result = collect(self.root, source_root=ROOT / 'openpilot')
    self.assertEqual(result['source']['status'], 'NOT_REPOSITORY_ROOT')
    self.assertIsNone(result['source']['commit'])

  def test_requested_git_root_ignores_inherited_git_selectors(self):
    expected = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    with patch.dict(os.environ, {'GIT_DIR':str(self.root/'wrong.git'), 'GIT_WORK_TREE':str(self.root)}):
      result = collect(self.root, source_root=ROOT)
    self.assertEqual(result['source']['status'], 'OBSERVED_METADATA_ONLY')
    self.assertEqual(result['source']['commit'], expected)
    self.assertFalse(result['source']['working_tree_content_verified'])

  def test_native_modules_not_needed_for_observation(self):
    before = set(sys.modules)
    collect(self.root)
    self.assertFalse(any(name.startswith(('openpilot.', 'msgq', 'capnp')) for name in set(sys.modules)-before))

  def test_bundle_is_identical_and_runs_outside_repo_without_site_packages(self):
    a, b = self.root/'a.zip', self.root/'b.zip'
    build_bundle(a)
    build_bundle(b)
    self.assertEqual(a.read_bytes(), b.read_bytes())
    out = self.root/'extracted'
    with zipfile.ZipFile(a) as archive:
      self.assertIsNone(archive.testzip())
      manifest = json.loads(archive.read('MANIFEST.json'))
      self.assertEqual(set(archive.namelist()), set(manifest['files']) | {'MANIFEST.json'})
      for name, sha in manifest['files'].items():
        self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), sha)
      archive.extractall(out)
    result = subprocess.run([sys.executable,'-S','-B','device_probe.py'],cwd=out,env={**os.environ,'PYTHONPATH':''},capture_output=True,text=True,timeout=8)
    self.assertEqual(result.returncode, 0, result.stderr)
    data = json.loads(result.stdout)
    self.assertEqual(data['observation_scope'], 'SYSTEM_ROOT')
    self.assertEqual(data['source']['status'], 'NOT_PROVIDED')
    self.assertFalse(data['device_installation_qualified'])
    self.assertEqual(data['probe_sha256'], manifest['files']['device_probe.py'])

  def test_export_records_public_host_facts_and_complete_checksums(self):
    release = self.root / 'release'
    export_release(release)
    manifest = json.loads((release / 'MANIFEST.json').read_text())
    self.assertEqual({p.name for p in release.iterdir()}, set(manifest) | {'MANIFEST.json'})
    for name, sha in manifest.items():
      self.assertEqual(hashlib.sha256((release/name).read_bytes()).hexdigest(), sha)
    observation = json.loads((release/'HOST_OBSERVATION.json').read_text())
    self.assertEqual(observation['observation_scope'], 'SYSTEM_ROOT')
    self.assertFalse(observation['device_installation_qualified'])
    for line in (release/'SHA256SUMS.txt').read_text().splitlines():
      sha, name = line.split('  ', 1)
      self.assertEqual(Path(name).name, name)
      self.assertEqual(hashlib.sha256((release/name).read_bytes()).hexdigest(), sha)
