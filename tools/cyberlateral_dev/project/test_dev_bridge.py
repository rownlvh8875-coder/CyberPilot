"""Catch unsafe source reads, fixture widening and synthetic caller state loss."""

import hashlib
import importlib
import json
import struct
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields, replace
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

    def transition_module(self):
        m = self.module()
        self.assertTrue(callable(getattr(m, 'advance', None)), 'Missing planned DEV advance')
        return m

    def test_literal_first_transition_and_result_immutability(self):
        m, p = self.transition_module(), package_feature()
        result = m.advance(m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a'))
        self.assertEqual(result.contract_id, 'F70UGZ_R11_DEV_BRIDGE_V1')
        self.assertEqual((result.fixture_id, result.sequence_id, result.consumed_offset), ('ramp', 'a', 0))
        self.assertEqual((result.diagnostic.projection.integer_command, result.diagnostic.projection.normalized_expression,
                          result.diagnostic.steer_request), (2, 0.125, True))
        self.assertEqual(result.next_session.model_state, p.LateralState(1, 16, 2, 0))
        self.assertEqual(result.next_session.next_offset, 1)
        self.assertFalse(hasattr(result, '__dict__'))
        with self.assertRaises(FrozenInstanceError):
            result.consumed_offset = 99

    def test_history_scale_preserves_noncanonical_seed_and_unclamped_output(self):
        m, p = self.transition_module(), package_feature()
        result = m.advance(m.fixture_snapshot('history-scale', 0, 'h'), m.begin_sequence('history-scale', 'h'))
        self.assertEqual(result.diagnostic.projection.integer_command, 95)
        self.assertEqual(result.diagnostic.projection.normalized_expression, 19.0)
        self.assertEqual(result.next_session.model_state, p.LateralState(2, 0, 95, 0))

    def test_real_looking_objects_and_subclass_records_reject_before_attributes(self):
        m = self.transition_module()

        class NativeLooking:
            def __getattribute__(self, name):
                raise AssertionError('NATIVE_PROPERTY_TOUCHED')

        class SnapshotSubclass(m.DevSourceSnapshotV1):
            pass

        snapshot, session = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for first, second in [(NativeLooking(), session), (snapshot, NativeLooking()), (None, session),
                              (SnapshotSubclass(**{f.name: getattr(snapshot, f.name) for f in fields(snapshot)}), session)]:
            self.assert_rejected(m, 'BRIDGE_RECORD_TYPE', m.advance, first, second)

    def test_rejection_order_before_any_model_computation(self):
        m, p = self.transition_module(), package_feature()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        cases = [
            ('BRIDGE_SCOPE', replace(x, scope='PRODUCTION', profile_id='bad', sequence_id='!')),
            ('BRIDGE_SCOPE', replace(x, schema_version=True)),
            ('BRIDGE_SCOPE', replace(x, value_representation='CAPNP_FLOAT32')),
            ('BRIDGE_SOURCE_PROFILE', replace(x, source_set_id='ajouatom_6ca11a4', sequence_id='!', fixture_id='?')),
            ('BRIDGE_SEQUENCE', replace(x, sequence_id='!', fixture_id='?', offset=-1)),
            ('BRIDGE_FIXTURE', replace(x, fixture_id='?', offset=-1, limits=None)),
            ('BRIDGE_ORDER', replace(x, offset=3, limits=None)),
            ('BRIDGE_DOMAIN', replace(x, limits=None, requested_torque=0.5)),
            ('BRIDGE_SNAPSHOT_MISMATCH', replace(x, requested_torque=0.5)),
        ]
        with patch.object(p, 'step', side_effect=AssertionError('NO_CURRENT')), patch.object(p, 'simulate', side_effect=AssertionError('NO_PREFIX')):
            for code, snapshot in cases:
                with self.subTest(code=code):
                    self.assert_rejected(m, code, m.advance, snapshot, s)

    def test_hostile_field_objects_never_receive_callbacks(self):
        m = self.transition_module()

        class HostileString(str):
            def __eq__(self, other):
                raise AssertionError('STRING_EQUALITY_CALLBACK')

            def __hash__(self):
                raise AssertionError('STRING_HASH_CALLBACK')

        class HostileInt(int):
            def __le__(self, other):
                raise AssertionError('INTEGER_COMPARE_CALLBACK')

        class Hostile:
            def __eq__(self, other):
                raise AssertionError('OBJECT_EQUALITY_CALLBACK')

        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for field, value, code in [
            ('scope', HostileString(x.scope), 'BRIDGE_SCOPE'),
            ('schema_version', HostileInt(1), 'BRIDGE_SCOPE'),
            ('profile_id', HostileString(x.profile_id), 'BRIDGE_SOURCE_PROFILE'),
            ('source_set_id', Hostile(), 'BRIDGE_SOURCE_PROFILE'),
            ('sequence_id', HostileString('a'), 'BRIDGE_SEQUENCE'),
            ('fixture_id', HostileString('ramp'), 'BRIDGE_FIXTURE'),
            ('offset', HostileInt(0), 'BRIDGE_ORDER'),
            ('model_index', HostileInt(0), 'BRIDGE_ORDER'),
            ('requested_torque', Hostile(), 'BRIDGE_DOMAIN'),
        ]:
            with self.subTest(field=field):
                self.assert_rejected(m, code, m.advance, replace(x, **{field: value}), s)
        self.assert_rejected(m, 'BRIDGE_SEQUENCE', m.begin_sequence, 'ramp', HostileString('a'))
        self.assert_rejected(m, 'BRIDGE_FIXTURE', m.begin_sequence, HostileString('ramp'), 'a')
        self.assert_rejected(m, 'BRIDGE_ORDER', m.fixture_snapshot, 'ramp', HostileInt(0), 'a')

    def test_session_metadata_sequence_fixture_and_order_are_not_ignored(self):
        m = self.transition_module()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for code, altered in [
            ('BRIDGE_SCOPE', replace(s, scope='PRODUCTION')), ('BRIDGE_SCOPE', replace(s, schema_version=True)),
            ('BRIDGE_SOURCE_PROFILE', replace(s, profile_id='unknown')), ('BRIDGE_SOURCE_PROFILE', replace(s, source_set_id=None)),
            ('BRIDGE_SEQUENCE', replace(s, sequence_id='b')), ('BRIDGE_FIXTURE', replace(s, fixture_id='inactive')),
            ('BRIDGE_ORDER', replace(s, next_offset=True)), ('BRIDGE_ORDER', replace(s, next_offset=1)),
            ('BRIDGE_DOMAIN', replace(s, model_state=None)),
        ]:
            with self.subTest(code=code, altered=altered):
                self.assert_rejected(m, code, m.advance, x, altered)
        for index in [True, -1, 1, 4096, 0.0]:
            self.assert_rejected(m, 'BRIDGE_ORDER', m.advance, replace(x, model_index=index), s)

    def test_domain_rejects_unsupported_numeric_inputs_without_coercion(self):
        m = self.transition_module()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for field, values in [
            ('requested_torque', [True, 1, '1.0', float('nan'), float('inf'), -1.001]),
            ('driver_torque_native', [True, 0, float('nan'), 1025.0, 0.1]),
            ('steering_angle_deg', [False, 0, float('inf'), 180.1, 0.1]),
            ('lat_active', [0, 1, 'true', None]),
        ]:
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assert_rejected(m, 'BRIDGE_DOMAIN', m.advance, replace(x, **{field: value}), s)
        numpy = importlib.import_module('numpy')
        self.assert_rejected(m, 'BRIDGE_DOMAIN', m.advance, replace(x, requested_torque=numpy.float64(1.0)), s)

    def test_limits_domain_has_no_scale_or_allowance_fallback(self):
        m = self.transition_module()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for field, values in [
            ('STEER_MAX', [None, True, 0, -1, 2049]),
            ('STEER_DELTA_UP', [True, -1, 65]), ('STEER_DELTA_DOWN', [None, -1, 65]),
            ('STEER_DRIVER_ALLOWANCE', [250, -1, 65]),
            ('STEER_DRIVER_FACTOR', [-1, 9]), ('STEER_DRIVER_MULTIPLIER', [True, -1, 9]),
        ]:
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assert_rejected(m, 'BRIDGE_DOMAIN', m.advance, replace(x, limits=replace(x.limits, **{field: value})), s)
        self.assert_rejected(m, 'BRIDGE_SNAPSHOT_MISMATCH', m.advance, replace(x, limits=replace(x.limits, STEER_MAX=409)), s)

    def test_snapshot_identity_checks_all_registered_values(self):
        m = self.transition_module()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        for changed in [replace(x, requested_torque=-1.0), replace(x, driver_torque_native=1.0),
                        replace(x, steering_angle_deg=1.0), replace(x, lat_active=False),
                        replace(x, limits=replace(x.limits, STEER_DELTA_UP=3))]:
            self.assert_rejected(m, 'BRIDGE_SNAPSHOT_MISMATCH', m.advance, changed, s)

    def test_binary64_identity_rejects_signed_zero_and_float32_substitution(self):
        m = self.transition_module()
        x = m.fixture_snapshot('signed-zero', 0, 'zero')
        self.assert_rejected(m, 'BRIDGE_SNAPSHOT_MISMATCH', m.advance, replace(x, requested_torque=0.0), m.begin_sequence('signed-zero', 'zero'))
        s = m.advance(m.fixture_snapshot('decimal-ties', 0, 'decimal'), m.begin_sequence('decimal-ties', 'decimal')).next_session
        x = m.fixture_snapshot('decimal-ties', 1, 'decimal')
        f32_value = struct.unpack('!f', struct.pack('!f', 0.3))[0]
        self.assertNotEqual(f32_value, 0.3)
        self.assert_rejected(m, 'BRIDGE_SNAPSHOT_MISMATCH', m.advance, replace(x, requested_torque=f32_value), s)

    def test_valid_but_wrong_previous_state_rejects_without_self_healing(self):
        m, p = self.transition_module(), package_feature()
        x = m.fixture_snapshot('ramp', 1, 'a')
        s = replace(m.begin_sequence('ramp', 'a'), next_offset=1, model_state=p.LateralState(1, 16, 2, 0))
        for field, value in [('previous_requested', 15), ('previous_applied', 0), ('angle_counter', 1), ('index', 2)]:
            bad = replace(s, model_state=replace(s.model_state, **{field: value}))
            with self.subTest(field=field), patch.object(p, 'step', side_effect=AssertionError('NO_NEW_TRANSITION')):
                self.assert_rejected(m, 'BRIDGE_STATE_MISMATCH', m.advance, x, bad)
            self.assertEqual(getattr(bad.model_state, field), value)

    def test_state_domain_is_validated_before_prefix_work(self):
        m, p = self.transition_module(), package_feature()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        states = [p.LateralState(True, None, 0, 0), p.LateralState(0, 0, 0, 0), p.LateralState(0, None, 1, 0),
                  p.LateralState(0, None, 0, 1), p.LateralState(1, None, 0, 0), p.LateralState(1, True, 0, 0),
                  p.LateralState(1, 0, 2049, 0), p.LateralState(1, 0, 0, 91)]
        with patch.object(p, 'simulate', side_effect=AssertionError('NO_PREFIX')):
            for state in states:
                self.assert_rejected(m, 'BRIDGE_DOMAIN', m.advance, x, replace(s, model_state=state))

    def test_retry_is_deterministic_but_duplicate_on_advanced_session_rejects(self):
        m = self.transition_module()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        before = asdict(x), asdict(s)
        first = m.advance(x, s)
        self.assertEqual(first, m.advance(x, s))
        self.assertEqual((asdict(x), asdict(s)), before)
        self.assert_rejected(m, 'BRIDGE_ORDER', m.advance, x, first.next_session)
        s = first.next_session
        for offset in [1, 2]:
            s = m.advance(m.fixture_snapshot('ramp', offset, 'a'), s).next_session
        self.assert_rejected(m, 'BRIDGE_ORDER', m.advance, m.fixture_snapshot('ramp', 2, 'a'), s)

    def test_prefix_is_trusted_and_offset_zero_never_simulates_empty_tuple(self):
        m, p = self.transition_module(), package_feature()
        with patch.object(p, 'simulate', side_effect=AssertionError('NO_EMPTY_PREFIX')):
            first = m.advance(m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a'))
        with patch.object(p, 'simulate', wraps=p.simulate) as prefix, patch.object(p, 'step', wraps=p.step) as current:
            m.advance(m.fixture_snapshot('ramp', 1, 'a'), first.next_session)
        prefix.assert_called_once_with(package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()[1].samples[:1], p.LateralState(0, None, 0, 0))
        self.assertEqual(current.call_count, 1)  # One NEW step, in addition to trusted prefix work.

    def test_unexpected_model_errors_are_chained_without_fallback(self):
        m, p = self.transition_module(), package_feature()
        x, s = m.fixture_snapshot('ramp', 0, 'a'), m.begin_sequence('ramp', 'a')
        error = ValueError('SYNTHETIC_MODEL_FAILURE')
        with patch.object(p, 'step', side_effect=error), self.assertRaises(m.DevBridgeError) as raised:
            m.advance(x, s)
        self.assertEqual(raised.exception.code, 'BRIDGE_MODEL_REJECTED')
        self.assertIs(raised.exception.__cause__, error)
        second = m.fixture_snapshot('ramp', 1, 'a')
        continued = replace(s, next_offset=1, model_state=p.LateralState(1, 16, 2, 0))
        with patch.object(p, 'simulate', side_effect=error), self.assertRaises(m.DevBridgeError) as raised:
            m.advance(second, continued)
        self.assertEqual(raised.exception.code, 'BRIDGE_MODEL_REJECTED')
        self.assertIs(raised.exception.__cause__, error)

    def test_all_interleaved_sequences_match_frozen_full_output_hashes(self):
        m, p = self.transition_module(), package_feature()
        golden = json.loads((ROOT / 'reference/synthetic_harness_expected_v1.json').read_bytes())['scenarios']
        sessions = [m.begin_sequence(row['id'], 'caller_' + row['id']) for row in golden]
        outputs = [[] for _ in golden]
        for offset in range(94):
            for i, row in enumerate(golden):
                if offset < row['steps']:
                    result = m.advance(m.fixture_snapshot(row['id'], offset, sessions[i].sequence_id), sessions[i])
                    outputs[i].append(result.diagnostic)
                    sessions[i] = result.next_session
        for row, state, diagnostics in zip(golden, sessions, outputs, strict=True):
            payload = asdict(p.SimulationResult(tuple(diagnostics), state.model_state))
            raw = (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['result_sha256'], row['id'])


if __name__ == '__main__':
    unittest.main()
