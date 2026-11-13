"""Independent gate for the read-only web component, not a vehicle build."""

import argparse
import hashlib
import json
import py_compile
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.system.cyberpilot_web.readiness import inspect_readiness  # noqa: E402
from tools.cyberpilot_web.distribute import build_bundle  # noqa: E402


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  out = args.output.resolve()
  if out.is_relative_to(ROOT):
    parser.error("verification output must be outside checkout")
  out.mkdir(parents=True, exist_ok=False)
  results = {}

  def command(name, argv):
    with (out / f"{name}.log").open("w") as stream:
      result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    results[name] = {"exit": result.returncode}
    if result.returncode:
      raise RuntimeError(f"{name} failed; inspect {out / (name + '.log')}")

  package = "openpilot/system/cyberpilot_web"
  tooling = "tools/cyberpilot_web"
  config = f"{tooling}/pyproject.toml"
  command("ruff", [sys.executable, "-m", "ruff", "check", "--config", config, package, tooling])
  command("ty", [sys.executable, "-m", "ty", "check", "--project", tooling, package, tooling])
  command("codespell", [sys.executable, "-m", "codespell_lib", package, tooling, "docs/CYBERPILOT_WEB_KO.md", "--skip", "*.lock,.venv", "-L", "assertin"])
  suite = unittest.defaultTestLoader.discover(str(ROOT / tooling / "tests"))
  with (out / "tests.log").open("w") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
  results["tests"] = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)}
  if not result.wasSuccessful():
    raise RuntimeError("unit tests failed")
  sources = sorted((ROOT / package).rglob("*.py")) + sorted(p for p in (ROOT / tooling).rglob("*.py") if ".venv" not in p.parts)
  for index, source in enumerate(sources):
    py_compile.compile(str(source), cfile=str(out / "compile" / f"{index}.pyc"), doraise=True)
  results["compile"] = len(sources)
  command("javascript", ["node", "--check", f"{package}/assets/app.js"])
  for launcher in ("launch_openpilot.sh", "launch_chffrplus.sh"):
    command("syntax-" + launcher, ["bash", "-n", launcher])
  command("browser", [sys.executable, "-B", f"{tooling}/browser_check.py", "--output", str(out / "browser")])
  build_bundle(ROOT, out / "cyberpilot-web-source.zip")
  build_bundle(ROOT, out / "cyberpilot-web-source-repeat.zip")
  a = (out / "cyberpilot-web-source.zip").read_bytes()
  if a != (out / "cyberpilot-web-source-repeat.zip").read_bytes():
    raise RuntimeError("source bundle not deterministic")
  results["bundle_sha256"] = hashlib.sha256(a).hexdigest()
  results["bundle_byte_identical"] = True
  (out / "readiness.json").write_text(json.dumps(inspect_readiness(ROOT), indent=2) + "\n")
  results.update(status="PASS", scope="CLOUD_READ_ONLY_MONITOR_ONLY", vehicle_execution=0, f61_execution=0,
                 actual_rate_calculation=0, device_installation_qualified=False)
  (out / "RESULTS.json").write_text(json.dumps(results, indent=2) + "\n")
  manifest = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file()}
  (out / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
  print(json.dumps(results, indent=2))


if __name__ == "__main__":
  main()
