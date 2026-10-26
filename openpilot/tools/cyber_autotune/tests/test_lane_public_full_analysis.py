import unittest
from openpilot.tools.cyber_autotune import lane_public_full_analysis as a
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune.native_protocol import digest


def fixture():
  rows = []
  for i in range(2):
    row = {
      'ordinal': i,
      'frame_status': 'COMPLETED',
      'run_sha256': digest(b'run'),
      'ledger': seal(
        {
          'frame_id': f'imgs/{i}.png',
          'gt_components': i,
          'raw_prediction_count': i,
          'failure_category': 'NO_LARGE_ROW_TAIL',
          'row_tail_points': i,
          'coverage': 0.5,
        }
      ),
      'pool': {'pred': [0.0, 10.0] if i == 0 else [20.0, 30.0], 'gt': [2.0, 4.0], 'paired_spatial_pred': [1.0, 3.0]},
      'regions': {
        k: {
          'gt_runs': 1,
          'covered_runs': 1,
          'pred_points': 1,
          'unsupported_points': 0,
          'off_mask_points': 0,
          'missed_runs': 0,
          'pred': [float(i)],
          'gt': [float(i)],
        }
        for k in ('far', 'mid', 'near')
      },
    }
    rows.append(seal(row))
  marker = seal({'storage_status': 'COMPLETED', 'processed': 2, 'expected': 2, 'run_sha256': digest(b'run'), 'reference_promotable': False})
  return rows, marker


class TestLanePublicFullAnalysis(unittest.TestCase):
  def test_pooled_not_average_of_frame_percentiles(self):
    rows, m = fixture()
    result = a.analyze(rows, m)
    self.assertEqual(result['directions']['pred']['median'], 15.0)
    self.assertAlmostEqual(result['directions']['pred']['p95'], 28.5)
    self.assertEqual(result['directions']['pred']['p50'], 15.0)
    self.assertFalse(result['reference_promotable'])

  def test_partial_rejected(self):
    rows, m = fixture()
    with self.assertRaises(ValueError):
      a.analyze(rows[:1], m)

  def test_duplicate_ordinal_rejected(self):
    rows, m = fixture()
    rows[1] = rows[0]
    with self.assertRaises(ValueError):
      a.analyze(rows, m)

  def test_run_identity_drift_rejected(self):
    rows, m = fixture()
    x = {k: v for k, v in rows[0].items() if k != 'receipt_sha256'}
    x['run_sha256'] = 'f' * 64
    rows[0] = seal(x)
    with self.assertRaises(ValueError):
      a.analyze(rows, m)

  def test_failed_row_rejected(self):
    rows, m = fixture()
    x = {k: v for k, v in rows[0].items() if k != 'receipt_sha256'}
    x['frame_status'] = 'DETECTOR_FAILED'
    rows[0] = seal(x)
    with self.assertRaises(ValueError):
      a.analyze(rows, m)

  def test_count_buckets_cover_without_overlap(self):
    rows, m = fixture()
    result = a.analyze(rows, m)
    for values in result['count_buckets'].values():
      self.assertEqual(sum(v['frame_count'] for v in values), 2)
    self.assertEqual(result['regions']['far']['pred_to_gt']['sample_count'], 2)

  def test_bucket_boundaries(self):
    bins = [[0, 0], [1, 7], [8, 31], [32, None]]
    self.assertEqual([a.count_bucket(i, bins) for i in (0, 1, 7, 8, 31, 32, 100)], [0, 1, 1, 2, 2, 3, 3])
    for i in (-1, True, 1.5):
      with self.assertRaises(ValueError):
        a.count_bucket(i, bins)

  def test_empty_distances_preserved(self):
    rows, m = fixture()
    for i, row in enumerate(rows):
      x = {k: v for k, v in row.items() if k != 'receipt_sha256'}
      x['pool'] = {k: [] for k in x['pool']}
      rows[i] = seal(x)
    result = a.analyze(rows, m)
    self.assertIsNone(result['directions']['pred']['p95'])
    self.assertEqual(result['directions']['pred']['sample_count'], 0)

  def test_nonfinite_failure(self):
    rows, m = fixture()
    x = {k: v for k, v in rows[0].items() if k != 'receipt_sha256'}
    x['pool']['pred'] = [-1.0]
    rows[0] = seal(x)
    with self.assertRaises(ValueError):
      a.analyze(rows, m)

  def test_subset_stays_diagnostic(self):
    rows, m = fixture()
    full = a.analyze(rows, m)
    result = a.subset_comparison(full, full)
    self.assertEqual(result['scope'], 'DIAGNOSTIC_SUBSET_NOT_QUALIFICATION')
    self.assertEqual(result['direction_deltas']['pred']['p95'], 0)
    self.assertFalse(result['qualification_granted'])

  def test_historical_subset_protocol_binding(self):
    from pathlib import Path

    path = Path(a.__file__).resolve().parents[3] / 'docs/cyberpilot/changes/public-lane-detector-diagnostic-protocol.json'
    value = a.historical_subset_protocol(path.read_bytes())
    self.assertEqual(len(value['pairs']), 119)
    with self.assertRaises(ValueError):
      a.historical_subset_protocol(b'{}')

  def test_failure_coverage_and_y_frame_denominators(self):
    rows, m = fixture()
    result = a.analyze(rows, m)
    self.assertEqual(result['coverage']['gt_eligible_frames'], 1)
    self.assertEqual(result['coverage']['detection_failure_rate'], 0.0)
    self.assertEqual(result['regions']['mid']['frame_count'], 2)
    self.assertEqual(result['regions']['mid']['unavailable_frames'], 0)
    self.assertEqual(result['coverage']['off_mask_prediction_ratio'], 0.0)

  def test_no_gt_failure_rate_is_unavailable(self):
    rows, m = fixture()
    x = {k: v for k, v in rows[1].items() if k != 'receipt_sha256'}
    entry = {k: v for k, v in x['ledger'].items() if k != 'receipt_sha256'}
    entry['gt_components'] = 0
    x['ledger'] = seal(entry)
    rows[1] = seal(x)
    result = a.analyze(rows, m)
    self.assertIsNone(result['coverage']['detection_failure_rate'])
