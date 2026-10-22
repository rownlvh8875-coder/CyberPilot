"""Explicit, pinned F8 local evidence -> non-binding F7 metric diagnostics.

This adapter never imports an archived source or executes a controller. Historical
execution/profile evidence is corroborated, not externally authenticated.
"""

import argparse
import ast
from collections import Counter
from pathlib import Path
import sys
from typing import NoReturn

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot import offline_multiobjective_metrics_v1 as m
from tools.cyberpilot import f8_evidence_diagnostics_v1 as d
from tools.cyberpilot.f8_evidence_reader_v1 import Archive, F8Error, Output, digest, json_value, need, regular_file
from tools.cyberpilot.f8_evidence_validation_v1 import ARMS, mathematical_domain, near, verify_trace

REPO = Path(__file__).resolve().parents[2]
CONTRACT_PATH = 'docs/cyberpilot/changes/track-f9-f8-evidence-contract-v1.json'
CONTRACT_SHA = 'a68f94c7e620946d317742072f0d5a786f3bdc0b7887e3904bfd9f853a50d67f'
NAMESPACE = 'CYBERPILOT_F9_F8_DIAGNOSTIC_SIDECAR_V1'
NATIVE_IDENTITY = {
  'car_params_sha256': 'fb13c87310903b14558ff169a5f7da6a66c388b690ec8a12aaacb8538c3fec54',
  'config_sha256': '0b974652a5a02bdf729f0ad16d9ac086918c51903e351f8bae15caa869f8f0c2',
  'role': 'UNCHANGED_NATIVE_BASELINE',
  'source_sha256': '56f0d5ef041573b9aa199cd5b753a9ab97bd6cc2a6077173501106d52fc0847e',
}


def source_bytes(relative: str) -> bytes:
  need(relative.startswith(('tools/', 'openpilot/', 'docs/')) and '..' not in Path(relative).parts, 'F8_SOURCE_PATH')
  with regular_file(REPO / relative, REPO, 4 * 1024**2) as stream:
    raw = stream.read(4 * 1024**2 + 1)
  need(len(raw) <= 4 * 1024**2, 'F8_SOURCE_BOUND')
  return raw


def authority(value: dict[str, object]) -> None:
  for key in ('effective', 'performance_qualified'):
    need(value.get(key) is False, 'F8_FORGED_QUALIFICATION')
  need(value.get('selected_candidate') is None and value.get('selected_policy') is None, 'F8_SELECTION_FORBIDDEN')


def load_contract() -> tuple[dict[str, object], dict[str, object]]:
  raw = source_bytes(CONTRACT_PATH)
  need(digest(raw) == CONTRACT_SHA, 'F8_ADAPTER_CONTRACT_SHA')
  contract = g.mapping(json_value(raw))
  g.sealed(contract, 'receipt_sha256')
  authority(contract)
  need(contract.get('diagnostic_only') is True and contract.get('runtime_authorized') is False and contract.get('vehicle_authority') == 'NONE', 'F8_AUTHORITY')
  f7 = g.mapping(contract['f7'])
  for path, expected in g.mapping(f7['source_sha256']).items():
    need(digest(source_bytes(path)) == expected, 'F8_F7_SOURCE_SHA')
  for path, expected in g.mapping(contract['original_sources']).items():
    need(digest(source_bytes(path)) == expected, 'F8_ORIGINAL_SOURCE_SHA')
  f7_contract = g.mapping(json_value(source_bytes('docs/cyberpilot/changes/track-f7-offline-multiobjective-contract.json')))
  g.sealed(f7_contract, 'receipt_sha256')
  need(f7_contract['receipt_sha256'] == f7['contract_receipt'] and f7_contract['effective'] is False, 'F8_F7_CONTRACT')
  need(len(g.sequence(f7_contract['metrics'])) == 28 and len(g.sequence(f7_contract['hard_gates'])) == 10, 'F8_F7_DEFINITIONS')
  return contract, f7_contract


def historical_roots(raw: bytes) -> dict[str, str]:
  """Parse three pinned literal identity roots without executing archived Python."""
  roots: dict[str, str] = {}
  try:
    tree = ast.parse(raw)
  except (SyntaxError, ValueError, RecursionError) as exc:
    raise F8Error('F8_HISTORICAL_ROOTS') from exc
  for node in tree.body:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
      continue
    name = node.targets[0].id
    if name not in ('ROOT', 'TASK', 'HIST'):
      continue
    value = node.value
    need(
      isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'Path' and len(value.args) == 1 and not value.keywords,
      'F8_HISTORICAL_ROOTS',
    )
    if isinstance(value, ast.Call) and len(value.args) == 1:
      item = value.args[0]
      need(isinstance(item, ast.Constant) and isinstance(item.value, str), 'F8_HISTORICAL_ROOTS')
      if isinstance(item, ast.Constant) and isinstance(item.value, str):
        need(Path(item.value).is_absolute() and '..' not in Path(item.value).parts and name not in roots, 'F8_HISTORICAL_ROOTS')
        roots[name] = item.value.rstrip('/') + '/'
  need(set(roots) == {'ROOT', 'TASK', 'HIST'}, 'F8_HISTORICAL_ROOTS')
  return roots


def source_lock(a: Archive, name: str, contract: dict[str, object]) -> dict[str, object]:
  lock = g.mapping(a.json(name))
  need(
    lock['effective'] is False
    and lock['feature_head'] == contract['evidence_source_head']
    and lock['selected_candidate'] is None
    and lock['selected_policy'] is None,
    'F8_EXECUTION_LOCK',
  )
  roots = historical_roots(a.raw('scripts/f8_runtime.py'))
  for path, expected in g.mapping(lock['sources']).items():
    if path.startswith(roots['ROOT']):
      raw = source_bytes(path[len(roots['ROOT']) :])
    elif path.startswith(roots['HIST']) and path[len(roots['HIST']) :] in ('counterfactual.py', 'offline_policy.py'):
      raw = a.raw('historical_sources/' + path[len(roots['HIST']) :])
    elif path.startswith(roots['TASK']):
      raw = a.raw(path[len(roots['TASK']) :])
    else:
      raise F8Error('F8_UNKNOWN_SOURCE_LOCATION')
    need(digest(raw) == expected, 'F8_EXECUTION_SOURCE_SHA')
  return lock


def metadata(a: Archive, contract: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
  root = g.mapping(contract['trust_root'])
  receipt = g.mapping(a.json('EXPERIMENTAL_RECEIPT.json'))
  g.sealed(receipt, 'receipt_sha256')
  authority(receipt)
  need(receipt['receipt_sha256'] == root['f8_receipt'] and receipt['feature_head'] == contract['evidence_source_head'], 'F8_SOURCE_RECEIPT')
  links = {
    'execution_lock_sha256': 'evidence/execution-lock.json',
    'reset_v2_lock_sha256': 'evidence/execution-lock-reset-v2.json',
    'analysis_sha256': 'results/analysis-r1.json',
    'frequency_oracle_sha256': 'evidence/frequency-oracle.json',
    'input_manifest_sha256': 'evidence/input-manifest.json',
    'oracle_sha256': 'evidence/oracle.json',
    'summary_sha256': 'results/summary.json',
  }
  for key, path in links.items():
    need(digest(a.raw(path)) == receipt[key], 'F8_RECEIPT_LINK')
  for path, expected in g.mapping(receipt['source_sha256']).items():
    need(path.startswith('scripts/') and digest(a.raw(path)) == expected, 'F8_ARCHIVED_SOURCE_SHA')
  need(a.raw('results/analysis-r1.json') == a.raw('results/analysis-r2.json'), 'F8_ANALYSIS_REPEAT')
  return (source_lock(a, links['execution_lock_sha256'], contract), source_lock(a, links['reset_v2_lock_sha256'], contract), receipt)


def catalog(a: Archive, arm: str, cohort: str, rep: int) -> list[dict[str, object]]:
  prefix = f'{arm}{cohort}-r{rep}'
  execution = g.mapping(a.json(f'evidence/{prefix}-execution.json'))
  environment = g.mapping(a.json(f'evidence/{prefix}-environment.json'))
  need(execution['exit_code'] == 0 and execution['arm'] == arm and execution['rep'] == rep, 'F8_EXECUTION_RESULT')
  need(
    environment.get('new_controller') is False
    and environment.get('params_write') is False
    and environment.get('vehicle_authority') == 'NONE'
    and environment.get('read_only_source') is True
    and environment.get('host_drives_visible') is False,
    'F8_HISTORICAL_ISOLATION',
  )
  return [g.mapping(x) for x in g.sequence(a.json(f'results/{prefix}/catalog.json'))]


def source_identity(item: dict[str, object], spec: dict[str, object], lock: dict[str, object], contract: dict[str, object]) -> str:
  need(item['native_identity'] == NATIVE_IDENTITY and item['plant_sha256'] == g.sha(g.canonical(g.PLANT)), 'F8_NATIVE_PLANT_IDENTITY')
  need(item['policy_sha256'] == g.sha(g.canonical(item['policy'])), 'F8_POLICY_SHA')
  source = g.sha(
    g.canonical(
      {
        'namespace': spec['namespace'],
        'execution_lock': lock,
        'original_sources': contract['original_sources'],
        'policy': item['policy'],
        'native_identity': item['native_identity'],
      }
    )
  )
  need(item['source_sha256'] == source, 'F8_COMPOSITE_SOURCE')
  return source


def index(records: object) -> dict[tuple[str, str], dict[str, object]]:
  out = {}
  for value in g.sequence(records):
    r = g.mapping(value)
    key = (g.text(r['arm']), g.text(r['id']))
    need(key not in out, 'F8_DUPLICATE_RECORD')
    out[key] = r
  return out


def run(archive: Path, read_root: Path, output: Path) -> dict[str, object]:
  """Fixed audited cohort only. No override pins or evidence auto-discovery."""
  contract, f7 = load_contract()
  source_names = ('offline_f8_evidence_v1.py', 'f8_evidence_reader_v1.py', 'f8_evidence_validation_v1.py', 'f8_evidence_diagnostics_v1.py')
  sources_before = {name: digest(source_bytes('tools/cyberpilot/' + name)) for name in source_names}
  root = g.mapping(contract['trust_root'])
  with (
    Archive(archive, read_root, g.text(root['archive_sha256']), g.text(root['manifest_sha256']), g.integer(root['manifest_records'])) as a,
    Output(output, forbidden=(REPO, read_root)) as out,
  ):
    out.write('INCOMPLETE.json', {'namespace': NAMESPACE, 'complete': False})
    need(len(a.members) == root['zip_entries'], 'F8_INVENTORY_COUNT')
    main_lock, reset_lock, historical_receipt = metadata(a, contract)
    manifest = [g.mapping(x) for x in g.sequence(a.json('evidence/input-manifest.json'))]
    need(len(manifest) == 37, 'F8_SCENARIO_COUNT')
    specs = {}
    for entry in manifest:
      name = g.text(entry['id'])
      need(name not in specs and all(c.isalnum() or c == '_' for c in name), 'F8_SCENARIO_ID')
      raw = a.raw(f'inputs/{name}.json')
      need(digest(raw) == entry['sha256'], 'F8_SCENARIO_SHA')
      spec = g.mapping(json_value(raw))
      need(spec['id'] == name and spec['group'] == entry['group'] and len(g.sequence(spec['frames'])) == entry['frames'], 'F8_INPUT_ID')
      specs[name] = spec
    analysis = g.mapping(a.json('results/analysis-r1.json'))
    analysis_metrics = index(analysis['metrics'])
    old_oracle = index(a.json('evidence/oracle.json'))
    summary_old = g.mapping(a.json('results/summary.json'))
    reset_old = index(summary_old['reset_v2'])
    definitions = [g.mapping(x) for x in g.sequence(f7['metrics'])]
    records, files, frequency, settled = [], [], [], []
    coverage: dict[str, dict[str, int]] = {}
    reset_evidence: dict[str, object] = {}
    main_sg: tuple[g.Frame, ...] | None = None
    checked_frames = blocked = pairs = 0
    for arm in ARMS:
      for cohort in ('', '-reset-v2'):
        cat1, cat2 = catalog(a, arm, cohort, 1), catalog(a, arm, cohort, 2)
        need(cat1 == cat2 and len(cat1) == (1 if cohort else 37), 'F8_CATALOG_REPEAT')
        need({g.text(c['id']) for c in cat1} == ({'initial_reset'} if cohort else set(specs)), 'F8_CATALOG_COHORT')
        for item in cat1:
          name = g.text(item['id'])
          spec = specs[name]
          need(item['arm'] == arm, 'F8_ARM_IDENTITY')
          if item['status'] != 'PREFLIGHT_BLOCKED':
            need(item['group'] == spec['group'], 'F8_GROUP_IDENTITY')
          need(item['input_sha256'] == g.sha(g.canonical(spec)), 'F8_INPUT_SHA')
          domain = mathematical_domain(spec, arm)
          need(g.mapping(item['domain'])['admitted'] == domain['candidate_domain_admitted'], 'F8_DOMAIN_BINDING')
          if not cohort:
            group = g.text(spec['group'])
            counts = coverage.setdefault(group, {'planned': 0, 'executed': 0, 'blocked': 0, 'frames': 0})
            counts['planned'] += 1
          if item['status'] == 'PREFLIGHT_BLOCKED':
            need(not cohort and arm == 'A2' and domain['candidate_domain_admitted'] is False and item['frames'] == 0, 'F8_PREFLIGHT_BLOCK')
            blocked += 1
            counts['blocked'] += 1
            records.append(
              {
                'arm': arm,
                'scenario': name,
                'cohort': 'main',
                'status': 'STRUCTURALLY_BLOCKED',
                'reason': 'A2_DEVELOPMENT_ENVELOPE_SOURCE_DOMAIN',
                'domain': domain,
              }
            )
            continue
          need(item['input_sha256'] == g.sha(g.canonical(spec)), 'F8_INPUT_SHA')
          source = source_identity(item, spec, reset_lock if cohort else main_lock, contract)
          mode = (
            'RESET_MODE_B'
            if cohort
            else (('RESET_MODE_A' if arm == 'SG-A' else 'SOURCE_DEFINED_OPTIMIZER_EVENT_RESET') if spec['reset_sequence'] is not None else 'NO_EXPLICIT_RESET')
          )
          paths = [f'results/{arm}{cohort}-r{rep}/{name}.json.gz' for rep in (1, 2)]
          need(a.expected[paths[0]]['sha256'] == a.expected[paths[1]]['sha256'] == item['compressed_sha256'], 'F8_REPEAT_TRACE_SHA')
          raw_trace = a.trace(paths[0])
          need(a.last_trace_sha256 == item['trace_sha256'], 'F8_DECODED_TRACE_SHA')
          frames = verify_trace(raw_trace, item, spec, mode, source)
          window = d.reset_window(raw_trace, spec)
          del raw_trace
          # Equal verified compressed bytes bind rep2 to the same decoded frame buffer.
          need(a.raw(paths[1]) == a.raw(paths[0]), 'F8_REPEAT_TRACE_BYTES')
          pairs += 1
          checked_frames += len(frames)
          if not cohort:
            counts['executed'] += 1
            counts['frames'] += len(frames)
          scalar = d.scalar_metrics(frames)
          historical = g.mapping(reset_old[(arm, name)]['metrics']) if cohort else g.mapping(analysis_metrics[(arm, name)]['metrics'])
          for key, value in scalar.items():
            near(value, historical[key])
          if not cohort:
            oracle = old_oracle[(arm, name)]
            need(oracle['trace_sha256'] == item['trace_sha256'] and oracle['status'] == 'ARITHMETIC_VERIFIED', 'F8_ORACLE_BINDING')
            for key, value in g.mapping(oracle['scalar']).items():
              near(scalar[key], value)
          calculated = m.calculate(frames, g.mapping(g.PLANT), arm, definitions)
          need(Counter(x['status'] for x in calculated.values()) == {'METRIC_COMPUTED': 22, 'METRIC_UNAVAILABLE': 6}, 'F8_F7_STATUS_CHANGED')
          evidence_id = f'{arm}{"-reset-v2" if cohort else "-main"}-{name}'
          diag = {
            'namespace': NAMESPACE,
            'evidence_id': evidence_id,
            'evidence_schema': contract['schema'],
            'historical_namespace': spec['namespace'],
            'evidence_source_head': contract['evidence_source_head'],
            'independent_oracle_status': 'PLANT_YAW_HEADING_POSE_ARITHMETIC_VERIFIED',
            'native_pid_recurrence_status': 'NOT_RECOMPUTED_SOURCE_PROFILE_AND_FEEDBACK_BINDING_ONLY',
            'version': 1,
            'effective': False,
            'diagnostic_only': True,
            'performance_qualified': False,
            'runtime_authorized': False,
            'vehicle_authority': 'NONE',
            'selected_candidate': None,
            'selected_policy': None,
            'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
            'threshold_status': 'THRESHOLD_APPROVAL_REQUIRED',
            'status': 'STRUCTURALLY_VALID',
            'input_sha256': item['input_sha256'],
            'initial_state_sha256': item['initial_state_sha256'],
            'declared_initial_physical_state': spec['initial'],
            'trace_sha256': item['trace_sha256'],
            'repeat_trace_sha256': cat2[cat1.index(item)]['trace_sha256'],
            'source_sha256': source,
            'plant_sha256': item['plant_sha256'],
            'native_identity': item['native_identity'],
            'policy_sha256': item['policy_sha256'],
            'frames': len(frames),
            'timebase': {'start_ns': 0, 'dt_ns': g.TIME_NS, 'post_step_metrics': True},
            'units': {
              'curvature': 'm^-1',
              'yaw': 'rad/s',
              'heading': 'rad',
              'position': 'm',
              'command': 'normalized',
              'positive_command': 'negative_curvature_negative_plant_input',
            },
            'reset_mode': mode,
            'measurement': spec['measurement'],
            'domain': domain,
            'F7_metrics': calculated,
            'F7_gate_definitions_reference': f7['hard_gates'],
            'F7_historical_gate_execution': 'NOT_RUN_DIFFERENT_SCHEMA',
            'F7_embedded_gate_labels': 'References only; verified by F8 verify_trace, not an F7 historical gate PASS',
            'F8_validation_scope': (
              'Pinned identity; source/profile/feedback state binding; candidate/Plant/pose arithmetic. Native PID/filter recurrence NOT recomputed.'
            ),
            'initial_derivative_sidecar': d.initial_aware_derivative(frames, g.number(g.mapping(spec['initial'])['applied_last'])),
            'reset_window': window,
          }
          severe = g.mapping(contract['severe_observation'])
          if item['trace_sha256'] == severe['trace_sha256']:
            near(scalar['normal_rms'], severe['normal_rms_m'])
            near(scalar['saturation_fraction'], severe['stock_rail_occupancy'])
            diag['observed_deviation'] = severe
          files.append(out.write(f'{evidence_id}.json', diag))
          records.append(
            {
              'evidence_id': evidence_id,
              'arm': arm,
              'scenario': name,
              'cohort': 'reset-v2' if cohort else 'main',
              'status': 'STRUCTURALLY_VALID',
              'reset_mode': mode,
              'scalar': scalar,
              'trace_sha256': item['trace_sha256'],
              'domain': domain,
            }
          )
          if spec['reset_sequence'] is not None:
            reset_evidence[evidence_id] = {'reset_mode': mode, 'window': window, 'scalar': scalar}
          if arm == 'SG-A' and name == 'initial_reset':
            if not cohort:
              main_sg = frames
            else:
              need(main_sg is not None, 'F8_RESET_COMPARISON')
              if main_sg is not None:
                reset_evidence['SG-A_mode_comparison'] = m.compare(main_sg, frames)
                main_sg = None
          if not cohort:
            frequency_spec = spec['frequency']
            if frequency_spec is not None:
              hz = g.number(g.mapping(frequency_spec)['hz'])
              for kind in ('periodic_hann', 'rectangular'):
                estimate = d.tone(frames, hz, kind)
                direct = d.direct_tone(frames, hz, kind)
                for key, value in direct.items():
                  near(value, estimate[key])
                frequency.append({'arm': arm, 'id': name, 'amplitude': g.mapping(frequency_spec)['amplitude'], **estimate, 'independent_oracle': direct})
            settled.extend({'arm': arm, 'id': name, **row} for row in d.settling(frames, spec))
          del frames, calculated, diag
    need(pairs == 149 and blocked == 3 and checked_frames == 370000, 'F8_COHORT_TOTAL')
    need(coverage == summary_old['coverage_unique'], 'F8_COVERAGE_RECONCILIATION')
    need(len(frequency) == 72 and len(settled) == 909, 'F8_DIAGNOSTIC_COUNT')
    near(settled, analysis['settling_grid'])
    old_frequency = {(r['arm'], r['id'], r['window']): r for r in (g.mapping(x) for x in g.sequence(analysis['frequency']))}
    for record in frequency:
      prior = old_frequency[(record['arm'], record['id'], record['window'])]
      for key in ('gain', 'phase_rad', 'coherence', 'ls_gain', 'ls_phase_rad'):
        near(record[key], prior[key])
    a.finish()
    sources = {
      name: digest(source_bytes('tools/cyberpilot/' + name))
      for name in ('offline_f8_evidence_v1.py', 'f8_evidence_reader_v1.py', 'f8_evidence_validation_v1.py', 'f8_evidence_diagnostics_v1.py')
    }
    need(sources == sources_before, 'F8_ADAPTER_SOURCE_MUTATION')
    payload = {
      'namespace': NAMESPACE,
      'complete': True,
      'effective': False,
      'diagnostic_only': True,
      'performance_qualified': False,
      'runtime_authorized': False,
      'vehicle_authority': 'NONE',
      'selected_candidate': None,
      'selected_policy': None,
      'authority': contract['authority'],
      'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
      'threshold_status': 'THRESHOLD_APPROVAL_REQUIRED',
      'contract_sha256': CONTRACT_SHA,
      'adapter_sources': sources,
      'evidence_source_head': contract['evidence_source_head'],
      'archive_sha256': root['archive_sha256'],
      'historical_receipt': historical_receipt['receipt_sha256'],
      'trust_scope': root['authentication'],
      'cohort': contract['cohort'],
      'coverage': coverage,
      'records': records,
      'six_metric_sidecar_status': contract['metric_evidence_status'],
      'frequency': frequency,
      'settling_grid': settled,
      'reset_ownership': reset_evidence,
      'F7_effective': False,
      'F7_historical_gate_execution': 'NOT_RUN_DIFFERENT_SCHEMA',
      'F7_metrics_per_trace': {'METRIC_COMPUTED': 22, 'METRIC_UNAVAILABLE': 6},
      'native_controller_executions_by_adapter': 0,
      'raw_data_published': False,
      'reader_processed': {'member_bytes': a.member_processed, 'decoded_bytes': a.inner_processed},
      'diagnostic_files': files,
    }
    payload['receipt_sha256'] = g.sha(g.canonical(payload))
    out.write('summary.json', payload)
    out.remove_marker()
    return payload


def no_transport(event: str, args: tuple[object, ...]) -> None:
  # Defense in depth for the CLI. This is not a general-purpose Python sandbox.
  if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
    raise F8Error('F8_NO_TRANSPORT')
  if event == 'open' and args and isinstance(args[0], (str, bytes)):
    path = args[0].decode() if isinstance(args[0], bytes) else args[0]
    need(not path.startswith(('/data/params', '/dev/')) or path in ('/dev/null', '/dev/random', '/dev/urandom'), 'F8_NO_VEHICLE_INTERFACE')


class Parser(argparse.ArgumentParser):
  def error(self, message: str) -> NoReturn:
    del message
    raise F8Error('F8_EXPLICIT_ARGUMENTS')


def main() -> int:
  parser = Parser(description=__doc__)
  parser.add_argument('--archive', required=True, type=Path)
  parser.add_argument('--read-root', required=True, type=Path)
  parser.add_argument('--output', required=True, type=Path)
  try:
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.addaudithook(no_transport)
    result = run(args.archive, args.read_root, args.output)
    print(g.canonical({'namespace': NAMESPACE, 'complete': True, 'receipt_sha256': result['receipt_sha256']}).decode())
    return 0
  except (F8Error, g.EvidenceError) as exc:
    print(exc.code, file=sys.stderr)
    return 2
  except (OSError, KeyError, TypeError, ValueError, ArithmeticError):
    print('F8_INVALID_EVIDENCE', file=sys.stderr)
    return 2


if __name__ == '__main__':
  raise SystemExit(main())
