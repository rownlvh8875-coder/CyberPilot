"""F65 inert Source generation and state gate; never a Controller or candidate."""
import hashlib
import math

from tools.cyberpilot.f64 import source

FAMILIES = ('constant', 'linear_ramp', 'piecewise_constant', 'piecewise_linear',
            'deterministic_pulse', 'bounded_noise', 'irregular_valid')
D = (1 << 63) - 1
BASE_AMPLITUDE = 1 << 62
STATUS = 'F65_SOURCE_SEPARATION_PARTIAL_PASS_R_BUDGET_UNRESOLVED'
canonical = source.canonical


class GateError(ValueError):
  """Fixed public codes only."""


def need(condition, code):
  if not condition:
    raise GateError(code)


def generate(spec):
  need(type(spec) is dict and set(spec) == {'family', 'seed', 'split', 'count'}, 'F65_SPEC')
  family, seed, split, count = (spec[k] for k in ('family', 'seed', 'split', 'count'))
  need(type(family) is str and family in FAMILIES and type(seed) is int and 0 <= seed < 1 << 64 and
       type(split) is str and split in ('PUBLIC', 'EVALUATION') and
       type(count) is int and 2 <= count <= 8000, 'F65_SPEC')
  amplitude = BASE_AMPLITUDE + (seed >> 2)
  low = seed & 3
  sign = 1 if split == 'PUBLIC' else -1
  width = count-1
  times, values = [], []
  timestamp = 0
  for i in range(count):
    if i:
      interval = 5000000-low if family == 'irregular_valid' and i % 2 == 0 else 10000000-low
      timestamp += interval
    times.append(timestamp)
    if family == 'constant':
      value = amplitude
    elif family in ('linear_ramp', 'irregular_valid'):
      value = amplitude*(width-i)//width
    elif family == 'piecewise_constant':
      value = amplitude if i == 0 or i < count//3 else -amplitude if i < 2*count//3 else amplitude//2
    elif family == 'piecewise_linear':
      value = amplitude*abs(2*i-width)//width
    elif family == 'deterministic_pulse':
      value = amplitude if i % 4 == 0 else 0
    elif i == 0:
      value = amplitude
    else:
      payload = b'F65_NOISE_V1:' + seed.to_bytes(8, 'big') + i.to_bytes(8, 'big')
      value = int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big') % (2*amplitude+1)-amplitude
    values.append(sign*value)
  # Unchanged scalar observation format. New generator provenance is separate.
  return source.encode_source({'schema_version': source.SCHEMA, 'source_identity': source.IDENTITY,
                               'origin': source.ORIGIN, 'unit': source.UNIT,
                               'times_ns': times, 'numerators': values, 'denominator': D})


def recover_seed(data):
  obj = source.decode_source(data)
  need(len(obj['times_ns']) >= 2 and obj['denominator'] == D and obj['times_ns'][0] == 0, 'F65_SPEC')
  high = abs(obj['numerators'][0])-BASE_AMPLITUDE
  low = 10000000-(obj['times_ns'][1]-obj['times_ns'][0])
  need(0 <= high < 1 << 62 and 0 <= low < 4, 'F65_SPEC')
  return (high << 2) | low


def signal_hash(data):
  obj = source.decode_source(data)
  values = []
  for numerator in obj['numerators']:
    factor = math.gcd(numerator, obj['denominator'])
    values.append([str(numerator//factor), str(obj['denominator']//factor)])
  return hashlib.sha256(canonical({'times_ns': obj['times_ns'], 'normalized_rational_values': values})).hexdigest()


def verify_record(record, data):
  need(type(record) is dict and record.get('sha256') == hashlib.sha256(data).hexdigest() and
       record.get('signal_sha256') == signal_hash(data), 'F65_BUNDLE_MISMATCH')
  need(data == generate(record.get('spec')), 'F65_BUNDLE_MISMATCH')
  return True


def final_gate(value):
  need(type(value) is dict and value.get('status') == STATUS, 'F65_GATE_STATUS')
  for key, expected in [('verified_cases', 14), ('source_overlap', 0), ('metric_mismatches', 0),
                        ('controller_calls', 0), ('SOURCE_SCHEMA_UNQUALIFIED', 6000)]:
    need(type(value.get(key)) is int and value[key] == expected, 'F65_GATE_CONTRACT')
  need('candidate_output' in value and value['candidate_output'] is None and
       value.get('r_budget') == 'R_BUDGET_UNRESOLVED' and value.get('runtime') == 'NO_GO' and
       value.get('NO_ADMISSIBLE_NEXT_CANDIDATE') is True and
       'selected_candidate' in value and value['selected_candidate'] is None and
       'selected_policy' in value and value['selected_policy'] is None and
       value.get('Vehicle_authority') == 'NONE', 'F65_GATE_AUTHORITY')
  return True
