"""R19: preflight must fail closed before any native execution."""

import base64
import csv
import hashlib
import importlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from v1_helpers import ROOT


class NativeQualificationTests(unittest.TestCase):
    def tool(self):
        self.assertTrue((ROOT / 'native_qualification/run.py').is_file(), 'Missing opt-in qualification tool')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.run')

    def worker(self):
        self.tool()
        return importlib.import_module('native_qualification.worker')

    def test_import_does_not_load_native_or_original_modules(self):
        before = set(sys.modules)
        self.tool()
        loaded = set(sys.modules) - before
        self.assertFalse(any(n.split('.')[0] in {'capnp', 'opendbc', 'openpilot', 'cereal'} for n in loaded))

    def test_wrong_wheel_rejects_before_import(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            wheel = Path(scratch) / 'bad.whl'
            wheel.write_bytes(b'not the approved wheel')
            with self.assertRaisesRegex(ValueError, 'WHEEL_IDENTITY'):
                w.verify_inputs(wheel, ROOT / 'reference/car.capnp')
        self.assertNotIn('capnp', sys.modules)

    def test_wrong_schema_rejects_before_import(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            schema = Path(scratch) / 'car.capnp'
            schema.write_bytes(b'not the frozen schema')
            with self.assertRaisesRegex(ValueError, 'SCHEMA_IDENTITY'):
                w.verify_inputs(Path(scratch) / 'missing.whl', schema)

    def test_installed_mutation_or_missing_member_rejects(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'fixture.whl'
            site = root / 'site'
            (site / 'capnp').mkdir(parents=True)
            member = site / 'capnp/module.py'
            member.write_bytes(b'approved')
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('capnp/module.py', b'approved')
            self.assertEqual(w.verify_installed(wheel, site)['capnp/module.py'],
                             '2687f86ed6784b8a5fca36e6c468e12aa44dc3c7e8137e3160d1a95079bdcd02')
            member.write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_IDENTITY'):
                w.verify_installed(wheel, site)
            member.unlink()
            with self.assertRaisesRegex(ValueError, 'INSTALLED_IDENTITY'):
                w.verify_installed(wheel, site)

    def test_installed_symlink_or_unsafe_wheel_path_rejects(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'fixture.whl'
            site = root / 'site'
            site.mkdir()
            payload = root / 'payload'
            payload.write_bytes(b'approved')
            (site / 'module.py').symlink_to(payload)
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('module.py', b'approved')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_IDENTITY'):
                w.verify_installed(wheel, site)
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('../payload', b'approved')
            with self.assertRaisesRegex(ValueError, 'UNSAFE_WHEEL'):
                w.verify_installed(wheel, site)

    def test_existing_output_and_dangling_link_reject_without_spawn(self):
        m = self.tool()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for output in [root, root / 'dangling']:
                if output != root:
                    output.symlink_to(root / 'missing')
                with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                    m.qualify(root / 'missing-python', root / 'missing-wheel', output)

    def test_installer_record_must_cover_and_hash_all_payload_bytes(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            site, wheel = root / 'site', root / 'fixture.whl'
            metadata = site / 'fixture.dist-info'
            metadata.mkdir(parents=True)
            (site / 'module.py').write_bytes(b'approved')
            record_name = 'fixture.dist-info/RECORD'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('module.py', b'approved')
                archive.writestr(record_name, 'original wheel RECORD')
            digest = base64.urlsafe_b64encode(hashlib.sha256(b'approved').digest()).rstrip(b'=').decode()
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerows([['module.py', 'sha256=' + digest, '8'], [record_name, '', '']])
            record = metadata / 'RECORD'
            record.write_text(text.getvalue())
            self.assertIn(record_name, w.verify_installed(wheel, site))
            record.write_text(record_name + ',,\n')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_RECORD'):
                w.verify_installed(wheel, site)

    def test_only_exact_generated_entrypoint_is_permitted(self):
        w = self.worker()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            site, wheel = root / 'env/lib/python3.12/site-packages', root / 'fixture.whl'
            metadata = site / 'pycapnp-2.1.0.dist-info'
            metadata.mkdir(parents=True)
            (root / 'env/bin').mkdir()
            (root / 'env/bin/capnpc-cython').write_bytes(b'installer-generated')
            record_name = 'pycapnp-2.1.0.dist-info/RECORD'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr(record_name, 'original wheel RECORD')
            digest = base64.urlsafe_b64encode(hashlib.sha256(b'installer-generated').digest()).rstrip(b'=').decode()
            record = metadata / 'RECORD'
            record.write_text('../../../bin/capnpc-cython,sha256=' + digest + ',19\n' + record_name + ',,\n')
            self.assertIn('../../../bin/capnpc-cython', w.verify_installed(wheel, site))
            record.write_text('../../../bin/other,sha256=' + digest + ',19\n' + record_name + ',,\n')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_RECORD_PATH'):
                w.verify_installed(wheel, site)

    def test_special_float_encoding_is_exact_and_canonical(self):
        w = self.worker()
        self.assertEqual(w.number(-0.0), {'type': 'builtins.float', 'hex': '-0x0.0p+0'})
        self.assertEqual(w.number(float('inf')), {'type': 'builtins.float', 'hex': 'inf'})
        self.assertEqual(w.number(float('nan')), {'type': 'builtins.float', 'hex': 'nan'})
        self.assertEqual(w.canonical({'n': w.number(float('nan'))}),
                         b'{"n":{"hex":"nan","type":"builtins.float"}}\n')

    def test_numeric_encoding_rejects_non_builtin_float_without_coercion(self):
        w = self.worker()
        for value in [1, True, '0.3', None]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'OBSERVATION_FLOAT_TYPE'):
                w.number(value)

    def test_mismatched_observations_do_not_publish_result(self):
        m = self.tool()
        with self.assertRaisesRegex(ValueError, 'OBSERVATIONS_DIFFER'):
            m.compare_observations({'a': 1}, {'a': 2})


if __name__ == '__main__':
    unittest.main()
