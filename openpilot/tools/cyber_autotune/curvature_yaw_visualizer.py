"""Render admitted synthetic screening receipts into a network-free standalone viewer."""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.curvature_yaw_screening import SCREENING_CASES, validate_screening_report
from openpilot.tools.cyber_autotune.native_protocol import _invalid_constant, _keys, _unique_pairs, canonical, digest

TEMPLATE = Path(__file__).with_suffix('.html')
SCRIPT = Path(__file__).with_suffix('.js')
MAX_INPUT_BYTES = 16*1024*1024  # bounded report transport, not an acceptance threshold


def validate_payload(payload):
  if type(payload) is not dict:
    raise ValueError('INVALID_VISUALIZER_PAYLOAD')
  _keys(payload, ('reports','catalog_sha256') if 'catalog_sha256' in payload else ('reports',))
  reports = payload['reports']
  if type(reports) is not list or not 1 <= len(reports) <= len(SCREENING_CASES):
    raise ValueError('INVALID_SCREENING_REPORT_COUNT')
  for report in reports:
    validate_screening_report(report)
  names = [r['manifest']['scenario'] for r in reports]
  if len(set(names)) != len(names):
    raise ValueError('DUPLICATE_SCREENING_SCENARIO')
  if 'catalog_sha256' in payload:
    expected = digest(canonical([r['manifest_sha256'] for r in reports]))
    if payload['catalog_sha256'] != expected or tuple(names) != SCREENING_CASES:
      raise ValueError('INVALID_FROZEN_CATALOG_BINDING')


def load_payload(path):
  with Path(path).open('rb') as stream:
    raw = stream.read(MAX_INPUT_BYTES+1)
  if not 0 < len(raw) <= MAX_INPUT_BYTES:
    raise ValueError('INVALID_VISUALIZER_INPUT_SIZE')
  payload = json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  validate_payload(payload)
  return payload


def render_html(payload):
  validate_payload(payload)
  # Sever caller references before any rendering; no date, random value or remote asset.
  payload = json.loads(canonical(payload))
  value = {'reports':payload['reports'],'artifact':{
    'input_sha256':digest(canonical(payload)),
    'renderer_sha256':digest(Path(__file__).read_bytes()),
    'template_sha256':digest(TEMPLATE.read_bytes()),
    'script_sha256':digest(SCRIPT.read_bytes()),
    'scope':'INTERNAL_CONSISTENCY_ONLY_NOT_AUTHENTICATED_EXECUTION',
  }}
  data = canonical(value).decode().replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
  data = data.replace('\u2028','\\u2028').replace('\u2029','\\u2029')
  return TEMPLATE.read_text().replace('@@DATA@@',data).replace('@@SCRIPT@@',SCRIPT.read_text())


def main():
  import argparse
  parser = argparse.ArgumentParser(description='Local synthetic receipt viewer; no lane truth or qualification.')
  parser.add_argument('--input',type=Path,required=True)
  parser.add_argument('--output',type=Path,required=True)
  args = parser.parse_args()
  html = render_html(load_payload(args.input))  # validate entirely before writing output
  args.output.write_text(html)


if __name__ == '__main__':
  main()
