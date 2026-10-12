"""Public-only binding, immutable storage and anti-execution tests."""
import builtins
import copy
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_fitting_policy as policy


class TestS2RIFittingPublication(unittest.TestCase):
  def test_exact_file_and_receipt_binding(self):
    inputs = policy.load_inputs()
    self.assertEqual(len(inputs), 14)
    self.assertEqual(inputs['empirical-s2-ri-readiness-v1.json']['steering_rate_dependency'], 'NONE')

  def public_copy(self, root):
    for n in policy.PINS:
      (root/n).write_bytes((policy.PUBLIC/n).read_bytes())

  def test_whitespace_input_drift_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      self.public_copy(root)
      n = next(iter(policy.PINS))
      (root/n).write_bytes((root/n).read_bytes()+b' ')
      with mock.patch.object(policy, 'PUBLIC', root), self.assertRaisesRegex(ValueError, 'HISTORICAL_FILE_SHA'):
        policy.build()

  def test_resealed_historical_drift_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      self.public_copy(root)
      n = 'empirical-s2-ri-readiness-v1.json'
      v = json.loads((root/n).read_bytes())
      v['status'] = 'MODEL_READY'
      v = p.seal({k:x for k,x in v.items() if k != 'receipt_sha256'})
      (root/n).write_text(json.dumps(v))
      with mock.patch.object(policy, 'PUBLIC', root), self.assertRaises(ValueError):
        policy.build()

  def test_pins_not_self_accepting_receipts(self):
    for pin in policy.PINS.values():
      self.assertEqual(len(pin['file_sha256']), 64)
      self.assertEqual(len(pin['receipt_sha256']), 64)
    with mock.patch.object(policy, 'PINS', copy.deepcopy(policy.PINS)):
      policy.PINS[next(iter(policy.PINS))]['receipt_sha256'] = '0'*64
      with self.assertRaisesRegex(ValueError, 'HISTORICAL_RECEIPT_SHA'):
        policy.build()

  def test_missing_input_fails(self):
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(policy, 'PUBLIC', Path(tmp)):
      with self.assertRaises(FileNotFoundError):
        policy.build()

  def test_input_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      (root/'public').symlink_to(policy.PUBLIC, target_is_directory=True)
      with mock.patch.object(policy, 'PUBLIC', root/'public'), self.assertRaisesRegex(ValueError, 'SYMLINK'):
        policy.build()

  def test_immutable_publish_and_exact_resume(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      a=policy.publish(root)
      before={n:(root/n).read_bytes() for n in a}
      b=policy.publish(root)
      self.assertEqual(a,b)
      self.assertEqual(before,{n:(root/n).read_bytes() for n in a})
      self.assertEqual(len(a),13)
      policy.validate({n:json.loads(raw) for n,raw in before.items()})

  def test_conflicting_publication_no_overwrite_or_partial_write(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      name='empirical-s2-ri-selection-rule-v1.json'
      (root/name).write_bytes(b'conflict')
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE_POLICY'):
        policy.publish(root)
      self.assertEqual([x.name for x in root.iterdir()], [name])
      self.assertEqual((root/name).read_bytes(), b'conflict')

  def test_output_symlink_and_traversal_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      (root/'link').symlink_to(root, target_is_directory=True)
      for path in (root/'link', root/'child'/'..'):
        with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'TRAVERSAL_OR_SYMLINK'):
          policy.publish(path)

  def test_interrupted_atomic_resume(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      bundle=policy.build()
      name=next(iter(bundle))
      (root/(name+'.atomic')).write_text(json.dumps(bundle[name],sort_keys=True,indent=2)+'\n')
      policy.publish(root)
      self.assertFalse((root/(name+'.atomic')).exists())
      self.assertEqual(json.loads((root/name).read_bytes()),bundle[name])

  def test_wrong_types_do_not_pass_python_equality(self):
    bundle=policy.build()
    name='empirical-s2-ri-fitting-policy-readiness-v1.json'
    bundle[name]['opening_count']=False
    bundle[name]=p.seal({k:v for k,v in bundle[name].items() if k!='receipt_sha256'})
    with self.assertRaisesRegex(ValueError,'CONTRACT_DRIFT'):
      policy.validate(bundle)

  def test_historical_files_unchanged(self):
    before={n:(policy.PUBLIC/n).read_bytes() for n in policy.PINS}
    policy.validate(policy.build())
    self.assertEqual(before,{n:(policy.PUBLIC/n).read_bytes() for n in policy.PINS})

  def test_no_private_reads_solver_or_execution_imports(self):
    expected=policy.build()
    allowed={(policy.PUBLIC/n).absolute() for n in policy.PINS}
    allowed.update(Path(policy.__file__).with_name(n).absolute() for n in (
      'empirical_s2_ri_fitting_policy.py','empirical_s2_ri_fitting_contracts.py'))
    original_io_open=io.open
    original_import=builtins.__import__
    forbidden=('empirical_s2_ri_execution','empirical_s2_ri_publication','empirical_identifiability_execution',
      'empirical_plant_fit','empirical_plant_cv','empirical_causal_dataset_reader','empirical_causal_dataset_execution',
      'empirical_qlog','logreader','trajectory_authority','smoothness_governor','scipy','sklearn')

    def guarded_open(path,*args,**kwargs):
      if not isinstance(path,(str,bytes,Path)) or Path(path).absolute() not in allowed:
        raise AssertionError('PRIVATE_OR_UNDECLARED_FILE_ACCESS')
      if args and any(s in str(args[0]) for s in ('w','a','+')):
        raise AssertionError('UNAUTHORIZED_WRITE')
      return original_io_open(path,*args,**kwargs)

    def guarded_import(name,*args,**kwargs):
      names=[name, *([x for x in args[2] if isinstance(x,str)] if len(args)>2 and args[2] else [])]
      if any(any(token in n for token in forbidden) for n in names):
        raise AssertionError('MODEL_OR_PRIVATE_EXECUTION_IMPORT_FORBIDDEN')
      return original_import(name,*args,**kwargs)

    trap=AssertionError('NUMERIC_EXECUTION_FORBIDDEN')
    with mock.patch('io.open',side_effect=guarded_open), mock.patch('builtins.open',side_effect=guarded_open), \
         mock.patch('builtins.__import__',side_effect=guarded_import), mock.patch.object(np,'load',side_effect=trap), \
         mock.patch.object(np.linalg,'lstsq',side_effect=trap), mock.patch.object(np,'polyfit',side_effect=trap):
      self.assertEqual(policy.validate(policy.build()),expected)

  def test_no_executable_model_interface(self):
    for name in ('fit','predict','rollout','select','score','load_arrays','evaluate_metrics'):
      self.assertFalse(hasattr(policy,name))
    contracts=importlib.import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_fitting_contracts')
    for name in ('fit','predict','rollout','select','score','load_arrays','evaluate_metrics'):
      self.assertFalse(hasattr(contracts,name))

  def test_noncanonical_atomic_cannot_publish_unresumable_bytes(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      bundle=policy.build()
      name='empirical-s2-ri-selection-rule-v1.json'
      atomic=root/(name+'.atomic')
      atomic.write_text(json.dumps(bundle[name],separators=(',',':')))
      before=atomic.read_bytes()
      with self.assertRaisesRegex(ValueError,'IMMUTABLE_POLICY'):
        policy.publish(root)
      self.assertEqual({x.name for x in root.iterdir()}, {atomic.name})
      self.assertEqual(atomic.read_bytes(),before)

  def test_late_corrupt_atomic_prevents_all_publication(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      atomic=root/'empirical-s2-ri-selection-rule-v1.json.atomic'
      atomic.write_bytes(b'corrupt')
      with self.assertRaises(ValueError):
        policy.publish(root)
      self.assertEqual({x.name for x in root.iterdir()}, {atomic.name})

  def test_atomic_symlink_rejected_before_any_write(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      atomic=root/'empirical-s2-ri-selection-rule-v1.json.atomic'
      atomic.symlink_to(root/'missing-target')
      with self.assertRaises(ValueError):
        policy.publish(root)
      self.assertEqual({x.name for x in root.iterdir()}, {atomic.name})

  def test_persistence_result_bytes_checked_before_success(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=Path(tmp)
      original=p.persist

      def changed_encoding(path,value):
        original(path,value)
        if path.name=='empirical-s2-ri-selection-rule-v1.json':
          path.write_text(json.dumps(value,separators=(',',':')))

      with mock.patch.object(p,'persist',side_effect=changed_encoding), self.assertRaisesRegex(ValueError,'PUBLICATION_BYTES'):
        policy.publish(root)
