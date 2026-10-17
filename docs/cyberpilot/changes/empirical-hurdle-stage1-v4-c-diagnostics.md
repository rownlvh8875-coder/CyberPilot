# V4 Stage1 C 진단 집계

CyberPilot V4가 저장한 점수와 실제 gate를 다시 읽어, 움직임 시작과 종료에서 어떤 오류가 나타나는지 확인한다. 새 모델이나 판단 기준은 만들지 않는다. TRAIN gate는 저장되지 않았으므로 복원하지 않는다.

## 사전 고정 범위

- 저장소: `rownlvh8875-coder/CyberPilot`, `feature/cyber-autotune`.
- 기준: `8689ab0445b7de0c1785315e7ec90daccc684e59`.
- 원래 실행: `bd8045ef2a0da62a92603439f38e7740f5923622`.
- 입력: 16 candidate × 두 Fold의 32 jobs, TRAIN 세 필드와 DEV 네 필드만 사용한다. [프로토콜](empirical-hurdle-stage1-v4-c-diagnostic-protocol.json)의 정확한 필드 목록을 따른다.
- B0 및 B1의 224개 필드 무결성·기록된 원래 행 순서 증거를 비공개 binding으로 연결한다. V4 Repeat-1만 읽고, Repeat-2는 기존 B1의 필드별 일치 증거를 연결한다.
- 기존 B0/B1 reader, 과학적 실행 코드, 모델, normalizer, threshold 정책, controller, rollout 및 workflow는 변경하지 않는다. Apache-2.0 저장소의 additive 검증 도구다.

## 계산과 해석 계약

`prior_delta_tick != 0`은 source-grid 직전 변화다. 현재 truth와 결합해 STATIC_HOLD, MOVE_ONSET, MOVE_TERMINATION, MOVE_CONTINUATION을 구분한다. 미래 truth는 추론 입력으로 사용하지 않는다.

전체·이전 STATIC·이전 MOVE별 AUC, Brier, 평균 확률, MOVE prevalence, calibration bias를 계산한다. AUC는 점수 동점을 정확한 정수 쌍 수로 처리한다. float64 제곱 오차와 점수의 합은 `math.fsum`으로 고정한다. 분모 또는 class가 없으면 `NOT_IDENTIFIABLE`이다.

Reliability는 `[0.0,0.1), …, [0.9,1.0]` 열 구간이며 정책 후보가 아니다. DEV confusion은 저장된 gate만 사용한다. TRAIN에는 gate confusion이 없다. TRAIN/DEV의 N은 서로 달라도 되며, 각 역할의 고정된 N과 anchor에 각각 맞아야 한다.

Fold별 요약은 16개 job의 median/min/max와 유효 job 수다. 같은 주행 구간과 anchor가 겹치므로 독립 표본, pooled AUC, 유의확률 또는 인과효과로 해석하지 않는다. 합산 행 수를 사용하면 `JOB_ROW_EXPOSURES`로만 표시한다. One-step과 H200 rollout은 다른 모집단이다.

Gate MOVE는 projected tick 변화와 다르다. 이번 일곱 필드에는 Stage2 delta나 projected tick이 없으므로 harmful movement, Stage2 잔여 오차 또는 recursive feedback의 새로운 효과를 계산할 수 없다. [기존 attribution](empirical-hurdle-stage1-v4-causal-rollout-error-attribution.md)의 한계를 보전한다.

## 실행 전 안전 조건

새 reader는 B1의 정확한 압축·NPY·payload 해시와 N/dtype/C-order를 다시 대조한다. Linux openat2의 기존 경로 제한, bounded gzip/NPY 검증을 재사용한다. bool byte는 0/1만 허용하며 확률은 finite `[0,1]`, prior delta는 int64여야 한다. 다른 root, member, 혼합 TRAIN carrier, threshold와 coefficients는 읽지 않는다. OS 전체 sandbox가 있다고 주장하지 않는다.

프로토콜·코드 commit의 exact-head CI, synthetic 테스트, 두 독립 검토의 승인 뒤 현재 사용자 C 승인을 비공개 binding에 연결한다. 한 job씩 처리하며 주소 공간 2 GiB, CPU 900초, wall 1200초, 단일 thread, private result 8 MiB, 총 출력 상한과 reserve 각각 16 MiB를 고정한다. 원본 쓰기는 없고 결과는 별도 0700/0600 위치에 exclusive 생성한다. 원시 배열은 저장하지 않는다.

공개 출력에는 bin, 과학적 cell count, population total, per-job score가 없다. 양쪽 Fold의 모든 TRAIN/DEV job에서 모든 context의 두 truth class가 각각 201 이상인 경우에만 점수 요약을 공개한다. 한 context라도 부족하면 전체·이전 STATIC·이전 MOVE의 점수와 transfer 요약을 모두 숨겨 다른 context로 역산하지 못하게 한다. 전이율은 모든 job에서 N≥201이고 event/complement가 각각 0 또는 201 이상이어야 한다. 하나라도 부족하면 양 Fold의 해당 전이율 전체를 숨긴다. 이는 개인정보 공개 규칙이며 성능 acceptance cutoff가 아니다.

## 실제 실행 결과와 무결성

`C_DIAGNOSTIC_AGGREGATION_COMPLETE`: **32/32 jobs**, **224/224 승인 필드**를 실제로 읽고 집계했다. TRAIN/DEV의 모든 지정 지표와 고정 열 구간을 계산했다. 이 작업은 같은 저장 자료의 기술 집계이며 새로운 독립 주행 실험이 아니다.

프로토콜 V1의 raw SHA256은 `0549292dd5101c39b118839d881720a23037cc6db6e516c6fa5d8bcda04b742f`다. 실제 숫자 접근 전에 코드와 프로토콜을 [56f7d00ad0c304f91910902337e1da6419e85b0a](https://github.com/rownlvh8875-coder/CyberPilot/commit/56f7d00ad0c304f91910902337e1da6419e85b0a)에 고정했고, [그 exact-head CI](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39050624381)의 completed / SUCCESS를 확인했다. 이후 분석 코드·지표·bin·공개 규칙을 변경하지 않았다.

| 실제 E payload 읽기 | 파일 수 | Bytes |
| --- | ---: | ---: |
| TRAIN | 96 | 62,492,752 |
| DEV | 128 | 63,365,372 |
| 합계 | 224 | 125,858,124 |

기존 비공개 handoff, B0/B1 binding/result/resume와 공개 authorization·원래 writer source identity를 연결했다. E의 metadata carrier는 새로 열지 않았다. Repeat-2도 다시 읽지 않았다. 각 payload의 압축·NPY·수치 payload 해시, exact N/shape/dtype/C-order와 기록된 원래 행 순서 증거가 통과했다. TRAIN의 inner hash 기대값은 봉인된 B1 관측 기록이며, 미열람 mixed descriptor와 비교했다는 뜻이 아니다.

한 번의 실행에서 완료 job 집계 32회를 기록했다. 원본 쓰기와 금지 연산 19종은 모두 0이고 차단된 금지 시도도 0이다. 결과는 Git 외부의 제한된 별도 위치에 봉인했다. 원시 배열 복사본은 저장하지 않았다. Verify-only는 원본 재열기 0, 재계산 0으로 PASS했다. 공개 요약 작성은 저장된 job 집계에 대한 고정된 projection이며 verify-only와 별도다.

## TRAIN/DEV 점수: Fold별 job median

아래는 각각 16개 job의 median이다. 전체 job 평균이나 pooled AUC가 아니다. [공개 결과 JSON](empirical-hurdle-stage1-v4-c-diagnostic-results.json)의 `folds`에 min/max, 유효 job 수, 평균 확률과 prevalence도 보존했다. 작은 집계와 bin은 공개하지 않는다.

| Fold / 이전 상태 | AUC TRAIN → DEV | Brier TRAIN → DEV | DEV calibration bias |
| --- | --- | --- | ---: |
| A / 전체 | 0.713364 → 0.699326 | 0.108829 → 0.107032 | +0.022214 |
| A / STATIC | 0.568525 → 0.537743 | 0.085896 → 0.084388 | +0.018292 |
| A / MOVE | 0.584332 → 0.590284 | 0.241472 → 0.242705 | +0.045765 |
| B / 전체 | 0.701325 → 0.706966 | 0.105541 → 0.109645 | −0.014195 |
| B / STATIC | 0.540976 → 0.555800 | 0.083700 → 0.086200 | −0.009418 |
| B / MOVE | 0.603997 → 0.558285 | 0.236867 → 0.245308 | −0.041870 |

TRAIN calibration-bias median은 표시 정밀도에서 모두 거의 0이다. 평균 bias가 0이라는 사실은 모든 score 구간에서 calibration이 정확하다는 증명이 아니다. 고정 reliability bin의 support/평균 점수/관측 MOVE 비율은 비공개 상세 결과에서만 보존한다. 새 calibration 함수는 fitting하지 않았다.

아래 변화는 **각 job의 DEV−TRAIN을 먼저 계산한 후 median을 낸 값**이다. 두 median을 단순히 뺀 값과 일반적으로 같지 않다.

| Fold / 이전 상태 | ΔAUC median [min, max] | ΔBrier median | Δbias median | Δprevalence median |
| --- | --- | ---: | ---: | ---: |
| A / 전체 | −0.014038 [−0.020060, −0.008299] | −0.001866 | +0.022214 | −0.004358 |
| A / STATIC | −0.030887 [−0.036357, −0.025514] | −0.001506 | +0.018292 | −0.003080 |
| A / MOVE | +0.007607 [−0.006118, +0.020576] | +0.001058 | +0.045765 | −0.001162 |
| B / 전체 | +0.004360 [−0.002122, +0.010705] | +0.004064 | −0.014195 | +0.004358 |
| B / STATIC | +0.014197 [−0.001180, +0.026897] | +0.002517 | −0.009418 | +0.003080 |
| B / MOVE | −0.044286 [−0.054109, −0.018525] | +0.008427 | −0.041870 | +0.001162 |

Fold A의 이전 STATIC AUC는 16개 모두 감소했다. Fold B의 이전 MOVE AUC도 16개 모두 감소했다. 반면 Fold B의 전체·이전 STATIC AUC median은 상승했다. 따라서 전체 ranking 개선 하나로 상태 내부 문제나 decision transfer가 해결됐다고 말할 수 없다. 이는 기술적 관찰이며 유의성·인과효과 또는 새로운 성능 acceptance 판정이 아니다.

## 저장된 DEV gate와 네 전이

| Truth transition | 필요한 gate | 이번 공개 Fold A | 이번 공개 Fold B |
| --- | --- | --- | --- |
| STATIC_HOLD | STATIC | false-MOVE median 34.886%, 범위 31.280–39.661% | false-MOVE median 0.778%, 범위 0.457–2.074% |
| MOVE_ONSET | MOVE | SUPPRESSED_PRIVACY | SUPPRESSED_PRIVACY |
| MOVE_TERMINATION | STATIC | false-MOVE 100%, 16/16 jobs | false-MOVE 100%, 16/16 jobs |
| MOVE_CONTINUATION | MOVE | SUPPRESSED_PRIVACY | SUPPRESSED_PRIVACY |

Onset와 continuation의 모든 수치도 실제로 계산했다. 다만 사전 고정한 event/complement support 규칙을 통과하지 못한 지표군은 양 Fold 전체를 숨겼다. 결과를 본 뒤 공개 규칙을 완화하지 않았다. Bin/cell count나 작은 job 결과를 우회 공개하지 않는다.

이미 공개된 [이전 attribution](empirical-hurdle-stage1-v4-stage1-confusion-attribution.json)의 onset recall A 40.195% / B 2.147%, continuation A 100% / B 약 99.999%는 기존 frozen 관찰이다. 이 수치는 겹치는 anchor의 **JOB_ROW_EXPOSURES 합산율**이며 이번 median을 대신하는 새 계산값이 아니다. 이번에는 동일한 one-step 모집단의 개별 job gate count가 32개 모두 정확히 일치했음을 확인했다.

STATIC_HOLD와 종료는 서로 다르다. Fold B의 STATIC_HOLD false-MOVE median은 작지만 MOVE_TERMINATION에서는 모든 job이 100% false-MOVE다. 이전 MOVE head가 항상 MOVE로 hard-code됐다는 뜻은 아니다. 기존 구현은 raw previous-delta로 head를 선택한 후 score와 frozen TRAIN decision으로 판단한다. 하나의 candidate/fold job 안의 두 head가 decision을 공유하며, 모든 job이 동일한 수치 threshold를 공유한다는 뜻은 아니다. 이번에는 그 threshold를 읽거나 적용하지 않았다.

## 무엇이 설명되고 무엇이 미식별인가

1. **관찰:** 이전 STATIC의 상태 내부 AUC는 전체 AUC보다 낮고 TRAIN에서도 완전한 분리가 아니다. Fold A에는 DEV에서 추가적인 ranking 감소가 있다. 기존 onset miss와 함께 관측되지만 representation 부족이 단독 원인이라고 확정하지 않는다. 기존 입력 history와 종료 negative label은 이미 있다.
2. **관찰:** Fold B는 이전 STATIC AUC median이 DEV에서 상승해도 기존 onset 검출 실패가 존재한다. 서로 다른 집계 단위의 효과 크기를 비교하는 것이 아니라, ranking이 frozen gate의 recall을 보장하지 않는다는 구분이다. Fold B의 이전 MOVE ranking 저하와 음의 bias도 별도로 남는다.
3. **관찰:** 종료 행에서 저장된 gate가 모두 MOVE다. 높은 continuation recall과 종료 FP는 같은 이전 MOVE population의 다른 truth 결과다. 순위를 일부 개선해도 특정 operating point가 두 집단을 올바르게 나눈다는 보장은 없다.
4. **미식별:** 어떤 private threshold, parameter 또는 새 policy가 단독 원인인지, 다른 기준이 더 나은지는 확인하지 않았다. TRAIN gate는 `NOT_SAVED`이며 전이별 TRAIN gate confusion을 복원하지 않았다. Brier/bias shift에는 population composition도 영향을 줄 수 있다.
5. **범위 밖:** Gate FP는 실제 projected false movement와 같지 않다. 새 tick/Stage2/rollout 자료를 읽지 않았으므로 magnitude residual, tick realization 및 recursive feedback의 독립 기여율은 이번 C에서 식별할 수 없다. 기존 관련 위험과 fail-closed 결론을 보전한다.

기존 [ranking](empirical-hurdle-stage1-v4-state-conditional-ranking.json)과 비교한 32 jobs의 support와 AUC 정수 numerator/denominator, [confusion](empirical-hurdle-stage1-v4-stage1-confusion-attribution.json)의 gate count는 exact 일치했다. Brier·평균 확률·prevalence·bias는 사전 고정한 산술 roundoff 허용량 2e−15 이내였다. 이 값은 성능 gate가 아니다. Exact-hit과 H200 rollout을 다시 계산하거나 one-step과 같은 모집단으로 비교하지 않았다.

## 검증과 독립 검토

- 신규 C synthetic 39 PASS, B0/B1/C focused 163 PASS, private caller synthetic 8 PASS.
- Attribution focused 95 PASS, combined empirical 2,469 PASS, full AutoTune/controls 5,329 PASS, lateral replay 16 PASS.
- Ruff, compileall, SCons, JSON, publication/privacy, authority/source identity 및 diff 검사 PASS. 로컬 회귀에서는 실제 D/E 자료를 mount namespace로 가렸다. 회귀의 synthetic fitting은 실제 private-input 연산과 구분한다.
- 최초 로컬 lateral 명령의 module 위치 오류는 실제 workflow의 process-replay 경로로 바로잡아 16 PASS를 확인했다. 제품 코드는 변경하지 않았다.
- 수치/무결성과 권한/개인정보 검토를 별도 GPT-6.1 Sol xHigh reviewer가 수행했다. 두 검토 모두 최종 bytes에 대해 실제 입력 접근 전 APPROVED였다. 초기 privacy 검토가 발견한 context 역산 문제는 synthetic 회귀로 재현·수정하고 재승인받았다.
- Verify-only는 실제 저장 결과 digest/seal을 확인하며 reader와 집계 함수를 trap한 상태에서 원본 재열기 0 / recompute 0 PASS였다. Whole-run replica를 새로 전부 검증했다는 주장은 하지 않는다.
- 결과 publication의 최종 exact-head CI는 push 후 확인하며 최종 handoff와 별도 비공개 receipt에 기록한다. 자기 참조 commit의 미래 CI 성공을 이 파일에서 미리 주장하지 않는다.

## 다음 승인 범위

C 입력 진단은 완료됐다. 다음에 새 판단 기준을 실제로 검토하려면 **D 정책 명세/변경 승인과 E 오프라인 효과 평가 승인**을 구분해 받아야 한다. TRAIN frozen gate 적용, boundary 분석, calibration fitting, 대체 gate, Stage2 및 recursive downstream 실행 중 허용할 항목을 명시하고 독립 평가 계획을 먼저 고정해야 한다. 이번 C는 어느 것도 승인하지 않는다.

향후 평가는 STATIC exact-hit 손실/이득, onset·termination·continuation, harmful projected movement, TRUE MOVE 보호, Fold A/B, 기존 32-clause both-fold gate, Stage2 residual, 25/50/100/200-step OVERALL/PATH_MOVED rollout, repeatability와 untouched future holdout 독립성을 함께 보전해야 한다. 새 수치 cutoff나 후보를 이번 결과로 선택하지 않았다.

## 보전 상태와 중지

`HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`, selected candidate `null`을 유지한다. Whole-run replica는 `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`, TRAIN rowwise gate는 `NOT_SAVED`다.

HOLDOUT은 CLOSED이며 `FUTURE_UNTOUCHED_HOLDOUT_REQUIRED`, `NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT`, `FINAL_POOLED_REFIT_NOT_AUTHORIZED`, `COMPOSITION_NOT_AUTHORIZED`를 유지한다. Vehicle은 NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED, authority NONE이다. Hugging Face는 NOT_REQUIRED / NOT_USED다.

Source-grid tick은 물리 EPS movement가 아니며 logged command는 POST-CARCONTROLLER normalized command다. `steeringRateDeg`는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다. C 완료는 모델·정책·실차 승인이 아니다. D/E/F와 V5는 별도 승인 전까지 시작하지 않는다.
