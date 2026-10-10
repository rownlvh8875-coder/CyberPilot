"""Explicit supplemental source closure and narrowly scoped reviewed differences."""

import ast
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_fingerprint as f

REVIEW_PIN = '380cd79ebaba089a5e704a4ac564d2a65a58a8555a8b6c3205754ef29e569e71'
DIFF_PINS = {
  'opendbc_repo/opendbc/can/dbc.py': '8decc5fedb15fb45a8a204a45e5b4b3683ffbedcb29177025ff01d032feeb805',
  'opendbc_repo/opendbc/car/car.capnp': '01f3cef87b71f9a392adbc2126698fbe55889e28dd9ffdaa22c4f22bc7f60d75',
  'opendbc_repo/opendbc/car/hyundai/radar_interface.py': 'dff577ba9fd5cb8a6de66deac0ec956036451a101f47c484d825dd256e47060c',
  'openpilot/selfdrive/car/cruise.py': 'c8426d47fe876553b9bf8a76ad40f550e5b9acc1f31e42dafa7c2b82c0647652',
}
PAIR = ('18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29', '6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90')
DEPENDENCIES = (
  'opendbc_repo/opendbc/can/dbc.py',
  'opendbc_repo/opendbc/can/parser.py',
  'opendbc_repo/opendbc/can/packer.py',
  'opendbc_repo/opendbc/car/structs.py',
  'opendbc_repo/opendbc/car/common/conversions.py',
  'opendbc_repo/opendbc/car/common/simple_kalman.py',
  'opendbc_repo/opendbc/car/common/crc.py',
  'opendbc_repo/opendbc/car/vehicle_model.py',
  'opendbc_repo/opendbc/car/hyundai/radar_interface.py',
  'openpilot/selfdrive/car/cruise.py',
  'openpilot/selfdrive/pandad/__init__.py',
  'openpilot/common/i2c.py',
  'openpilot/common/gpio.py',
  'openpilot/common/filter_simple.py',
  'openpilot/cereal/__init__.py',
  'openpilot/cereal/include/c++.capnp',
  'openpilot/cereal/messaging/__init__.py',
  'openpilot/cereal/messaging/messaging.h',
  'openpilot/system/loggerd/zstd_writer.h',
  'openpilot/system/loggerd/zstd_writer.cc',
  'pyproject.toml',
  'uv.lock',
)


def dependency_policy():
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_DEPENDENCY_RESOLUTION_V1', 'paths': list(DEPENDENCIES),
    'predicate_symbol': ['openpilot/selfdrive/controls/lib/drive_helpers.py', 'is_volkswagen_meb'],
    'scope': 'LEGACY_HYUNDAI_SANTA_FE_2022_SIGNAL_CONTENT_AND_LOGICAL_PUBLICATION_ONLY',
    'excluded': ['RADAR_DATA', 'LIVE_TRACKS', 'LONGITUDINAL_BEHAVIOR', 'PHYSICAL_SCHEDULING_OR_CAN_ACQUISITION_AGE'],
    'physical_runtime_equivalence': False,
    'base_manifest_role_set_weakened': False,
  })


def supplement(repo, commit):
  prefix = ['git', '-c', f'safe.directory={repo}', '-C', str(repo)]
  def blob(path):
    return subprocess.check_output([*prefix, 'show', f'{commit}:{path}'])
  entries, missing = {}, []
  for path in DEPENDENCIES:
    try:
      actual = path
      if path == 'opendbc_repo/opendbc/car/common/crc.py':
        actual = 'opendbc_repo/opendbc/car/crc.py'
      entries[path] = f.source_entry(actual, blob(actual))
    except subprocess.CalledProcessError:
      missing.append(path)
  predicate_path, symbol = dependency_policy()['predicate_symbol']
  tree = ast.parse(blob(predicate_path).decode())
  node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == symbol)
  predicate = ast.get_source_segment(blob(predicate_path).decode(), node).encode()
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_DEPENDENCY_BINDING_V1', 'commit': commit,
    'dependency_policy_sha256': dependency_policy()['receipt_sha256'],
    'entries': entries, 'missing': missing,
    'predicate_file_sha256': p.sha(blob(predicate_path)), 'predicate_slice_sha256': p.sha(predicate),
    'predicate_normalized_sha256': p.sha(f.normalized_source(predicate, '.py')),
    'predicate_scope': 'BRAND_VOLKSWAGEN_AND_MEB_FLAG_FALSE_FOR_FROZEN_HYUNDAI_PROFILE',
  })


def review_pair(a, b, da, db, raw_diffs):
  """The caller supplies exact Git diff bytes; all are hash-bound before class use."""
  if tuple(sorted((a['commit'], b['commit']))) != tuple(sorted(PAIR)):
    raise ValueError('NO_REVIEWED_SEMANTIC_DIFFERENCE_FOR_PAIR')
  expected = {
    'schema_car', 'schema_dependency:opendbc_repo/opendbc/car/car.capnp',
  }
  differences = {k for k in a['files'] if a['files'][k]['file_sha256'] != b['files'][k]['file_sha256']}
  if differences != expected or da['missing'] or db['missing']:
    raise ValueError('REVIEWED_DIFFERENCE_SCOPE_CHANGED')
  dependency_diffs = {k for k in da['entries'] if da['entries'][k]['file_sha256'] != db['entries'][k]['file_sha256']}
  allowed = {'opendbc_repo/opendbc/can/dbc.py', 'openpilot/selfdrive/car/cruise.py', 'opendbc_repo/opendbc/car/hyundai/radar_interface.py'}
  if dependency_diffs != allowed or da['predicate_normalized_sha256'] != db['predicate_normalized_sha256']:
    raise ValueError('DEPENDENCY_DIFFERENCE_SCOPE_CHANGED')
  if set(raw_diffs) != allowed | {'opendbc_repo/opendbc/car/car.capnp'} or any(not x for x in raw_diffs.values()):
    raise ValueError('EXACT_DIFF_RECEIPTS_REQUIRED')
  if {path: p.sha(data) for path, data in raw_diffs.items()} != DIFF_PINS:
    raise ValueError('REVIEWED_DIFF_BYTES_CHANGED')
  return p.seal({
    'schema': 'EMPIRICAL_REVIEWED_SOURCE_DIFFERENCES_V1',
    'scope': dependency_policy()['scope'], 'commits': sorted(PAIR),
    'fingerprint_sha256': sorted([a['receipt_sha256'], b['receipt_sha256']]),
    'dependency_sha256': sorted([da['receipt_sha256'], db['receipt_sha256']]),
    'diff_sha256': {path: p.sha(data) for path, data in sorted(raw_diffs.items())},
    'facts': [
      'CAR_SCHEMA_REMOVES_RADARPOINT_RADARSOURCE_10_AND_HUDCONTROL_LEADLIMITING_21_ONLY_RETAINED_LATERAL_FIELDS_UNCHANGED',
      'DBC_LOADER_CHANGE_ONLY_VW_MEB_2024_CHECKSUM_BRANCH_HYUNDAI_GENERIC_UNCHANGED',
      'CRUISE_CHANGE_GUARDED_BY_VOLKSWAGEN_MEB_PREDICATE_FALSE_FOR_HYUNDAI_PROFILE',
      'RADAR_POINT_INITIALIZATION_AND_FILTER_CHANGED_RADARDATA_AND_LIVETRACKS_OUTSIDE_SIGNAL_SCOPE',
      'LOGGER_AND_SELECTED_CAN_STATE_COMMAND_GYRO_PRODUCERS_AND_LOGICAL_PUBLICATION_ORDER_EQUAL',
    ],
    'review': 'INDEPENDENT_SOURCE_REVIEW_LEGACY_HYUNDAI_SCOPE',
    'equivalence': 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT',
    'physical_yaw_unit': 'PENDING_DBC_UNIT_EMPTY',
    'runtime_steer_max': 'NUMERIC_CONFIRMATION_PENDING',
    'acquisition_age_and_scheduler': 'UNVERIFIED',
    'global_controller_or_radar_behavior_equivalent': False,
  })


def verify_review(review, a, b, da, db):
  for receipt in (review, a, b, da, db):
    p.verify(receipt)
  if review['receipt_sha256'] != REVIEW_PIN:
    raise ValueError('EXACT_INDEPENDENT_REVIEW_RECEIPT_REQUIRED')
  if review['fingerprint_sha256'] != sorted([a['receipt_sha256'], b['receipt_sha256']]):
    raise ValueError('REVIEW_SOURCE_HASH_MISMATCH')
  if review['dependency_sha256'] != sorted([da['receipt_sha256'], db['receipt_sha256']]):
    raise ValueError('REVIEW_DEPENDENCY_HASH_MISMATCH')
  return review['equivalence']


CLOSURE_PATHS = (
  'opendbc_repo/opendbc/__init__.py',
  'opendbc_repo/opendbc/car/carlog.py',
  'opendbc_repo/opendbc/car/torque_data/params.toml',
  'opendbc_repo/opendbc/car/torque_data/override.toml',
  'opendbc_repo/opendbc/car/torque_data/substitute.toml',
  'openpilot/common/params.py', 'openpilot/common/params_pyx.pyx',
  'openpilot/common/params.h', 'openpilot/common/params.cc', 'openpilot/common/params_keys.h',
  'openpilot/common/timing.h', 'openpilot/common/realtime.py', 'openpilot/common/utils.py',
  'msgq_repo/msgq/__init__.py', 'msgq_repo/msgq/event.cc', 'msgq_repo/msgq/event.h',
  'msgq_repo/msgq/impl_fake.cc', 'msgq_repo/msgq/impl_fake.h',
  'msgq_repo/msgq/impl_msgq.cc', 'msgq_repo/msgq/impl_msgq.h',
  'msgq_repo/msgq/ipc.cc', 'msgq_repo/msgq/ipc.h',
  'msgq_repo/msgq/ipc.pxd', 'msgq_repo/msgq/ipc_pyx.pyx',
  'msgq_repo/msgq/msgq.cc', 'msgq_repo/msgq/msgq.h',
  'msgq_repo/msgq/logger/logger.h', 'msgq_repo/pyproject.toml',
)


def closure_policy():
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_LOGICAL_TRANSPORT_CLOSURE_POLICY_V1',
    'paths': list(CLOSURE_PATHS),
    'existing_checksum_closure': ['can_builder', 'canfd_builder',
                                  'opendbc_repo/opendbc/car/common/crc.py'],
    'scope': dependency_policy()['scope'],
    'runtime_binary_or_physical_acquisition_equivalence': False,
  })


def closure(repo, commit):
  prefix = ['git', '-c', f'safe.directory={repo}', '-C', str(repo)]
  entries, missing = {}, []
  for path in CLOSURE_PATHS:
    try:
      data = subprocess.check_output([*prefix, 'show', f'{commit}:{path}'])
      entries[path] = f.source_entry(path, data)
    except subprocess.CalledProcessError:
      missing.append(path)
  return p.seal({'schema': 'EMPIRICAL_SOURCE_LOGICAL_TRANSPORT_CLOSURE_V1',
                 'commit': commit, 'policy_sha256': closure_policy()['receipt_sha256'],
                 'entries': entries, 'missing': missing})


def verify_closure(a, b, review=None):
  for receipt in (a, b):
    p.verify(receipt)
    if receipt.get('policy_sha256') != closure_policy()['receipt_sha256'] or receipt.get('missing'):
      raise ValueError('LOGICAL_SOURCE_CLOSURE_INCOMPLETE')
    if set(receipt['entries']) != set(CLOSURE_PATHS):
      raise ValueError('LOGICAL_SOURCE_CLOSURE_ROLE_MISMATCH')
  if (a['commit'], b['commit']) != PAIR:
    raise ValueError('NO_REVIEWED_CLOSURE_PAIR')
  changed = {k for k in CLOSURE_PATHS if a['entries'][k]['file_sha256'] != b['entries'][k]['file_sha256']}
  if changed:
    if review is None:
      raise ValueError('UNREVIEWED_LOGICAL_SOURCE_CLOSURE_DIFFERENCE')
    p.verify(review)
    if (review['receipt_sha256'] != CLOSURE_REVIEW_PIN or changed != set(CLOSURE_DIFF_PINS)
        or review['closure_sha256'] != [a['receipt_sha256'], b['receipt_sha256']]):
      raise ValueError('EXACT_LOGICAL_CLOSURE_REVIEW_REQUIRED')
  return True


CLOSURE_REVIEW_PIN = '76b27aeb86b355e82b6bbf6b4b9b5a590faf36e52de034acb8f098ffccb08f82'
CLOSURE_DIFF_PINS = {
  'opendbc_repo/opendbc/car/torque_data/override.toml': '5c6ed4a11e16b83e6c6e2de47af349b2a9bbd18308a02b031b2c6ec597ad164d',
  'openpilot/common/params_keys.h': 'df3b08610e78498e919e26db2d76cdc112f2ae1d9f3605ee8e07a2cf3925724c',
}


def review_closure_pair(a, b, diffs):
  for receipt in (a, b):
    p.verify(receipt)
  if (a['commit'], b['commit']) != PAIR:
    raise ValueError('NO_REVIEWED_CLOSURE_PAIR')
  if {k: p.sha(v) for k, v in diffs.items()} != CLOSURE_DIFF_PINS:
    raise ValueError('EXACT_CLOSURE_DIFF_BYTES_REQUIRED')
  return p.seal({
    'schema': 'EMPIRICAL_LOGICAL_CLOSURE_REVIEW_V1',
    'diff_options': ['--abbrev=8', '--no-color', '--no-ext-diff', '--no-textconv', '--unified=3'],
    'closure_sha256': [a['receipt_sha256'], b['receipt_sha256']],
    'diff_sha256': CLOSURE_DIFF_PINS, 'commits': list(PAIR),
    'scope': dependency_policy()['scope'],
    'facts': ['ONLY_VW_ID4_MK2_TORQUE_OVERRIDE_ROW_REMOVED_HYUNDAI_PROFILE_UNCHANGED',
              'ONLY_UI_CARROT_TIRE_TRAJECTORY_PARAM_KEY_REMOVED_CUSTOM_STEER_MAX_AND_PARAM_IMPL_UNCHANGED',
              'MSGQ_SOURCE_TRANSPORT_TIMING_AND_DBC_PATH_IDENTICAL'],
    'physical_runtime_equivalence': False,
  })
