"""Read-only comparison frontend and exclusive publication, no model imports."""

import hashlib
import platform
import sys
from pathlib import Path

from .scenario_compare_data import compare_batches
from .scenario_compare_input import CompareError, _manifest, read_batch
from .scenario_output import canonical

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'cyberlateral_dev', 'capnp', 'numpy', 'openpilot', 'opendbc', 'cereal'}
SOURCE_FILES = ['integration_tools/' + name + '.py' for name in [
    '__init__', 'scenario_compare_input', 'scenario_compare_data', 'scenario_compare_run',
    'scenario_input', 'scenario_output', 'scenario_report_data']] + ['tools/scenario_compare.py']


def _write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _source_hashes() -> dict[str, str]:
    try:
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
    except OSError as error:
        raise CompareError('COMPARE_SOURCE_IDENTITY') from error


def _preflight(baseline: Path, candidate: Path, output: Path) -> None:
    try:
        for value in [baseline, candidate, output, ROOT, Path(sys.executable)]:
            str(value.absolute()).encode('utf-8', errors='strict')
    except UnicodeError as error:
        raise CompareError('COMPARE_PATH_ENCODING') from error
    if output.exists() or output.is_symlink():
        raise CompareError('COMPARE_OUTPUT_EXISTS')
    if not output.parent.is_dir():
        raise CompareError('COMPARE_OUTPUT_PARENT')
    try:
        destination = output.resolve()
        if destination.is_relative_to(ROOT):
            raise CompareError('COMPARE_OUTPUT_LOCATION')
        for source in [baseline, candidate]:
            if destination.is_relative_to(source.resolve()):
                raise CompareError('COMPARE_OUTPUT_LOCATION')
    except (OSError, RuntimeError) as error:
        raise CompareError('COMPARE_INPUT_FILE') from error
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise CompareError('COMPARE_RUNTIME')


def _summary(record: dict) -> bytes:
    first = record['first_difference']
    location = '없음' if first is None else f'{first["case_id"]} / index={first["sample_index"]} / {first["field"]}'
    text = ('# 저장된 합성 batch 회귀 비교\n\n'
            f'상태: {record["status"]}\n\n'
            f'같은 입력에서 비교한 저장 sample: {record["compared_sample_count"]}개. 새 모델 실행:0.\n\n'
            f'차이: {record["difference_count"]}개. 상세 보존: {len(record["differences"])}개. '
            f'상세 잘림: {record["details_truncated"]}.\n\n'
            f'첫 차이: {location}\n\n'
            f'관찰된 producer identity 전체 일치: {record["all_observed_producer_identities_match"]}.\n\n'
            'MATCH는 저장된 값·거절 기록의 정확 일치이며 독립 수치 검증이나 출처 인증이 아닙니다.\n'
            '생산자 identity 변화는 별도 표시하며 MATCH가 identity 동일성을 뜻하지 않습니다.\n'
            '입력 변경은 같은 입력의 회귀로 판정하지 않습니다. bytes가 없는 입력은 일치를 확정하지 않습니다.\n'
            '호출 index는 초나 실제10ms 주기가 아닙니다. 허용오차·기준 자동 갱신은 없습니다.\n\n'
            'R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/차량 scale=null.\n'
            '실차 입력·활성화·F70UH/V/F71은 허용되지 않습니다.\n')
    return text.encode()


def run_comparison(baseline: Path, candidate: Path, output: Path) -> dict:
    _preflight(baseline, candidate, output)
    identity = _source_hashes()
    old, new = read_batch(baseline), read_batch(candidate)
    record = compare_batches(old, new)
    if _source_hashes() != identity:
        raise CompareError('COMPARE_SOURCE_CHANGED')
    receipt = {'schema_version': 1, 'baseline_directory': str(baseline.absolute()), 'candidate_directory': str(candidate.absolute()),
               'output_directory': str(output.absolute()), 'source_root': str(ROOT), 'comparator_source_hashes': identity,
               'baseline_root_manifest_sha256': old['root_manifest_sha256'], 'candidate_root_manifest_sha256': new['root_manifest_sha256'],
               'python_executable': sys.executable, 'python_version': platform.python_version(),
               'python_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
               'forbidden_modules_loaded': sorted({n.split('.')[0] for n in sys.modules} & FORBIDDEN),
               'new_model_executions': 0, 'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API',
               'scope': 'OWNED_BYTES_AND_COOPERATIVE_PROCESS_NOT_ATOMIC_OS_OR_INPUT_ORIGIN_ATTESTATION'}
    files = {'COMPARE.json': canonical(record), 'SUMMARY_KO.md': _summary(record), 'RECEIPT.json': canonical(receipt)}
    files['SHA256SUMS.txt'] = _manifest(files)
    try:
        output.mkdir(exist_ok=False)
        for name in ['SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt', 'COMPARE.json']:
            _write_exclusive(output / name, files[name])
    except OSError as error:
        raise CompareError('COMPARE_PUBLICATION_FAILED') from error
    return record
