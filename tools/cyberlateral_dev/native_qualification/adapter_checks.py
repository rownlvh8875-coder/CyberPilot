"""Real native adapter boundary checks; no model step, simulate or F61 calls."""

import copy
import gc
import io
import unittest
import weakref
from dataclasses import FrozenInstanceError, replace


def run_checks(adapter) -> dict:
    import cyberlateral_dev as p
    from integration_tools import native_adapter as m
    from integration_tools import owned_message_boundary as b
    from native_qualification.adapter_oracle import expected

    records = []

    class Checks(unittest.TestCase):
        def spec(self):
            stamp = b.Stamp('R28', 0, 'SYNTHETIC')
            return m.SyntheticSpec(stamp, b.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
                                   b.PreviousSnapshot(stamp, None, 0, 0, 0, 0, None, 'ENTRY_BEFORE_CURRENT_LIMITER'),
                                   0.25, 1.5, -7.25, True)

        def read(self, spec):
            handle = adapter.construct(spec)
            frame = adapter.inspect(handle)
            prepared = adapter.prepare(handle)
            want = expected(frame, spec.request, spec.driver, spec.angle_deg, spec.lat_active)
            self.assertEqual((prepared.prepared.sample, prepared.prepared.state), want)
            self.assertEqual([prepared.prepared.sample.request.hex(), prepared.prepared.sample.driver.hex(),
                              prepared.prepared.sample.angle_deg.hex()],
                             [want[0].request.hex(), want[0].driver.hex(), want[0].angle_deg.hex()])
            return handle, frame, prepared

        def reject(self, spec, code):
            with self.assertRaises(m.AdapterError) as error:
                adapter.construct(spec)
            self.assertEqual(error.exception.code, code)

        def test_literal_input_not_model_execution(self):
            handle, frame, result = self.read(self.spec())
            self.assertEqual(result.prepared.sample, p.LateralInput(0, 0.25, 1.5, -7.25, True, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'))
            self.assertEqual(result.prepared.state, p.LateralState(0, None, 0, 0))
            self.assertEqual(result.prepared.custody_claim, 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY')
            self.assertEqual(result.prepared.time_semantics, 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
            self.assertEqual(result.read_claim, 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT')
            self.assertEqual(type(frame.cc.payload), bytes)
            self.assertEqual(adapter.prepare(handle), result)
            records.append({'id': 'literal', 'request_hex': result.prepared.sample.request.hex(), 'state': [0, None, 0, 0]})

        def test_negative_zero_survives_all_fields(self):
            _, _, result = self.read(replace(self.spec(), request=-0.0, driver=-0.0, angle_deg=-0.0))
            self.assertEqual([result.prepared.sample.request.hex(), result.prepared.sample.driver.hex(), result.prepared.sample.angle_deg.hex()],
                             ['-0x0.0p+0'] * 3)
            records.append({'id': 'negative_zero', 'hex': '-0x0.0p+0'})

        def test_minimum_subnormal_preserved(self):
            _, _, result = self.read(replace(self.spec(), request=float.fromhex('0x1p-149')))
            self.assertEqual(result.prepared.sample.request.hex(), '0x1.0000000000000p-149')
            records.append({'id': 'subnormal', 'hex': result.prepared.sample.request.hex()})

        def test_explicit_promoted_point_three_preserved(self):
            _, _, result = self.read(replace(self.spec(), request=float.fromhex('0x1.333334p-2')))
            self.assertEqual(result.prepared.sample.request.hex(), '0x1.3333340000000p-2')
            records.append({'id': 'promoted_point_three', 'hex': result.prepared.sample.request.hex()})

        def test_inclusive_bounds_preserved(self):
            for request, driver, angle in [(-1.0, -1024.0, -180.0), (1.0, 1024.0, 180.0)]:
                _, _, result = self.read(replace(self.spec(), request=request, driver=driver, angle_deg=angle))
                self.assertEqual((result.prepared.sample.request, result.prepared.sample.driver, result.prepared.sample.angle_deg),
                                 (request, driver, angle))

        def test_previous_state_not_current_request_or_applied_alias(self):
            spec = self.spec()
            stamp = replace(spec.stamp, invocation_index=1)
            spec = replace(spec, stamp=stamp, settings=replace(spec.settings, stamp=stamp),
                           previous=b.PreviousSnapshot(stamp, 0, 3, 1, 3, 1, 5, 'ENTRY_BEFORE_CURRENT_LIMITER'))
            _, _, result = self.read(spec)
            self.assertEqual(result.prepared.state, p.LateralState(1, 5, 3, 1))
            records.append({'id': 'resumed', 'state': [1, 5, 3, 1]})

        def test_binary64_rounding_not_silent(self):
            self.reject(replace(self.spec(), request=0.3), 'ADAPTER_PRECISION')
            self.reject(replace(self.spec(), request=float.fromhex('0x1p-150')), 'ADAPTER_PRECISION')

        def test_bad_domain_and_types_reject(self):
            for name, value in [('request', float('nan')), ('request', float('inf')), ('request', 1),
                                ('driver', 1025.0), ('angle_deg', 181.0), ('lat_active', 1)]:
                self.reject(replace(self.spec(), **{name: value}), 'ADAPTER_DOMAIN')

        def test_mismatched_settings_stamp_rejects(self):
            spec = self.spec()
            self.reject(replace(spec, settings=replace(spec.settings, stamp=replace(spec.stamp, capture_id='OTHER'))),
                        'ADAPTER_ENVELOPE:OWNED_STAMP')

        def test_inconsistent_previous_state_rejects(self):
            spec = self.spec()
            self.reject(replace(spec, previous=replace(spec.previous, previous_applied=1)), 'ADAPTER_ENVELOPE:OWNED_PREVIOUS')

        def test_inspected_frame_and_bytes_cannot_be_parsed_by_api(self):
            handle = adapter.construct(self.spec())
            frame = adapter.inspect(handle)
            for value in [frame, frame.cc.payload, bytearray(frame.cc.payload)]:
                with self.assertRaises(m.AdapterError) as error:
                    adapter.prepare(value)
                self.assertEqual(error.exception.code, 'ADAPTER_HANDLE_TYPE')

        def test_copied_and_foreign_handles_reject(self):
            handle = adapter.construct(self.spec())
            with self.assertRaises(m.AdapterError) as error:
                adapter.prepare(copy.copy(handle))
            self.assertEqual(error.exception.code, 'ADAPTER_HANDLE_UNKNOWN')
            other = m._SyntheticAdapter(None)
            with self.assertRaises(m.AdapterError) as error:
                other.prepare(handle)
            self.assertEqual(error.exception.code, 'ADAPTER_HANDLE_UNKNOWN')

        def test_owned_data_outlives_temporary_native_readers(self):
            handle, frame, result = self.read(self.spec())
            gc.collect()
            self.assertEqual(adapter.prepare(handle), result)
            with self.assertRaises(FrozenInstanceError):
                frame.scope = 'ACTUAL'
            with self.assertRaises(FrozenInstanceError):
                result.read_claim = 'ACTUAL'

        def test_weak_handles_do_not_retain_abandoned_frames(self):
            handle = adapter.construct(self.spec())
            pointer = weakref.ref(handle)
            del handle
            gc.collect()
            self.assertIsNone(pointer())

        def test_inactive_false_is_explicit_not_missing(self):
            _, frame, result = self.read(replace(self.spec(), request=0.0, lat_active=False))
            self.assertIs(result.prepared.sample.lat_active, False)
            self.assertIn('CC.latActive', frame.ledger.written_fields)

    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise ValueError('ADAPTER_NATIVE_CHECKS_FAILED:' + stream.getvalue())
    return {'tests_run': result.testsRun, 'failures': 0, 'errors': 0, 'records': sorted(records, key=lambda row: row['id'])}
