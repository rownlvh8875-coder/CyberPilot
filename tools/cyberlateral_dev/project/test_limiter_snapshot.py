"""Declared settings/state links must not become inferred requests or model approval."""

import importlib
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, fields, replace

from v1_helpers import ROOT


class LimiterSnapshotTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/limiter_snapshot.py').is_file(), 'Missing CORE4 limiter snapshot boundary')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.limiter_snapshot')

    def frames(self, m):
        r = importlib.import_module('integration_tools.request_snapshot')
        context = r.SyntheticRequestContextV1(
            1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY', 'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1',
            'capture-A', 'controller-A', 'config-A', 'DECLARED_LIVE_MONOTONIC_NS',
            'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0,
        )
        before_request = r.SyntheticRequestSnapshotV1(context, 0, 1_000_000_000, bytes.fromhex('be800000'), True, False, False)
        now_request = r.SyntheticRequestSnapshotV1(context, 1, 1_010_000_000, bytes.fromhex('3f000000'), True, False, False)
        settings = m.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        before = m.SyntheticLimiterSnapshotV1(before_request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', 7, -2, 3, 4, True)
        now = m.SyntheticLimiterSnapshotV1(now_request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', -2, 4, 4, 5, True)
        return before, now

    def reject(self, m, code, before, now, constructor=False):
        call = m.PreparedSyntheticLimiterPairV1 if constructor else m.prepare_limiter_pair
        with self.assertRaises(m.LimiterSnapshotError) as raised:
            call(before, now)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(str(raised.exception), code)

    def test_literal_requests_state_counters_and_separate_settings_are_preserved(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(before, now)
        self.assertIs(pair.previous, before)
        self.assertIs(pair.current, now)
        self.assertIs(pair.request_pair.previous, before.request)
        self.assertIs(pair.request_pair.current, now.request)
        self.assertEqual((before.request.requested_binary32.hex(), now.request.requested_binary32.hex()), ('be800000', '3f000000'))
        self.assertEqual((before.limited_state_at_entry, before.saved_limited_state, now.limited_state_at_entry, now.saved_limited_state), (7, -2, -2, 4))
        self.assertEqual((before.angle_counter_at_entry, before.saved_angle_counter, now.angle_counter_at_entry, now.saved_angle_counter), (3, 4, 4, 5))
        self.assertEqual((pair.current.settings.request_scale, pair.current.settings.limiter_scale), (16, 16))

    def test_required_carrier_fields_and_no_rate_or_model_input_defaults(self):
        m = self.module()
        before, _ = self.frames(m)
        for record in (before, before.settings):
            values = {field.name: getattr(record, field.name) for field in fields(record)}
            for name in values:
                missing = dict(values)
                missing.pop(name)
                with self.subTest(record=type(record).__name__, name=name), self.assertRaises(TypeError):
                    type(record)(**missing)
            for name in ('rate_budget_per_s', 'nominal_dt', 'vehicle_context', 'previous_requested'):
                with self.assertRaises(TypeError):
                    type(record)(**values, **{name: 0})

    def test_input_constructors_are_carriers_but_pair_boundary_validates(self):
        m = self.module()
        before, now = self.frames(m)
        invalid = replace(now, settings=None)
        self.reject(m, 'LIMITER_SETTINGS_TYPE', before, invalid)

    def test_exact_frames_reject_source_looking_objects_and_subclasses_before_reads(self):
        m = self.module()

        class SourceLooking:
            def __getattribute__(self, _name):
                raise AssertionError('SOURCE_READ')

        class FrameChild(m.SyntheticLimiterSnapshotV1):
            pass

        before, now = self.frames(m)
        child = FrameChild(**{field.name: getattr(before, field.name) for field in fields(before)})
        for bad in (SourceLooking(), child, None, {}, True):
            self.reject(m, 'LIMITER_SNAPSHOT_TYPE', bad, now)
            self.reject(m, 'LIMITER_SNAPSHOT_TYPE', before, bad)

    def test_actual_or_ambiguous_state_and_settings_declarations_rejected(self):
        m = self.module()
        before, now = self.frames(m)
        for name, wrong in [('state_stage', 'PREVIOUS_REQUEST'), ('state_stage', 'ACTUAL_APPLIED_COMMAND'),
                            ('settings_origin', 'ACTUAL_CONSUMED'), ('settings_origin', None)]:
            self.reject(m, 'LIMITER_DECLARATION', before, replace(now, **{name: wrong}))

    def test_settings_exact_type_before_any_external_property_access(self):
        m = self.module()

        class SettingsLooking:
            def __getattribute__(self, _name):
                raise AssertionError('SETTINGS_READ')

        class SettingsChild(m.SyntheticConsumedSettingsV1):
            pass

        before, now = self.frames(m)
        for bad in (SettingsLooking(), None, {}, SettingsChild(16, 16, 2, 5, 7, 1, 3)):
            self.reject(m, 'LIMITER_SETTINGS_TYPE', before, replace(now, settings=bad))

    def test_bounded_r31_settings_domains_require_exact_builtin_ints(self):
        m = self.module()

        class IntChild(int):
            pass

        before, now = self.frames(m)
        for field in fields(now.settings):
            low, high = ((1, 2048) if field.name in ('request_scale', 'limiter_scale') else
                         (0, 8) if field.name in ('driver_factor', 'driver_multiplier') else (0, 64))
            for invalid in (low - 1, high + 1, True, 1.0, None, IntChild(low)):
                with self.subTest(name=field.name, invalid=invalid):
                    self.reject(m, 'LIMITER_SETTINGS_DOMAIN', before, replace(now, settings=replace(now.settings, **{field.name: invalid})))

    def test_setting_domain_endpoints_are_not_vehicle_policy_values(self):
        m = self.module()
        before, now = self.frames(m)
        for settings in (m.SyntheticConsumedSettingsV1(1, 1, 0, 0, 0, 0, 0),
                         m.SyntheticConsumedSettingsV1(2048, 2048, 64, 64, 64, 8, 8)):
            pair = m.prepare_limiter_pair(replace(before, settings=settings), replace(now, settings=settings))
            self.assertIs(pair.current.settings, settings)
            self.assertFalse(pair.model_input_allowed)
            self.assertFalse(hasattr(pair, 'rate_budget_per_s'))

    def test_separate_request_and_limiter_scale_mismatch_never_selects_one(self):
        m = self.module()
        before, now = self.frames(m)
        for name in ('request_scale', 'limiter_scale'):
            self.reject(m, 'LIMITER_SCALE_MISMATCH', before, replace(now, settings=replace(now.settings, **{name: 17})))

    def test_each_changed_settings_parameter_rejects_even_in_same_config_epoch(self):
        m = self.module()
        before, now = self.frames(m)
        changed = [replace(now.settings, request_scale=17, limiter_scale=17)]
        changed.extend(replace(now.settings, **{name: getattr(now.settings, name) + 1})
                       for name in ('delta_up', 'delta_down', 'driver_allowance', 'driver_factor', 'driver_multiplier'))
        for settings in changed:
            with self.subTest(settings=settings):
                self.reject(m, 'LIMITER_PAIR_SETTINGS', before, replace(now, settings=settings))

    def test_state_fields_are_integer_command_units_not_normalized_request_or_bool(self):
        m = self.module()
        before, now = self.frames(m)
        for name in ('limited_state_at_entry', 'saved_limited_state'):
            for invalid in (-2049, 2049, True, 0.5, bytes.fromhex('3f000000'), None):
                self.reject(m, 'LIMITER_STATE_DOMAIN', before, replace(now, **{name: invalid}))

    def test_state_endpoints_and_resumed_sequence_zero_are_not_clamped_to_scale(self):
        m = self.module()
        before, now = self.frames(m)
        settings = replace(before.settings, request_scale=1, limiter_scale=1)
        a = replace(before, settings=settings, limited_state_at_entry=2048, saved_limited_state=-2048)
        b = replace(now, settings=settings, limited_state_at_entry=-2048, saved_limited_state=2048)
        pair = m.prepare_limiter_pair(a, b)
        self.assertEqual(pair.previous.request.sequence, 0)
        self.assertEqual(pair.previous.limited_state_at_entry, 2048)
        self.assertEqual(pair.current.saved_limited_state, 2048)
        self.assertEqual(pair.state_link_scope, 'PREVIOUS_SAVED_TO_CURRENT_ENTRY_ONLY_NOT_PREHISTORY')

    def test_previous_saved_state_not_previous_request_or_current_saved_result(self):
        m = self.module()
        before, now = self.frames(m)
        self.reject(m, 'LIMITER_PAIR_STATE_LINK', before, replace(now, limited_state_at_entry=7))
        self.reject(m, 'LIMITER_PAIR_STATE_LINK', before, replace(now, limited_state_at_entry=now.saved_limited_state))

    def test_counter_fields_are_bounded_explicit_software_state(self):
        m = self.module()
        before, now = self.frames(m)
        for name in ('angle_counter_at_entry', 'saved_angle_counter'):
            for invalid in (-1, 91, True, 0.0, None):
                self.reject(m, 'LIMITER_COUNTER_DOMAIN', before, replace(now, **{name: invalid}))
        pair = m.prepare_limiter_pair(replace(before, angle_counter_at_entry=90, saved_angle_counter=0),
                                      replace(now, angle_counter_at_entry=0, saved_angle_counter=90))
        self.assertEqual(pair.current.saved_angle_counter, 90)

    def test_counter_continuity_uses_previous_saved_counter_not_current_output(self):
        m = self.module()
        before, now = self.frames(m)
        self.reject(m, 'LIMITER_PAIR_COUNTER_LINK', before, replace(now, angle_counter_at_entry=5))

    def test_later_inactive_gate_is_required_exact_bool(self):
        m = self.module()
        before, now = self.frames(m)
        for invalid in (0, 1, 'false', None):
            self.reject(m, 'LIMITER_GATE_FLAG', before, replace(now, inactive_gate_active=invalid))

    def test_false_later_gate_requires_saved_state_zero(self):
        m = self.module()
        before, now = self.frames(m)
        self.reject(m, 'LIMITER_INACTIVE_STATE', before, replace(now, inactive_gate_active=False))
        pair = m.prepare_limiter_pair(before, replace(now, inactive_gate_active=False, saved_limited_state=0))
        self.assertFalse(pair.current.inactive_gate_active)
        self.assertEqual(pair.current.saved_limited_state, 0)

    def test_request_active_and_later_gate_active_are_not_aliased(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(before, replace(now, request=replace(now.request, request_active=False)))
        self.assertFalse(pair.current.request.request_active)
        self.assertTrue(pair.current.inactive_gate_active)
        self.assertEqual(pair.current.saved_limited_state, 4)
        pair = m.prepare_limiter_pair(before, replace(now, inactive_gate_active=False, saved_limited_state=0))
        self.assertTrue(pair.current.request.request_active)
        self.assertFalse(pair.current.inactive_gate_active)

    def test_previous_inactive_saved_zero_links_to_current_entry_zero(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(replace(before, inactive_gate_active=False, saved_limited_state=0),
                                      replace(now, limited_state_at_entry=0))
        self.assertEqual(pair.request_pair.current.requested_binary32.hex(), '3f000000')
        self.assertEqual(pair.current.limited_state_at_entry, 0)

    def test_linked_state_declarations_are_not_limiter_arithmetic_approval(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(replace(before, limited_state_at_entry=0, saved_limited_state=100),
                                      replace(now, limited_state_at_entry=100, saved_limited_state=-100))
        self.assertEqual(pair.current.saved_limited_state, -100)
        self.assertEqual(pair.validation_claim, 'DECLARED_STATE_LINKS_NOT_LIMITER_ARITHMETIC_OR_SOURCE_PROOF')
        for absent in ('arithmetic_pass', 'model_input', 'integer_request', 'previous_requested', 'dt', 'f61_input'):
            self.assertFalse(hasattr(pair, absent))

    def test_core3_request_scope_and_raw_errors_are_safely_wrapped(self):
        m = self.module()
        before, now = self.frames(m)
        self.reject(m, 'LIMITER_REQUEST:REQUEST_SCOPE', before,
                    replace(now, request=replace(now.request, context=replace(now.request.context, scope='ACTUAL_PRODUCTION'))))
        self.reject(m, 'LIMITER_REQUEST:REQUEST_WORD', before,
                    replace(now, request=replace(now.request, requested_binary32=bytes.fromhex('7f800000'))))
        self.reject(m, 'LIMITER_REQUEST:REQUEST_SNAPSHOT_TYPE', before, replace(now, request=None))

    def test_context_sequence_time_reset_transitions_keep_core3_guards(self):
        m = self.module()
        before, now = self.frames(m)
        for changes, code in [({'sequence': 7}, 'REQUEST_PAIR_SEQUENCE'),
                              ({'sample_time_ns': before.request.sample_time_ns}, 'REQUEST_PAIR_TIME'),
                              ({'reset_since_previous': True}, 'REQUEST_PAIR_RESET'),
                              ({'context': replace(now.request.context, loss_generation=1)}, 'REQUEST_PAIR_CONTEXT'),
                              ({'context': replace(now.request.context, configuration_epoch_id='other')}, 'REQUEST_PAIR_CONTEXT')]:
            self.reject(m, 'LIMITER_REQUEST:' + code, before, replace(now, request=replace(now.request, **changes)))

    def test_override_and_prior_reset_are_preserved_without_rate_or_command_choice(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(replace(before, request=replace(before.request, request_override=True, reset_since_previous=True)),
                                      replace(now, request=replace(now.request, request_override=True)))
        self.assertTrue(pair.request_pair.previous.reset_since_previous)
        self.assertTrue(pair.request_pair.current.request_override)
        self.assertFalse(pair.f61_input_allowed)

    def test_all_records_are_frozen_with_only_immutable_aliases(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(before, now)
        for record, name, value in ((before.settings, 'delta_up', 9), (before, 'saved_limited_state', 0), (pair, 'current', before)):
            self.assertFalse(hasattr(record, '__dict__'))
            with self.assertRaises(FrozenInstanceError):
                setattr(record, name, value)
        self.assertIs(pair.current.settings, now.settings)

    def test_direct_result_constructor_and_replace_cannot_bypass_state_links(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.PreparedSyntheticLimiterPairV1(before, now)
        self.reject(m, 'LIMITER_PAIR_STATE_LINK', before, replace(now, limited_state_at_entry=99), constructor=True)
        with self.assertRaises(m.LimiterSnapshotError) as raised:
            replace(pair, current=replace(now, angle_counter_at_entry=99))
        self.assertEqual(raised.exception.code, 'LIMITER_COUNTER_DOMAIN')

    def test_derived_request_pair_and_permission_fields_cannot_be_injected(self):
        m = self.module()
        before, now = self.frames(m)
        pair = m.prepare_limiter_pair(before, now)
        for name, injected in [('request_pair', pair.request_pair), ('model_input_allowed', True), ('v4_payload_allowed', True),
                               ('f61_input_allowed', True), ('actual_activation_allowed', True), ('source_identity_reauthenticated', True)]:
            with self.assertRaises(TypeError):
                m.PreparedSyntheticLimiterPairV1(before, now, **{name: injected})
            with self.assertRaises(ValueError):
                replace(pair, **{name: injected})
            if name != 'request_pair':
                self.assertIs(getattr(pair, name), False)

    def test_rejection_order_keeps_request_then_previous_frame_then_pair_links(self):
        m = self.module()
        before, now = self.frames(m)
        self.reject(m, 'LIMITER_REQUEST:REQUEST_PAIR_RESET', replace(before, settings=None),
                    replace(now, request=replace(now.request, reset_since_previous=True)))
        self.reject(m, 'LIMITER_SETTINGS_TYPE', replace(before, settings=None), replace(now, limited_state_at_entry=99))
        self.reject(m, 'LIMITER_PAIR_SETTINGS', before, replace(now, limited_state_at_entry=99, settings=replace(now.settings, delta_up=3)))

    def test_repeated_results_are_independent_and_inputs_unchanged(self):
        m = self.module()
        before, now = self.frames(m)
        first = m.prepare_limiter_pair(before, now)
        second = m.prepare_limiter_pair(before, now)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first.request_pair, second.request_pair)
        self.assertEqual(before.saved_limited_state, -2)
        self.assertEqual(now.settings.request_scale, 16)

    def test_fresh_prepare_imports_no_model_native_calculator_or_rate_tool(self):
        self.module()
        code = (f'import sys;sys.path[:0]={[str(ROOT), str(ROOT / "project")]!r};'
                'before=set(sys.modules);from test_limiter_snapshot import LimiterSnapshotTests;'
                'test=LimiterSnapshotTests();m=test.module();a,b=test.frames(m);m.prepare_limiter_pair(a,b);'
                'import json;print(json.dumps(sorted(set(sys.modules)-before)))')
        run = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        names = set(json.loads(run.stdout))
        for forbidden in ('cyberlateral_dev', 'numpy', 'capnp', 'cereal', 'openpilot', 'opendbc', 'selfdrive', 'fractions',
                          'integration_tools.f61_signal_adapter_v4', 'synthetic_rate_constraint_feasibility_v1',
                          'synthetic_rate_constraint_feasibility_reconstructed_v2'):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + '.') for name in names), forbidden)
