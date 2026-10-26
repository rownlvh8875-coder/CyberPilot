"""Exact public logger blobs; parsing is static and never executes upstream source."""
import ast
import math
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base

COMMIT = '18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29'
REPOSITORY = 'https://github.com/ajouatom/openpilot'
FILES = {
  'services': ('openpilot/cereal/services.py', '9f44630c58622ad7285de56b80ca357ce9797904e4c2dd46fce19bb60a84c7dd'),
  'loggerd': ('openpilot/system/loggerd/loggerd.cc', '09b91ed7fc0517b8f0aa34eba2c3278a4ff87d6312fa4afca3cac7fcb8c3b160'),
  'logger': ('openpilot/system/loggerd/logger.cc', 'ddf2ffb10b871d466f17d13859e2cdeac4b454573a495f82ebac45f303ef9ccd'),
  'logger_header': ('openpilot/system/loggerd/logger.h', '66eb66cfa79326994aa2f38953ee48d31bea0f5356ae3d6fe0de1f8c30ed406d'),
}
EXPECTED = {'carState': (100., 10), 'carControl': (100., 10), 'carOutput': (100., 10),
            'gyroscope': (104., 104), 'carParams': (0.02, 1)}


def require_source(commit, source):
  if commit != COMMIT or source.get('commit') != COMMIT or source.get('repository') != REPOSITORY or not source.get('complete'):
    raise ValueError('QLOG_EXACT_AUDITED_PUBLIC_SOURCE_REQUIRED')


def service_policy(text):
  assignments = []
  for node in ast.parse(text).body:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    if any(isinstance(t, ast.Name) and t.id == '_services' for t in targets):
      assignments.append(node)
  if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Dict):
    raise ValueError('LITERAL_SERVICE_POLICY_REQUIRED')
  result = {}
  for key, value in zip(assignments[0].value.keys, assignments[0].value.values, strict=True):
    if not isinstance(value, ast.Tuple) or len(value.elts) not in (2, 3, 4):
      raise ValueError('LITERAL_SERVICE_TUPLE_REQUIRED')
    name = ast.literal_eval(key)
    enabled = ast.literal_eval(value.elts[0])
    frequency_node = value.elts[1]
    if isinstance(frequency_node, ast.BinOp) and isinstance(frequency_node.op, ast.Div):
      left, right = ast.literal_eval(frequency_node.left), ast.literal_eval(frequency_node.right)
      if type(left) not in (int, float) or type(right) not in (int, float) or right == 0:
        raise ValueError('INVALID_CONSTANT_FREQUENCY_DIVISION')
      frequency = left / right
    else:
      frequency = ast.literal_eval(frequency_node)
    decimation = ast.literal_eval(value.elts[2]) if len(value.elts) >= 3 else None
    if type(decimation) is float and math.isfinite(decimation) and decimation.is_integer():
      decimation = int(decimation)
    if (name in result or not isinstance(name, str) or type(enabled) is not bool
        or type(frequency) not in (int, float) or not math.isfinite(frequency) or frequency < 0
        or (decimation is not None and (type(decimation) is not int or decimation <= 0))):
      raise ValueError('INVALID_SERVICE_POLICY')
    result[name] = {'should_log': enabled, 'frequency': frequency, 'decimation': decimation}
  return result


def audit(repo, source):
  require_source(source['commit'], source)
  texts, bindings = {}, {}
  for role, (path, expected) in FILES.items():
    data = subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo), 'show', COMMIT+':'+path])
    if p.sha(data) != expected:
      raise ValueError('QLOG_LOGGER_SOURCE_DRIFT')
    texts[role] = data.decode()
    bindings[role] = {'path': path, 'file_sha256': expected, 'source_slice_sha256': expected,
                      'scope': 'EXACT_FULL_FILE_REVIEWED_SLICE'}
  services = service_policy(texts['services'])
  for name, (frequency, decimation) in EXPECTED.items():
    if services[name] != {'should_log': True, 'frequency': frequency, 'decimation': decimation}:
      raise ValueError('QLOG_SERVICE_CADENCE_CONFLICT')
  facts = {
    'retained_event': 'UNCHANGED_EVENT_BYTES_LOGMONOTIME_VALID_AND_BODY_PRESERVED',
    'selection': 'PER_SERVICE_COUNTER_MODULO_DECIMATION_FIRST_COUNTER_ZERO',
    'counter_rotation': 'COUNTER_PERSISTS_ACROSS_SEGMENT_ROTATION_RESETS_AT_LOGGERD_START',
    'message_order': 'PER_SERVICE_ARRIVAL_ORDER_NO_GLOBAL_TIMESTAMP_SORT_OR_TRANSACTION_ID',
    'init_data': 'ONCE_PER_LOGGERSTATE_REUSED_EVERY_SEGMENT_BOTH_STREAMS',
    'car_params': 'DECIMATION_ONE_ALL_PUBLISHED_MESSAGES_RETAINED',
    'rotation': 'RLOG_QLOG_OPEN_TOGETHER_SHARED_ORDINAL_SENTINELS_TO_BOTH',
    'excluded_services': 'DECIMATION_NONE_EXCLUDED_ORDINARY_SERVICE_MESSAGES',
    'forbidden_services': 'MAY_EXIST_IN_QLOG_ENVELOPE_BODY_NEVER_DEREFERENCED',
  }
  matrix = {event+'.'+field: ('EXACT_EQUIVALENT' if event in ('initData', 'carParams')
                            else 'DOWNSAMPLED_BUT_SEMANTICALLY_EQUIVALENT')
            for event, fields in base.WHITELIST.items() for field in fields}
  return p.seal({'schema': 'EMPIRICAL_QLOG_SOURCE_SEMANTICS_V1', 'status': 'QLOG_SOURCE_SEMANTICS_COMPLETE',
    'repository': REPOSITORY, 'commit': COMMIT, 'files': bindings, 'services': services, 'facts': facts,
    'source_fingerprint_sha256': source['receipt_sha256'], 'licenses': source['licenses'],
    'license_status': source['license_status'], 'equivalence': matrix,
    'live_submaster_health': 'NOT_AVAILABLE', 'physical_eps_application': 'NOT_AVAILABLE',
    'schema_and_signal_semantics': 'EXACT_EXISTING_SOURCE_FINGERPRINT_NO_PHYSICAL_UNIT_PROMOTION',
    'cadence_admission': 'RETAIN_100HZ_GRID_20MS_AGE_NULL_GAP_NO_INTERPOLATION'})
