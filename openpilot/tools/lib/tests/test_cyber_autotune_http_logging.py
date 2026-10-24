"""Source-only callback checks; never import private tools or open a server."""

import ast
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler
import inspect
import io
from pathlib import Path
from types import FunctionType
from typing import override
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2] / 'cyber_autotune'
CALLBACK_FILES = ('approximate_geometry_visualizer.py', 'private_pixel_review.py')


def logging_callback(filename: str) -> FunctionType:
  tree = ast.parse((SOURCE_ROOT / filename).read_text())
  methods: list[ast.stmt] = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'log_message']
  if len(methods) != 1:
    raise AssertionError('Expected one logging callback')
  namespace: dict[str, object] = {'override': override}
  exec(compile(ast.Module(body=methods, type_ignores=[]), filename, 'exec'), namespace)
  callback = namespace['log_message']
  if not isinstance(callback, FunctionType):
    raise AssertionError('Expected a Python function')
  return callback


class TestCyberAutoTuneHTTPLogging(unittest.TestCase):
  def test_base_format_keyword_is_accepted(self):
    inspect.signature(BaseHTTPRequestHandler.log_message).bind(None, format='message')
    for filename in CALLBACK_FILES:
      with self.subTest(filename=filename):
        self.assertIsNone(logging_callback(filename)(None, format='message'))

  def test_existing_positional_inputs_remain_noops(self):
    for filename in CALLBACK_FILES:
      callback = logging_callback(filename)
      for args in ((), ('message',), ('value %s', 'sample'), (None,), (True,), (object(), 1, 2)):
        with self.subTest(filename=filename, args=args):
          self.assertIsNone(callback(None, *args))

  def test_unknown_keyword_is_rejected(self):
    for filename in CALLBACK_FILES:
      with self.subTest(filename=filename), self.assertRaisesRegex(TypeError, 'unexpected keyword argument'):
        logging_callback(filename)(None, unexpected='message')

  def test_duplicate_format_is_rejected(self):
    for filename in CALLBACK_FILES:
      with self.subTest(filename=filename), self.assertRaises(TypeError):
        logging_callback(filename)(None, 'positional', format='duplicate')

  def test_logging_remains_silent(self):
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
      for filename in CALLBACK_FILES:
        callback = logging_callback(filename)
        callback(None, 'value %s', 'sample')
        callback(None)
    self.assertEqual(output.getvalue(), '')
    self.assertEqual(errors.getvalue(), '')

  def test_signature_accepts_base_keyword_binding(self):
    for filename in CALLBACK_FILES:
      with self.subTest(filename=filename):
        inspect.signature(logging_callback(filename)).bind(None, format='message')
