"""Negative and independent numeric controls for the non-binding F8 adapter."""

from dataclasses import replace
import math
import unittest
from unittest.mock import patch

import numpy as np

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot import offline_multiobjective_metrics_v1 as m
from tools.cyberpilot.f8_evidence_diagnostics_v1 import direct_tone, initial_aware_derivative, settling, tone
from tools.cyberpilot.f8_evidence_reader_v1 import F8Error
from tools.cyberpilot.f8_evidence_validation_v1 import mathematical_domain
from tools.cyberpilot.offline_f8_evidence_v1 import authority, load_contract
from openpilot.tools.cyberpilot_tests.test_f8_evidence_trace_v1 import fixture


def signal_frames(hz=0.5):
  return tuple(
    g.Frame(
      n,
      (n + 1) * 0.01,
      7.5,
      math.sin(2 * math.pi * hz * n * 0.01) * 0.001,
      math.sin(2 * math.pi * hz * n * 0.01 - 0.3) * 0.0005,
      0.0,
      0.0,
      0.0,
      0.0,
      ((n + 1) * 0.075, 0.0, 0.0),
      ((n + 1) * 0.075, 0.0, 0.0),
      0.0,
      True,
      False,
      False,
    )
    for n in range(4000)
  )


class DiagnosticTests(unittest.TestCase):
  def test_pinned_contract_and_unchanged_f7_definitions(self):
    c, f7 = load_contract()
    self.assertFalse(c['effective'])
    self.assertEqual((len(g.sequence(f7['metrics'])), len(g.sequence(f7['hard_gates']))), (28, 10))

  def test_fake_contract_source_receipt(self):
    with patch('tools.cyberpilot.offline_f8_evidence_v1.source_bytes', return_value=b'{}'):
      with self.assertRaises(F8Error):
        load_contract()

  def test_forged_authority_and_selection(self):
    valid: dict[str, object] = {'effective': False, 'performance_qualified': False, 'selected_candidate': None, 'selected_policy': None}
    authority(valid)
    for key, value in [('effective', True), ('performance_qualified', True), ('selected_candidate', 'A3')]:
      with self.subTest(key=key), self.assertRaises(F8Error):
        authority({**valid, key: value})

  def test_two_tone_windows_and_direct_oracle(self):
    frames = signal_frames()
    for window in ('periodic_hann', 'rectangular'):
      r, oracle = tone(frames, 0.5, window), direct_tone(frames, 0.5, window)
      self.assertAlmostEqual(g.number(r['gain']), 0.5, places=12)
      self.assertAlmostEqual(g.number(r['phase_rad']), -0.3, places=12)
      for key in oracle:
        self.assertAlmostEqual(g.number(r[key]), oracle[key], places=12)
      self.assertFalse(r['full_response_qualified'])

  def test_invalid_excitation_is_not_full_response(self):
    with self.assertRaises(F8Error):
      tone(signal_frames()[:100], 0.5, 'periodic_hann')
    with self.assertRaises(F8Error):
      tone(signal_frames(), 3.0, 'periodic_hann')

  def test_settling_remains_explanatory(self):
    frames = tuple(replace(f, desired=0.0 if n < 100 else 0.001, curvature=0.0 if n < 100 else 0.001) for n, f in enumerate(signal_frames()[:500]))
    grid = settling(frames, {'id': 'authored_step', 'group': 'transition'})
    self.assertEqual(len(grid), 9)
    self.assertTrue(all(r['status'] == 'DEFINITION_APPROVAL_REQUIRED' for r in grid))
    self.assertTrue(all(r['first_hold_s'] == 0.01 for r in grid))

  def test_frequency_and_ramp_not_settling_steps(self):
    self.assertEqual(settling(signal_frames(), {'id': 'tone', 'group': 'frequency'}), [])
    self.assertEqual(settling(signal_frames(), {'id': 'ramp_control', 'group': 'transition'}), [])

  def test_six_unavailable_f7_metrics_are_not_requalified(self):
    _, f7 = load_contract()
    result = m.calculate(signal_frames()[:50], g.mapping(g.PLANT), 'A0', [g.mapping(x) for x in g.sequence(f7['metrics'])])
    self.assertEqual(sum(r['status'] == 'METRIC_UNAVAILABLE' for r in result.values()), 6)
    self.assertTrue(all(r['performance_status'] == 'PERFORMANCE_NOT_QUALIFIED' for r in result.values()))

  def test_high_saturation_is_observation_without_arbitrary_gate(self):
    frames = tuple(replace(f, command=(-1.0) ** n) for n, f in enumerate(signal_frames()[:20]))
    result = m.saturation(np.array([f.command for f in frames]), 0.01)
    self.assertEqual((result['events'], result['frames'], result['occupancy']), (20, 20, 1.0))
    self.assertEqual(result['qualification'], 'PERFORMANCE_NOT_QUALIFIED')

  def test_normal_and_xy_differ(self):
    actual = np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    reference = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    value = m.position_components(actual, reference)
    self.assertEqual((value['normal']['rms'], value['euclidean']['rms']), (0.0, 1.0))

  def test_initial_applied_derivative_is_separate(self):
    frames = tuple(replace(f, applied=-0.05) for f in signal_frames()[:20])
    sidecar = initial_aware_derivative(frames, -0.05)
    self.assertEqual(g.mapping(sidecar['physical_applied_derivative'])['rms'], 0.0)
    self.assertEqual(sidecar['prior_applied'], -0.05)

  def test_mathematical_and_development_domain_are_separate(self):
    _, _, spec = fixture()
    for f in spec['frames']:
      f['speed_mps'] = 30.0
    r = mathematical_domain(spec, 'A2')
    self.assertEqual(r['mathematical_status'], 'MATHEMATICAL_DOMAIN_VALID')
    self.assertFalse(r['candidate_domain_admitted'])
    self.assertEqual(r['dynamic_status'], 'DYNAMIC_FEASIBILITY_UNQUALIFIED')

  def test_outside_plant_or_malformed_measurement_domain(self):
    _, _, spec = fixture()
    for value in (0.0, float('nan'), True):
      with self.subTest(value=value), self.assertRaises((F8Error, g.EvidenceError)):
        spec['frames'][0]['speed_mps'] = value
        mathematical_domain(spec, 'A0')

  def test_literal_historical_paths_are_inert(self):
    from tools.cyberpilot.offline_f8_evidence_v1 import historical_roots

    raw = b'ROOT=Path("/source")\nTASK=Path("/task")\nHIST=Path("/history")\nraise RuntimeError("must never execute")'
    self.assertEqual(historical_roots(raw), {'ROOT': '/source/', 'TASK': '/task/', 'HIST': '/history/'})

  def test_executable_or_missing_historical_root_rejected(self):
    from tools.cyberpilot.offline_f8_evidence_v1 import historical_roots

    for raw in (b'ROOT=Path(str(compute()))', b'ROOT=Path("/source")', b'invalid syntax ???'):
      with self.subTest(raw=raw), self.assertRaises(F8Error):
        historical_roots(raw)

  def test_cli_transport_and_device_guard(self):
    from tools.cyberpilot.offline_f8_evidence_v1 import no_transport

    for event, args in (('socket.__new__', ()), ('subprocess.Popen', ()), ('open', ('/dev/can0',)), ('open', ('/data/params/policy',))):
      with self.subTest(event=event), self.assertRaises(F8Error):
        no_transport(event, args)

  def test_explicit_cli_arguments_required(self):
    from tools.cyberpilot.offline_f8_evidence_v1 import Parser

    parser = Parser()
    parser.add_argument('--archive', required=True)
    with self.assertRaises(F8Error):
      parser.parse_args([])
