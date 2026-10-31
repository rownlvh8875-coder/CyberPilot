"""R28 preflight: malformed declarations must fail before native allocation."""

import importlib
import sys
import unittest
from dataclasses import replace

from v1_helpers import ROOT, package_feature


class NativeAdapterTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/native_adapter.py').is_file(), 'Missing R28 adapter')
        package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (importlib.import_module('integration_tools.native_adapter'),
                importlib.import_module('integration_tools.owned_message_boundary'))

    def spec(self, m, b):
        stamp = b.Stamp('R28', 0, 'SYNTHETIC')
        return m.SyntheticSpec(stamp, b.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
                               b.PreviousSnapshot(stamp, None, 0, 0, 0, 0, None, 'ENTRY_BEFORE_CURRENT_LIMITER'),
                               0.25, 1.5, -7.25, True)

    def reject(self, m, spec, code):
        with self.assertRaises(m.AdapterError) as error:
            m.validate_spec(spec)
        self.assertEqual(error.exception.code, code)

    def test_accepts_exact_values_without_normalization(self):
        m, b = self.modules()
        spec = self.spec(m, b)
        for value in [0.25, -0.0, -1.0, 1.0, float.fromhex('0x1p-149'), float.fromhex('0x1.333334p-2')]:
            m.validate_spec(replace(spec, request=value))

    def test_nonexact_float_rejects_instead_of_rounding(self):
        m, b = self.modules()
        for value in [0.3, float.fromhex('0x1p-150')]:
            self.reject(m, replace(self.spec(m, b), request=value), 'ADAPTER_PRECISION')

    def test_bad_domains_and_scalar_types_reject(self):
        m, b = self.modules()
        for name, value in [('request', 1), ('request', True), ('request', float('nan')), ('request', float('inf')),
                            ('request', 1.1), ('driver', 1025.0), ('driver', 0.1), ('angle_deg', 181.0),
                            ('angle_deg', 0.30000001192092896), ('lat_active', 1)]:
            self.reject(m, replace(self.spec(m, b), **{name: value}), 'ADAPTER_DOMAIN')

    def test_wrong_record_rejects_without_property_access(self):
        m, _ = self.modules()
        class Hostile:
            def __getattribute__(self, name):
                raise AssertionError('must not inspect')
        self.reject(m, Hostile(), 'ADAPTER_SPEC_TYPE')

    def test_stamp_settings_and_previous_associations_reject(self):
        m, b = self.modules()
        spec = self.spec(m, b)
        for changed, code in [
            (replace(spec, stamp=replace(spec.stamp, invocation_index=True)), 'OWNED_STAMP'),
            (replace(spec, settings=replace(spec.settings, stamp=replace(spec.stamp, capture_id='OTHER'))), 'OWNED_STAMP'),
            (replace(spec, settings=replace(spec.settings, steer_max=0)), 'OWNED_SETTINGS'),
            (replace(spec, previous=replace(spec.previous, previous_applied=1)), 'OWNED_PREVIOUS'),
            (replace(spec, previous=replace(spec.previous, previous_invocation_index=0)), 'OWNED_PREVIOUS'),
        ]:
            self.reject(m, changed, 'ADAPTER_ENVELOPE:' + code)

    def test_resumed_snapshot_is_validated_not_inferred(self):
        m, b = self.modules()
        spec = self.spec(m, b)
        stamp = replace(spec.stamp, invocation_index=1)
        spec = replace(spec, stamp=stamp, settings=replace(spec.settings, stamp=stamp),
                       previous=b.PreviousSnapshot(stamp, 0, 3, 1, 3, 1, 5, 'ENTRY_BEFORE_CURRENT_LIMITER'))
        m.validate_spec(spec)
        self.reject(m, replace(spec, previous=replace(spec.previous, previous_invocation_index=None)), 'ADAPTER_ENVELOPE:OWNED_PREVIOUS')

    def test_foreign_input_and_closed_adapter_reject_before_native_use(self):
        m, _ = self.modules()
        # No native dependency required for rejection paths; invalid input must
        # never touch this deliberately unusable backend.
        adapter = m._SyntheticAdapter(None)
        for value in [b'arbitrary bytes', object(), None]:
            with self.assertRaises(m.AdapterError) as error:
                adapter.prepare(value)
            self.assertEqual(error.exception.code, 'ADAPTER_HANDLE_TYPE')
        adapter.close()
        with self.assertRaises(m.AdapterError) as error:
            adapter.prepare(None)
        self.assertEqual(error.exception.code, 'ADAPTER_CONTEXT_CLOSED')
