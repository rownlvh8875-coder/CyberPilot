"""R20 structural ownership, never native validity or historical custody."""

import hashlib
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, fields, replace

from v1_helpers import ROOT


class OwnedBoundaryTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/owned_message_boundary.py').is_file(), 'Missing owned boundary')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.owned_message_boundary')

    def frame(self, m, index=0):
        stamp = m.Stamp('A', index, 'capture_A_' + str(index))
        cc, cs = b'opaque cc fixture', b'opaque cs fixture'
        a, b = hashlib.sha256(cc).hexdigest(), hashlib.sha256(cs).hexdigest()
        return m.OwnedFrame(
            'SYNTHETIC_OWNED_MESSAGES_ONLY', 'R11_C8FB9068_4134C0D1_V1',
            '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788',
            'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', stamp,
            m.OwnedPayload(stamp, 17836551423953212591, cc, a),
            m.OwnedPayload(stamp, 11359479080460390460, cs, b),
            m.FieldLedger(stamp, a, b, ('CC.actuators.torque', 'CC.latActive', 'CS.out.steeringAngleDeg', 'CS.out.steeringTorque')),
            m.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
            m.PreviousSnapshot(stamp, None if index == 0 else index - 1, 0, 0, 0, 0,
                               None if index == 0 else 3, 'ENTRY_BEFORE_CURRENT_LIMITER'),
        )

    def rejected(self, m, code, frame):
        with self.assertRaises(m.OwnedBoundaryError) as error:
            m.prepare_owned_frame(frame)
        self.assertEqual(error.exception.code, code)

    def test_opaque_bytes_preserved_without_native_validity_claim(self):
        m = self.module()
        frame = self.frame(m)
        output = m.prepare_owned_frame(frame)
        self.assertIs(output.frame, frame)
        self.assertEqual(output.frame.cc.payload, b'opaque cc fixture')
        self.assertEqual(output.custody_claim, 'STRUCTURAL_SYNTHETIC_DECLARATION_ONLY')
        self.assertEqual(output.precision_claim, 'OPAQUE_OWNED_WIRE_BYTES_NO_DECODE')
        self.assertEqual(output.time_semantics, 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
        self.assertNotIn('capnp', sys.modules)

    def test_records_required_frozen_and_closed(self):
        m = self.module()
        f = self.frame(m)
        for item in [f, f.stamp, f.cc, f.ledger, f.settings, f.previous, m.prepare_owned_frame(f)]:
            attrs = {field.name: getattr(item, field.name) for field in fields(item)}
            with self.subTest(record=type(item).__name__):
                self.assertFalse(hasattr(item, '__dict__'))
                with self.assertRaises(FrozenInstanceError):
                    setattr(item, next(iter(attrs)), None)
                with self.assertRaises(TypeError):
                    type(item)(**attrs, extra=1)
                for name in attrs:
                    missing = dict(attrs)
                    missing.pop(name)
                    with self.assertRaises(TypeError):
                        type(item)(**missing)

    def test_hostile_root_and_wrong_nested_record_reject_before_access(self):
        m = self.module()
        class Hostile:
            def __getattribute__(self, name):
                raise AssertionError('No property access allowed')
        self.rejected(m, 'OWNED_RECORD_TYPE', Hostile())
        self.rejected(m, 'OWNED_RECORD_TYPE', replace(self.frame(m), cc=Hostile()))
        self.rejected(m, 'OWNED_RECORD_TYPE', replace(self.frame(m), stamp=None))

    def test_record_subclass_rejected(self):
        m = self.module()
        class Child(m.Stamp):
            pass
        self.rejected(m, 'OWNED_RECORD_TYPE', replace(self.frame(m), stamp=Child('A', 0, 'capture')))

    def test_scope_source_and_static_context_reject(self):
        m = self.module()
        f = self.frame(m)
        for name in ['scope', 'source_set_id', 'schema_sha256', 'static_context_reference']:
            self.rejected(m, 'OWNED_SCOPE', replace(f, **{name: 'ACTUAL_VEHICLE'}))

    def test_stamp_domains_and_cross_frame_binding(self):
        m = self.module()
        f = self.frame(m)
        for stamp in [m.Stamp('bad space', 0, 'x'), m.Stamp('A', True, 'x'), m.Stamp('A', 4096, 'x'), m.Stamp('A', 0, '')]:
            self.rejected(m, 'OWNED_STAMP', replace(f, stamp=stamp))
        crossed = m.Stamp('B', 0, 'other_capture')
        for name in ['cc', 'cs', 'ledger', 'settings', 'previous']:
            self.rejected(m, 'OWNED_STAMP', replace(f, **{name: replace(getattr(f, name), stamp=crossed)}))

    def test_wrong_schema_or_swapped_message_rejects(self):
        m = self.module()
        f = self.frame(m)
        for cc in [f.cs, replace(f.cc, schema_id=True), replace(f.cc, schema_id=0)]:
            self.rejected(m, 'OWNED_SCHEMA', replace(f, cc=cc))

    def test_mutable_empty_oversized_and_hash_mismatched_payload_rejects(self):
        m = self.module()
        f = self.frame(m)
        for value in [bytearray(f.cc.payload), memoryview(f.cc.payload), b'', b'x' * 65537, f.cc.payload + b'x']:
            self.rejected(m, 'OWNED_PAYLOAD', replace(f, cc=replace(f.cc, payload=value)))
        self.rejected(m, 'OWNED_PAYLOAD', replace(f, cc=replace(f.cc, payload_sha256='0' * 64)))

    def test_missing_duplicate_extra_or_mutable_ledger_rejects(self):
        m = self.module()
        f = self.frame(m)
        required = f.ledger.written_fields
        for value in [(), required[:-1], required + (required[0],), required + ('CC.enabled',), list(required)]:
            self.rejected(m, 'OWNED_FIELD_LEDGER', replace(f, ledger=replace(f.ledger, written_fields=value)))

    def test_ledger_digests_bound_to_each_owned_payload(self):
        m = self.module()
        f = self.frame(m)
        self.rejected(m, 'OWNED_FIELD_LEDGER', replace(f, ledger=replace(f.ledger, cc_sha256=f.cs.payload_sha256)))

    def test_settings_are_explicit_bounded_builtin_integers(self):
        m = self.module()
        f = self.frame(m)
        for name, value in [('steer_max', 0), ('steer_max', 2049), ('delta_up', True), ('delta_down', -1),
                            ('driver_allowance', 65), ('driver_factor', 9), ('driver_multiplier', 1.0)]:
            self.rejected(m, 'OWNED_SETTINGS', replace(f, settings=replace(f.settings, **{name: value})))

    def test_resumed_state_keeps_prior_candidate_separate(self):
        m = self.module()
        f = self.frame(m, 1)
        output = m.prepare_owned_frame(f)
        self.assertEqual(output.frame.previous.previous_requested, 3)
        self.assertEqual(output.frame.previous.source_previous_applied, 0)

    def test_prior_order_stage_state_and_source_mismatch_reject(self):
        m = self.module()
        f = self.frame(m, 1)
        for change in [{'previous_invocation_index': None}, {'previous_invocation_index': True}, {'previous_requested': None},
                       {'previous_requested': 2049}, {'stage': 'AFTER_LIMITER'}, {'source_previous_applied': 1},
                       {'source_angle_counter': 1}, {'angle_counter': 91}, {'previous_applied': -2049}]:
            self.rejected(m, 'OWNED_PREVIOUS', replace(f, previous=replace(f.previous, **change)))

    def test_initial_state_must_be_declared_zero_without_previous_request(self):
        m = self.module()
        f = self.frame(m)
        for change in [{'previous_invocation_index': 0}, {'previous_requested': 0},
                       {'source_previous_applied': 1, 'previous_applied': 1}, {'source_angle_counter': 1, 'angle_counter': 1}]:
            self.rejected(m, 'OWNED_PREVIOUS', replace(f, previous=replace(f.previous, **change)))


if __name__ == '__main__':
    unittest.main()
