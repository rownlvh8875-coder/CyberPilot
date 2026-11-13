"""Portable source-only public-facts probe; never a comma installer."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.cyberpilot_web_native.device_probe import MODEL_SOURCE, collect  # noqa: E402
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


def export_release(output):
  output = check_output_path(ROOT, output)
  output.mkdir()
  build_bundle(output / 'CYBERPILOT_DEVICE_PROBE.zip')
  (output / 'HOST_OBSERVATION.json').write_text(json.dumps(collect(), ensure_ascii=False, sort_keys=True, indent=2) + '\n')
  sums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
  (output / 'SHA256SUMS.txt').write_text(''.join(f'{sha}  {name}\n' for name, sha in sums.items()))
  manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
  (output / 'MANIFEST.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  destination = parser.add_mutually_exclusive_group(required=True)
  destination.add_argument('--output', type=Path)
  destination.add_argument('--release-dir', type=Path)
  args = parser.parse_args()
  if args.release_dir:
    export_release(args.release_dir)
    print('Read-only device probe package and host observation exported.')
  else:
    build_bundle(args.output)
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == '__main__':
  main()
