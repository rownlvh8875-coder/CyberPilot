"""Deterministic unsafe paths fail before IPC; real native failure cleanup."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cyberpilot_web_native import native_check
from tools.cyberpilot_web_native.fixtures import SyntheticPublisher
from tools.cyberpilot_web_native.isolation import namespace


def reject_socket_factory(*args, **kwargs):
  raise RuntimeError('native_socket_factory_reached')


def blocked_native_module():
  return types.SimpleNamespace(messaging=types.SimpleNamespace(PubMaster=reject_socket_factory))


class EndpointSafetyTests(unittest.TestCase):
  def test_temporary_root_cannot_reach_native_socket_factory(self):
    with tempfile.TemporaryDirectory() as directory, namespace(Path(directory)) as run:
      with patch.dict(sys.modules, {'openpilot.cereal': blocked_native_module()}), self.assertRaises(ValueError):
        SyntheticPublisher(run)

  def test_hardlinked_endpoint_rejected_before_native_factory(self):
    with namespace() as run:
      outside = run.path.with_name(run.path.name + '_outside')
      outside.write_bytes(b'preserve unrelated bytes')
      endpoint = run.path / 'carState'
      try:
        os.link(outside, endpoint)
        with patch.dict(sys.modules, {'openpilot.cereal': blocked_native_module()}), self.assertRaises(ValueError):
          SyntheticPublisher(run)
        self.assertEqual(outside.read_bytes(), b'preserve unrelated bytes')
      finally:
        endpoint.unlink()
        outside.unlink()

  def test_foreign_endpoint_rejected_before_native_factory(self):
    with namespace() as run:
      endpoint = run.path / 'carState'
      endpoint.write_bytes(b'foreign metadata fixture')
      real_lstat = Path.lstat
      def metadata(path):
        info = real_lstat(path)
        if path == endpoint:
          values = list(info)
          values[4] = os.getuid() + 1
          return os.stat_result(values)
        return info
      # No chown privilege needed; substitute only external filesystem metadata.
      with patch.object(Path, 'lstat', metadata), patch.dict(sys.modules, {'openpilot.cereal': blocked_native_module()}), self.assertRaises(ValueError):
        SyntheticPublisher(run)


class CleanupSafetyTests(unittest.TestCase):
  def prepared(self):
    spec = importlib.util.find_spec('msgq')
    assert spec is not None and spec.origin is not None
    return Path(spec.origin).resolve().parents[2]

  def test_unconfirmed_worker_retains_owned_queues_and_fails(self):
    class StuckWorker:
      ident = 1
      def join(self, timeout):
        pass
      def is_alive(self):
        return True
    run = None
    publisher = None
    try:
      with namespace() as run:
        publisher = SyntheticPublisher(run)
        with self.assertRaises(RuntimeError):
          native_check.cleanup_case(run, publisher, None, StuckWorker(), threading.Event(), None)
      self.assertTrue(run.path.exists())
      self.assertTrue(publisher.pm.sock)
    finally:
      if publisher is not None:
        publisher.close()
      if run is not None and run.path.exists():
        for endpoint in run.path.iterdir():
          endpoint.unlink()
        run.path.rmdir()

  def test_launch_failure_closes_real_publisher_before_queue_removal(self):
    created = []
    close_order = []
    real_close = SyntheticPublisher.close
    def construct(run):
      publisher = SyntheticPublisher(run)
      created.append(publisher)
      return publisher
    def close(publisher):
      close_order.append(publisher.run.path.exists())
      real_close(publisher)
    try:
      with tempfile.TemporaryDirectory() as directory, patch.object(native_check, 'SyntheticPublisher', construct), patch.object(SyntheticPublisher, 'close', close), patch.object(native_check.subprocess, 'Popen', side_effect=OSError('test launch failure')):
        with self.assertRaises(OSError):
          native_check.exercise_case(None, Path(directory), 390, 844, self.prepared())
      self.assertEqual(close_order, [True])
      self.assertFalse(created[0].pm.sock)
      self.assertFalse(created[0].run.path.exists())
    finally:
      for publisher in created:
        real_close(publisher)

  def test_browser_close_failure_still_reaps_real_child_and_sockets(self):
    class Page:
      def on(self, *args):
        pass
      def goto(self, *args):
        raise RuntimeError('test browser body failed')
    class Context:
      def new_page(self):
        return Page()
      def close(self):
        raise RuntimeError('test browser close failed')
    class Browser:
      def new_context(self, **kwargs):
        return Context()
    publishers, processes = [], []
    real_popen = subprocess.Popen
    def construct(run):
      publisher = SyntheticPublisher(run)
      publishers.append(publisher)
      return publisher
    def popen(*args, **kwargs):
      process = real_popen(*args, **kwargs)
      processes.append(process)
      return process
    try:
      with tempfile.TemporaryDirectory() as directory, patch.object(native_check, 'SyntheticPublisher', construct), patch.object(native_check.subprocess, 'Popen', popen):
        with self.assertRaises(RuntimeError):
          native_check.exercise_case(Browser(), Path(directory), 390, 844, self.prepared())
      self.assertTrue(processes and all(p.poll() is not None for p in processes))
      self.assertTrue(publishers and all(not p.pm.sock for p in publishers))
    finally:
      for process in processes:
        if process.poll() is None:
          process.kill()
        process.communicate(timeout=5)
      for publisher in publishers:
        publisher.close()
