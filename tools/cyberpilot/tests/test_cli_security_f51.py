"""F51 synthetic boundary regressions; no private driving data or runtime."""
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

CANARY = 'F51_SYNTHETIC_PRIVATE_CANARY'
ROOT = Path(__file__).resolve().parents[3]


class BoundaryTests(unittest.TestCase):
  def test_unknown_option_and_private_prog_are_redacted(self):
    from tools.cyberpilot import rlog_observer_regression_v1 as api
    out, err = io.StringIO(), io.StringIO()
    with patch('sys.argv', [CANARY, '--unknown', CANARY]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      try:
        code = api.main()
      except SystemExit as error:
        code = error.code
    self.assertNotEqual(code, 0)
    self.assertNotIn(CANARY, out.getvalue() + err.getvalue())
    self.assertNotIn('Traceback', out.getvalue() + err.getvalue())

  def test_direct_worker_cannot_populate_existing_directory(self):
    for name in ('rlog_observer_regression_v1', 'recorded_input_binding_v1'):
      api = importlib.import_module('tools.cyberpilot.' + name)
      with self.subTest(module=name), tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / 'existing'
        output.mkdir(mode=0o700)
        argv = ['f51', '--worker', '--raw', CANARY, '--source-root', CANARY,
                '--source-manifest', CANARY, '--output', str(output)]
        if name == 'recorded_input_binding_v1':
          argv += ['--f46-tape', CANARY]
        def decoder(*args, api=api):
          api_base = api.base() if hasattr(api, 'base') else api
          api_base.write_private(args[-1] / 'bad.json', b'UNAUTHORIZED')
        out, err = io.StringIO(), io.StringIO()
        with patch('sys.argv', argv), patch.object(api, 'decode', side_effect=decoder), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
          code = api.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(list(output.iterdir()), [])
        self.assertNotIn(CANARY, out.getvalue() + err.getvalue())


class DirectoryTests(unittest.TestCase):
  def setUp(self):
    self.sec = importlib.import_module('tools.cyberpilot.cli_security_f51')
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.output = self.sec.SecureDirectory.create(self.root / 'output')
    self.addCleanup(self.output.close)

  def test_private_normal_write_read_and_modes(self):
    self.output.write('summary.json', b'{"unchanged":true}\n')
    self.assertEqual(self.output.read('summary.json'), b'{"unchanged":true}\n')
    self.assertEqual((self.root / 'output').stat().st_mode & 0o777, 0o700)
    self.assertEqual((self.root / 'output/summary.json').stat().st_mode & 0o777, 0o600)

  def test_existing_owned_directory_has_verified_metadata(self):
    existing = self.sec.SecureDirectory.existing(self.root / 'output')
    try:
      existing.verify()
    finally:
      existing.close()

  def test_new_invocation_never_reuses_existing_owned_folder(self):
    with self.assertRaises(ValueError):
      self.sec.SecureDirectory.create(self.root / 'output')

  def test_wrong_owner_is_rejected_without_chown(self):
    with patch.object(self.sec.os, 'geteuid', return_value=os.geteuid() + 10000), self.assertRaises(ValueError):
      self.sec.SecureDirectory.existing(self.root / 'output')

  def test_group_writable_leaf_is_rejected(self):
    (self.root / 'output').chmod(0o720)
    with self.assertRaises(ValueError):
      self.output.write('x', b'bad')
    self.assertFalse((self.root / 'output/x').exists())

  def test_world_writable_leaf_is_rejected(self):
    (self.root / 'output').chmod(0o702)
    with self.assertRaises(ValueError):
      self.output.write('x', b'bad')
    self.assertFalse((self.root / 'output/x').exists())

  def test_nonprivate_read_permissions_are_rejected(self):
    (self.root / 'output').chmod(0o755)
    with self.assertRaises(ValueError):
      self.sec.SecureDirectory.existing(self.root / 'output')

  def test_writable_ancestor_is_rejected(self):
    self.root.chmod(0o770)
    with self.assertRaises(ValueError):
      self.output.write('x', b'bad')

  def test_symlink_directory_is_rejected(self):
    (self.root / 'link').symlink_to(self.root / 'output', target_is_directory=True)
    with self.assertRaises((OSError, ValueError)):
      self.sec.SecureDirectory.existing(self.root / 'link')

  def test_symlink_ancestor_is_rejected(self):
    (self.root / 'link').symlink_to(self.root / 'output', target_is_directory=True)
    with self.assertRaises((OSError, ValueError)):
      self.sec.SecureDirectory.create(self.root / 'link/child')
    self.assertFalse((self.root / 'output/child').exists())

  def test_symlink_output_file_is_not_followed(self):
    target = self.root / 'victim'
    target.write_bytes(b'KEEP')
    (self.root / 'output/x').symlink_to(target)
    with self.assertRaises((OSError, ValueError)):
      self.output.write('x', b'bad')
    self.assertEqual(target.read_bytes(), b'KEEP')

  def test_existing_file_is_never_overwritten(self):
    self.output.write('x', b'KEEP')
    with self.assertRaises(ValueError):
      self.output.write('x', b'bad')
    self.assertEqual(self.output.read('x'), b'KEEP')

  def test_relative_directory_escape_is_rejected(self):
    with self.assertRaises(ValueError):
      self.sec.SecureDirectory.create(self.root / 'output/../escape')

  def test_relative_filename_escape_is_rejected(self):
    with self.assertRaises(ValueError):
      self.output.write('../escape', b'bad')

  def test_regular_file_cannot_be_an_output_directory(self):
    (self.root / 'file').write_bytes(b'KEEP')
    with self.assertRaises((OSError, ValueError)):
      self.sec.SecureDirectory.existing(self.root / 'file')

  def test_unqualified_filesystem_fails_closed(self):
    with patch.object(self.sec, 'filesystem_type', return_value=0xFACE), self.assertRaises(ValueError):
      self.output.write('x', b'bad')
    self.assertFalse((self.root / 'output/x').exists())

  def test_metadata_unavailable_fails_closed(self):
    with patch.object(self.sec.os, 'fstat', side_effect=OSError(CANARY)), self.assertRaises(OSError):
      self.output.write('x', b'bad')
    self.assertFalse((self.root / 'output/x').exists())

  def test_non_linux_filesystem_contract_fails_closed(self):
    with patch.object(self.sec.sys, 'platform', 'win32'), self.assertRaises(ValueError):
      self.sec.SecureDirectory.existing(self.root / 'output')

  def test_path_replaced_before_write_is_rejected(self):
    (self.root / 'output').rename(self.root / 'old')
    (self.root / 'output').mkdir(mode=0o700)
    with self.assertRaises(ValueError):
      self.output.write('x', b'bad')
    self.assertEqual(list((self.root / 'output').iterdir()), [])

  def test_path_replaced_between_check_and_open_cannot_redirect(self):
    original_open = os.open
    changed = False
    def replace(path, flags, mode=0o777, *, dir_fd=None):
      nonlocal changed
      if path == 'x' and flags & os.O_CREAT and not changed:
        changed = True
        (self.root / 'output').rename(self.root / 'old')
        (self.root / 'attacker').mkdir(mode=0o700)
        (self.root / 'output').symlink_to(self.root / 'attacker', target_is_directory=True)
      return original_open(path, flags, mode, dir_fd=dir_fd)
    with patch.object(self.sec.os, 'open', side_effect=replace) as mocked, \
         patch.object(self.sec.os, 'supports_dir_fd', os.supports_dir_fd | {mocked}), self.assertRaises((OSError, ValueError)):
      self.output.write('x', b'ANCHORED')
    self.assertTrue(changed)
    self.assertEqual(list((self.root / 'attacker').iterdir()), [])
    self.assertEqual((self.root / 'old/x').read_bytes(), b'ANCHORED')

  def test_intermediate_component_swap_cannot_redirect(self):
    (self.root / 'parent').mkdir(mode=0o700)
    (self.root / 'elsewhere').mkdir(mode=0o700)
    original_open = os.open
    changed = False
    def replace(path, flags, mode=0o777, *, dir_fd=None):
      nonlocal changed
      if path == 'parent':
        changed = True
        (self.root / 'parent').rename(self.root / 'parent-old')
        (self.root / 'parent').symlink_to(self.root / 'elsewhere', target_is_directory=True)
      return original_open(path, flags, mode, dir_fd=dir_fd)
    with patch.object(self.sec.os, 'open', side_effect=replace) as mocked, \
         patch.object(self.sec.os, 'supports_dir_fd', os.supports_dir_fd | {mocked}), self.assertRaises((OSError, ValueError)):
      self.sec.SecureDirectory.create(self.root / 'parent/leaf')
    self.assertTrue(changed)
    self.assertEqual(list((self.root / 'elsewhere').iterdir()), [])

  def test_worker_requires_inherited_capability(self):
    with self.assertRaises(ValueError):
      self.sec.from_worker(self.root / 'output', None, None)

  def test_worker_normal_subprocess_writes_only_anchored_directory(self):
    script = ("import sys;from tools.cyberpilot.cli_security_f51 import from_worker;" +
              "d=from_worker(sys.argv[1],int(sys.argv[3]),int(sys.argv[5]));" +
              "d.write('worker.json',b'{\"ok\":true}\\n');d.close()")
    result = self.sec.run_worker([sys.executable, '-B', '-c', script, str(self.output)], self.output, 10)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(self.output.read('worker.json'), b'{"ok":true}\n')

  def test_nonempty_worker_directory_is_rejected(self):
    self.output.write('keep', b'KEEP')
    script = ("import sys;from tools.cyberpilot.cli_security_f51 import from_worker;" +
              "d=from_worker(sys.argv[1],int(sys.argv[3]),int(sys.argv[5]))")
    result = self.sec.run_worker([sys.executable, '-B', '-c', script, str(self.output)], self.output, 10)
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(self.output.read('keep'), b'KEEP')


class PrivacyTests(unittest.TestCase):
  def setUp(self):
    self.api = importlib.import_module('tools.cyberpilot.rlog_observer_regression_v1')
    self.sec = self.api.security()

  def invoke_error(self, exception=None, worker_stdout=None, malformed_reader=None):
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'new'
      args = [CANARY, '--raw', CANARY, '--source-root', CANARY, '--source-manifest', CANARY,
              '--output', str(output)]
      def worker(command, directory, timeout):
        if exception is not None:
          raise exception
        if malformed_reader is not None:
          directory.write('reader.json', malformed_reader)
          directory.write('recorded_commands.jsonl', b'')
        return subprocess.CompletedProcess(command, 0 if malformed_reader is not None else 2,
                                           worker_stdout or b'', CANARY.encode())
      out, err = io.StringIO(), io.StringIO()
      with patch('sys.argv', args), patch.object(self.sec, 'run_worker', side_effect=worker), \
           contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = self.api.main()
      error_json = (output / 'failure.json').read_text()
      captured = out.getvalue() + err.getvalue() + error_json
      self.assertEqual(code, 2)
      self.assertNotIn(CANARY, captured)
      self.assertNotIn('Traceback', captured)
      self.assertIn('reason', json.loads(error_json))
      return json.loads(error_json)['reason']

  def test_exception_message_canary_not_forwarded(self):
    self.assertEqual(self.invoke_error(RuntimeError(CANARY)), 'UNEXPECTED_INTERNAL_ERROR')

  def test_uppercase_canary_is_not_a_public_error_code(self):
    self.assertEqual(self.invoke_error(self.api.BindingError(CANARY)), 'UNEXPECTED_INTERNAL_ERROR')

  def test_nested_exception_is_not_forwarded(self):
    nested = ValueError(CANARY)
    nested.__cause__ = RuntimeError(CANARY)
    self.assertEqual(self.invoke_error(nested), 'UNEXPECTED_INTERNAL_ERROR')

  def test_permission_path_canary_is_not_forwarded(self):
    self.assertEqual(self.invoke_error(PermissionError(CANARY)), 'INPUT_FILE_ACCESS_DENIED')

  def test_malformed_json_canary_is_not_forwarded(self):
    self.assertEqual(self.invoke_error(malformed_reader=('{"' + CANARY).encode()), 'INVALID_INPUT_SCHEMA')

  def test_schema_key_canary_is_not_forwarded(self):
    self.assertEqual(self.invoke_error(malformed_reader=json.dumps({CANARY: 1}).encode()), 'INVALID_INPUT_SCHEMA')

  def test_child_stdout_stderr_and_error_json_do_not_leak(self):
    self.assertEqual(self.invoke_error(worker_stdout=('F46_SOURCE_BINDING_BLOCKED:' + CANARY).encode()), 'READER_BLOCKED')

  def test_known_fixed_binding_error_is_preserved(self):
    self.assertEqual(self.invoke_error(worker_stdout=b'F46_SOURCE_BINDING_BLOCKED:FILE_UNAVAILABLE'), 'FILE_UNAVAILABLE')

  def test_worker_decoder_prints_native_writes_and_nested_traceback_are_private(self):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
      try:
        with self.sec.private_decoder():
          print(CANARY)
          print(CANARY, file=sys.stderr)
          os.write(1, CANARY.encode())
          os.write(2, CANARY.encode())
          import traceback
          try:
            raise RuntimeError(CANARY)
          except RuntimeError:
            traceback.print_exc()
            raise
      except RuntimeError as error:
        print(self.sec.error_code(error))
    self.assertEqual(stderr.getvalue(), '')
    self.assertEqual(stdout.getvalue(), 'UNEXPECTED_INTERNAL_ERROR\n')

  def test_help_uses_fixed_program_without_argv(self):
    out, err = io.StringIO(), io.StringIO()
    with patch('sys.argv', [CANARY, '--help']), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      with self.assertRaises(SystemExit) as status:
        self.api.main()
    self.assertEqual(status.exception.code, 0)
    self.assertNotIn(CANARY, out.getvalue() + err.getvalue())
    self.assertIn('usage: f46', out.getvalue())


class CompatibilityTests(unittest.TestCase):
  def test_normal_f46_cli_result_format_and_command_bytes_are_preserved(self):
    from tools.cyberpilot import rlog_observer_regression_v1 as api
    from tools.cyberpilot.tests.test_rlog_observer_regression_v1 import TestRecordedCommandObserver
    fixture = TestRecordedCommandObserver()
    fixture.setUp()
    record = fixture.command()
    tape = api.tape_bytes((record,))
    secure = api.security()
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'new'
      args = ['f46', '--raw', CANARY, '--source-root', CANARY, '--source-manifest', CANARY, '--output', str(output)]
      def worker(command, directory, timeout):
        directory.write('recorded_commands.jsonl', tape)
        directory.write('reader.json', api.canonical({'binding': record.binding, 'total_messages': 1,
                                                     'all_service_counts': {'carControl': 1}}))
        return subprocess.CompletedProcess(command, 0, b'', b'')
      out = io.StringIO()
      with patch('sys.argv', args), patch.object(secure, 'run_worker', side_effect=worker), \
           patch.object(api, 'EXPECTED_COUNTS', {'carControl': 1}), contextlib.redirect_stdout(out):
        code = api.main()
      self.assertEqual(code, 0)
      self.assertEqual(out.getvalue(), 'F46_RECORDED_COMMAND_REPLAY_PASS\n')
      self.assertEqual((output / 'recorded_commands.jsonl').read_bytes(), tape)
      summary = json.loads((output / 'summary.json').read_bytes())
      self.assertFalse(summary['runtime_authorized'])
      self.assertEqual(summary['controller_state'], 'F46_INSUFFICIENT_RECORDED_STATE')
      self.assertFalse((output / 'failure.json').exists())

  def test_normal_f47_cli_keeps_unknown_schema_status(self):
    from dataclasses import asdict
    from tools.cyberpilot import recorded_input_binding_v1 as api
    f46 = api.base()
    secure = f46.security()
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'new'
      args = ['f47', '--raw', CANARY, '--source-root', CANARY, '--source-manifest', CANARY,
              '--f46-tape', CANARY, '--output', str(output)]
      def worker(command, directory, timeout):
        stamps = (api.Stamp(1, 'carControl', 100, True, 'a' * 64),)
        directory.write('headers.jsonl', b''.join(api.canonical(asdict(x)) for x in stamps))
        directory.write('recorded_commands.jsonl', b'SYNTHETIC_ONLY')
        directory.write('reader.json', api.canonical({'binding': 'a' * 64, 'nominal_frequencies_hz': {},
                                                     'command_sha256': 'b' * 64, 'original_4450_records_verified': False}))
        return subprocess.CompletedProcess(command, 0, b'', b'')
      out = io.StringIO()
      with patch('sys.argv', args), patch.object(secure, 'run_worker', side_effect=worker), contextlib.redirect_stdout(out):
        code = api.main()
      self.assertEqual(code, 0)
      self.assertEqual(out.getvalue(), 'F47_IMPLEMENTATION_PASS\n')
      rows = [json.loads(x) for x in (output / 'binding_rows.jsonl').read_bytes().splitlines()]
      self.assertEqual(len(rows), 1)
      self.assertIn('SOURCE_SCHEMA_UNQUALIFIED', json.dumps(rows))
      self.assertNotIn(CANARY, (output / 'summary.json').read_text())

  def test_actual_subprocess_unknown_option_and_path_canaries(self):
    from tools.cyberpilot import rlog_observer_regression_v1 as api
    result = subprocess.run([sys.executable, '-B', api.__file__, '--raw', CANARY, '--source-root', CANARY,
                             '--source-manifest', CANARY, '--output', CANARY, '--unknown', CANARY],
                            capture_output=True, check=False)
    self.assertEqual(result.returncode, 2)
    self.assertNotIn(CANARY.encode(), result.stdout + result.stderr)
    self.assertNotIn(b'Traceback', result.stdout + result.stderr)
    self.assertIn(b'INVALID_CLI_ARGUMENT', result.stdout)

  def test_f47_internal_failure_does_not_forward_canary(self):
    from tools.cyberpilot import recorded_input_binding_v1 as api
    secure = api.base().security()
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'new'
      args = ['f47', '--raw', CANARY, '--source-root', CANARY, '--source-manifest', CANARY,
              '--f46-tape', CANARY, '--output', str(output)]
      out, err = io.StringIO(), io.StringIO()
      with patch('sys.argv', args), patch.object(secure, 'run_worker', side_effect=RuntimeError(CANARY)), \
           contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = api.main()
      self.assertEqual(code, 2)
      self.assertNotIn(CANARY, out.getvalue() + err.getvalue() + (output / 'failure.json').read_text())



class FinalBoundaryTests(unittest.TestCase):
  def test_cleanup_exception_cannot_escape_cli(self):
    from tools.cyberpilot import rlog_observer_regression_v1 as api
    secure = api.security()
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'new'
      args = ['f46', '--raw', CANARY, '--source-root', CANARY, '--source-manifest', CANARY, '--output', str(output)]
      out, err = io.StringIO(), io.StringIO()
      original_close = secure.SecureDirectory.close
      def close_with_error(directory):
        original_close(directory)
        raise RuntimeError(CANARY)
      with patch('sys.argv', args), patch.object(secure.SecureDirectory, 'close', close_with_error), \
           contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = api.main()
      self.assertNotEqual(code, 0)
      self.assertNotIn(CANARY, out.getvalue() + err.getvalue())

  def test_native_stdio_buffer_cannot_flush_after_redaction(self):
    script = '\n'.join(("import ctypes", "from tools.cyberpilot.cli_security_f51 import private_decoder",
                           "lib=ctypes.CDLL(None)", "with private_decoder():",
                           " lib.printf(b'F51_SYNTHETIC_PRIVATE_CANARY')", "lib.fflush(None)"))
    result = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True, check=False)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertNotIn(CANARY.encode(), result.stdout + result.stderr)



if __name__ == '__main__':
  unittest.main()
