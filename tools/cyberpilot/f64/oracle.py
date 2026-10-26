"""Independent integer/common-denominator oracle; no production or generator imports."""
import json
import math


def compute(data):
  x = json.loads(data)
  t, y, scale = x['times_ns'], x['numerators'], x['denominator']
  # Reference uses integer gcd/lcm reduction, not Fraction or production helpers.
  def digits(value):
    parts = []
    while value:
      value, remainder = divmod(value, 10**1000)
      parts.append(str(remainder))
    return '0' if not parts else parts[-1] + ''.join(p.zfill(1000) for p in reversed(parts[:-1]))
  def reduced(numerator, denominator):
    common = math.gcd(numerator, denominator)
    return {'numerator': digits(numerator//common), 'denominator': digits(denominator//common)}
  fractions = []
  for i in range(1, len(t)):
    numerator = (y[i]-y[i-1])*1000000000
    denominator = scale*(t[i]-t[i-1])
    common = math.gcd(numerator, denominator)
    fractions.append((numerator//common, denominator//common))
  count = len(fractions)
  shared = math.lcm(*(q for _, q in fractions)) if count else 1
  integers = [p*(shared//q) for p, q in fractions]
  ordered = sorted(abs(n) for n in integers)
  squared = reduced(sum(n*n for n in integers), count*shared*shared) if count else None
  def percentile(p):
    position, rest = divmod((count-1)*p, 100)
    numerator = ordered[position]*100
    if rest:
      numerator += rest*(ordered[position+1]-ordered[position])
    return reduced(numerator, 100*shared)
  return {'schema': 'F64_EXACT_ADJACENT_RATE_METRICS_V1', 'sample_count': len(t), 'pair_count': count,
          'duration_ns': t[-1]-t[0], 'rate_unit': 'normalized_command/s',
          'mean_square_unit': 'normalized_command^2/s^2', 'weighting': 'EQUAL_PAIR', 'initial_prepend': False,
          'status': 'METRICS_AVAILABLE' if count else 'INSUFFICIENT_PAIRS',
          'rate_mean_square': squared, 'rate_rms_exact': {'sqrt_of': squared} if count else None,
          'abs_rate_p95': percentile(95) if count else None,
          'abs_rate_p99': percentile(99) if count else None,
          'max_abs_rate': reduced(ordered[-1], shared) if count else None,
          'max_abs_delta': reduced(max(abs(y[i]-y[i-1]) for i in range(1, len(y))), scale) if count else None}
