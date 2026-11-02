# R39 — 저장된 batch의 독립 계산·상태 일괄 검증

완전한 R33 batch를 한 번 읽고 검산한 뒤, 정상 case마다 기존 R38 독립 참조를 실행합니다.
R34는 두 저장 결과의 비교이고 R39는 선택 source의 참조 계산입니다. 둘은 같은 검사가 아닙니다.
공개 wheel API/CLI 옵션이 아닌 별도 DEV 도구이며 기존 모델0.3.0/wheel은 바뀌지 않습니다.

## 실행

기존 CPython3.12.13/Linux/binary64/NumPy2.5.3 locked DEV 환경에서 저장소 또는 부분
export root 기준으로 실행합니다. 추가 의존성·전역 설정·차량 장치는 필요하지 않습니다.

```bash
r39_component="$PWD/tools/cyberlateral_dev"
r39_parent="$(mktemp -d /tmp/cyberlateral-batch-reference-XXXXXX)"
# 이 값만 실제 완전한 R33 결과 경로로 바꾸세요. 공유 portable ZIP은 입력이 아닙니다.
r39_saved_batch='/absolute/complete-r33-batch'
uv run --project "$r39_component" --locked --offline python -B "$r39_component/tools/scenario_batch_reference_check.py" --input "$r39_saved_batch" --output "$r39_parent/check-one"
uv run --project "$r39_component" --locked --offline python -B "$r39_component/tools/scenario_batch_reference_check.py" --input "$r39_saved_batch" --output "$r39_parent/check-two"
```

입력은 BATCH/index/receipt/원형·portable sums, snapshots, 정상 case의 data6파일 및
report/log를 포함한 **완전한 R33 결과**여야 합니다. raw JSON·단일 R31·portable subset은
받지 않습니다. 원본 입력·저장 결과·receipt 경로의 파일을 따라가거나 수정하지 않습니다.
출력 부모는 존재해야 하고 각 출력은 input/component 밖의 새 경로여야 합니다.
기존/부분 출력을 삭제·덮어쓰기·resume하지 말고 새 경로를 사용하세요.

## 판정과 종료 코드

| 상태 | 의미 | exit |
|---|---|---|
| MATCH | 완료 case 모두 독립 참조와 일치, 입력 거절 없음 | 0 |
| MATCH_WITH_INPUT_REJECTIONS | 완료 case 모두 일치, 보존된 불량 JSON의 거절 사유도 확인 | 0 |
| DIFFERENT | 계산 값 또는 보존된 JSON의 거절 사유가 기록과 다름 | 1 |
| INCOMPLETE | 원본 bytes가 없어 거절 사유를 재확인할 수 없음 | 1 |
| NO_COMPLETED_CASES | 거절만 확인했으며 정상 수치 case는 없음 | 1 |
| ERROR | 하나 이상의 독립 참조 호출/결과 읽기 오류 | 2 |

잘못된 요청/완전하지 않은 입력/checksum·schema·runtime·source/출력 쓰기 실패는
`REJECTED: <code>`와 exit2입니다. preflight 실패에는 결과가 생기지 않습니다.
case 실행 오류는 명시적 ERROR 집계로 기록할 수 있으며 정상 case와 섞어 PASS하지 않습니다.
여러 문제가 있으면 ERROR > DIFFERENT > INCOMPLETE > NO_COMPLETED_CASES 순입니다.
입력 거절은 오류를 숨긴 성공이 아니며, 전체가 거절이면 수치 MATCH로 처리하지 않습니다.

거절된 raw snapshot은 현재 parser로 다시 확인합니다. recorded code와 같아야
INPUT_REJECTION_CONFIRMED입니다. valid input을 rejected로 표시하거나 사유가 다르면
REJECTION_MISMATCH입니다. snapshot이 없으면 INPUT_REJECTION_UNVERIFIED입니다.
이것은 보존된 JSON의 판정이지 과거 파일 접근 실패 사실·실제 출처의 인증이 아닙니다.

## 출력과 계산량

루트 BATCH_REFERENCE_CHECK.json/SUMMARY_KO.md/SHA256SUMS.txt와, 참조 계산이
완료된 case-NNN마다 R38 REFERENCE_CHECK.json/SHA256SUMS.txt를 저장합니다.
루트 sums는 child sums를 포함한 모든 다른 파일을 덮으며 nested sums도 각각 검산합니다.
stdout은 상태·count·새 모델0의 canonical JSON 한 줄입니다. 수치 상세 차이는 child
보고서를 따르며 case별256개 상세 cap과 전체 차이 수를 혼동하지 않습니다.

R35 혼합9개 batch의 기대값은 MATCH_WITH_INPUT_REJECTIONS /6matched/3confirmed/
38reference steps/새 public model0입니다. 한 번 검사에 limiter/fault helper 각각38회,
case별 helper 정의2개 compile이 필요합니다. 두 번 검사면 참조76steps이며 새 모델0입니다.
batch를 새로 생성했다면 그 R33 모델38steps는 별도로 NONZERO입니다.
unit/gate의 추가 합성 모델·참조 작업도 별도이며 전체 작업0회라고 표현하지 않습니다.

ERROR가 있는 검사에서 reference_steps/helper 합계는 **성공한 child 보고서만** 집계합니다.
실패한 호출도 작업을 일부 수행했을 수 있으며 그 count는 미확정입니다. ERROR case의
reference_steps는null로 기록하고 fake0이나 성공 보고서를 만들지 않습니다.
출력 쓰기 도중 실패하면 일부 파일이 남습니다. JSON marker 존재만으로 성공을 판정하지
말고 상태/전체 sums를 확인하세요. 재시도는 새 폴더에서 합니다.

## 소유 bytes·동일성·해석 경계

기존 R34의 no-follow/bounded reader로 원본을 한 번 읽어 private snapshot에 보존합니다.
모든 case의 record·hash·schema·raw/typed/report 관계를 검산한 뒤 R38이 그 사본의
완전한6파일 data만 소비합니다. 검증 후 원본 경로를 다시 열지 않습니다. 적용 한계는
32cases/8192samples/512files/총128MiB입니다. atomic/OS snapshot 인증은 아닙니다.
case 사이 상태는 전달하지 않으며 resumed initial_state도 선언값일 뿐입니다.

같은 완전한 input bytes/current source/runtime에서 반복한 모든 출력은 byte-identical입니다.
개인 receipt가 달라지면 input root hash와 child full report가 바뀔 수 있습니다. 서로 다른
새 producer 결과의 full hash를 억지로 비교하거나 baseline을 자동 갱신하지 않습니다.
원본 receipt에 들어 있는 경로는 metadata이며 따라가지 않습니다. 집계/요약에 개인 경로,
입력 파일 label이나 원래 로그를 복사하지 않습니다.

R39 DEV 모듈 추가로 새 R31/R33 producer의 observed DEV source identity/full RESULTS
bytes가 달라질 수 있습니다. 기존 R35 hand-authored 수치 literal과 public wheel은 보존합니다.
기존 R34/R38 계약·과거 source inventory/검증 기록을 새 검사 실행 증거로 바꾸지 않습니다.

한정 합성·선택 source parity일 뿐 전체 Controller 동등성·일반 수치 증명·실제 과거 이력·
입력 출처·물리 차량 안전·성능 평가가 아닙니다. 실제 r/T2/scale=null,
R_BUDGET UNRESOLVED, Static Gate FAIL, SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED, F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/V/F71 NOT_ALLOWED를 유지합니다.
F61·실제r/dt·Controller·차량Runtime·CAN·실차 입력/활성화·후보 평가는0입니다.
