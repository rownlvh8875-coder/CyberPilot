"""Independent analytic fixtures only: no raw F8 evidence is published."""

from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from tools.cyberpilot.f8_evidence_reader_v1 import Archive, F8Error, Limits, Output, json_value


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


class ReaderTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.archive = self.root / 'fixture.zip'

  def tearDown(self):
    self.temp.cleanup()

  def make(self, entries=None, extra=None):
    entries = entries or {'data.json': b'{"public_synthetic_unit_control":true}'}
    manifest = {'files': [{'path': k, 'bytes': len(v), 'sha256': sha(v)} for k, v in entries.items()]}
    raw = json.dumps(manifest).encode()
    with zipfile.ZipFile(self.archive, 'w') as z:
      for name, value in entries.items():
        z.writestr(name, value)
      z.writestr('SHA256SUMS.json', raw)
      if extra:
        extra(z)
    return sha(self.archive.read_bytes()), sha(raw), len(entries)

  def reader(self, pins, limits=None):
    return Archive(self.archive, self.root, *pins, limits=limits)

  def test_valid_explicit_archive(self):
    pins = self.make()
    with self.reader(pins) as a:
      self.assertEqual(a.json('data.json'), {'public_synthetic_unit_control': True})
      a.finish()

  def test_wrong_archive_hash(self):
    pins = self.make()
    with self.assertRaises(F8Error):
      self.reader(('0' * 64, *pins[1:]))

  def test_wrong_manifest_hash(self):
    pins = self.make()
    with self.assertRaises(F8Error):
      self.reader((pins[0], '0' * 64, pins[2]))

  def test_path_traversal(self):
    for name in ('../escape', '/absolute', 'x/../escape', 'x//y', 'C:/escape', 'x\\y'):
      with self.subTest(name=name):
        pins = self.make({name: b'x'})
        with self.assertRaises(F8Error):
          self.reader(pins)

  def test_duplicate_entry(self):
    pins = self.make(extra=lambda z: z.writestr('data.json', b'{}'))
    with self.assertRaises(F8Error):
      self.reader(pins)

  def test_unlisted_entry(self):
    pins = self.make(extra=lambda z: z.writestr('unlisted', b'x'))
    with self.assertRaises(F8Error):
      self.reader(pins)

  def test_symlink_entry(self):
    def extra(z):
      entry = zipfile.ZipInfo('link')
      entry.create_system = 3
      entry.external_attr = (stat.S_IFLNK | 0o777) << 16
      z.writestr(entry, 'outside')

    pins = self.make(extra=extra)
    with self.assertRaises(F8Error):
      self.reader(pins)

  def test_special_entry(self):
    def extra(z):
      entry = zipfile.ZipInfo('fifo')
      entry.create_system = 3
      entry.external_attr = (stat.S_IFIFO | 0o600) << 16
      z.writestr(entry, '')

    pins = self.make(extra=extra)
    with self.assertRaises(F8Error):
      self.reader(pins)

  def test_archive_symlink(self):
    pins = self.make()
    link = self.root / 'link.zip'
    link.symlink_to(self.archive)
    with self.assertRaises(F8Error):
      Archive(link, self.root, *pins)

  def test_parent_symlink(self):
    pins = self.make()
    link = self.root / 'link'
    link.symlink_to(self.root, target_is_directory=True)
    with self.assertRaises(F8Error):
      Archive(link / self.archive.name, self.root, *pins)

  def test_outside_capability_root(self):
    pins = self.make()
    other = self.root / 'other'
    other.mkdir()
    with self.assertRaises(F8Error):
      Archive(self.archive, other, *pins)

  def test_member_and_total_bounds(self):
    pins = self.make({'data.json': b'x' * 1000})
    for limits in (replace(Limits(), member_bytes=500), replace(Limits(), outer_total_bytes=500)):
      with self.subTest(limits=limits), self.assertRaises(F8Error):
        self.reader(pins, limits)

  def test_inner_gzip_bound(self):
    raw = gzip.compress(b'[' + b'0,' * 1000 + b'0]', mtime=0)
    pins = self.make({'trace.gz': raw})
    with self.reader(pins, replace(Limits(), inner_trace_bytes=100, compression_ratio=10000)) as a:
      with self.assertRaises(F8Error):
        a.trace('trace.gz')

  def test_inner_cumulative_bound(self):
    raw = gzip.compress(b'[0,0,0]', mtime=0)
    pins = self.make({'trace.gz': raw})
    with self.reader(pins, replace(Limits(), inner_total_bytes=10)) as a:
      a.trace('trace.gz')
      with self.assertRaises(F8Error):
        a.trace('trace.gz')

  def test_malformed_json_and_constants(self):
    for raw in (b'{', b'{"a":1,"a":2}', b'[NaN]', b'[Infinity]', b'9' * 5000):
      with self.subTest(raw=raw[:30]), self.assertRaises(F8Error):
        json_value(raw)

  def test_output_exclusive_and_safe(self):
    folder = self.root / 'new-output'
    with Output(folder, forbidden=(self.root / 'source',)) as out:
      out.write('report.json', {'qualification': False})
      with self.assertRaises(F8Error):
        out.write('report.json', {})
      with self.assertRaises(F8Error):
        out.write('../escape', {})
    with self.assertRaises(F8Error):
      Output(folder, forbidden=())

  def test_output_symlink_and_forbidden(self):
    parent = self.root / 'real'
    parent.mkdir()
    (self.root / 'link').symlink_to(parent, target_is_directory=True)
    with self.assertRaises(F8Error):
      Output(self.root / 'link' / 'out', forbidden=())
    with self.assertRaises(F8Error):
      Output(parent / 'out', forbidden=(parent,))

  def test_no_extraction(self):
    pins = self.make()
    before = set(self.root.iterdir())
    with self.reader(pins):
      pass
    self.assertEqual(set(self.root.iterdir()), before)

  def test_true_directory_count_precedes_zip_parser(self):
    import struct
    from unittest.mock import patch

    pins = self.make({'one': b'1', 'two': b'2', 'three': b'3'})
    raw = bytearray(self.archive.read_bytes())
    at = raw.rfind(b'PK\x05\x06')
    struct.pack_into('<HH', raw, at + 8, 1, 1)
    self.archive.write_bytes(raw)
    pins = (sha(raw), *pins[1:])
    with patch('tools.cyberpilot.f8_evidence_reader_v1.zipfile.ZipFile') as parser:
      with self.assertRaises(F8Error):
        self.reader(pins, replace(Limits(), entries=2))
      parser.assert_not_called()

  def test_compression_ratio_bound(self):
    pins = self.make({'data': b'0' * 10000})
    with self.assertRaises(F8Error):
      self.reader(pins, replace(Limits(), compression_ratio=0))

  def test_declared_entry_count_bound(self):
    pins = self.make()
    with self.assertRaises(F8Error):
      self.reader(pins, replace(Limits(), entries=1))

  def test_cumulative_read_budget(self):
    pins = self.make()
    with self.assertRaises(F8Error):
      self.reader(pins, replace(Limits(), processed_member_bytes=1))

  def test_member_hash_mismatch_with_resealed_zip(self):
    pins = self.make()
    with zipfile.ZipFile(self.archive) as z:
      entries = {n: z.read(n) for n in z.namelist()}
    entries['data.json'] = b'{}'
    with zipfile.ZipFile(self.archive, 'w') as z:
      for name, value in entries.items():
        z.writestr(name, value)
    with self.assertRaises(F8Error):
      self.reader((sha(self.archive.read_bytes()), *pins[1:]))

  def test_in_place_archive_mutation_before_completion(self):
    pins = self.make()
    with self.reader(pins) as a:
      with self.archive.open('r+b') as writer:
        writer.seek(-1, 2)
        writer.write(b'X')
      with self.assertRaises(F8Error):
        a.finish()

  def test_invalid_gzip(self):
    pins = self.make({'invalid.gz': b'not a gzip stream'})
    with self.reader(pins) as a:
      with self.assertRaises(F8Error):
        a.trace('invalid.gz')

  def test_output_budget(self):
    with Output(self.root / 'bounded', forbidden=(), file_limit=20, total_limit=25) as out:
      with self.assertRaises(F8Error):
        out.write('too-large.json', {'large': 'x' * 30})
      out.write('one.json', {'x': 1})
      out.write('two.json', {'x': 1})
      with self.assertRaises(F8Error):
        out.write('three.json', {'x': 'long'})

  def test_missing_evidence_member(self):
    pins = self.make()
    with self.reader(pins) as a:
      with self.assertRaises(F8Error):
        a.json('missing.json')
