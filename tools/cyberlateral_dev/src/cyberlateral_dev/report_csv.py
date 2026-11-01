"""Exact CSV projection of INTERNAL fixed-catalog analysis, no spreadsheet engine."""
import csv
import io

COLUMNS = ('scenario_id', 'invocation_index', 'request_hex', 'scale', 'integer_requested', 'previous_applied',
           'limited_command', 'final_command', 'normalized_expression_hex', 'torque_f32_bits', 'torque_output_can_f32_bits',
           'lat_active', 'steer_request', 'fault_condition', 'angle_counter', 'limiter_adjusted', 'inactive_gate_changed',
           'fault_request_suppressed', 'delta_from_previous_command')


def render_csv(analysis: dict) -> bytes:
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(COLUMNS)
    for scenario in analysis['scenarios']:
        for row in scenario['rows']:
            record = dict(row, scenario_id=scenario['id'])
            writer.writerow(str(record[key]).lower() if type(record[key]) is bool else record[key] for key in COLUMNS)
    return output.getvalue().encode('utf-8')
