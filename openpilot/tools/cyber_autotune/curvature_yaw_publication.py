"""Opt-in offline diagnostic publication; exact-source consistency, not authentication."""
import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

from openpilot.tools.cyber_autotune import curvature_yaw_diagnostics_offline_v1 as diagnostic
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import decode_request, encode_request
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import run_native_transcript
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest, _keys, _hex, _unique_pairs, _invalid_constant

CONTRACT = 'CHECKED_DIAGNOSTIC_OWNED_PUBLICATION_V1'
BUNDLE_CONTRACT = 'CHECKED_DIAGNOSTIC_ARCHIVE_BUNDLE_V1'
# One offline archive contains eight reports and eight diagnostic publications.
# Additional interface bound only; no private E2 resource contract is changed.
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
SOURCE_NAMES = ('curvature_yaw_publication.py','curvature_yaw_diagnostics_offline_v1.py',
                'curvature_yaw_diagnostic_worker.py','curvature_yaw_rejection_offline_v1.py',
                'curvature_yaw_rejection_export_offline_v1.py','curvature_yaw_rejection_visualizer_offline_v1.py')



def _require_offline(offline_publication_v1: object) -> None:
  if type(offline_publication_v1) is not bool or offline_publication_v1 is not True:
    raise ValueError('OFFLINE_PUBLICATION_OPT_IN_REQUIRED')


def source_identity() -> dict[str, str]:
  return {name:digest(Path(__file__).with_name(name).read_bytes()) for name in SOURCE_NAMES}


@dataclass(frozen=True, slots=True)
class DiagnosticPublication:
  packet: bytes
  request_payload: bytes
  native_payload: bytes
  observations: tuple[diagnostic.VerifiedObservation, ...]
  receipt_sha256: str
  repetition_sha256: tuple[str, str]
  producer_source_sha256: str
  supervisor_source_sha256: str
  request_sha256: str

  def project(self) -> dict:
    # A fresh output projection: none of these mutable dictionaries are trusted input.
    return {'observations':[asdict(row) for row in self.observations],
            'receipt_sha256':self.receipt_sha256,'repetition_sha256':list(self.repetition_sha256),
            'producer_source_sha256':self.producer_source_sha256,
            'supervisor_source_sha256':self.supervisor_source_sha256,'request_sha256':self.request_sha256}


def admit_publication(packet: bytes, *, offline_publication_v1: object = False) -> DiagnosticPublication:
  _require_offline(offline_publication_v1)
  if type(packet) is not bytes or not 0 < len(packet) <= diagnostic.MAX_SNAPSHOT_BYTES + 8192:
    raise ValueError('PUBLICATION_BYTES_REQUIRED')
  envelope=json.loads(packet,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  _keys(envelope,('contract','sources','payload','receipt_sha256'))
  if (envelope['contract']!=CONTRACT or envelope['sources']!=source_identity()
      or digest(canonical({k:v for k,v in envelope.items() if k!='receipt_sha256'}))!=envelope['receipt_sha256']
      or canonical(envelope)!=packet):
    raise ValueError('PUBLICATION_SOURCE_OR_RECEIPT_MISMATCH')
  payload=envelope['payload']
  _keys(payload,('request','native','result'))
  rows=diagnostic.checked_diagnostics_snapshot(canonical(payload),offline_publication_v1=True)
  result=payload['result']
  repeat=result['repetition_sha256']
  metadata=tuple(result[key] for key in ('receipt_sha256','producer_source_sha256','supervisor_source_sha256','request_sha256'))
  if (not all(type(v) is str and _hex(v,64) for v in metadata)
      or type(repeat) is not list or len(repeat)!=2 or not all(type(v) is str and _hex(v,64) for v in repeat)):
    raise ValueError('PUBLICATION_METADATA_INVALID')
  return DiagnosticPublication(packet,encode_request(payload['request']),canonical(payload['native']),rows,
                               result['receipt_sha256'],(repeat[0],repeat[1]),result['producer_source_sha256'],
                               result['supervisor_source_sha256'],result['request_sha256'])


def produce_diagnostics(request_payload: bytes, *, timeout_s: float = 30., offline_publication_v1: object = False) -> DiagnosticPublication:
  # The only input is immutable bytes. No caller-owned request/native/result tree
  # can enter the producer. Its fresh decoded trees never escape or reach callbacks.
  _require_offline(offline_publication_v1)
  request=decode_request(request_payload)
  if encode_request(request)!=request_payload:
    raise ValueError('PUBLICATION_REQUEST_NONCANONICAL')
  native=run_native_transcript(request,timeout_s=timeout_s)
  result=diagnostic.run_diagnostics(request,native,timeout_s=timeout_s,offline_publication_v1=True)
  body={'contract':CONTRACT,'sources':source_identity(),
        'payload':{'request':request,'native':native,'result':result}}
  body['receipt_sha256']=digest(canonical(body))
  return admit_publication(canonical(body),offline_publication_v1=True)


@dataclass(frozen=True, slots=True)
class PublicationVersion:
  generation: int
  publication: DiagnosticPublication


class DiagnosticChannel:
  """All supported writers/readers use this lock; no mutable state is exposed."""
  def __init__(self, *, offline_publication_v1: object = False):
    _require_offline(offline_publication_v1)
    self._lock=Lock()
    self._current: PublicationVersion | None = None

  def publish_request(self, payload: bytes, *, expected_generation: int | None = None, offline_publication_v1: object = False) -> PublicationVersion:
    # Slow computation is private, never a partially visible publication.
    _require_offline(offline_publication_v1)
    publication=produce_diagnostics(payload,offline_publication_v1=True)
    with self._lock:
      generation=0 if self._current is None else self._current.generation
      if expected_generation is not None and (type(expected_generation) is not int or expected_generation!=generation):
        raise ValueError('PUBLICATION_STALE_GENERATION')
      current=PublicationVersion(generation+1,publication)
      self._current=current
      return current

  def read(self, *, offline_publication_v1: object = False) -> PublicationVersion:
    _require_offline(offline_publication_v1)
    with self._lock:
      if self._current is None:
        raise ValueError('PUBLICATION_NOT_READY')
      return self._current


def seal_bundle(body: dict, *, offline_publication_v1: object = False) -> bytes:
  # Internal producer helper. Calling this with arbitrary mutable state does not
  # create ownership; the supported producer owns every member before this call.
  _require_offline(offline_publication_v1)
  envelope={'contract':BUNDLE_CONTRACT,'sources':source_identity(),'body':body}
  envelope['receipt_sha256']=digest(canonical(envelope))
  payload=canonical(envelope)
  if len(payload)>MAX_BUNDLE_BYTES:
    raise ValueError('PUBLICATION_BUNDLE_SIZE')
  return payload


def read_bundle(path: Path, *, offline_publication_v1: object = False) -> dict:
  # Exactly one opened immutable message, no member-path rereads after admission.
  _require_offline(offline_publication_v1)
  descriptor=os.open(path,os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(descriptor,'rb') as stream:
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
      raise ValueError('PUBLICATION_REGULAR_FILE_REQUIRED')
    payload=stream.read(MAX_BUNDLE_BYTES+1)
  if not 0 < len(payload) <= MAX_BUNDLE_BYTES:
    raise ValueError('PUBLICATION_BUNDLE_SIZE')
  envelope=json.loads(payload,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  _keys(envelope,('contract','sources','body','receipt_sha256'))
  if (envelope['contract']!=BUNDLE_CONTRACT or envelope['sources']!=source_identity()
      or digest(canonical({k:v for k,v in envelope.items() if k!='receipt_sha256'}))!=envelope['receipt_sha256']
      or canonical(envelope)!=payload):
    raise ValueError('PUBLICATION_BUNDLE_BINDING')
  body=envelope['body']
  _keys(body,('evaluation','selection','evaluation_freeze','matrix','reports','ledger','decision','records'))
  return body


def publish_bundle(path: Path, payload: bytes, *, offline_publication_v1: object = False) -> None:
  """Complete bytes become visible by same-directory atomic rename, never append."""
  _require_offline(offline_publication_v1)
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_BUNDLE_BYTES:
    raise ValueError('PUBLICATION_BUNDLE_SIZE')
  descriptor,name=tempfile.mkstemp(prefix='.diagnostic-',dir=path.parent)
  temporary=Path(name)
  try:
    with os.fdopen(descriptor,'wb') as stream:
      stream.write(payload)
      stream.flush()
      os.fsync(stream.fileno())
    os.replace(temporary,path)
    directory=os.open(path.parent,os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(directory)
    finally:
      os.close(directory)
  finally:
    temporary.unlink(missing_ok=True)


def read_evaluation_context(directory: Path, *, offline_publication_v1: object = False) -> dict:
  # Independent externally supplied authority anchor, one immutable message.
  _require_offline(offline_publication_v1)
  with (directory/'evaluation-envelope.json').open('rb') as stream:
    raw=stream.read(MAX_BUNDLE_BYTES+1)
  if not 0 < len(raw) <= MAX_BUNDLE_BYTES:
    raise ValueError('EVALUATION_CONTEXT_SIZE')
  context=json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  _keys(context,('evaluation','selection','evaluation_freeze'))
  if canonical(context)!=raw:
    raise ValueError('EVALUATION_CONTEXT_NONCANONICAL')
  return context
