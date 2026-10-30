"""Catch unsafe source reads, fixture widening and synthetic caller state loss."""

import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class DevBridgeTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/dev_bridge.py').is_file(), 'Missing planned DEV bridge')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.dev_bridge')

    def assert_rejected(self, m, code, function, *args):
        with self.assertRaises(m.DevBridgeError) as raised:
            function(*args)
        self.assertEqual(raised.exception.code, code)

    def test_factory_ramp_preserves_source_shaped_fields_without_model_execution(self):
        m, p = self.module(), package_feature()
        with patch.object(p, 'step', side_effect=AssertionError('NO_TRANSITION')), patch.object(p, 'simulate', side_effect=AssertionError('NO_PREFIX')):
            snapshot = m.fixture_snapshot('ramp', 0, 'caller_A-1')
            session = m.begin_sequence('ramp', 'caller_A-1')
        self.assertEqual(asdict(snapshot), {
            'schema_version': 1, 'scope': 'SYNTHETIC_DEVELOPMENT_ONLY', 'value_representation': 'SYNTHETIC_PYTHON_BINARY64',
            'profile_id': 'R11_HYUNDAI_TORQUE_SYNTHETIC_V1', 'source_set_id': 'R11_C8FB9068_4134C0D1_V1',
            'fixture_id': 'ramp', 'sequence_id': 'caller_A-1', 'offset': 0, 'model_index': 0,
            'requested_torque': 1.0, 'driver_torque_native': 0.0, 'steering_angle_deg': 0.0, 'lat_active': True,
            'limits': {'STEER_MAX': 16, 'STEER_DELTA_UP': 2, 'STEER_DELTA_DOWN': 5,
                       'STEER_DRIVER_ALLOWANCE': 7, 'STEER_DRIVER_FACTOR': 1, 'STEER_DRIVER_MULTIPLIER': 3},
        })
        self.assertEqual(session.model_state, p.LateralState(0, None, 0, 0))
        self.assertEqual(session.next_offset, 0)
        self.assertFalse(hasattr(session, 'value_representation'))

    def test_registered_history_seed_is_not_reset_by_offset_zero(self):
        m, p = self.module(), package_feature()
        self.assertEqual(m.begin_sequence('history-scale', 'history').model_state, p.LateralState(1, 100, 100, 0))
        self.assertEqual(m.fixture_snapshot('history-scale', 0, 'history').model_index, 1)

    def test_records_are_immutable_slots_and_closed_to_extra_inputs(self):
        m = self.module()
        for record in [m.fixture_snapshot('ramp', 0, 'x'), m.begin_sequence('ramp', 'x')]:
            with self.subTest(record=type(record).__name__):
                self.assertFalse(hasattr(record, '__dict__'))
                with self.assertRaises(FrozenInstanceError):
                    record.sequence_id = 'changed'
                values = asdict(record)
                for forbidden in ['rate_budget_per_s', 'dt', 'current_sample_time_ns', 'CP']:
                    with self.assertRaises(TypeError):
                        type(record)(**values, **{forbidden: 1})
                for field in fields(record):
                    incomplete = dict(values)
                    incomplete.pop(field.name)
                    with self.assertRaises(TypeError):
                        type(record)(**incomplete)

    def test_sequence_labels_are_explicit_builtin_ascii_and_bounded(self):
        m = self.module()
        for label in ['a', 'A_0-' * 16]:
            self.assertEqual(m.begin_sequence('ramp', label).sequence_id, label)
        for label in ['', 'a' * 65, '한글', 'space here', 'newline\n', True, 7, None]:
            with self.subTest(label=label):
                self.assert_rejected(m, 'BRIDGE_SEQUENCE', m.begin_sequence, 'ramp', label)

    def test_factory_rejects_unknown_fixture_and_invalid_offset(self):
        m = self.module()
        for name in ['unknown', '', None, True]:
            self.assert_rejected(m, 'BRIDGE_FIXTURE', m.begin_sequence, name, 'x')
        for offset in [True, -1, 3, 4096, 0.0, None]:
            with self.subTest(offset=offset):
                self.assert_rejected(m, 'BRIDGE_ORDER', m.fixture_snapshot, 'ramp', offset, 'x')

    def test_package_or_closed_catalog_drift_is_not_auto_upgraded(self):
        m, p = self.module(), package_feature()
        catalog = package_feature('cyberlateral_dev.synthetic_catalog')
        with patch.object(p, '__version__', '0.3.1'):
            self.assert_rejected(m, 'BRIDGE_SOURCE_PROFILE', m.begin_sequence, 'ramp', 'x')
        with patch.object(catalog, 'fixed_catalog', return_value=()):
            self.assert_rejected(m, 'BRIDGE_SOURCE_PROFILE', m.fixture_snapshot, 'ramp', 0, 'x')

    def test_factory_preserves_negative_zero_bits(self):
        m = self.module()
        self.assertEqual(m.fixture_snapshot('signed-zero', 0, 'zero').requested_torque.hex(), '-0x0.0p+0')
        self.assertEqual(m.fixture_snapshot('signed-zero', 1, 'zero').requested_torque.hex(), '0x0.0p+0')


if __name__ == '__main__':
    unittest.main()
