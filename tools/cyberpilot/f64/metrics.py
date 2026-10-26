"""Exact adjacent-rate production path for inert public observations."""
from decimal import Decimal
from fractions import Fraction
from tools.cyberpilot.f64.source import decode_source, need


def ratio(value):
  return {'numerator': str(Decimal(value.numerator)), 'denominator': str(Decimal(value.denominator))}


def compute(data):
  obj = decode_source(data)
  times, values, scale = obj['times_ns'], obj['numerators'], obj['denominator']
  rates = [Fraction((b-a)*1000000000, scale*(tb-ta))
           for a, b, ta, tb in zip(values, values[1:], times, times[1:], strict=False)]
  absolute = sorted(abs(x) for x in rates)
  pairs = len(rates)
  def quantile(percent):
    location = Fraction((pairs-1)*percent, 100)
    low = location.numerator // location.denominator
    weight = location-low
    return absolute[low] if weight == 0 else absolute[low] + weight*(absolute[low+1]-absolute[low])
  mean_square = sum((x*x for x in rates), Fraction()) / pairs if pairs else None
  return {'schema': 'F64_EXACT_ADJACENT_RATE_METRICS_V1', 'sample_count': len(times), 'pair_count': pairs,
          'duration_ns': times[-1]-times[0], 'rate_unit': 'normalized_command/s',
          'mean_square_unit': 'normalized_command^2/s^2', 'weighting': 'EQUAL_PAIR', 'initial_prepend': False,
          'status': 'METRICS_AVAILABLE' if pairs else 'INSUFFICIENT_PAIRS',
          'rate_mean_square': ratio(mean_square) if mean_square is not None else None,
          'rate_rms_exact': {'sqrt_of': ratio(mean_square)} if mean_square is not None else None,
          'abs_rate_p95': ratio(quantile(95)) if pairs else None,
          'abs_rate_p99': ratio(quantile(99)) if pairs else None,
          'max_abs_rate': ratio(absolute[-1]) if pairs else None,
          'max_abs_delta': ratio(max(Fraction(abs(b-a), scale) for a, b in zip(values, values[1:], strict=False))) if pairs else None}


def classify_rms(summary, numerator, denominator):
  need(type(numerator) is int and type(denominator) is int and numerator >= 0 and denominator > 0, 'F64_VALUE_RANGE')
  if summary['rate_mean_square'] is None:
    return 'UNAVAILABLE'
  item = summary['rate_mean_square']
  difference = Fraction(int(Decimal(item['numerator'])), int(Decimal(item['denominator']))) - Fraction(numerator, denominator)**2
  return 'BELOW' if difference < 0 else 'ABOVE' if difference > 0 else 'EQUAL'


def check_f60(data):
  # Existing path is pure numeric arithmetic. No historical loader or Controller.
  from tools.cyberpilot.synthetic_command_rate_attribution_v1 import Sample, attribute_samples
  obj = decode_source(data)
  times, values, denominator = obj['times_ns'], obj['numerators'], obj['denominator']
  if any(b-a != 10000000 for a, b in zip(times, times[1:], strict=False)):
    return {'status': 'NOT_APPLICABLE_IRREGULAR_GRID'}
  numbers = [float(Fraction(value, denominator)) for value in values]
  # F60 takes binary floats. Arbitrary rational observations are not silently rounded
  # into exact equality claims. All selected public/holdout count17 fixtures are dyadic.
  if any(Fraction(number) != Fraction(value, denominator) for number, value in zip(numbers, values, strict=True)):
    return {'status': 'NOT_APPLICABLE_NON_DYADIC_VALUE'}
  rows = [Sample(i, i*10000000, v, v, 'baseline', True, False, ()) for i, v in enumerate(numbers)]
  historical = attribute_samples(rows)
  current = compute(data)
  need(historical['valid_pairs'] == current['pair_count'], 'F64_ORACLE_MISMATCH')
  expected = historical['total']['mean_square_exact']['command'] if historical['total'] is not None else None
  need(expected == current['rate_mean_square'], 'F64_ORACLE_MISMATCH')
  return {'status': 'EXACT_MSE_AND_SUPPORT_MATCH', 'f60_mean_square_exact': expected,
          'numeric_fixture_alias_only': True, 'controller_source_qualification': False}
