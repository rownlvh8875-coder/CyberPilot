"""Read-only F10 command-rate arithmetic; no policy, Controller or Plant execution."""
from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
import gzip
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from types import MappingProxyType
from typing import Any, cast

TIME_NS = 10_000_000  # F10 integer synthetic time grid; not a hardware deadline.
F10_HEAD = '51c1cdb3327f442d026e5ba3bdcc173438a6aae1'
SECURITY_SHA = '932decf5067d305dae0df25612c79fa0bc5a6c8052f0830a374a415d549f953d'
ACTIONS = frozenset(('baseline', 'NATIVE_PASSTHROUGH', 'CURRENT_RESIDUAL_GUARD_NATIVE',
                     'SAME_SIGN_MIDPOINT_PROJECTION', 'OFFLINE_DELIVERY_ZERO_RESET'))
EVENTS = frozenset(('EXPERIMENT_START', 'CONTROLLER_RESET', 'INACTIVE', 'STEERING_PRESSED',
                    'RELEASE', 'REENGAGEMENT'))
CODES = frozenset(('F60_INVALID_SAMPLE', 'F60_TIME_ORDER', 'F60_EMPTY_INPUT',
                   'F60_INVALID_JSON', 'F60_SOURCE_MISMATCH', 'F60_RECEIPT_MISMATCH',
                   'F60_SCHEMA_MISMATCH', 'F60_ARTIFACT_MISMATCH', 'F60_UNSAFE_INPUT',
                   'F60_PRIVATE_INPUT_BLOCKED', 'F60_INPUT_FILE_MISSING', 'F60_INPUT_OUTPUT_OVERLAP',
                   'F60_COMMON_INPUT_MISMATCH', 'F60_ARITHMETIC_MISMATCH', 'F60_OUTPUT_LOCATION_BLOCKED'))
ROW_KEYS = frozenset(('sequence', 'time_ns', 'input', 'measurement', 'native_input', 'native',
                      'policy', 'raw_candidate', 'command', 'applied_before', 'applied',
                      'plant_before', 'plant_after', 'pose_after', 'reference_pose',
                      'native_state_before_sha256', 'native_state_after_sha256', 'native_pid_i',
                      'native_pid_error', 'events', 'source_sha256', 'previous_receipt_sha256', 'receipt_sha256'))


@dataclass(frozen=True, slots=True)
class FilePin:
  size: int
  sha256: str


# These are historical byte identities, not configurable performance thresholds.
PINS = MappingProxyType({
  'evidence/execution-lock.json': FilePin(4692, '90726716504bf2319e7cd819ddfc99d1c40786b908f166f92585709d39bdce88'),
  'evidence/input-manifest.json': FilePin(4564, '8641a077aaea413d9f72c558f7abc82b864e1e499e118f31088109f6eff858ec'),
  'results/A0-r1/catalog.json': FilePin(30610, '17c1c71e6b97c058fa71ae42fbd825689dad6e251a9f279de597195cc28b45f8'),
  'results/T1-r1/catalog.json': FilePin(30700, '7b5ca0705376d894b6bdac049dc447c28a0c49f5312b9bff7e4eee7e54d5ec0e'),
  'scripts/f10_worker.py': FilePin(9166, '23887f9de706525639567aaf14029a59ac25253038b4168346a64a9295100ac4'),
  'scripts/tracking_policy.py': FilePin(3413, 'bbbcb75a2c52e59d7503e0994f0c82ebb03a2fe26ce10a0e0f51c95938ca6d6a'),
})
TRACES = MappingProxyType({
  'A0': (FilePin(2566169, '1130a91e8041d86abaa0c314948693c398e179fcc26a8b23632c3fa2871e7c52'),
         FilePin(19906675, '98b46185f9d652bb91ca73ba7386179dea684b107b96d02aa0b61e960e366149'),
         '5163bfd9ca61140870ea91efacbe1ac79774a0d5edb8a01adf6551b3c0a84ff5',
         'df00046aafa8e718b6eecdaab717590036d0529e6ec76db1341e8ef2f3a408aa'),
  'T1': (FilePin(2696091, 'ea913c6556487f2b94d6b226a182a2c608d1addad0269a623561a66eebb6aa92'),
         FilePin(18450551, '9e08c5ede1fe03b86b84bcdfe1b36ea2648b3db50056d4704c17badcd97f8fc5'),
         'cee492a4f9e56cb88e01d11e25ae9510aeade97f47e4e75a550af3412e22917e',
         '144d81094ec1bb30ea025fb0b130966e8f2d4e152430e43c0f247e8119bd36b1'),
})


class AttributionError(ValueError):
  """Fixed safe diagnostic codes only."""


def need(value: object, code: str) -> None:
  if not value:
    raise AttributionError(code)


def canonical(value: object) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def _json(data: bytes) -> Any:
  def unique(pairs):
    out = {}
    for key, value in pairs:
      need(key not in out, 'F60_INVALID_JSON')
      out[key] = value
    return out
  def bad(_):
    raise AttributionError('F60_INVALID_JSON')
  try:
    return json.loads(data, object_pairs_hook=unique, parse_constant=bad)
  except (UnicodeError, json.JSONDecodeError) as exc:
    raise AttributionError('F60_INVALID_JSON') from exc


@dataclass(frozen=True, slots=True)
class Sample:
  sequence: int
  time_ns: int
  native: float
  command: float
  action: str
  active: bool
  driver: bool
  events: tuple[str, ...]


def _number(value: object) -> float:
  need(type(value) in (int, float), 'F60_INVALID_SAMPLE')
  number = cast(int | float, value)
  need(abs(number) <= 1 and math.isfinite(number), 'F60_INVALID_SAMPLE')
  return float(number)


def _samples(values: object) -> tuple[Sample, ...]:
  need(type(values) in (tuple, list) and bool(values), 'F60_EMPTY_INPUT')
  validated = cast(tuple[Sample, ...] | list[Sample], values)
  for i, row in enumerate(validated):
    need(type(row) is Sample, 'F60_INVALID_SAMPLE')
    need(type(row.sequence) is int and row.sequence == i and
         type(row.time_ns) is int and row.time_ns == i * TIME_NS, 'F60_TIME_ORDER')
    _number(row.native)
    _number(row.command)
    need(type(row.active) is bool and type(row.driver) is bool and
         type(row.action) is str and row.action in ACTIONS and type(row.events) is tuple and
         all(type(e) is str and e in EVENTS for e in row.events) and
         len(row.events) == len(set(row.events)), 'F60_INVALID_SAMPLE')
    need((row.active and not row.driver) or row.command == 0, 'F60_INVALID_SAMPLE')
  return tuple(validated)


def _ratio(value: Fraction) -> dict[str, str]:
  return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _energy(values: list[tuple[Fraction, Fraction]]) -> dict[str, Any] | None:
  if not values:
    return None
  n = len(values)
  native = sum((a * a for a, _ in values), Fraction()) / n
  correction = sum((b * b for _, b in values), Fraction()) / n
  cross = 2 * sum((a * b for a, b in values), Fraction()) / n
  command = sum(((a + b) ** 2 for a, b in values), Fraction()) / n
  residual = command - native - correction - cross
  need(residual == 0, 'F60_ARITHMETIC_MISMATCH')
  return {'mean_square_exact': {k: _ratio(v) for k, v in
                               {'command': command, 'native': native, 'correction': correction,
                                'cross': cross, 'residual': residual}.items()},
          'command_rate_rms': math.sqrt(float(command)), 'native_rate_rms': math.sqrt(float(native)),
          'correction_rate_rms': math.sqrt(float(correction)), 'cross_mean_square_term': float(cross)}


def attribute_samples(values: object) -> dict[str, Any]:
  """Unattested pure arithmetic never grants historical or Controller source qualification."""
  rows = _samples(values)
  pairs: list[tuple[Fraction, Fraction]] = []
  groups: dict[tuple[str, str], list[tuple[Fraction, Fraction]]] = {}
  excluded: Counter[str] = Counter()
  for previous, current in zip(rows, rows[1:], strict=False):
    if not previous.active or not current.active:
      excluded['INACTIVE_BOUNDARY'] += 1
    elif previous.driver or current.driver:
      excluded['DRIVER_OVERRIDE_BOUNDARY'] += 1
    elif current.events:
      excluded['EVENT_BOUNDARY'] += 1
    else:
      dt = Fraction(current.time_ns - previous.time_ns, 1_000_000_000)
      native = (Fraction(current.native) - Fraction(previous.native)) / dt
      command = (Fraction(current.command) - Fraction(previous.command)) / dt
      item = (native, command - native)
      pairs.append(item)
      groups.setdefault((previous.action, current.action), []).append(item)
  need(len(pairs) + sum(excluded.values()) == len(rows) - 1, 'F60_ARITHMETIC_MISMATCH')
  return {'schema': 'SYNTHETIC_COMMAND_RATE_ATTRIBUTION_V1', 'data_origin': 'UNATTESTED_PURE_INPUT',
          'status': 'ARITHMETIC_IDENTITIES_VERIFIED' if pairs else 'INSUFFICIENT_CONTINUOUS_PAIRS',
          'sample_count': len(rows),
          'eligible_interval_sha256': sha(canonical([(i-1, i) for i in range(1, len(rows))
             if rows[i-1].active and rows[i].active and not rows[i-1].driver and
             not rows[i].driver and not rows[i].events])),
          'sample_sha256': sha(canonical([asdict(x) for x in rows])),
          'valid_pairs': len(pairs), 'excluded_pairs': dict(sorted(excluded.items())),
          'rate_unit': 'normalized_command/s', 'mean_square_unit': 'normalized_command^2/s^2',
          'total': _energy(pairs),
          'transitions': [{'from': key[0], 'to': key[1], 'pairs': len(group), **(_energy(group) or {})}
                          for key, group in sorted(groups.items())],
          'source_schema_qualified_for_controller': False, 'performance_qualified': False,
          'controller_invocations': 0, 'candidate_output': None, 'runtime_authority': 'NONE',
          'native_state_reconstructed': False, 'native_exact_replay_proven': False,
          'physical_delay_identified': False, 'position_heading_evaluated': False,
          'target_deadline_qualified': False}


def compare_attributions(base: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
  need(base.get('sample_count') == trial.get('sample_count') and
       base.get('eligible_interval_sha256') == trial.get('eligible_interval_sha256') and
       base.get('valid_pairs') == trial.get('valid_pairs') and base.get('valid_pairs', 0) > 0 and
       base.get('data_origin') == trial.get('data_origin') == 'UNATTESTED_PURE_INPUT',
       'F60_COMMON_INPUT_MISMATCH')
  def exact(summary, key):
    value = summary['total']['mean_square_exact'][key]
    return Fraction(int(value['numerator']), int(value['denominator']))
  differences = {k: exact(trial, k) - exact(base, k) for k in ('command', 'native', 'correction', 'cross')}
  differences['residual'] = differences['command'] - sum(differences[k] for k in ('native', 'correction', 'cross'))
  need(differences['residual'] == 0, 'F60_ARITHMETIC_MISMATCH')
  return {'difference_mean_square_exact': {k: _ratio(v) for k, v in differences.items()},
          'command_rate_rms_difference': trial['total']['command_rate_rms'] - base['total']['command_rate_rms'],
          'recorded_command_rate_order': 'HIGHER' if differences['command'] > 0 else
                                         'LOWER' if differences['command'] < 0 else 'SAME',
          'causal_effect_identified': False, 'performance_qualified': False}


def _security():
  path = Path(__file__).absolute().parent / 'cli_security_f51.py'
  need(not path.is_symlink() and sha(path.read_bytes()) == SECURITY_SHA, 'F60_SOURCE_MISMATCH')
  module = importlib.import_module('tools.cyberpilot.cli_security_f51')
  need(module.__file__ is not None and Path(module.__file__).absolute() == path, 'F60_SOURCE_MISMATCH')
  return module


def _path(value: Path) -> Path:
  value = Path(value)
  need('..' not in value.parts and '\x00' not in str(value), 'F60_UNSAFE_INPUT')
  value = value.absolute()
  for part in value.parts:
    label = part.casefold().replace('-', '_').replace(' ', '_')
    need('holdout' not in label and 'private_e2' not in label and
         label not in ('.ssh', 'rlog', 'rlog.zst', 'qlog', 'qlog.zst'), 'F60_PRIVATE_INPUT_BLOCKED')
  return value


def _output_path(value: Path) -> Path:
  path = _path(value)
  code_root = Path(__file__).absolute().parents[2]
  need(not path.is_relative_to(code_root) and not code_root.is_relative_to(path),
       'F60_OUTPUT_LOCATION_BLOCKED')
  return path


def _read_fixed(root: Path, relative: str, pin: FilePin) -> bytes:
  root = _path(root)
  name = Path(relative)
  need(type(relative) is str and not name.is_absolute() and relative and
       not any(p in ('..', '.') for p in name.parts) and '\x00' not in relative, 'F60_UNSAFE_INPUT')
  _path(root / name)
  need(sys.platform == 'linux' and hasattr(os, 'geteuid') and os.geteuid() != 0 and
       os.open in os.supports_dir_fd, 'F60_UNSAFE_INPUT')
  need(type(pin) is FilePin and type(pin.size) is int and 0 < pin.size <= 2_696_091 and
       re.fullmatch('[0-9a-f]{64}', pin.sha256), 'F60_ARTIFACT_MISMATCH')
  sec = _security()
  directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
  fd = os.open('/', directory_flags)
  try:
    for part in (*root.parts[1:], *name.parts[:-1]):
      info = os.fstat(fd)
      sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
      need(info.st_uid in (0, os.geteuid()) and
           (not info.st_mode & 0o022 or sticky_root) and
           sec.filesystem_type(fd) in sec.TRUSTED_FS, 'F60_UNSAFE_INPUT')
      next_fd = os.open(part, directory_flags, dir_fd=fd)
      os.close(fd)
      fd = next_fd
    info = os.fstat(fd)
    need(info.st_uid == os.geteuid() and not info.st_mode & 0o022 and
         sec.filesystem_type(fd) in sec.TRUSTED_FS, 'F60_UNSAFE_INPUT')
    file_fd = os.open(name.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    if not stat.S_ISREG(os.fstat(file_fd).st_mode):
      os.close(file_fd)
      raise AttributionError('F60_UNSAFE_INPUT')
    with os.fdopen(file_fd, 'rb') as stream:
      before = os.fstat(stream.fileno())
      need(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and
           before.st_nlink == 1 and not before.st_mode & 0o022 and before.st_size == pin.size,
           'F60_UNSAFE_INPUT')
      data = stream.read(pin.size + 1)
      after = os.fstat(stream.fileno())
      current = os.stat(name.name, dir_fd=fd, follow_symlinks=False)
      need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
           (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns), 'F60_UNSAFE_INPUT')
    need(len(data) == pin.size and sha(data) == pin.sha256, 'F60_ARTIFACT_MISMATCH')
    return data
  except FileNotFoundError as exc:
    raise AttributionError('F60_INPUT_FILE_MISSING') from exc
  finally:
    os.close(fd)


def _decode_history(rows: object, arm: str, source: str, final: str, count: int) -> tuple[Sample, ...]:
  need(type(rows) is list and len(rows) == count and arm in TRACES, 'F60_SCHEMA_MISMATCH')
  previous = '0' * 64
  samples = []
  for i, row in enumerate(cast(list[dict[str, Any]], rows)):
    need(type(row) is dict and set(row) == ROW_KEYS, 'F60_SCHEMA_MISMATCH')
    need(row['source_sha256'] == source, 'F60_SOURCE_MISMATCH')
    need(row['previous_receipt_sha256'] == previous and
         row['receipt_sha256'] == sha(canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})),
         'F60_RECEIPT_MISMATCH')
    previous = row['receipt_sha256']
    frame, policy = row['input'], row['policy']
    need(type(frame) is dict and type(policy) is dict and
         frame['sequence'] == row['sequence'] == i and frame['time_ns'] == row['time_ns'] == i * TIME_NS,
         'F60_TIME_ORDER')
    need(all(type(row[k]) is str and re.fullmatch('[0-9a-f]{64}', row[k])
             for k in ('native_state_before_sha256', 'native_state_after_sha256')), 'F60_SCHEMA_MISMATCH')
    if arm == 'T1':
      need(policy['state_owner'] == 'T1' and policy['mode'] == 'OFFLINE_EXPERIMENTAL_ONLY' and
           policy['runtime_authorized'] is False and policy['vehicle_authority'] == 'NONE' and
           policy['integral_control_authority'] is False and policy['native_pid_intent_verified'] is False and
           canonical(policy['command']) == canonical(row['command']), 'F60_SCHEMA_MISMATCH')
      action = policy['action']
    else:
      result = policy['source_result']
      need(result['variant'] == 'A0' and result['valid'] is True and
           result['execution_stage'] == 'offline_only' and result['live_actuator_authority'] is False and
           result['reason'] == 'baseline', 'F60_SCHEMA_MISMATCH')
      action = result['reason']
    need(type(row['events']) is list, 'F60_SCHEMA_MISMATCH')
    samples.append(Sample(row['sequence'], row['time_ns'], row['native'], row['command'],
                          action, frame['active'], frame['steering_pressed'], tuple(row['events'])))
  need(previous == final, 'F60_RECEIPT_MISMATCH')
  return _samples(tuple(samples))


def analyze_f10_pair(root: Path) -> dict[str, Any]:
  root = _path(root)
  metadata = {name: _read_fixed(root, name, pin) for name, pin in PINS.items()}
  lock = _json(metadata['evidence/execution-lock.json'])
  need(lock['schema'] == 'CYBERPILOT_F10_PREEXECUTION_LOCK_V1' and lock['head'] == F10_HEAD and
       lock['effective'] is False, 'F60_SOURCE_MISMATCH')
  manifest = _json(metadata['evidence/input-manifest.json'])
  entries = [r for r in manifest if r['id'] == 'dev_entry']
  need(len(entries) == 1 and entries[0]['frames'] == 8000 and
       entries[0]['cohort'] == 'DEVELOPMENT', 'F60_SCHEMA_MISMATCH')
  item = entries[0]
  results, provenance, original_rows, catalogs = {}, {}, {}, {}
  for arm, (packed_pin, raw_pin, source, final) in TRACES.items():
    derived = sha(canonical({'lock': lock, 'arm': arm, 'input': item}))
    need(derived == source, 'F60_SOURCE_MISMATCH')
    catalog = _json(metadata[f'results/{arm}-r1/catalog.json'])
    selected = [row for row in catalog if row['id'] == 'dev_entry']
    need(len(selected) == 1, 'F60_SCHEMA_MISMATCH')
    entry = selected[0]
    need(entry['arm'] == arm and entry['source_sha256'] == source and
         entry['trace_sha256'] == raw_pin.sha256 and entry['gzip_sha256'] == packed_pin.sha256 and
         entry['last_receipt_sha256'] == final and entry['frames'] == 8000 and
         entry['performance_qualified'] is False and entry['selected_candidate'] is None and
         entry['vehicle_authority'] == 'NONE' and entry['status'] == 'OFFLINE_EXPERIMENTAL_ONLY',
         'F60_SOURCE_MISMATCH')
    packed = _read_fixed(root, f'results/{arm}-r1/dev_entry.json.gz', packed_pin)
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
      raw = stream.read(raw_pin.size + 1)
    need(len(raw) == raw_pin.size and sha(raw) == raw_pin.sha256, 'F60_ARTIFACT_MISMATCH')
    rows = _json(raw)
    samples = _decode_history(rows, arm, source, final, 8000)
    results[arm] = attribute_samples(samples)
    original_rows[arm], catalogs[arm] = rows, entry
    provenance[arm] = {'gzip_sha256': packed_pin.sha256, 'raw_sha256': raw_pin.sha256,
                       'source_sha256': source, 'last_receipt_sha256': final}
  need(all(canonical(a['input']) == canonical(b['input']) for a, b in
           zip(original_rows['A0'], original_rows['T1'], strict=True)), 'F60_COMMON_INPUT_MISMATCH')
  need(all(catalogs['A0'][k] == catalogs['T1'][k] for k in
           ('input_sha256', 'plant_sha256', 'initial_state_sha256', 'native_identity')),
       'F60_COMMON_INPUT_MISMATCH')
  return {'schema': 'HISTORICAL_F10_COMMAND_RATE_ATTRIBUTION_V1', 'historical_head': F10_HEAD,
          'input_provenance': 'VERIFIED_HISTORICAL_F10_SYNTHETIC_BYTES',
          'implementation_sha256': sha(Path(__file__).read_bytes()), 'security_sha256': SECURITY_SHA,
          'metadata_sha256': {name: pin.sha256 for name, pin in PINS.items()},
          'scenario': 'dev_entry', 'arms': results, 'trace_provenance': provenance,
          'comparison': compare_attributions(results['A0'], results['T1']),
          'common_exogenous_inputs_verified': True, 'own_feedback_may_differ': True,
          'native_state_reconstructed': False, 'controller_invocations': 0, 'candidate_output': None,
          'source_schema_qualified_for_controller': False, 'performance_qualified': False,
          'runtime_authority': 'NONE', 'real_log_SOURCE_SCHEMA_UNQUALIFIED_preserved': 6000,
          'physical_delay_identified': False, 'position_heading_evaluated': False,
          'native_exact_replay_proven': False, 'target_deadline_qualified': False}


def write_result(path: Path, summary: object) -> str:
  path = _output_path(path)
  sec = _security()
  raw = canonical(summary) + b'\n'
  result_sha = sha(raw)
  folder = sec.SecureDirectory.create(path)
  try:
    folder.write('summary.json', raw)
    folder.write('summary.sha256', (result_sha + '\n').encode())
    need(folder.read('summary.json', expected_bytes=len(raw)) == raw, 'F60_ARTIFACT_MISMATCH')
  finally:
    folder.close()
  return result_sha


def main(argv=None) -> int:
  sec = None
  try:
    sec = _security()
    parser = sec.PrivateParser(description='Read-only fixed historical synthetic attribution.')
    parser.add_argument('--f10-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    root, output = _path(Path(args.f10_root)), _output_path(Path(args.output))
    need(not output.is_relative_to(root) and not root.is_relative_to(output), 'F60_INPUT_OUTPUT_OVERLAP')
    summary = analyze_f10_pair(root)
    result_sha = write_result(output, summary)
    print('F60_SYNTHETIC_ATTRIBUTION_VERIFIED')
    print('F60_CANONICAL_SHA256 ' + result_sha)
    return 0
  except Exception as error:
    code = sec.error_code(error, CODES) if sec is not None else (
      error.args[0] if isinstance(error, AttributionError) and error.args and
      type(error.args[0]) is str and error.args[0] in CODES else 'UNEXPECTED_INTERNAL_ERROR')
    print('F60_BLOCKED:' + code)
    return 2


if __name__ == '__main__':
  raise SystemExit(main())
