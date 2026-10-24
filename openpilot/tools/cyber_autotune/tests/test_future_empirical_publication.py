"""Public contracts and manual synthetic workflow."""

import copy
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_contracts as c
from openpilot.tools.cyber_autotune import future_empirical_admission as a
from openpilot.tools.cyber_autotune import future_empirical_cli as cli
from openpilot.tools.cyber_autotune import future_empirical_publication as pub
from openpilot.tools.cyber_autotune.tests.test_future_empirical_data import SyntheticHistory, metadata, history


class TestFuturePublication(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows = c.artifacts()

  def test_seven_published_contracts(self):
    self.assertEqual(pub.load(), self.rows)

  def test_numeric_authority_cannot_promote(self):
    rows = copy.deepcopy(self.rows)
    name = c.NAMES[0]
    rows[name]['numeric_extraction_allowed'] = True
    rows[name] = p.seal({k: v for k, v in rows[name].items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_holdout_cannot_open(self):
    rows = copy.deepcopy(self.rows)
    name = c.NAMES[4]
    rows[name]['opening_allowed'] = True
    rows[name] = p.seal({k: v for k, v in rows[name].items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_private_values_cannot_publish(self):
    rows = copy.deepcopy(self.rows)
    name = c.NAMES[-1]
    rows[name]['raw_signals'] = [1.0, 2.0]
    rows[name] = p.seal({k: v for k, v in rows[name].items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_no_background_automation(self):
    self.assertFalse(self.rows[c.NAMES[0]]['background_automation_allowed'])

  def test_no_model_selection(self):
    self.assertEqual(self.rows[c.NAMES[5]]['selection'], 'NOT_RUN')
    self.assertFalse(self.rows[c.NAMES[5]]['implementation_allowed'])

  def test_calibration_unchanged(self):
    self.assertEqual(self.rows[c.NAMES[-1]]['calibration_blockers'], p.BLOCKERS)

  def test_no_ta_sg_production(self):
    for row in self.rows.values():
      for key, value in p.FIREWALL.items():
        self.assertIs(row[key], value)

  def test_source_snapshot_mutation_not_cached(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)
      row = p.seal({'schema': 'SYNTHETIC', 'value': 1})
      (path / 'x.json').write_text(json.dumps(row))
      with patch.object(p, 'PUBLIC', path):
        self.assertEqual(c.read('x.json')['value'], 1)
        (path / 'x.json').write_text(json.dumps({**row, 'value': 2}))
        with self.assertRaises(ValueError):
          c.read('x.json')

  def test_future_only_base_preserved(self):
    self.assertFalse(self.rows[c.NAMES[1]]['historical_regeneration_allowed'])
    self.assertEqual(c.read('empirical-causal-context-schema-v1.json')['historical_steering_rate'], 'UNAVAILABLE_NOT_PRESERVED')


class TestFutureManualCLI(SyntheticHistory, unittest.TestCase):
  def test_explicit_args_required(self):
    with self.assertRaises(SystemExit):
      cli.main(['inspect'])

  def test_raw_reader_exception_manual_metadata_success(self):
    with tempfile.TemporaryDirectory() as tmp:
      store = Path(tmp)
      (store / 'history.json').write_text(json.dumps(history()))
      base = ['--private-root', '/mnt/d/CarrotLogs', '--private-store', str(store)]
      with patch('openpilot.tools.cyber_autotune.empirical_route_eligibility.read_numeric', side_effect=AssertionError('raw forbidden')):
        for i in range(3):
          name = store / f'metadata{i}.json'
          name.write_text(json.dumps(metadata(i)))
          cli.main(['inventory', *base, '--metadata-receipt', str(name), '--history-metadata', str(store / 'history.json')])
        roles = cli.main(['assign', *base])
        self.assertEqual(roles, cli.main(['assign', *base]))
        self.assertEqual(roles, cli.main(['inspect', *base]))

  def test_resealed_historical_source_rejected_before_write(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp)
      public = base / 'public'
      public.mkdir()
      for path in p.PUBLIC.glob('*.json'):
        shutil.copyfile(path, public / path.name)
      name = 'empirical-source-equivalence-classes-v1.json'
      altered = json.loads((public / name).read_text())
      for group in altered['classes']:
        group['status'] = 'NOT_EQUIVALENT'
      altered = p.seal({k: v for k, v in altered.items() if k != 'receipt_sha256'})
      (public / name).write_text(json.dumps(altered))
      store = base / 'fresh-store'
      with patch.object(p, 'PUBLIC', public), self.assertRaises(ValueError):
        cli.main(['inspect', '--private-root', '/mnt/d/CarrotLogs', '--private-store', str(store)])
      self.assertFalse(store.exists())

  def test_extract_disabled_before_store_write(self):
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(ValueError):
        cli.main(['extract', '--private-root', '/mnt/d/CarrotLogs', '--private-store', tmp])
      self.assertEqual(list(Path(tmp).iterdir()), [])

  def test_metadata_must_live_in_explicit_store(self):
    with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as inner:
      path = Path(outer) / 'meta.json'
      path.write_text(json.dumps(metadata()))
      with self.assertRaises(ValueError):
        a.load_private(path, inner)

  def test_symlink_store_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'real').mkdir()
      (root / 'alias').symlink_to(root / 'real', target_is_directory=True)
      with self.assertRaises(ValueError):
        a.private_store(root / 'alias')

  def test_store_parent_traversal_rejected(self):
    repo = Path(__file__).resolve().parents[4]
    path = Path('/tmp') / '..' / repo.relative_to('/') / 'newstore'
    with self.assertRaises(ValueError):
      a.private_store(path)

  def test_json_parent_traversal_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'store').mkdir()
      (root / 'outside.json').write_text(json.dumps(metadata()))
      with self.assertRaises(ValueError):
        a.load_private(root / 'store' / '..' / 'outside.json', root / 'store')

  def test_no_raw_filename_input(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'rlog.zst'
      with self.assertRaises(ValueError):
        a.load_private(path, tmp)

  def test_source_template_never_equivalent(self):
    with tempfile.TemporaryDirectory() as tmp:
      row = cli.main(['source-template', '--private-root', '/mnt/d/CarrotLogs', '--private-store', tmp, '--source-commit', '0' * 40])
      self.assertEqual(row['status'], 'SOURCE_AUDIT_PENDING')
      self.assertFalse(row['numeric_opening_allowed'])


if __name__ == '__main__':
  unittest.main()
