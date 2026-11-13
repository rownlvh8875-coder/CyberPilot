"""Portable source-only public-facts probe; never a comma installer."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.cyberpilot_web_native.device_probe import MODEL_SOURCE  # noqa: E402
from tools.cyberpilot_web_native.prepare import check_output_path  # noqa: E402


def build_bundle(output):
  output = check_output_path(ROOT, output)
  files = {'device_probe.py': Path(__file__).with_name('device_probe.py').read_bytes(),
           'README_KO.md': (ROOT / 'docs/CYBERPILOT_DEVICE_PROBE_KO.md').read_bytes(),
           'MODEL_RULE_SOURCE.json': (json.dumps(MODEL_SOURCE, sort_keys=True, indent=2) + '\n').encode()}
  manifest = {'schema_version': 1, 'scope': 'READ_ONLY_PUBLIC_FACTS_NOT_INSTALLER',
              'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
  files['MANIFEST.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
  with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, data in sorted(files.items()):
      info = zipfile.ZipInfo(name, (2026, 11, 13, 0, 0, 0))
      info.compress_type = zipfile.ZIP_DEFLATED
      info.external_attr = 0o100644 << 16
      archive.writestr(info, data, compresslevel=9)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  build_bundle(args.output)
  print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == '__main__':
  main()
