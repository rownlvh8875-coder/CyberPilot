"""Private F41-C01 recorded-command fidelity; no controller or actuator execution.

Framing/zstd checks adapt the verified F42 f42_common.py algorithm.
Source pins come from the sealed F45 evidence, not the current cereal schema.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
import importlib
from functools import cache
from pathlib import Path
import stat
import struct
import sys


RAW_SHA = '9db34f2698d6857c2f4c07298b973b3f731c76b0b5441f2a54159edcfa43d5a5'
RAW_BYTES = 11452764
MANIFEST_BYTES = 5895
SOURCE_COMMIT = 'a559fcd971ccaa5a87befb8ec080f59a2966325b'
MANIFEST_SHA = '96ec3bc609beac9fba027d5adf83ce72c2d7d70013e00e878c14e9da996dfa94'
# F42 bounded-analysis resource contract, not a driving-performance threshold.
MAX_DECODED_BYTES = 512 * 1024**2
CHUNK_BYTES = 65536
MAX_CAPNP_SEGMENTS = 512
ROOT = Path(__file__).resolve().parents[2]
SECURITY_PATCH_IDENTITY = 'F51_SECURITY_PATCH_CANDIDATE_V1'
SECURITY_HELPER_SHA = '932decf5067d305dae0df25612c79fa0bc5a6c8052f0830a374a415d549f953d'
PUBLIC_ERROR_CODES = frozenset((
  'ACTUAL_PRODUCER_CONSUMER_BINDING_UNPROVEN',
  'ARCHIVE_TIMESTAMP_REVERSAL',
  'ARCHIVE_TIME_ORDER_ERROR_OBSERVED',
  'CLOCK_ACQUISITION_UNQUALIFIED',
  'COMMAND_FIDELITY_MISMATCH',
  'CONTROLLER_DIAGNOSTIC_COMPANION',
  'CONTROLLER_FAMILY_MISMATCH',
  'COVERAGE_ACCOUNTING_ERROR',
  'CROSS_SEGMENT_BINDING',
  'CYBERPILOT_F46_RECORDED_COMMAND_OBSERVER_V1',
  'CYBERPILOT_F47_RECORDED_INPUT_CANDIDATES_V1',
  'D2',
  'DECLARED_MESSAGE_AGE_EXCEEDED',
  'DECLARED_MESSAGE_AGE_ONLY',
  'DECOMPRESSION_RESOURCE_CAP',
  'DIRTY_RECORDED_SOURCE',
  'DRIVER_OVERRIDE',
  'DUPLICATE_LATEST_TIMESTAMP',
  'DUPLICATE_MESSAGE',
  'EQUAL_MESSAGE_TIMESTAMP',
  'F19',
  'F46_4450_RECORD_MISMATCH',
  'F46_IMPLEMENTATION_BLOCKED',
  'F46_INPUT_QUALITY_OBSERVER_PASS',
  'F46_INSUFFICIENT_RECORDED_STATE',
  'F46_RECORDED_COMMAND_REPLAY_PASS',
  'F46_SOURCE_BINDING_BLOCKED',
  'F46_SOURCE_DRIFT',
  'F47_IMPLEMENTATION_FAIL',
  'F47_IMPLEMENTATION_PASS',
  'FILE_IDENTITY_MISMATCH',
  'FILE_UNAVAILABLE',
  'FUTURE_FILE_PREDECESSOR_BYPASSED',
  'FUTURE_INPUT_REJECTED',
  'HISTORICAL_SERVICE_MAPPING_UNQUALIFIED',
  'I',
  'IDENTITY_MESSAGE_MISSING',
  'INCOMPLETE_CONTROLLER_STATE',
  'INCORRECT_SERVICE_BINDING',
  'INCORRECT_SOURCE_BINDING',
  'INCORRECT_SOURCE_IDENTITY',
  'INPUT_BINDING_UNQUALIFIED',
  'INPUT_MISSING',
  'INTERNAL_STATE_UNAVAILABLE',
  'INVALID_AGE_CONTRACT',
  'INVALID_ARGUMENTS',
  'INVALID_CAPNP_SEGMENTS',
  'INVALID_CLI_ARGUMENT',
  'INVALID_HEADER',
  'INVALID_INPUT',
  'INVALID_LATEST_EVENT',
  'INVALID_SERVICE_FREQUENCY',
  'INVALID_SERVICE_REGISTRY',
  'INVALID_TIMESTAMP_TYPE',
  'INVALID_ZSTD',
  'LATERAL_INACTIVE',
  'LEGACY_UNRESOLVED',
  'MESSAGE_COVERAGE_MISMATCH',
  'MISSING_INPUT',
  'MISSING_PRIOR_INPUT',
  'MONOTONIC_OBSERVED',
  'NONE',
  'NONFINITE_RATE',
  'NONFINITE_VALUE',
  'NO_EARLIER_FILE_EVENT',
  'NO_GO',
  'ONLY_FUTURE_MESSAGE_TIMESTAMPS',
  'PERFORMANCE_NOT_EVALUATED',
  'PER_SERVICE_ORDER_ERROR',
  'PRIVACY_VIOLATION',
  'PROCESSED_COMMAND_OBSERVATION_ONLY',
  'READER_BLOCKED',
  'RECORDED_INPUT_CANDIDATE',
  'RECORDED_INPUT_MESSAGE_CANDIDATE',
  'RECORDED_INTEGER_TIMESTAMP_RELATION_ONLY',
  'RECORD_COVERAGE_MISMATCH',
  'RLOG_REQUIRED',
  'SCHEMA_MANIFEST_MISMATCH',
  'SCHEMA_MISMATCH',
  'SERVICE_REGISTRY_MISSING',
  'SOURCE_SCHEMA_UNQUALIFIED',
  'STALE_INPUT',
  'TEMPORAL_BINDING_AMBIGUOUS',
  'TIMESTAMP_REVERSAL',
  'TRUNCATED_CAPNP',
  'TRUNCATED_ZSTD',
  'UNAVAILABLE',
  'UNQUALIFIED',
  'UNSAFE_OUTPUT',
  'UNVERIFIED_FRESHNESS',
  'WIRE_ORDER_MISMATCH',
  'WITHIN_DECLARED_AGE',
  'WRONG_SERVICE_ROLE',
))


@cache
def security():
  path = ROOT / 'tools/cyberpilot/cli_security_f51.py'
  need(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == SECURITY_HELPER_SHA, 'SECURITY_SOURCE_DRIFT')
  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  module = importlib.import_module('tools.cyberpilot.cli_security_f51')
  need(Path(module.__file__).resolve() == path, 'SECURITY_SOURCE_DRIFT')
  return module


FIELDS = {
  'carControl': ('actuators.torque', 'actuators.steeringAngleDeg', 'actuators.curvature',
                 'currentCurvature', 'latActive', 'enabled', 'longActive'),
  'controlsState': ('curvature', 'desiredCurvature', 'lateral.output', 'lateral.active', 'lateral.saturated', 'lateral.union'),
  'carState': ('vEgo', 'steeringAngleDeg', 'steeringPressed', 'canValid'),
  'carOutput': ('actuatorsOutput.torque', 'actuatorsOutput.torqueOutputCan'),
  'selfdriveState': ('active', 'enabled'),
  'modelV2': ('frameId', 'frameIdExtra', 'timestampEof'),
}
BOOL_FIELDS = frozenset(('latActive', 'enabled', 'longActive', 'lateral.active', 'lateral.saturated',
                         'steeringPressed', 'canValid', 'active'))
EXPECTED_COUNTS = {'carControl': 6000, 'controlsState': 6000, 'carState': 6001,
                   'carOutput': 6001, 'selfdriveState': 6001, 'modelV2': 1200}
DIAGNOSTICS = ('MISSING_INPUT', 'INVALID_INPUT', 'NONFINITE_VALUE', 'TIMESTAMP_REVERSAL',
               'DUPLICATE_MESSAGE', 'STALE_INPUT', 'UNVERIFIED_FRESHNESS', 'LATERAL_INACTIVE',
               'DRIVER_OVERRIDE', 'INCOMPLETE_CONTROLLER_STATE', 'NONFINITE_RATE',
               'ARCHIVE_TIMESTAMP_REVERSAL', 'MISSING_PRIOR_INPUT', 'FUTURE_INPUT_REJECTED')


class BindingError(ValueError):
  """Only fixed error codes may cross the private decoder boundary."""


def need(condition, code):
  if not condition:
    raise BindingError(code)


def digest(data):
  return hashlib.sha256(data).hexdigest()


def canonical(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()


def read_regular(path, expected_bytes=None, max_bytes=None):
  if isinstance(path, security().FileRef):
    return security().read_output(path, expected_bytes, max_bytes)
  try:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
      info = os.fstat(stream.fileno())
      need(stat.S_ISREG(info.st_mode), 'FILE_UNAVAILABLE')
      need(expected_bytes is None or info.st_size == expected_bytes, 'FILE_IDENTITY_MISMATCH')
      bound = expected_bytes if expected_bytes is not None else max_bytes
      return stream.read() if bound is None else stream.read(bound + 1)
  except OSError as error:
    raise BindingError('FILE_UNAVAILABLE') from error


def read_verified(path, expected_sha, expected_bytes):
  data = read_regular(path, expected_bytes)
  need(len(data) == expected_bytes and digest(data) == expected_sha, 'FILE_IDENTITY_MISMATCH')
  return data


def validate_metadata(source_commit, dataset_sha):
  need(source_commit == SOURCE_COMMIT, 'INCORRECT_SOURCE_IDENTITY')
  need(dataset_sha == RAW_SHA, 'CROSS_SEGMENT_BINDING')


def verify_source(source_root, manifest_path):
  data = read_regular(manifest_path, max_bytes=MANIFEST_BYTES)
  need(len(data) == MANIFEST_BYTES and digest(data) == MANIFEST_SHA, 'SCHEMA_MANIFEST_MISMATCH')
  manifest = json.loads(data)
  need(manifest['recorded_commit'] == SOURCE_COMMIT, 'INCORRECT_SOURCE_IDENTITY')
  root = Path(source_root)
  need(not root.is_symlink(), 'SCHEMA_MISMATCH')
  for name, pin in manifest['files'].items():
    relative = Path(name)
    need(not relative.is_absolute() and '..' not in relative.parts, 'SCHEMA_MISMATCH')
    path = root / relative
    need(not any(parent.is_symlink() for parent in (path, *path.parents)), 'SCHEMA_MISMATCH')
    need(digest(read_verified(path, pin['sha256'], pin['bytes'])) == pin['sha256'], 'SCHEMA_MISMATCH')
  need({p.relative_to(root).as_posix() for p in root.rglob('*.capnp')} ==
       {n for n in manifest['files'] if n.endswith('.capnp')}, 'SCHEMA_MISMATCH')
  return manifest


def decompress(raw):
  import zstandard
  need(bool(raw), 'TRUNCATED_ZSTD')
  output, total, at, decoder = [], 0, 0, None
  try:
    while at < len(raw):
      if decoder is None:
        decoder = zstandard.ZstdDecompressor().decompressobj()
      chunk = raw[at:at + CHUNK_BYTES]
      at += len(chunk)
      data = decoder.decompress(chunk)
      total += len(data)
      need(total <= MAX_DECODED_BYTES, 'DECOMPRESSION_RESOURCE_CAP')
      output.append(data)
      if decoder.eof:
        at -= len(decoder.unused_data)
        decoder = None
    need(decoder is None, 'TRUNCATED_ZSTD')
    return b''.join(output)
  except zstandard.ZstdError as error:
    raise BindingError('INVALID_ZSTD') from error


def message_slices(data):
  at = 0
  while at < len(data):
    start = at
    need(len(data) - at >= 8, 'TRUNCATED_CAPNP')
    count = struct.unpack_from('<I', data, at)[0] + 1
    need(1 <= count <= MAX_CAPNP_SEGMENTS, 'INVALID_CAPNP_SEGMENTS')
    table_bytes = ((count + 2) // 2) * 8
    need(at + table_bytes <= len(data), 'TRUNCATED_CAPNP')
    sizes = struct.unpack_from('<' + 'I' * count, data, at + 4)
    at += table_bytes + sum(sizes) * 8
    need(at <= len(data), 'TRUNCATED_CAPNP')
    yield start, at


@dataclass(frozen=True, slots=True)
class Record:
  ordinal: int
  service: str
  timestamp_ns: int
  valid: bool
  values: tuple[tuple[str, object], ...]
  binding: str


def check_projection(record):
  need(type(record.values) is tuple and all(type(pair) is tuple and len(pair) == 2 for pair in record.values), 'PRIVACY_VIOLATION')
  need(record.service in FIELDS, 'PRIVACY_VIOLATION')
  keys = [key for key, _ in record.values]
  need(len(keys) == len(set(keys)) and set(keys) <= set(FIELDS[record.service]), 'PRIVACY_VIOLATION')
  need(all(type(v) in (bool, int, float, str) for _, v in record.values), 'PRIVACY_VIOLATION')


def json_value(value):
  if type(value) is float and not math.isfinite(value):
    return {'nonfinite': 'NaN' if math.isnan(value) else ('+Infinity' if value > 0 else '-Infinity')}
  return value


def tape_bytes(records):
  rows = []
  for record in records:
    check_projection(record)
    row = asdict(record)
    row['values'] = {k: json_value(v) for k, v in record.values}
    rows.append(canonical(row))
  return b''.join(rows)


def assess_age(source_ns, consumer_ns, *, max_age_ns=None):
  if source_ns is None:
    return 'MISSING_INPUT'
  if source_ns > consumer_ns:
    return 'INPUT_BINDING_UNQUALIFIED'
  if max_age_ns is None:
    return 'UNQUALIFIED'
  need(type(max_age_ns) is int and max_age_ns >= 0, 'INVALID_AGE_CONTRACT')
  return 'STALE_INPUT' if consumer_ns - source_ns > max_age_ns else 'WITHIN_DECLARED_AGE'


def observe(records, binding, expected_counts, *, age_contract=None):
  if age_contract is not None:
    need(set(age_contract) == {'max_age_ns', 'provenance'} and
         type(age_contract['max_age_ns']) is int and age_contract['max_age_ns'] >= 0 and
         isinstance(age_contract['provenance'], str) and bool(age_contract['provenance'].strip()), 'INVALID_AGE_CONTRACT')
  diagnostics = Counter(dict.fromkeys(DIAGNOSTICS, 0))
  counts, previous_times, observed_times, deltas = Counter(), {}, {}, defaultdict(list)
  previous_archive_service, last_model_time, cross_service_reversals = None, None, 0
  previous_ordinal, previous_archive_time, archive_reversals = -1, None, 0
  previous_command, command_count, valid_count = None, 0, 0
  rates, windows, window_start, states = [], [], None, Counter(lateral_active=0, lateral_inactive=0, driver_override=0)
  for record in records:
    check_projection(record)
    need(record.binding == binding, 'INCORRECT_SOURCE_BINDING')
    need(type(record.ordinal) is int and record.ordinal > previous_ordinal, 'WIRE_ORDER_MISMATCH')
    previous_ordinal = record.ordinal
    need(type(record.timestamp_ns) is int, 'INVALID_TIMESTAMP_TYPE')
    counts[record.service] += 1
    diagnostics['UNVERIFIED_FRESHNESS'] += 1
    if previous_archive_time is not None and record.timestamp_ns < previous_archive_time:
      archive_reversals += 1
      diagnostics['ARCHIVE_TIMESTAMP_REVERSAL'] += 1
      cross_service_reversals += previous_archive_service != record.service
    previous_archive_time = record.timestamp_ns
    previous_archive_service = record.service
    last_time = previous_times.get(record.service)
    valid = record.valid is True and record.timestamp_ns > 0
    diagnostics['INVALID_INPUT'] += not valid
    if record.service in observed_times:
      deltas[record.service].append(record.timestamp_ns - observed_times[record.service])
    observed_times[record.service] = record.timestamp_ns
    if last_time is not None:
      delta = record.timestamp_ns - last_time
      if delta <= 0:
        diagnostics['DUPLICATE_MESSAGE' if delta == 0 else 'TIMESTAMP_REVERSAL'] += 1
        valid = False
    previous_times[record.service] = max(last_time or record.timestamp_ns, record.timestamp_ns)
    values = dict(record.values)
    if set(values) != set(FIELDS[record.service]):
      diagnostics['MISSING_INPUT'] += 1
      valid = False
    nonfinite = any(type(v) is float and not math.isfinite(v) for v in values.values())
    if nonfinite:
      diagnostics['NONFINITE_VALUE'] += 1
      valid = False
    wrong_types = any(type(v) is not bool if k in BOOL_FIELDS else
                      type(v) is not str if k == 'lateral.union' else type(v) not in (int, float)
                      for k, v in values.items())
    if wrong_types:
      diagnostics['INVALID_INPUT'] += 1
      valid = False
    if record.service == 'carState' and values.get('steeringPressed') is True:
      states['driver_override'] += 1
      diagnostics['DRIVER_OVERRIDE'] += 1
    if record.service == 'modelV2':
      last_model_time = record.timestamp_ns if valid else None
    if record.service != 'carControl':
      continue
    age_status = assess_age(last_model_time, record.timestamp_ns,
                            max_age_ns=age_contract['max_age_ns'] if age_contract is not None else None)
    if age_status == 'MISSING_INPUT':
      diagnostics['MISSING_PRIOR_INPUT'] += 1
    elif age_status == 'INPUT_BINDING_UNQUALIFIED':
      diagnostics['FUTURE_INPUT_REJECTED'] += 1
    elif age_status == 'STALE_INPUT':
      diagnostics['STALE_INPUT'] += 1
    index = command_count
    command_count += 1
    diagnostics['INCOMPLETE_CONTROLLER_STATE'] += 1
    if values.get('latActive') is True:
      states['lateral_active'] += 1
    elif values.get('latActive') is False:
      states['lateral_inactive'] += 1
      diagnostics['LATERAL_INACTIVE'] += 1
    if valid:
      valid_count += 1
      if window_start is None:
        window_start = index
      if previous_command is not None and previous_command[2] == values['latActive']:
        rate = (values['actuators.torque'] - previous_command[1]) * 1e9 / (record.timestamp_ns - previous_command[0])
        if math.isfinite(rate):
          rates.append(rate)
        else:
          diagnostics['NONFINITE_RATE'] += 1
      previous_command = (record.timestamp_ns, values['actuators.torque'], values['latActive'])
    else:
      if window_start is not None:
        windows.append([window_start, index - 1])
      window_start, previous_command = None, None
  if window_start is not None:
    windows.append([window_start, command_count - 1])
  for name, count in expected_counts.items():
    diagnostics['MISSING_INPUT'] += max(0, count - counts[name])
  scale = max((abs(x) for x in rates), default=0.)
  rms = scale * math.sqrt(sum((x / scale)**2 for x in rates) / len(rates)) if scale else (0. if rates else None)
  return {
    'command_count': command_count, 'observed_counts': dict(counts),
    'valid_command_count': valid_count, 'invalid_command_count': command_count - valid_count,
    'valid_command_index_windows': windows,
    'expected_counts_match': all(counts[k] == v for k, v in expected_counts.items()),
    'diagnostics': dict(diagnostics), 'state_counts': dict(states),
    'timestamp_statistics': {k: {'count': counts[k], 'delta_count': len(deltas[k]),
                                 'max_delta_ns': max(deltas[k], default=None),
                                 'min_delta_ns': min(deltas[k], default=None)} for k in counts},
    'selected_archive_timestamp_reversals': archive_reversals,
    'archive_cross_service_timestamp_reversals': cross_service_reversals,
    'archive_time_order_status': 'ARCHIVE_TIME_ORDER_ERROR_OBSERVED' if archive_reversals else 'MONOTONIC_OBSERVED',
    'archive_order_is_not_controller_receive_order': True,
    'rate_summary': {'count': len(rates), 'rms_per_s': rms, 'unit': 'recorded-normalized-command/s',
                     'first_history': 'UNAVAILABLE', 'active_transition_pairs_excluded': True},
    'input_binding': 'INPUT_BINDING_UNQUALIFIED', 'input_binding_unqualified_commands': command_count,
    'staleness_qualification': 'UNQUALIFIED' if age_contract is None else 'DECLARED_MESSAGE_AGE_ONLY',
    'stale_input_unknown_commands': command_count if age_contract is None else 0,
    'freshness_qualification': 'UNQUALIFIED',
    'controller_state': 'F46_INSUFFICIENT_RECORDED_STATE',
    'limit_qualification': 'UNQUALIFIED', 'candidate_output': None,
    'runtime_authorized': False, 'vehicle_authority': 'NONE',
    'selected_candidate': None, 'selected_policy': None,
  }


def validate_output(path):
  path = Path(path).absolute()
  need('..' not in path.parts, 'UNSAFE_OUTPUT')
  need(not any(p.is_symlink() for p in (path, *path.parents)), 'UNSAFE_OUTPUT')
  resolved = path.resolve()
  need(not resolved.is_relative_to(ROOT) and not resolved.is_relative_to('/mnt'), 'UNSAFE_OUTPUT')
  need(not any(x.lower() in ('onedrive', 'googledrive', 'google drive', 'dropbox', '.git') for x in path.parts), 'UNSAFE_OUTPUT')
  return resolved


def write_private(path, data):
  security().write_private(path, data)


def decode(raw_path, source_root, manifest_path, output):
  need('qlog' not in Path(raw_path).name.lower(), 'RLOG_REQUIRED')
  verify_source(source_root, manifest_path)
  raw = read_verified(raw_path, RAW_SHA, RAW_BYTES)
  data = decompress(raw)
  import capnp
  capnp.remove_import_hook()
  schema = capnp.load(str(Path(source_root) / 'openpilot/cereal/log.capnp'),
                      imports=[str(Path(source_root) / 'opendbc_repo/opendbc/car')])
  binding = digest(canonical({'raw_sha256': RAW_SHA, 'schema_manifest': MANIFEST_SHA, 'source': SOURCE_COMMIT}))
  counts, records, init_count, params_count = Counter(), [], 0, 0
  for ordinal, (start, end) in enumerate(message_slices(data)):
    with schema.Event.from_bytes(data[start:end]) as event:
      service = event.which()
      counts[service] += 1
      if service == 'initData':
        validate_metadata(str(event.initData.gitSrcCommit) or str(event.initData.gitCommit), RAW_SHA)
        need(not event.initData.dirty, 'DIRTY_RECORDED_SOURCE')
        init_count += 1
      if service == 'carParams':
        need(str(event.carParams.steerControlType) == 'torque' and
             event.carParams.lateralTuning.which() == 'torque', 'CONTROLLER_FAMILY_MISMATCH')
        params_count += 1
      if service not in FIELDS:
        continue
      body = getattr(event, service)
      values = []
      for field in FIELDS[service]:
        if field.startswith('lateral.'):
          member = body.lateralControlState.which()
          need(member == 'torqueState', 'CONTROLLER_FAMILY_MISMATCH')
          value = member if field == 'lateral.union' else getattr(getattr(body.lateralControlState, member), field.split('.')[1])
        else:
          value = body
          for part in field.split('.'):
            value = getattr(value, part)
        values.append((field, value))
      records.append(Record(ordinal, service, int(event.logMonoTime), bool(event.valid), tuple(values), binding))
  need(init_count == 1 and params_count == 1, 'IDENTITY_MESSAGE_MISSING')
  need(sum(counts.values()) == 86400 and len(counts) == 57, 'MESSAGE_COVERAGE_MISMATCH')
  write_private(output / 'recorded_commands.jsonl', tape_bytes(records))
  reader = {'dataset': 'F41-C01', 'raw_sha256': RAW_SHA, 'raw_bytes': len(raw), 'source_commit': SOURCE_COMMIT,
            'schema_manifest_sha256': MANIFEST_SHA, 'binding': binding, 'all_service_counts': dict(counts),
            'total_messages': sum(counts.values()), 'selected_records': len(records),
            'decoder_sha256': digest(Path(__file__).read_bytes()), 'no_controller_execution': True}
  write_private(output / 'reader.json', canonical(reader))


def load_tape(data):
  records = []
  special = {'NaN': float('nan'), '+Infinity': float('inf'), '-Infinity': -float('inf')}
  for line in data.splitlines():
    row = json.loads(line)
    values = tuple((k, special[v['nonfinite']] if isinstance(v, dict) else v) for k, v in row['values'].items())
    records.append(Record(row['ordinal'], row['service'], row['timestamp_ns'], row['valid'], values, row['binding']))
  return tuple(records)


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise BindingError('INVALID_CLI_ARGUMENT')


def _main():
  parser = PrivateParser(prog='f46', description=__doc__)
  for name in ('raw', 'source-root', 'source-manifest', 'output'):
    parser.add_argument('--' + name, required=True)
  parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--output-dir-fd', type=int, help=argparse.SUPPRESS)
  parser.add_argument('--worker-proof-fd', type=int, help=argparse.SUPPRESS)
  output, owns_output, secure = None, False, None
  try:
    args = parser.parse_args()
    secure = security()
    location = validate_output(args.output)
    if args.worker:
      output = secure.from_worker(location, args.output_dir_fd, args.worker_proof_fd)
      with secure.private_decoder():
        decode(args.raw, args.source_root, args.source_manifest, output)
      return 0
    need(args.output_dir_fd is None and args.worker_proof_fd is None, 'WORKER_OWNERSHIP_REQUIRED')
    output = secure.SecureDirectory.create(location)
    owns_output = True
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--raw', args.raw,
               '--source-root', args.source_root, '--source-manifest', args.source_manifest, '--output', str(output)]
    result = secure.run_worker(command, output, timeout=120)
    if result.returncode != 0:
      raise BindingError(secure.worker_error(result.stdout, 'F46_SOURCE_BINDING_BLOCKED:', PUBLIC_ERROR_CODES))
    tape = read_regular(output / 'recorded_commands.jsonl')
    reader = json.loads(read_regular(output / 'reader.json'))
    summary = observe(load_tape(tape), reader['binding'], EXPECTED_COUNTS)
    summary.update({'schema': 'CYBERPILOT_F46_RECORDED_COMMAND_OBSERVER_V1', 'dataset': 'F41-C01',
                    'raw_sha256': RAW_SHA, 'source_commit': SOURCE_COMMIT, 'schema_manifest_sha256': MANIFEST_SHA,
                    'tape_sha256': digest(tape), 'total_messages': reader['total_messages'],
                    'service_count': len(reader['all_service_counts']), 'implementation_sha256': digest(Path(__file__).read_bytes()),
                    'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'runtime': 'NO_GO'})
    bad = sum(summary['diagnostics'][key] for key in ('TIMESTAMP_REVERSAL', 'DUPLICATE_MESSAGE', 'INVALID_INPUT', 'NONFINITE_VALUE', 'NONFINITE_RATE'))
    ok = summary['expected_counts_match'] and bad == 0 and summary['diagnostics']['MISSING_INPUT'] == 0
    summary['recorded_command_status'] = 'F46_RECORDED_COMMAND_REPLAY_PASS' if ok else 'F46_IMPLEMENTATION_BLOCKED'
    summary['observer_status'] = 'F46_INPUT_QUALITY_OBSERVER_PASS'
    write_private(output / 'summary.json', canonical(summary))
    write_private(output / 'result_sha256.json', canonical({'summary.json': digest(canonical(summary)), 'recorded_commands.jsonl': digest(tape)}))
    print(summary['recorded_command_status'])
    return 0 if ok else 3
  except Exception as error:
    code = secure.error_code(error, PUBLIC_ERROR_CODES) if secure is not None else (
      'INVALID_CLI_ARGUMENT' if isinstance(error, BindingError) and error.args == ('INVALID_CLI_ARGUMENT',)
      else 'UNEXPECTED_INTERNAL_ERROR')
    if owns_output and output is not None:
      try:
        write_private(output / 'failure.json', canonical({'status': 'F46_SOURCE_BINDING_BLOCKED', 'reason': code}))
      except Exception:
        pass
    print('F46_SOURCE_BINDING_BLOCKED:' + code)
    return 2
  finally:
    if output is not None:
      output.close()


def main():
  try:
    return _main()
  except Exception:
    print('F46_SOURCE_BINDING_BLOCKED:UNEXPECTED_INTERNAL_ERROR')
    return 2


if __name__ == '__main__':
  sys.exit(main())
