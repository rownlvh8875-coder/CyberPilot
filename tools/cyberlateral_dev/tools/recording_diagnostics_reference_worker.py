"""Private typed declared-state worker;never import public model or vehicle code."""

import importlib.abc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'cyberlateral_dev', 'openpilot', 'opendbc', 'cereal', 'capnp'}


def _forbidden(name):
    return name.split('.')[0] in FORBIDDEN or name.startswith(('integration_tools.f61_', 'synthetic_rate_constraint_feasibility'))


class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if _forbidden(fullname):
            raise ImportError('REFERENCE_FORBIDDEN_IMPORT')
        return None


def main() -> int:
    try:
        if (sys.version_info[:3] != (3, 12, 13) or sys.implementation.name != 'cpython' or sys.platform != 'linux'
                or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)
                or sys.flags.optimize != 0 or any(_forbidden(n) for n in sys.modules)):
            raise ValueError('REFERENCE_RUNTIME_OR_IMPORT')
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, _Block())
        sys.path.insert(0, str(ROOT))
        from integration_tools.core_sequence_saved import _parse
        from integration_tools.scenario_output import canonical
        from integration_tools.verify import verify_imports

        raw = sys.stdin.buffer.read(1048577)
        if not 0 < len(raw) <= 1048576:
            raise ValueError('REFERENCE_INPUT_SIZE')
        payload = _parse(raw)
        verify_imports(ROOT)
        sys.path.insert(0, str(ROOT / 'project'))
        from project.recording_diagnostics_reference import reference_declared_states

        result = reference_declared_states(payload)
        import numpy as np

        result.update(python=sys.version.split()[0], numpy_version=np.__version__,
                      forbidden_modules_loaded=sorted(n for n in sys.modules if _forbidden(n)))
        if result['forbidden_modules_loaded']:
            raise ValueError('REFERENCE_FORBIDDEN_IMPORT')
        output = canonical(result)
        if len(output) > 1048576 or sys.stdout.buffer.write(output) != len(output):
            raise ValueError('REFERENCE_OUTPUT')
        return 0
    except Exception:
        sys.stderr.write('RECORDING_REFERENCE_WORKER_FAILED\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
