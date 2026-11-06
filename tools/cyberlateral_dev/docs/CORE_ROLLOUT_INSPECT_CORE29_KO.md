# CORE29 — 봉인된 고정 rollout 파일 읽기 전용 검사

[CORE28](CORE_ROLLOUT_RUN_CORE28_KO.md)의 고정3예제 저장 파일이 과거 봉인값과
byte-identical인지 확인한다. **입력을 JSON으로 해석하거나 모델을 다시 실행하지 않는다.**
새 입력의 유효성·산술·현재 source·이력·출처·실차 적합성을 인증하는 기능이 아니다.

## 실행

저장 폴더에는 INPUT.json, RESULTS.json, SHA256SUMS.txt 정규 파일만 있어야 한다.
심볼릭 링크·FIFO·추가/누락 파일은 거절한다. 저장 폴더를 새로 생성하지 않는다.
기존 CORE28 예제 폴더를 아래 YOUR_SAVED_CORE28_DIR 대신 지정한다. 저장 폴더 밖에서 실행한다.

```bash
tools/cyberlateral_dev/.venv/bin/python -I -B tools/cyberlateral_dev/tools/core_rollout_inspect.py --case sign-cycle --input-root YOUR_SAVED_CORE28_DIR
```

세 case: sign-cycle, declared-difference, late-invalid. --run, 출력 폴더, rate,
임의 JSON/schema 옵션은 없다. 정확한 API는
`integration_tools.core_rollout_inspect.inspect_rollout_case(case_id, input_root)`이다.

정상 stdout은 canonical JSON receipt이며 검사 exit0이다. 과거 결과는 별도 보존한다:

| case | recorded_result_status | recorded_result_exit_code | recorded_model_steps | 현재 검사 exit |
|---|---|---|---|---|
| sign-cycle | MATCH | 0 | 3 | 0 |
| declared-difference | DIFFERENT | 1 | 3 | 0 |
| late-invalid | REJECTED | 2 | 0 | 0 |

저장된 거절 결과도 봉인된 원래 파일과 일치하면 **검사**는 성공한다. 현재 입력을
재판정한 것이 아니다. recorded_metadata_origin은 PINNED_CORE28_VECTOR_NOT_REPARSED이다.
현재 모델·참조·quantizer·입력 수치 재검증·F61 실행은0이다. 파일 읽기와 SHA 계산은 수행한다.
unit/full gate의 fixture 생성에는 별도의 합성 모델 작업이 있으며 이0에 포함하지 않는다.

## 고정 근거와 거절

핀은 이전 CORE28 Evidence ZIP
`2e8f658c5bfa03aea6d688cded43314118d10a949abdc9f7928a3fe4b9362fdc`의
독립 검산된 원래 산출물 size/full SHA256이다. 개발 검산에서 원래 ZIP member와도 비교한다.
현재 실행에서는 ZIP을 열거나 다시 검산하지 않는다
(reference_evidence_verified_during_inspection=false). 파일별 hash와 크기는 receipt에 나온다.
이는 서명·타임스탬프·보관자 identity 증명 또는 현재 production source 인증이 아니다.

각 파일을 한 번만 capture하며 pinned size를 넘기면 읽기 전에/도중에 거절한다.
정확한 크기와 SHA가 모두 같아야 한다. 자체 checksum만 다시 맞춘 변경, JSON 공백/키순서/
newline 변경, 다른 case 폴더, 향후 의도적인 새 catalog 결과도 이 버전에서는 거절한다.
새 핀은 별도 provenance와 버전 검토가 필요하며 자동 fallback/repair는 없다.

오류 exit2: ROLLOUT_INSPECT_CASE, ROLLOUT_INSPECT_ARTIFACT_IDENTITY,
ROLLOUT_INSPECT_ROOT_IDENTITY, ROLLOUT_INSPECT:RUN_INSPECT_LAYOUT/FILE_TYPE/SIZE,
경로 검증 오류, ROLLOUT_INSPECT_INPUT. CLI 잘못된 인자는
ROLLOUT_INSPECT_USAGE_NO_MODEL_EXECUTION, 기타 입출력 오류는
ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION이다. 비공개 경로나 raw 입력을 진단에 넣지 않는다.

반환 직전 root descriptor/path device+inode와 layout/types를 재검사하지만 atomic snapshot,
동시 변경 완전 탐지, 검사 이후 불변성 또는 ancestor 경로 인증을 보장하지 않는다.
오직 캡처된 bytes와 핀의 일치다. 입력 파일 쓰기·추출·수리·임시 파일은 없다.
CLI는 parser부터 출력까지 bytecode 쓰기를 억제하고 sys.path/flag를 복원한다.
초기 Python import까지 억제하려면 위 -I -B를 유지한다. API 호출자의 초기 import/cache는
호출자가 관리한다. 파일 권한 우회나 symlink 신뢰 승격을 제공하지 않는다.

stdout의 short write는 끝까지 처리한다. 중간 출력 실패는 exit2이며 이미 출력한 prefix는
회수할 수 없다. **exit0을 확인한 뒤** 전체 JSON을 사용한다. shell redirection은 검사 밖이다.
`> YOUR_SAVED_CORE28_DIR/INPUT.json` 같은 명령은 shell이 먼저 원본을 지우므로 금지한다.

## 유지 제한

실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
실제 차량 입력·F61·r/dt 계산·Controller·Runtime·CAN·실차 활성화는 허용하지 않는다.
새로운 input 의미 검증이나 범용 reader는 별도 단계이며 이 byte 검사 성공으로 대체하지 않는다.
