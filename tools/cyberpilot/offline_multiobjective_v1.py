"""Explicit-path, non-binding F6 offline diagnostics. Never executes a controller.

V1 admits only the preserved public synthetic F5 archive anchored by the F6 contract.
Paths are input capabilities, not discovered from archived code/identities. No network,
source imports, subprocess, vehicle interface, qualification or selection.
"""

import argparse
import gzip
import io
import json
import os
from pathlib import Path
import stat
import zlib
from typing import NoReturn

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot import offline_multiobjective_metrics_v1 as m

F5_MANIFEST_SHA256 = '37bb761c4eb6eeb92bf68db7d34577831b409103c5bc3ee05ceae6bfc58ee681'
F6_CONTRACT_SHA256 = '8e944560d7fd369b7f345a72ad031c1e090e4d8b4e5bafbf43e4fde61eacb2a9'
BASE_HEAD = '66bb193e13ca9f17beb73badb6f2a94a67faa2da'
MAX_FILE_BYTES = 64 * 1024 * 1024  # Reader resource bounds, not control/performance thresholds.
MAX_DECODED_BYTES = 128 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_REQUEST_BYTES = 1024 * 1024
MAX_CATALOG_ITEMS = 512
CONTRACT = Path(__file__).resolve().parents[2] / 'docs/cyberpilot/changes/track-f7-offline-multiobjective-contract.json'


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
  out: dict[str, object] = {}
  for key, value in items:
    g.require(key not in out, 'E_DUPLICATE_KEY')
    out[key] = value
  return out


def _tree(value: object, depth: int = 0) -> None:
  g.require(depth <= MAX_JSON_DEPTH, 'E_JSON_DEPTH')
  if value is None or isinstance(value, (str, bool)):
    return
  if isinstance(value, (int, float)):
    g.number(value)
  elif isinstance(value, list):
    for item in value:
      _tree(item, depth + 1)
  elif isinstance(value, dict):
    for key, item in value.items():
      g.require(isinstance(key, str), 'E_KEY')
      _tree(item, depth + 1)
  else:
    raise g.EvidenceError('E_JSON_TYPE')


def _constant(_value: str) -> object:
  raise g.EvidenceError('E_NONFINITE', 'HG02')


def strict_json(raw: bytes) -> object:
  try:
    value: object = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    _tree(value)
    return value
  except g.EvidenceError:
    raise
  except (UnicodeError, ValueError, RecursionError) as exc:
    raise g.EvidenceError('E_JSON') from exc


def _resolve(path: Path, strict: bool = False) -> Path:
  try:
    return path.resolve(strict=strict)
  except (OSError, RuntimeError, ValueError) as exc:
    # Path.resolve raises RuntimeError on symlink loops in supported Python versions.
    raise g.EvidenceError('E_PATH_RESOLUTION') from exc


def read_regular(path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
  fd = None
  try:
    g.require(path.is_absolute() and path == _resolve(path, strict=True), 'E_EXPLICIT_REGULAR_PATH')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    info = os.fstat(fd)
    g.require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'E_FILE_BOUND')
    with os.fdopen(fd, 'rb') as source:
      fd = None
      raw = source.read(limit + 1)
    g.require(len(raw) <= limit, 'E_FILE_BOUND')
    return raw
  except OSError as exc:
    raise g.EvidenceError('E_INPUT_FILE') from exc
  finally:
    if fd is not None:
      os.close(fd)


def decode_trace(raw: bytes, limit: int = MAX_DECODED_BYTES) -> object:
  try:
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:
      decoded = source.read(limit + 1)
    g.require(len(decoded) <= limit, 'E_DECODED_BOUND')
    return strict_json(decoded)
  except (OSError, EOFError, zlib.error) as exc:
    raise g.EvidenceError('E_COMPRESSED_TRACE') from exc


def load_contract() -> dict[str, object]:
  raw = read_regular(CONTRACT)
  g.require(g.sha(raw) == F6_CONTRACT_SHA256, 'E_CONTRACT_SHA')
  contract = g.mapping(strict_json(raw))
  g.sealed(contract, 'receipt_sha256')
  g.require(contract['effective'] is False and contract['promotion_enabled'] is False, 'E_CONTRACT_AUTHORITY', 'HG10')
  g.require(len(g.sequence(contract['metrics'])) == 28 and len(g.sequence(contract['hard_gates'])) == 10, 'E_CONTRACT_COUNT')
  return contract


def _catalog(value: object) -> dict[str, Path]:
  out = {}
  entries = g.sequence(value)
  g.require(len(entries) <= MAX_CATALOG_ITEMS, 'E_CATALOG_BOUND')
  for obj in entries:
    record = g.mapping(obj)
    g.require(set(record) == {'id', 'path'}, 'E_CATALOG')
    name = g.text(record['id'])
    g.require(name not in out, 'E_DUPLICATE_PATH_ID')
    out[name] = Path(g.text(record['path']))
  return out


def _checked_artifact(name: str, paths: dict[str, Path], manifest: dict[str, dict[str, object]]) -> bytes:
  g.require(name in paths and name in manifest, 'E_ARTIFACT_MAPPING')
  raw = read_regular(paths[name])
  expected = manifest[name]
  g.require(len(raw) == g.integer(expected['bytes']) and g.sha(raw) == expected['sha256'], 'E_ARTIFACT_SHA')
  return raw


def _select(payload: dict[str, object], case: str) -> dict[str, object]:
  g.require(payload['schema'] == 'F5_REAL_OWN_FEEDBACK_PREDECLARED_V1' and payload['source_head'] == BASE_HEAD, 'E_PRODUCER')
  g.require(all(payload[k] is False for k in ('CAN_access', 'Params_write', 'runtime_policy_activation')), 'E_AUTHORITY', 'HG09')
  selected = [g.mapping(x) for x in g.sequence(payload['results']) if g.mapping(x)['case_id'] == case]
  g.require(len(selected) == 1, 'E_CASE')
  item = selected[0]
  g.sealed(item, 'result_receipt_sha256')
  identity = g.mapping(item['source_identity'])
  g.require(g.sha(g.canonical(identity)) == item['source_sha256'], 'E_SOURCE_SHA')
  g.require(g.sha(g.canonical(item['policy'])) == item['policy_sha256'], 'E_POLICY_SHA')
  g.require(item['runtime_active'] is False and item['selected_candidate'] is None and item['selected_policy'] is None, 'E_AUTHORITY', 'HG09')
  calls = g.mapping(item['source_function_calls'])
  g.require(
    all(g.integer(calls[k]) == g.integer(item['frames']) for k in ('native_update', 'latcontrol_torque_update', 'original_plant')),
    'E_HISTORICAL_CALL_PROFILE',
    'HG08',
  )
  return item


def _sources(item: dict[str, object], paths: dict[str, Path], used: set[str]) -> None:
  identity = g.mapping(item['source_identity'])
  for group, prefix in (('F5_runtime_sources', 'runtime:'), ('original_sources', 'original:')):
    for name, claimed in g.mapping(identity[group]).items():
      key = prefix + name
      g.require(key in paths, 'E_SOURCE_MAPPING')
      g.require(g.sha(read_regular(paths[key])) == claimed, 'E_SOURCE_SHA')
      used.add(key)


def _binding(raw: object, item: dict[str, object]) -> None:
  rows = [g.mapping(r) for r in g.sequence(raw)]
  exogenous = ('sequence', 'speed_mps', 'desired_curvature_1pm', 'roll_rad', 'active', 'steering_pressed', 'safety_limited', 'curvature_limited')
  inputs = [{k: g.mapping(r['input'])[k] for k in exogenous} for r in rows]
  g.require(g.sha(g.canonical(inputs)) == item['input_sha256'], 'E_INPUT_SHA')
  initial = {
    'plant': rows[0]['plant_before'],
    'pose': rows[0]['pose_before'],
    'applied_last': 0.0,
    'native_state': rows[0]['native_state_before'],
    'candidate_state': None,
  }
  g.require(g.sha(g.canonical(initial)) == item['initial_state_sha256'], 'E_INITIAL_STATE_SHA')
  commands = [{k: r[k] for k in ('sequence', 'native_request', 'raw_candidate', 'delivered', 'applied')} for r in rows]
  feedback = [
    {k: r[k] for k in ('sequence', 'plant_before', 'plant_after', 'pose_before', 'pose_after', 'native_state_before', 'native_state_after')} for r in rows
  ]
  g.require(g.sha(g.canonical(commands)) == item['command_trace_sha256'], 'E_COMMAND_TRACE_SHA')
  g.require(g.sha(g.canonical(feedback)) == item['feedback_trace_sha256'], 'E_FEEDBACK_TRACE_SHA')


def _gates(contract: dict[str, object], failure: g.EvidenceError | None = None, a2_insufficient: bool = False) -> list[dict[str, object]]:
  out = []
  for raw in g.sequence(contract['hard_gates']):
    definition = g.mapping(raw)
    gate = g.text(definition['id'])
    blocked = failure is not None or (gate == 'HG07' and a2_insufficient)
    reason = (failure.code if gate == failure.gate else 'E_NOT_EVALUATED') if failure else 'A2_DOMAIN_INSUFFICIENT' if blocked else None
    out.append(
      {
        'gate_id': gate,
        'purpose': definition['name'],
        'source_contract': definition['source'],
        'condition': definition['constraint'],
        'input': 'Explicit pinned artifact/source records and verified frames',
        'status': 'STRUCTURALLY_BLOCKED' if blocked else 'STRUCTURALLY_VALID',
        'reason': reason,
        'approval_state': 'F6_STRUCTURAL_SCOPE_ONLY_NOT_PERFORMANCE_AUTHORIZATION',
        'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
      }
    )
  return out


def _new_report() -> dict[str, object]:
  identities = {}
  for name in ('offline_multiobjective_v1.py', 'offline_multiobjective_metrics_v1.py', 'offline_multiobjective_gates_v1.py'):
    identities[name] = g.sha(read_regular(Path(__file__).resolve().with_name(name)))
  return {
    'schema': 'CYBERPILOT_OFFLINE_DIAGNOSTIC_V1',
    'structural_status': 'STRUCTURALLY_BLOCKED',
    'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
    'threshold_status': 'THRESHOLD_APPROVAL_REQUIRED',
    'effective': False,
    'selected_candidate': None,
    'selected_policy': None,
    'authority': {'D2': 'PERFORMANCE_NOT_EVALUATED', 'Private E2': 'NOT_AUTHORIZED', 'HOLDOUT': 'CLOSED', 'Vehicle authority': 'NONE'},
    'tool_source_sha256': identities,
    'contract_sha256': F6_CONTRACT_SHA256,
    'historical_manifest_sha256': F5_MANIFEST_SHA256,
    'new_controller_executions': 0,
    'numerical_environment': {'numpy': m.np.__version__},
    'traces': [],
    'comparisons': [],
  }


def _load_request(request_path: Path, request_sha256: str) -> dict[str, object]:
  raw = read_regular(request_path, MAX_REQUEST_BYTES)
  g.require(g.sha(raw) == request_sha256, 'E_REQUEST_SHA')
  request = g.mapping(strict_json(raw))
  g.require(set(request) == {'schema', 'scope', 'manifest', 'artifacts', 'source_files', 'traces'}, 'E_REQUEST_KEYS')
  g.require(request['schema'] == 'CYBERPILOT_OFFLINE_EVALUATION_REQUEST_V1' and request['scope'] == 'PUBLIC_SYNTHETIC_ONLY', 'E_SCOPE', 'HG09')
  return request


def _guard_output(directory: Path, request: dict[str, object]) -> None:
  destination = _resolve(directory)
  g.require(directory.is_absolute(), 'E_OUTPUT_PATH')
  g.require(not destination.is_relative_to(Path(__file__).resolve().parents[2]), 'E_OUTPUT_SOURCE_TREE')
  manifest = g.mapping(request['manifest'])
  g.require(set(manifest) == {'path'}, 'E_MANIFEST_MAPPING')
  inputs = [Path(g.text(manifest['path']))]
  inputs.extend(_catalog(request['artifacts']).values())
  inputs.extend(_catalog(request['source_files']).values())
  # A blocked diagnostic must not be written into preserved input/source directories either.
  for path in inputs:
    g.require(path.is_absolute(), 'E_EXPLICIT_REGULAR_PATH')
    g.require(not destination.is_relative_to(_resolve(path.parent, strict=True)), 'E_OUTPUT_INPUT_TREE')


def evaluate(request_path: Path, request_sha256: str, output_dir: Path | None = None) -> dict[str, object]:
  report = _new_report()
  contract = load_contract()
  try:
    request = _load_request(request_path, request_sha256)
    manifest_ref = g.mapping(request['manifest'])
    g.require(set(manifest_ref) == {'path'}, 'E_MANIFEST_MAPPING')
    manifest_path = Path(g.text(manifest_ref['path']))
    if output_dir is not None:
      _guard_output(output_dir, request)
    manifest_raw = read_regular(manifest_path)
    g.require(g.sha(manifest_raw) == F5_MANIFEST_SHA256, 'E_MANIFEST_SHA')
    manifest_obj = g.mapping(strict_json(manifest_raw))
    manifest = {g.text(e['path']): e for e in (g.mapping(x) for x in g.sequence(manifest_obj['files']))}
    artifact_paths = _catalog(request['artifacts'])
    source_paths = _catalog(request['source_files'])
    used_artifacts: set[str] = set()
    used_sources: set[str] = set()
    definitions = [g.mapping(x) for x in g.sequence(contract['metrics'])]
    specs = g.sequence(request['traces'])
    g.require(0 < len(specs) <= 65, 'E_TRACE_COUNT')
    retained = []
    traces = []
    all_metrics: list[dict[str, dict[str, object]]] = []
    seen = set()
    for obj in specs:
      spec = g.mapping(obj)
      g.require(set(spec) == {'result_id', 'repeat_result_id', 'case_id', 'trace_id', 'repeat_trace_id'}, 'E_TRACE_SPEC')
      names = {k: g.text(v) for k, v in spec.items()}
      first_id, second_id = names['result_id'], names['repeat_result_id']
      g.require(first_id.endswith('-r1/result.json') and second_id == first_id.replace('-r1/', '-r2/'), 'E_REPEAT_ID', 'HG08')
      payload = g.mapping(strict_json(_checked_artifact(first_id, artifact_paths, manifest)))
      repeat_payload = g.mapping(strict_json(_checked_artifact(second_id, artifact_paths, manifest)))
      item = _select(payload, names['case_id'])
      repeat = _select(repeat_payload, names['case_id'])
      for key in ('arm', 'case_id', 'source_sha256', 'policy_sha256', 'input_sha256', 'initial_state_sha256', 'native_identity', 'plant'):
        g.require(item[key] == repeat[key], 'E_REPEAT_BINDING', 'HG08')
      tid = first_id.removesuffix('result.json') + g.text(item['trace_file'])
      rid = second_id.removesuffix('result.json') + g.text(repeat['trace_file'])
      g.require(names['trace_id'] == tid and names['repeat_trace_id'] == rid and tid != rid, 'E_TRACE_ID', 'HG08')
      g.require((first_id, names['case_id']) not in seen, 'E_DUPLICATE_CASE')
      seen.add((first_id, names['case_id']))
      compressed = _checked_artifact(tid, artifact_paths, manifest)
      repeat_bytes = _checked_artifact(rid, artifact_paths, manifest)
      g.require(compressed == repeat_bytes, 'E_REPEAT_BYTES', 'HG08')
      g.require(g.sha(compressed) == item['compressed_sha256'] == repeat['compressed_sha256'], 'E_COMPRESSED_SHA')
      rows = decode_trace(compressed)
      g.require(g.sha(g.canonical(rows)) == item['trace_sha256'] == repeat['trace_sha256'], 'E_TRACE_SHA')
      _sources(item, source_paths, used_sources)
      frames = g.verify_frames(rows, item)
      _binding(rows, item)
      arm = g.text(item['arm'])
      insufficient = arm == 'A2' and any(
        g.required_static_command(f.desired, f.speed, f.roll, g.mapping(item['plant'])) > (0.3 + (f.speed - 5) / 5 * (0.2 - 0.3)) for f in frames
      )
      calculated = m.calculate(frames, g.mapping(item['plant']), arm, definitions)
      observations = []
      if any(abs(f.command) == 1 for f in frames):
        observations.append('SATURATION_OBSERVED_NOT_QUALIFIED')
      if any(f.curvature - f.desired > 0 for f in frames) and any(f.curvature - f.desired < 0 for f in frames):
        observations.append('SIGNED_ERROR_CANCELLATION_OBSERVED_NOT_QUALIFIED')
      trace = {
        'arm': arm,
        'case_id': item['case_id'],
        'frames': len(frames),
        'structural_status': 'STRUCTURALLY_BLOCKED' if insufficient else 'STRUCTURALLY_VALID',
        'source_sha256': item['source_sha256'],
        'policy_sha256': item['policy_sha256'],
        'input_sha256': item['input_sha256'],
        'initial_state_sha256': item['initial_state_sha256'],
        'historical_native_identity': item['native_identity'],
        'trace_sha256': item['trace_sha256'],
        'historical_result_receipt_sha256': item['result_receipt_sha256'],
        'metrics': calculated,
        'gates': _gates(contract, a2_insufficient=insufficient),
        'observations': observations,
        'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
      }
      traces.append(trace)
      all_metrics.append(calculated)
      retained.append((item, frames))
      used_artifacts.update((first_id, second_id, tid, rid))
    g.require(set(artifact_paths) == used_artifacts and set(source_paths) == used_sources, 'E_UNUSED_EXPLICIT_MAPPING')
    comparisons = []
    for i, (left, lf) in enumerate(retained):
      for j, (right, rf) in enumerate(retained[i + 1 :], i + 1):
        if left['case_id'] != right['case_id']:
          continue
        g.require(all(left[k] == right[k] for k in ('input_sha256', 'initial_state_sha256', 'native_identity', 'plant')), 'E_COMPARISON_BINDING', 'HG02')
        comparisons.append({'left_trace': i, 'right_trace': j, **m.compare(lf, rf), 'metrics': m.compare_metrics(all_metrics[i], all_metrics[j])})
    report.update(
      traces=traces,
      comparisons=comparisons,
      request_sha256=request_sha256,
      gates=_gates(contract, a2_insufficient=any(t['structural_status'] == 'STRUCTURALLY_BLOCKED' for t in traces)),
    )
    report['structural_status'] = 'STRUCTURALLY_VALID' if all(t['structural_status'] == 'STRUCTURALLY_VALID' for t in traces) else 'STRUCTURALLY_BLOCKED'
  except g.EvidenceError as exc:
    report.update(error_code=exc.code, gates=_gates(contract, exc))
  except (KeyError, TypeError, ValueError, OverflowError, FloatingPointError, RecursionError) as exc:
    failure = g.EvidenceError('E_INVALID_OR_NUMERICAL_INPUT', 'HG02')
    report.update(error_code=failure.code, gates=_gates(contract, failure))
    del exc
  report['receipt_sha256'] = g.sha(g.canonical(report))
  return report


def write_report(directory: Path, report: dict[str, object]) -> None:
  g.require(not _resolve(directory).is_relative_to(Path(__file__).resolve().parents[2]), 'E_OUTPUT_SOURCE_TREE')
  try:
    g.require(directory.is_absolute() and directory.parent == _resolve(directory.parent, strict=True), 'E_OUTPUT_PATH')
    directory.mkdir(mode=0o700)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
      target = os.open('diagnostics.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
      with os.fdopen(target, 'wb') as stream:
        stream.write(g.canonical(report))
    finally:
      os.close(fd)
  except OSError as exc:
    raise g.EvidenceError('E_OUTPUT_EXCLUSIVE') from exc


class _Parser(argparse.ArgumentParser):
  def error(self, message: str) -> NoReturn:
    del message
    raise g.EvidenceError('E_ARGUMENTS')


def main(argv: list[str] | None = None) -> int:
  parser = _Parser(description=__doc__)
  parser.add_argument('--request', type=Path, required=True)
  parser.add_argument('--request-sha256', required=True)
  parser.add_argument('--output-dir', type=Path, required=True)
  try:
    args = parser.parse_args(argv)
    request = _load_request(args.request, args.request_sha256)
    _guard_output(args.output_dir, request)
    report = evaluate(args.request, args.request_sha256, args.output_dir)
    write_report(args.output_dir, report)
    print(
      json.dumps(
        {'structural_status': report['structural_status'], 'performance_status': 'PERFORMANCE_NOT_QUALIFIED', 'receipt_sha256': report['receipt_sha256']},
        sort_keys=True,
      )
    )
    return 0 if report['structural_status'] == 'STRUCTURALLY_VALID' else 2
  except g.EvidenceError as exc:
    print(json.dumps({'structural_status': 'STRUCTURALLY_BLOCKED', 'performance_status': 'PERFORMANCE_NOT_QUALIFIED', 'error_code': exc.code}))
    return 2


if __name__ == '__main__':
  raise SystemExit(main())
