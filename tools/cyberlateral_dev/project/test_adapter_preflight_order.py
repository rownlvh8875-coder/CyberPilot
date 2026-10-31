"""M1 regression: invalid construct inputs must never touch native allocation."""

import importlib
import sys
import unittest
from dataclasses import replace

from v1_helpers import ROOT, package_feature


class AdapterPreflightOrderTests(unittest.TestCase):
    def fixture(self):
        package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        m = importlib.import_module('integration_tools.native_adapter')
        b = importlib.import_module('integration_tools.owned_message_boundary')
        stamp = b.Stamp('M1', 0, 'NO_ALLOCATION')
        spec = m.SyntheticSpec(stamp, b.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
                               b.PreviousSnapshot(stamp, None, 0, 0, 0, 0, None, 'ENTRY_BEFORE_CURRENT_LIMITER'),
                               0.25, 1.5, -7.25, True)
        return m, spec

    def rejects_without_backend_access(self, m, spec, code):
        accesses = []
        class AllocationTripwire:
            def __getattr__(self, name):
                accesses.append(name)
                raise AssertionError('Native allocation must not be attempted')
        adapter = m._SyntheticAdapter(AllocationTripwire())
        try:
            with self.assertRaises(m.AdapterError) as error:
                adapter.construct(spec)
            self.assertEqual(error.exception.code, code)
            self.assertEqual(accesses, [])
        finally:
            adapter.close()

    def test_bad_envelope_rejects_before_allocation(self):
        m, spec = self.fixture()
        for changed, code in [
            (replace(spec, stamp=replace(spec.stamp, capture_id='OTHER')), 'OWNED_STAMP'),
            (replace(spec, settings=replace(spec.settings, steer_max=0)), 'OWNED_SETTINGS'),
            (replace(spec, previous=replace(spec.previous, previous_applied=1)), 'OWNED_PREVIOUS'),
        ]:
            self.rejects_without_backend_access(m, changed, 'ADAPTER_ENVELOPE:' + code)

    def test_bad_domain_and_type_reject_before_allocation(self):
        m, spec = self.fixture()
        for changed, code in [(None, 'ADAPTER_SPEC_TYPE'), (replace(spec, request=1), 'ADAPTER_DOMAIN'),
                              (replace(spec, request=float('inf')), 'ADAPTER_DOMAIN'), (replace(spec, lat_active=1), 'ADAPTER_DOMAIN')]:
            self.rejects_without_backend_access(m, changed, code)

    def test_precision_loss_rejects_before_allocation(self):
        m, spec = self.fixture()
        for request in [0.3, float.fromhex('0x1p-150')]:
            self.rejects_without_backend_access(m, replace(spec, request=request), 'ADAPTER_PRECISION')
