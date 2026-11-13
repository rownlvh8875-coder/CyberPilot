"""Publish one explicit synthetic reference audit and bounded Korean summary."""

import hashlib
from pathlib import Path

from .core_sequence_archive_workflow import ArchiveWorkflowError, _output, _publish
from .recording_diagnostics_reference import RecordingReferenceError, check_recording_reference
from .recording_diagnostics_saved import FLAGS, _sha
from .scenario_output import canonical


class ReferenceWorkflowError(ValueError):
    """Preparation failed;reference work may already have happened."""

    def __init__(self):
        self.code = 'REFERENCE_WORKFLOW_PREPARATION_FAILED_WORK_MAY_BE_NONZERO'
        super().__init__(self.code)


def _row_state(row) -> str:
    if row is None:
        return '행 없음'
    def state(value):
        return '/'.join(str(value[k]) for k in ('index', 'previous_requested', 'previous_applied', 'angle_counter'))
    saved = row['declared_saved_state']
    return (f"entry={state(row['declared_entry_state'])}; next={state(row['computed_next_state'])}; "
            f"saved={saved['saved_limited_state']}/{saved['saved_angle_counter']}; {row['status']}")


def _summary(result: dict) -> bytes:
    """Fresh checker-owned enums/integers only;not an untrusted saved-JSON reader."""
    stored, reference = result['stored_record'], result['reference_projection']
    indices = result['differing_transition_indices']
    label = '일치' if result['audit_status'] == 'REFERENCE_MATCH' else '차이 있음'
    lines = ['# 합성 진단 참조 대조', '', f'참조 대조: {label}',
        f"audit status: {result['audit_status']} / exit {result['audit_exit_code']}",
        f"저장 진단: {result['saved_diagnostic_status']}", f"참조 진단: {result['reference_diagnostic_status']}", '',
        '대조 일치는 저장 진단의 MATCH를 뜻하지 않습니다. DIFFERENT 진단도 그대로 재현될 수 있습니다.', '',
        f"입력 SHA256: {result['input_sha256']}", f"저장 진단 SHA256: {result['diagnostics_sha256']}", '',
        f"과거 기록 모델 step: {result['recorded_model_steps']}",
        f"새 모델 step: {result['new_synthetic_model_steps']}", f"새 참조 step: {result['new_reference_steps']}",
        'helper·양자화·숫자 검증 작업은 비영입니다. 모델0은 전체 계산0이 아닙니다.', '',
        '입력 admission은 공유하며,각 선언 entry state를 사용합니다. computed rollout이나 repair는 하지 않습니다.',
        '첫 anchor·prehistory·전체 trace·전체 입력 영역·실제 출처/build·차량/성능 권한은 미검증입니다.', '',
        '상태 표기: entry/next=index/이전정수요청/이전제한출력/counter; saved=제한출력/counter.',
        '정수 명령 단위이며 물리 torque·실제 시간·주기를 뜻하지 않습니다.', '',
        '헤더 차이: ' + (', '.join(result['differing_header_fields']) or '없음'),
        f"저장 진단 차이 전이: {stored['differing_transition_indices']}",
        f"참조 진단 차이 전이: {reference['differing_transition_indices']}", '',
        f'대조 차이 전이: 전체 {len(indices)} / 표시 {min(20, len(indices))} / 생략 {max(0, len(indices) - 20)}', '',
        '| 전이 | 다른 행 필드 | 저장 행 상태 | 참조 행 상태 |', '| --- | --- | --- | --- |']
    for i in indices[:20]:
        left = stored['rows'][i] if i < len(stored['rows']) else None
        right = reference['rows'][i] if i < len(reference['rows']) else None
        fields = '행 존재 여부' if left is None or right is None else ', '.join(
            k for k in sorted(left) if canonical(left[k]) != canonical(right[k]))
        lines.append(f'| {i} | {fields} | {_row_state(left)} | {_row_state(right)} |')
    if not indices:
        lines.append('| — | 대조 차이 없음 | — | — |')
    lines.extend(['', '모든 header·행·차이·참조 source 관찰값은 REFERENCE_AUDIT.json에 보존됩니다.',
        'SHA256SUMS.txt는 이 두 파일의 무결성 검산용이며 원래 출처의 서명 인증이 아닙니다.', '',
        'R_BUDGET=UNRESOLVED,Static Gate=FAIL,실제 r/T2/scale=null.',
        'SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED.',
        '실제 Controller/Runtime/CAN/F61/차량 input·capture/actual r·dt/install/deploy0.', ''])
    return '\n'.join(lines).encode('utf-8')


def publish_recording_reference(input_file: Path, input_sha256: str, diagnostics_root: Path,
                                diagnostics_sha256: str, output_root: Path) -> dict:
    """Preflight output,check once,prepare everything,then exclusive readback publication."""
    if not _sha(input_sha256) or not _sha(diagnostics_sha256):
        raise RecordingReferenceError('RECORDING_REFERENCE_EXPECTED_SHA256')
    target = _output(output_root)
    try:
        overlaps = target.resolve().is_relative_to(diagnostics_root.resolve())
    except (OSError, ValueError, RuntimeError) as error:
        raise ArchiveWorkflowError('REFERENCE_WORKFLOW_DIAGNOSTICS_PATH') from error
    if overlaps:
        raise ArchiveWorkflowError('REFERENCE_WORKFLOW_OUTPUT_OVERLAPS_DIAGNOSTICS')
    result = check_recording_reference(input_file, input_sha256, diagnostics_root, diagnostics_sha256)
    try:
        raw, markdown = canonical(result), _summary(result)
        if not 0 < len(raw) <= 2097152 or not 0 < len(markdown) <= 65536:
            raise ValueError('prepared output size')
        files = {'REFERENCE_AUDIT.json': raw, 'SUMMARY_KO.md': markdown}
        files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(content).hexdigest() + '  ' + name + '\n'
            for name, content in sorted(files.items())).encode()
        receipt = {'schema_version': 1, 'contract_id': 'CORE70_REFERENCE_AUDIT_WORKFLOW_V1',
            'status': 'REFERENCE_AUDIT_PUBLISHED',
            **{k: result[k] for k in ('audit_status', 'audit_exit_code', 'saved_diagnostic_status',
                'reference_diagnostic_status', 'input_sha256', 'input_bytes', 'diagnostics_sha256', 'diagnostics_bytes',
                'recorded_model_steps', 'new_synthetic_model_steps', 'new_reference_steps', 'reference_helper_counts',
                'shared_admission_preflight', *FLAGS)},
            'gates': dict(result['gates']),
            'files': {n: {'sha256': hashlib.sha256(v).hexdigest(), 'byte_size': len(v)} for n, v in files.items()},
            'scope': 'ONE_DECLARED_SYNTHETIC_REFERENCE_AUDIT_PUBLICATION_NOT_ORIGIN_OR_VEHICLE_PROOF'}
        if not 0 < len(canonical(receipt)) <= 16384:
            raise ValueError('receipt size')
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        raise ReferenceWorkflowError() from error
    _publish(target, files)
    return receipt
