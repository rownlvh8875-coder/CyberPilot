"""Bounded checksummed R31 records. Consistency only; never execute the model."""

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import asdict, fields
from pathlib import Path

from .scenario_input import (
    LimitsSpec,
    SampleSpec,
    ScenarioError,
    ScenarioSpec,
    StateSpec,
    _constant,
    _depth_bound,
    _float_token,
    _int_token,
    _pairs,
    validate_spec,
)
from .scenario_output import GATES, canonical, render_outputs

CAPS = {'INPUT.json': 1048576, 'RESULTS.json': 16777216, 'TRACE.csv': 1048576,
        'SUMMARY_KO.md': 16384, 'RECEIPT.json': 524288, 'SHA256SUMS.txt': 4096}
PORTABLE = ('INPUT.json', 'RESULTS.json', 'SUMMARY_KO.md', 'TRACE.csv')
SOURCE_KEYS = {'schema_version', 'contract_id', 'scenario_id', 'input_raw_sha256', 'input_origin'}
IMPORTED = {'files': 77, 'source_sha256': 'c2f9c240aba8d181a4a341cf5e7edce3d74210759ee2b43ed2ed7bdfadbec83a',
            'expected_wheel_sha256': '3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c',
            'scope': 'manifest consistency, not authenticity of an untrusted manifest'}


class ReportError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(ok, code='REPORT_SCHEMA'):
    if not ok:
        raise ReportError(code)


def _keys(value, names):
    _require(type(value) is dict and value.keys() == set(names))


def _same(actual, expected):
    _require(canonical(actual) == canonical(expected), 'REPORT_CONSISTENCY')


def _integer(value, low=-2048, high=2048):
    _require(type(value) is int and low <= value <= high)


def _digest(value):
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None)


def _hex(value):
    _require(type(value) is str and len(value) <= 128)
    try:
        number = float.fromhex(value)
    except (ValueError, OverflowError) as error:
        raise ReportError('REPORT_SCHEMA') from error
    _require(math.isfinite(number) and number.hex() == value)
    return number


def _files(path):
    try:
        directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            _require(set(os.listdir(directory)) == CAPS.keys(), 'REPORT_FILES')
            owned = {}
            for name, cap in CAPS.items():
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
                with os.fdopen(descriptor, 'rb') as stream:
                    _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'REPORT_INPUT_FILE')
                    raw = stream.read(cap + 1)
                    _require(len(raw) <= cap, 'REPORT_SIZE')
                    owned[name] = raw
        finally:
            os.close(directory)
    except (OSError, AttributeError) as error:
        raise ReportError('REPORT_INPUT_FILE') from error
    expected = ''.join(hashlib.sha256(owned[name]).hexdigest() + '  ' + name + '\n' for name in sorted(CAPS) if name != 'SHA256SUMS.txt')
    _require(owned['SHA256SUMS.txt'] == expected.encode(), 'REPORT_CHECKSUM')
    return owned


def _json(raw):
    try:
        _depth_bound(raw)
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant,
                           parse_float=_float_token, parse_int=_int_token)
        _require(canonical(value) == raw, 'REPORT_JSON')
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, ScenarioError) as error:
        raise ReportError('REPORT_JSON') from error


def _spec(source):
    _keys(source, SOURCE_KEYS | {'limits', 'initial_state', 'samples'})
    _keys(source['limits'], [f.name for f in fields(LimitsSpec)])
    _keys(source['initial_state'], [f.name for f in fields(StateSpec)])
    _require(type(source['samples']) is list and 1 <= len(source['samples']) <= 4096)
    samples = []
    for item in source['samples']:
        _keys(item, {'index', 'request_hex', 'driver_hex', 'angle_hex', 'lat_active'})
        samples.append(SampleSpec(item['index'], _hex(item['request_hex']), _hex(item['driver_hex']), _hex(item['angle_hex']), item['lat_active']))
    spec = ScenarioSpec(source['scenario_id'], LimitsSpec(**source['limits']), StateSpec(**source['initial_state']),
                        tuple(samples), source['input_raw_sha256'])
    try:
        validate_spec(spec)
    except ScenarioError as error:
        raise ReportError('REPORT_SCHEMA') from error
    return spec


def _identity(value):
    _keys(value, {'imported', 'model_execution', 'model_version', 'observed_dev_source_hashes'})
    _same(value['imported'], IMPORTED)
    _same(value['model_version'], '0.3.0')
    _same(value['model_execution'], 'VERIFIED_LOCAL_DEV_SOURCE_NOT_INSTALLED_WHEEL')
    inventory = value['observed_dev_source_hashes']
    _require(type(inventory) is dict and 1 <= len(inventory) <= 256)
    required = {'IMPORTED_ARTIFACT.json', 'tools/scenario.py'} | {'integration_tools/scenario_' + n + '.py' for n in ['input', 'engine', 'output', 'run']}
    _require(required <= inventory.keys())
    for name, digest in inventory.items():
        _require(re.fullmatch(r'(?:integration_tools/[A-Za-z0-9_]+\.py|tools/scenario\.py|IMPORTED_ARTIFACT\.json)', name) is not None)
        _digest(digest)  # Metadata only; never open a supplied path.


def _receipt(value, spec):
    names = {'schema_version', 'input_raw_sha256', 'input_path', 'output_path', 'source_root', 'model_origin',
             'python_executable', 'python_version', 'python_executable_sha256', 'python_prefix', 'cache_policy',
             'forbidden_modules_loaded', 'scope'}
    _keys(value, names)
    _same(value['schema_version'], 1)
    _same(value['input_raw_sha256'], spec.raw_sha256)
    _digest(value['python_executable_sha256'])
    for name in names - {'schema_version', 'forbidden_modules_loaded'}:
        _require(type(value[name]) is str and len(value[name]) <= 8192)
    modules = value['forbidden_modules_loaded']
    _require(type(modules) is list and len(modules) <= 100 and all(type(v) is str and len(v) <= 64 for v in modules))


def _state(value):
    _keys(value, {'index', 'previous_requested', 'previous_applied', 'angle_counter'})
    _integer(value['index'], 1, 4096)
    _integer(value['previous_requested'])
    _integer(value['previous_applied'])
    _integer(value['angle_counter'], 0, 90)


def _clip(value):
    _keys(value, {'x', 'lower', 'upper', 'result'})
    for scalar in value.values():
        _keys(scalar, {'kind', 'value'})
        if scalar['kind'] in ('python.int', 'numpy.int64'):
            _integer(scalar['value'], -(2 ** 63), 2 ** 63 - 1)
        else:
            _require(scalar['kind'] in ('python.float', 'numpy.float64'))
            _hex(scalar['value'])


def _output(value):
    _keys(value, {'next_state', 'projection', 'steer_request', 'trace'})
    _require(type(value['steer_request']) is bool)
    _state(value['next_state'])
    projection = value['projection']
    _keys(projection, {'integer_command', 'scale', 'normalized_expression', 'normalized_expression_hex',
                       'status', 'torque_float32', 'torque_output_can_float32'})
    _integer(projection['integer_command'])
    _integer(projection['scale'], 1, 2048)
    number = projection['normalized_expression']
    _require(type(number) is float and math.isfinite(number) and abs(number) <= 2048)
    _same(_hex(projection['normalized_expression_hex']).hex(), number.hex())
    _same(projection['status'], 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE')
    for name in ['torque_float32', 'torque_output_can_float32']:
        word = projection[name]
        _keys(word, {'bits_hex', 'value_hex'})
        _require(type(word['bits_hex']) is str and re.fullmatch(r'[0-9a-f]{8}', word['bits_hex']) is not None)
        _hex(word['value_hex'])  # Shape only, no Float32 serialization recalculation.
    _keys(value['trace'], {'quantization', 'downstream'})
    quant = value['trace']['quantization']
    _keys(quant, {'integer_command', 'rounded_integer', 'request_hex', 'scale', 'product_hex'})
    for name in ['integer_command', 'rounded_integer']:
        _integer(quant[name])
    _integer(quant['scale'], 1, 2048)
    _hex(quant['request_hex'])
    _hex(quant['product_hex'])
    down = value['trace']['downstream']
    _keys(down, {'driver_clip', 'rate_clip', 'limiter_previous', 'limited_command', 'final_command', 'fault_condition', 'steer_request', 'next_state'})
    for name in ['limiter_previous', 'limited_command', 'final_command']:
        _integer(down[name])
    for name in ['fault_condition', 'steer_request']:
        _require(type(down[name]) is bool)
    _state(down['next_state'])
    _clip(down['driver_clip'])
    _clip(down['rate_clip'])
    _same(down['next_state'], value['next_state'])
    _same(down['steer_request'], value['steer_request'])
    _same(down['final_command'], projection['integer_command'])


def read_report(path: Path) -> dict:
    owned = _files(path)
    source, record, receipt = [_json(owned[name]) for name in ['INPUT.json', 'RESULTS.json', 'RECEIPT.json']]
    spec = _spec(source)
    _keys(record, SOURCE_KEYS | {'final_state', 'gates', 'identity', 'model_steps', 'numerical_claim', 'output_scope', 'rows', 'status', 'time_semantics'})
    _identity(record['identity'])
    _receipt(receipt, spec)
    _integer(record['model_steps'], 1, 4096)
    _require(type(record['rows']) is list and len(record['rows']) == record['model_steps'] == len(spec.samples))
    rows, state = [], asdict(spec.initial_state)
    for sample, row in zip(spec.samples, record['rows'], strict=True):
        _keys(row, {'prepared', 'model_output'})
        _keys(row['prepared'], {'sample', 'state'})
        prepared = {'index': sample.index, 'request_hex': float.hex(sample.request), 'driver_hex': float.hex(sample.driver),
                    'angle_hex': float.hex(sample.angle_deg), 'lat_active': sample.lat_active,
                    'limits': list(asdict(spec.limits).values()), 'provenance': 'SYNTHETIC_ONLY'}
        _same(row['prepared'], {'sample': prepared, 'state': state})
        output = row['model_output']
        _output(output)
        quant, down = output['trace']['quantization'], output['trace']['downstream']
        _same(quant['request_hex'], prepared['request_hex'])
        _same(quant['scale'], spec.limits.STEER_MAX)
        _same(output['projection']['scale'], spec.limits.STEER_MAX)
        _same(down['limiter_previous'], state['previous_applied'])
        _same(down['driver_clip']['x'], {'kind': 'python.int', 'value': quant['integer_command']})
        _same(down['rate_clip']['x'], down['driver_clip']['result'])
        next_state = output['next_state']
        _same(next_state['index'], sample.index + 1)
        _same(next_state['previous_requested'], quant['integer_command'])
        _same(next_state['previous_applied'], output['projection']['integer_command'])
        rows.append({'index': sample.index, 'request_hex': prepared['request_hex'], 'driver_hex': prepared['driver_hex'],
                     'angle_hex': prepared['angle_hex'], 'lat_active': sample.lat_active,
                     'previous_requested': state['previous_requested'], 'previous_applied': state['previous_applied'],
                     'angle_counter_before': state['angle_counter'], 'integer_request': quant['integer_command'],
                     'limited_command': down['limited_command'], 'final_command': down['final_command'],
                     'steer_request': output['steer_request'], 'angle_counter_after': next_state['angle_counter'],
                     'fault_condition': down['fault_condition'],
                     'limiter_adjusted': down['limited_command'] != quant['integer_command'],
                     'inactive_gate_changed': down['limited_command'] != down['final_command'],
                     'fault_request_suppressed': sample.lat_active and not output['steer_request']})
        state = next_state
    _same(record['final_state'], state)
    recorded = {name: record[name] for name in ['model_steps', 'rows', 'final_state']}
    # Regenerate duplicate data projections only. This helper never calls the model.
    expected = render_outputs(spec, recorded, record['identity'], receipt)
    _require(all(owned[name] == raw for name, raw in expected.items()), 'REPORT_CONSISTENCY')
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in owned.items()}
    view = {'schema_version': 1, 'contract_id': 'F70UGZ_R32_RECORDED_SCENARIO_VIEW_V1',
            'scenario_id': spec.scenario_id, 'input_raw_sha256': spec.raw_sha256,
            'validation_claim': 'CHECKSUM_AND_CROSS_RECORD_CONSISTENCY_NOT_MODEL_OR_ORIGIN_VALIDATION',
            'producer_identity': record['identity'], 'source_portable_hashes': {name: hashes[name] for name in PORTABLE},
            'recorded_model_steps': len(rows), 'renderer_model_executions': 0,
            'initial_state': asdict(spec.initial_state), 'final_state': state, 'rows': rows, 'gates': dict(GATES),
            'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
            'summary': {'steps': len(rows), 'inactive_calls': sum(not r['lat_active'] for r in rows),
                        **{name: sum(r[name] for r in rows) for name in ['limiter_adjusted', 'inactive_gate_changed', 'fault_request_suppressed']}}}
    return {'view': view, 'source_hashes': hashes}
