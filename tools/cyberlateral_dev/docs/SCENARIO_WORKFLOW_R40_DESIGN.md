# R40 — 선언 합성 시나리오 통합 실행·검증 설계

## 목적과 범위

사용자가 명시한 합성 JSON을 한 명령으로 사전 검사하고 기존 R33 실행·R32 리포트·
R39 독립 참조를 연결한다. 선택한 완전한 R33 baseline이 있으면 R34 회귀 비교도 한다.
모델·산술·R31~R39 API를 재설계하거나 같은 wheel을 새 모델로 표현하지 않는다.
사용자는 위 기능을 승인하고 반복 설계 질문을 생략하도록 위임했다. 아래 세부 선택은
구현자의 결정이며 사용자가 개별 지정한 사항으로 취급하지 않는다.

## 접근 방식

1. Bash에서 기존 CLI 연결: 단순하지만 혼합 입력 exit1·상태·소유 snapshot·오류 집계가
   shell마다 중복되고 종료 코드만으로 성공을 오판하기 쉽다.
2. 별도 Python DEV CLI에서 기존 구현 함수를 연결: 선택. 기존 owned reader/worker/
   source 검증/수치 판정을 재사용하고 새 모델·추가 의존성 없이 결과를 묶는다.
3. 공개 wheel API나 dev.py verify에 통합: 사용자 입력 도구와 고정 개발 gate를 혼합하므로 제외.

## 인터페이스와 소유 bytes

`tools/scenario_workflow.py --input <합성 JSON> [--input ...] --output <새 폴더>
[--baseline <완전한 저장 R33 batch>]`.

기존 CPython3.12.13/Linux/binary64/NumPy2.5.3 locked DEV 환경을 쓴다. 공개 모델0.3.0,
wheel/lock/dependency는 불변이다. frontend는 모델/NumPy/native를 import하지 않는다.

기존 R33 prepare_batch로 입력1..32개·합계8192samples·명시 순서·중복/경로/크기/형태를
검사하고 원본마다 bounded raw bytes를 한 번만 읽는다. 읽을 수 없거나 크기 제한을 넘겨
raw를 확보하지 못하면 WORKFLOW_INPUT_UNAVAILABLE/exit2, 출력 미생성이다. R33의
부분 증거 기능을 이 workflow에서 가짜 snapshot으로 대체하지 않는다. 읽힌 불량 JSON은
기존 parser의 정상적인 입력 거절로 계속 처리한다.

출력은 기존 부모 안의 새 폴더이며 component 밖이어야 한다. 기존/부분/깨진 symlink 출력,
입력/선택 baseline 내부 출력은 거절한다. 출력 덮어쓰기·resume·삭제·자동 baseline 갱신 없음.
선택 baseline도 모델 전에 기존 no-follow bounded reader로 완전한 사본을 확보하고 전체
schema/checksum을 검산한다. portable subset은 baseline이 아니다. 후속 비교는 원본이
아닌 사본을 소비한다. original receipt의 경로는 metadata일 뿐 따라가지 않는다.

## 실행·산출물

- owned 입력을 `inputs/case-NNN.json`에 원형 보존. 실제 사용자 경로/이름은 private receipt만.
- 같은 사본을 R37 validator로 확인하여 `VALIDATION.json` 저장. 모델 실행0.
- 기존 R33 `run_batch`를 그 사본에 실행하여 `batch/`와 기존 개별 HTML/그래프/표 생성.
- 기존 R39 `check_batch`를 완전한 `batch/`에 실행하여 `reference/` 생성.
- 선택 baseline이 있으면 기존 R34 `run_comparison`으로 `regression/` 생성.
- `WORKFLOW.json` / `SUMMARY_KO.md` / private `RECEIPT.json` / 전체 `SHA256SUMS.txt`.

루트 WORKFLOW에는 상대 링크·각 stage 상태·거절 수·모델/참조/helper 작업량·source identity·
닫힌 Gate를 기록한다. 전체 sums는 모든 다른 파일 및 nested sums를 덮는다. 완료 JSON을
마지막에 기록하며 marker만으로 성공을 판정하지 않는다. 오류/부분 출력은 보존한다.
직접 호출한 stage가 예외를 내면 exit2/REJECTED, 루트 완료 JSON을 만들지 않는다.

## 상태와 종료 코드

판정 우선순위: ERROR > REFERENCE_DIFFERENT > REGRESSION_DIFFERENT > INCOMPLETE >
NO_COMPLETED_CASES > VERIFIED_WITH_INPUT_REJECTIONS > VERIFIED.

- VERIFIED: 수치 case 모두 참조 MATCH, 입력 거절 없음, 선택 회귀도 MATCH. exit0.
- VERIFIED_WITH_INPUT_REJECTIONS: 완료 case는 MATCH이나 입력 거절도 있음. exit1.
- REFERENCE_DIFFERENT / REGRESSION_DIFFERENT / INCOMPLETE / NO_COMPLETED_CASES: exit1.
- ERROR 또는 요청/IO/source/runtime/worker 오류: exit2. fallback이나 거짓 성공 없음.

R39 ERROR의 reference count는 성공한 child만 집계한다. 실패한 작업은 NONZERO일 수 있고
미집계임을 명시한다. 모든 입력이 거절되면 수치 검증 성공이 아니다.

## 정확성·재현성·공유

batch/model 단계의 실제 sample 수와 R39 참조/helper 수를 별도 기록한다. R37/R34/R39의
새 public 모델0을 전체 작업0으로 표현하지 않는다. source 및 owned raw의 전후 관찰이
달라지면 루트 완료 결과를 발행하지 않는다. cooperative 관찰이지 atomic/OS 인증은 아니다.

같은 입력·source/runtime에서 루트 WORKFLOW/SUMMARY/VALIDATION 및 batch portable 결과를
반복 비교한다. private receipt에 따라 full batch/reference report/전체 sums는 달라질 수
있다. 이를 숨기거나 같은 cloud full hash를 강요하지 않는다. 임의 tolerance/정규화/수치
expected 자동 갱신 없음. 고정·bounded 합성 source parity이지 범용 독립 oracle이 아니다.

완전한 결과에는 private 경로와 합성 원문이 있다. 자동 공유/ZIP/publish 기능은 넣지 않는다.
기존 standalone 명령과 public wheel은 그대로 유지한다.

## 유지 제한

실제 r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/V/F71 NOT_ALLOWED.
F61·실제 r/dt·Controller·차량 Runtime·CAN·실차 입력/활성화·후보 평가는0.
