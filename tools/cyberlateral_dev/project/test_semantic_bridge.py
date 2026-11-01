"""R21 literal mapping and independent precision validation; never model work."""

import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from unittest.mock import patch

import test_owned_message_boundary as owned_fixtures
from v1_helpers import ROOT, package_feature


class SemanticBridgeTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/semantic_bridge.py').is_file(), 'Missing semantic bridge')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        p = package_feature()
        return (importlib.import_module('integration_tools.semantic_bridge'),
                importlib.import_module('integration_tools.semantic_types'),
                importlib.import_module('integration_tools.semantic_oracle'), p)

    def fixture(self, types, index=0):
        b = importlib.import_module('integration_tools.owned_message_boundary')
        frame = owned_fixtures.OwnedBoundaryTests().frame(b, index)
        readback = types.ScalarReadback(frame.stamp, frame.cc.payload_sha256, frame.cs.payload_sha256,
                                        'NATIVE_FLOAT32_DECLARATION', float.fromhex('0x1.333334p-2'), 1.5, -7.25, False)
        return frame, readback

    def rejected(self, m, o, frame, readback, code):
        with self.assertRaises(m.SemanticBridgeError) as error:
            m.prepare_semantic_input(frame, readback)
        self.assertEqual(error.exception.code, code)
        with self.assertRaises(o.OracleRejection) as other:
            o.oracle_prepare(frame, readback)
        self.assertEqual(other.exception.code, code)

    def test_literal_complete_sample_limits_and_state_mapping(self):
        m, t, o, p = self.modules()
        f, r = self.fixture(t)
        result = m.prepare_semantic_input(f, r)
        expected = p.LateralInput(0, 0.30000001192092896, 1.5, -7.25, False, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')
        self.assertEqual(result.sample, expected)
        self.assertEqual(result.state, p.LateralState(0, None, 0, 0))
        self.assertEqual(o.oracle_prepare(f, r), (expected, p.LateralState(0, None, 0, 0)))
        self.assertEqual(result.precision_claim, 'EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT')
        self.assertEqual(result.custody_claim, 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY')

    def test_resumed_prior_candidate_is_not_inferred_from_request(self):
        m, t, o, p = self.modules()
        f, r = self.fixture(t, 1)
        f = replace(f, previous=replace(f.previous, source_previous_applied=3, previous_applied=3,
                                      source_angle_counter=1, angle_counter=1, previous_requested=5))
        self.assertEqual(m.prepare_semantic_input(f, r).state, p.LateralState(1, 5, 3, 1))
        self.assertEqual(o.oracle_prepare(f, r)[1], p.LateralState(1, 5, 3, 1))

    def test_signed_zero_in_all_three_fields_survives(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        r = replace(r, request=-0.0, driver=-0.0, angle_deg=-0.0)
        for sample in [m.prepare_semantic_input(f, r).sample, o.oracle_prepare(f, r)[0]]:
            self.assertEqual([sample.request.hex(), sample.driver.hex(), sample.angle_deg.hex()], ['-0x0.0p+0'] * 3)

    def test_binary64_only_point_three_rejects_without_rounding(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        self.rejected(m, o, f, replace(r, request=0.3), 'SEMANTIC_PRECISION')

    def test_native_point_three_driver_angle_do_not_expand_dyadic_domain(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        for field in ['driver', 'angle_deg']:
            self.rejected(m, o, f, replace(r, **{field: 0.30000001192092896}), 'SEMANTIC_DOMAIN')

    def test_bounds_and_smallest_native_subnormal_are_preserved(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        for request, expected_hex in [(-1.0, '-0x1.0000000000000p+0'), (1.0, '0x1.0000000000000p+0'),
                                      (float.fromhex('0x1p-149'), '0x1.0000000000000p-149')]:
            value = replace(r, request=request, driver=-1024.0, angle_deg=180.0)
            self.assertEqual(m.prepare_semantic_input(f, value).sample.request.hex(), expected_hex)
            self.assertEqual(o.oracle_prepare(f, value)[0].request.hex(), expected_hex)
        self.rejected(m, o, f, replace(r, request=float.fromhex('0x1p-150')), 'SEMANTIC_PRECISION')

    def test_nonfinite_wrong_scalar_type_and_domain_reject(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        for name, value in [('request', float('nan')), ('request', float('inf')), ('driver', -float('inf')),
                            ('request', 2.0), ('driver', 1025.0), ('angle_deg', 181.0), ('request', 1),
                            ('driver', True), ('angle_deg', '0'), ('lat_active', 1)]:
            self.rejected(m, o, f, replace(r, **{name: value}), 'SEMANTIC_DOMAIN')

    def test_readback_stamp_hash_and_representation_binding(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        for change in [{'cc_sha256': f.cs.payload_sha256}, {'cs_sha256': '0' * 64}, {'representation': 'BINARY64'},
                       {'stamp': replace(r.stamp, capture_id='OTHER')}, {'stamp': replace(r.stamp, invocation_index=True)}]:
            self.rejected(m, o, f, replace(r, **change), 'SEMANTIC_BINDING')

    def test_hostile_readback_and_stamp_reject_without_callbacks(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        class Hostile:
            def __getattribute__(self, name):
                raise AssertionError('No arbitrary property access')
        self.rejected(m, o, f, Hostile(), 'SEMANTIC_READBACK_TYPE')
        self.rejected(m, o, f, replace(r, stamp=Hostile()), 'SEMANTIC_READBACK_TYPE')

    def test_envelope_rejection_is_not_bypassed(self):
        m, t, _, _ = self.modules()
        f, r = self.fixture(t)
        with self.assertRaises(m.SemanticBridgeError) as error:
            m.prepare_semantic_input(replace(f, cc=f.cs), r)
        self.assertEqual(error.exception.code, 'SEMANTIC_ENVELOPE:OWNED_SCHEMA')

    def test_no_step_simulate_initial_state_or_r14_fallback(self):
        m, t, _, p = self.modules()
        f, r = self.fixture(t)
        old = importlib.import_module('integration_tools.message_boundary')
        with (patch.object(p, 'step', side_effect=AssertionError('No model work')),
              patch.object(p, 'simulate', side_effect=AssertionError('No model work')),
              patch.object(p, 'initial_state', side_effect=AssertionError('No initialization')),
              patch.object(old, 'extract_synthetic_message', side_effect=AssertionError('No R14 fallback'))):
            self.assertEqual(m.prepare_semantic_input(f, r).sample.driver, 1.5)

    def test_oracle_does_not_call_bridge_or_struct_roundtrip(self):
        m, t, o, _ = self.modules()
        f, r = self.fixture(t)
        with (patch.object(m, 'prepare_semantic_input', side_effect=AssertionError('Oracle independent')),
              patch('struct.pack', side_effect=AssertionError('No shared precision algorithm')),
              patch('struct.unpack', side_effect=AssertionError('No shared precision algorithm'))):
            self.assertEqual(o.oracle_prepare(f, r)[0].angle_deg, -7.25)
            with self.assertRaises(o.OracleRejection) as error:
                o.oracle_prepare(f, replace(r, request=0.3))
            self.assertEqual(error.exception.code, 'SEMANTIC_PRECISION')

    def test_target_version_mismatch_rejects(self):
        m, t, o, p = self.modules()
        f, r = self.fixture(t)
        with patch.object(p, '__version__', '0.4.0'):
            self.rejected(m, o, f, r, 'SEMANTIC_TARGET_VERSION')

    def test_required_frozen_readback_and_prepared_records(self):
        m, t, _, _ = self.modules()
        f, r = self.fixture(t)
        for item in [r, m.prepare_semantic_input(f, r)]:
            attrs = {field.name: getattr(item, field.name) for field in fields(item)}
            with self.assertRaises(FrozenInstanceError):
                setattr(item, next(iter(attrs)), None)
            with self.assertRaises(TypeError):
                type(item)(**attrs, extra=1)
            for name in attrs:
                reduced = dict(attrs)
                reduced.pop(name)
                with self.assertRaises(TypeError):
                    type(item)(**reduced)


if __name__ == '__main__':
    unittest.main()
