"""Synthetic arrays and temporary stores only; no actual saved scientific input."""

import copy
import gzip
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_evidence as b1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_train_score as train
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_b1_train_score import train_fixture

try:
  c = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_c_diagnostics')
  m = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_c_math')
except ModuleNotFoundError:
  c = m = None


def raw_array(values, dtype):
  stream = io.BytesIO()
  np.save(stream, np.array(values, dtype=dtype), allow_pickle=False)
  npy = stream.getvalue()
  raw = gzip.compress(npy, mtime=0)
  desc = {
    'dtype': dtype,
    'shape': [len(values)],
    'order': 'C',
    'array_sha256': b1.sha(npy[-len(values) * np.dtype(dtype).itemsize :]),
    'file_sha256': b1.sha(raw),
    'npy_sha256': b1.sha(npy),
    'filename': 'p_move.npy.gz',
    'storage_format': 'NPY_GZIP_V1',
    'lossless_roundtrip_verified': True,
  }
  return raw, desc


class MathTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(m, 'C metric implementation missing')
    self.p = np.array([0.1, 0.8, 0.7, 0.9], dtype='<f8')
    self.y = np.array([False, True, False, True])
    self.z = np.array([0, 0, 1, -2], dtype='<i8')
    self.g = np.array([False, False, True, True])

  def analyze(self, **kw):
    return m.analyze(kw.get('p', self.p), kw.get('y', self.y), kw.get('z', self.z), gate=kw.get('g', self.g))

  def test_four_populations_disjoint_exhaustive(self):
    row = self.analyze()
    self.assertEqual(row['support'], {'OVERALL': 4, 'STATIC_HOLD': 1, 'MOVE_ONSET': 1, 'MOVE_TERMINATION': 1, 'MOVE_CONTINUATION': 1})

  def test_previous_state_is_nonzero_source_grid_delta(self):
    self.assertEqual(self.analyze()['scores']['PREVIOUS_MOVE']['n'], 2)

  def test_confusion_and_transition_rates(self):
    row = self.analyze()
    self.assertEqual(row['gates']['OVERALL']['counts'], {'TP': 1, 'FP': 1, 'TN': 1, 'FN': 1})
    self.assertEqual(row['transitions']['MOVE_ONSET']['rate'], 0)
    self.assertEqual(row['transitions']['MOVE_TERMINATION']['rate'], 1)
    self.assertEqual(row['transitions']['MOVE_CONTINUATION']['rate'], 1)

  def test_zero_denominator_not_identifiable(self):
    row = m.confusion(np.zeros(2, dtype=bool), np.zeros(2, dtype=bool))
    self.assertIsNone(row['recall'])
    self.assertEqual(row['status']['recall'], 'NOT_IDENTIFIABLE')

  def test_auc_exact_ties(self):
    row = m.auc(np.array([0.2, 0.2, 0.8, 0.8]), self.y)
    self.assertEqual((row['numerator'], row['denominator'], row['value']), (4, 8, 0.5))

  def test_auc_perfect_and_reversed(self):
    for p, value in (([0.0, 0.8, 0.1, 1.0], 1), ([1.0, 0.1, 0.8, 0.0], 0)):
      self.assertEqual(m.auc(np.array(p), self.y)['value'], value)

  def test_auc_constant(self):
    self.assertEqual(m.auc(np.ones(4), self.y)['value'], 0.5)

  def test_auc_missing_class(self):
    self.assertEqual(m.auc(self.p, np.zeros(4, dtype=bool))['status'], 'NOT_IDENTIFIABLE')

  def test_empty_population(self):
    row = m.score_metrics(np.array([], dtype='<f8'), np.array([], dtype=bool))
    self.assertIsNone(row['mean_probability'])
    self.assertEqual(row['n'], 0)

  def test_brier_and_calibration(self):
    row = self.analyze()['scores']['OVERALL']
    self.assertAlmostEqual(row['brier'], (0.01 + 0.04 + 0.49 + 0.01) / 4)
    self.assertAlmostEqual(row['calibration_bias'], 0.625 - 0.5)

  def test_fixed_bins_boundaries_zero_one(self):
    p = np.array([i / 10 for i in range(11)], dtype='<f8')
    bins = m.score_metrics(p, np.zeros(11, dtype=bool))['reliability']
    self.assertEqual([r['count'] for r in bins], [1] * 9 + [2])
    self.assertEqual(bins[-1]['mean_probability'], 0.95)

  def test_nan_inf_out_of_range_rejected(self):
    for value in (float('nan'), float('inf'), -0.01, 1.01):
      with self.subTest(value=str(value)), self.assertRaises(ValueError):
        self.analyze(p=np.array([value, 0.2, 0.3, 0.4]))

  def test_invalid_truth_gate_prior_dtype_rejected(self):
    for kw in ({'y': self.y.astype('i8')}, {'g': self.g.astype('i8')}, {'z': self.z.astype('f8')}, {'p': self.p.astype('f4')}):
      with self.subTest(field=next(iter(kw))), self.assertRaises(ValueError):
        self.analyze(**kw)

  def test_shape_alignment_no_truncation(self):
    with self.assertRaises(ValueError):
      self.analyze(g=self.g[:-1])

  def test_train_gate_not_reconstructed(self):
    row = m.analyze(self.p, self.y, self.z)
    self.assertIsNone(row['gates'])
    self.assertIsNone(row['transitions'])

  def test_train_dev_different_n_is_valid_same_job(self):
    a = m.analyze(self.p, self.y, self.z)
    b = m.analyze(self.p[:3], self.y[:3], self.z[:3], gate=self.g[:3])
    self.assertAlmostEqual(m.transfer(a, b)['OVERALL']['prevalence'], 1 / 3 - 1 / 2)

  def test_deterministic_json(self):
    self.assertEqual(b1.b0._canonical(self.analyze()), b1.b0._canonical(self.analyze()))


class DecoderTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(c, 'C reader missing')

  def test_decode_readonly_numeric(self):
    raw, desc = raw_array([0, 0.2, 1], '<f8')
    row = c.decode(raw, desc, 3, '<f8')
    self.assertFalse(row.flags.writeable)
    self.assertEqual(row.tolist(), [0, 0.2, 1])

  def test_hash_conflict(self):
    raw, desc = raw_array([0.2], '<f8')
    desc['array_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      c.decode(raw, desc, 1, '<f8')

  def test_noncanonical_bool_byte_rejected_before_bool_coercion(self):
    raw, desc = raw_array([True], '|b1')
    npy = gzip.decompress(raw)[:-1] + b'\x02'
    raw = gzip.compress(npy, mtime=0)
    desc.update(file_sha256=b1.sha(raw), npy_sha256=b1.sha(npy), array_sha256=b1.sha(b'\x02'))
    with self.assertRaises(ValueError):
      c.decode(raw, desc, 1, '|b1')

  def test_gzip_bomb_truncated_multimember_trailing(self):
    raw, desc = raw_array([0.2], '<f8')
    for bad in (raw[:-1], raw + gzip.compress(b'x'), raw + b'x', gzip.compress(bytes(200000))):
      d = {**desc, 'file_sha256': b1.sha(bad)}
      with self.subTest(hash=b1.sha(bad)), self.assertRaises(ValueError):
        c.decode(bad, d, 1, '<f8')

  def test_object_dtype_and_wrong_shape_forbidden(self):
    raw, desc = raw_array([0.2], '<f8')
    for dtype, count in (('|O', 1), ('<f8', 2)):
      with self.subTest(dtype=dtype, count=count), self.assertRaises(ValueError):
        c.decode(raw, desc, count, dtype)


class StoreTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    if c is None:
      return
    cls.tmp = tempfile.TemporaryDirectory()
    cls.root = Path(cls.tmp.name)
    request, cls.previous = train_fixture(cls.root)
    binding = b1.sealed({'schema': 'CYBERPILOT_V4_B1_TRAIN_PRIVATE_BINDING_V1', 'request': {k: v for k, v in request.items() if k != 'binding_sha256'}})
    request['binding_sha256'] = binding['receipt_sha256']
    result = train.run(request, cls.previous)
    resume = train.verify_only(result, b1.sha(b1.b0._canonical(result)), binding['receipt_sha256'])
    cls.completion = {'binding': binding, 'result': result, 'resume': resume}

  @classmethod
  def tearDownClass(cls):
    if c is not None:
      cls.tmp.cleanup()

  def setUp(self):
    self.assertIsNotNone(c, 'C reader missing')

  def test_lineage_all224_inputs_repeat1_only(self):
    jobs = c.inputs(self.previous, self.completion)
    self.assertEqual(len(jobs), 32)
    self.assertEqual(sum(len(j['fields']) for j in jobs), 224)
    for job in jobs:
      self.assertTrue(all('repeat-2/' not in v['path'] for v in job['fields']))
      self.assertEqual([v['field'] for v in job['fields']], [v[2] for v in b1.FIELDS])

  def test_wrong_anchor_candidate_fold_or_order(self):
    for key, value in (('train_anchor', '0' * 64), ('candidate_id', 'OTHER'), ('fold', 'OTHER')):
      completion = copy.deepcopy(self.completion)
      completion['binding']['request']['jobs'][0][key] = value
      completion['binding'] = b1.sealed({k: v for k, v in completion['binding'].items() if k != 'receipt_sha256'})
      with self.subTest(key=key), self.assertRaises(ValueError):
        c.inputs(self.previous, completion)

  def test_same_length_wrong_order_not_accepted(self):
    completion = copy.deepcopy(self.completion)
    completion['result']['fields'][0]['replicas'][0]['row_alignment'] = 'LENGTH_ONLY'
    completion['result'] = b1.sealed({k: v for k, v in completion['result'].items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      c.inputs(self.previous, completion)

  def test_run_224_reads_no_metadata_or_second_replica(self):
    req = {
      'authorized': True,
      'binding_sha256': 'a' * 64,
      'protocol_sha256': 'b' * 64,
      'mount_root': str(self.root),
      'mount_identity': (self.root.stat().st_dev, self.root.stat().st_ino),
    }
    row = c.run(req, self.previous, self.completion)
    self.assertEqual(row['status'], 'C_DIAGNOSTIC_AGGREGATION_COMPLETE')
    self.assertEqual(row['reads']['array_file_openings'], 224)
    self.assertEqual(row['reads']['metadata_file_openings'], 0)
    self.assertEqual(len(row['jobs']), 32)
    self.assertEqual(row['authorized_C_aggregation_calls'], 32)
    self.assertEqual(row['train_rowwise_gate'], 'NOT_SAVED')

  def test_current_grant_required(self):
    row = c.run({'authorized': False}, self.previous, self.completion)
    self.assertNotEqual(row['status'], 'C_DIAGNOSTIC_AGGREGATION_COMPLETE')
    self.assertEqual(row['reads']['array_file_openings'], 0)

  def test_alias_member_not_accepted(self):
    jobs = c.inputs(self.previous, self.completion)
    jobs[1]['fields'][0]['path'] = jobs[0]['fields'][0]['path']
    # GuardedReader rejects a second read of the exact target; no fallback.
    allow = {v['path']: (v['cap'], 'array') for j in jobs for v in j['fields']}
    with b1.GuardedReader(str(self.root), (self.root.stat().st_dev, self.root.stat().st_ino), allow) as reader:
      field = jobs[0]['fields'][0]
      reader.read(field['path'], field['cap'], 'array')
      with self.assertRaises(ValueError):
        reader.read(field['path'], field['cap'], 'array')

  def test_no_unapproved_metadata_read(self):
    jobs = c.inputs(self.previous, self.completion)
    allow = {v['path']: (v['cap'], 'array') for j in jobs for v in j['fields']}
    with b1.GuardedReader(str(self.root), (self.root.stat().st_dev, self.root.stat().st_ino), allow) as reader:
      with self.assertRaises(ValueError):
        reader.read(str(self.root / 'train/receipt.json'), 65536, 'metadata')
      self.assertEqual(reader.counters['metadata_file_openings'], 0)

  def test_resume_without_source_or_aggregation(self):
    req = {
      'authorized': True,
      'binding_sha256': 'a' * 64,
      'protocol_sha256': 'b' * 64,
      'mount_root': str(self.root),
      'mount_identity': (self.root.stat().st_dev, self.root.stat().st_ino),
    }
    report = c.run(req, self.previous, self.completion)
    with (
      patch.object(b1.GuardedReader, 'read', side_effect=AssertionError('source reopened')),
      patch.object(c, 'run', side_effect=AssertionError('run')),
      patch.object(m, 'analyze', side_effect=AssertionError('recompute')),
      patch.object(m, 'public_folds', side_effect=AssertionError('aggregate')),
    ):
      resume = c.verify_only(report, b1.sha(b1.b0._canonical(report)), 'a' * 64)
    self.assertEqual(resume['recompute_calls'], 0)
    self.assertEqual(resume['source_file_openings'], 0)

  def test_resume_wrong_digest_rejected(self):
    with self.assertRaises(ValueError):
      c.verify_only({}, '0' * 64, 'a' * 64)

  def test_mount_change_rejected(self):
    jobs = c.inputs(self.previous, self.completion)
    allow = {v['path']: (v['cap'], 'array') for j in jobs for v in j['fields']}
    with self.assertRaises(ValueError):
      b1.GuardedReader(str(self.root), (0, 0), allow)

  def test_no_model_threshold_or_mixed_receipt_code(self):
    source = Path(c.__file__).read_text()
    for forbidden in ('train/receipt.json', 'predict_delta(', 'select_threshold(', 'np.load(', 'pickle', 'rglob(', 'glob(', 'scandir(', 'listdir('):
      self.assertNotIn(forbidden, source)


class PublicationTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(m, 'C math missing')

  def test_privacy_rule_complementary_and_zero(self):
    self.assertFalse(m.cell_safe(201, 1))
    self.assertFalse(m.cell_safe(402, 202))
    self.assertTrue(m.cell_safe(402, 201))
    self.assertTrue(m.cell_safe(201, 0))

  def test_all_bins_and_counts_never_public(self):
    a = np.array([0.1, 0.9] * 402, dtype='<f8')
    y = np.array([False, True] * 402)
    z = np.array([0, 0, 1, 1] * 201, dtype='<i8')
    trainrow = m.analyze(a, y, z)
    dev = m.analyze(a, y, z, gate=y)
    jobs = [{'candidate_id': j[0], 'fold': j[1], 'TRAIN': trainrow, 'DEV': dev, 'transfer': m.transfer(trainrow, dev)} for j in b1.JOBS]
    row = m.public_folds(jobs)
    text = json.dumps(row)
    for forbidden in ('reliability', 'candidate_id', 'anchor', 'count', 'probabilities', 'threshold'):
      self.assertNotIn(forbidden, text)
    self.assertEqual(row['FOLD_A']['DEV']['transitions']['MOVE_ONSET']['median'], 1)

  def test_small_cell_suppresses_entire_metric_family(self):
    a = np.array([0.1, 0.9] * 202, dtype='<f8')
    y = np.array([False, True] * 202)
    z = np.array([0, 0, 1, 1] * 101, dtype='<i8')
    tr = m.analyze(a, y, z)
    dev = m.analyze(a, y, z, gate=y)
    jobs = [{'candidate_id': j[0], 'fold': j[1], 'TRAIN': tr, 'DEV': dev, 'transfer': m.transfer(tr, dev)} for j in b1.JOBS]
    self.assertEqual(m.public_folds(jobs)['FOLD_A']['DEV']['transitions']['MOVE_ONSET']['status'], 'SUPPRESSED_PRIVACY')

  def test_private_strings_cannot_enter_numeric_summary(self):
    with self.assertRaises(ValueError):
      m.summary(['/private/unpublishable'])

  def test_no_unapproved_extra_metric(self):
    self.assertEqual(m.TRANSFER_METRICS, ('auc', 'brier', 'calibration_bias', 'prevalence'))
    self.assertEqual(m.PUBLIC_MIN_SUPPORT, 201)
    self.assertEqual(len(m.EDGES), 11)

  def test_companion_contexts_cannot_reconstruct_hidden_class(self):
    # Static support202 has one positive. Overall/move supports pass in isolation.
    # Identical jobs make released min/median/max exact; prior public Ns would
    # permit subtraction unless the entire score/transfer family is hidden.
    y = np.array([True] + [False] * 201 + [True] * 201 + [False] * 402)
    z = np.array([0] * 202 + [1] * 603, dtype='<i8')
    p = np.full(805, 0.5, dtype='<f8')
    tr, dev = m.analyze(p, y, z), m.analyze(p, y, z, gate=y)
    jobs = [{'candidate_id': a, 'fold': b, 'TRAIN': tr, 'DEV': dev, 'transfer': m.transfer(tr, dev)} for a, b in b1.JOBS]
    row = m.public_folds(jobs)
    for fold in ('FOLD_A', 'FOLD_B'):
      for context in m.CONTEXTS:
        self.assertEqual(row[fold]['TRAIN']['scores'][context]['prevalence']['status'], 'SUPPRESSED_PRIVACY')
        self.assertEqual(row[fold]['transfer'][context]['prevalence']['status'], 'SUPPRESSED_PRIVACY')


if __name__ == '__main__':
  unittest.main()
