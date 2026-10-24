# CyberPilot V4 — D0/D1 실제 오프라인 평가 결과

두 번의 fresh E 실험을 실제 저장 데이터로 수행했고, 32 jobs의 canonical 결과가 byte-exact로 일치했다. 최종 판정은 **E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE**이다. 종료 시 잘못된 MOVE gate는 줄었지만 STATIC_HOLD 오판과 one-step·TRUE MOVE 오차가 악화됐다. 장기 rollout RMSE의 job 중앙값은 개선됐으나 기존 필수 기준을 충족하지 못했다.

## 실행 및 근거

- 사전 실행 HEAD: `77e66c37206555400a7219e76fdc5e8eabc992ed`; [exact-head CI SUCCESS](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39094984620).
- Protocol: `V4_E_D0_D1_PROTOCOL_V2`, raw SHA256 `2933aaf1eb40addcd1e872e831901da3ff6b778147cdfe46150fc4c1251a37a5`. [동결 프로토콜](empirical-hurdle-stage1-v4-e-execution-protocol-v2.json), [D 설계](empirical-hurdle-stage1-v4-d-transition-aware-policy.json), [평가 계약](empirical-hurdle-stage1-v4-d-offline-evaluation-contract.json), [C 공개 진단](empirical-hurdle-stage1-v4-c-diagnostics.md).
- B0/B1/C/D의 sealed lineage와 224개 기존 logical field를 연결했다. 복구한 causal/derived reference는 기존 실행 기록 및 공개 root identity로 결부했으며 드라이브 탐색을 하지 않았다.
- 각 반복은 32 jobs의 TRAIN decision 64개를 먼저 독립 계산·durable seal/readback한 뒤 DEV를 읽었다. 각 반복에서 32 one-step jobs와 H25/50/100/200의 128 recursive job-horizon을 새로 실행했다.
- D0의 score·Stage2·projection·저장 path·same-anchor metric을 검증했다. D1만 두 context의 TRAIN decision lookup을 사용했다. 모델·normalizer·feature 순서·Stage2·projection·전체 history 갱신은 동결 소스와 같다.
- 공개 수치는 [frozen publisher](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_e_publication.py)의 검사를 통과한 [결과 JSON](empirical-hurdle-stage1-v4-e-results.json)이다. pointer는 `/metric_families`, `/transitions`, `/acceptance_by_job`; 운영·22-domain 검증은 [validation JSON](empirical-hurdle-stage1-v4-e-validation.json)에 있다.

## 통계 단위와 해석

아래는 Fold별 16 jobs의 중앙값이다. 범위와 valid_jobs는 결과 JSON에 함께 보존했다. 같은 행을 공유하는 candidate·anchor가 있으므로 pooled 독립 표본, 통계적 유의성, 독립 주행 32회로 해석하지 않는다. 중앙값의 D0→D1 표시는 같은 job 집합의 두 요약이며 paired 차이의 중앙값을 새로 계산한 것이 아니다. DEV는 이미 관찰됐으며 이번 비교는 retrospective이다.

## 네 전이 집단과 gate

이전 변화와 다음 truth가 (0,0)이면 STATIC_HOLD, (0,1)이면 MOVE_ONSET, (1,0)이면 MOVE_TERMINATION, (1,1)이면 MOVE_CONTINUATION이다. Truth는 평가 label이며 inference routing 입력이 아니다. One-step은 observed prior delta, recursive는 실제 projected delta와 전체 projected history를 사용했다.

| Gate 오류의 job 중앙값 | Fold A D0→D1 | Fold B D0→D1 |
|---|---:|---:|
| STATIC_HOLD false-MOVE | 34.886% → 48.855% | 0.778% → 30.972% |
| MOVE_TERMINATION false-MOVE | 100.000% → 54.415% | 100.000% → 9.840% |

MOVE_ONSET와 MOVE_CONTINUATION의 recall/FN·projected correctness는 비공개 결과에서 계산했지만 C 승계 suppression으로 공개하지 않는다. 공개값이 없다는 이유로 개선·보호 성공을 주장하지 않는다. Termination의 개선은 확인됐지만 continuation 보호와 같은 결론으로 대체할 수 없다.

Gate MOVE는 projected HOLD가 될 수 있다. STATIC_HOLD의 잘못된 MOVE gate 증가를 harmful realized movement 증가량으로 치환하지 않는다. 두 정책 모든 job에서 gate FP = FP projected HOLD + harmful false movement 및 candidate exact hits = HOLD_LAST exact hits − STATIC hit loss + MOVE hit gain, net = gain − loss를 검증했다. Exact-hit loss/gain/net과 harmful movement의 세부 수치는 rare-cell·complementary 보호에 따라 비공개다. Gate STATIC→HOLD 불변 조건은 유지됐다.

## One-step과 TRUE MOVE

기존 acceptance의 이 지표는 integrated gated continuous delta 오차이며 projected integer tick exact-hit과 구분한다. 단위는 source-grid tick increment다.

| Population / metric | Fold A D0→D1 | Fold B D0→D1 |
|---|---:|---:|
| one_step RMSE | 0.553319 → 0.582054 | 0.466649 → 0.551353 |
| one_step MAE | 0.268541 → 0.292014 | 0.188012 → 0.236428 |
| one_step P95 | 1.097298 → 1.121636 | 1.000000 → 1.000000 |
| true_move RMSE | 1.126815 → 1.211099 | 1.090212 → 1.346329 |
| true_move MAE | 0.921072 → 0.984713 | 0.955993 → 1.166658 |
| true_move P95 | 2.000000 → 2.000000 | 2.000000 → 2.000000 |

RMSE·MAE 중앙값은 두 Fold에서 모두 악화됐다. D0/D1의 teacher-forced score는 동일하므로 one-step ranking·Brier·calibration은 기존 C와 같은 점수 계약이다. 새 decision의 오류 변화가 새 representation이나 calibration 개선을 뜻하지 않는다. Gate-TP magnitude/quantized-step residual은 support 조건부로 계산했고 작은 집단은 미식별로 남겼다. Stage2 고유 오차와 quantization·selection·feedback의 독립 인과 기여율은 확정하지 않는다.

## Full-state recursive rollout

Projected terminal tick 오차다. 각 path/horizon을 동결된 eligible observed history에서 초기화했고, gate bit 대신 실제 projected tick 차이로 context와 전체 history를 갱신했다. PATH_MOVED는 observed truth path가 initial tick에서 한 번이라도 달라진 모집단이다. 원래 supplied command/speed에 조건부인 계산이다.

### RMSE

| Horizon / population | Fold A D0→D1 | Fold B D0→D1 |
|---|---:|---:|
| H25 OVERALL | 15.810565 → 15.112128 | 8.946854 → 7.606530 |
| H25 PATH_MOVED | 18.300889 → 17.395027 | 10.605424 → 8.877992 |
| H50 OVERALL | 27.086676 → 25.791616 | 16.262617 → 13.391612 |
| H50 PATH_MOVED | 29.228515 → 27.705474 | 17.565416 → 14.301677 |
| H100 OVERALL | 38.115380 → 35.483478 | 29.413911 → 22.696152 |
| H100 PATH_MOVED | 39.132907 → 36.426698 | 29.998508 → 23.088942 |
| H200 OVERALL | 44.510744 → 42.370625 | 45.282670 → 34.241959 |
| H200 PATH_MOVED | 44.841830 → 42.684271 | 45.376488 → 34.302735 |

### MAE

| Horizon / population | Fold A D0→D1 | Fold B D0→D1 |
|---|---:|---:|
| H25 OVERALL | 5.454032 → 5.523997 | 3.414510 → 3.040586 |
| H25 PATH_MOVED | 7.530104 → 7.548239 | 4.828180 → 4.193826 |
| H50 OVERALL | 10.566416 → 10.581651 | 6.418981 → 5.576230 |
| H50 PATH_MOVED | 12.412678 → 12.303012 | 7.486784 → 6.412828 |
| H100 OVERALL | 16.197921 → 15.874433 | 11.875771 → 9.640016 |
| H100 PATH_MOVED | 17.096399 → 16.763401 | 12.372273 → 10.004440 |
| H200 OVERALL | 20.465107 → 20.023169 | 19.356068 → 15.059034 |
| H200 PATH_MOVED | 20.769186 → 20.317480 | 19.438845 → 15.117083 |

### P95

| Horizon / population | Fold A D0→D1 | Fold B D0→D1 |
|---|---:|---:|
| H25 OVERALL | 24.000000 → 23.000000 | 15.500000 → 12.000000 |
| H25 PATH_MOVED | 29.000000 → 27.500000 | 20.500000 → 15.000000 |
| H50 OVERALL | 45.000000 → 44.000000 | 27.000000 → 22.000000 |
| H50 PATH_MOVED | 47.500000 → 46.000000 | 31.000000 → 24.000000 |
| H100 OVERALL | 68.000000 → 65.500000 | 48.000000 → 38.000000 |
| H100 PATH_MOVED | 70.000000 → 67.500000 | 50.000000 → 39.000000 |
| H200 OVERALL | 82.000000 → 74.500000 | 88.000000 → 62.000000 |
| H200 PATH_MOVED | 83.000000 → 75.000000 | 88.000000 → 62.000000 |

RMSE 중앙값은 모든 horizon/모집단/두 Fold에서 낮아졌다. 모든 job·지표가 개선됐다는 뜻은 아니다. Fold A의 H25 OVERALL/PATH_MOVED MAE와 H50 OVERALL MAE 중앙값은 악화됐다. D0보다 일부 좋아지는 것과 same-anchor HOLD_LAST 기준을 모두 통과하는 것은 다르다. Full-state drift와 moved gate-/movement-perfect subset은 비공개 descriptive 진단이며, support가 부족하면 원래 NOT_IDENTIFIABLE 규칙을 유지한다.

## Frozen 32 clauses와 22 domains

원래 policy raw SHA256 `606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1`, canonical receipt `1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60`를 그대로 적용했다. 5 one-step + 3 TRUE MOVE + 24 rollout, support 201, epsilon 0, same-anchor HOLD_LAST, both-fold 규칙과 inequality를 변경하지 않았다. D0 paired comparison은 HOLD_LAST를 대체하지 않는다.

D1은 Fold A 0/16 jobs, Fold B 0/16 jobs가 전체 gate를 통과했다. Both-fold qualifying candidate는 0/16이다. ONE_STEP_EXACT_HIT은 D0/D1 모두 32/32 jobs에서 실패했고 ONE_STEP_WITHIN_ONE_TICK도 각 Fold 4 jobs에서 실패했다. TRUE MOVE 세 clause는 두 정책 모두 통과했지만 D1의 D0 대비 TRUE MOVE RMSE/MAE 중앙값 악화를 없애는 결과는 아니다. 상세 clause 실패는 `/acceptance_by_job`에 있다.

22 domains를 기존 verification/failure_behavior와 연결했다. 실행·무결성 확인과 성능 합격을 구분했으며, 전이 세부 수치 억제·조건부 residual support·인과 미식별은 PASS로 꾸미지 않았다.

## 반복·실행량·안전성

- 두 반복의 canonical payload는 byte-exact. Run-specific envelope는 분리했다. 두 stored verify-only 모두 source rereads/inference/recompute/source writes = 0이었다.
- 각 반복 원본 읽기: TRAIN decision arrays 96 files / 62,492,752 bytes; DEV 저장 one-step arrays 224 / 105,814,816; D0 저장 rollout arrays 384 / 149,304,755; frozen model/normalizer arrays 416 / 111,740; causal/derived source arrays 1,232 / 45,984,446; metadata 637 / 8,566,855. 이는 원본 scientific input 읽기이며 lineage control·own-output 조회는 별도다.
- 초기 V1 중단까지 포함한 원본 읽기 총계: **5,985 file openings / 748,368,721 bytes**. 첫 중단은 0 completed jobs이며 metadata 4 / 1,242,951 bytes와 TRAIN arrays 3 / 2,575,042 bytes였다. [Startup repair 기록](empirical-hurdle-stage1-v4-e-startup-repair.md)을 보존했다. V2 두 반복의 blocked attempts는 0이다.
- 함수 호출 단위의 실제 inference·projection 및 별도 row-evaluation telemetry를 비공개 receipt에 기록했다. Gate-dependent 호출 수와 row-evaluation count는 모두 공개하지 않는다. 공개 실행량은 고정 job·horizon·TRAIN decision 단위로만 보고한다. Source writes, refit, calibration fit, additional search, posthoc tuning, raw/qlog, HOLDOUT, controller/vehicle 동작은 실제 private-input 기준 모두 0이다. Mixed TRAIN carrier와 원래 D0 threshold도 열지 않았다.
- 완료 후 임의 추가 private 요약 파일명은 output allowlist가 차단했다. 파일 생성·우회·source 재읽기·과학 재계산은 없었고, 봉인된 결과와 프로토콜은 변경하지 않았다.
- Read-only openat2·exact member binding·fd-stamp 검증 범위이며 OS sandbox, atime 보존 또는 전체 원본 store의 fresh 재해시를 주장하지 않는다. 원래 V4 whole-replica 상태는 REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED다.

## 검증과 공개 경계

사전 전체 AutoTune/controls 5,400 PASS(613.35s), E focused 47 PASS, lateral synthetic 16 PASS, Ruff·compileall·SCons PASS. 사후 E/D/B0/B1/TRAIN/C/attribution focused bundle 234 PASS, JSON 814개 parse·공개 receipt 2개·frozen source pin 45개 검증, Ruff·compileall·SCons도 통과했다. 실제 private 드라이브는 회귀 과정에서 숨겼다. 기존 synthetic fitting은 실제 입력 refit과 구분한다. 두 별도 reviewer agent가 exact V2 source/protocol/caller/doc bytes를 각각 science와 authority/privacy 관점에서 APPROVED했다. 실제 입력을 reviewer가 별도로 열거나 human/external 인증을 했다고 주장하지 않는다. 최종 공개 HEAD의 CI는 push 후 확인하며, 이 문서에 미리 SUCCESS로 기록하지 않는다.

Public projection은 양 policy·양 Fold 전체의 support/complement/paired-change 검사를 거쳤다. Onset/continuation, exact-hit·within-tick 수치, bins/cells/source IDs/private hashes, 실제 decisions·coefficients·normalizer·row arrays·private paths는 공개하지 않는다. 원본과 별도 private output에 0700/0600·exclusive creation으로 결과를 보존했다.

## 쉬운 답변과 중지

1. 움직임 시작을 덜 놓쳤는가: 실제로 계산했으나 inherited C suppression 때문에 공개 세부 변화는 제공하지 않는다. Onset 개선이 입증됐다는 공개 결론으로 승격하지 않는다.
2. 움직임 종료 오판은 줄었는가: 그렇다. 공개 가능한 termination false-MOVE 중앙값은 A 100%→54.415%, B 100%→9.840%로 줄었다.
3. 다른 오류도 괜찮은가: STATIC_HOLD false-MOVE gate와 one-step/TRUE MOVE RMSE·MAE는 악화됐다. Harmful projected movement의 정확한 변화량은 비공개다. 장기 RMSE 중앙값 개선과 일부 MAE 악화가 공존한다.
4. 종합 기준을 통과했는가: 아니다. D1의 전체 gate 통과 job은 0/32이며 qualifying candidate는 없다. 일부 장기 metric 개선만으로 채택할 수 없다.
5. 실차 준비가 됐는가: 아니다. Source-grid tick은 검증된 물리 EPS movement가 아니고 logged command는 applied EPS torque가 아니다. Steering rate는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다. 현재 실험은 실차 closed-loop 검증이 아니다.

기존 HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED / selected_candidate=null을 보존한다. Original TRAIN rowwise gate=NOT_SAVED도 그대로다. HOLDOUT CLOSED, FUTURE_UNTOUCHED_HOLDOUT_REQUIRED, NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, FINAL_POOLED_REFIT_NOT_AUTHORIZED, COMPOSITION_NOT_AUTHORIZED를 유지한다. Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED / authority=NONE, Hugging Face NOT_REQUIRED / NOT_USED다.

추가 정책·representation·모델 실험은 새 후보/선택 규칙/입력/검증/공개 범위를 동결하는 별도 D/E 승인이 필요하다. F/HOLDOUT/차량은 별도 권한이며 이번에 부여되지 않았다. 결과에 맞춘 tuning, 추가 후보, refit, V5, policy adoption으로 자동 진행하지 않는다. 최종 exact-head CI와 clean 상태를 확인한 뒤 중지한다.
