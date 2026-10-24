"""Read-only attribution stops before array decoding when targets were not saved."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

MODULE = 'openpilot.tools.cyber_autotune.empirical_s2_ri_failure_attribution'


class TestAttributionInput(unittest.TestCase):
  def module(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'attribution input gate is required')
    return __import__(MODULE, fromlist=[''])

  def test_module_exists(self):
    self.module()

  def test_exact_manifest(self):
    a = self.module()
    with self.assertRaisesRegex(ValueError, 'EXACT_A50D'):
      a.require_manifest(p.seal({'files':{}, 'job_count':32}))

  def test_missing_targets_fail_before_loader(self):
    a = self.module()
    result = a.availability({'one_step_buffers':dict.fromkeys(
      ('prediction','projected','error','comparator_error'),'a'*64),
      'rollout_buffers':{str(h):dict.fromkeys(('projected','error','comparator_error'),'b'*64) for h in a.HORIZONS}})
    self.assertEqual(result['status'], 'ATTRIBUTION_INPUT_INSUFFICIENT')
    self.assertIn('ONE_STEP_CURRENT_AND_TARGET_NOT_PERSISTED', result['reasons'])
    self.assertFalse(result['numeric_attribution_allowed'])

  def test_no_alias_target(self):
    a = self.module()
    result = a.availability({'one_step_buffers':{'comparator_error':'a'*64}, 'rollout_buffers':{}})
    self.assertIsNone(result['target_sha256'])
    self.assertFalse(result['recover_target_from_error'])

  def test_safe_file_hash(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      root = Path(name)
      (root/'buffer.npy').write_bytes(b'opaque bytes, never np.load')
      manifest = p.seal({'files':{'buffer.npy':p.sha((root/'buffer.npy').read_bytes())}})
      self.assertEqual(a.verify_files(root, manifest), p.sha(p.canonical(manifest['files'])))
      (root/'buffer.npy').write_bytes(b'drift')
      with self.assertRaisesRegex(ValueError, 'IMMUTABILITY'):
        a.verify_files(root, manifest)

  def test_missing_file(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      with self.assertRaisesRegex(ValueError, 'INPUT_INCOMPLETE'):
        a.verify_files(Path(name), p.seal({'files':{'missing.npy':'a'*64}}))

  def test_traversal(self):
    a = self.module()
    for name in ('../other','/tmp/other',r'..\other',r'C:\other','a//b','./a'):
      with self.subTest(name=name), self.assertRaises(ValueError):
        a.relative_file(Path('/tmp/attribution'), name)

  def test_symlink(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      root = Path(name)
      (root/'real').write_bytes(b'data')
      (root/'alias').symlink_to(root/'real')
      with self.assertRaises(ValueError):
        a.relative_file(root, 'alias')

  def test_public_pins_and_no_verdict_change(self):
    a = self.module()
    public = a.public_inputs()
    self.assertEqual(public['selection-result']['admissible_count'], 0)
    self.assertIsNone(public['selection-result']['selected_candidate'])
    counts = a.failure_counts(public['fit-cv-results']['jobs'])
    self.assertEqual(counts['ONE_STEP_RMSE'], 0)
    self.assertEqual(counts['ONE_STEP_MAE'], 32)
    self.assertEqual(counts['ONE_STEP_EXACT_HIT'], 32)
    self.assertEqual(counts['ONE_STEP_P95'], 27)
    self.assertEqual(counts['ROLLOUT_25_P95'], 32)

  def test_anchor_mismatch(self):
    a = self.module()
    with self.assertRaisesRegex(ValueError, 'ANCHOR'):
      a.verify_anchors({'one_step':{'anchor_sha256':'a'*64,'comparator_anchor_sha256':'b'*64},
        'rollout':{}})

  def test_missing_horizon(self):
    a = self.module()
    with self.assertRaisesRegex(ValueError, 'INPUT_INCOMPLETE'):
      a.verify_anchors({'one_step':{'anchor_sha256':'a'*64,'comparator_anchor_sha256':'a'*64},
        'rollout':{}})

  def test_public_receipt_drift(self):
    a = self.module()
    with patch.object(a, 'PUBLIC_PINS', {**a.PUBLIC_PINS,'fit-cv-results':'0'*64}):
      with self.assertRaisesRegex(ValueError, 'PUBLIC_INPUT'):
        a.public_inputs()

  def test_job_count_and_order(self):
    a = self.module()
    jobs = a.public_inputs()['fit-cv-results']['jobs']
    a.require_jobs(jobs)
    for changed in (jobs[:-1], jobs+[jobs[0]], list(reversed(jobs))):
      with self.subTest(count=len(changed)), self.assertRaisesRegex(ValueError, 'INPUT_INCOMPLETE'):
        a.require_jobs(changed)

  def test_no_promotion_from_missing(self):
    a = self.module()
    v = a.availability({'one_step_buffers':{},'rollout_buffers':{}})
    self.assertEqual(v['analyses'], None)
    self.assertEqual(v['hurdle_trigger'], 'NOT_EVALUATED_INSUFFICIENT_INPUT')
    self.assertFalse(v['hurdle_implementation_authorized'])

  def test_sealed_receipt_required(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      path = Path(name)/'receipt.json'
      path.write_text(json.dumps({'receipt_sha256':'x'}))
      with self.assertRaises(ValueError):
        a.read_json(path)

  def test_policy_firewall(self):
    a = self.module()
    v = a.policy()
    for key in ('fit','predict','rollout','select','causal_arrays','raw_logs','qlog','holdout','hurdle'):
      self.assertFalse(v['authorized'][key])
    self.assertEqual(v['input_manifest_sha256'], a.INPUT_SHA)

  def test_resume_hash_drift(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      root=Path(name)
      a.write(root/'audit.json',p.seal({'status':'ATTRIBUTION_INPUT_INSUFFICIENT'}))
      a.finish(root, ['audit.json'], {'schema':'TEST'})
      self.assertEqual(a.resume(root)['schema'],'TEST')
      (root/'audit.json').write_bytes(b'changed')
      with self.assertRaisesRegex(ValueError, 'IMMUTABILITY'):
        a.resume(root)

  def test_no_overwrite(self):
    a = self.module()
    with tempfile.TemporaryDirectory() as name:
      path=Path(name)/'r.json'
      value=p.seal({'test':1})
      a.write(path,value)
      a.write(path,value)
      with self.assertRaises(ValueError):
        a.write(path,p.seal({'test':2}))

  def test_all_32_anchors_match(self):
    a = self.module()
    for job in a.public_inputs()['fit-cv-results']['jobs']:
      a.verify_anchors(job)

  def test_reject_fake_candidate(self):
    a = self.module()
    jobs=copy.deepcopy(a.public_inputs()['fit-cv-results']['jobs'])
    jobs[0]['candidate_id']='S2RI_D21_L46'
    with self.assertRaisesRegex(ValueError,'INPUT_INCOMPLETE'):
      a.require_jobs(jobs)


if __name__ == '__main__':
  unittest.main()


class TestAttributionPublication(unittest.TestCase):
  def test_publication_module_exists(self):
    self.assertIsNotNone(importlib.util.find_spec(
      'openpilot.tools.cyber_autotune.empirical_s2_ri_failure_attribution_publication'))

  def test_firewall_has_no_numeric_executor_import(self):
    import ast
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    tree=ast.parse(Path(a.__file__).read_text())
    imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    self.assertFalse(any('execution' in n or 'fit_cv' in n for n in imports))
    calls=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
    self.assertFalse(set(calls) & {'load','lstsq','solve','pinv','fit','predict','recursive','select'})

  def test_audit_under_model_and_decoder_traps(self):
    from contextlib import ExitStack
    import numpy as np
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_execution as execute
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates
    with ExitStack() as stack:
      for obj, name in ((np,'load'),(np.linalg,'lstsq'),(np.linalg,'solve'),(np.linalg,'pinv'),
                        (m,'normalizer'),(m,'fit'),(m,'predict'),(m,'recursive'),
                        (execute,'load_routes'),(execute,'rollout'),(gates,'select')):
        stack.enter_context(patch.object(obj,name,side_effect=AssertionError('FORBIDDEN_EXECUTION')))
      self.assertEqual(a.policy()['input_mode'],'READ_ONLY_HASH_AND_SEALED_METADATA')
      public=a.public_inputs()
      a.require_jobs(public['fit-cv-results']['jobs'])
      for job in public['fit-cv-results']['jobs']:
        a.verify_anchors(job)
      with tempfile.TemporaryDirectory() as name:
        root=Path(name)
        value=p.seal({'schema':'TEST','status':'ATTRIBUTION_INPUT_INSUFFICIENT'})
        a.write(root/'audit.json',value)
        a.finish(root,['audit.json'],{'schema':'TEST'})
        a.resume(root)

  def test_resume_does_not_reinspect_source(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    with tempfile.TemporaryDirectory() as name:
      root=Path(name)
      a.write(root/'audit.json',p.seal({'status':'ATTRIBUTION_INPUT_INSUFFICIENT'}))
      a.finish(root,['audit.json'],{'schema':'TEST'})
      with patch.object(a,'inspect_store',side_effect=AssertionError('SOURCE_REOPENED')):
        a.resume(root)


class TestUnavailablePublication(unittest.TestCase):
  def test_no_false_complete_or_trigger(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution_publication as pub
    value=pub.unavailable('one-step-attribution',p.seal({'input_manifest_sha256':a.INPUT_SHA,
      'status':'ATTRIBUTION_INPUT_INSUFFICIENT'}))
    self.assertIsNone(value['analysis'])
    self.assertEqual(value['status'],'ATTRIBUTION_INPUT_INSUFFICIENT')
    self.assertFalse(value['attribution_complete'])
    self.assertEqual(value['array_decodes'],0)

  def test_resume_output_overlap_reject(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    with self.assertRaisesRegex(ValueError,'OVERLAP'):
      a.run(Path('/tmp/s2ri-fit/repeat-1'), Path('/tmp/s2ri-fit/repeat-1/attribution'))

  def test_missing_array_decode_cannot_fallback(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    import numpy as np
    with patch.object(np,'load',side_effect=AssertionError('NO_ARRAY_DECODE')):
      result=a.availability({'one_step_buffers':{'prediction':'a'*64,'projected':'b'*64},
        'rollout_buffers':{}})
    self.assertEqual(result['status'],'ATTRIBUTION_INPUT_INSUFFICIENT')

  def test_no_public_rows(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution_publication as pub
    value=pub.unavailable('error-decomposition',p.seal({'status':'ATTRIBUTION_INPUT_INSUFFICIENT',
      'input_manifest_sha256':'a'*64, 'private_path':'DO_NOT_COPY', 'raw_predictions':[1,2,3]}))
    text=json.dumps(value)
    self.assertNotIn('DO_NOT_COPY',text)
    self.assertNotIn('raw_predictions',text)


class TestReviewRegressions(unittest.TestCase):
  def test_stale_bundle_rejected_before_publication(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution_publication as pub
    jobs=[{'candidate_id':c,'fold':f,'private_path':'NEVER_PUBLISH'}
          for c in a.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    audit=p.seal({'schema':'WRONG_SCHEMA','input_manifest_sha256':a.INPUT_SHA,'job_count':32,
      'numerical_attribution':'NOT_RUN','array_decodes':0,'status':'ATTRIBUTION_INPUT_INSUFFICIENT',
      'jobs':jobs,'historical_failure_counts':{},'input_files_verified':0,
      'input_bytes_unchanged':False,'input_files_sha256':'a'*64})
    manifest=p.seal({'schema':'WRONG_SCHEMA','files':{},'audit_sha256':audit['receipt_sha256']})
    resume=p.seal({'manifest_sha256':manifest['receipt_sha256'],
      'source_reinspection_trapped':True,'array_decode_trapped':True})
    with patch.object(a,'resume',return_value=manifest), patch.object(a,'read_json',
      side_effect=lambda path:resume if path.name=='resume-verification.json' else audit):
      with self.assertRaises(ValueError):
        pub.build(Path('/tmp/stale-bundle'),manifest['receipt_sha256'])

  def test_public_job_ignores_untrusted_extensions(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution_publication as pub
    historical=a.public_inputs()['fit-cv-results']['jobs'][0]
    job={'candidate_id':historical['candidate_id'],'fold':historical['fold'],
      'job_receipt_sha256':historical['receipt_sha256'],
      'model_receipt_sha256':historical['model_receipt_sha256'],
      'normalizer_receipt_sha256':historical['normalizer_receipt_sha256'],
      'one_step_array_sha256':dict.fromkeys(('prediction','projected','error','comparator_error'),'a'*64),
      'rollout_array_sha256':{str(h):dict.fromkeys(('projected','error','comparator_error'),'b'*64) for h in a.HORIZONS},
      'one_step_anchor_sha256':historical['one_step']['anchor_sha256'],
      'rollout_anchor_sha256':{h:v['anchor_sha256'] for h,v in historical['rollout'].items()},
      'candidate_comparator_anchors_equal':True,
      'private_path':'NEVER_PUBLISH',
      'availability':{'private_path':'NEVER_PUBLISH'}}
    value=pub.public_job(job,historical)
    self.assertNotIn('NEVER_PUBLISH',json.dumps(value))
    bad=copy.deepcopy(job)
    bad['one_step_array_sha256']['prediction']='private-path'
    with self.assertRaises(ValueError):
      pub.public_job(bad,historical)

  def test_expected_audit_manifest_pin_required(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution_publication as pub
    with self.assertRaises(ValueError):
      pub.build(Path('/tmp/not-read'),'not-a-sha')


class TestSavedEvidenceInvariants(unittest.TestCase):
  def test_valid_saved_identity_then_semantic_drift(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    with tempfile.TemporaryDirectory() as name:
      root=Path(name)
      audit=p.seal({
        'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_INPUT_AUDIT_V1',
        'policy_sha256':a.policy()['receipt_sha256'],'executor_sha256':a.digest_file(Path(a.__file__)),
        'input_manifest_sha256':a.INPUT_SHA,'input_files_verified':834,'job_count':32,
        'input_bytes_unchanged':True,'input_files_sha256':'b'*64,'input_files_after_sha256':'b'*64,
        'historical_failure_counts':a.EXPECTED_FAILURES,'status':'ATTRIBUTION_INPUT_INSUFFICIENT',
        'numerical_attribution':'NOT_RUN','array_decodes':0,'new_fit_calls':0,'prediction_generations':0,
        'rollout_generations':0,'candidate_selection_calls':0,
        'jobs':[{'candidate_id':c,'fold':f} for c in a.CANDIDATES for f in ('FOLD_A','FOLD_B')],
      })
      a.write(root/'policy.json',a.policy())
      a.write(root/'audit.json',audit)
      fields={'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_MANIFEST_V1',
        'policy_sha256':a.policy()['receipt_sha256'],'executor_sha256':a.digest_file(Path(a.__file__)),
        'input_manifest_sha256':a.INPUT_SHA,'status':'ATTRIBUTION_INPUT_INSUFFICIENT',
        'audit_sha256':audit['receipt_sha256']}
      a.finish(root,['audit.json','policy.json'],fields)
      self.assertEqual(a.verified_saved(root)[1],audit)
      for field,value in (('input_bytes_unchanged',False),('input_files_after_sha256','c'*64),
                          ('array_decodes',1),('new_fit_calls',1),('prediction_generations',1),
                          ('rollout_generations',1),('candidate_selection_calls',1),
                          ('input_files_verified',0),('historical_failure_counts',{})):
        with self.subTest(field=field):
          modified=p.seal({k:v for k,v in {**audit,field:value}.items() if k!='receipt_sha256'})
          # In-memory test of a fully resealed semantic lie, not source mutation.
          manifest=a.resume(root)
          manifest=p.seal({k:v for k,v in {**manifest,'audit_sha256':modified['receipt_sha256']}.items() if k!='receipt_sha256'})
          with patch.object(a,'resume',return_value=manifest),patch.object(a,'read_json',
              side_effect=lambda path, value=modified:a.policy() if path.name=='policy.json' else value):
            with self.assertRaisesRegex(ValueError,'EVIDENCE_CONFLICT'):
              a.verified_saved(root)


class TestOutputBoundary(unittest.TestCase):
  def test_output_cannot_target_unrelated_store(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    with patch.object(a,'inspect_store',side_effect=AssertionError('SOURCE_MUST_NOT_OPEN')):
      with self.assertRaisesRegex(ValueError,'OUTPUT_LAYOUT'):
        a.run(Path('/tmp/owner/empirical-s2-ri-retrospective-fit-cv-v1/repeat-1'),
              Path('/tmp/owner/causal-store/other'))

  def test_no_private_literal_in_code(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a
    from tools.cyberpilot.check_publication import scan_text
    self.assertEqual(scan_text('module.py',Path(a.__file__).read_text()),())
