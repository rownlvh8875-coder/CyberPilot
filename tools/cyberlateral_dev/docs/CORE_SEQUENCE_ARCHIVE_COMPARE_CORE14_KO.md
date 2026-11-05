# CORE14 — ZIP 두 개의 저장 결과 비교

CORE13 ZIP 두 개를 압축 해제·원본 파일 재열기·모델 재실행 없이 비교한다.
양쪽 전체 SHA를 파일 접근 전에 검사하고, ZIP별 bounded capture/검증을 한 번씩 한다.
기존 CORE13의 ZIP64·실제11entry·CRC·Manifest·schema·Gate·canonical bytes 검사를 모두
통과한 소유 records만 CORE10 exact-type 비교에 전달한다. 별도 temp extraction은 없다.

## 사용

기존 개발 환경의 프로젝트 폴더에서 실행한다. SHA 자리에는 신뢰하는 인계 경로에서
받은 전체64hex 소문자 SHA256을 넣는다. ZIP 자체의 자기 hash만으로 출처 인증이 되지 않는다.

```bash
.venv/bin/python -I -B tools/core_sequence_archive_compare.py \
  --left-archive /external/baseline.zip --left-sha256 FULL_LEFT_SHA256 \
  --right-archive /external/current.zip --right-sha256 FULL_RIGHT_SHA256
```

stdout은 canonical JSON 보고서다. exit0은 검증된 ZIP bytes 동일, exit1은 검증된
차이 존재, exit2는 손상·미지원·오류다. 한쪽이 손상되면 부분 비교 보고서를 출력하지 않는다.
`--run`, `--extract`, `--r`, `--format`, `--output`, 생략 가능한 SHA 옵션은 없다.
CLI private cache는 사용하지만 입력 ZIP에 쓰거나 내용을 추출하지 않는다.

API는 `integration_tools.core_sequence_archive_compare`의
`compare_suite_archives(left: Path, left_sha256: str, right: Path, right_sha256: str)`와
`compare_suite_archive_bytes(left: bytes, left_sha256: str, right: bytes, right_sha256: str)`다.
반환 dict에 `exit_code(report)`를 적용할 수 있다. programmatic embedding은 API를 사용한다.

## 보고서 해석

`archive_bytes_identical`은 캡처한 전체 bytes를 직접 비교한다. 각 case는 고정 순서
sign-cycle/declared-difference/late-invalid이며 per-case CORE10 결과를 그대로 보존한다.
INPUT/RESULT/IDENTITY별 전체 차이를 집계한다. identity는 opaque 저장값이므로 무시하거나
현재 source 인증으로 승격하지 않는다. bool과 int, null과 missing, 배열 위치는 구분한다.
JSON pointer는 각 case 내 파일 경로이며 바깥 `case_id`와 함께 읽는다.

상세는 case별 첫256개(최대768개)이며 전체 차이 개수는 모두 센다. 상세 잘림 여부와
표시 수를 명시한다. 임의 허용오차·정렬 재매핑·숫자 coercion·field 무시는 없다.
양쪽 CORE13 receipt와 저장 MATCH/DIFFERENT/REJECTED·과거 step 수를 보존한다.
저장 DIFFERENT/REJECTED가 있어도 같은 ZIP이면 비교 exit0이다. 이는 새 수치 MATCH나
성능/회귀 qualification을 뜻하지 않는다.

`new_synthetic_model_steps`, comparison model/reference executions는0이다.
`arithmetic_recomputed`, `source_identity_reauthenticated`는false다. 전체 unit/gate가
만드는 합성 fixture 작업량은 별개이며 NONZERO_NOT_AGGREGATED다.

오류는 `ARCHIVE_COMPARE_LEFT:PORTABLE_…` 또는 `ARCHIVE_COMPARE_RIGHT:PORTABLE_…`로
역할을 구분하고 raw path/exception을 노출하지 않는다. 예상하지 못한 CLI 오류는 고정
ARCHIVE_COMPARE_FAILED_NO_MODEL_EXECUTION이다. cache cleanup·직렬화·exit 계산이 끝나야
보고서를 쓰며, 이미 전송한 stdout prefix는 되돌리지 못한다.

## 한계와 유지 Gate

동일 path를 양쪽에 주어도 두 role을 따로 캡처한다. atomic snapshot이나 두 캡처 사이
불변성·현재 source/build/deployment 인증·서명·산술 진위는 증명하지 않는다. 일관된
위조는 통과할 수 있다. 기존 POSIX/Python3.12/cooperative filesystem 범위를 유지하며
악의적인 부모/alias/동시변경·native Windows·미래 Python 호환성을 보장하지 않는다.

실제 r/T2/vehicle_scale=null, R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL이다.
F61·Controller·Runtime·CAN·실제 r 계산 및 실차 input/활성화는 실행·승인하지 않는다.
F70UH/F70V/F71은 NOT_ALLOWED다. 비교 결과로 policy·배포 권한은 추가되지 않는다.
