"""B01-B24: reject unsafe carriers, preserve supplied values, never certify history."""

import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields, replace
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class MessageBoundaryTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/message_boundary.py').is_file(), 'Missing planned pure message boundary')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.message_boundary')

    def frame(self, m, resumed=False):
        p = package_feature()
        state = p.LateralState(1, 16, 2, 0) if resumed else p.LateralState(0, None, 0, 0)
        return m.SyntheticBoundaryFrameV1(
            1, 'SYNTHETIC_DEVELOPMENT_ONLY', 'R13_HYUNDAI_TORQUE_ENTRY_SYNTHETIC_V1', 'R11_C8FB9068_4134C0D1_V1',
            'SYNTHETIC_PYTHON_BINARY64', 'A', state.index, 'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', 'EXPLICIT_SYNTHETIC_CALL_ENTRY',
            m.SyntheticCarControlV1(m.SyntheticActuatorsV1(1.0), True),
            m.SyntheticCarStateWrapperV1(m.SyntheticCarStateValuesV1(0.0, 0.0)), p.Limits(16, 2, 5, 7, 1, 3),
            m.SyntheticPreviousV1('ENTRY_BEFORE_CURRENT_LIMITER', 'A', 0 if resumed else None,
                                   state.previous_applied, state.angle_counter, state),
        )

    def rejected(self, m, code, frame):
        with self.assertRaises(m.MessageBoundaryError) as raised:
            m.extract_synthetic_message(frame)
        self.assertEqual(raised.exception.code, code)

    def request(self, frame, value):
        return replace(frame, cc=replace(frame.cc, actuators=replace(frame.cc.actuators, torque=value)))

    def test_literal_nested_field_mapping(self):
        m, p = self.module(), package_feature()
        frame = self.frame(m)
        prepared = m.extract_synthetic_message(frame)
        self.assertEqual(prepared.sample, p.LateralInput(0, 1.0, 0.0, 0.0, True, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'))
        self.assertEqual(prepared.state, p.LateralState(0, None, 0, 0))
        self.assertIs(prepared.state, frame.previous.model_state)
        self.assertEqual((prepared.contract_id, prepared.source_set_id, prepared.sequence_id),
                         ('F70UGZ_R13_MESSAGE_BOUNDARY_V1', 'R11_C8FB9068_4134C0D1_V1', 'A'))
        self.assertEqual((prepared.custody_claim, prepared.precision_claim, prepared.time_semantics),
                         ('SYNTHETIC_DECLARATION_ONLY', 'EXACT_SUPPLIED_BINARY64_NOT_NATIVE_ABI', 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'))

    def test_records_immutable_and_closed(self):
        m = self.module()
        x = self.frame(m)
        records = [x, x.cc, x.cc.actuators, x.cs, x.cs.out, x.previous, m.extract_synthetic_message(x)]
        before = asdict(x)
        for record in records:
            values = {f.name: getattr(record, f.name) for f in fields(record)}
            with self.subTest(record=type(record).__name__):
                self.assertFalse(hasattr(record, '__dict__'))
                with self.assertRaises(FrozenInstanceError):
                    setattr(record, next(iter(values)), None)
                with self.assertRaises(TypeError):
                    type(record)(**values, unknown_policy=1)
                for name in values:
                    missing = dict(values)
                    missing.pop(name)
                    with self.assertRaises(TypeError):
                        type(record)(**missing)
        self.assertEqual(asdict(x), before)

    def test_native_like_and_subclass_rejected_before_properties(self):
        m = self.module()
        x = self.frame(m)

        class NativeLike:
            def __getattribute__(self, name):
                raise AssertionError('NATIVE_PROPERTY_TOUCHED')

        class FrameSubclass(m.SyntheticBoundaryFrameV1):
            pass

        class ControlSubclass(m.SyntheticCarControlV1):
            pass

        subclass = FrameSubclass(**{f.name: getattr(x, f.name) for f in fields(x)})
        for invalid in [NativeLike(), subclass, replace(x, cc=NativeLike()), replace(x, cs=NativeLike()),
                        replace(x, previous=NativeLike()), replace(x, cc=ControlSubclass(x.cc.actuators, True))]:
            self.rejected(m, 'BOUNDARY_RECORD_TYPE', invalid)

    def test_missing_nested_record_no_defaults(self):
        m = self.module()
        x = self.frame(m)
        for bad in [replace(x, cc=None), replace(x, cc=replace(x.cc, actuators=None)), replace(x, cs=None),
                    replace(x, cs=replace(x.cs, out=None)), replace(x, consumed_limits=None), replace(x, previous=None),
                    replace(x, previous=replace(x.previous, model_state=None))]:
            self.rejected(m, 'BOUNDARY_RECORD_TYPE', bad)

    def test_scope_and_representation_rejected_first(self):
        m = self.module()
        x = self.frame(m)
        for name, value in [('schema_version', True), ('schema_version', 2), ('scope', 'PRODUCTION'),
                            ('value_representation', 'NATIVE_FLOAT32'), ('static_context_reference', None),
                            ('consumed_settings_origin', 'CONFIG_BACKUP')]:
            with self.subTest(field=name):
                self.rejected(m, 'BOUNDARY_SCOPE', replace(x, **{name: value}, profile_id='bad', sequence_id='!'))

    def test_source_profile_and_package_identity(self):
        m, p = self.module(), package_feature()
        x = self.frame(m)
        for name, value in [('profile_id', 'UNKNOWN'), ('source_set_id', 'OLD_AJOUATOM')]:
            self.rejected(m, 'BOUNDARY_SOURCE_PROFILE', replace(x, **{name: value}, sequence_id='!'))
        for version in ['0.3.1', True, None]:
            with patch.object(p, '__version__', version):
                self.rejected(m, 'BOUNDARY_SOURCE_PROFILE', x)

    def test_builtin_metadata_before_operations(self):
        m, p = self.module(), package_feature()
        x = self.frame(m)

        class HostileString(str):
            def __eq__(self, other):
                raise AssertionError('EQUALITY_CALLBACK')

            def __hash__(self):
                raise AssertionError('HASH_CALLBACK')

        class HostileInt(int):
            def __le__(self, other):
                raise AssertionError('INTEGER_CALLBACK')

        class Hostile:
            def __eq__(self, other):
                raise AssertionError('OBJECT_CALLBACK')

            def __float__(self):
                raise AssertionError('COERCION_CALLBACK')

        for name, value, code in [
            ('schema_version', HostileInt(1), 'BOUNDARY_SCOPE'), ('scope', HostileString(x.scope), 'BOUNDARY_SCOPE'),
            ('value_representation', HostileString(x.value_representation), 'BOUNDARY_SCOPE'),
            ('static_context_reference', Hostile(), 'BOUNDARY_SCOPE'), ('consumed_settings_origin', Hostile(), 'BOUNDARY_SCOPE'),
            ('profile_id', HostileString(x.profile_id), 'BOUNDARY_SOURCE_PROFILE'), ('source_set_id', Hostile(), 'BOUNDARY_SOURCE_PROFILE'),
            ('sequence_id', HostileString('A'), 'BOUNDARY_SEQUENCE'), ('invocation_index', HostileInt(0), 'BOUNDARY_ORDER'),
        ]:
            with self.subTest(field=name):
                self.rejected(m, code, replace(x, **{name: value}))
        self.rejected(m, 'BOUNDARY_DOMAIN', self.request(x, Hostile()))
        self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, consumed_limits=replace(x.consumed_limits, STEER_MAX=HostileInt(16))))
        self.rejected(m, 'BOUNDARY_ORDER', replace(x, previous=replace(x.previous, model_state=p.LateralState(HostileInt(0), None, 0, 0))))
        self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous, snapshot_stage=HostileString('ENTRY_BEFORE_CURRENT_LIMITER'))))

    def test_sequence_ascii_and_cross_caller(self):
        m = self.module()
        x = self.frame(m)
        for value in ['', 'a' * 65, '한글', 'A\n', True, None, 'B']:
            self.rejected(m, 'BOUNDARY_SEQUENCE', replace(x, sequence_id=value))
            self.rejected(m, 'BOUNDARY_SEQUENCE', replace(x, previous=replace(x.previous, sequence_id=value)))
        for valid in ['a', 'A_0-' * 16]:
            prepared = m.extract_synthetic_message(replace(x, sequence_id=valid, previous=replace(x.previous, sequence_id=valid)))
            self.assertEqual(prepared.sequence_id, valid)

    def test_order_is_explicit_not_elapsed_time(self):
        m, p = self.module(), package_feature()
        x = self.frame(m)
        for value in [True, -1, 4096, 0.0, None, 1]:
            self.rejected(m, 'BOUNDARY_ORDER', replace(x, invocation_index=value))
        for value in [True, -1, 4096, 4097, 0.0, None, 1]:
            self.rejected(m, 'BOUNDARY_ORDER', replace(x, previous=replace(x.previous, model_state=p.LateralState(value, None, 0, 0))))

    def test_first_and_resume_adjacency(self):
        m = self.module()
        first, resume = self.frame(m), self.frame(m, resumed=True)
        self.assertEqual(m.extract_synthetic_message(resume).state.index, 1)
        for value in [0, True, -1]:
            self.rejected(m, 'BOUNDARY_ORDER', replace(first, previous=replace(first.previous, previous_invocation_index=value)))
        for value in [None, True, -1, 1, 0.0]:
            self.rejected(m, 'BOUNDARY_ORDER', replace(resume, previous=replace(resume.previous, previous_invocation_index=value)))

    def test_all_numeric_domains_without_coercion(self):
        m = self.module()
        x = self.frame(m)
        numpy = importlib.import_module('numpy')
        for value in [True, 1, '1.0', float('nan'), float('inf'), -1.01, numpy.float64(1.0)]:
            self.rejected(m, 'BOUNDARY_DOMAIN', self.request(x, value))
        for field, bound in [('steeringTorque', 1024.0), ('steeringAngleDeg', 180.0)]:
            for value in [True, 0, '0.0', float('nan'), float('inf'), bound + 1.0, numpy.float64(0.0)]:
                self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, cs=replace(x.cs, out=replace(x.cs.out, **{field: value}))))
            valid = replace(x, cs=replace(x.cs, out=replace(x.cs.out, **{field: bound})))
            m.extract_synthetic_message(valid)
        for value in [0, 1, None, 'true', numpy.bool_(True)]:
            self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, cc=replace(x.cc, latActive=value)))
        self.assertFalse(m.extract_synthetic_message(replace(x, cc=replace(x.cc, latActive=False))).sample.lat_active)

    def test_limiter_domain_no_vehicle_fallback(self):
        m = self.module()
        x = self.frame(m)
        for name, invalid in [('STEER_MAX', [None, True, 0, 2049]), ('STEER_DELTA_UP', [True, -1, 65]),
                              ('STEER_DELTA_DOWN', [-1, 65]), ('STEER_DRIVER_ALLOWANCE', [-1, 65, 250]),
                              ('STEER_DRIVER_FACTOR', [-1, 9]), ('STEER_DRIVER_MULTIPLIER', [True, -1, 9])]:
            for value in invalid:
                with self.subTest(field=name, value=value):
                    self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, consumed_limits=replace(x.consumed_limits, **{name: value})))
        for scale in [1, 409, 2048]:
            prepared = m.extract_synthetic_message(replace(x, consumed_limits=replace(x.consumed_limits, STEER_MAX=scale)))
            self.assertEqual(prepared.sample.limits.STEER_MAX, scale)  # Supplied synthetic value, never vehicle authority.

    def test_state_field_domains(self):
        m = self.module()
        for resumed in [False, True]:
            x = self.frame(m, resumed)
            for field, values in [('previous_applied', [True, -2049, 2049]), ('angle_counter', [True, -1, 91]),
                                  ('previous_requested', [True, -2049, 2049, None] if resumed else [0, True])]:
                for value in values:
                    self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, previous=replace(x.previous,
                                  model_state=replace(x.previous.model_state, **{field: value}))))
            for field, values in [('source_previous_applied', [True, -2049, 2049]), ('source_angle_counter', [True, -1, 91])]:
                for value in values:
                    self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, previous=replace(x.previous, **{field: value})))

    def test_mismatched_source_previous_applied(self):
        m = self.module()
        x = self.frame(m, True)
        self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous,
                      model_state=replace(x.previous.model_state, previous_applied=3))))
        self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous, source_previous_applied=3)))

    def test_mismatched_source_counter_or_phase(self):
        m = self.module()
        x = self.frame(m, True)
        self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous,
                      model_state=replace(x.previous.model_state, angle_counter=1))))
        self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous, source_angle_counter=1)))
        for stage in ['AFTER_LIMITER', '', None]:
            self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=replace(x.previous, snapshot_stage=stage)))

    def test_noncanonical_first_state(self):
        m = self.module()
        x = self.frame(m)
        for applied, counter in [(1, 0), (0, 1)]:
            prior = replace(x.previous, source_previous_applied=applied, source_angle_counter=counter,
                            model_state=replace(x.previous.model_state, previous_applied=applied, angle_counter=counter))
            self.rejected(m, 'BOUNDARY_CUSTODY', replace(x, previous=prior))

    def test_prior_candidate_is_declaration_not_proven_history(self):
        m = self.module()
        x = self.frame(m, True)
        for candidate in [15, 16, -2048, 2048]:
            declared = replace(x, previous=replace(x.previous, model_state=replace(x.previous.model_state, previous_requested=candidate)))
            result = m.extract_synthetic_message(declared)
            self.assertEqual(result.state.previous_requested, candidate)
            self.assertEqual(result.custody_claim, 'SYNTHETIC_DECLARATION_ONLY')

    def test_resume_history_survives_scale_change(self):
        m, p = self.module(), package_feature()
        x = self.request(self.frame(m, True), 0.0)
        x = replace(x, consumed_limits=p.Limits(5, 5, 5, 0, 1, 1),
                    previous=replace(x.previous, source_previous_applied=100, model_state=p.LateralState(1, 100, 100, 0)))
        result = m.extract_synthetic_message(x)
        self.assertEqual(result.state, p.LateralState(1, 100, 100, 0))
        self.assertEqual(result.sample.limits.STEER_MAX, 5)
        self.assertFalse(hasattr(result, 'projection'))

    def test_signed_zero_exact_bits(self):
        m = self.module()
        x = self.request(self.frame(m), -0.0)
        x = replace(x, cs=replace(x.cs, out=replace(x.cs.out, steeringTorque=-0.0, steeringAngleDeg=-0.0)))
        result = m.extract_synthetic_message(x)
        self.assertEqual([float.hex(v) for v in [result.sample.request, result.sample.driver, result.sample.angle_deg]], ['-0x0.0p+0'] * 3)

    def test_binary64_not_implicitly_float32(self):
        m = self.module()
        x = self.frame(m)
        for value, expected in [(0.3, '0x1.3333333333333p-2'), (0.30000001192092896, '0x1.3333340000000p-2')]:
            self.assertEqual(float.hex(m.extract_synthetic_message(self.request(x, value)).sample.request), expected)

    def test_driver_angle_dyadic_subset(self):
        m = self.module()
        x = self.frame(m)
        self.assertEqual(m.extract_synthetic_message(self.request(x, 0.1)).sample.request, 0.1)
        for name in ['steeringTorque', 'steeringAngleDeg']:
            self.rejected(m, 'BOUNDARY_DOMAIN', replace(x, cs=replace(x.cs, out=replace(x.cs.out, **{name: 0.1}))))
            result = m.extract_synthetic_message(replace(x, cs=replace(x.cs, out=replace(x.cs.out, **{name: 0.5}))))
            self.assertIn(0.5, [result.sample.driver, result.sample.angle_deg])

    def test_extraction_no_model_or_native_execution(self):
        m, p = self.module(), package_feature()
        quantizer = package_feature('cyberlateral_dev._r4.request_quantizer')
        before = set(sys.modules)
        with patch.object(p, 'step', side_effect=AssertionError('NO_STEP')), patch.object(p, 'simulate', side_effect=AssertionError('NO_SIMULATE')), \
             patch.object(quantizer, 'quantize', side_effect=AssertionError('NO_QUANTIZATION')):
            prepared = m.extract_synthetic_message(self.frame(m))
        self.assertEqual(prepared.sample, p.LateralInput(0, 1.0, 0.0, 0.0, True, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'))
        forbidden = {'openpilot', 'opendbc', 'selfdrive', 'cereal', 'capnp', 'synthetic_rate_constraint_feasibility_v1'}
        self.assertEqual([n for n in set(sys.modules) - before if n.split('.')[0] in forbidden], [])

    def test_no_time_r_or_output_actuator_api(self):
        m = self.module()
        x = self.frame(m)
        values = {f.name: getattr(x, f.name) for f in fields(x)}
        for forbidden in ['r', 'rate_budget_per_s', 'dt', 'frame', 'timestamp', 'enabled']:
            with self.assertRaises(TypeError):
                type(x)(**values, **{forbidden: 1})
        with self.assertRaises(TypeError):
            m.SyntheticCarControlV1(x.cc.actuators, True, enabled=True)
        result = m.extract_synthetic_message(x)
        for forbidden in ['command', 'projection', 'CAN', 'f61_input', 'next_state']:
            self.assertFalse(hasattr(result, forbidden))

    def test_retry_and_interleaved_extraction_have_no_hidden_state(self):
        m = self.module()
        a = self.frame(m)
        b = self.request(replace(a, sequence_id='B', previous=replace(a.previous, sequence_id='B')), -1.0)
        before = asdict(a), asdict(b)
        first = m.extract_synthetic_message(a)
        second = m.extract_synthetic_message(b)
        self.assertEqual(second.sample.request, -1.0)
        self.assertEqual(m.extract_synthetic_message(a), first)
        self.assertEqual(m.extract_synthetic_message(b), second)
        self.assertEqual((asdict(a), asdict(b)), before)


if __name__ == '__main__':
    unittest.main()
