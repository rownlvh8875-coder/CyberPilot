"""A declared pair becomes one explicit synthetic input, never a proved next state."""

import importlib
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, fields, replace

from v1_helpers import ROOT, package_feature


class SyntheticModelInputTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/synthetic_model_input.py').is_file(), 'Missing CORE5 synthetic model input boundary')
        package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.synthetic_model_input')

    def fixture(self, m):
        r = importlib.import_module('integration_tools.request_snapshot')
        limiter = importlib.import_module('integration_tools.limiter_snapshot')
        context = r.SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'capture-A', 'controller-A', 'config-A',
            'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
        a = r.SyntheticRequestSnapshotV1(context, 0, 1_000_000_000, bytes.fromhex('be800000'), True, False, False)
        b = r.SyntheticRequestSnapshotV1(context, 1, 1_010_000_000, bytes.fromhex('3f000000'), True, False, False)
        settings = limiter.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        before = limiter.SyntheticLimiterSnapshotV1(a, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', 7, -2, 3, 4, True)
        now = limiter.SyntheticLimiterSnapshotV1(b, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', -2, 4, 4, 5, True)
        extra = m.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', 5, -4, 1.5, 85.0)
        return before, now, extra

    def reject(self, m, code, before, now, context, direct=False):
        call = m.PreparedSyntheticModelInputV1 if direct else m.prepare_model_input
        with self.assertRaises(m.ModelInputError) as raised:
            call(before, now, context)
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))

    def test_maps_literal_current_input_and_entry_state_not_saved_output(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        result = m.prepare_model_input(before, now, extra)
        p = package_feature()
        self.assertIs(type(result.model_state), p.LateralState)
        self.assertIs(type(result.model_input), p.LateralInput)
        self.assertEqual(result.model_state, p.LateralState(5, -4, -2, 4))
        self.assertEqual(result.model_input, p.LateralInput(5, 0.5, 1.5, 85.0, True, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'))
        self.assertIs(result.limiter_pair.previous, before)
        self.assertIs(result.limiter_pair.current, now)
        self.assertIs(result.context, extra)
        self.assertTrue(result.synthetic_model_input_allowed)
        for name in ('source_identity_reauthenticated', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertFalse(getattr(result, name))
        self.assertFalse(result.limiter_pair.model_input_allowed)

    def test_missing_auxiliary_fields_and_policy_defaults_are_never_inferred(self):
        m = self.module()
        _, _, extra = self.fixture(m)
        values = {f.name: getattr(extra, f.name) for f in fields(extra)}
        for key in values:
            missing = dict(values)
            missing.pop(key)
            with self.assertRaises(TypeError):
                m.SyntheticModelContextV1(**missing)
        for key in ('rate_budget_per_s', 'dt', 'T2', 'actual_scale'):
            with self.assertRaises(TypeError):
                m.SyntheticModelContextV1(**values, **{key: 0})

    def test_foreign_frames_are_rejected_by_core4_before_reads(self):
        m = self.module()
        before, now, extra = self.fixture(m)

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('SOURCE_READ')

        self.reject(m, 'MODEL_LIMITER:LIMITER_SNAPSHOT_TYPE', Foreign(), now, extra)
        self.reject(m, 'MODEL_LIMITER:LIMITER_SNAPSHOT_TYPE', before, Foreign(), extra)

    def test_exact_context_class_is_required_before_leaf_reads(self):
        m = self.module()
        before, now, extra = self.fixture(m)

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('CONTEXT_READ')

        class Child(m.SyntheticModelContextV1):
            pass

        child = Child(**{f.name: getattr(extra, f.name) for f in fields(extra)})
        for invalid in (Foreign(), child, None, {}, True):
            self.reject(m, 'MODEL_CONTEXT_TYPE', before, now, invalid)

    def test_scope_rejects_actual_or_unlabeled_context(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for scope in ('ACTUAL_VEHICLE', 'SYNTHETIC_ONLY', None, True):
            self.reject(m, 'MODEL_SCOPE', before, now, replace(extra, scope=scope))

    def test_explicit_model_index_does_not_come_from_capture_sequence(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for index in (1, 4095):
            result = m.prepare_model_input(before, now, replace(extra, model_index=index))
            self.assertEqual((result.model_state.index, result.model_input.index), (index, index))
            self.assertEqual((result.previous.request.sequence, result.current.request.sequence), (0, 1))

    def test_zero_out_of_range_or_nonbuiltin_index_is_rejected(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for index in (-1, 0, 4096, True, 5.0, None):
            self.reject(m, 'MODEL_INDEX', before, now, replace(extra, model_index=index))

    def test_previous_integer_request_requires_exact_bounded_int(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for value in (-2049, 2049, True, -4.0, None, bytes.fromhex('be800000')):
            self.reject(m, 'MODEL_PREVIOUS_REQUEST', before, now, replace(extra, previous_integer_request=value))

    def test_limited_state_cannot_substitute_for_previous_integer_request(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for wrong in (-2, 4, 7):
            self.reject(m, 'MODEL_PREVIOUS_REQUEST_MISMATCH', before, now, replace(extra, previous_integer_request=wrong))

    def test_previous_tie_quantization_uses_same_scale_and_round_to_even(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for word, integer in [('3d000000', 0), ('3dc00000', 2), ('bd000000', 0), ('bdc00000', -2)]:
            a = replace(before, request=replace(before.request, requested_binary32=bytes.fromhex(word)))
            result = m.prepare_model_input(a, now, replace(extra, previous_integer_request=integer))
            self.assertEqual(result.model_state.previous_requested, integer)
            self.reject(m, 'MODEL_PREVIOUS_REQUEST_MISMATCH', a, now, replace(extra, previous_integer_request=integer + 1))

    def test_previous_quantization_endpoint_values_use_explicit_synthetic_scale(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        settings = replace(before.settings, request_scale=2048, limiter_scale=2048)
        for word, integer in [('bf800000', -2048), ('3f800000', 2048)]:
            a = replace(before, settings=settings, request=replace(before.request, requested_binary32=bytes.fromhex(word)))
            result = m.prepare_model_input(a, replace(now, settings=settings), replace(extra, previous_integer_request=integer))
            self.assertEqual((result.model_state.previous_requested, result.model_input.limits.STEER_MAX), (integer, 2048))

    def test_current_raw_signed_zero_and_subnormals_embed_exactly(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for word, want in [('80000000', '-0x0.0p+0'), ('00000000', '0x0.0p+0'),
                           ('00000001', '0x1.0000000000000p-149'), ('80000001', '-0x1.0000000000000p-149'),
                           ('3f800000', '0x1.0000000000000p+0'), ('bf800000', '-0x1.0000000000000p+0')]:
            b = replace(now, request=replace(now.request, requested_binary32=bytes.fromhex(word)))
            result = m.prepare_model_input(before, b, extra)
            self.assertEqual(result.model_input.request.hex(), want)
            self.assertEqual(result.current.request.requested_binary32.hex(), word)

    def test_driver_requires_finite_builtin_dyadic_float(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for driver in (None, 0, True, float('nan'), float('inf'), -1024.5, 1024.5, 0.1, 1 / 512):
            self.reject(m, 'MODEL_DRIVER', before, now, replace(extra, current_driver=driver))

    def test_angle_requires_finite_builtin_dyadic_float(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for angle in (None, 85, True, float('nan'), -float('inf'), -180.5, 180.5, 0.1, 1 / 512):
            self.reject(m, 'MODEL_ANGLE', before, now, replace(extra, current_angle_deg=angle))

    def test_float_domain_endpoints_and_signed_auxiliary_zero_survive(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        cases = [(-1024.0, -180.0, '-0x1.0000000000000p+10', '-0x1.6800000000000p+7'),
                 (1024.0, 180.0, '0x1.0000000000000p+10', '0x1.6800000000000p+7'),
                 (0.00390625, -0.00390625, '0x1.0000000000000p-8', '-0x1.0000000000000p-8'),
                 (-0.0, -0.0, '-0x0.0p+0', '-0x0.0p+0')]
        for driver, angle, driver_hex, angle_hex in cases:
            result = m.prepare_model_input(before, now, replace(extra, current_driver=driver, current_angle_deg=angle))
            self.assertEqual((result.model_input.driver.hex(), result.model_input.angle_deg.hex()), (driver_hex, angle_hex))

    def test_hostile_primitive_subclasses_do_not_trigger_comparison_or_conversion(self):
        m = self.module()
        before, now, extra = self.fixture(m)

        class IntChild(int):
            def __le__(self, _other):
                raise AssertionError('COMPARE')

        class FloatChild(float):
            def as_integer_ratio(self):
                raise AssertionError('CONVERT')

        class StrChild(str):
            def __eq__(self, _other):
                raise AssertionError('COMPARE')

        for key, bad, code in [('scope', StrChild(extra.scope), 'MODEL_SCOPE'),
                               ('model_index', IntChild(5), 'MODEL_INDEX'),
                               ('previous_integer_request', IntChild(-4), 'MODEL_PREVIOUS_REQUEST'),
                               ('current_driver', FloatChild(1.5), 'MODEL_DRIVER'),
                               ('current_angle_deg', FloatChild(85), 'MODEL_ANGLE')]:
            self.reject(m, code, before, now, replace(extra, **{key: bad}))

    def test_override_is_not_silently_ignored_in_either_frame(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        self.reject(m, 'MODEL_OVERRIDE', replace(before, request=replace(before.request, request_override=True)), now, extra)
        self.reject(m, 'MODEL_OVERRIDE', before, replace(now, request=replace(now.request, request_override=True)), extra)

    def test_disagreeing_read_roles_are_rejected_without_changing_core4(self):
        m = self.module()
        limiter = importlib.import_module('integration_tools.limiter_snapshot')
        before, now, extra = self.fixture(m)
        for a, b in [(replace(before, request=replace(before.request, request_active=False)), now),
                     (before, replace(now, request=replace(now.request, request_active=False)))]:
            self.assertFalse(limiter.prepare_limiter_pair(a, b).model_input_allowed)
            self.reject(m, 'MODEL_ACTIVE_READS', a, b, extra)

    def test_inactive_current_and_previous_to_current_activity_change_are_representable(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        inactive_now = replace(now, request=replace(now.request, request_active=False), inactive_gate_active=False, saved_limited_state=0)
        result = m.prepare_model_input(before, inactive_now, extra)
        self.assertFalse(result.model_input.lat_active)
        self.assertEqual(result.model_state.previous_applied, -2)

    def test_resumed_state_is_not_clamped_or_replaced_with_canonical_initial_state(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        settings = replace(before.settings, request_scale=1, limiter_scale=1)
        a = replace(before, settings=settings, saved_limited_state=-2048, saved_angle_counter=90)
        b = replace(now, settings=settings, limited_state_at_entry=-2048, angle_counter_at_entry=90)
        result = m.prepare_model_input(a, b, replace(extra, previous_integer_request=0))
        self.assertEqual(result.model_state, package_feature().LateralState(5, 0, -2048, 90))

    def test_current_saved_values_do_not_authorize_or_override_current_model_state(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        result = m.prepare_model_input(before, replace(now, saved_limited_state=999, saved_angle_counter=88), extra)
        self.assertEqual((result.model_state.previous_applied, result.model_state.angle_counter), (-2, 4))
        self.assertEqual((result.current.saved_limited_state, result.current.saved_angle_counter), (999, 88))
        self.assertFalse(hasattr(result, 'next_state'))

    def test_pair_link_settings_and_reset_checks_are_not_bypassed(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for bad, code in [(replace(now, limited_state_at_entry=-1), 'LIMITER_PAIR_STATE_LINK'),
                          (replace(now, settings=replace(now.settings, delta_up=3)), 'LIMITER_PAIR_SETTINGS'),
                          (replace(now, request=replace(now.request, reset_since_previous=True)), 'LIMITER_REQUEST:REQUEST_PAIR_RESET')]:
            self.reject(m, 'MODEL_LIMITER:' + code, before, bad, extra)

    def test_sample_times_are_preserved_without_nominal_period_substitution(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        for ns in (1_000_000_001, 1_010_000_000, (1 << 63) - 1):
            b = replace(now, request=replace(now.request, sample_time_ns=ns))
            result = m.prepare_model_input(before, b, extra)
            self.assertEqual(result.current.request.sample_time_ns, ns)
            self.assertFalse(hasattr(result, 'dt'))
            self.assertFalse(hasattr(result.model_input, 'rate_budget_per_s'))

    def test_result_constructor_and_replace_revalidate_and_block_derived_field_injection(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        result = m.PreparedSyntheticModelInputV1(before, now, extra)
        self.reject(m, 'MODEL_PREVIOUS_REQUEST_MISMATCH', before, now, replace(extra, previous_integer_request=0), direct=True)
        with self.assertRaises(m.ModelInputError):
            replace(result, context=replace(extra, model_index=0))
        for key, bad in [('model_input', None), ('model_state', None), ('limiter_pair', None),
                         ('synthetic_model_input_allowed', False), ('actual_activation_allowed', True)]:
            with self.assertRaises(TypeError):
                m.PreparedSyntheticModelInputV1(before, now, extra, **{key: bad})
            with self.assertRaises(ValueError):
                replace(result, **{key: bad})

    def test_result_subclasses_and_inherited_constructor_do_not_claim_validation(self):
        m = self.module()
        before, now, extra = self.fixture(m)

        class Child(m.PreparedSyntheticModelInputV1):
            pass

        with self.assertRaisesRegex(m.ModelInputError, '^MODEL_INPUT_TYPE$'):
            Child(before, now, extra)

    def test_result_is_frozen_deterministic_and_preserves_owned_inputs(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        a = m.prepare_model_input(before, now, extra)
        b = m.prepare_model_input(before, now, extra)
        self.assertEqual(a, b)
        self.assertIs(a.previous, before)
        with self.assertRaises(FrozenInstanceError):
            a.model_input = None
        with self.assertRaises(FrozenInstanceError):
            a.model_state.previous_applied = 0

    def test_fixed_rejection_order_pair_then_context_then_activity_then_quantization(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        self.reject(m, 'MODEL_LIMITER:LIMITER_PAIR_STATE_LINK', before, replace(now, limited_state_at_entry=0), None)
        bad = replace(now, request=replace(now.request, request_active=False, request_override=True))
        self.reject(m, 'MODEL_INDEX', before, bad, replace(extra, model_index=0, previous_integer_request=0))
        self.reject(m, 'MODEL_OVERRIDE', before, bad, replace(extra, previous_integer_request=0))
        self.reject(m, 'MODEL_ACTIVE_READS', before, replace(bad, request=replace(bad.request, request_override=False)),
                    replace(extra, previous_integer_request=0))

    def test_model_version_is_compatibility_gate_not_assumed_by_type_mapping(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        model = package_feature()
        original = model.__version__
        try:
            for version in ('0.4.0', None, 0.3):
                model.__version__ = version
                self.reject(m, 'MODEL_VERSION', before, now, extra)
        finally:
            model.__version__ = original

    def test_prepared_input_can_be_consumed_by_real_existing_synthetic_model(self):
        m = self.module()
        before, now, extra = self.fixture(m)
        result = m.prepare_model_input(before, now, extra)
        output = package_feature().step(result.model_input, result.model_state)
        self.assertEqual(output.next_state, package_feature().LateralState(6, 8, 2, 5))
        self.assertEqual(now.saved_limited_state, 4)  # not promoted to model output
        self.assertFalse(result.actual_activation_allowed)

    def test_preparation_does_not_call_transition_oracles_or_load_original_runtime(self):
        self.module()
        script = '''
import json, sys
from test_synthetic_model_input import SyntheticModelInputTests
t = SyntheticModelInputTests()
m = t.module()
from cyberlateral_dev import api, simulation
from cyberlateral_dev._r4 import state_model, oracle
blocked = {f.__code__ for f in (api.step, simulation.simulate, state_model.step, oracle.oracle_limiter, oracle.oracle_fault)}
def profile(frame, event, arg):
    if event == 'call' and frame.f_code in blocked:
        raise AssertionError('TRANSITION_EXECUTED')
sys.setprofile(profile)
a, b, c = t.fixture(m)
m.prepare_model_input(a, b, c)
t.reject(m, 'MODEL_PREVIOUS_REQUEST_MISMATCH', a, b, __import__('dataclasses').replace(c, previous_integer_request=0))
sys.setprofile(None)
bad = [n for n in sys.modules if n == 'numpy' or n.startswith(('openpilot', 'opendbc', 'selfdrive', 'synthetic_rate_constraint_feasibility'))]
assert bad == [], bad
print(json.dumps({'transition_calls': 0, 'forbidden_modules': bad}))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT / 'project', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'transition_calls': 0, 'forbidden_modules': []})
