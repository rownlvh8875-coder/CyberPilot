"""Actual local wheel build/RECORD/isolation proof, no publish or vehicle install."""
import base64
import csv
import hashlib
import importlib
import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from v1_helpers import ROOT


class WheelTests(unittest.TestCase):
    def backend(self):
        self.assertTrue((ROOT / "build_backend.py").is_file(), "Missing planned wheel backend")
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module("build_backend")

    def test_deterministic_wheel_record_and_dependency_free_payload(self):
        backend = self.backend()
        with tempfile.TemporaryDirectory() as scratch:
            a, b = Path(scratch) / "one", Path(scratch) / "two"
            name = backend.build_wheel(str(a))
            self.assertEqual(name, backend.build_wheel(str(b)))
            raw = (a / name).read_bytes()
            self.assertEqual(raw, (b / name).read_bytes())
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names = z.namelist()
                self.assertEqual(names, sorted(names))
                self.assertEqual(z.testzip(), None)
                self.assertTrue(all(info.date_time == (2020, 1, 1, 0, 0, 0) for info in z.infolist()))
                files = {n: z.read(n) for n in names}
            record = next(n for n in names if n.endswith('.dist-info/RECORD'))
            covered = set()
            for path, digest, size in csv.reader(io.StringIO(files[record].decode())):
                covered.add(path)
                if path == record:
                    self.assertEqual((digest, size), ("", ""))
                else:
                    expected = base64.urlsafe_b64encode(hashlib.sha256(files[path]).digest()).rstrip(b"=").decode()
                    self.assertEqual(digest, "sha256=" + expected)
                    self.assertEqual(int(size), len(files[path]))
            self.assertEqual(covered, set(names))
            metadata = files[next(n for n in names if n.endswith('.dist-info/METADATA'))].decode()
            self.assertIn("Name: cyberlateral-dev\n", metadata)
            self.assertIn("Requires-Python: ==3.12.13\n", metadata)
            self.assertNotIn("Requires-Dist:", metadata)
            self.assertTrue(any(n.endswith('licenses/opendbc.LICENSE') for n in names))
            self.assertFalse(any(n.endswith(('/kernel.py', '.pth')) or 'reference/' in n for n in names))

    def test_existing_wheel_never_overwritten(self):
        backend = self.backend()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root))
            before = (root / name).read_bytes()
            with self.assertRaises(FileExistsError):
                backend.build_wheel(str(root))
            self.assertEqual((root / name).read_bytes(), before)

    def test_actual_offline_install_into_empty_venv_and_isolated_api(self):
        backend = self.backend()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            dist = root / "dist"
            name = backend.build_wheel(str(dist))
            env = root / "env"
            subprocess.run([sys.executable, "-B", "-m", "venv", "--without-pip", str(env)], check=True, capture_output=True, text=True)
            python = env / "bin/python"
            installed = subprocess.run(["uv", "pip", "install", "--offline", "--no-deps", "--python", str(python), str(dist / name)],
                                       capture_output=True, text=True, check=False)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            code = """
import sys,importlib.util,importlib.metadata,types
assert importlib.util.find_spec('numpy') is None
sys.modules['domain']=types.ModuleType('domain');sys.modules['oracle']=types.ModuleType('oracle')
import cyberlateral_dev as p
assert '/site-packages/cyberlateral_dev/' in p.__file__
r=p.step(p.LateralInput(0,0.3,0.0,0.0,True,p.Limits(5,5,5,0,1,1),'SYNTHETIC_ONLY'),p.initial_state())
assert r.projection.integer_command==2 and r.projection.torque_float32.bits_hex=='3ecccccd'
assert r.next_state.previous_applied==2
assert not importlib.metadata.requires('cyberlateral-dev')
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','opendbc','selfdrive','openpilot','cereal','capnp','kernel','normalized_pipeline'}]
print('ISOLATED_WHEEL_API_PASS')
"""
            result = subprocess.run([str(python), "-I", "-B", "-c", code], cwd=root,
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "ISOLATED_WHEEL_API_PASS\n")


if __name__ == "__main__":
    unittest.main()
