"""Keep the logger deletion test double inside its unittest lifecycle."""

import os
from pathlib import Path
import shutil
import unittest
from unittest import mock

from openpilot.system.loggerd.tests import test_deleter


class TestLoggerdStatvfsIsolation(unittest.TestCase):
  def test_successful_deleter_test_restores_statvfs(self):
    original = os.statvfs
    with mock.patch.object(os, 'statvfs', original):
      result = unittest.TestResult()
      test_deleter.TestDeleter('test_delete').run(result)
      self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
      self.assertIs(os.statvfs, original)
      self.assertGreater(shutil.disk_usage(Path.cwd()).total, 0)

  def test_failing_deleter_test_restores_statvfs(self):
    original = os.statvfs
    with mock.patch.object(os, 'statvfs', original):
      case = test_deleter.TestDeleter('test_delete')
      result = unittest.TestResult()
      with mock.patch.object(case, '_callTestMethod', side_effect=RuntimeError('synthetic body failure')):
        case.run(result)
      self.assertEqual(len(result.errors), 1)
      self.assertEqual(result.failures, [])
      self.assertIn('synthetic body failure', result.errors[0][1])
      self.assertIs(os.statvfs, original)
      self.assertGreater(shutil.disk_usage(Path.cwd()).total, 0)
