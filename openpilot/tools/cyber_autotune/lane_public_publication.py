"""Fail-closed public diagnostic publication links. No reference promotion."""

import os
from pathlib import Path
import tempfile

from openpilot.tools.cyber_autotune import lane_public_full_analysis as a
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_public_batch as b
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import digest


def verify_completed_store(root, protocol_path, manifest_path):
  root = Path(root)
  run = s.read_json(root / 'run-freeze.json')
  ui.require_frozen_metric_sources(run)
  if digest(Path(protocol_path).read_bytes()) != run['protocol_file_sha256'] or digest(Path(manifest_path).read_bytes()) != run['manifest_file_sha256']:
    raise ValueError('PUBLICATION_INPUT_FREEZE_MISMATCH')
  protocol, inputs = s.read_json(protocol_path), s.read_json(manifest_path)
  r.validate_protocol_pairs(protocol, inputs)
  pairs = protocol['pairs']
  if len(pairs) != 11888:
    raise ValueError('PUBLICATION_FULL_POPULATION_REQUIRED')
  identities = {f['path']: f for f in inputs['files']}
  durable = s.DurableRun(root, run, [p['image'] for p in pairs])

  def validator(row):
    ordinal = row['ordinal']
    return b.verify_resume(row, run['receipt_sha256'], ordinal, pairs[ordinal], identities)

  marker = durable.verify_completed(validator)
  return run, marker, durable


def validate_analysis_parents(marker, full, subset, original_rows_sha):
  f, sub = unseal(full), unseal(subset)
  if (
    f.get('schema') != 'PUBLIC_FULL_DIAGNOSTIC_ANALYSIS_V1'
    or f.get('completion_sha256') != marker['receipt_sha256']
    or f.get('processed') != 11888
    or f.get('expected') != 11888
    or sub.get('schema') != 'PUBLIC_HISTORICAL_SUBSET_DERIVED_FROM_COMPLETED_FULL_RUN_V1'
    or sub.get('processed') != 119
    or sub.get('parent_full_completion_sha256') != marker['receipt_sha256']
    or sub.get('historical_subset_protocol_sha256') != a.HISTORICAL_PROTOCOL_SHA
    or sub.get('original_full_receipts_sha256') != original_rows_sha
  ):
    raise ValueError('PUBLICATION_ANALYSIS_PARENT_MISMATCH')


def validate_cached_hashes(run_sha, snapshot, kill, actual_hashes):
  snap, k = unseal(snapshot), unseal(kill)
  rows = snap.get('rows')
  if (
    snap.get('run_sha256') != run_sha
    or k.get('run_sha256') != run_sha
    or type(rows) is not dict
    or not rows
    or rows != actual_hashes
    or set(rows) != {f'{i:05d}.json' for i in range(len(rows))}
    or k.get('intentional_exit_code') != -9
    or k.get('kill_scope') != 'OWNED_SESSION_PROCESS_GROUP_ONLY'
    or k.get('completed_marker_present') is not False
    or type(k.get('cached_rows_before_restart')) is not dict
    or not k['cached_rows_before_restart']
    or any(name not in rows or rows[name] != sha for name, sha in k['cached_rows_before_restart'].items())
  ):
    raise ValueError('PUBLICATION_CACHE_REUSE_BINDING_MISMATCH')


def validate_public_pending(manifest, expected_manifest, index):
  core = c.validate_manifest(manifest)
  state = unseal(index)
  if (
    core['scope'] != 'PUBLIC_COMMA10K_HUMAN_REVIEW'
    or manifest != expected_manifest
    or state.get('manifest_sha256') != manifest['receipt_sha256']
    or state.get('rows') != []
    or state.get('review_status') != c.review_status(manifest, [])
  ):
    raise ValueError('PUBLICATION_REAL_HUMAN_PENDING_BINDING_REQUIRED')
  return state['review_status']


def publish_immutable(path, value):
  path = Path(path)
  if path.exists():
    if s.read_json(path) != value:
      raise ValueError('IMMUTABLE_PUBLICATION_HISTORY_REQUIRED')
    return
  s.atomic_json(path, value)


def publish_immutable_text(path, text):
  path = Path(path)
  if path.is_symlink():
    raise ValueError('REGULAR_PUBLICATION_TEXT_REQUIRED')
  data = text.encode()
  if path.exists():
    if path.read_bytes() != data:
      raise ValueError('IMMUTABLE_PUBLICATION_HISTORY_REQUIRED')
    return
  s.durable_mkdir(path.parent)
  fd, temporary = tempfile.mkstemp(prefix='.publication-', dir=path.parent)
  try:
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(directory)
    finally:
      os.close(directory)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def validate_resume_links(run_sha, marker, snapshot, kill, window, progress, resume, proof, actual_hashes, file_hashes):
  validate_cached_hashes(run_sha, snapshot, kill, actual_hashes)
  w, pr, re, pf, k = (unseal(value) for value in (window, progress, resume, proof, kill))
  cached = len(snapshot['rows'])
  killed = len(k['cached_rows_before_restart'])
  if (
    w.get('status') != 'INTERRUPTED_RESUMABLE'
    or w.get('processed_rows') != cached
    or w.get('expected') != 11888
    or w.get('kill_proof_sha256') != file_hashes['kill']
    or w.get('cached_rows_reused_unchanged') != killed
    or w.get('completion_marker_file_sha256') is not None
    or pr.get('run_sha256') != run_sha
    or pr.get('completed_frames') != cached
    or pr.get('expected_frames') != 11888
    or pr.get('failure_records') != []
    or re.get('status') != 'COMPLETED'
    or re.get('processed_rows') != marker['processed']
    or re.get('expected') != marker['expected']
    or re.get('kill_proof_sha256') != file_hashes['kill']
    or re.get('cached_rows_reused_unchanged') != killed
    or re.get('completion_marker_file_sha256') != file_hashes['completion']
    or pf.get('status') != 'COMPLETED'
    or pf.get('run_sha256') != run_sha
    or pf.get('cached_rows_reused_unchanged') != cached
    or pf.get('processed') != marker['processed']
    or pf.get('expected') != marker['expected']
    or pf.get('cache_snapshot_file_sha256') != file_hashes['snapshot']
    or pf.get('window1_result_file_sha256') != file_hashes['window1']
    or pf.get('window1_progress_file_sha256') != file_hashes['progress']
    or pf.get('final_result_file_sha256') != file_hashes['resume']
  ):
    raise ValueError('PUBLICATION_RESUME_PROOF_LINK_MISMATCH')


def require_no_annotation_rows(root, manifest):
  root = Path(root)
  if s.read_json(root / 'review-freeze.json') != manifest:
    raise ValueError('PUBLICATION_REVIEW_FREEZE_MISMATCH')
  annotations = root / 'annotations'
  if annotations.is_symlink() or not annotations.is_dir() or any(annotations.iterdir()):
    raise ValueError('PUBLICATION_HUMAN_ROWS_PRESENT_OR_UNVERIFIED')


def validate_frozen_environment(environment, frozen):
  from openpilot.tools.cyber_autotune import lane_detector_execution as e

  e._unseal(environment, 'environment_sha256')
  if environment != frozen:
    raise ValueError('PUBLICATION_FROZEN_ENVIRONMENT_MISMATCH')


def verify_publication_certificate(root, certificate, required_files):
  core = unseal(certificate)
  files = core.get('artifact_file_sha256')
  if (
    core.get('schema') != 'PUBLIC_DIAGNOSTIC_PUBLICATION_CERTIFICATE_V1'
    or core.get('publication_source_sha256') != digest(Path(__file__).read_bytes())
    or type(files) is not dict
    or not files
    or not set(required_files) <= files.keys()
    or any(type(name) is not str or Path(name).name != name or not name.endswith('.json') for name in files)
  ):
    raise ValueError('PUBLICATION_CERTIFICATE_REQUIRED')
  for name, sha in files.items():
    r.read_bound_bytes(Path(root) / name, sha)
    s.read_json(Path(root) / name)
  return core
