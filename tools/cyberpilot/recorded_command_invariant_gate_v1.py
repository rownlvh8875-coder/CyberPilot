"""F56 read-only recorded-command fidelity and non-executing admission gate.

No Controller callback, proposal generator, current-schema synthesis or transport.
Pure results do not attest data origin; only pinned historical projection reads do.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = 'F56_RECORDED_COMMAND_INVARIANT_GATE_V1'
MAX_COMMANDS = 6000
PINS = {
  'tools/cyberpilot/rlog_observer_regression_v1.py': '8a12a5e6052296c8a588c3840ea4eaa9da8781d265efb59089bd33bace196ef2',
  'tools/cyberpilot/recorded_input_binding_v1.py': 'd0e3fc5371c9478aa9016288ed5ed6631630b9e63c8d2631f6d2a2777e270ae7',
  'tools/cyberpilot/cli_security_f51.py': '932decf5067d305dae0df25612c79fa0bc5a6c8052f0830a374a415d549f953d',
}
# Expected digests are from the preserved F47 seal/repeatability, not discovered inputs.
ARTIFACTS = {
  'reader.json': (2514, '430978eb73d4ed7614c8adc0c2d681258dca3416a0fd9a498faf01a56ecc737a'),
  'recorded_commands.jsonl': (2299528, '7acd71a82c6e10d883c5f9e92f483e69f477e1c3ecef1ee71327fa101f799197'),
  'binding_rows.jsonl': (15543603, 'fb2682c4cb066cca1cabefdaedff0cfd9b8efd54541a30e51a59ebf147d90572'),
  'summary.json': (133054, '959b00c7e6e50707bdd0f93efed3b05427bbab487bfde2f7bfd4febf54dae4ca'),
}
CODES = frozenset(('SOURCE_IDENTITY_MISMATCH', 'INVALID_RECORD', 'INVALID_BINDING',
                   'COMMAND_COVERAGE_MISMATCH', 'COMMAND_FIDELITY_MISMATCH', 'INVALID_QUALIFICATION',
                   'NONFINITE_VALUE', 'NONFINITE_RATE', 'WIRE_ORDER_MISMATCH', 'TIMESTAMP_ERROR',
                   'ARTIFACT_IDENTITY_MISMATCH', 'HISTORICAL_RECEIPT_MISMATCH', 'INVALID_INPUT_SCHEMA', 'OVERLAPPING_OUTPUT'))


class GateError(ValueError):
  """Fixed public codes only."""


def need(value, code):
  if not value:
    raise GateError(code)


def digest(data):
  return hashlib.sha256(data).hexdigest()


def canonical(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def modules():
  for name, expected in PINS.items():
    p = ROOT / name
    need(p.is_file() and not any(x.is_symlink() for x in (p, *p.parents)) and
         digest(p.read_bytes()) == expected, 'SOURCE_IDENTITY_MISMATCH')
  names = ('rlog_observer_regression_v1', 'recorded_input_binding_v1', 'cli_security_f51')
  loaded = tuple(importlib.import_module('tools.cyberpilot.' + n) for n in names)
  need(all(isinstance(m.__file__, str) and Path(m.__file__).resolve() == ROOT / ('tools/cyberpilot/' + n + '.py')
           for n, m in zip(names, loaded, strict=True)), 'SOURCE_IDENTITY_MISMATCH')
  return loaded


@dataclass(frozen=True, slots=True)
class Qualification:
  ordinal: int
  timestamp_ns: int
  primary_status: str
  binding: str


def _commands(records, binding, base):
  need(type(records) is tuple and 0 < len(records) <= MAX_COMMANDS, 'COMMAND_COVERAGE_MISMATCH')
  previous = None
  for record in records:
    need(type(record) is base.Record and record.service == 'carControl' and record.binding == binding,
         'INVALID_RECORD')
    need(type(record.ordinal) is int and 0 <= record.ordinal < 2**64 and
         type(record.timestamp_ns) is int and 0 < record.timestamp_ns < 2**64 and
         type(record.valid) is bool, 'INVALID_RECORD')
    base.check_projection(record)
    values = dict(record.values)
    need(len(record.values) == len(values) == len(base.FIELDS['carControl']) and
         set(values) == set(base.FIELDS['carControl']), 'INVALID_RECORD')
    for name, value in values.items():
      if name in base.BOOL_FIELDS:
        need(type(value) is bool, 'INVALID_RECORD')
      else:
        need(type(value) in (int, float), 'INVALID_RECORD')
        try:
          valid = math.isfinite(value)
        except OverflowError:
          valid = False
        need(valid, 'NONFINITE_VALUE')
    if previous is not None:
      need(record.ordinal > previous.ordinal, 'WIRE_ORDER_MISMATCH')
      need(record.timestamp_ns > previous.timestamp_ns, 'TIMESTAMP_ERROR')
    previous = record
  return records


def evaluate(reference, observed, qualifications, *, binding):
  """Compare immutable recorded observations, never execute or approve a Controller."""
  need(type(binding) is str and re.fullmatch('[a-f0-9]{64}', binding), 'INVALID_BINDING')
  base, temporal, _ = modules()
  reference = _commands(reference, binding, base)
  observed = _commands(observed, binding, base)
  need(len(reference) == len(observed), 'COMMAND_COVERAGE_MISMATCH')
  before, after = base.tape_bytes(reference), base.tape_bytes(observed)
  need(before == after, 'COMMAND_FIDELITY_MISMATCH')
  need(type(qualifications) is tuple and len(qualifications) == len(reference), 'INVALID_QUALIFICATION')
  counts = Counter()
  rates = []
  previous = None
  for record, quality in zip(observed, qualifications, strict=True):
    need(type(quality) is Qualification and type(quality.ordinal) is int and
         type(quality.timestamp_ns) is int and quality.ordinal == record.ordinal and
         quality.timestamp_ns == record.timestamp_ns and quality.binding == binding and
         type(quality.primary_status) is str and quality.primary_status in temporal.STATUSES,
         'INVALID_QUALIFICATION')
    counts[quality.primary_status] += 1
    values = dict(record.values)
    if record.valid:
      if previous is not None and previous[2] == values['latActive']:
        rate = (values['actuators.torque'] - previous[1]) * 1e9 / (record.timestamp_ns - previous[0])
        need(math.isfinite(rate), 'NONFINITE_RATE')
        rates.append(rate)
      previous = (record.timestamp_ns, values['actuators.torque'], values['latActive'])
    else:
      previous = None
  rms = math.hypot(*rates) / math.sqrt(len(rates)) if rates else None
  need(rms is None or math.isfinite(rms), 'NONFINITE_RATE')
  return {
    'identity': IDENTITY, 'data_origin': 'UNATTESTED_PURE_INPUT', 'command_count': len(observed),
    'software_fidelity': 'PASS', 'reference_command_sha256': digest(before),
    'observed_command_sha256': digest(after), 'primary_counts': dict(sorted(counts.items())),
    'invalid_commands': sum(not x.valid for x in observed),
    'lateral_inactive_commands': sum(not dict(x.values)['latActive'] for x in observed),
    'rate': {'observed_pairs': len(rates), 'rms_per_s': rms, 'first_rate': None,
             'units': 'RECORDED_TORQUE_FIELD_UNITS_PER_SECOND',
             'physical_scaling': 'UNQUALIFIED', 'reset_gap_qualification': 'UNKNOWN',
             'certified_continuity_pairs': 0, 'interpolation_or_forward_fill': False},
    'admission': {'status': 'BLOCKED', 'blocked_commands': len(observed),
                  'reason': 'CONTROLLER_EXECUTION_NOT_IMPLEMENTED',
                  'controller_execution_supported': False, 'controller_invocations': 0,
                  'candidate_output': None, 'actual_consumer_input_proven': False},
    'limit_qualification': 'UNQUALIFIED', 'physical_response_qualified': False,
    'target_deadline_qualified': False, 'native_exact_replay_proven': False,
    'runtime_authorized': False, 'vehicle_authority': 'NONE',
    'selected_candidate': None, 'selected_policy': None,
    'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'runtime': 'NO_GO',
  }


def read_artifact(directory, name, expected_sha, expected_bytes):
  data = directory.read(name, expected_bytes=expected_bytes)
  need(len(data) == expected_bytes and digest(data) == expected_sha, 'ARTIFACT_IDENTITY_MISMATCH')
  return data


def _pairs(items):
  out = {}
  for key, value in items:
    need(key not in out, 'INVALID_INPUT_SCHEMA')
    out[key] = value
  return out


def _constant(_):
  raise GateError('NONFINITE_VALUE')


def _json(data):
  return json.loads(data, object_pairs_hook=_pairs, parse_constant=_constant)


def run_private(f46_results, f47_results, output):
  """Only pinned F46/F47 projections; this function cannot parse or open an RLOG."""
  base, temporal, sec = modules()
  first_path = base.validate_output(f46_results)
  second_path = base.validate_output(f47_results)
  output_path = base.validate_output(output)
  need(not any(output_path.is_relative_to(p) or p.is_relative_to(output_path)
               for p in (first_path, second_path)), 'OVERLAPPING_OUTPUT')
  first = sec.SecureDirectory.existing(first_path)
  second = None
  try:
    second = sec.SecureDirectory.existing(second_path)
    tape = read_artifact(first, 'recorded_commands.jsonl', temporal.F46_TAPE_SHA, temporal.F46_TAPE_BYTES)
    inputs = {name: read_artifact(second, name, pin[1], pin[0]) for name, pin in ARTIFACTS.items()}
  finally:
    first.close()
    if second is not None:
      second.close()
  reader, summary = _json(inputs['reader.json']), _json(inputs['summary.json'])
  binding = digest(base.canonical({'raw_sha256': base.RAW_SHA, 'schema_manifest': base.MANIFEST_SHA,
                                   'source': base.SOURCE_COMMIT}))
  need(reader['raw_sha256'] == base.RAW_SHA and reader['recorded_source'] == base.SOURCE_COMMIT and
       reader['source_manifest_sha256'] == base.MANIFEST_SHA and reader['binding'] == binding and
       reader['command_sha256'] == ARTIFACTS['recorded_commands.jsonl'][1] and
       reader['command_count'] == MAX_COMMANDS and reader['original_4450_records_verified'] is True,
       'HISTORICAL_RECEIPT_MISMATCH')
  need(summary['command_count'] == MAX_COMMANDS and summary['primary_counts']['SOURCE_SCHEMA_UNQUALIFIED'] == MAX_COMMANDS and
       sum(summary['primary_counts'].values()) == MAX_COMMANDS and
       summary['source_commit'] == base.SOURCE_COMMIT and summary['raw_sha256'] == base.RAW_SHA and
       summary['source_manifest_sha256'] == base.MANIFEST_SHA and
       summary['actual_controller_consumption_proven'] is False and summary['native_exact_replay_proven'] is False,
       'HISTORICAL_RECEIPT_MISMATCH')
  reference = tuple(x for x in base.load_tape(tape) if x.service == 'carControl')
  observed = base.load_tape(inputs['recorded_commands.jsonl'])
  rows = tuple(_json(line) for line in inputs['binding_rows.jsonl'].splitlines())
  qualities = tuple(Qualification(x['command_ordinal'], x['command_timestamp_ns'], x['primary_status'], binding)
                    for x in rows)
  result = evaluate(reference, observed, qualities, binding=binding)
  need(result['command_count'] == MAX_COMMANDS and
       result['primary_counts'] == {'SOURCE_SCHEMA_UNQUALIFIED': MAX_COMMANDS}, 'HISTORICAL_RECEIPT_MISMATCH')
  result.update(
    data_origin='PINNED_HISTORICAL_F46_F47_PROJECTIONS', dataset='F41-C01',
    raw_rlog_opened=False, raw_rlog_sha256=base.RAW_SHA, historical_source=base.SOURCE_COMMIT,
    historical_schema_manifest=base.MANIFEST_SHA,
    historical_reader_implementation=reader['implementation_sha256'],
    current_reader_sources=dict(PINS), gate_source_sha256=digest(Path(__file__).read_bytes()),
    preserved_F47_primary_counts=summary['primary_counts'],
    source_artifact_sha256={name: pin[1] for name, pin in ARTIFACTS.items()},
    original_F46_tape_sha256=temporal.F46_TAPE_SHA,
  )
  body = canonical(result)
  directory = sec.SecureDirectory.create(output_path)
  try:
    directory.write('summary.json', body)
    directory.write('summary.sha256', (digest(body) + '\n').encode())
  finally:
    directory.close()
  return result


def main(argv=None):
  sec = None
  try:
    sec = modules()[2]
    parser = sec.PrivateParser(prog='recorded-command-invariant-gate-v1',
                               description='Pinned private projection fidelity; Controller execution unavailable.')
    parser.add_argument('--f46-results', required=True)
    parser.add_argument('--f47-results', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    run_private(args.f46_results, args.f47_results, args.output)
    print('F56_PRIVATE_GATE_PASS_CONTROLLER_BLOCKED')
    return 0
  except Exception as error:
    code = sec.error_code(error, CODES) if sec is not None else 'SOURCE_IDENTITY_MISMATCH'
    print('F56_BLOCKED:' + code)
    return 2


if __name__ == '__main__':
  raise SystemExit(main())
