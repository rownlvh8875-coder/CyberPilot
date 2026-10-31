"""Pure recorded-data report frontend/publication; no model or native imports."""

import hashlib
import platform
import sys
from pathlib import Path

from .scenario_output import canonical
from .scenario_report_data import ReportError, read_report
from .scenario_report_html import _render_html

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'cyberlateral_dev', 'capnp', 'numpy', 'openpilot', 'opendbc', 'cereal'}


def _write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _publish(output: Path, files: dict[str, bytes]) -> None:
    try:
        output.mkdir(exist_ok=False)
        for name in ['VIEW.json', 'RECEIPT.json', 'SHA256SUMS.txt', 'index.html']:
            _write_exclusive(output / name, files[name])
    except OSError as error:
        raise ReportError('REPORT_PUBLICATION_FAILED') from error


def run_report(input_path: Path, output_path: Path) -> dict:
    if output_path.exists() or output_path.is_symlink():
        raise ReportError('REPORT_OUTPUT_EXISTS')
    if not output_path.parent.is_dir():
        raise ReportError('REPORT_OUTPUT_PARENT')
    if output_path.resolve().is_relative_to(input_path.resolve()):
        raise ReportError('REPORT_OUTPUT_LOCATION')
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise ReportError('REPORT_RUNTIME')
    data = read_report(input_path)
    html = _render_html(data['view'])
    names = ['integration_tools/' + name + '.py' for name in ['scenario_report_data', 'scenario_report_html', 'scenario_report_run',
                                                            'scenario_input', 'scenario_output']]
    names += ['tools/scenario_report.py', 'integration_tools/__init__.py']
    receipt = {'schema_version': 1, 'input_directory': str(input_path.absolute()), 'output_directory': str(output_path.absolute()),
               'source_hashes': data['source_hashes'], 'renderer_source_hashes': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names},
               'python_executable': sys.executable, 'python_version': platform.python_version(),
               'python_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
               'renderer_model_executions': 0, 'producer_model_executions': 'NOT_RUN_BY_READER',
               'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API',
               'forbidden_modules_loaded': sorted({n.split('.')[0] for n in sys.modules} & FORBIDDEN),
               'scope': 'OWNED_BYTES_AND_COOPERATIVE_PROCESS_NOT_ATOMIC_OS_OR_INPUT_ORIGIN_ATTESTATION'}
    files = {'index.html': html, 'VIEW.json': canonical(data['view']), 'RECEIPT.json': canonical(receipt)}
    files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()
    _publish(output_path, files)
    return {'status': 'F70UGZ_R32_RECORDED_SCENARIO_REPORT_COMPLETE', 'recorded_steps': data['view']['recorded_model_steps'],
            'renderer_model_executions': 0}
