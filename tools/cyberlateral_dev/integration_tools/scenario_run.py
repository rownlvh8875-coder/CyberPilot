"""Inert DEV frontend; only load verified local model after complete preflight."""

import hashlib
import importlib
import platform
import sys
from pathlib import Path

from .scenario_input import ScenarioError, read_scenario

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'capnp', 'numpy', 'openpilot', 'opendbc', 'cereal'}


def source_identity(root: Path) -> dict:
    from .verify import verify_imports

    try:
        imported = verify_imports(root)
        paths = sorted((root / 'integration_tools').glob('*.py')) + [root / 'tools/scenario.py', root / 'IMPORTED_ARTIFACT.json']
        hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    except (OSError, ValueError) as error:
        raise ScenarioError('SCENARIO_SOURCE_IDENTITY') from error
    return {'model_version': '0.3.0', 'model_execution': 'VERIFIED_LOCAL_DEV_SOURCE_NOT_INSTALLED_WHEEL',
            'imported': imported, 'observed_dev_source_hashes': hashes}


def load_model(root: Path):
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise ScenarioError('SCENARIO_RUNTIME')
    identity = source_identity(root)
    source = str(root / 'src')
    if source not in sys.path:
        sys.path.insert(0, source)
    package = importlib.import_module('cyberlateral_dev')
    if (type(package.__version__) is not str or package.__version__ != '0.3.0'
            or type(package.__file__) is not str or Path(package.__file__).resolve() != root / 'src/cyberlateral_dev/__init__.py'):
        raise ScenarioError('SCENARIO_MODEL_IDENTITY')
    return package, identity


def run_scenario(input_path: Path, output_path: Path) -> dict:
    # Order matters: no input read, import or simulation for invalid output paths.
    if output_path.exists() or output_path.is_symlink():
        raise ScenarioError('SCENARIO_OUTPUT_EXISTS')
    if not output_path.parent.is_dir():
        raise ScenarioError('SCENARIO_OUTPUT_PARENT')
    spec = read_scenario(input_path)
    package, identity = load_model(ROOT)
    from .scenario_engine import evaluate_scenario
    from .scenario_output import publish, render_outputs

    result = evaluate_scenario(spec)
    if source_identity(ROOT) != identity:
        raise ScenarioError('SCENARIO_SOURCE_CHANGED')
    receipt = {
        'schema_version': 1, 'input_path': str(input_path.absolute()), 'output_path': str(output_path.absolute()),
        'input_raw_sha256': spec.raw_sha256, 'source_root': str(ROOT), 'model_origin': package.__file__,
        'python_executable': sys.executable, 'python_version': platform.python_version(),
        'python_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'python_prefix': sys.prefix, 'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API',
        'forbidden_modules_loaded': sorted({n.split('.')[0] for n in sys.modules} & FORBIDDEN),
        'scope': 'COOPERATIVE_PROCESS_FILESYSTEM_NOT_OS_ATTESTATION_OR_INPUT_ORIGIN_PROOF',
    }
    files = render_outputs(spec, result, identity, receipt)
    publish(output_path, files)
    return {'status': 'F70UGZ_R31_DECLARED_SYNTHETIC_SCENARIO_COMPLETE', 'model_steps': result['model_steps']}
