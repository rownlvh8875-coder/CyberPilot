# CORE21 portable suite ZIP 입력 의미 사전 검증

기존 [CORE13 portable suite](CORE_SEQUENCE_PORTABLE_CORE13_KO.md)의 완전한 ZIP을
추출하지 않고 검산한 뒤, 그 안의 세 case 입력을 [CORE19](CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md)
규칙으로 재검증한다. 새 API이며 새 CLI/모델/차량 reader가 아니다.

이 API를 그대로 호출하는 별도 [CORE22 CLI](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CLI_CORE22_KO.md)는
--archive/--sha256으로 원래 JSON을 출력한다. 현재 입력 호환/거절은 exit0/1,
사용법·파일·운영 오류는2이며 이 API의 규칙과 반환 JSON은 바꾸지 않는다.

## API와 사용

`integration_tools.core_sequence_archive_preflight`:

- `preflight_suite_archive(input_archive: Path, expected_sha256: str) -> dict`
- `preflight_suite_archive_bytes(raw: bytes, expected_sha256: str) -> dict`
- 저장/검산 오류: `ArchivePreflightError.code`

tools/cyberlateral_dev의 기존 전용 환경과 해당 cwd에서:

```bash
.venv/bin/python -I -B -c '
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / "src")]
from integration_tools.core_sequence_archive_preflight import preflight_suite_archive
from integration_tools.scenario_output import canonical
sys.stdout.buffer.write(canonical(preflight_suite_archive(Path(sys.argv[1]), sys.argv[2])))
' /absolute/suite.zip FULL_LOWERCASE_SHA256
```

두 번째 인자는 별도로 전달·확인한 전체64자리 소문자 SHA다. manifest 내부 hash로
임의 대체하지 않는다. Path API는 SHA 형식을 먼저 검사하고 ZIP을 한 번만 bounded
read 한다. bytes API는 exact built-in bytes를 받아 caller archive 파일을 열지 않는다.
import/cache 인프라는 호출자 책임이므로 예제는 -I -B를 쓴다.

## 검증 순서

1. CORE13의 `_verified_suite`를 한 번 호출한다. 기존2MB cap, 고정11 stored members,
   member별 크기/CRC/Manifest/closed schema/saved report/canonical ZIP을 모두 확인한다.
2. **전체** 검산이 끝난 뒤 소유 decoded records에 CORE19 공통 판정 본문을 적용한다.
   중간 의미 거절이 있어도 sign-cycle,declared-difference,late-invalid 순서로 모두 검사한다.
3. 파일 추출·case 재읽기·모델/reference 전이 실행 없이 case별 receipt와 집계를 반환한다.

CORE19의 기존 Path API도 같은 내부 본문을 호출한다. 옮긴 판정 본문 AST와 기존
반환 JSON/오류 동작을 보존했다. private `_preflight_captured`는 이미 검산된 소유
CORE9 record만 받는 내부 연결점이며 임의 외부 dict용 public 검증 API가 아니다.
CORE13 verifier와 CORE20 CLI에는 코드 변경이 없다.

## 결과 구분

contract_id는 CORE21_PORTABLE_SUITE_INPUT_PREFLIGHT_V1이다.
`archive`는 변경 없는 CORE13 verification receipt, `case_reports`는 고정 순서의
기존 CORE19 receipt 세 개다. `case_ids`/`case_count`/`all_cases_processed`도 함께 둔다.

`compatible_case_count`와 `rejected_case_count`는 **현재 입력** 판정 수다.
전부 호환일 때만 aggregate INPUTS_COMPATIBLE, 하나라도 거절이면 INPUTS_REJECTED다.
`validated_transition_count`는 각 case의 성공한 검증 prefix 합계이고
`declared_transition_count`는9다. `recorded_model_steps`는 과거 기록 합계이지 새 실행 수가 아니다.

기본 묶음은 호환2/거절1, 검증 prefix 합8, 기록 step6이다. saved DIFFERENT 입력도
호환일 수 있다. 과거 REJECTED label을 가진 입력을 현재 규칙에 맞게 별도 사본으로
공급하면 호환3/검증9가 될 수 있다. 과거 판정·source provenance가 바뀌거나 승인된다는
뜻은 아니다. 세 입력이 모두 거절되면 거절3이며 빈 성공으로 처리하지 않는다.

SHA/파일/ZIP/Manifest/schema 손상은 `ARCHIVE_PREFLIGHT:<기존 PORTABLE code>` 예외다.
의미 거절 receipt와 구분하며 이 경우 aggregate를 만들지 않는다. 후반 helper의
예상치 못한 오류도 전파하고 부분 성공/일반 input rejection으로 숨기지 않는다.
그 오류 전의 numeric validation은 비영일 수 있으며0으로 주장하지 않는다.

## 실행·권한 경계

입력 숫자 해석·양자화 검증은 NONZERO_NOT_AGGREGATED다. 새 model/reference step과
F61/실제 r-dt/Controller/Runtime/CAN/차량 작업은 이 기능에서0이다. 전체 unit/gate
fixture 작업은 별도 비영이다. prepared/model/F61 constructor args는 반환하지 않는다.
bytes·mode를 수정하지 않지만 atime·atomic snapshot·적대적 경로경쟁/alias·host hook은
보장하지 않는다. ZIP 자체 정합성+현재 합성 입력 호환이지 저장 산술·출처·과거 실행·
anchor/prehistory·computed rollout·실제 source/차량 성능 인증이 아니다.

실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
