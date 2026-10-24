import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from importlib import import_module
import numpy as np
from openpilot.tools.cyber_autotune.tests.test_empirical_s2_ri_admission import fixture
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as store
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as old
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as oldpol
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestS2RIExecution(unittest.TestCase):
  def module(self):
    return import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_execution')

  def test_qlog_denied_before_array_access(self):
    e = self.module()
    pol = oldpol.policy()
    auth = {'segments': {pol['route_ids'][0]: [pol['excluded_qlog_content_sha256'][0]]}}
    with tempfile.TemporaryDirectory() as td, patch.object(old, 'read_json', side_effect=[{}, auth]), \
         patch('numpy.load', side_effect=AssertionError('QLOG_OPENED')):
      with self.assertRaisesRegex(ValueError, 'QLOG_CAUSAL_ADMISSION_FORBIDDEN'):
        e.preflight(Path(td), e.policy.policy())

  def test_changed_policy_denied_before_array(self):
    e = self.module()
    pol = e.policy.policy()
    pol['forms'] = []
    with tempfile.TemporaryDirectory() as td, patch('numpy.load', side_effect=AssertionError):
      with self.assertRaises(ValueError):
        e.preflight(Path(td), pol)

  def test_rate_and_request_proof(self):
    e = self.module()
    a = fixture()
    a['state.rate'] = np.arange(100.)
    a['state.rate.available'] = np.ones(100, bool)
    self.assertTrue(e.independence_proof(a))
    real_derive = e.admission.derive
    def hidden_dependency(x):
      return {**real_derive(x), 'hidden_rate_mask': np.isfinite(x.get('state.rate', np.ones(100)))}
    with patch.object(e.admission, 'derive', side_effect=hidden_dependency):
      with self.assertRaisesRegex(ValueError, 'HIDDEN_RATE'):
        e.independence_proof(a)

  def test_two_synthetic_runs_and_resume_no_fit(self):
    e = self.module()
    with tempfile.TemporaryDirectory() as td:
      root, output = Path(td)/'input', Path(td)/'output'
      root.mkdir()
      records = []
      ids = e.policy.policy()['route_ids']
      for number, rid in enumerate(ids):
        base = root/rid
        a = fixture(100)
        a['state.rate'] = np.arange(100.)
        a['state.rate.available'] = np.ones(100, bool)
        bindings = {k: store.array_write(base/'arrays'/old.array_name(k), v) for k, v in a.items()}
        records.append((base, {'route_id': rid, 'segment_sha256': p.sha(str(number).encode()), 'arrays': bindings,
                               'receipt_sha256': p.sha(('receipt'+str(number)).encode())}))
      fake = (None, None, {'receipt_sha256': 'a'*64}, records, {})
      from openpilot.tools.cyber_autotune import empirical_plant_model as model
      from openpilot.tools.cyber_autotune import empirical_v3_models as cv
      from openpilot.tools.cyber_autotune import controller_plant_experiment as candidate
      with contextlib.ExitStack() as traps:
        for module, names in ((model, ('fit', 'static_fit', 'select', 'evaluate', 'statistics', 'group_stats')),
                              (cv, ('predictions', 'evaluate', 'choose')),
                              (candidate, ('run_input', 'original_geometry_oracle'))):
          for name in names:
            traps.enter_context(patch.object(module, name, side_effect=AssertionError('MODEL_OPERATION_FORBIDDEN')))
        with patch.dict(os.environ, {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}), \
           patch.object(e, 'preflight', return_value=fake), patch('numpy.linalg.lstsq', side_effect=AssertionError('FIT')), \
           patch('numpy.polyfit', side_effect=AssertionError('FIT')), patch('numpy.linalg.pinv', side_effect=AssertionError('FIT')), \
           contextlib.redirect_stdout(io.StringIO()):
          a = e.run(root, output, 'repeat-1')
          b = e.run(root, output, 'repeat-2')
          self.assertEqual(a, b)
          self.assertEqual(e.run(root, output, 'repeat-1'), a)
      self.assertEqual(a['qlog_arrays_opened'], 0)
      self.assertEqual(a['rate_dependency'], 'NONE')
      self.assertEqual(len(a['forms']), 8)
      self.assertTrue(a['input_bytes_unchanged'])

  def test_overlay_does_not_mutate_source(self):
    e = self.module()
    a = fixture()
    before = {k: v.tobytes() for k, v in a.items()}
    e.independence_proof(a)
    self.assertEqual(before, {k: v.tobytes() for k, v in a.items()})
