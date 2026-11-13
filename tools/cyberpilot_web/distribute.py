"""Build a reproducible source-only host monitor bundle, never a vehicle image."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path("openpilot/system/cyberpilot_web")


def build_bundle(root: Path, output: Path):
  files = {str(path.relative_to(root)): path.read_bytes()
           for path in sorted((root / PACKAGE).rglob("*")) if path.is_file() and path.suffix in (".py", ".js", ".css", ".html")}
  for name in ("openpilot/__init__.py", "openpilot/system/__init__.py"):
    files[name] = (root / name).read_bytes()
  files["README_KO.md"] = (root / "docs/CYBERPILOT_WEB_KO.md").read_bytes()
  files["run-web.sh"] = b'#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec python3 -B -m openpilot.system.cyberpilot_web "$@"\n'
  manifest = {"schema_version": 1, "scope": "SOURCE_ONLY_READ_ONLY_MONITOR_NOT_VEHICLE_IMAGE",
              "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
  files["MANIFEST.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
  with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, data in sorted(files.items()):
      item = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
      item.compress_type = zipfile.ZIP_DEFLATED
      item.external_attr = (0o100755 if name == "run-web.sh" else 0o100644) << 16
      archive.writestr(item, data, compresslevel=9)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  build_bundle(ROOT, args.output)
  print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == "__main__":
  main()
