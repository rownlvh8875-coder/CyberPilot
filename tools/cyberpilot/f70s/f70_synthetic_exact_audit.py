"""Independent integer-pair arithmetic audit; no Primary or Fraction helpers."""
import hashlib
import json
from math import gcd

CONTRACT_ID = 'F70_SYNTHETIC_EXACT_INTERVAL_V1'

class AuditError(ValueError):
  """Fixed diagnostic code only."""

def require(ok, code):
  if not ok:
    raise AuditError(code)

def parse(value):
  require(type(value) is dict and all(type(k) is str for k in value) and set(value) == {'numerator', 'denominator'}, 'F70S_RATIO')
  n, d = value['numerator'], value['denominator']
  require(type(n) is str and type(d) is str, 'F70S_RATIO')
  body = n.removeprefix('-')
  require(0 < len(body) <= 128 and 0 < len(d) <= 128, 'F70S_RATIO')
  require(all('0' <= c <= '9' for c in body+d), 'F70S_RATIO')
  require((body == '0' or not body.startswith('0')) and not d.startswith('0') and n != '-0', 'F70S_RATIO')
  ni, di = int(n), int(d)
  require(di > 0 and gcd(abs(ni), di) == 1, 'F70S_RATIO')
  return ni, di

def normal(n, d):
  if d < 0:
    n, d = -n, -d
  g = gcd(abs(n), d)
  return n//g, d//g

def add(x, y):
  return normal(x[0]*y[1]+y[0]*x[1], x[1]*y[1])

def sub(x, y):
  return normal(x[0]*y[1]-y[0]*x[1], x[1]*y[1])

def divide(x, y):
  return normal(x[0]*y[1], x[1]*y[0])

def compare(x, y):
  difference = x[0]*y[1]-y[0]*x[1]
  return (difference > 0)-(difference < 0)

def smaller(x, y):
  return x if compare(x, y) <= 0 else y

def larger(x, y):
  return x if compare(x, y) >= 0 else y

def packed(x):
  return {'numerator': str(x[0]), 'denominator': str(x[1])}

def packed_interval(a, b):
  return {'lower': packed(a), 'upper': packed(b)}

def evaluate(request):
  require(type(request) is dict, 'F70S_REQUEST_TYPE')
  names = {'schema_version', 'context_id', 'source_kind', 'command_unit', 'rate_unit', 'time_unit',
           'reference_command', 'previous_command', 'admissible_interval', 'previous_time_ns',
           'current_time_ns', 'previous_sequence', 'current_sequence', 'gates'}
  require(all(type(k) is str for k in request) and set(request) == names, 'F70S_FIELDS')
  require(type(request['schema_version']) is str and request['schema_version'] == '1' and
          type(request['source_kind']) is str and request['source_kind'] == 'PREREGISTERED_SYNTHETIC_INTERVAL', 'F70S_SOURCE')
  label = request['context_id']
  require(type(label) is str and label.startswith('F70S_') and len(label) > 5 and
          all('A' <= c <= 'Z' or '0' <= c <= '9' or c == '_' for c in label[5:]), 'F70S_CONTEXT_ID')
  for key, expected in [('command_unit', 'normalized_command'), ('rate_unit', 'normalized_command/s'), ('time_unit', 'ns')]:
    require(type(request[key]) is str and request[key] == expected, 'F70S_UNITS')
  gates = request['gates']
  require(type(gates) is dict and all(type(k) is str for k in gates) and
          set(gates) == {'previous_active', 'active', 'previous_override', 'override', 'reset_between_samples'}
          and all(type(v) is bool for v in gates.values()), 'F70S_FLAGS')
  bounds = request['admissible_interval']
  require(type(bounds) is dict and all(type(k) is str for k in bounds) and set(bounds) == {'lower', 'upper'}, 'F70S_FIELDS')
  n, p = parse(request['reference_command']), parse(request['previous_command'])
  a, b = parse(bounds['lower']), parse(bounds['upper'])
  for value in [n, p, a, b]:
    require(compare(value, (-1, 1)) >= 0 and compare(value, (1, 1)) <= 0, 'F70S_DOMAIN')
  require(compare(a, b) <= 0, 'F70S_INTERVAL_ORDER')
  previous, current = request['previous_time_ns'], request['current_time_ns']
  require(type(previous) is int and type(current) is int, 'F70S_TIME_TYPE')
  minimum, maximum = -(2**63), 2**63-1
  require(minimum <= previous <= maximum and minimum <= current <= maximum, 'F70S_TIME_RANGE')
  require(current > previous, 'F70S_TIME_ORDER')
  ns = current-previous
  require(ns <= maximum, 'F70S_DT_RANGE')
  first, second = request['previous_sequence'], request['current_sequence']
  require(type(first) is int and type(second) is int and 0 <= first < 2**64 and 0 <= second < 2**64 and second-first == 1, 'F70S_SEQUENCE')
  require(compare(a, p) <= 0 and compare(p, b) <= 0, 'F70S_ANCHOR')
  why = []
  if gates['reset_between_samples']:
    why.append('RESET_INTERVAL')
  if not (gates['previous_active'] and gates['active']):
    why.append('LATERAL_INACTIVE')
  if gates['previous_override'] or gates['override']:
    why.append('DRIVER_OVERRIDE')
  digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
  out = {'identity': 'F70_SYNTHETIC_EXACT_INTERVAL_RESULT_V1', 'contract_id': CONTRACT_ID,
         'input_sha256': digest, 'status': 'NOT_EVALUATED', 'reason_codes': why,
         'dt_s': None, 'L_up': None, 'L_down': None, 'r': None, 'rate_interval': None,
         'sign_interval': None, 'intersection_bounds': None, 'is_nonempty': None,
         'candidate_output': None, 'command_generated': False, 'controller_invocations': 0,
         'runtime_authority': 'NONE', 'source_schema_qualified_for_controller': False,
         'physical_response_evaluated': False, 'performance_qualified': False,
         'synthetic_assumption_only': True, 'source_provenance': 'CALLER_DECLARED_SYNTHETIC_ASSUMPTION_ONLY'}
  if why:
    return out
  duration = normal(ns, 1000000000)
  left_width, right_width = sub(p, a), sub(b, p)
  radius = smaller(left_width, right_width)
  rate = divide(radius, duration)
  lower, upper = sub(p, radius), add(p, radius)
  slo, shi = smaller((0, 1), n), larger((0, 1), n)
  ilow, ihigh = larger(lower, slo), smaller(upper, shi)
  matches = compare(ilow, ihigh) <= 0
  out.update(status='FEASIBLE' if matches else 'CONSTRAINT_CONFLICT',
             dt_s=packed(duration), L_up=packed(divide(right_width, duration)),
             L_down=packed(divide(sub(a, p), duration)), r=packed(rate),
             rate_interval=packed_interval(lower, upper), sign_interval=packed_interval(slo, shi),
             intersection_bounds=packed_interval(ilow, ihigh), is_nonempty=matches)
  return out

def canonical_summary(request):
  return (json.dumps(evaluate(request), sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
