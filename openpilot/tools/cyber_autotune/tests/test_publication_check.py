import unittest


class TestPublicationCheck(unittest.TestCase):
  def scan(self, text):
    from tools.cyberpilot.check_publication import scan_text
    return scan_text('example.txt', text)

  def test_private_route_and_local_paths_are_detected(self):
    cases = {
      'route': 'segment ' + '000000bf' + '--' + 'a60644168c' + '--29',
      'mnt': '/mnt/' + 'd/' + 'carrotlog/20260922/file',
      'home': '/home/' + 'cyberpilot/' + 'CyberPilot-step7/file',
      'windows': 'D:' + chr(92) + 'CarrotLogs' + chr(92) + 'route' + chr(92) + 'rlog.zst',
      'timestamp_route': 'a' * 16 + '|' + '2020-01-01--00-00-00',
      'timestamp_disk': 'a' * 16 + '--' + '2020-01-01--00-00-00',
      'other_home': '/home/' + 'alice/logs/rlog.zst',
      'windows_home': 'C:/' + 'Users/alice/logs/rlog.zst',
    }
    for name, text in cases.items():
      with self.subTest(name=name):
        findings = self.scan(text)
        self.assertTrue(findings)
        self.assertTrue(any(item.kind.startswith('private_') for item in findings))

  def test_secret_patterns_are_detected(self):
    cases = (
      '-----BEGIN ' + 'PRIVATE KEY-----',
      'AK' + 'IAABCDEFGHIJKLMNOP',
      'gh' + 'p_abcdefghijklmnopqrstuvwxyz1234567890',
      'sk-' + 'proj-abcdefghijklmnopqrstuvwxyz123456',
      'Bear' + 'er abcdefghijklmnopqrstuvwxyz.1234567890',
      'github_' + 'pat_' + 'a' * 40,
    )
    for text in cases:
      with self.subTest(text=text[:12]):
        self.assertTrue(self.scan(text))

  def test_safe_fixtures_and_hashes_are_not_rejected(self):
    safe = (
      'development-route--fixture--29',
      'SHA-256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      '/proc/self/fd/7',
      '/tmp/cyber-test',
      'C:/generic/output',
      'docs/cyberpilot/changes/report.md',
    )
    for text in safe:
      with self.subTest(text=text):
        self.assertEqual(self.scan(text), ())

  def test_line_numbers_and_redacted_preview_are_reported(self):
    findings = self.scan('safe\n/mnt/' + 'd/CyberPilot/private\n')
    self.assertEqual(len(findings), 1)
    self.assertEqual(findings[0].line_number, 2)
    self.assertEqual(findings[0].path, 'example.txt')
    self.assertNotIn('/mnt/' + 'd/CyberPilot/private', findings[0].preview)
    self.assertIn('[REDACTED]', findings[0].preview)

  def test_binary_like_text_is_rejected_by_file_reader_not_scanner(self):
    from tools.cyberpilot.check_publication import is_probably_text
    self.assertTrue(is_probably_text(b'plain utf-8\n'))
    self.assertFalse(is_probably_text(b'abc\x00def'))

  def test_unsupported_large_or_binary_files_block_publication(self):
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from tools.cyberpilot.check_publication import scan_file

    with TemporaryDirectory() as directory:
      root = Path(directory)
      binary = root / 'binary.bin'
      binary.write_bytes(b'\x00' + b'/mnt/' + b'd/carrotlog')
      large = root / 'large.txt'
      large.write_bytes(b'a' * 1_048_577 + b'/mnt/' + b'd/carrotlog')
      self.assertEqual(scan_file(binary, root)[0].kind, 'unscannable_binary')
      self.assertEqual(scan_file(large, root)[0].kind, 'unscannable_size')

  def test_preview_never_contains_other_secrets_or_private_suffixes(self):
    first = 'gh' + 'p_' + 'a' * 30
    second = 'sk-' + 'b' * 30
    for finding in self.scan(first + ' ' + second):
      self.assertNotIn(first, finding.preview)
      self.assertNotIn(second, finding.preview)
    for finding in self.scan('/home/' + 'cyberpilot/sensitive-owner/route'):
      self.assertNotIn('sensitive-owner', finding.preview)

  def test_missing_and_symlink_files_fail_closed(self):
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from tools.cyberpilot.check_publication import scan_file

    with TemporaryDirectory() as directory:
      root = Path(directory)
      self.assertEqual(scan_file(root / 'missing', root)[0].kind, 'unscannable_file')
      (root / 'link').symlink_to('/etc/hostname')
      self.assertEqual(scan_file(root / 'link', root)[0].kind, 'unscannable_symlink')

  def test_staged_and_unstaged_files_including_newline_names_are_discovered(self):
    from pathlib import Path
    import subprocess
    from tempfile import TemporaryDirectory
    from tools.cyberpilot.check_publication import audit_changed

    with TemporaryDirectory() as directory:
      root = Path(directory)

      def git(*args):
        return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.DEVNULL)

      git('init')
      (root / 'tracked.txt').write_text('safe')
      git('add', '.')
      git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
      base = git('rev-parse', 'HEAD').decode().strip()
      secret = 'gh' + 'p_' + 'a' * 30
      (root / 'tracked.txt').write_text(secret)
      self.assertTrue(audit_changed(root, base))
      git('add', 'tracked.txt')
      (root / 'tracked.txt').write_text('safe again')
      self.assertTrue(audit_changed(root, base), 'index must be scanned independently')
      (root / 'line\nbreak.txt').write_text(secret)
      findings = audit_changed(root, base)
      self.assertTrue(any(finding.path == 'line\nbreak.txt' for finding in findings))

  def test_secret_removed_from_tip_still_blocks_history_publication(self):
    from pathlib import Path
    import subprocess
    from tempfile import TemporaryDirectory
    from tools.cyberpilot.check_publication import audit_changed

    with TemporaryDirectory() as directory:
      root = Path(directory)

      def git(*args):
        return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.DEVNULL)

      git('init')
      (root / 'file.txt').write_text('safe')
      git('add', '.')
      commit_args = ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-am', 'fixture')
      git(*commit_args)
      base = git('rev-parse', 'HEAD').decode().strip()
      (root / 'file.txt').write_text('gh' + 'p_' + 'a' * 30)
      git(*commit_args)
      (root / 'file.txt').write_text('safe')
      git(*commit_args)
      self.assertTrue(audit_changed(root, base), 'a later cleanup does not remove a secret from Git history')

  def test_type_change_is_audited_in_worktree_index_and_history(self):
    from pathlib import Path
    import subprocess
    from tempfile import TemporaryDirectory
    from tools.cyberpilot.check_publication import audit_changed

    with TemporaryDirectory() as directory:
      root = Path(directory)

      def git(*args):
        return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.DEVNULL)

      git('init')
      (root / 'file.txt').write_text('safe')
      git('add', '.')
      commit_args = ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-am', 'fixture')
      git(*commit_args)
      base = git('rev-parse', 'HEAD').decode().strip()
      (root / 'file.txt').unlink()
      (root / 'file.txt').symlink_to('gh' + 'p_' + 'a' * 30)
      self.assertTrue(audit_changed(root, base))
      git('add', '.')
      self.assertTrue(audit_changed(root, base))
      git(*commit_args)
      self.assertTrue(audit_changed(root, base))

  def test_sensitive_filenames_and_raw_log_exports_are_not_disclosed_or_allowed(self):
    from tools.cyberpilot.check_publication import scan_bytes

    secret = 'gh' + 'p_' + 'a' * 30
    findings = scan_bytes(secret + '.txt', b'safe')
    self.assertTrue(findings)
    self.assertNotIn(secret, repr(findings))
    self.assertTrue(scan_bytes('rlog.json', b'{}'))
    self.assertTrue(scan_bytes('export.txt', b'{"latitude":' + b'12.345, "longitude":' + b'67.89}'))

  def test_cli_failure_has_no_paths_or_traceback(self):
    from pathlib import Path
    import subprocess
    import sys
    from tempfile import TemporaryDirectory

    script = Path(__file__).resolve().parents[4] / 'tools/cyberpilot/check_publication.py'
    with TemporaryDirectory() as directory:
      result = subprocess.run([sys.executable, str(script), '--repo', directory, '--json'], capture_output=True, text=True)
      self.assertNotEqual(result.returncode, 0)
      self.assertNotIn(directory, result.stdout + result.stderr)
      self.assertNotIn('Traceback', result.stderr)

  def test_cli_symlink_loop_has_no_sensitive_diagnostics(self):
    from pathlib import Path
    import subprocess
    import sys
    from tempfile import TemporaryDirectory

    script = Path(__file__).resolve().parents[4] / 'tools/cyberpilot/check_publication.py'
    with TemporaryDirectory() as directory:
      root = Path(directory)
      subprocess.run(['git', '-C', directory, 'init'], check=True, capture_output=True)
      subprocess.run(['git', '-C', directory, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '--allow-empty', '-m', 'fixture'], check=True, capture_output=True)
      secret = 'gh' + 'p_' + 'a' * 30
      (root / secret).symlink_to(secret)
      result = subprocess.run([sys.executable, str(script), '--repo', directory, '--base', 'HEAD', '--json'],
                              capture_output=True, text=True)
      self.assertNotEqual(result.returncode, 0)
      self.assertNotIn(secret, result.stdout + result.stderr)
      self.assertNotIn('Traceback', result.stderr)

  def test_git_cannot_silently_omit_unreadable_untracked_directory(self):
    from pathlib import Path
    import subprocess
    import sys
    from tempfile import TemporaryDirectory

    script = Path(__file__).resolve().parents[4] / 'tools/cyberpilot/check_publication.py'
    with TemporaryDirectory() as directory:
      root = Path(directory)
      subprocess.run(['git', '-C', directory, 'init'], check=True, capture_output=True)
      subprocess.run(['git', '-C', directory, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '--allow-empty', '-m', 'fixture'], check=True, capture_output=True)
      hidden = root / 'unreadable'
      hidden.mkdir()
      (hidden / 'secret.txt').write_text('gh' + 'p_' + 'a' * 30)
      hidden.chmod(0)
      try:
        result = subprocess.run([sys.executable, str(script), '--repo', directory, '--base', 'HEAD', '--json'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(directory, result.stdout + result.stderr)
      finally:
        hidden.chmod(0o700)

  def test_duplicate_patterns_on_one_line_report_each_kind_once(self):
    findings = self.scan('/mnt/' + 'd/carrotlog/' + '000000bf' + '--' + 'a60644168c' + '--29/rlog.zst')
    kinds = tuple(item.kind for item in findings)
    self.assertEqual(len(kinds), len(set(kinds)))
    self.assertIn('private_route', kinds)
    self.assertIn('private_mnt_path', kinds)


if __name__ == '__main__':
  unittest.main()
