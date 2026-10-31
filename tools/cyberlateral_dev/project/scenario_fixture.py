"""Hand-authored synthetic JSON inputs for tests only; no expected model math."""

import json


def document(count=1):
    return {
        'schema_version': 1, 'scope': 'SYNTHETIC_ONLY', 'scenario_id': 'R31_test',
        'limits': {'STEER_MAX': 16, 'STEER_DELTA_UP': 2, 'STEER_DELTA_DOWN': 5,
                   'STEER_DRIVER_ALLOWANCE': 7, 'STEER_DRIVER_FACTOR': 1, 'STEER_DRIVER_MULTIPLIER': 3},
        'initial_state': {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0},
        'samples': [{'index': i, 'request': 0.25, 'driver': 0.0, 'angle_deg': 0.0, 'lat_active': True} for i in range(count)],
    }


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
