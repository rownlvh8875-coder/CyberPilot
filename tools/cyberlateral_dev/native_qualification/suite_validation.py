"""Data-only fixed stage validation; no native/model or archive extraction."""

import json
from pathlib import Path

from native_qualification.coverage import validate_coverage
from native_qualification.suite_profiles import ROOT, Profile, get_profile
from native_qualification.worker import canonical, sha

FILES = ('OBSERVATIONS.json', 'RECEIPT_1.json', 'RECEIPT_2.json', 'SUMMARY.json')
MAX_FILE_BYTES = 2_000_000


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _sources(profile: Profile) -> dict:
    result = {}
    for key in profile.tool_sources:
        path = ROOT / ('native_qualification/' + key if key in ('run.py', 'worker.py') else key)
        _require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(ROOT.resolve()), 'SUITE_TOOL_SOURCE')
        result[key] = sha(path.read_bytes())
    return result


def validate_stage(directory: Path, stage_id: str) -> dict:
    profile = get_profile(stage_id)
    _require(not directory.is_symlink() and directory.is_dir(), 'SUITE_STAGE_FILES')
    _require({p.name for p in directory.iterdir()} == {*FILES, 'SHA256SUMS.txt'}, 'SUITE_STAGE_FILES')
    for name in (*FILES, 'SHA256SUMS.txt'):
        path = directory / name
        _require(not path.is_symlink() and path.is_file() and path.stat().st_size <= MAX_FILE_BYTES, 'SUITE_STAGE_FILES')
    raw = {name: (directory / name).read_bytes() for name in FILES}
    manifest = ''.join(sha(raw[name]) + '  ' + name + '\n' for name in FILES).encode()
    _require((directory / 'SHA256SUMS.txt').read_bytes() == manifest, 'SUITE_MANIFEST')
    decoded = {}
    for name, content in raw.items():
        try:
            record = json.loads(content)
            _require(type(record) is dict and canonical(record) == content, 'SUITE_CANONICAL_RECORD')
        except (TypeError, ValueError) as error:
            raise ValueError('SUITE_CANONICAL_RECORD') from error
        decoded[name] = record
    observed, summary = decoded['OBSERVATIONS.json'], decoded['SUMMARY.json']
    _require(sha(raw['OBSERVATIONS.json']) == profile.observations_sha256, 'SUITE_OBSERVATION_IDENTITY')
    if profile.case_count is not None:
        _require(type(observed.get('cases')) is list and len(observed['cases']) == profile.case_count, 'SUITE_CASES')
    count = validate_coverage(observed, stage_id) if profile.model_steps_per_worker else 0
    _require(type(count) is int and count == profile.model_steps_per_worker, 'SUITE_MODEL_COUNT')
    expected = {'status': profile.status, 'observations_sha256': profile.observations_sha256, 'worker_processes': 2,
                'byte_identical_observations': True, 'native_reader': 'NOT_IMPLEMENTED', 'actual_input': 'NOT_ALLOWED',
                'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'tool_sources': _sources(profile),
                'F61_execution': 0, 'model_execution': count * 2, 'r_calculation': 0, 'dt_calculation': 0}
    if count:
        expected.update(model_execution_per_worker=count, model_execution_scope='TWO_SEALED_WORKERS_NOT_UNIT_TEST_OR_STAGE_TOTAL',
                        model_reference_sha256=profile.reference_sha256)
    _require(canonical(summary) == canonical(expected), 'SUITE_SUMMARY')
    return {'stage_id': stage_id, 'status': profile.status, 'observations_sha256': profile.observations_sha256,
            'summary_sha256': sha(raw['SUMMARY.json']), 'reference_sha256': profile.reference_sha256,
            'case_count': profile.case_count, 'worker_processes': summary['worker_processes'],
            'model_execution_per_worker': count, 'model_execution': summary['model_execution']}
