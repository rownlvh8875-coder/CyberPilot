# R35 — 고정 합성 시나리오 회귀팩

기존 R31 실행 → R33 batch → R34 저장 결과 비교를 사용하는 입력·기대값·테스트
묶음입니다. 새 CLI나 모델/API 변경은 없습니다. 정상6개 시나리오38개 호출과
의도적 거절3개를 함께 유지합니다. 기존 두 예제도 그대로 보존합니다.

## 고정 순서와 기대값

모든 입력은 [examples/r35](../examples/r35)에 있습니다. 순서는 아래 표 그대로이며
기계 판독 기준은 [별도 literal reference](../reference/r35_regression_expected_v1.json)의
order와 cases입니다. 기대값은 모델 실행 전에 직접 계산·기록했으며 자동 갱신하지
않습니다. 입력이나 모델을 바꾼다면 변경 사유와 새 기대값을 별도로 검토해야 합니다.

| 파일 (모두 _v1.json) | 확인할 동작 | 최종 명령 또는 거절 코드 |
|---|---|---|
| positive_crossing | 양수 이력에서 감쇠·부호 전환 | 2,4,6,1,-2,0,2,-2 |
| negative_crossing | 음수/0 분기에서 증가·부호 전환 | -2,-4,-6,-1,2,0,-2,2 |
| inactive_resume | 다른 요청/출력 이력, 비활성화와 재개 | 0,2,0,-2,2 |
| angle_counter | counter89/90/91, ±85와 -84.5 | 2,4,4,4,4 |
| fractional_driver | 소수 driver 경계와 nearest-even | 2,4,-2,-4,0,0 |
| quantization_ties | ±0.5/±1.5 tie, binary64와 -0.0 | 0,2,0,-2,5,0 |
| invalid_late_request | 뒤 sample의 bare integer request | SCENARIO_DOMAIN |
| invalid_order | 호출 index0 다음 index2 | SCENARIO_ORDER |
| invalid_policy | 받지 않는 rate_budget_per_s 필드 | SCENARIO_KEYS |

reference rows는 순서대로 index, previous_requested, previous_applied,
angle_counter_before, integer_request, limited_command, final_command,
steer_request, angle_counter_after입니다. 마지막 state와 선택된 trace/hex도 별도
literal로 보존합니다. bool/int/float를 같게 취급하거나 허용오차를 넣지 않습니다.

## 기대값 도출

이 문서의 수식은 변경하지 않은 **합성 모델**을 위한 계산입니다. F61 rate 정책,
실제 차량 한계·scale·시간으로 승격하지 않습니다. STEER_MAX16, UP2, DOWN5 등은
직접 정한 합성 fixture 값이며 차량 설정이나 관측값이 아닙니다.

부호 전환 두 파일에서는 driver가0이므로 driver 범위는 [-16,16]입니다.
이전 applied를 p라 하면 p>0일 때 rate 구간은 [max(p-5,-2),p+2], p<=0이면
[p-2,min(p+5,2)]입니다. 예를 들어 p=6에서 -16 요청은 [1,8]로 제한되어1이고,
다음 p=1에서는 [-2,3]이므로 -2입니다. 음수 mirror는 p=-6에서 [-8,-1]로
제한되어 -1입니다. 이전 **요청16/-16**을 이 p로 대신 사용하지 않습니다.

inactive_resume의 첫 선언은 index10, 이전 요청12, 이전 applied6, counter7입니다.
첫 제한값은8이지만 비활성화 이후 최종 출력은0, 다음 applied/counter도0입니다.
이전 요청에는16이 보존됩니다. 다음 활성 sample은 applied0에서 다시2로 시작합니다.

angle_counter는 초기88부터 high-angle에서89/90/91을 셉니다. 이때 request flag는
true/false/false이고 세 번째 뒤 counter는0입니다. abs(-85)는 경계를 포함합니다.
다음85 sample로 counter1을 만든 뒤 -84.5에서 실제1→0 초기화를 확인합니다.
마지막 request=true이며 최종 counter0입니다. 이 모델에서 request flag=false는
lat_active=false가 아니므로, 명령을 자동으로0으로 바꾼다고 해석하지 않습니다.

fractional_driver에서는 allowance0, factor1, multiplier1, MAX16이므로
driver=-13.5/-12.5일 때 양수 경계가2.5/3.5가 됩니다. 충분히 넓은 UP/DOWN64
안에서 nearest-even 결과는2/4이며 반대쪽 -2.5/-3.5는 -2/-4입니다.
driver=-16.0의0 경계는 python.float인 반면 -17.0에서는 clamp된 python.int0입니다.
같은 정수 최종값0이라도 선택 trace의 kind는 구분합니다.

quantization_ties는 MAX16을 곱해 ±0.5/±1.5를 만들고 nearest-even으로0/±2를
얻습니다. 0.3은 binary64 `0x1.3333333333333p-2`이며 곱16은
`0x1.3333333333333p+2`, 정수 요청은5입니다. -0.0의 request/product hex 부호는
보존되지만 정수 명령은0입니다. 임의 decimal 정규화나 Float32 왕복은 없습니다.

## 실행

기존 pinned Linux/CPython3.12.13 DEV 환경에서, 저장소 root 기준 Bash 예입니다.
출력 부모는 이미 존재해야 하며 각 출력은 **아직 없는 새 경로**로 바꿉니다.
기존 결과를 삭제하거나 덮어쓰지 않습니다.

```bash
r35_args=(
  --input tools/cyberlateral_dev/examples/r35/positive_crossing_v1.json
  --input tools/cyberlateral_dev/examples/r35/negative_crossing_v1.json
  --input tools/cyberlateral_dev/examples/r35/inactive_resume_v1.json
  --input tools/cyberlateral_dev/examples/r35/angle_counter_v1.json
  --input tools/cyberlateral_dev/examples/r35/fractional_driver_v1.json
  --input tools/cyberlateral_dev/examples/r35/quantization_ties_v1.json
  --input tools/cyberlateral_dev/examples/r35/invalid_late_request_v1.json
  --input tools/cyberlateral_dev/examples/r35/invalid_order_v1.json
  --input tools/cyberlateral_dev/examples/r35/invalid_policy_v1.json
)
uv run --project tools/cyberlateral_dev --locked --offline python -B tools/cyberlateral_dev/tools/scenario_batch.py "${r35_args[@]}" --output /absolute/NEW-r35-one
uv run --project tools/cyberlateral_dev --locked --offline python -B tools/cyberlateral_dev/tools/scenario_batch.py "${r35_args[@]}" --output /absolute/NEW-r35-two
uv run --project tools/cyberlateral_dev --locked --offline python -B tools/cyberlateral_dev/tools/scenario_compare.py --baseline /absolute/NEW-r35-one --candidate /absolute/NEW-r35-two --output /absolute/NEW-r35-compare
```

위 명령은 개별 실행 예입니다. batch 두 명령은 의도적 거절을 포함하므로 exit1이
기대값이며, `set -e`인 연속 스크립트에서는 비교까지 진행되지 않습니다. 단순히
exit1이면 합격하는 것이 아니라 BATCH.json의 input9/complete6/rejected3/model_steps38,
각 거절 코드와 전체 Manifest도 확인합니다. worker 오류는 기대하는 거절이 아닙니다.
비교 명령은 exit0/MATCH, 정상 sample38개 비교, 차이0, 새 모델 실행0이 기대값입니다.

## 검증 범위

공개0.3.0/기존 CLI 그대로 새 테스트가 raw 입력→prepared history→선택 수치/state,
저장 RESULTS→CSV/VIEW, 완전한 batch→비교를 실행합니다. 뒤쪽 불량 sample도 모델을
읽기 전에 전체를 거절합니다. 각 batch의 portable47파일과 전체 Manifest를 검산하고
독립2회 portable bytes를 직접 비교합니다. 개인 path를 담은 receipt와 이를 참조하는
전체 Manifest는 portable 동일성 대상이 아닙니다.

입력을 바꾼 별도 사본은 INPUT_CHANGED이며 같은 입력의 수치 회귀와 혼동하지 않습니다.
MATCH는 저장값 일치이지 수치의 올바름을 단독으로 증명하지 않습니다. 따라서 먼저
별도 literal로 지정한 행·state·선택 trace를 확인합니다. 모든 출력 field나 임의 입력의
독립 oracle/general qualification은 주장하지 않습니다. 새 브라우저 화면 검증도 별도 범위입니다.

공유 portable 부분 ZIP은 완전한 batch가 아니므로 R34 입력으로 쓸 수 없습니다.
실제 r/T2/scale이나 경과 초는 만들지 않습니다. 호출 index는 초·실차10ms가 아닙니다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED를
유지합니다. 실차 입력·Controller·Runtime·CAN·F61/r/dt·실차 설치는 범위 밖입니다.
