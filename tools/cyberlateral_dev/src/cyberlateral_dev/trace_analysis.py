"""Descriptive rows from an INTERNAL fixed-catalog result, not data authentication."""
import hashlib

from .reporting import canonical_report

COUNT_KEYS = ('steps', 'limiter_adjusted', 'inactive_calls', 'inactive_gate_changed',
              'fault_request_suppressed', 'normalized_outside_unit_interval')


def _summary(rows):
    return {'steps': len(rows), 'limiter_adjusted': sum(r['limiter_adjusted'] for r in rows),
            'inactive_calls': sum(not r['lat_active'] for r in rows),
            'inactive_gate_changed': sum(r['inactive_gate_changed'] for r in rows),
            'fault_request_suppressed': sum(r['fault_request_suppressed'] for r in rows),
            'normalized_outside_unit_interval': sum(abs(float.fromhex(r['normalized_expression_hex'])) > 1 for r in rows)}


def analyze_trace(source: dict) -> dict:
    if (type(source.get('schema_version')) is not int or source['schema_version'] != 1 or
            source.get('contract_id') != 'F70UGZ_R6_OFFLINE_SIMULATION_V1' or source.get('scope') != 'SYNTHETIC_DEVELOPMENT_ONLY' or
            source.get('scenario_count') != 7 or len(source['scenarios']) != 7):
        raise ValueError('INTERNAL_FIXED_CATALOG_SCHEMA_REQUIRED')
    scenarios: list[dict] = []
    for scenario in source['scenarios']:
        rows = []
        for sample, output in zip(scenario['samples'], scenario['result']['outputs'], strict=True):
            trace, projection = output['trace'], output['projection']
            down = trace['downstream']
            rows.append({'invocation_index': sample['index'], 'request_hex': float(sample['request']).hex(),
                         'scale': sample['limits']['STEER_MAX'], 'integer_requested': trace['quantization']['integer_command'],
                         'previous_applied': down['limiter_previous'], 'limited_command': down['limited_command'],
                         'final_command': down['final_command'], 'normalized_expression_hex': projection['normalized_expression_hex'],
                         'torque_f32_bits': projection['torque_float32']['bits_hex'],
                         'torque_output_can_f32_bits': projection['torque_output_can_float32']['bits_hex'],
                         'lat_active': sample['lat_active'], 'steer_request': output['steer_request'],
                         'fault_condition': down['fault_condition'], 'angle_counter': output['next_state']['angle_counter'],
                         'limiter_adjusted': down['limited_command'] != trace['quantization']['integer_command'],
                         'inactive_gate_changed': down['final_command'] != down['limited_command'],
                         'fault_request_suppressed': sample['lat_active'] and not output['steer_request'],
                         'delta_from_previous_command': down['final_command'] - down['limiter_previous']})
        scenarios.append({'id': scenario['id'], 'initial_state': dict(scenario['initial_state']), 'rows': rows, 'summary': _summary(rows)})
    totals = {key: sum(s['summary'][key] for s in scenarios) for key in COUNT_KEYS}
    if totals['steps'] != 112 or source.get('total_steps') != totals['steps']:
        raise ValueError('FIXED_CATALOG_STEP_COUNT_MISMATCH')
    return {'schema_version': 1, 'contract_id': 'F70UGZ_R7_OFFLINE_TRACE_ANALYSIS_V1', 'package_version': source['package_version'],
            'scope': 'SYNTHETIC_DEVELOPMENT_ONLY', 'source_report_sha256': hashlib.sha256(canonical_report(source)).hexdigest(),
            'fixture_catalog_sha256': source['fixture_catalog_sha256'], 'gates': dict(source['gates']), 'scenarios': scenarios,
            'summary': totals, 'units': {'x': 'model_invocation_index_NOT_elapsed_time', 'command': 'synthetic_model_command_units_NOT_physical_torque',
            'normalized': 'binary64_normalized_expression_NOT_F61_native_or_inverse',
            'delta_from_previous_command': 'model_command_difference_per_invocation_NOT_per_second'},
            'claim': 'descriptive trace counts only; not feasibility, rate policy, vehicle safety or performance evaluation'}
