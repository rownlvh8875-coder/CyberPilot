"""Execute native test ledger in its own process and refuse skipped coverage."""

import argparse
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  if 'OPENPILOT_PREFIX' in os.environ or 'CEREAL_FAKE' in os.environ:
    raise ValueError('unisolated_test_process')
  executed = []

  class Result(unittest.TextTestResult):
    def startTest(self, test):
      executed.append(test.id())
      super().startTest(test)

  def result_factory(stream, descriptions, verbosity):
    return Result(stream, descriptions, verbosity)

  suite = unittest.defaultTestLoader.discover(str(ROOT / 'tools/cyberpilot_web_native/tests'))
  result = unittest.TextTestRunner(verbosity=2, resultclass=result_factory).run(suite)
  native = [name for name in executed if name.startswith('test_native.NativeCollectorTests.')]
  passed = result.wasSuccessful() and not result.skipped and len(native) >= 9 and 'OPENPILOT_PREFIX' not in os.environ
  module = sys.modules.get('msgq.ipc_pyx')
  cereal = sys.modules.get('openpilot.cereal.messaging')
  passed = passed and module is not None and cereal is not None
  record = {'status': 'PASS' if passed else 'FAIL', 'tests_run': result.testsRun, 'native_cases_executed': native,
            'executed_test_ids': executed, 'skipped': len(result.skipped), 'failures': len(result.failures), 'errors': len(result.errors),
            'native_extension_path': getattr(module, '__file__', None), 'cereal_path': getattr(cereal, '__file__', None),
            'namespace_environment_restored': 'OPENPILOT_PREFIX' not in os.environ,
            'scope': 'HOST_NATIVE_SYNTHETIC_STATUS_ONLY', 'actual_vehicle_inputs': 0}
  args.output.write_text(json.dumps(record, indent=2) + '\n')
  raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
  main()
