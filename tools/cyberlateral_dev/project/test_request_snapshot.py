"""Counterfactual raw request pairs must not acquire inferred history or permission."""

import importlib
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields, replace

from v1_helpers import ROOT


class RequestSnapshotTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/request_snapshot.py').is_file(), 'Missing CORE3 request snapshot boundary')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.request_snapshot')

    def context(self, m, **changes):
        values = {
            'schema_version': 1, 'scope': 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'source_profile': 'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'capture_epoch_id': 'capture-A',
            'controller_instance_id': 'controller-A', 'configuration_epoch_id': 'config-A',
            'clock_domain': 'DECLARED_LIVE_MONOTONIC_NS', 'control_mode': 'DECLARED_TORQUE_CONTROL',
            'request_stage': 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 'reset_generation': 0, 'loss_generation': 0,
        }
        return m.SyntheticRequestContextV1(**{**values, **changes})

    def pair_inputs(self, m):
        context = self.context(m)
        before = m.SyntheticRequestSnapshotV1(context, 0, 1_000_000_000, bytes.fromhex('be800000'), True, False, False)
        now = m.SyntheticRequestSnapshotV1(context, 1, 1_010_000_000, bytes.fromhex('3f000000'), True, False, False)
        return before, now

    def reject(self, m, code, before, now, constructor=False):
        call = m.PreparedSyntheticRequestPairV1 if constructor else m.prepare_request_pair
        with self.assertRaises(m.RequestSnapshotError) as raised:
            call(before, now)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(str(raised.exception), code)

    def test_literal_raw_pair_preserved_without_native_or_time_conversion(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.prepare_request_pair(before, now)
        self.assertIs(pair.previous, before)
        self.assertIs(pair.current, now)
        self.assertEqual((pair.previous.requested_binary32.hex(), pair.current.requested_binary32.hex()), ('be800000', '3f000000'))
        self.assertEqual((pair.previous.sample_time_ns, pair.current.sample_time_ns), (1_000_000_000, 1_010_000_000))
        self.assertEqual(pair.time_semantics, 'ORDER_ONLY_NO_DELTA_OR_PERIOD')
        self.assertEqual(pair.validation_claim, 'COOPERATIVE_SYNTHETIC_DECLARATION_ONLY')
        for forbidden in ('dt', 'dt_s', 'current_native', 'f61_input', 'previous_applied', 'consumed_settings'):
            self.assertFalse(hasattr(pair, forbidden))

    def test_all_constructor_inputs_required_and_no_policy_or_vehicle_arguments(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for record in (before.context, before):
            values = {field.name: getattr(record, field.name) for field in fields(record)}
            for name in values:
                missing = dict(values)
                missing.pop(name)
                with self.subTest(record=type(record).__name__, name=name), self.assertRaises(TypeError):
                    type(record)(**missing)
            for name in ('rate_budget_per_s', 'nominal_dt', 'vehicle_context', 'previous_applied', 'STEER_MAX'):
                with self.subTest(extra=name), self.assertRaises(TypeError):
                    type(record)(**values, **{name: 0})
        self.assertTrue(m.prepare_request_pair(before, now))

    def test_input_carriers_do_not_claim_validation_until_pair_boundary(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        malformed = replace(before, requested_binary32=b'bad')
        self.reject(m, 'REQUEST_WORD', malformed, now)

    def test_scope_is_exact_synthetic_and_not_a_claimed_actual_gate(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for bad in ('ACTUAL_PRODUCTION', 'SYNTHETIC_REFERENCE_ONLY', '', None, True):
            with self.subTest(scope=bad):
                self.reject(m, 'REQUEST_SCOPE', before, replace(now, context=self.context(m, scope=bad)))
        for version in (True, 1.0, 2, None):
            self.reject(m, 'REQUEST_SCOPE', before, replace(now, context=self.context(m, schema_version=version)))

    def test_old_observation_or_v4_source_profile_is_not_requalified(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for source in ('F70UGY_STEP7_PER_FILE_REFERENCES_V1', '6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90', '', None):
            self.reject(m, 'REQUEST_SOURCE_PROFILE', before, replace(now, context=self.context(m, source_profile=source)))

    def test_exact_snapshot_types_rejected_without_source_attribute_reads(self):
        m = self.module()

        class SourceLooking:
            def __getattribute__(self, _name):
                raise AssertionError('SOURCE_ATTRIBUTE_READ')

        class SnapshotChild(m.SyntheticRequestSnapshotV1):
            pass

        before, now = self.pair_inputs(m)
        child = SnapshotChild(**{field.name: getattr(before, field.name) for field in fields(before)})
        for bad in (SourceLooking(), child, None, {}, True):
            self.reject(m, 'REQUEST_SNAPSHOT_TYPE', bad, now)
            self.reject(m, 'REQUEST_SNAPSHOT_TYPE', before, bad)

    def test_exact_context_type_is_required_before_reading_properties(self):
        m = self.module()

        class ContextChild(m.SyntheticRequestContextV1):
            pass

        before, now = self.pair_inputs(m)
        child = ContextChild(**asdict(before.context))
        for bad in (None, {}, child):
            self.reject(m, 'REQUEST_CONTEXT_TYPE', before, replace(now, context=bad))

    def test_mode_stage_and_clock_are_explicit_not_inferred_from_flags(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for changes in ({'control_mode': 'CANFD'}, {'control_mode': 'TORQUE_CONTROL'},
                        {'request_stage': 'PREVIOUS_LIMITED_STATE'}, {'request_stage': 'RETURNED_ACTUATOR'},
                        {'clock_domain': 'WALL_CLOCK'}, {'clock_domain': 'LIVE_MONOTONIC_NS'}, {'clock_domain': None}):
            with self.subTest(changes=changes):
                self.reject(m, 'REQUEST_CONTEXT_MODE', before, replace(now, context=self.context(m, **changes)))

    def test_labels_are_bounded_builtin_ascii_without_whitespace(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for name in ('capture_epoch_id', 'controller_instance_id', 'configuration_epoch_id'):
            for invalid in ('', 'x' * 65, '한글', 'x\n', 'x y', 3, None):
                with self.subTest(name=name, invalid=invalid):
                    self.reject(m, 'REQUEST_CONTEXT_ID', before, replace(now, context=self.context(m, **{name: invalid})))
            context = self.context(m, **{name: 'A_0-' * 16})
            m.prepare_request_pair(replace(before, context=context), replace(now, context=context))

    def test_generations_are_builtin_uint64_not_bool_or_wrapped(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for name in ('reset_generation', 'loss_generation'):
            for invalid in (-1, 1 << 64, True, 0.0, None):
                self.reject(m, 'REQUEST_GENERATION', before, replace(now, context=self.context(m, **{name: invalid})))
            context = self.context(m, **{name: (1 << 64) - 1})
            m.prepare_request_pair(replace(before, context=context), replace(now, context=context))

    def test_context_transitions_reject_even_when_times_and_sequences_match(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for changes in ({'capture_epoch_id': 'capture-B'}, {'controller_instance_id': 'controller-B'},
                        {'configuration_epoch_id': 'config-B'}, {'reset_generation': 1}, {'loss_generation': 1},
                        {'clock_domain': 'DECLARED_REPLAY_RECORDED_CAN_NS'}):
            with self.subTest(changes=changes):
                self.reject(m, 'REQUEST_PAIR_CONTEXT', before, replace(now, context=self.context(m, **changes)))

    def test_replay_context_remains_explicit_and_accepted_as_one_domain(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        context = self.context(m, clock_domain='DECLARED_REPLAY_RECORDED_CAN_NS')
        pair = m.prepare_request_pair(replace(before, context=context), replace(now, context=context))
        self.assertEqual(pair.current.context.clock_domain, 'DECLARED_REPLAY_RECORDED_CAN_NS')
        self.assertFalse(pair.source_identity_reauthenticated)

    def test_sequence_type_range_and_adjacency_reject_with_no_seed(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for invalid in (True, 1.0, -1, 1 << 64, None):
            self.reject(m, 'REQUEST_SEQUENCE', before, replace(now, sequence=invalid))
        for sequence in (0, 2, 7):
            self.reject(m, 'REQUEST_PAIR_SEQUENCE', before, replace(now, sequence=sequence))
        self.reject(m, 'REQUEST_PAIR_SEQUENCE', replace(before, sequence=(1 << 64) - 1), replace(now, sequence=0))
        pair = m.prepare_request_pair(replace(before, sequence=(1 << 64) - 2), replace(now, sequence=(1 << 64) - 1))
        self.assertEqual(pair.current.sequence, (1 << 64) - 1)

    def test_timestamps_are_exact_signed_int64_without_float_or_bool(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for invalid in (True, 1.0, -(1 << 63) - 1, 1 << 63, None):
            self.reject(m, 'REQUEST_TIME', before, replace(now, sample_time_ns=invalid))
        pair = m.prepare_request_pair(replace(before, sample_time_ns=-(1 << 63)), replace(now, sample_time_ns=(1 << 63) - 1))
        self.assertEqual((pair.previous.sample_time_ns, pair.current.sample_time_ns), (-(1 << 63), (1 << 63) - 1))

    def test_nonpositive_time_order_rejected_without_nominal_dt(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for timestamp in (before.sample_time_ns, before.sample_time_ns - 1):
            self.reject(m, 'REQUEST_PAIR_TIME', before, replace(now, sample_time_ns=timestamp))

    def test_one_ns_ten_ms_and_seventeen_ms_are_order_only_not_v4_eligibility(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for timestamp in (1_000_000_001, 1_010_000_000, 1_017_000_000):
            pair = m.prepare_request_pair(before, replace(now, sample_time_ns=timestamp))
            self.assertEqual(pair.current.sample_time_ns, timestamp)
            self.assertFalse(pair.v4_payload_allowed)
            self.assertFalse(pair.f61_input_allowed)
            self.assertFalse(hasattr(pair, 'dt'))

    def test_binary32_raw_domain_endpoints_signed_zero_and_subnormals_preserved(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for word in ('00000000', '80000000', '00000001', '80000001', '3f800000', 'bf800000', '3dcccccd'):
            raw = bytes.fromhex(word)
            for which in ('previous', 'current'):
                a, b = (replace(before, requested_binary32=raw), now) if which == 'previous' else (before, replace(now, requested_binary32=raw))
                pair = m.prepare_request_pair(a, b)
                self.assertEqual(getattr(pair, which).requested_binary32.hex(), word)
                self.assertIs(type(getattr(pair, which).requested_binary32), bytes)

    def test_nonfinite_and_outside_range_words_rejected_not_clipped(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for word in ('7f800000', 'ff800000', '7fc00000', 'ffc00000', '3f800001', 'bf800001', '7f7fffff', 'ff7fffff'):
            with self.subTest(word=word):
                self.reject(m, 'REQUEST_WORD', before, replace(now, requested_binary32=bytes.fromhex(word)))
                self.reject(m, 'REQUEST_WORD', replace(before, requested_binary32=bytes.fromhex(word)), now)

    def test_only_four_immutable_msb_first_bytes_are_accepted(self):
        m = self.module()

        class BytesChild(bytes):
            pass

        before, now = self.pair_inputs(m)
        for invalid in (b'', b'123', b'12345', '3f000000', bytearray(b'\x3f\0\0\0'), memoryview(b'\x3f\0\0\0'), BytesChild(b'\x3f\0\0\0'), 0.5, None):
            self.reject(m, 'REQUEST_WORD', before, replace(now, requested_binary32=invalid))

    def test_flags_are_required_exact_bool_not_numeric_defaults(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        for name in ('request_active', 'request_override', 'reset_since_previous'):
            for invalid in (0, 1, None, 'false', 0.0):
                self.reject(m, 'REQUEST_FLAGS', before, replace(now, **{name: invalid}))

    def test_inactive_and_override_flags_are_preserved_not_evaluated(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.prepare_request_pair(replace(before, request_active=False, request_override=True),
                                      replace(now, request_active=False, request_override=True))
        self.assertFalse(pair.previous.request_active)
        self.assertTrue(pair.current.request_override)
        self.assertFalse(pair.actual_activation_allowed)
        self.assertFalse(hasattr(pair, 'feasible'))
        self.assertFalse(hasattr(pair, 'command'))

    def test_current_reset_rejected_even_when_generations_are_equal(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        self.reject(m, 'REQUEST_PAIR_RESET', before, replace(now, reset_since_previous=True))

    def test_reset_before_previous_does_not_describe_inside_supplied_pair(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.prepare_request_pair(replace(before, reset_since_previous=True), now)
        self.assertTrue(pair.previous.reset_since_previous)
        self.assertFalse(pair.current.reset_since_previous)

    def test_snapshots_context_and_result_are_frozen_without_mutable_aliases(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.prepare_request_pair(before, now)
        for record, name, value in ((before.context, 'capture_epoch_id', 'changed'), (before, 'request_active', False), (pair, 'current', before)):
            self.assertFalse(hasattr(record, '__dict__'))
            with self.assertRaises(FrozenInstanceError):
                setattr(record, name, value)
        self.assertEqual(before.requested_binary32.hex(), 'be800000')

    def test_direct_result_constructor_and_replace_run_the_same_guards(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.PreparedSyntheticRequestPairV1(before, now)
        self.reject(m, 'REQUEST_PAIR_SEQUENCE', before, replace(now, sequence=7), constructor=True)
        with self.assertRaises(m.RequestSnapshotError) as raised:
            replace(pair, current=replace(now, reset_since_previous=True))
        self.assertEqual(raised.exception.code, 'REQUEST_PAIR_RESET')

    def test_permission_and_claim_fields_cannot_be_supplied_or_replaced(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        pair = m.prepare_request_pair(before, now)
        for name in ('source_identity_reauthenticated', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(pair, name), False)
            with self.assertRaises(TypeError):
                m.PreparedSyntheticRequestPairV1(before, now, **{name: True})
            with self.assertRaises(ValueError):
                replace(pair, **{name: True})

    def test_rejection_order_is_previous_then_current_before_pair_relations(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        self.reject(m, 'REQUEST_WORD', replace(before, requested_binary32=b'bad'), replace(now, sequence=7))
        self.reject(m, 'REQUEST_PAIR_CONTEXT', before, replace(now, context=self.context(m, reset_generation=1), reset_since_previous=True))

    def test_repeated_calls_are_equal_without_shared_sessions_or_input_mutation(self):
        m = self.module()
        before, now = self.pair_inputs(m)
        first = m.prepare_request_pair(before, now)
        second = m.prepare_request_pair(before, now)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIs(first.previous, second.previous)
        self.assertEqual(before.sequence, 0)
        self.assertEqual(now.sequence, 1)

    def test_fresh_import_and_prepare_do_not_load_model_adapter_or_calculator(self):
        self.module()
        code = (f'import sys;sys.path[:0]={[str(ROOT), str(ROOT / "project")]!r};'
                'before=set(sys.modules);from test_request_snapshot import RequestSnapshotTests;'
                'test=RequestSnapshotTests();m=test.module();a,b=test.pair_inputs(m);m.prepare_request_pair(a,b);'
                'import json;print(json.dumps(sorted(set(sys.modules)-before)))')
        run = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        names = set(json.loads(run.stdout))
        for forbidden in ('numpy', 'cyberlateral_dev', 'capnp', 'cereal', 'openpilot', 'opendbc', 'selfdrive',
                          'synthetic_rate_constraint_feasibility_v1', 'synthetic_rate_constraint_feasibility_reconstructed_v2',
                          'integration_tools.f61_signal_adapter_v4', 'fractions'):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + '.') for name in names), forbidden)
