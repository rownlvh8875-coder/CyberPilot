"""Exact continuous synthetic interval reference; no IO or Controller path."""
import hashlib
import json
import re
from fractions import Fraction

CONTRACT_ID = 'F70_SYNTHETIC_EXACT_INTERVAL_V1'
FIELDS = {'schema_version', 'context_id', 'source_kind', 'command_unit', 'rate_unit', 'time_unit',
          'reference_command', 'previous_command', 'admissible_interval', 'previous_time_ns',
          'current_time_ns', 'previous_sequence', 'current_sequence', 'gates'}
GATES = {'previous_active', 'active', 'previous_override', 'override', 'reset_between_samples'}
I64_MIN, I64_MAX, U64_MAX = -(1 << 63), (1 << 63)-1, (1 << 64)-1

class SyntheticReferenceError(ValueError):
  """Fixed diagnostic code only."""

def need(condition, code):
  if not condition:
    raise SyntheticReferenceError(code)

def ratio(value):
  need(type(value) is dict and all(type(k) is str for k in value) and set(value) == {'numerator', 'denominator'}, 'F70S_RATIO')
  n, d = value['numerator'], value['denominator']
  need(type(n) is str and type(d) is str, 'F70S_RATIO')
  need(len(n.lstrip('-')) <= 128 and len(d) <= 128, 'F70S_RATIO')
  need(re.fullmatch(r'(0|-?[1-9][0-9]*)', n) is not None and
       re.fullmatch(r'[1-9][0-9]*', d) is not None, 'F70S_RATIO')
  numerator, denominator = int(n), int(d)
  result = Fraction(numerator, denominator)
  need(result.numerator == numerator and result.denominator == denominator, 'F70S_RATIO')
  return result

def encoded(value):
  return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}

def interval(lower, upper):
  return {'lower': encoded(lower), 'upper': encoded(upper)}

def evaluate(request):
  need(type(request) is dict, 'F70S_REQUEST_TYPE')
  need(all(type(k) is str for k in request) and set(request) == FIELDS, 'F70S_FIELDS')
  need(type(request['schema_version']) is str and request['schema_version'] == '1' and
       type(request['source_kind']) is str and request['source_kind'] == 'PREREGISTERED_SYNTHETIC_INTERVAL', 'F70S_SOURCE')
  need(type(request['context_id']) is str and re.fullmatch(r'F70S_[A-Z0-9_]+', request['context_id']) is not None, 'F70S_CONTEXT_ID')
  need(all(type(request[k]) is str and request[k] == v for k, v in
           [('command_unit', 'normalized_command'), ('rate_unit', 'normalized_command/s'), ('time_unit', 'ns')]), 'F70S_UNITS')
  gates = request['gates']
  need(type(gates) is dict and all(type(k) is str for k in gates) and set(gates) == GATES and all(type(v) is bool for v in gates.values()), 'F70S_FLAGS')
  bounds = request['admissible_interval']
  need(type(bounds) is dict and all(type(k) is str for k in bounds) and set(bounds) == {'lower', 'upper'}, 'F70S_FIELDS')
  n, p, a, b = (ratio(request['reference_command']), ratio(request['previous_command']),
                 ratio(bounds['lower']), ratio(bounds['upper']))
  need(all(-1 <= v <= 1 for v in (n, p, a, b)), 'F70S_DOMAIN')
  need(a <= b, 'F70S_INTERVAL_ORDER')
  t0, t1 = request['previous_time_ns'], request['current_time_ns']
  need(type(t0) is int and type(t1) is int, 'F70S_TIME_TYPE')
  need(I64_MIN <= t0 <= I64_MAX and I64_MIN <= t1 <= I64_MAX, 'F70S_TIME_RANGE')
  need(t1 > t0, 'F70S_TIME_ORDER')
  delta = t1-t0
  need(delta <= I64_MAX, 'F70S_DT_RANGE')
  s0, s1 = request['previous_sequence'], request['current_sequence']
  need(type(s0) is int and type(s1) is int and 0 <= s0 <= U64_MAX and 0 <= s1 <= U64_MAX and s1 == s0+1, 'F70S_SEQUENCE')
  need(a <= p <= b, 'F70S_ANCHOR')
  reasons = []
  if gates['reset_between_samples']:
    reasons.append('RESET_INTERVAL')
  if not gates['previous_active'] or not gates['active']:
    reasons.append('LATERAL_INACTIVE')
  if gates['previous_override'] or gates['override']:
    reasons.append('DRIVER_OVERRIDE')
  digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
  result = {'identity': 'F70_SYNTHETIC_EXACT_INTERVAL_RESULT_V1', 'contract_id': CONTRACT_ID,
            'input_sha256': digest, 'status': 'NOT_EVALUATED', 'reason_codes': reasons,
            'dt_s': None, 'L_up': None, 'L_down': None, 'r': None, 'rate_interval': None,
            'sign_interval': None, 'intersection_bounds': None, 'is_nonempty': None,
            'candidate_output': None, 'command_generated': False, 'controller_invocations': 0,
            'runtime_authority': 'NONE', 'source_schema_qualified_for_controller': False,
            'physical_response_evaluated': False, 'performance_qualified': False,
            'synthetic_assumption_only': True, 'source_provenance': 'CALLER_DECLARED_SYNTHETIC_ASSUMPTION_ONLY'}
  if reasons:
    return result
  dt = Fraction(delta, 1000000000)
  up, down = (b-p)/dt, (a-p)/dt
  r = min(up, -down)
  low, high = p-r*dt, p+r*dt
  sign_low, sign_high = min(Fraction(0), n), max(Fraction(0), n)
  left, right = max(low, sign_low), min(high, sign_high)
  nonempty = left <= right
  result.update(status='FEASIBLE' if nonempty else 'CONSTRAINT_CONFLICT',
                dt_s=encoded(dt), L_up=encoded(up), L_down=encoded(down), r=encoded(r),
                rate_interval=interval(low, high), sign_interval=interval(sign_low, sign_high),
                intersection_bounds=interval(left, right), is_nonempty=nonempty)
  return result

def canonical_summary(request):
  return (json.dumps(evaluate(request), sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
