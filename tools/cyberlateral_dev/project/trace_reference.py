"""Independent DEV row oracle from original-helper/bit-output reference records."""
from consumer_reference import expected_simulation


def reference_rows(scenario, reference):
    result = expected_simulation(scenario, reference)
    rows = []
    for sample, output in zip(scenario.samples, result['outputs'], strict=True):
        trace, projection = output['trace'], output['projection']
        downstream = trace['downstream']
        rows.append({'invocation_index':sample.index, 'request_hex':sample.request.hex(), 'scale':sample.limits.STEER_MAX,
                     'integer_requested':trace['quantization']['integer_command'], 'previous_applied':downstream['limiter_previous'],
                     'limited_command':downstream['limited_command'], 'final_command':downstream['final_command'],
                     'normalized_expression_hex':projection['normalized_expression_hex'],
                     'torque_f32_bits':projection['torque_float32']['bits_hex'], 'torque_output_can_f32_bits':projection['torque_output_can_float32']['bits_hex'],
                     'lat_active':sample.lat_active,'steer_request':output['steer_request'],'fault_condition':downstream['fault_condition'],
                     'angle_counter':output['next_state']['angle_counter'],
                     'limiter_adjusted':downstream['limited_command'] != trace['quantization']['integer_command'],
                     'inactive_gate_changed':downstream['final_command'] != downstream['limited_command'],
                     'fault_request_suppressed':sample.lat_active and not output['steer_request'],
                     'delta_from_previous_command':downstream['final_command']-downstream['limiter_previous']})
    return rows
