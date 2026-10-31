"""Preserved portable model results + explicitly constructed test receipt, no model."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / 'fixtures/r31_report'
NAMES = ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md', 'RECEIPT.json']


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def rehash(root):
    (root / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((root / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                                               for name in sorted(NAMES)).encode())


def write_bundle(root, profile='sign'):
    root.mkdir()
    for name in NAMES[:-1]:
        (root / name).write_bytes((FIXTURES / profile / name).read_bytes())
    source = json.loads((root / 'INPUT.json').read_bytes())
    receipt = {'schema_version': 1, 'input_raw_sha256': source['input_raw_sha256'],
               'input_path': '/declared-fixture/input.json', 'output_path': '/declared-fixture/output',
               'source_root': '/declared-fixture/component', 'model_origin': '/declared-fixture/component/src/cyberlateral_dev/__init__.py',
               'python_executable': '/declared-fixture/python', 'python_version': '3.12.13',
               'python_executable_sha256': '0' * 64, 'python_prefix': '/declared-fixture/env',
               'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API', 'forbidden_modules_loaded': [],
               'scope': 'TEST_FIXTURE_DECLARATION_NOT_RUNTIME_ATTESTATION'}
    (root / 'RECEIPT.json').write_bytes(canonical(receipt))
    rehash(root)
    return root


def edit_json(root, name, change):
    value = json.loads((root / name).read_bytes())
    change(value)
    (root / name).write_bytes(canonical(value))
    rehash(root)


def layout_bundle(root, count=1, negative_zero=False):
    """Literal zero-command formatting fixture, NOT a recorded model execution."""
    from integration_tools.scenario_input import parse_scenario
    from integration_tools.scenario_output import render_outputs

    write_bundle(root)
    original = json.loads((root / 'RESULTS.json').read_bytes())
    receipt = json.loads((root / 'RECEIPT.json').read_bytes())
    zero = -0.0 if negative_zero else 0.0
    zero_hex = '-0x0.0p+0' if negative_zero else '0x0.0p+0'
    limits = json.loads((root / 'INPUT.json').read_bytes())['limits']
    raw = canonical({'schema_version': 1, 'scope': 'SYNTHETIC_ONLY', 'scenario_id': 'R32_layout_fixture',
                     'limits': limits, 'initial_state': {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0},
                     'samples': [{'index': i, 'request': zero, 'driver': zero, 'angle_deg': zero, 'lat_active': True} for i in range(count)]})
    spec = parse_scenario(raw)
    rows = []
    for i in range(count):
        row = deepcopy(original['rows'][0])
        row['prepared']['sample'].update(index=i, request_hex=zero_hex, driver_hex=zero_hex, angle_hex=zero_hex)
        row['prepared']['state'].update(index=i, previous_requested=None if i == 0 else 0)
        output = row['model_output']
        state = {'index': i + 1, 'previous_requested': 0, 'previous_applied': 0, 'angle_counter': 0}
        output['next_state'] = dict(state)
        output['projection'].update(integer_command=0, normalized_expression=0.0, normalized_expression_hex='0x0.0p+0')
        for field in ['torque_float32', 'torque_output_can_float32']:
            output['projection'][field] = {'bits_hex': '00000000', 'value_hex': '0x0.0p+0'}
        output['trace']['quantization'].update(integer_command=0, rounded_integer=0, request_hex=zero_hex, product_hex=zero_hex)
        down = output['trace']['downstream']
        down.update(limited_command=0, final_command=0, next_state=dict(state))
        down['driver_clip']['x']['value'] = 0
        down['driver_clip']['result'] = {'kind': 'numpy.int64', 'value': 0}
        down['rate_clip']['x'] = {'kind': 'numpy.int64', 'value': 0}
        down['rate_clip']['result'] = {'kind': 'numpy.int64', 'value': 0}
        rows.append(row)
    receipt['input_raw_sha256'] = spec.raw_sha256
    files = render_outputs(spec, {'model_steps': count, 'rows': rows, 'final_state': rows[-1]['model_output']['next_state']}, original['identity'], receipt)
    for name, value in files.items():
        (root / name).write_bytes(value)
    return root
