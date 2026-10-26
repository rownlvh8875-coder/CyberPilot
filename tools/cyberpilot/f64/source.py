"""Controller-free public synthetic observation bytes, never actuator commands."""
import hashlib
import json

SCHEMA = 'F64_SYNTHETIC_SOURCE_V1'
IDENTITY = 'F64_CONTROLLER_FREE_SYNTHETIC_OBSERVATIONS_V1'
ORIGIN = 'PUBLIC_SYNTHETIC_FIXTURE'
UNIT = 'normalized_command'
MAX_I64 = (1 << 63) - 1
MAX_U64 = (1 << 64) - 1
MAX_SAMPLES = 8000
MAX_GAP_NS = 10000000
SCALE = 1024
FAMILIES = ('constant', 'linear_ramp', 'piecewise_constant', 'piecewise_linear',
            'deterministic_pulse', 'bounded_noise', 'irregular_valid')
FIELDS = frozenset(('schema_version', 'source_identity', 'origin', 'unit', 'times_ns', 'numerators', 'denominator'))
FACTORS = {'ns': 1, 'us': 1000, 'ms': 1000000, 's': 1000000000}


class ContractError(ValueError):
  """Only fixed non-sensitive codes."""


def need(condition, code):
  if not condition:
    raise ContractError(code)


def canonical(obj):
  return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def to_ns(value, unit):
  need(type(unit) is str and unit in FACTORS, 'F64_TIME_UNIT')
  need(type(value) is int, 'F64_TIME_TYPE')
  need(value >= 0, 'F64_TIME_NEGATIVE')
  result = value * FACTORS[unit]
  need(value <= MAX_I64 and result <= MAX_I64, 'F64_TIME_OVERFLOW')
  return result


def from_ns(value, unit):
  checked = to_ns(value, 'ns')
  need(type(unit) is str and unit in FACTORS, 'F64_TIME_UNIT')
  quotient, remainder = divmod(checked, FACTORS[unit])
  need(remainder == 0, 'F64_TIME_NONINTEGRAL')
  return quotient


def validate_source(obj):
  need(type(obj) is dict and set(obj) == FIELDS, 'F64_SCHEMA_KEYS')
  need(obj['schema_version'] == SCHEMA, 'F64_SCHEMA_VERSION')
  need(obj['source_identity'] == IDENTITY and obj['origin'] == ORIGIN, 'F64_SOURCE_IDENTITY')
  need(obj['unit'] == UNIT, 'F64_UNIT')
  times, values, denominator = obj['times_ns'], obj['numerators'], obj['denominator']
  need(type(times) is list and type(values) is list, 'F64_VALUE_TYPE')
  need(len(times) > 0 and len(values) > 0, 'F64_EMPTY_INPUT')
  need(len(times) == len(values) and len(times) <= MAX_SAMPLES, 'F64_LENGTH')
  need(type(denominator) is int, 'F64_VALUE_TYPE')
  need(0 < denominator <= MAX_I64, 'F64_VALUE_RANGE')
  previous = None
  for timestamp, value in zip(times, values, strict=True):
    checked = to_ns(timestamp, 'ns')
    need(type(value) is int, 'F64_VALUE_TYPE')
    need(abs(value) <= denominator, 'F64_VALUE_RANGE')
    if previous is not None:
      interval = checked - previous
      need(interval != 0, 'F64_TIME_DUPLICATE')
      need(interval > 0, 'F64_TIME_ORDER')
      need(interval <= MAX_GAP_NS, 'F64_TIME_GAP')
    previous = checked
  return obj


def encode_source(obj):
  validate_source(obj)
  return canonical(obj)


def decode_source(data):
  need(type(data) is bytes, 'F64_JSON')
  def unique(pairs):
    out = {}
    for key, value in pairs:
      need(key not in out, 'F64_JSON_DUPLICATE')
      out[key] = value
    return out
  def invalid(_):
    raise ContractError('F64_JSON')
  try:
    obj = json.loads(data.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)
    normalized = canonical(obj)
  except ContractError:
    raise
  except (UnicodeError, ValueError, OverflowError, RecursionError):
    raise ContractError('F64_JSON') from None
  need(normalized == data, 'F64_NONCANONICAL')
  return validate_source(obj)


def generate(spec):
  need(type(spec) is dict and set(spec) == {'family', 'seed', 'count', 'start_ns'}, 'F64_SPEC')
  family, seed, count, start = (spec[k] for k in ('family', 'seed', 'count', 'start_ns'))
  need(type(family) is str and family in FAMILIES and type(seed) is int and 0 <= seed <= MAX_U64 and
       type(count) is int and 1 <= count <= MAX_SAMPLES, 'F64_SPEC')
  to_ns(start, 'ns')
  amplitude = 32 + seed % 32
  width = max(1, count-1)
  denominator = SCALE * width if family in ('linear_ramp', 'piecewise_linear', 'irregular_valid') else SCALE
  times, values = [], []
  timestamp = start
  for i in range(count):
    if i:
      interval = MAX_GAP_NS // 2 if family == 'irregular_valid' and (seed+i) % 2 else MAX_GAP_NS
      timestamp = to_ns(timestamp + interval, 'ns')
    times.append(timestamp)
    if family == 'constant':
      value = 0 if seed == 0 else amplitude
    elif family in ('linear_ramp', 'irregular_valid'):
      value = amplitude * (2*i-width)
    elif family == 'piecewise_constant':
      value = amplitude if i < count//3 else -amplitude if i < 2*count//3 else 0
    elif family == 'piecewise_linear':
      value = amplitude * (width - abs(2*i-width))
    elif family == 'deterministic_pulse':
      value = amplitude if i % 4 == 1 else 0
    else:
      payload = b'F64_NOISE_V1:' + seed.to_bytes(8, 'big') + i.to_bytes(8, 'big')
      value = int.from_bytes(hashlib.sha256(payload).digest()[:4], 'big') % (2*amplitude+1) - amplitude
    values.append(value)
  return encode_source({'schema_version': SCHEMA, 'source_identity': IDENTITY, 'origin': ORIGIN, 'unit': UNIT,
                        'times_ns': times, 'numerators': values, 'denominator': denominator})
