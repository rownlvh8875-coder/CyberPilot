"""Catch actual notice resolution failures rather than mere metadata presence."""
import importlib
import sys
import tempfile
import unittest
import zipfile
from email.parser import BytesParser
from pathlib import Path

from v1_helpers import ROOT, package_feature


class LicenseMetadataTests(unittest.TestCase):
    def backend(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module("build_backend")

    def test_each_declared_notice_resolves_under_wheel_license_root(self):
        with tempfile.TemporaryDirectory() as scratch:
            name = self.backend().build_wheel(scratch)
            with zipfile.ZipFile(Path(scratch) / name) as z:
                metadata_name = next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))
                metadata = BytesParser().parsebytes(z.read(metadata_name))
                declarations = metadata.get_all('License-File', [])
                self.assertEqual(len(declarations), 2)
                for declaration in declarations:
                    target = metadata_name.removesuffix('/METADATA') + '/licenses/' + declaration
                    self.assertIn(target, z.namelist(), f"Unresolvable License-File: {declaration}")
                    self.assertEqual(z.read(target), (ROOT / 'licenses' / Path(declaration).name).read_bytes())

    def test_distribution_and_public_api_versions_match_new_feature_release(self):
        with tempfile.TemporaryDirectory() as scratch:
            name = self.backend().build_wheel(scratch)
            with zipfile.ZipFile(Path(scratch) / name) as z:
                metadata = BytesParser().parsebytes(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))))
            self.assertEqual(metadata['Version'], '0.3.0')
            self.assertEqual(metadata['Version'], package_feature().__version__)


if __name__ == '__main__':
    unittest.main()
