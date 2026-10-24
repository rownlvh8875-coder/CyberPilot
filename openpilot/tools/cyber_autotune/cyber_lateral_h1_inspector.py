"""Aggregate-only manual inspector; accepts only the immutable H1 synthetic package."""

from collections import Counter
import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h

MAX_PACKAGE_BYTES = 32 * 1024 * 1024  # Transport budget for the frozen 800-row schema, not a metric gate.


def aggregate(package):
  h.verify_package(package)
  rows = package['rows']
  return p.seal(
    {
      'schema': 'CYBER_LATERAL_H1_INSPECTION_V1',
      'data_class': 'SYNTHETIC_ONLY',
      'row_count': len(rows),
      'trace_sha256': package['trace_sha256'],
      'trace_receipt_sha256': package['receipt_sha256'],
      'experiment_identity_sha256': package['binding']['experiment_sha256'],
      'config_sha256': package['configs'][0]['config_sha256'],
      'policy_sha256': package['policy_sha256'],
      'epoch_count': len({r['process_epoch'] for r in rows}),
      'event_counts': dict(Counter(r['event'] for r in rows)),
      'null_coverage': {name: sum(row['signals'][name] is None for row in rows) for name in c.PROVENANCE},
      'service_health': 'UNAVAILABLE_SYNTHETIC_DIRECT_CALL_NO_MESSAGE_BUS',
      'consumed_snapshot_set_sha256': p.sha(p.canonical([row['consumed_input_snapshot_sha256'] for row in rows])),
      'complete_row_digest_set_sha256': p.sha(p.canonical([row['row_sha256'] for row in rows])),
      'tier': c.TIER,
      'visual_readiness': 'VISUAL_FRAME_CONVERSION_PARTIAL',
      'visual_available': [
        'relative time grid',
        'native post-limit/pre-governor',
        'final command',
        'applied descriptive command',
        'pre-step feedback curvature',
        'post-step curvature/yaw/heading/pose',
        'normalized rail',
        'intervention',
      ],
      'visual_unavailable': dict(c.UNAVAILABLE),
      'visual_adapter_implemented': False,
      'server_implemented': False,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'holdout_opener_implemented': False,
      'calibration_blockers': p.BLOCKERS,
      'vehicle_states': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )


def inspect(store):
  path = h.store_path(store)
  if not path.is_file() or path.stat().st_size > MAX_PACKAGE_BYTES:
    raise ValueError('H1_SYNTHETIC_PACKAGE_SIZE_OR_FILE')
  return aggregate(json.loads(path.read_bytes()))


def main():
  import argparse

  parser = argparse.ArgumentParser(description='Read only a sealed synthetic H1 package; aggregates only.')
  parser.add_argument('--store', required=True)
  args = parser.parse_args()
  print(json.dumps(inspect(args.store), sort_keys=True, indent=2))


if __name__ == '__main__':
  main()
