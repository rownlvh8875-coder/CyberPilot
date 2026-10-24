"""Isolated second-human protocol. No AI/assisted store access or automatic human labels."""

from pathlib import Path

from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ATTESTATIONS = {
  'explicit_human_ack': True,
  'not_original_assisted_reviewer': True,
  'prior_ai_suggestion_access': False,
  'prior_assisted_label_access': False,
  'prior_stratum_hypothesis_access': False,
}
PRESENTATION_FIELDS = ('frame_id', 'image_sha256', 'mask_sha256', 'prediction_sha256')
POLICY = {
  'schema': 'SECOND_REVIEWER_BLIND_POLICY_V1',
  'labels': list(c.LABELS),
  'guide': w.GUIDE,
  'attestations': ATTESTATIONS,
  'presentation_fields': list(PRESENTATION_FIELDS),
  'visible_views': ['original_image', 'category_2_gt_mask', 'detector_prediction_geometry'],
  'hidden': ['ai_suggestions', 'assisted_labels', 'stratum_hypotheses', 'metrics', 'detector_confidence'],
  'store': 'SEPARATE_IMMUTABLE_REGISTRATION_ROWS_AND_INDEX; NO_PREVIOUS_STORE_IMPORT',
  'limits': 'OPAQUE_ID_AND_SELF_ATTESTATION_DO_NOT_CRYPTOGRAPHICALLY_PROVE_EXTERNAL_NONEXPOSURE',
  'human_input': 'EXPLICIT_HUMAN_ACK_ONLY; NO_AUTOMATIC_OR_COPIED_LABELS',
  'reference_promotable': False,
  'private_input_allowed': False,
}
POLICY_SHA = digest(canonical(POLICY))


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'workflow': w.workflow_identity(), 'policy': POLICY_SHA}))


def protocol(manifest):
  w.require_manifest(manifest)
  return seal(
    {
      'schema': 'SECOND_REVIEWER_BLIND_V1',
      'manifest_sha256': manifest['receipt_sha256'],
      'frame_count': len(manifest['frames']),
      'policy': POLICY,
      'policy_sha256': POLICY_SHA,
      'tool_sha256': identity(),
      'scope': manifest['scope'],
      'independent_reviewer_status': 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def validate_protocol(value):
  core = unseal(value)
  if (
    set(core)
    != {
      'schema',
      'manifest_sha256',
      'frame_count',
      'policy',
      'policy_sha256',
      'tool_sha256',
      'scope',
      'independent_reviewer_status',
      'private_input_allowed',
      'reference_promotable',
    }
    or core['schema'] != 'SECOND_REVIEWER_BLIND_V1'
    or core['policy'] != POLICY
    or core['policy_sha256'] != POLICY_SHA
    or core['tool_sha256'] != identity()
    or not is_sha256(core['manifest_sha256'])
    or type(core['frame_count']) is not int
    or core['frame_count'] != 29
    or core['scope'] not in c.SCOPES
    or core['independent_reviewer_status'] != 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE'
    or core['private_input_allowed'] is not False
    or core['reference_promotable'] is not False
  ):
    raise ValueError('EXACT_BLIND_PROTOCOL_REQUIRED')
  return core


def register(value, reviewer_id, attestations):
  validate_protocol(value)
  if not is_sha256(reviewer_id) or type(attestations) is not dict or attestations != ATTESTATIONS or any(type(v) is not bool for v in attestations.values()):
    raise ValueError('OPAQUE_NEW_BLIND_REVIEWER_ATTESTATION_REQUIRED')
  return seal(
    {
      'schema': 'SECOND_BLIND_REVIEWER_REGISTRATION_V1',
      'protocol': value,
      'protocol_sha256': value['receipt_sha256'],
      'reviewer_id': reviewer_id,
      'attestations': attestations,
      'scope': value['scope'],
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def validate_registration(value, manifest):
  core = unseal(value)
  if (
    set(core) != {'schema', 'protocol', 'protocol_sha256', 'reviewer_id', 'attestations', 'scope', 'private_input_allowed', 'reference_promotable'}
    or core['protocol'] != protocol(manifest)
    or value != register(core['protocol'], core['reviewer_id'], core['attestations'])
  ):
    raise ValueError('EXACT_BLIND_REGISTRATION_REQUIRED')
  return core


def pending(value):
  validate_protocol(value)
  return seal(
    {
      'schema': 'SECOND_BLIND_REVIEWER_PENDING_V1',
      'protocol_sha256': value['receipt_sha256'],
      'status': 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE',
      'completed_rows': 0,
      'reviewer_id': None,
      'inter_rater_statistics': None,
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def validate_row(manifest, registration, row):
  core = unseal(row)
  if (
    set(core)
    != {
      'schema',
      'annotation',
      'registration_sha256',
      'reviewer_id',
      'ai_suggestion_exposed_before_human_decision',
      'assisted_human_review',
      'blind_human_review',
      'reference_promotable',
    }
    or core['schema'] != 'SECOND_BLIND_HUMAN_ANNOTATION_V1'
    or core['registration_sha256'] != registration['receipt_sha256']
    or core['reviewer_id'] != registration['reviewer_id']
    or core['ai_suggestion_exposed_before_human_decision'] is not False
    or core['assisted_human_review'] is not False
    or core['blind_human_review'] is not True
    or core['reference_promotable'] is not False
  ):
    raise ValueError('BLIND_ROW_PROVENANCE_REQUIRED')
  c.validate_annotation(manifest, core['annotation'])
  return row


def validate_export(manifest, value):
  w.require_manifest(manifest)
  core = unseal(value)
  if set(core) != {'schema', 'registration', 'manifest_sha256', 'rows', 'completed_rows', 'status', 'scope', 'private_input_allowed', 'reference_promotable'}:
    raise ValueError('EXACT_BLIND_EXPORT_REQUIRED')
  validate_registration(core['registration'], manifest)
  if (
    core['schema'] != 'SECOND_BLIND_HUMAN_EXPORT_V1'
    or core['manifest_sha256'] != manifest['receipt_sha256']
    or core['scope'] != manifest['scope']
    or core['private_input_allowed'] is not False
    or core['reference_promotable'] is not False
    or type(core['rows']) is not list
  ):
    raise ValueError('EXACT_BLIND_EXPORT_REQUIRED')
  annotations = [validate_row(manifest, core['registration'], row)['annotation'] for row in core['rows']]
  ordered = w.ordered_rows(manifest, annotations)
  if annotations != ordered or type(core['completed_rows']) is not int or core['completed_rows'] != len(ordered):
    raise ValueError('BLIND_EXPORT_ROW_ACCOUNTING_REQUIRED')
  status = (
    'INDEPENDENT_BLIND_REVIEW_PENDING'
    if len(ordered) < len(manifest['frames'])
    else ('TEST_ONLY_NOT_HUMAN_EVIDENCE' if manifest['scope'] == c.SCOPES[1] else 'INDEPENDENT_BLIND_HUMAN_REVIEW_COMPLETE')
  )
  if core['status'] != status:
    raise ValueError('BLIND_EXPORT_STATUS_MISMATCH')
  return ordered


class BlindStore:
  """No path/API for AI or previous labels. Presentation is a strict whitelist."""

  def __init__(self, manifest, registration, root):
    validate_registration(registration, manifest)
    self.manifest, self.registration, self.root = manifest, registration, Path(root)
    if self.root.absolute() != self.root.resolve():
      raise ValueError('BLIND_STORE_SYMLINK_FORBIDDEN')
    s.durable_mkdir(self.root)
    with s.writer_lease(self.root):
      freeze = self.root / 'registration.json'
      if freeze.exists():
        self.guard()
      else:
        if {p.name for p in self.root.iterdir()} != {'writer.lock'}:
          raise ValueError('SEPARATE_EMPTY_BLIND_STORE_REQUIRED')
        s.atomic_json(freeze, registration)
        s.durable_mkdir(self.root / 'rows')
        s.atomic_json(self.root / 'index.json', self.make_index([]))
      self.rows()

  def guard(self):
    validate_registration(self.registration, self.manifest)
    if self.root.absolute() != self.root.resolve() or (self.root / 'rows').is_symlink():
      raise ValueError('BLIND_STORE_SYMLINK_FORBIDDEN')
    if s.read_json(self.root / 'registration.json') != self.registration:
      raise ValueError('IMMUTABLE_BLIND_REGISTRATION_REQUIRED')
    if {p.name for p in self.root.iterdir()} != {'writer.lock', 'rows', 'registration.json', 'index.json'}:
      raise ValueError('FOREIGN_BLIND_STORE_CONTENT_FORBIDDEN')

  def ordinal(self, index):
    if type(index) is not int or not 0 <= index < len(self.manifest['frames']):
      raise ValueError('KNOWN_BLIND_FRAME_REQUIRED')
    return self.manifest['frames'][index]

  def presentation(self, index):
    self.guard()
    return {key: self.ordinal(index)[key] for key in PRESENTATION_FIELDS}

  def make_index(self, rows):
    return seal(
      {
        'schema': 'SECOND_BLIND_ROW_INDEX_V1',
        'registration_sha256': self.registration['receipt_sha256'],
        'rows': [
          {
            'index': self.manifest['frames'].index(next(f for f in self.manifest['frames'] if f['frame_id'] == row['annotation']['frame_id'])),
            'receipt_sha256': row['receipt_sha256'],
          }
          for row in rows
        ],
      }
    )

  def rows(self):
    self.guard()
    index = s.read_json(self.root / 'index.json')
    core = unseal(index)
    if (
      set(core) != {'schema', 'registration_sha256', 'rows'}
      or core['schema'] != 'SECOND_BLIND_ROW_INDEX_V1'
      or core['registration_sha256'] != self.registration['receipt_sha256']
    ):
      raise ValueError('BLIND_INDEX_BINDING_MISMATCH')
    rows = []
    for path in sorted((self.root / 'rows').iterdir()):
      if path.name.startswith('.') and path.suffix == '.tmp':
        continue  # Uncommitted atomic-write remnants; never interpret as annotation.
      if len(path.name) != 10 or not path.name[:5].isdigit() or path.suffix != '.json':
        raise ValueError('FOREIGN_BLIND_ROW_FORBIDDEN')
      frame = self.ordinal(int(path.stem))
      row = validate_row(self.manifest, self.registration, s.read_json(path))
      if row['annotation']['frame_id'] != frame['frame_id']:
        raise ValueError('BLIND_FILENAME_FRAME_MISMATCH')
      rows.append(row)
    expected = self.make_index(rows)
    if index != expected:
      raise ValueError('BLIND_INDEX_MISSING_STALE_OR_ORPHAN_ROW')
    return rows

  def append(self, index, *, label, reviewable, comment, timestamp, human_ack):
    frame = self.ordinal(index)
    with s.writer_lease(self.root):
      self.rows()
      path = self.root / 'rows' / f'{index:05d}.json'
      if path.exists():
        raise FileExistsError('IMMUTABLE_BLIND_HUMAN_ROW')
      annotation = c.make_annotation(
        self.manifest,
        frame['frame_id'],
        label=label,
        reviewable=reviewable,
        comment=comment,
        timestamp=timestamp,
        human_ack=human_ack,
        tool_sha256=self.manifest['review_tool_sha256'],
      )
      row = seal(
        {
          'schema': 'SECOND_BLIND_HUMAN_ANNOTATION_V1',
          'annotation': annotation,
          'registration_sha256': self.registration['receipt_sha256'],
          'reviewer_id': self.registration['reviewer_id'],
          'ai_suggestion_exposed_before_human_decision': False,
          'assisted_human_review': False,
          'blind_human_review': True,
          'reference_promotable': False,
        }
      )
      existing = self.rows()
      s.atomic_json(path, row)
      order = {f['frame_id']: i for i, f in enumerate(self.manifest['frames'])}
      existing.append(row)
      existing.sort(key=lambda r: order[r['annotation']['frame_id']])
      s.atomic_json(self.root / 'index.json', self.make_index(existing))
      return row

  def export(self):
    rows = self.rows()
    result = seal(
      {
        'schema': 'SECOND_BLIND_HUMAN_EXPORT_V1',
        'registration': self.registration,
        'manifest_sha256': self.manifest['receipt_sha256'],
        'rows': rows,
        'completed_rows': len(rows),
        'status': 'INDEPENDENT_BLIND_REVIEW_PENDING'
        if len(rows) < len(self.manifest['frames'])
        else ('TEST_ONLY_NOT_HUMAN_EVIDENCE' if self.manifest['scope'] == c.SCOPES[1] else 'INDEPENDENT_BLIND_HUMAN_REVIEW_COMPLETE'),
        'scope': self.manifest['scope'],
        'private_input_allowed': False,
        'reference_promotable': False,
      }
    )
    validate_export(self.manifest, result)
    return result

  def finalize(self, metric_loader):
    rows = validate_export(self.manifest, self.export())
    if len(rows) != len(self.manifest['frames']):
      raise ValueError('BLIND_REVIEW_INCOMPLETE')
    return seal(
      {
        'schema': 'SECOND_BLIND_TAIL_ATTRIBUTION_V1',
        'blind_export_sha256': self.export()['receipt_sha256'],
        'attribution': w.aggregate(self.manifest, rows, metric_loader),
        'reference_promotable': False,
      }
    )
