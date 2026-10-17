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

## 사전 검증 및 결과

이 commit은 실행 프로토콜을 고정하는 단계다. 실제 private numeric input 접근과 C 결과는 아직 수행하지 않았다. 실행 후 결과 전용 publication에서 실제 reads, bytes, 수치, 검증과 resume를 기록한다. 과거 PASS 수를 이번 결과로 사용하지 않는다.

## 보전 상태와 중지

`HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`, selected candidate `null`을 유지한다. Whole-run replica는 `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`, TRAIN rowwise gate는 `NOT_SAVED`다.

HOLDOUT은 CLOSED이며 `FUTURE_UNTOUCHED_HOLDOUT_REQUIRED`, `NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT`, `FINAL_POOLED_REFIT_NOT_AUTHORIZED`, `COMPOSITION_NOT_AUTHORIZED`를 유지한다. Vehicle은 NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED, authority NONE이다. Hugging Face는 NOT_REQUIRED / NOT_USED다.

Source-grid tick은 물리 EPS movement가 아니며 logged command는 POST-CARCONTROLLER normalized command다. `steeringRateDeg`는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다. C 완료는 모델·정책·실차 승인이 아니다. D/E/F와 V5는 별도 승인 전까지 시작하지 않는다.
