"""Private R38 worker: owned typed INPUT bytes only, no public model imports."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'cyberlateral_dev', 'capnp', 'openpilot', 'opendbc', 'cereal'}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r38-worker-cache-') as cache:
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        from integration_tools.scenario_output import canonical
        from integration_tools.scenario_report_data import CAPS, _json, _spec
        from integration_tools.verify import verify_imports

        raw = sys.stdin.buffer.read(CAPS['INPUT.json'] + 1)
        if len(raw) > CAPS['INPUT.json']:
            raise ValueError('REFERENCE_INPUT_SIZE')
        spec = _spec(_json(raw))
        verify_imports(ROOT)
        sys.path.insert(0, str(ROOT / 'project'))
        from project.scenario_reference import reference_values

        result = reference_values(spec)
        import numpy as np

        result['numpy_version'] = np.__version__
        result['forbidden_modules_loaded'] = sorted({name.split('.')[0] for name in sys.modules} & FORBIDDEN)
        if result['forbidden_modules_loaded']:
            raise ValueError('REFERENCE_FORBIDDEN_IMPORT')
        sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
