"""Catch report mode side effects and installed/source-path dependency leaks."""
import contextlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consumer_reference import expected_simulation
from normalized_reference import NormalizedReference
from test_source_contract import REFERENCE
from trace_reference import reference_rows
from v1_helpers import ROOT, package_feature


class ReportCliTests(unittest.TestCase):
    def cli(self):
        m=package_feature('cyberlateral_dev.cli')
        self.assertTrue(hasattr(m,'build_report_bundle'),'Missing planned report CLI')
        return m

    def test_report_requires_output_before_any_bundle_work(self):
        m=self.cli()
        with (contextlib.redirect_stderr(io.StringIO()),patch.object(m,'build_report_bundle',side_effect=AssertionError('NO_WORK')),
              self.assertRaises(SystemExit) as error):m.main(['--report'])
        self.assertEqual(error.exception.code,2)

    def test_existing_file_directory_and_dangling_link_reject_before_bundle(self):
        m=self.cli()
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch);targets=[root/'file',root/'dir',root/'dead']
            targets[0].write_bytes(b'KEEP');targets[1].mkdir();targets[2].symlink_to(root/'missing',target_is_directory=True)
            for path in targets:
                with (contextlib.redirect_stderr(io.StringIO()),patch.object(m,'build_report_bundle',side_effect=AssertionError('NO_WORK'))):
                    self.assertEqual(m.main(['--report','--output',str(path)]),2)
            self.assertEqual(targets[0].read_bytes(),b'KEEP')
            self.assertTrue(targets[2].is_symlink())

    def test_report_does_not_open_arbitrary_data_mode(self):
        m=self.cli()
        with tempfile.TemporaryDirectory() as scratch:
            target=Path(scratch)/'out'
            with (contextlib.redirect_stderr(io.StringIO()),patch.object(m,'build_report_bundle',side_effect=AssertionError('NO_WORK')),
                  self.assertRaises(SystemExit) as error):m.main(['--report','--output',str(target),'--data','actual_log'])
            self.assertEqual(error.exception.code,2)
            self.assertFalse(target.exists())

    def test_actual_empty_installed_report_twice_and_legacy_mode_independent_parity(self):
        self.cli()
        if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
        backend=importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch);name=backend.build_wheel(str(root/'dist'))
            subprocess.run([sys.executable,'-B','-m','venv','--without-pip',str(root/'env')],check=True,capture_output=True)
            py=root/'env/bin/python'
            result=subprocess.run(['uv','pip','install','--offline','--no-deps','--link-mode=copy','--python',str(py),str(root/'dist'/name)],capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            for out in [root/'one',root/'two']:
                result=subprocess.run([str(py),'-I','-B','-m','cyberlateral_dev','--report','--output',str(out)],cwd=root,capture_output=True,text=True,check=False)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout,'F70UGZ_R7_OFFLINE_TRACE_REPORT_WRITTEN\n')
            files={p.name:p.read_bytes() for p in (root/'one').iterdir()}
            self.assertEqual(files,{p.name:p.read_bytes() for p in (root/'two').iterdir()})
            legacy=subprocess.run([str(py),'-I','-B','-m','cyberlateral_dev'],cwd=root,capture_output=True,check=False)
            self.assertEqual(legacy.returncode,0,legacy.stderr)
            self.assertEqual(files['simulation.json'],legacy.stdout)
            source=json.loads(files['simulation.json']);analysis=json.loads(files['analysis.json'])
            scenarios=package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()
            reference=NormalizedReference((REFERENCE/'carcontroller.py').read_bytes(),(REFERENCE/'lateral.py').read_bytes())
            for scenario,src,flattened in zip(scenarios,source['scenarios'],analysis['scenarios'],strict=True):
                self.assertEqual(src['result'],json.loads(json.dumps(expected_simulation(scenario,reference))))
                self.assertEqual(flattened['rows'],reference_rows(scenario,reference))
            check="""
import importlib.util,sys
assert importlib.util.find_spec('numpy') is None
from cyberlateral_dev.trace_report import build_report_bundle
assert len(build_report_bundle())==5
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','kernel','selfdrive','openpilot','opendbc','cereal','capnp','normalized_reference','output_oracle'}]
print('ISOLATED_REPORT_PASS')
"""
            checked=subprocess.run([str(py),'-I','-B','-c',check],cwd=root,capture_output=True,text=True,check=False)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertEqual(checked.stdout,'ISOLATED_REPORT_PASS\n')


if __name__=='__main__':unittest.main()
