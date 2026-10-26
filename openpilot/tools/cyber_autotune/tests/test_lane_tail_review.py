import unittest
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import digest, canonical

SHA = digest(b'public test identity')


def fixture(n=20):
  rows = []
  for i in range(n):
    dist = {'sample_count': 1, 'median': float(i), 'p90': float(i), 'p95': float(i), 'p99': float(i), 'maximum': float(i)}
    rows.append(
      seal(
        {
          'frame_id': f'imgs/{i:04d}.png',
          'image_sha256': SHA,
          'gt_mask_sha256': SHA,
          'detector_result_sha256': SHA,
          'raw_prediction_count': 0 if i == 0 else 4,
          'gt_components': i,
          'missed_gt_components': i,
          'row_tail_still_spatially_remote_points': i,
          'pred_to_gt': dist,
          'gt_to_pred': dist,
          'regions': {k: {'pred_to_gt': dist} for k in ('far', 'mid', 'near')},
          'confidence': {'median': 0.8},
        }
      )
    )
  marker = seal(
    {
      'storage_status': 'COMPLETED',
      'processed': n,
      'expected': n,
      'run_sha256': SHA,
      'reference_promotable': False,
      'artifact_file_sha256': {'ledger.json': digest(canonical(rows) + b'\n')},
    }
  )
  return rows, marker


def manifest():
  rows, marker = fixture()
  return c.freeze_review(rows, marker, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')


def annotation(m=None):
  m = m or manifest()
  return c.make_annotation(
    m, m['frames'][0]['frame_id'], label='UNRESOLVED', reviewable=True, comment='test', timestamp='2026-10-07T12:00:00Z', human_ack=True, tool_sha256=SHA
  )


class TestLaneTailReview(unittest.TestCase):
  def test_policy_is_immutable(self):
    p = c.selection_policy()
    self.assertEqual(p['receipt_sha256'], 'ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54')
    x = unseal(p)
    x['per_stratum_limit'] = 5
    with self.assertRaises(ValueError):
      c.freeze_review(*fixture(), seal(x), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')

  def test_selection_deterministic_and_bounded(self):
    rows, marker = fixture()
    a = c.freeze_review(rows, marker, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')
    self.assertEqual(a, c.freeze_review(list(reversed(rows)), marker, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION'))
    self.assertLessEqual(len(a['frames']), 40)
    for name in c.selection_policy()['strata']:
      self.assertLessEqual(sum(name in f['reasons'] for f in a['frames']), 4)
    self.assertEqual(len({f['frame_id'] for f in a['frames']}), len(a['frames']))

  def test_partial_cannot_freeze(self):
    rows, m = fixture()
    x = unseal(m)
    x['processed'] -= 1
    with self.assertRaises(ValueError):
      c.freeze_review(rows, seal(x), c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')

  def test_public_requires_exact_full_population(self):
    with self.assertRaises(ValueError):
      c.freeze_review(*fixture(), c.selection_policy(), SHA)

  def test_duplicate_ledger_rejected(self):
    rows, m = fixture()
    rows[-1] = rows[0]
    with self.assertRaises(ValueError):
      c.freeze_review(rows, m, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')

  def test_unsealed_row_rejected(self):
    rows, m = fixture()
    rows[0]['image_sha256'] = 'f' * 64
    with self.assertRaises(ValueError):
      c.freeze_review(rows, m, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')

  def test_missing_rows_rejected(self):
    rows, m = fixture()
    with self.assertRaises(ValueError):
      c.freeze_review(rows[:-1], m, c.selection_policy(), SHA, scope='TEST_ONLY_BROWSER_VALIDATION')

  def test_rank_strata(self):
    m = manifest()
    self.assertEqual([f['frame_id'] for f in m['frames'] if 'EXTREME_TAIL' in f['reasons']], [f'imgs/{i:04d}.png' for i in range(16, 20)])
    self.assertEqual([f['frame_id'] for f in m['frames'] if 'P95_NEIGHBORHOOD' in f['reasons']], [f'imgs/{i:04d}.png' for i in range(16, 20)])

  def test_no_automatic_causal_label(self):
    m = manifest()
    self.assertEqual(c.review_status(m, [])['status'], 'TAIL_HUMAN_REVIEW_PENDING')
    self.assertFalse(any('reviewer_label' in f for f in m['frames']))

  def test_human_ack_required(self):
    m = manifest()
    with self.assertRaises(ValueError):
      c.make_annotation(
        m, m['frames'][0]['frame_id'], label='DETECTOR_MISS', reviewable=True, comment='', timestamp='2026-10-07T12:00:00Z', human_ack=False, tool_sha256=SHA
      )

  def test_annotation_exact_binding(self):
    m = manifest()
    a = annotation(m)
    c.validate_annotation(m, a)
    for key in ('image_sha256', 'prediction_sha256', 'metric_result_sha256', 'review_manifest_sha256', 'review_tool_sha256'):
      x = unseal(a)
      x[key] = 'f' * 64
      with self.subTest(key=key), self.assertRaises(ValueError):
        c.validate_annotation(m, seal(x))

  def test_malformed_label_and_timestamp_fail(self):
    m = manifest()
    for label, stamp in [('LANE_CENTER_QUALIFIED', '2026-10-07T12:00:00Z'), ('OTHER', 'yesterday')]:
      with self.assertRaises(ValueError):
        c.make_annotation(m, m['frames'][0]['frame_id'], label=label, reviewable=True, comment='', timestamp=stamp, human_ack=True, tool_sha256=SHA)

  def test_tool_drift_rejected(self):
    m = manifest()
    with self.assertRaises(ValueError):
      c.make_annotation(
        m, m['frames'][0]['frame_id'], label='OTHER', reviewable=True, comment='', timestamp='2026-10-07T12:00:00Z', human_ack=True, tool_sha256='f' * 64
      )

  def test_test_annotations_never_human_evidence(self):
    m = manifest()
    rows = [
      c.make_annotation(
        m, f['frame_id'], label='DETECTOR_MISS', reviewable=True, comment='test', timestamp='2026-10-07T12:00:00Z', human_ack=True, tool_sha256=SHA
      )
      for f in m['frames']
    ]
    result = c.review_status(m, rows)
    self.assertEqual(result['status'], 'TEST_ONLY_NOT_HUMAN_EVIDENCE')
    self.assertFalse(result['reference_promotable'])

  def test_duplicate_annotation_rejected(self):
    m = manifest()
    a = annotation(m)
    with self.assertRaises(ValueError):
      c.review_status(m, [a, a])

  def test_unreviewable_requires_unresolved(self):
    m = manifest()
    with self.assertRaises(ValueError):
      c.make_annotation(
        m, m['frames'][0]['frame_id'], label='DETECTOR_MISS', reviewable=False, comment='', timestamp='2026-10-07T12:00:00Z', human_ack=True, tool_sha256=SHA
      )
