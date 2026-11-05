"""Current saved declarations must match both computed fields, without repair."""

import importlib
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields, replace
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class SyntheticTransitionCheckTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/synthetic_transition_check.py').is_file(), 'Missing CORE6 current transition checker')
        package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.synthetic_transition_check')

    def fixture(self):
        r = importlib.import_module('integration_tools.request_snapshot')
        limiter = importlib.import_module('integration_tools.limiter_snapshot')
        inputs = importlib.import_module('integration_tools.synthetic_model_input')
        context = r.SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'capture-A', 'controller-A', 'config-A',
            'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
        a = r.SyntheticRequestSnapshotV1(context, 0, 1_000_000_000, bytes.fromhex('be800000'), True, False, False)
        b = r.SyntheticRequestSnapshotV1(context, 1, 1_010_000_000, bytes.fromhex('3f000000'), True, False, False)
        settings = limiter.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        before = limiter.SyntheticLimiterSnapshotV1(a, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', 7, -2, 3, 4, True)
        now = limiter.SyntheticLimiterSnapshotV1(b, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', -2, 2, 4, 5, True)
        extra = inputs.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', 5, -4, 1.5, 85.0)
        return before, now, extra

    def reject(self, m, code, before, now, extra):
        with self.assertRaises(m.TransitionCheckError) as raised:
            m.check_synthetic_transition(before, now, extra)
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))

    def test_literal_match_computes_current_state_without_source_approval(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(before, now, extra)
        self.assertEqual(result.status, 'MATCH')
        self.assertEqual(result.computed_next_state, package_feature().LateralState(6, 8, 2, 5))
        self.assertEqual(result.differences, ())
        self.assertEqual(result.checked_fields, ('saved_limited_state', 'saved_angle_counter'))
        self.assertEqual(result.synthetic_model_steps, 1)
        self.assertIs(result.prepared.current, now)
        for name in ('previous_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                     'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)

    def test_saved_command_difference_is_data_not_repaired_or_raised(self):
        m = self.module()
        before, now, extra = self.fixture()
        wrong = replace(now, saved_limited_state=4)
        result = m.check_synthetic_transition(before, wrong, extra)
        self.assertEqual(result.status, 'DIFFERENT')
        self.assertEqual(result.differences, (m.SyntheticTransitionDifferenceV1('saved_limited_state', 4, 2),))
        self.assertIs(result.current, wrong)
        self.assertEqual((result.current.saved_limited_state, result.computed_next_state.previous_applied), (4, 2))

    def test_counter_only_mismatch_does_not_disappear_when_command_matches(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(before, replace(now, saved_angle_counter=6), extra)
        self.assertEqual((result.status, result.differences),
                         ('DIFFERENT', (m.SyntheticTransitionDifferenceV1('saved_angle_counter', 6, 5),)))

    def test_two_mismatches_keep_fixed_field_order_and_exact_values(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(before, replace(now, saved_limited_state=4, saved_angle_counter=6), extra)
        self.assertEqual(result.differences, (m.SyntheticTransitionDifferenceV1('saved_limited_state', 4, 2),
                                              m.SyntheticTransitionDifferenceV1('saved_angle_counter', 6, 5)))
        self.assertEqual((result.status, result.synthetic_model_steps), ('DIFFERENT', 1))

    def test_inactive_gate_compares_post_gate_zero_not_internal_limiter(self):
        m = self.module()
        before, now, extra = self.fixture()
        now = replace(now, request=replace(now.request, request_active=False), inactive_gate_active=False,
                      saved_limited_state=0, saved_angle_counter=0)
        result = m.check_synthetic_transition(before, now, extra)
        self.assertEqual((result.status, result.computed_next_state.previous_applied, result.computed_next_state.angle_counter), ('MATCH', 0, 0))

    def test_threshold_and_fault_counter_wrap_have_hand_checked_outputs(self):
        m = self.module()
        before, now, extra = self.fixture()
        cases = [(84.99609375, 4, 0), (85.0, 4, 5), (-85.0, 4, 5), (85.0, 88, 89), (85.0, 89, 90), (85.0, 90, 0)]
        for angle, entry, computed in cases:
            a = replace(before, saved_angle_counter=entry)
            b = replace(now, angle_counter_at_entry=entry, saved_angle_counter=computed)
            result = m.check_synthetic_transition(a, b, replace(extra, current_angle_deg=angle))
            self.assertEqual((result.status, result.computed_next_state.angle_counter), ('MATCH', computed))

    def test_sign_conditioned_history_branches_are_not_one_symmetric_clip(self):
        m = self.module()
        before, now, extra = self.fixture()
        for entry, word, computed in [(-2, 'bf000000', -4), (2, '3f000000', 4), (2, 'bf000000', -2), (0, '3f000000', 2)]:
            a = replace(before, saved_limited_state=entry)
            b = replace(now, limited_state_at_entry=entry, saved_limited_state=computed,
                        request=replace(now.request, requested_binary32=bytes.fromhex(word)))
            result = m.check_synthetic_transition(a, b, extra)
            self.assertEqual((result.status, result.computed_next_state.previous_applied), ('MATCH', computed))

    def test_driver_limited_request_is_computed_before_history_limit(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(before, replace(now, saved_limited_state=0), replace(extra, current_driver=-32.0))
        self.assertEqual((result.status, result.computed_next_state.previous_applied), ('MATCH', 0))

    def test_explicit_zero_deltas_remain_synthetic_settings_not_rate_fallback(self):
        m = self.module()
        before, now, extra = self.fixture()
        settings = replace(now.settings, delta_up=0, delta_down=0)
        result = m.check_synthetic_transition(replace(before, settings=settings),
            replace(now, settings=settings, saved_limited_state=-2), extra)
        self.assertEqual((result.status, result.computed_next_state.previous_applied), ('MATCH', -2))
        self.assertFalse(hasattr(result, 'rate_budget_per_s'))

    def test_current_round_to_even_and_raw_extremes_have_literal_integer_requests(self):
        m = self.module()
        before, now, extra = self.fixture()
        for word, requested, saved in [('3d000000', 0, 0), ('3dc00000', 2, 2), ('bd000000', 0, 0),
                                       ('bdc00000', -2, -2), ('80000000', 0, 0), ('00000001', 0, 0)]:
            b = replace(now, request=replace(now.request, requested_binary32=bytes.fromhex(word)), saved_limited_state=saved)
            result = m.check_synthetic_transition(before, b, extra)
            self.assertEqual((result.status, result.computed_next_state.previous_requested), ('MATCH', requested))
            self.assertEqual(result.current.request.requested_binary32.hex(), word)

    def test_resumed_state_is_not_clamped_and_last_input_index_can_finish(self):
        m = self.module()
        before, now, extra = self.fixture()
        settings = replace(now.settings, request_scale=1, limiter_scale=1)
        a = replace(before, settings=settings, saved_limited_state=-2048, saved_angle_counter=90)
        b = replace(now, settings=settings, limited_state_at_entry=-2048, saved_limited_state=-2043,
                    angle_counter_at_entry=90, saved_angle_counter=0)
        result = m.check_synthetic_transition(a, b, replace(extra, model_index=4095, previous_integer_request=0))
        self.assertEqual((result.status, result.computed_next_state), ('MATCH', package_feature().LateralState(4096, 0, -2043, 0)))
        self.assertEqual(result.prepared.model_state.previous_applied, -2048)

    def test_current_match_does_not_certify_previous_declaration_or_prehistory(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(replace(before, limited_state_at_entry=2000, angle_counter_at_entry=90), now, extra)
        self.assertEqual(result.status, 'MATCH')
        self.assertFalse(result.previous_transition_checked)
        self.assertFalse(result.prehistory_checked)

    def test_input_type_and_context_failures_keep_fixed_wrapped_codes(self):
        m = self.module()
        before, now, extra = self.fixture()
        self.reject(m, 'TRANSITION_INPUT:MODEL_CONTEXT_TYPE', before, now, None)
        self.reject(m, 'TRANSITION_INPUT:MODEL_INDEX', before, now, replace(extra, model_index=0))
        self.reject(m, 'TRANSITION_INPUT:MODEL_PREVIOUS_REQUEST_MISMATCH', before, now, replace(extra, previous_integer_request=-2))

    def test_core4_links_and_core3_reset_order_are_not_bypassed(self):
        m = self.module()
        before, now, extra = self.fixture()
        self.reject(m, 'TRANSITION_INPUT:MODEL_LIMITER:LIMITER_PAIR_STATE_LINK', before, replace(now, limited_state_at_entry=0), extra)
        self.reject(m, 'TRANSITION_INPUT:MODEL_LIMITER:LIMITER_REQUEST:REQUEST_PAIR_RESET', before,
                    replace(now, request=replace(now.request, reset_since_previous=True)), extra)

    def test_single_model_active_does_not_accept_unrepresented_read_or_override(self):
        m = self.module()
        before, now, extra = self.fixture()
        self.reject(m, 'TRANSITION_INPUT:MODEL_ACTIVE_READS', before,
                    replace(now, request=replace(now.request, request_active=False)), extra)
        self.reject(m, 'TRANSITION_INPUT:MODEL_OVERRIDE', before,
                    replace(now, request=replace(now.request, request_override=True)), extra)

    def test_invalid_input_calls_no_step_but_valid_factory_direct_and_replace_each_call_one(self):
        m = self.module()
        before, now, extra = self.fixture()
        calls = 0
        code = package_feature().step.__code__

        def profile(frame, event, _arg):
            nonlocal calls
            if event == 'call' and frame.f_code is code:
                calls += 1

        old = sys.getprofile()
        try:
            sys.setprofile(profile)
            self.reject(m, 'TRANSITION_INPUT:MODEL_CONTEXT_TYPE', before, now, None)
            self.assertEqual(calls, 0)
            a = m.check_synthetic_transition(before, now, extra)
            self.assertEqual(calls, 1)
            m.SyntheticTransitionCheckV1(before, now, extra)
            self.assertEqual(calls, 2)
            b = replace(a, current=replace(now, saved_angle_counter=6))
            self.assertEqual((calls, b.status), (3, 'DIFFERENT'))
        finally:
            sys.setprofile(old)

    def test_result_type_and_foreign_inputs_reject_before_hostile_attribute_reads(self):
        m = self.module()
        before, now, extra = self.fixture()

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('SOURCE_READ')

        class Child(m.SyntheticTransitionCheckV1):
            pass

        self.reject(m, 'TRANSITION_INPUT:MODEL_LIMITER:LIMITER_SNAPSHOT_TYPE', Foreign(), now, extra)
        with self.assertRaisesRegex(m.TransitionCheckError, '^TRANSITION_TYPE$'):
            Child(before, now, extra)

    def test_missing_inputs_and_derived_claim_injection_fail_without_fallback(self):
        m = self.module()
        before, now, extra = self.fixture()
        for values in [(), (before,), (before, now)]:
            with self.assertRaises(TypeError):
                m.check_synthetic_transition(*values)
        result = m.check_synthetic_transition(before, now, extra)
        for key in ('prepared', 'computed_next_state', 'differences', 'status', 'synthetic_model_steps', 'actual_activation_allowed'):
            with self.assertRaises(TypeError):
                m.SyntheticTransitionCheckV1(before, now, extra, **{key: None})
            with self.assertRaises(ValueError):
                replace(result, **{key: None})
        with self.assertRaises(TypeError):
            m.check_synthetic_transition(before, now, extra, rate_budget_per_s=0)

    def test_model_failure_never_becomes_partial_match_or_difference(self):
        m = self.module()
        before, now, extra = self.fixture()
        model = package_feature()
        for error in (ValueError('not forwarded'), ArithmeticError('not forwarded')):
            with patch.object(model, 'step', side_effect=error):
                with self.assertRaisesRegex(m.TransitionCheckError, '^TRANSITION_MODEL_FAILURE$') as raised:
                    m.check_synthetic_transition(before, now, extra)
                self.assertIs(raised.exception.__cause__, error)
        with patch.object(model, 'step', side_effect=RuntimeError('unexpected')):
            with self.assertRaisesRegex(RuntimeError, '^unexpected$'):
                m.check_synthetic_transition(before, now, extra)

    def test_wrong_model_result_type_rejects_before_getters(self):
        m = self.module()
        before, now, extra = self.fixture()

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('RESULT_READ')

        with patch.object(package_feature(), 'step', return_value=Foreign()):
            self.reject(m, 'TRANSITION_MODEL_RESULT', before, now, extra)

    def test_malformed_next_state_rejects_without_boolean_or_float_coercion(self):
        m = self.module()
        before, now, extra = self.fixture()
        model = package_feature()
        prepared = importlib.import_module('integration_tools.synthetic_model_input').prepare_model_input(before, now, extra)
        output = model.step(prepared.model_input, prepared.model_state)
        for state in (None, {}, replace(output.next_state, index=True), replace(output.next_state, index=5),
                      replace(output.next_state, previous_requested=None), replace(output.next_state, previous_requested=2049),
                      replace(output.next_state, previous_applied=True), replace(output.next_state, previous_applied=2.0),
                      replace(output.next_state, previous_applied=-2049), replace(output.next_state, angle_counter=True),
                      replace(output.next_state, angle_counter=91)):
            with patch.object(model, 'step', return_value=replace(output, next_state=state)):
                self.reject(m, 'TRANSITION_MODEL_RESULT', before, now, extra)

    def test_computed_state_subclasses_are_not_treated_as_exact_model_result(self):
        m = self.module()
        before, now, extra = self.fixture()
        model = package_feature()
        prepared = importlib.import_module('integration_tools.synthetic_model_input').prepare_model_input(before, now, extra)
        output = model.step(prepared.model_input, prepared.model_state)

        class Child(model.LateralState):
            pass

        child = Child(6, 8, 2, 5)
        with patch.object(model, 'step', return_value=replace(output, next_state=child)):
            self.reject(m, 'TRANSITION_MODEL_RESULT', before, now, extra)

    def test_repeated_results_are_exact_and_owned_declarations_do_not_change(self):
        m = self.module()
        before, now, extra = self.fixture()
        original = asdict(before), asdict(now), asdict(extra)
        a = m.check_synthetic_transition(before, now, extra)
        b = m.check_synthetic_transition(before, now, extra)
        self.assertEqual(a, b)
        self.assertEqual((asdict(before), asdict(now), asdict(extra)), original)
        self.assertIs(a.previous, before)
        self.assertIs(a.current, now)
        for obj, field in [(a, 'status'), (a.computed_next_state, 'previous_applied')]:
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, None)

    def test_difference_records_and_claims_are_frozen_but_never_vehicle_permissions(self):
        m = self.module()
        before, now, extra = self.fixture()
        result = m.check_synthetic_transition(before, replace(now, saved_limited_state=4), extra)
        with self.assertRaises(FrozenInstanceError):
            result.differences[0].computed = 4
        self.assertEqual({f.name for f in fields(result.differences[0])}, {'field', 'declared', 'computed'})
        self.assertFalse(result.actual_activation_allowed)
        self.assertFalse(result.f61_input_allowed)

    def test_timestamp_order_is_not_period_or_rate_policy_and_does_not_change_transition(self):
        m = self.module()
        before, now, extra = self.fixture()
        for time_ns in (1_000_000_001, 1_010_000_000, (1 << 63) - 1):
            b = replace(now, request=replace(now.request, sample_time_ns=time_ns))
            result = m.check_synthetic_transition(before, b, extra)
            self.assertEqual((result.status, result.computed_next_state.previous_applied), ('MATCH', 2))
            self.assertEqual(result.current.request.sample_time_ns, time_ns)
            self.assertFalse(hasattr(result, 'dt'))

    def test_fresh_process_loads_no_original_runtime_numpy_or_f61(self):
        self.module()
        script = '''
import json, sys
from test_synthetic_transition_check import SyntheticTransitionCheckTests
t = SyntheticTransitionCheckTests()
m = t.module()
m.check_synthetic_transition(*t.fixture())
bad = [n for n in sys.modules if n == 'numpy' or n.startswith(('openpilot', 'selfdrive', 'opendbc', 'synthetic_rate_constraint_feasibility'))]
assert bad == [], bad
print(json.dumps({'forbidden_modules': bad}))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT / 'project', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'forbidden_modules': []})
