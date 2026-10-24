"""Source-specific metadata adapter; no driving message body accessor."""

from collections import Counter
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_fingerprint as fingerprint

PROFILE_FIELDS = (
  'carFingerprint', 'steerControlType', 'steerRatio', 'wheelbase', 'centerToFront',
  'extFlags', 'steerRatioRear', 'steerAtStandstill', 'mass', 'tireStiffnessFront', 'tireStiffnessRear', 'lateralTuning', 'flags',
  'safetyConfigs', 'minSteerSpeed', 'steerActuatorDelay', 'steerLimitTimer',
  'steeringAngleDeadzoneDeg', 'brand', 'carName', 'radarUnavailable',
  'enableBsm', 'transmissionType', 'alternativeExperience',
)


def validate_adapter(binding, source):
  p.verify(binding)
  p.verify(source)
  if binding['source_fingerprint_sha256'] != source['receipt_sha256'] or binding['commit'] != source['commit']:
    raise ValueError('SOURCE_SPECIFIC_ADAPTER_MISMATCH')
  if not source['complete'] or binding.get('logger_reviewed') is not True or binding.get('schema_reviewed') is not True:
    raise ValueError('SOURCE_METADATA_REVIEW_REQUIRED_NO_GENERIC_FALLBACK')
  if binding.get('adapter_source_sha256') != p.sha(Path(__file__).read_bytes()):
    raise ValueError('ADAPTER_CODE_DRIFT')


def same_profile(a, b, irrelevant_field_proof=None):
  if a['full_carparams_sha256'] == b['full_carparams_sha256']:
    return True
  if a['empirical_profile_sha256'] != b['empirical_profile_sha256']:
    return False
  if irrelevant_field_proof is None:
    return False
  p.verify(irrelevant_field_proof)
  return (irrelevant_field_proof.get('full_hashes') == sorted([a['full_carparams_sha256'], b['full_carparams_sha256']])
          and irrelevant_field_proof.get('changed_fields')
          and not set(irrelevant_field_proof['changed_fields']) & set(PROFILE_FIELDS)
          and irrelevant_field_proof.get('reviewed_irrelevant') is True)


def route_classification(original, metadata_ok, source_origin, physical_reasons=()):
  if original['v1_overlap']:
    return 'ROUTE_SOURCE_AUDITED_DUPLICATE'
  if physical_reasons or original['status'] == 'ROUTE_CORRUPT_OR_INCOMPLETE':
    return 'ROUTE_SOURCE_AUDITED_INCOMPLETE'
  if original['status'] == 'ROUTE_IDENTITY_AMBIGUOUS' or source_origin != 'SOURCE_COMMIT_PUBLICLY_AVAILABLE':
    return 'ROUTE_SOURCE_AUDITED_IDENTITY_AMBIGUOUS'
  return 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE' if metadata_ok else 'ROUTE_SOURCE_AUDITED_INCOMPLETE'


def metadata(events, expected_commit, public_attested):
  initial, profiles, clocks = [], [], []
  counts, last = Counter(), {}
  for event in events:
    kind = event.which()
    counts[kind] += 1
    if kind in ('carState', 'carOutput', 'carControl'):
      clock = int(event.logMonoTime)
      if clock <= last.get(kind, -1):
        raise ValueError('NONMONOTONIC_LINEAGE')
      last[kind] = clock
      clocks.append(clock)
    elif kind == 'initData':
      x = event.initData
      if str(x.gitCommit) != expected_commit:
        raise ValueError('RECORDED_SOURCE_COMMIT_MISMATCH')
      remote = str(x.gitRemote)
      initial.append({
        'commit': str(x.gitCommit), 'remote': remote, 'branch_sha256': p.sha(str(x.gitBranch).encode()),
        'version_sha256': p.sha(str(x.version).encode()), 'dirty': bool(x.dirty), 'os_version': str(x.osVersion),
        'origin_status': fingerprint.origin_identity(remote, str(x.gitCommit), bool(x.dirty), public_attested),
        'logger_start_sha256': p.sha(p.canonical({
          'init_envelope_ns': int(event.logMonoTime), 'wall_ns': int(x.wallTimeNanos),
          'boot_sha256': p.sha(str(x.bootlogId).encode()), 'device_sha256': p.sha(str(x.dongleId).encode()),
        })),
      })
    elif kind == 'carParams':
      x = event.carParams
      fields = {}
      for name in PROFILE_FIELDS:
        if name not in x.schema.fields:
          fields[name] = None
          continue
        value = getattr(x, name)
        if hasattr(value, 'to_dict'):
          value = value.to_dict()
        elif name == 'safetyConfigs':
          value = [v.to_dict() for v in value]
        elif not isinstance(value, (str, int, float, bool)):
          value = str(value)
        fields[name] = value
      profiles.append({
        'full_carparams_sha256': p.sha(x.as_builder().to_bytes()),
        'empirical_profile_sha256': p.sha(p.canonical(fields)), 'fields': fields,
        'runtime_steer_max': None, 'steer_max_status': 'RUNTIME_STEER_MAX_NUMERIC_CONFIRMATION_PENDING',
        'bus_configuration': 'SOURCE_BOUND_CONFIGURATION_RUNTIME_METADATA_REVIEW_PENDING',
      })
  if not initial or not profiles or not clocks:
    raise ValueError('MISSING_MANDATORY_METADATA')
  if len({p.sha(p.canonical(x)) for x in initial}) != 1 or len({p.sha(p.canonical(x)) for x in profiles}) != 1:
    raise ValueError('MIXED_SOURCE_OR_CARPARAMS')
  return {'init': initial[0], 'profile': profiles[0], 'envelope_counts': dict(counts),
          'first_ns': min(clocks), 'last_ns': max(clocks), 'numeric_payloads_opened': False}


def schema_from_source(source, directory):
  """Only exact schema blobs from the fingerprint; never import runtime producers."""
  import capnp
  directory = Path(directory)
  for role, row in source['files'].items():
    if role.startswith('schema_'):
      path = directory / row['path']
      if not path.is_file() or p.sha(path.read_bytes()) != row['file_sha256']:
        raise ValueError('SOURCE_SCHEMA_BLOB_MISMATCH')
  log_path = directory / source['files']['schema_log']['path']
  car_path = directory / source['files']['schema_car']['path']
  return capnp.load(str(log_path), imports=[str(log_path.parent), str(car_path.parent)])


def train_dev_pool(routes):
  eligible = [x for x in routes if x['classification'] == 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE'
              and x.get('signal_semantics_complete') is True and x.get('profile_complete') is True and isinstance(x.get('full_carparams_sha256'), str)
              and not x['v1_overlap']]
  groups = {}
  for x in eligible:
    groups.setdefault((x['semantic_class_id'], x['empirical_profile_sha256'], x['full_carparams_sha256']), []).append(x['route_id'])
  pools = [{'semantic_class_id': key[0], 'empirical_profile_sha256': key[1], 'full_carparams_sha256': key[2], 'route_ids': sorted(set(ids)),
            'roles': ['TRAIN_CANDIDATE', 'DEVELOPMENT_CANDIDATE'], 'holdout_allowed': False}
           for key, ids in sorted(groups.items()) if len(set(ids)) >= 2]
  return p.seal({'schema': 'SOURCE_AUDITED_TRAIN_DEV_POOL_V1', 'pools': pools,
                 'status': 'SOURCE_AUDITED_TRAIN_DEV_POOL_AVAILABLE' if pools else 'NO_MULTI_ROUTE_EQUIVALENCE_CLASS',
                 'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED', 'numeric_split_created': False})
