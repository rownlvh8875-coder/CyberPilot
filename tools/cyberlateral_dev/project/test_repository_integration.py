"""Standalone integration must not inherit openpilot/native dependencies."""
import hashlib
import json
import tomllib
import unittest

from v1_helpers import ROOT


class RepositoryIntegrationTests(unittest.TestCase):
    def config(self):
        return tomllib.loads((ROOT/'pyproject.toml').read_text())

    def test_explicit_isolated_pinned_development_group(self):
        config=self.config()
        self.assertIn('dependency-groups',config,'Missing standalone development group')
        self.assertEqual(set(config['dependency-groups']['dev']),{
            'numpy==2.5.3','ruff==0.16.7','ty==0.0.80','codespell==2.4.3','PyYAML==6.0.3'})
        self.assertEqual(config['project']['dependencies'],[])
        self.assertEqual(config['project']['requires-python'],'==3.12.13')
        self.assertNotIn('sources',config.get('tool',{}).get('uv',{}))

    def test_exact_imported_bytes_and_original_project_metadata_preserved(self):
        self.assertIn('dependency-groups',self.config(),'Missing standalone integration config')
        record=json.loads((ROOT/'IMPORTED_ARTIFACT.json').read_bytes())
        self.assertEqual(record['source_sha256'],'c2f9c240aba8d181a4a341cf5e7edce3d74210759ee2b43ed2ed7bdfadbec83a')
        for name,checksum in record['imported_files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),checksum,name)
        self.assertEqual(self.config()['project'],tomllib.loads((ROOT/'reference/r7_pyproject.toml').read_text())['project'])

    def test_lockfile_binds_only_standalone_distribution(self):
        self.assertTrue((ROOT/'uv.lock').is_file(),'Missing standalone lockfile')
        lock=tomllib.loads((ROOT/'uv.lock').read_text())
        names={p['name'] for p in lock['package']}
        self.assertTrue({'cyberlateral-dev','numpy','ruff','ty','codespell','pyyaml'}<=names)
        self.assertFalse({'openpilot','opendbc','pandacan','pycapnp','scons'} & names)


if __name__=='__main__':unittest.main()
