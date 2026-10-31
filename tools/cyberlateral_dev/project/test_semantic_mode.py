"""Explicit R21 mode/public-wheel preflight and exact parity mutation coverage."""

import base64
import hashlib
import importlib
import sys
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from v1_helpers import ROOT, package_feature


class SemanticModeTests(unittest.TestCase):
    def demo(self):
        self.assertTrue((ROOT / 'native_qualification/semantic_demo.py').is_file(), 'Missing closed semantic demo')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('native_qualification.semantic_demo')

    def test_import_does_not_load_native_or_original_modules(self):
        before = set(sys.modules)
        self.demo()
        self.assertFalse(any(n.split('.')[0] in {'capnp', 'openpilot', 'opendbc', 'cereal'} for n in set(sys.modules) - before))

    def test_modes_and_missing_or_unexpected_public_wheel_reject_before_spawn(self):
        self.demo()
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        invalid: list[tuple[dict[str, Any], str]] = [
            ({'semantic_bridge': True}, 'PUBLIC_WHEEL_REQUIRED'),
            ({'semantic_bridge': True, 'owned_boundary': True}, 'EXPERIMENT_MODE_CONFLICT'),
            ({'semantic_bridge': 1}, 'EXPLICIT_BOOLEAN_MODE'),
            ({'package_wheel': Path('unused')}, 'UNEXPECTED_PACKAGE_WHEEL'),
        ]
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for kwargs, code in invalid:
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, code):
                    runner.qualify(root / 'python', root / 'capnp', root / 'output', **kwargs)
                with self.assertRaisesRegex(ValueError, code):
                    worker.observe(root / 'capnp', root / 'schema', **kwargs)
            self.assertFalse((root / 'output').exists())

    def test_bad_public_wheel_rejects_before_native_and_preserves_existing_output(self):
        self.demo()
        runner = importlib.import_module('native_qualification.run')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'package.whl'
            wheel.write_bytes(b'not the sealed package')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                runner.qualify(root / 'python', root / 'capnp', root / 'new', semantic_bridge=True, package_wheel=wheel)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'capnp', root, semantic_bridge=True, package_wheel=wheel)
            self.assertFalse((root / 'new').exists())
        self.assertNotIn('capnp', sys.modules)

    def test_parity_detects_swapped_fields_and_negative_zero_loss(self):
        demo = self.demo()
        p = package_feature()
        sample = p.LateralInput(0, -0.0, 1.5, -7.25, False, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')
        state = p.LateralState(0, None, 0, 0)
        demo.compare_preparation(sample, state, sample, state)
        for changed in [replace(sample, driver=-7.25, angle_deg=1.5), replace(sample, request=0.0),
                        replace(sample, limits=replace(sample.limits, STEER_DELTA_DOWN=2))]:
            with self.assertRaisesRegex(ValueError, 'SEMANTIC_ORACLE_PARITY'):
                demo.compare_preparation(changed, state, sample, state)
        with self.assertRaisesRegex(ValueError, 'SEMANTIC_ORACLE_PARITY'):
            demo.compare_preparation(sample, p.LateralState(0, 5, 3, 1), sample, state)

    def test_exact_public_installer_cache_metadata_is_hashed_not_executable(self):
        self.demo()
        worker = importlib.import_module('native_qualification.worker')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            site, wheel = root / 'site', root / 'fixture.whl'
            metadata = site / 'cyberlateral_dev-0.3.0.dist-info'
            metadata.mkdir(parents=True)
            record_name = 'cyberlateral_dev-0.3.0.dist-info/RECORD'
            cache_name = 'cyberlateral_dev-0.3.0.dist-info/uv_cache.json'
            cache = metadata / 'uv_cache.json'
            cache.write_bytes(b'{}')
            digest = base64.urlsafe_b64encode(hashlib.sha256(b'{}').digest()).rstrip(b'=').decode()
            (metadata / 'RECORD').write_text(record_name + ',,\n' + cache_name + ',sha256=' + digest + ',2\n')
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr(record_name, 'wheel RECORD')
            self.assertIn(cache_name, worker.verify_installed(wheel, site))
            cache.write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_RECORD_HASH'):
                worker.verify_installed(wheel, site)


if __name__ == '__main__':
    unittest.main()
