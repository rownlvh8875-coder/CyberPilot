"""Non-actuating historical liveDelay projection; never a current service adapter.

Pure projections check declared pins. Only the CLI's separate reader receipt
attests that selected record bytes came from the one verified private RLOG.
"""
import argparse
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from functools import cache
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import stat
import struct
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = 'HISTORICAL_LIVE_DELAY_OBSERVATION_V1'
RAW_SHA = '9db34f2698d6857c2f4c07298b973b3f731c76b0b5441f2a54159edcfa43d5a5'
RAW_BYTES = 11452764
SOURCE = 'a559fcd971ccaa5a87befb8ec080f59a2966325b'
MANIFEST_SHA = '96ec3bc609beac9fba027d5adf83ce72c2d7d70013e00e878c14e9da996dfa94'
SCHEMA_SHA = '676d82915a0f4f4455183ae263e5b7bf268e71a0f7772b5d0486457702347351'
PRODUCER_SHA = 'cd5922709e4686d105a4bef0dadcd56fda6e64eafc9efabb7c1b58a82c99226a'
EXPECTED_COUNT = 240  # Sealed F42/F47 count for this exact input, not a rate threshold.
STATUS = {'unestimated': 0, 'estimated': 1, 'invalid': 2}  # Historical schema enum.
FROZEN_PINS = {
  'tools/cyberpilot/rlog_observer_regression_v1.py': '8a12a5e6052296c8a588c3840ea4eaa9da8781d265efb59089bd33bace196ef2',
  'tools/cyberpilot/tests/test_rlog_observer_regression_v1.py': 'a43f3b3c3a6461e52d159650b52a13124e710d0a9f40a467a43c5da9643c9330',
  'docs/cyberpilot/changes/rlog-observer-regression-v1.md': '5e0a7fc5e7deda7a77df88d1bbe8af608fd55b98979c5d597ced9a38b11a64d0',
  'tools/cyberpilot/recorded_input_binding_v1.py': 'd0e3fc5371c9478aa9016288ed5ed6631630b9e63c8d2631f6d2a2777e270ae7',
  'tools/cyberpilot/tests/test_recorded_input_binding_v1.py': 'dd7be80b717e9cb9ee4f0a6b8183588ebc0b374da1ef6c66b1ef768522c21253',
}
PAYLOAD_KEYS = frozenset(('ordinal', 'timestamp_ns', 'historical_service', 'event_valid', 'units', 'fields'))
FIELD_KEYS = frozenset(('lateralDelayEstimate', 'lateralDelayEstimateStd', 'status', 'validBlocks', 'calPerc'))


def need(condition, code):
  if not condition:
    raise ValueError(code)


def digest(data):
  return hashlib.sha256(data).hexdigest()


def canonical(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()


@cache
def base():
  for name, expected in FROZEN_PINS.items():
    path = ROOT / name
    need(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == expected, 'PRESERVED_SOURCE_DRIFT')
  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  return importlib.import_module('tools.cyberpilot.rlog_observer_regression_v1')


@dataclass(frozen=True, slots=True)
class Binding:
  dataset_sha256: str = RAW_SHA
  source_commit: str = SOURCE
  schema_manifest_sha256: str = MANIFEST_SHA
  schema_sha256: str = SCHEMA_SHA
  producer_sha256: str = PRODUCER_SHA

  def __post_init__(self):
    need(self.dataset_sha256 == RAW_SHA, 'CROSS_SEGMENT_BINDING')
    need(self.source_commit == SOURCE, 'SOURCE_IDENTITY_MISMATCH')
    need(self.schema_manifest_sha256 == MANIFEST_SHA and self.schema_sha256 == SCHEMA_SHA, 'SCHEMA_IDENTITY_MISMATCH')
    need(self.producer_sha256 == PRODUCER_SHA, 'PRODUCER_IDENTITY_MISMATCH')


DEFAULT_BINDING = Binding()


def float32(value):
  if type(value) is not float:
    raise ValueError('INVALID_FIELD_TYPE')
  need(math.isfinite(value), 'NONFINITE_VALUE')
  try:
    packed = struct.pack('<f', value)
  except OverflowError as error:
    raise ValueError('NOT_EXACT_FLOAT32') from error
  need(struct.unpack('<f', packed)[0] == value, 'NOT_EXACT_FLOAT32')
  return value


def integer(value, minimum, maximum, code):
  if type(value) is not int or not minimum <= value <= maximum:
    raise ValueError(code)
  return value


@dataclass(frozen=True, slots=True)
class Sample:
  ordinal: int
  timestamp_ns: int
  mean_s: float
  std_s: float
  status: str
  event_valid: bool
  valid_blocks: int
  calibration_percent: int

  def __post_init__(self):
    integer(self.ordinal, 0, 2**64-1, 'INVALID_ORDINAL')
    integer(self.timestamp_ns, 1, 2**64-1, 'INVALID_TIMESTAMP')
    float32(self.mean_s)
    float32(self.std_s)
    need(self.std_s >= 0, 'NEGATIVE_STD')
    need(type(self.status) is str and self.status in STATUS, 'INVALID_STATUS')
    need(type(self.event_valid) is bool, 'INVALID_VALIDITY_TYPE')
    integer(self.valid_blocks, -(2**31), 2**31-1, 'INVALID_STATE_TYPE')
    integer(self.calibration_percent, -128, 127, 'INVALID_STATE_TYPE')


@dataclass(frozen=True, slots=True)
class Observation:
  sample: Sample
  binding: Binding

  def __post_init__(self):
    need(type(self.sample) is Sample and type(self.binding) is Binding, 'INVALID_OBSERVATION')

  def to_dict(self):
    s = self.sample
    diagnostics = ['ACQUISITION_TIMESTAMP_UNQUALIFIED', 'PRODUCER_INTERNAL_STATE_UNKNOWN',
                   'ESTIMATE_ORIGIN_UNKNOWN', 'PHYSICAL_DELAY_UNIDENTIFIABLE']
    if s.status != 'estimated':
      diagnostics.append('PRODUCER_REPORTED_' + s.status.upper())
    if not s.event_valid:
      diagnostics.append('EVENT_INVALID')
    if s.std_s == 0:
      diagnostics.append('ZERO_STD_NOT_ACCURACY')
    if not 0 <= s.valid_blocks <= 50 or not 0 <= s.calibration_percent <= 100:
      # Historical lagd BLOCK_NUM=50; progress is a percent, never physical confidence.
      diagnostics.append('HISTORICAL_STATE_RANGE_WARNING')
    if s.mean_s < 0:
      diagnostics.append('NEGATIVE_REPORTED_ESTIMATE')
    return {
      'identity': CONTRACT, 'historical_service': 'liveDelay', 'dataset': 'F41-C01',
      'source_binding': asdict(self.binding),
      'original_message': {'ordinal': s.ordinal, 'logMonoTime_ns': s.timestamp_ns, 'event_valid': s.event_valid,
                           'timestamp_meaning': 'RECORDED_MESSAGE_LABEL_NS',
                           'sensor_acquisition_clock': 'UNKNOWN', 'clock_alignment': 'UNQUALIFIED'},
      'original_fields': {
        'liveDelay.lateralDelayEstimate': {'type': 'Float32', 'units': 's', 'value': s.mean_s,
                                          'float32_hex_le': struct.pack('<f', s.mean_s).hex()},
        'liveDelay.lateralDelayEstimateStd': {'type': 'Float32', 'units': 's', 'value': s.std_s,
                                             'float32_hex_le': struct.pack('<f', s.std_s).hex()},
      },
      'original_state': {
        'status': {'field': 'liveDelay.status', 'type': 'LiveDelayData.Status', 'name': s.status, 'code': STATUS[s.status]},
        'validBlocks': {'field': 'liveDelay.validBlocks', 'type': 'Int32', 'value': s.valid_blocks},
        'calPerc': {'field': 'liveDelay.calPerc', 'type': 'Int8', 'value': s.calibration_percent},
      },
      'original_version': {'state': 'UNKNOWN', 'recorded_value': None, 'reason': 'FIELD_ABSENT_IN_PINNED_HISTORICAL_SCHEMA'},
      'observed_quantities': {'historical_estimate_s': s.mean_s, 'historical_estimate_std_s': s.std_s},
      'producer': {'path': 'openpilot/selfdrive/locationd/lagd.py', 'sha256': self.binding.producer_sha256,
                   'verification_level': 'PINNED_SOURCE_DEFINITION_ONLY', 'internal_state': 'UNKNOWN'},
      'qualification': {'source_schema_status': 'VERIFIED_HISTORICAL_QUANTITY_DEFINITION_ONLY',
                        'data_origin_verification': 'REQUIRES_ASSOCIATED_READER_RECEIPT',
                        'current_service_equivalence': False, 'current_estimator_version': 'UNKNOWN',
                        'physical_delay_qualified': False, 'producer_internal_state': 'UNKNOWN',
                        'controller_consumption_proven': False, 'runtime_authorized': False,
                        'vehicle_authority': 'NONE', 'freshness': 'UNQUALIFIED'},
      'diagnostics': sorted(diagnostics),
    }


def project(payload: Mapping[str, Any], binding: Binding = DEFAULT_BINDING, *, target: str = CONTRACT) -> Observation:
  need(target == CONTRACT, 'CURRENT_SCHEMA_SYNTHESIS_BLOCKED')
  need(type(binding) is Binding, 'SOURCE_IDENTITY_MISMATCH')
  need(isinstance(payload, Mapping), 'INVALID_RECORD_SHAPE')
  values = payload.get('fields')
  if not isinstance(values, Mapping):
    raise ValueError('INVALID_RECORD_SHAPE')
  need('version' not in payload and 'version' not in values, 'UNRECORDED_VERSION')
  need(set(payload) == PAYLOAD_KEYS, 'UNRECORDED_FIELDS')
  need(payload['historical_service'] == 'liveDelay', 'HISTORICAL_SERVICE_REQUIRED')
  need(payload['units'] == 's', 'INVALID_UNIT')
  need('lateralDelayEstimate' in values, 'MISSING_MEAN')
  need('lateralDelayEstimateStd' in values, 'MISSING_STD')
  need(set(values) == FIELD_KEYS, 'UNRECORDED_FIELDS')
  sample = Sample(payload['ordinal'], payload['timestamp_ns'],
                  values['lateralDelayEstimate'], values['lateralDelayEstimateStd'], values['status'],
                  payload['event_valid'], values['validBlocks'], values['calPerc'])
  return Observation(sample, binding)


def validate_sequence(observations):
  values = tuple(observations)
  need(bool(values), 'OBSERVATIONS_MISSING')
  previous = None
  for value in values:
    need(type(value) is Observation, 'INVALID_OBSERVATION')
    if previous is not None:
      need(value.sample.ordinal != previous.ordinal, 'DUPLICATE_MESSAGE')
      need(value.sample.ordinal > previous.ordinal, 'ORIGINAL_ORDER_MISMATCH')
      need(value.sample.timestamp_ns != previous.timestamp_ns, 'DUPLICATE_TIMESTAMP')
      need(value.sample.timestamp_ns > previous.timestamp_ns, 'TIMESTAMP_REVERSAL')
    previous = value.sample
  return values


def observe(payloads, binding=DEFAULT_BINDING):
  return validate_sequence(project(payload, binding) for payload in payloads)


def fidelity_bytes(sample):
  """Network order: ordinal U64, ns U64, mean/std F32, valid bool, blocks I32, progress I8, status U8."""
  return struct.pack('>QQff?ibB', sample.ordinal, sample.timestamp_ns, sample.mean_s, sample.std_s,
                     sample.event_valid, sample.valid_blocks, sample.calibration_percent, STATUS[sample.status])


def summarize(observations):
  values = validate_sequence(observations)
  means = [x.sample.mean_s for x in values]
  stds = [x.sample.std_s for x in values]
  deltas = [b.sample.timestamp_ns-a.sample.timestamp_ns for a, b in zip(values, values[1:], strict=False)]
  diagnostics = Counter()
  status = dict.fromkeys(STATUS, 0)
  for value in values:
    status[value.sample.status] += 1
    diagnostics.update(value.to_dict()['diagnostics'])
  def stats(numbers):
    return {'min': min(numbers), 'max': max(numbers), 'mean': statistics.fmean(numbers),
            'population_std': statistics.pstdev(numbers)}
  return {'identity': CONTRACT, 'dataset': 'F41-C01', 'source_binding': asdict(values[0].binding),
          'observation_count': len(values), 'status_counts': status,
          'event_invalid_count': sum(not x.sample.event_valid for x in values),
          'producer_state_unknown_count': len(values), 'version_unknown_count': len(values),
          'mean_field_observation_s': stats(means), 'std_field_observation_s': stats(stds),
          'diagnostic_counts': dict(diagnostics),
          'time_order': {'first_ordinal': values[0].sample.ordinal, 'last_ordinal': values[-1].sample.ordinal,
                         'duration_ns': values[-1].sample.timestamp_ns-values[0].sample.timestamp_ns,
                         'min_delta_ns': min(deltas, default=None), 'max_delta_ns': max(deltas, default=None),
                         'timestamp_reversals': 0, 'duplicate_timestamps': 0, 'original_order_preserved': True},
          'original_field_fidelity_sha256': digest(b''.join(fidelity_bytes(x.sample) for x in values)),
          'qualification': values[0].to_dict()['qualification'],
          'F47': 'PREVIOUS_SOURCE_SCHEMA_UNQUALIFIED_RESULTS_NOT_CHANGED',
          'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'runtime': 'NO_GO',
          'selected_candidate': None, 'selected_policy': None}


def output_location(args):
  output = base().validate_output(args.output)
  protected = (Path(args.raw).resolve().parent, Path(args.source_root).resolve(),
               Path(args.source_manifest).resolve().parent)
  need(all(not output.is_relative_to(path) and not path.is_relative_to(output) for path in protected), 'INPUT_OUTPUT_OVERLAP')
  return output


def decode(args, output):
  f46 = base()
  raw = f46.read_verified(args.raw, RAW_SHA, RAW_BYTES)
  need('qlog' not in Path(args.raw).name.lower(), 'RLOG_REQUIRED')
  f46.verify_source(args.source_root, args.source_manifest)
  source_root = Path(args.source_root)
  need(digest(f46.read_regular(source_root/'openpilot/cereal/log.capnp')) == SCHEMA_SHA, 'SCHEMA_IDENTITY_MISMATCH')
  need(digest(f46.read_regular(source_root/'openpilot/selfdrive/locationd/lagd.py')) == PRODUCER_SHA, 'PRODUCER_IDENTITY_MISMATCH')
  import capnp
  capnp.remove_import_hook()
  schema = capnp.load(str(source_root/'openpilot/cereal/log.capnp'),
                      imports=[str(source_root/'opendbc_repo/opendbc/car')])
  fields = schema.LiveDelayData.schema.fields
  need(hex(schema.LiveDelayData.schema.node.id) == '0x98dfdb22c44df8d4' and 'version' not in fields, 'SCHEMA_IDENTITY_MISMATCH')
  need(all(fields[n].proto.slot.type.which() == 'float32' for n in ('lateralDelayEstimate', 'lateralDelayEstimateStd')),
       'SCHEMA_IDENTITY_MISMATCH')
  data = f46.decompress(raw)
  selected = []
  for ordinal, (start, end) in enumerate(f46.message_slices(data)):
    with schema.Event.from_bytes(data[start:end]) as event:
      if event.which() != 'liveDelay':
        continue  # No non-liveDelay payload is read or analyzed.
      message = event.liveDelay
      selected.append({'ordinal': ordinal, 'timestamp_ns': int(event.logMonoTime), 'historical_service': 'liveDelay',
                       'event_valid': bool(event.valid), 'units': 's',
                       'fields': {'lateralDelayEstimate': float(message.lateralDelayEstimate),
                                  'lateralDelayEstimateStd': float(message.lateralDelayEstimateStd),
                                  'status': str(message.status), 'validBlocks': int(message.validBlocks),
                                  'calPerc': int(message.calPerc)}})
  need(len(selected) == EXPECTED_COUNT, 'HISTORICAL_COUNT_MISMATCH')
  values = observe(selected)
  projection = b''.join(canonical(x) for x in selected)
  f46.write_private(output/'source_projection.jsonl', projection)
  f46.write_private(output/'reader.json', canonical({
    'identity': CONTRACT, 'raw_sha256': RAW_SHA, 'raw_bytes': RAW_BYTES,
    'raw_hash_verified': True, 'historical_capsule_files_verified': 22,
    'source_binding': asdict(Binding()), 'source_schema_verified': True,
    'selected_service': 'liveDelay', 'selected_message_count': len(values),
    'payload_scope': 'LIVEDELAY_ONLY', 'other_services_analyzed': False,
    'projection_sha256': digest(projection),
    'original_field_fidelity_sha256': digest(b''.join(fidelity_bytes(x.sample) for x in values)),
    'tool_source_sha256': digest(Path(__file__).read_bytes()),
  }))



def verify_worker_output(output, descriptor):
  # Only this invocation's parent-created empty directory may be populated.
  need(type(descriptor) is int and descriptor >= 0, 'WORKER_OWNERSHIP_REQUIRED')
  need(stat.S_ISFIFO(os.fstat(descriptor).st_mode), 'WORKER_OWNERSHIP_REQUIRED')
  with os.fdopen(os.dup(descriptor), 'rb') as stream:
    proof_bytes = stream.read(4097)  # Bounded parent metadata; no data/credentials.
  need(len(proof_bytes) <= 4096, 'WORKER_OWNERSHIP_REQUIRED')
  proof = json.loads(proof_bytes)
  info = output.stat()
  need(proof == {'parent_pid': os.getppid(), 'output': str(output), 'device': info.st_dev, 'inode': info.st_ino},
       'WORKER_OWNERSHIP_REQUIRED')
  need(output.is_dir() and info.st_mode & 0o077 == 0 and not any(output.iterdir()), 'WORKER_OUTPUT_NOT_EMPTY')


def run_worker(command, output):
  # An inherited FIFO proves parent ownership without creating a random artifact.
  read_descriptor, write_descriptor = os.pipe()
  try:
    info = output.stat()
    proof = canonical({'parent_pid': os.getpid(), 'output': str(output), 'device': info.st_dev, 'inode': info.st_ino})
    os.write(write_descriptor, proof)
    os.close(write_descriptor)
    write_descriptor = -1
    return subprocess.run([*command, '--worker-fd', str(read_descriptor)], pass_fds=(read_descriptor,),
                          capture_output=True, timeout=180, check=False)
  finally:
    os.close(read_descriptor)
    if write_descriptor >= 0:
      os.close(write_descriptor)


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise ValueError('INVALID_ARGUMENTS')


def main():
  parser = PrivateParser(prog='f49', description=__doc__)
  for name in ('raw', 'source-root', 'source-manifest', 'output'):
    parser.add_argument('--' + name, required=True)
  parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--worker-fd', type=int, help=argparse.SUPPRESS)
  output, owned = None, False
  try:
    args = parser.parse_args()
    f46 = base()
    output = output_location(args)
    if args.worker:
      verify_worker_output(output, args.worker_fd)
      decode(args, output)
      return 0
    need(args.worker_fd is None, 'WORKER_OWNERSHIP_REQUIRED')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    owned = True
    code_sha = digest(Path(__file__).read_bytes())
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', *sys.argv[1:]]
    result = run_worker(command, output)
    if result.returncode:
      reason = result.stdout.decode(errors='replace').strip().removeprefix('F49_OBSERVER_BLOCKED:')
      raise ValueError(reason if re.fullmatch('[A-Z][A-Z0-9_]{0,79}', reason) else 'READER_BLOCKED')
    reader = json.loads(f46.read_regular(output/'reader.json'))
    projection = f46.read_regular(output/'source_projection.jsonl')
    need(reader['raw_hash_verified'] and reader['source_schema_verified'] and reader['source_binding'] == asdict(Binding()),
         'READER_BINDING_MISMATCH')
    need(reader['projection_sha256'] == digest(projection), 'PROJECTION_DRIFT')
    need(reader['tool_source_sha256'] == code_sha == digest(Path(__file__).read_bytes()), 'TOOL_SOURCE_DRIFT')
    observations = observe(json.loads(line) for line in projection.splitlines())
    need(len(observations) == EXPECTED_COUNT, 'HISTORICAL_COUNT_MISMATCH')
    summary = summarize(observations)
    need(summary['original_field_fidelity_sha256'] == reader['original_field_fidelity_sha256'], 'FIELD_FIDELITY_MISMATCH')
    summary.update({'verified_file_origin': True, 'reader_receipt_sha256': digest(f46.read_regular(output/'reader.json')),
                    'tool_source_sha256': code_sha})
    f46.write_private(output/'observations.jsonl', b''.join(canonical(x.to_dict()) for x in observations))
    f46.write_private(output/'summary.json', canonical(summary))
    names = ('source_projection.jsonl', 'reader.json', 'observations.jsonl', 'summary.json')
    f46.write_private(output/'result_sha256.json', canonical({n: digest(f46.read_regular(output/n)) for n in names}))
    print('F49_HISTORICAL_LIVE_DELAY_OBSERVER_PASS')
    return 0
  except Exception as error:
    message = str(error)
    code = message if isinstance(error, ValueError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}', message) else type(error).__name__
    if owned and output is not None:
      try:
        base().write_private(output/'failure.json', canonical({'status': 'F49_OBSERVER_BLOCKED', 'reason': code}))
      except Exception:
        pass
    print('F49_OBSERVER_BLOCKED:' + code)
    return 2


if __name__ == '__main__':
  sys.exit(main())
