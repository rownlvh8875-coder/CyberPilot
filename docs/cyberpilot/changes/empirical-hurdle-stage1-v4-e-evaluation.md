# V4 D0/D1 오프라인 평가 — 실행 전 동결 계약

이번 실험은 기존 V4 모델을 다시 학습하지 않고, 이전 tick 변화가 없는 경우와 있는 경우에 TRAIN 판단값을 따로 정하는 D1을 평가한다. 비교 기준 D0는 원래 저장된 V4 결과다. 개선 여부는 실제 실행 전에는 알 수 없다.

- 기준 HEAD: `4e5760f12d6f37401f2752b91d2223a336d353a7`.
- 정책: [동결 D 설계](empirical-hurdle-stage1-v4-d-transition-aware-policy.json).
- 실행 계약: [E protocol V1](empirical-hurdle-stage1-v4-e-execution-protocol.json). 자체 canonical receipt와 공개 입력 raw SHA, 원래 실행 source 및 새 평가기 SHA를 결부한다.
- 이전 C의 224개 필드 검증과 진단 결과를 보전한다. 추가 source root는 과거 성공한 실행 기록에서 복구하여 공개 root identity와 대조했고, 정확 경로와 기록은 Git 외부 비공개 handoff에만 둔다.

## 실제 실행 순서

1. 정확 host/volume/mount, 기존 B0/B1/C 봉인과 행 순서 provenance, 공개 입력과 source bytes, 출력 권한·용량을 확인한다. 디렉터리 탐색이나 대체 source는 허용하지 않는다.
2. Synthetic/회귀/build/privacy 검증과 두 독립 검토를 마친 protocol/code를 커밋하고 그 HEAD의 CI 성공을 확인한다. 비공개 controller도 정확 SHA로 결부한다.
3. 모든 32 jobs에서 TRAIN 두 context의 판단값 64개를 먼저 계산·봉인·fsync·digest 재확인한다. 그 전에는 DEV capability를 열지 않는다. 정수 balanced-accuracy numerator, TN, 큰 판단값 순으로 선택하며 strict `score > decision`을 쓴다.
4. Manifest로 지정된 기존 frozen head/normalizer/Stage2와 source-grid 입력을 읽는다. 혼합 `train/receipt.json`은 열지 않는다. Head 배열은 root/submanifest raw hash와 원래 basis에 결부하며, 미열람 descriptor까지 대조했다고 주장하지 않는다.
5. 같은 DEV anchor에서 one-step과 H25/50/100/200 전체 상태 rollout을 계산한다. 다음 context는 gate bit가 아니라 실제 projected tick 차이이며 전체 history도 갱신한다. 관측 future truth는 진단에만 사용한다.
6. 원래 32 acceptance clauses를 동일 anchor의 HOLD_LAST에 적용한다. D0와의 paired 비교는 추가 진단이다. 양 Fold 모두 보호하며 지원 부족과 수치 실패는 통과시키지 않는다.
7. 새로운 프로세스와 별도 exclusive 출력에서 동일 실험을 반복한다. Run envelope를 제외한 canonical 결과는 byte-exact해야 한다. Verify-only는 저장 결과·봉인만 확인하고 source 재읽기·inference·재계산은 0이다.

## 수치 의미와 제한

One-step continuous integrated delta error, projected integer exact-hit, 실제 tick 변화, gate correctness는 별개다. FP→HOLD와 harmful false movement를 나누며 exact-hit 손실/이득 항등식을 검사한다. Gate TP의 continuous residual과 projected step residual도 분리한다. Recursive movement/context/full-history drift, next-bit lag, first events 및 moved gate-perfect support FULL/SMALL/EMPTY는 private descriptive 진단이며 독립적인 인과 기여율이 아니다.

Source-grid tick은 물리 EPS torque나 검증된 실차 조향 성능이 아니다. Supplied command/speed 조건부 retrospective 계산이며, 이미 관찰한 DEV를 blinded independent validation이라고 부르지 않는다. 겹치는 32 jobs를 독립 주행 실험으로 해석하지 않는다.

## 권한·공개·중지

원본 read-only, 정확 member allowlist, openat2, bounded single-gzip/NPY, hash/shape/dtype/order, resource 상한을 적용한다. 이는 전체 process OS sandbox라는 주장이 아니다. Synthetic 회귀에서는 private drive를 가려 실제 데이터 실행과 구분한다. 기존 모델·정책·runtime·controller·workflow는 수정하지 않는다.

공개 projection은 양 arm·양 Fold를 함께 억제하며 기존 C의 onset/continuation 공개 제한을 유지한다. 과학적 셀/빈 건수, exact-hit·within-tick 비율, private path/input hash, 판단값, 계수, 개별 prediction은 게시하지 않는다. 허용된 fold별 job median/range와 clause 상태만 안전 조건을 통과할 때 공개한다.

기존 D0 `HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`, `selected_candidate = null`은 불변이다. 원래 TRAIN gate는 `NOT_SAVED`, 원래 whole-replica equality는 `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`다. HOLDOUT CLOSED, vehicle authority NONE, Hugging Face NOT_REQUIRED / NOT_USED를 유지한다. E 통과도 정책 채택·HOLDOUT·차량·V5 승인으로 이어지지 않는다. 최종 결과 공개와 exact-head CI/clean 확인 후 중지한다.

실제 결과·operation counts·최종 검증은 실행 후 별도 공개 결과 receipt에만 기록한다. 이 사전 문서는 실행 완료를 의미하지 않는다.
