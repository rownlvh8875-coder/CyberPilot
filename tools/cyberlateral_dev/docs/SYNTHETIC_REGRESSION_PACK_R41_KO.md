# R41 — 합성 복합 경계·긴 상태 전이 회귀팩

R35 개별 경계 검증을 대체하지 않고 조합·반복 범위를 추가합니다. 기존 R40 명령,
R38/R39 선택 source 참조, 공개0.3.0 wheel/모델/API를 그대로 사용합니다.
새 CLI·의존성·차량 설치는 없습니다.

| 고정 입력 (examples/r41) | 호출 | 검증할 조합 |
|---|---:|---|
| combined_boundaries_v1.json | 12 | driver 반정수 경계→rate clip→nearest-even, 부호 전환, counter89/90/91, 비활성화, signed zero |
| repeated_inactive_crossing_v1.json | 128 | 이전 요청/출력이 다른8호출 cycle16회, 비활성화·재개·부호 전환과 실제 state carry |
| long_fault_cycles_v1.json | 184 | ±85 포함 경계,91호출 counter cycle2회와 다음2호출, request bit 억제와 명령 유지 |

정해진 순서는 [별도 기대값](../reference/r41_regression_expected_v1.json)의 order입니다.
총3완료/0거절/324합성 모델 호출과324선택-source 참조 호출이 한 회차 기대값입니다.
검사·renderer·참조 checker의 새 public 모델0은 참조 계산0이 아닙니다.
unit/gate의 추가 합성 작업은 명시적 CLI 회차와 별도로 집계합니다.

## 독립 기대값과 정확성

모델 실행 전에 손으로 도출한12행,8행 반복 cycle,184호출의 closed-form counter/
flag/command 규칙과 최종 state를 등록했습니다. 모델 출력에서 golden을 만들거나
실패 후 자동 갱신하지 않습니다. bool/int/float와 signed-zero hex를 구분하고 허용오차를
넣지 않습니다. R39는 전체 saved rows/final_state를 별도 selected-source worker와 비교합니다.
선택 literal 일치와 source parity는 서로 다른 검사이며, 범용 독립 oracle을 뜻하지 않습니다.

R41 후속 보완에서는 long-fault의 sample_count184/fault_period91/complete_cycles2/
tail_samples2/suppressed_offsets[89,90,180,181]을 행 전개 전에 타입까지 정확히 검증합니다.
그 뒤 검증된 주기·호출 수·offset을 사용합니다. 잘못된 값·누락·int를 float/bool로 바꾼
메타데이터는 거절하며 기존 상수로 조용히 대체하지 않습니다. 이는 고정 회귀팩의
기대값 기록 보호이고, 변경 가능한 fault 정책 API나 실제 시간/차량 정책이 아닙니다.

합성 MAX16/UP2/DOWN5는 실제 scale·차량 한계·F61 r이 아닙니다. driver clip 뒤에
history/rate clip이 적용되므로 +3.5 driver 경계가 있어도 이전 applied-4이면 최종1입니다.
비활성화 sample은 제한값3/-4를 계산하고도 최종 applied/counter를0으로 만듭니다.
반면 high-angle fault 억제로 request=false가 된 것은 비활성화가 아니므로 명령을
자동0으로 바꾸지 않습니다. 184호출에서는 offsets89/90/180/181만 request=false이며,
첫 명령2 이후 명령4를 유지하고 최종 counter2입니다.

별도 saved 사본에 cycle 경계의 applied를2→16으로, fault counter를90→89로 바꾼
coherent 오답을 넣습니다. 중복 CSV/VIEW·checksum만 재생성한 뒤 참조가 후속 prepared
state의 차이를 검출해야 합니다. 참조가 잘못 저장된 상태를 자신의 이전 상태로 소비하면
실패하는 음성 대조입니다. 원본 입력·모델·기대값은 수정하지 않습니다.

## 실행

기존 locked CPython3.12.13/Linux x86_64/NumPy2.5.3 DEV 환경에서 저장소 root 기준:

```bash
r41_component="$PWD/tools/cyberlateral_dev"
r41_parent="$(mktemp -d /tmp/cyberlateral-r41-XXXXXX)"
r41_args=(
  --input "$r41_component/examples/r41/combined_boundaries_v1.json"
  --input "$r41_component/examples/r41/repeated_inactive_crossing_v1.json"
  --input "$r41_component/examples/r41/long_fault_cycles_v1.json"
)
uv run --project "$r41_component" --locked --offline python -B "$r41_component/tools/scenario_workflow.py" "${r41_args[@]}" --output "$r41_parent/one"
uv run --project "$r41_component" --locked --offline python -B "$r41_component/tools/scenario_workflow.py" "${r41_args[@]}" --output "$r41_parent/two"
uv run --project "$r41_component" --locked --offline python -B "$r41_component/tools/scenario_workflow.py" "${r41_args[@]}" --baseline "$r41_parent/one/batch" --output "$r41_parent/baseline-check"
```

각 명령은 새 모델324/참조324호출을 수행하고 VERIFIED/exit0이어야 합니다. 세 번째는
별도 저장값 비교 MATCH/324samples/차이0/추가 모델0도 확인합니다. 각 출력은 새 경로이고
완전한 baseline batch를 보존하며, portable 공유 부분만으로 baseline을 대신하지 않습니다.
SUMMARY_KO.md에서 개별 저장 리포트로 이동할 수 있지만 새 브라우저 실측은 별도입니다.

앞의 두 회차에서 WORKFLOW.json/VALIDATION.json/SUMMARY_KO.md와 batch portable23개가
byte-identical이어야 합니다. 세 번째는 baseline 메타데이터가 달라 root 기록은 동일성
대상이 아니지만 batch portable은 동일합니다. 개인 경로가 든 receipt/전체 Manifest의
bytes 일치, 전체 runtime 동일성, atomic snapshot은 주장하지 않습니다. 공유 전 원형 입력·
개인 경로·Manifest 참조를 따로 점검하고 전체 결과를 자동 게시하지 마세요.

## 유지 제한

긴 시퀀스는 호출 순서 검사이지 실제 시간·100Hz·주행 성능·native replay 검증이 아닙니다.
184호출을1.84초로 환산하지 않습니다. 실제 r/T2/scale=null, R_BUDGET=UNRESOLVED,
Static Gate=FAIL, Candidate/Runtime=NO_GO, F70UH/V/F71=NOT_ALLOWED 유지.
F61·실제 r/dt·Controller·Runtime·CAN·실차 입력·실차 설치/활성화·후보 평가는0입니다.
