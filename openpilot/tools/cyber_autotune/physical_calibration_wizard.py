"""Explicit local stationary observations -> unchanged structural admission. No calibration fit."""

import math
import os
from pathlib import Path
import stat
import tempfile
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

MAX_ATTACHMENT_BYTES = 32 * 1024 * 1024  # Explicit local file resource cap, not evidence threshold.
SCHEMA = 'PHYSICAL_CALIBRATION_WIZARD_V1'
EXTRA_UNITS = {'ground_vertical_m': 'm', 'distortion_residual_px': 'px'}
OBS_KEYS = (
  'value',
  'unit',
  'uncertainty',
  'uncertainty_unit',
  'method',
  'source_kind',
  'tier',
  'instrument_type',
  'instrument_resolution',
  'instrument_unit',
  'source_evidence_id',
  'instrument_evidence_id',
  'uncertainty_evidence_id',
  'uncertainty_method',
  'note',
)
FORBIDDEN = ('modelV2', 'cameraOdometry', 'liveCalibration', 'calibrationd', 'candidate', 'planner')
TARGET_KEYS = ('width_m', 'height_m', 'distance_m', 'absolute_bound_m', 'geometry_note', 'target_evidence_id', 'geometry_evidence_id')
INSTRUMENTS = {
  'TAPE_MEASURE': ('TIER_B', ('m',)),
  'LASER_DISTANCE': ('TIER_B', ('m',)),
  'INCLINOMETER': ('TIER_B', ('rad',)),
  'DIGITAL_LEVEL': ('TIER_B', ('rad',)),
  'SURVEYED_TARGET_SOLUTION': ('TIER_A', ('m', 'rad', 'px')),
  'INDEPENDENT_METROLOGY_RECORD': ('TIER_B', ('m', 'rad', 'px')),
}
STATIC_KEYS = ('fx_px', 'fy_px', 'cx_px', 'cy_px')


def asset_hashes():
  root = Path(__file__).with_name('physical_calibration_assets')
  return {name: digest((root / name).read_bytes()) for name in ('wizard.html', 'wizard.css', 'wizard.js')}


def identity():
  ui = Path(__file__).with_name('physical_calibration_wizard_ui.py')
  return digest(
    canonical(
      {
        'schema': SCHEMA,
        'assets': asset_hashes(),
        'source': digest(Path(__file__).read_bytes()),
        'admission': c.identity(),
        'ui': digest(ui.read_bytes()) if ui.exists() else None,
      }
    )
  )


def blank_draft():
  return {
    'camera': dict.fromkeys(('device', 'hardware_generation', 'sensor', 'view', 'unit_id', 'hardware_evidence_id')),
    'general': {'version_id': None, 'operator_id': None, 'timestamp': None, 'method': None, 'note': '', 'independence_confirmed': False},
    'observations': {k: {**dict.fromkeys(OBS_KEYS), 'note': ''} for k in {**c.UNITS, **EXTRA_UNITS}},
    'mount': {'datum_description': None, 'evidence_id': None, 'convention_confirmed': False},
    'ground': {'surface_method': None, 'slope_bound_deg': None, 'evidence_id': None},
    'distortion': {'state': None, 'evidence_id': None},
    'target': dict.fromkeys(TARGET_KEYS),
  }


def validate_draft(draft):
  template = blank_draft()
  c.exact(draft, template)
  for key in template:
    c.exact(draft[key], template[key])
  for row in draft['observations'].values():
    c.exact(row, OBS_KEYS)
  canonical(draft)  # Reject nonfinite/non-JSON input even in editable drafts.


def text(value):
  if type(value) is not str or not value.strip() or len(value) > 4096:
    raise ValueError('EXPLICIT_OBSERVATION_TEXT_REQUIRED')
  return value


def opaque(value):
  return digest(text(value).encode())


def evidence_ref(attachments, value):
  c.sha(value)
  matches = [a for a in attachments if a['opaque_id'] == value]
  if len(matches) != 1:
    raise ValueError('SELECT_EXISTING_LOCAL_EVIDENCE_REQUIRED')
  return matches[0]['sha256']


def map_observation(key, row, attachments):
  """UI unit conversion/provenance adapter only; c.admit is authoritative."""
  target_unit = ({**c.UNITS, **EXTRA_UNITS})[key]
  c.number(row['value'])
  c.number(row['uncertainty'], positive=True)
  if row['unit'] != row['uncertainty_unit']:
    raise ValueError('VALUE_UNCERTAINTY_UNIT_MISMATCH')
  angular = target_unit == 'rad'
  if row['unit'] not in (('rad', 'deg') if angular else (target_unit,)):
    raise ValueError('UNSUPPORTED_EXPLICIT_UNIT')
  if row['source_kind'] in FORBIDDEN:
    raise ValueError('MODEL_DERIVED_OR_CANDIDATE_SOURCE_FORBIDDEN')
  static = key in STATIC_KEYS
  if row['source_kind'] != ('STATIC_SOURCE' if static else 'PHYSICAL_OBSERVATION'):
    raise ValueError('EXPLICIT_PHYSICAL_VS_STATIC_PROVENANCE_REQUIRED')
  if row['tier'] not in ('TIER_A', 'TIER_B'):
    raise ValueError('PHONE_OR_INFORMAL_TIER_NOT_INDEPENDENT_ADMISSION')
  c.number(row['instrument_resolution'], positive=True)
  if row['instrument_unit'] not in ({'m': ('m', 'mm'), 'rad': ('rad', 'deg'), 'px': ('px',)})[target_unit]:
    raise ValueError('INSTRUMENT_RESOLUTION_UNIT_REQUIRED')
  kind = row['instrument_type']
  if type(kind) is not str or kind not in INSTRUMENTS:
    raise ValueError('TYPED_INDEPENDENT_INSTRUMENT_REQUIRED')
  tier, dimensions = INSTRUMENTS[kind]
  if tier != row['tier'] or target_unit not in dimensions:
    raise ValueError('INSTRUMENT_TIER_AND_OBSERVATION_DIMENSION_MISMATCH')
  if kind == 'SURVEYED_TARGET_SOLUTION' and row['method'] not in c.METHODS[:3]:
    raise ValueError('SURVEYED_TARGET_METHOD_REQUIRED')
  if row['uncertainty_method'] != 'METROLOGY_REVIEW':
    raise ValueError('DECLARED_INDEPENDENT_METROLOGY_REVIEW_REQUIRED')
  source = evidence_ref(attachments, row['source_evidence_id'])
  instrument = evidence_ref(attachments, row['instrument_evidence_id'])
  uncertainty = evidence_ref(attachments, row['uncertainty_evidence_id'])
  if row['method'] not in (('PINNED_HARDWARE_NOMINAL',) if static else c.METHODS):
    raise ValueError('SUPPORTED_SURVEY_METHOD_REQUIRED')
  conversion = math.radians if row['unit'] == 'deg' else lambda v: v
  return {
    'value': conversion(row['value']),
    'unit': target_unit,
    'method': row['method'],
    'provenance': {
      'role': 'STATIC_INTRINSICS' if static else 'INDEPENDENT_PHYSICAL',
      'source_sha256': c.CAMERA_SHA if static else digest(canonical({'original_input': row, 'source_evidence_sha256': source, 'wizard_sha256': identity()})),
      'instrument_sha256': instrument,
      'model_outputs_used': False,
      'candidate_outputs_used': False,
    },
    'uncertainty': {
      'kind': 'ABSOLUTE_BOUND',
      'value': conversion(row['uncertainty']),
      'unit': target_unit,
      'method': 'METROLOGY_REVIEW',
      'provenance_sha256': uncertainty,
    },
  }


def measurement(draft, attachments, scope):
  validate_draft(draft)
  if scope not in c.SCOPES:
    raise ValueError('EXPLICIT_ADMISSION_SCOPE_REQUIRED')
  raw = draft['camera']
  camera = {k: raw[k] for k in ('device', 'hardware_generation', 'sensor', 'view')}
  camera.update(unit_id_sha256=opaque(raw['unit_id']), hardware_evidence_sha256=evidence_ref(attachments, raw['hardware_evidence_id']))
  intrinsics = c.intrinsics(camera)
  g = draft['general']
  c.utc(g['timestamp'])
  if g['independence_confirmed'] is not True:
    raise ValueError('EXPLICIT_PHYSICAL_NON_MODEL_CONFIRMATION_REQUIRED')
  if g['method'] not in c.METHODS:
    raise ValueError('SUPPORTED_MEASUREMENT_METHOD_REQUIRED')
  text(draft['mount']['datum_description'])
  if draft['mount']['convention_confirmed'] is not True:
    raise ValueError('VEHICLE_DATUM_CONVENTION_CONFIRMATION_REQUIRED')
  text(draft['ground']['surface_method'])
  c.number(draft['ground']['slope_bound_deg'], positive=True)
  if draft['ground']['slope_bound_deg'] >= 90:
    raise ValueError('NONDEGENERATE_GROUND_SURVEY_BOUND_REQUIRED')
  evidence_ref(attachments, draft['ground']['evidence_id'])
  if draft['distortion']['state'] != 'INDEPENDENTLY_BOUNDED_UNDISTORTED_RESIDUAL':
    raise ValueError('DISTORTION_VALIDATION_PENDING')
  evidence_ref(attachments, draft['distortion']['evidence_id'])
  if g['method'] != 'OPTICAL_CENTER_SURVEY' or any(o['tier'] == 'TIER_A' or o['method'] in c.METHODS[:3] for o in draft['observations'].values()):
    for key in ('width_m', 'height_m', 'distance_m', 'absolute_bound_m'):
      c.number(draft['target'][key], positive=True)
    text(draft['target']['geometry_note'])
    for key in ('target_evidence_id', 'geometry_evidence_id'):
      evidence_ref(attachments, draft['target'][key])
  obs = {k: map_observation(k, row, attachments) for k, row in draft['observations'].items()}
  value = {
    'schema': c.SCHEMA['schema'],
    'scope': scope,
    'measurement_id_sha256': digest(canonical({'version': text(g['version_id']), 'camera': camera, 'timestamp': g['timestamp']})),
    'camera': camera,
    'timestamp': g['timestamp'],
    'operator_id_sha256': opaque(g['operator_id']),
    'method': g['method'],
    'human_acknowledgement': True,
    'intrinsics_sha256': intrinsics['receipt_sha256'],
    'schema_sha256': c.SCHEMA_SHA,
    'tool_sha256': c.identity(),
    'observations': {k: obs[k] for k in c.UNITS},
    'mounting_reference': {
      'definition': 'SURVEYED_VEHICLE_ORIGIN_TO_OPTICAL_CENTER',
      'convention': c.VEHICLE_FRAME,
      'evidence_sha256': evidence_ref(attachments, draft['mount']['evidence_id']),
    },
    'ground_surface': {'assumption': 'LOCALLY_SURVEYED_PLANAR_GROUND', 'vertical_deviation': obs['ground_vertical_m']},
    'distortion': {'state': draft['distortion']['state'], 'residual': obs['distortion_residual_px']},
  }
  return value, intrinsics


def preflight(draft, attachments, scope):
  errors = []
  try:
    validate_draft(draft)
    if not draft['ground']['surface_method'] or draft['ground']['slope_bound_deg'] is None:
      errors.append('GROUND_SURVEY_PENDING')
    if draft['distortion']['state'] is None:
      errors.append('DISTORTION_VALIDATION_PENDING')
    m, i = measurement(draft, attachments, scope)
    admission = c.admit(m, i)
    if admission['status'] != 'CALIBRATION_EVIDENCE_ADMITTED':
      errors.append(admission['reason'])
  except (ValueError, TypeError, KeyError, OverflowError):
    errors.append('EXPLICIT_COMPLETE_FINITE_INPUT_UNITS_PROVENANCE_REQUIRED')
  if errors:
    return {'valid': False, 'errors': errors, 'admission': None, 'readiness': 'CALIBRATION_MEASUREMENT_PENDING'}
  return {'valid': True, 'errors': [], 'admission': admission, 'readiness': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING'}


def atomic_blob(path, data):
  fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.attachment-', suffix='.tmp')
  try:
    with os.fdopen(fd, 'wb') as f:
      f.write(data)
      f.flush()
      os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)
  finally:
    if os.path.exists(tmp):
      os.unlink(tmp)


def read_blob(path):
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(fd, 'rb') as f:
    if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
      raise ValueError('REGULAR_LOCAL_EVIDENCE_REQUIRED')
    data = f.read(MAX_ATTACHMENT_BYTES + 1)
  if len(data) > MAX_ATTACHMENT_BYTES:
    raise ValueError('ATTACHMENT_RESOURCE_CAP')
  return data


class MeasurementSession:
  """Local/private versioned package, never a reference producer."""

  def __init__(self, root, *, scope='INDEPENDENT_PHYSICAL'):
    if scope not in c.SCOPES:
      raise ValueError('EXPLICIT_ADMISSION_SCOPE_REQUIRED')
    self.root = Path(root).absolute()
    self.scope = scope
    if self.root.resolve() != self.root or self.root.is_relative_to(c.ROOT):
      raise ValueError('EXPLICIT_NONREPOSITORY_NONSYMLINK_LOCAL_ROOT_REQUIRED')
    s.durable_mkdir(self.root)
    os.chmod(self.root, 0o700)
    for name in ('binding.json', 'draft.json', 'attachments.json', 'prepared-submission.json', 'admitted.json'):
      if (self.root / name).is_symlink():
        raise ValueError('WIZARD_STATE_SYMLINK_REJECTED')
    st = self.root.stat()
    self.root_id = (st.st_dev, st.st_ino)
    self.binding = c.seal({'schema': SCHEMA, 'scope': scope, 'tool_sha256': identity(), 'admission_tool_sha256': c.identity()})
    with s.writer_lease(self.root):
      path = self.root / 'binding.json'
      if path.exists():
        if s.read_json(path) != self.binding:
          raise ValueError('VERSIONED_WIZARD_BINDING_REQUIRED_NO_MIGRATION')
      else:
        if {p.name for p in self.root.iterdir()} != {'writer.lock'}:
          raise ValueError('SEPARATE_EMPTY_WIZARD_ROOT_REQUIRED')
        s.atomic_json(path, self.binding)
        s.atomic_json(self.root / 'draft.json', c.seal({'binding_sha256': self.binding['receipt_sha256'], 'draft': blank_draft()}))
        s.atomic_json(self.root / 'attachments.json', c.seal({'binding_sha256': self.binding['receipt_sha256'], 'rows': []}))
        s.durable_mkdir(self.root / 'evidence')
        os.chmod(self.root / 'evidence', 0o700)
    self.guard()

  def guard(self):
    if self.root.resolve() != self.root or not self.root.is_dir():
      raise ValueError('LOCAL_WIZARD_ROOT_CHANGED')
    for name in ('binding.json', 'draft.json', 'attachments.json', 'prepared-submission.json', 'admitted.json'):
      if (self.root / name).is_symlink():
        raise ValueError('WIZARD_STATE_SYMLINK_REJECTED')
    st = self.root.stat()
    if identity() != self.binding['tool_sha256']:
      raise ValueError('RUNNING_WIZARD_SOURCE_CHANGED')
    if (st.st_dev, st.st_ino) != self.root_id or s.read_json(self.root / 'binding.json') != self.binding:
      raise ValueError('LOCAL_WIZARD_ROOT_OR_BINDING_CHANGED')
    p = self.root / 'evidence'
    if p.resolve() != p.absolute() or not p.is_dir():
      raise ValueError('LOCAL_EVIDENCE_DIRECTORY_CHANGED')

  def rows(self):
    self.guard()
    x = s.read_json(self.root / 'attachments.json')
    core = unseal(x)
    c.exact(core, ('binding_sha256', 'rows'))
    if core['binding_sha256'] != self.binding['receipt_sha256'] or type(core['rows']) is not list:
      raise ValueError('ATTACHMENT_INDEX_BINDING_MISMATCH')
    seen = set()
    for row in core['rows']:
      c.exact(row, ('opaque_id', 'sha256', 'byte_size', 'status'))
      c.sha(row['sha256'])
      if row['opaque_id'] != row['sha256'] or row['opaque_id'] in seen or type(row['byte_size']) is not int or row['status'] != 'LOCAL_PRIVATE_ONLY':
        raise ValueError('INVALID_ATTACHMENT_IDENTITY')
      seen.add(row['opaque_id'])
      data = read_blob(self.root / 'evidence' / (row['opaque_id'] + '.bin'))
      if digest(data) != row['sha256'] or len(data) != row['byte_size']:
        raise ValueError('LOCAL_EVIDENCE_CONTENT_CHANGED')
    return core['rows']

  def draft(self):
    self.guard()
    x = unseal(s.read_json(self.root / 'draft.json'))
    c.exact(x, ('binding_sha256', 'draft'))
    if x['binding_sha256'] != self.binding['receipt_sha256']:
      raise ValueError('DRAFT_BINDING_MISMATCH')
    validate_draft(x['draft'])
    return x['draft']

  def editable(self):
    self.guard()
    if (self.root / 'prepared-submission.json').exists() or (self.root / 'admitted.json').exists():
      raise ValueError('IMMUTABLE_OR_INTERRUPTED_SUBMISSION_REQUIRES_NEW_VERSION')

  def save_draft(self, draft):
    self.guard()
    validate_draft(draft)
    with s.writer_lease(self.root):
      self.editable()
      s.atomic_json(self.root / 'draft.json', c.seal({'binding_sha256': self.binding['receipt_sha256'], 'draft': draft}))
    return self.state()

  def attach(self, data):
    self.guard()
    if type(data) is not bytes or not data or len(data) > MAX_ATTACHMENT_BYTES:
      raise ValueError('EXPLICIT_BOUNDED_LOCAL_ATTACHMENT_REQUIRED')
    row = {'opaque_id': digest(data), 'sha256': digest(data), 'byte_size': len(data), 'status': 'LOCAL_PRIVATE_ONLY'}
    with s.writer_lease(self.root):
      self.editable()
      rows = self.rows()
      if row in rows:
        return row
      path = self.root / 'evidence' / (row['opaque_id'] + '.bin')
      if path.exists() or path.is_symlink():
        if read_blob(path) != data:
          raise ValueError('ORPHAN_ATTACHMENT_CONTENT_MISMATCH')
      else:
        atomic_blob(path, data)
      rows.append(row)
      rows.sort(key=lambda r: r['opaque_id'])
      s.atomic_json(self.root / 'attachments.json', c.seal({'binding_sha256': self.binding['receipt_sha256'], 'rows': rows}))
    return row

  def preflight(self, draft):
    return preflight(draft, self.rows(), self.scope)

  def prepared(self):
    p = s.read_json(self.root / 'prepared-submission.json')
    core = unseal(p)
    c.exact(
      core,
      (
        'schema',
        'binding_sha256',
        'original_input',
        'original_input_sha256',
        'attachments',
        'admission',
        'independent_calibration_validated',
        'reference_promotable',
        'publish_this_package',
      ),
    )
    if core['schema'] != 'PHYSICAL_CALIBRATION_LOCAL_SUBMISSION_V1' or core['binding_sha256'] != self.binding['receipt_sha256']:
      raise ValueError('SUBMISSION_BINDING_MISMATCH')
    if core['original_input'] != self.draft() or core['original_input_sha256'] != digest(canonical(self.draft())) or core['attachments'] != self.rows():
      raise ValueError('ORIGINAL_INPUT_OR_ATTACHMENT_BINDING_MISMATCH')
    x = self.preflight(core['original_input'])
    if (
      not x['valid']
      or core['admission'] != x['admission']
      or any(core[k] is not False for k in ('independent_calibration_validated', 'reference_promotable', 'publish_this_package'))
    ):
      raise ValueError('EXACT_STRUCTURAL_SUBMISSION_REQUIRED')
    return p

  def finish(self):
    p = self.prepared()
    admission = p['admission']
    store = c.ImmutableCalibrationStore(self.root / 'admission')
    if (store.root / 'measurement.json').exists():
      if store.read() != admission:
        raise ValueError('CONFLICTING_ADMITTED_CALIBRATION')
    else:
      store.save(admission['measurement'], admission['intrinsics'])
    marker = c.seal(
      {
        'schema': 'WIZARD_IMMUTABLE_COMPLETION_V1',
        'binding_sha256': self.binding['receipt_sha256'],
        'package_sha256': p['receipt_sha256'],
        'admission_sha256': admission['receipt_sha256'],
      }
    )
    s.atomic_json(self.root / 'admitted.json', marker)
    return self.package()

  def admit(self):
    self.guard()
    with s.writer_lease(self.root):
      self.editable()
      draft = self.draft()
      x = self.preflight(draft)
      if not x['valid']:
        raise ValueError('PREFLIGHT_FAILED')
      p = c.seal(
        {
          'schema': 'PHYSICAL_CALIBRATION_LOCAL_SUBMISSION_V1',
          'binding_sha256': self.binding['receipt_sha256'],
          'original_input': draft,
          'original_input_sha256': digest(canonical(draft)),
          'attachments': self.rows(),
          'admission': x['admission'],
          'independent_calibration_validated': False,
          'reference_promotable': False,
          'publish_this_package': False,
        }
      )
      s.atomic_json(self.root / 'prepared-submission.json', p)
      return self.finish()

  def recover(self):
    self.guard()
    with s.writer_lease(self.root):
      self.guard()
      if (self.root / 'admitted.json').exists():
        raise ValueError('ALREADY_ADMITTED_IMMUTABLE')
      return self.finish()

  def package(self):
    self.guard()
    p = self.prepared()
    marker = unseal(s.read_json(self.root / 'admitted.json'))
    expected = {
      'schema': 'WIZARD_IMMUTABLE_COMPLETION_V1',
      'binding_sha256': self.binding['receipt_sha256'],
      'package_sha256': p['receipt_sha256'],
      'admission_sha256': p['admission']['receipt_sha256'],
    }
    if marker != expected or c.ImmutableCalibrationStore(self.root / 'admission').read() != p['admission']:
      raise ValueError('IMMUTABLE_COMPLETION_BINDING_MISMATCH')
    return p

  def state(self):
    self.guard()
    rows = self.rows()
    draft = self.draft()
    admitted = (self.root / 'admitted.json').exists()
    prepared = (self.root / 'prepared-submission.json').exists()
    if admitted:
      self.package()
    elif prepared:
      self.prepared()
    return {
      'schema': SCHEMA,
      'scope': self.scope,
      'status': 'ADMITTED_MEASUREMENT' if admitted else 'ADMISSION_INTERRUPTED_PENDING_RECOVERY' if prepared else 'DRAFT_MEASUREMENT',
      'draft': draft,
      'attachments': rows,
      'readiness': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING' if admitted else 'CALIBRATION_MEASUREMENT_PENDING',
      'independent_calibration_validated': False,
      'reference_promotable': False,
      'private_comma4': 'NOT_OPENED',
      'sealed_reference': 'NOT_GENERATED',
    }

  def public_summary(self):
    self.guard()
    admitted = (self.root / 'admitted.json').exists()
    package = self.package() if admitted else None
    return c.seal(
      {
        'schema': 'PHYSICAL_CALIBRATION_PUBLIC_STATUS_V1',
        'status': 'CALIBRATION_EVIDENCE_ADMITTED' if admitted else 'CALIBRATION_MEASUREMENT_PENDING',
        'scope': self.scope,
        'package_sha256': package['receipt_sha256'] if package else None,
        'measurement_sha256': package['admission']['measurement_sha256'] if package else None,
        'tool_sha256': identity(),
        'independent_calibration_validated': False,
        'reference_promotable': False,
      }
    )
