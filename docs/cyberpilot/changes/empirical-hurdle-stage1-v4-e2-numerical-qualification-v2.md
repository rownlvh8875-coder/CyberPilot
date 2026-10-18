# E2 numerical qualification V2

Mission: `STAGE1_V4_E2_NUMERICAL_QUALIFICATION_CONTRACT_V2`
Scope: `CONTRACT_DESIGN_AND_SYNTHETIC_VALIDATION_ONLY`
Baseline: `93bc9db25565bcd8b6bd988550c4488ad1c42500`
Baseline exact-head CI: [39136679623 completed / SUCCESS](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39136679623).

이 increment는 공개 계약 두 개와 synthetic test만 추가한다. 기존 E2 executor, D2 정책, V1 프로토콜, 실패 결과, 진단 결과, acceptance 및 workflow는 그대로 보존한다. 실제 E2 재실행과 정책 채택은 승인하지 않는다. 최종 동결 판정은 아래 검증과 두 독립 최종 byte 검토 및 GitHub exact-head CI를 모두 확인한 뒤 handoff에서 확정한다.

- `V4_E2_NUMERICAL_QUALIFICATION_CONTRACT_V2`: raw SHA256 `7a51775da2ec0edd18c21abf73d78123f940cff3c8e125ddac0cd43857427ccf`, canonical receipt `dfca44a4a0658f09568d657b4961a565b28be29c60d6634e3ff3ec972d796755`.
- `V4_E2_D0_D1_D2_PROTOCOL_V2`: raw SHA256 `7a4e02966d921759430a4b6c3c9ca1f343f400a293e4f79f1a9a73fb8aaeeb2f`, canonical receipt `be0bc8005695b03bff57a128374cf535eee76989d4b52c3239f29d1f1967bd08`.

## 근거와 문제

[공개 root-cause 결과](empirical-hurdle-stage1-v4-e2-numerical-root-cause.json)의 한 작업 `HRI_D00_L01 / FOLD_B / TRAIN`에서 A는 original-segment/order 512-row all-row cache, B는 chunk-local D0 selected rows, C는 원래 D0 whole-job selected rows, W는 whole-job all rows다. 변환된 입력 행은 byte-exact했지만 B/A float와 bytes가 달랐다. C/A와 W/A는 byte-exact했고 해당 작업의 projected tick은 같았다. 이는 batch/layout-sensitive matmul 차이의 증거다. 특정 BLAS 내부 kernel 또는 FMA instruction은 확인하지 않았다.

고정 synthetic 60개와 추가 고정 대조 60개는 원본 그대로 유지한다. 추가 대조에서 B/A 44/60 불일치, 최대80 ULP, 동일64-byte alignment에서도 차이가 재현됐다. 별도 rounding-boundary fixture에서는1 ULP가 projected tick을 바꿀 수 있다. 이 synthetic 결과와 실제 한 작업 결과는 구분한다. 나머지31개 TRAIN job과 D2 selected path의 동등성은 아직 확인되지 않았다.

원래 D0는 전체 job에서 gate가 MOVE인 행을 원래 순서대로 모아 Stage2를 호출한다. B는 그 경로가 아니다. 실제 C/A PASS와 B/A FAIL의 공존은 B/A가 C/A의 필요조건이 아님을 보여 준다. 기존 synthetic의 다른 batch 비교도 B/A가 C/A를 대신하는 충분조건이 아님을 보여 준다. V1은 B/A에서 먼저 중단돼 C/A에 도달하지 못했다. 이 역사적 실패를 소급해 PASS로 바꾸지 않는다.

## V1 → V2

| 검증 | V1 | V2 |
|---|---|---|
| B/A chunk subset | C/A 이전 필수 중단 조건 | Q2 non-authoritative diagnostic, 기본 private 실행 없음 |
| C/A whole-job D0 subset | B/A 이후 hard gate | Q1 hard gate,32/32 완료 후 D2 선택 |
| D2 whole-job selected subset/cache | 별도 hard gate 없음 | Q3 hard gate,64 decisions 선택 후32/32 완료, 최종 TRAIN seal·DEV 이전 |
| 수치 허용오차 | 없음 | 없음: dtype/shape/order/raw bytes 및 signed zero까지 동일 |
| D2 objective·guards·tree | 동결 | 완전히 동일 |
| 성능 acceptance | frozen32 | 완전히 동일 |
| 권한 | 과거 V1 실행 승인 | 이번에는 계약·synthetic만, 새 V2 실행 승인 필요 |

Q1은 original `predict_delta(ascontiguousarray(x_full[D0_gate]), stage2)`와 같은 행의 A를 비교한다. Source/model/normalizer/ordered anchor와 입력 identity가 동일해야 한다. 모든32 jobs에서 통과해야 한다. 실패 상태는 기존 `E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`다. Projected tick만 같거나 ULP 차이가 작아도 통과하지 않는다.

Q2는 기존 공개 진단과 synthetic regression으로 보존하며 기본 실제 실행 상태는 `NOT_EXECUTED_DIAGNOSTIC`이다. 향후 bounded private 진단을 추가하려면 별도 scope·resource·privacy binding이 필요하다. Q2 mismatch가 Q1 실패를 무시하게 하거나 Q1 PASS를 대신하게 하지 않는다. Private mismatch telemetry를 공개하지 않는다.

Q3는 두 context의 최종 선택 decision으로 original-order full-job gate를 구성하고, `predict_delta(ascontiguousarray(x_full[D2_gate]), stage2)`와 A의 동일 행을 byte-exact 비교한다. 원래 D2는 같은 frozen Stage2를 실제 MOVE selected path에 사용하므로 cache 기반 TRAIN loss가 그 경로와 일치하는지 확인하는 보수적 numerical eligibility gate다. Objective, guards, 후보 grid 또는 winner는 바꾸지 않는다. Per-threshold Stage2 재계산도 아니다. Q3에 실패하면 차선 decision을 고르지 않고 `E2_D2_TRAIN_SELECTED_PATH_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`로 중지한다. 이는 성능 FAIL 판정이 아니다.

D0-equivalent feasible witness 증명은 공통 cache에 대한 TRAIN 선택의 비공집합 증명으로 유지된다. 그 증명이 임의의 D2 winner에 대한 Q3 통과까지 보장하지는 않는다. Q3 불일치 시 re-batching retry, epsilon, clipping, row 삭제, objective 변경, DEV·rollout 진행을 모두 금지한다.

Empty gate는 원래 integrated가 Stage2 호출을 건너뛰고 full-N positive-zero delta와 HOLD tick을 반환하는 no-op 계약으로 확인한다. Gate/shape/order/identity와 빈 selected/cache view를 검증한 별도 `VERIFIED_EMPTY_GATE_ORIGINAL_INTEGRATED_NOOP` 상태를 기록한다. 증거 없는 자동 PASS는 금지한다. All-MOVE gate는 전체 행에 대한 실제 selected call과 byte 비교가 필요하다.

## 단계와 수치 의미

A exact input preflight → B all32 D0 TRAIN reconstruction → C all32 fixed512 potentials → D all32 Q1 → E all64 D2 decisions → F all32 Q3 → G durable TRAIN seal/fsync/readback → H DEV barrier release 순서다. 각 fresh repeat에서 독립적으로 수행한다. TRAIN route가 반대 Fold의 DEV route와 겹칠 수 있다는 기존 공개 계약은 유지한다. TRAIN role의 admitted source 외 DEV saved score/gate/metrics 및 E1 canonical result는 barrier 전에 열지 않는다. 새로운 blinded validation으로 표현하지 않는다.

D2 candidate set `{0,1} ∪ unique finite context TRAIN scores`, strict `p > decision`, equality STATIC, signed-zero 후보 동일 숫자 처리, original-order fixed binary64 loss tree, exact integer counters와 deterministic tie 순서를 유지한다. D0 동일 TRAIN context 대비 TRUE MOVE TP 감소 없음, SSE/SAE 증가 없음, harmful STATIC realized movement 증가 없음의 네 guard도 그대로다. Cache delta의 signed zero는 byte 비교에서 구분한다.

Frozen Stage2, normalization, ties-to-even 및 signed16 overflow fail-closed를 바꾸지 않는다. One-step은 observed prior delta, recursive는 실제 previous projected tick delta로 head와 decision을 선택한다. Gate MOVE가 realized movement를 뜻하지 않으며 future truth는 routing 입력이 아니다. Continuous delta/SSE/SAE도 중요하므로 tick equality로 float equality를 대체할 수 없다.

## 자원 상한 검토

Nmax336941, Pmax93, source rows916535, admitted segments≤154, chunk512, worker1, threads1, Hmax200을 공개 frozen 계약에서 사용한다. 실제 private input의 자원 측정은 하지 않았다.

| 항목 | V1 | V2 한 repeat 상한 |
|---|---|---|
| All-row Stage2 | K calls | 동일K, K≤25984 보수적 상한 |
| D0 selected Stage2 | chunk B≤K + whole-job C≤32 | Q1≤32, 기본 Q2=0 |
| D2 selected 검증 | 없음 | Q3≤32, 각 job nonempty일 때1회 |
| Selected row volume | B≤32×Nmax, C≤32×Nmax | Q1·Q3 각각≤10,782,112 |
| 보수적 live-buffer bound |1,410,679,894 bytes |5,574,680,630 bytes, runtime reserve2GiB 포함 |
| Address space |8GiB |8GiB 그대로 |
| CPU / wall |6h /12h |6h /12h hard abort caps 그대로 |
| Input / output |3000 opens·64GiB /384MiB |같음, 추가 source reread 없음 |
| Qualification receipt 증가 | 별도 없음 |≤262,144 bytes/repeat, 기존 output cap 안에 포함 |

새 memory bound는 V1 buffer bound에8×Nmax×Pmax×8 matrix workspace,32×Nmax 비교 bytes, qualification proof bytes 및2GiB runtime reserve를 보수적으로 더했다. V1과 design workspace 일부를 의도적으로 중복 산정한다. Q1/Q3 때 full x/selected x/transform/index/subtraction/division/assembly buffer를 제한하고, selection tree는 Q3 전에 해제한다. Resident immutable TRAIN source blocks에서 동일 순서 features를 다시 구성하며 private source를 다시 읽지 않는다. 이러한 실제 caller liveness와 BLAS workspace를 향후 코드에서 증명하지 못하면 numeric 접근 전에 `E2_RESOURCE_PREFLIGHT_BLOCKED`다.

전체 Stage2 호출 수가 줄 수 있어도 wall time 개선을 주장하지 않는다. Row/call bound로 BLAS 실행시간을 보장할 수 없다. CPU/wall 상한은 완료 보장이 아니라 중지 한계다. 향후 exact caller 및 승인된 runner capacity proof가 필요하며, 부족하면 자동 예산 연장 대신 중지한다. Optional Q2 private diagnostic은 기본 예산에 포함되지 않는다.

## 보존되는 평가·개인정보·권한

Frozen acceptance raw SHA256 `606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1`의5 one-step +3 TRUE MOVE +24 rollout clauses, support201, epsilon0, same-anchor HOLD_LAST, 원래 inequality, 양 Fold, H25/50/100/200 OVERALL/PATH_MOVED를 그대로 유지한다.22 validation domains와 R01–R17 traceability도 원본과 deep-equal이다. Q1/Q3 통과는 성능 합격이 아니다.

D0/D1/D2 세 arm, 두 fresh process/repeat, 별도 private output, canonical byte-exact 비교, source/inference/recompute0 verify-only를 유지한다. C/E의 기존 joint complementary suppression, 최소 support201, onset/continuation 및 rare exact-hit 억제를 완화하지 않는다. Q1/Q3 row telemetry·private hash/path/decision/coefficients도 private에만 남긴다.

이번 actual private-input operation counters는 모두0이다. 근거는 public tracked-file read 경로, 네 신규 파일 allowlist, unchanged source/V1 hash checks 및 private SSD가 숨겨진 namespace의 synthetic regression이다. 공개 문서 작성은 original source write와 구분한다. OS sandbox를 새로 구현했다고 주장하지 않는다.

## 검증 기록

- 신규 synthetic tests:51 PASS. 초기 계약 파일 미작성 시 fail 확인 후 두 JSON을 작성하고 green을 확인했다.
- 관련 집중 회귀415 PASS(신규51 포함), full AutoTune/controls5581 PASS /595.50s, lateral synthetic16 PASS. Full regression은 private SSD mounts를 가린 isolated namespace에서 실행했다. 공개 경로 검사 literal 정리 후 최종 focused51 PASS를 다시 확인했다. Full5581 실행 후의 변경은 이 privacy 검사와 본 검증 기록뿐이며 scientific source/JSON은 바뀌지 않았다.
- Ruff·compileall·SCons PASS. 공개 JSON824 parse PASS, 신규 두 canonical receipt와 상호 raw-hash binding PASS, 기존 source50/public17 pin PASS, original execution HEAD의 mathematical source6개 byte identity PASS. Publication/privacy는 최종 네 파일 allowlist에서 files=4 / findings=0 PASS다. Authority actual-private counters23개 int0, staged additive4개만 허용하고 original tracked files 변경0 및 diff check를 확인한다.
- 독립 Review A scientific/numerical은 계약과 synthetic51개에 blocker 없이 APPROVED했다. Review B authority/privacy도 실질 blocker0을 확인했다. 검증 기록과 privacy-test literal을 정리한 최종 네 파일의 exact-byte 승인 receipts는 두 reviewer가 별도로 제공하며 최종 handoff에 결부한다. 이 기록은 private 관측 재인증이나 미래 실행 승인이 아니다.
- 최종 HEAD/CI와 두 reviewer의 exact-byte receipt는 최종 handoff에 기록한다. 보고서 자신의 hash는 자기참조를 피하기 위해 Git commit 및 외부 review transcript에 결부한다.

## 재개 조건과 중지

다음 단일 승인 대상은 **V2 additive runner 구현·pre-execution 검증과 Q1/Q3를 포함한 두 fresh E2 실행**이다. 정확한 V2 protocol/amendment raw+canonical receipts, 새 caller raw hashes, 두 독립 최종 byte review, pre-execution CI SUCCESS, 기존 exact private source/member/model/anchor binding, 별도0700/0600 exclusive output 및 capacity/reserve를 새 execution binding에 결부해야 한다. 과거 V1 grant나 이 계약 작성 승인은 실제 V2 접근 권한이 아니다.

현재 기존 V1 failure는 보존되고 D2는 `PERFORMANCE_NOT_EVALUATED`다. `selected_candidate=null`, `selected_policy=null`, historical TRAIN gate=`NOT_SAVED`, original whole-replica=`REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`를 유지한다. HOLDOUT은 CLOSED, vehicle authority는 NONE, activation은 BLOCKED다. Pooled refit·composition·V5는 미승인, Hugging Face는 NOT_REQUIRED / NOT_USED다. Source-grid tick은 실제 EPS 움직임 자체가 아니며 logged command는 post-CarController normalized command다. SteeringRateDeg는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다.

실제 runner 수정, 비공개 재접근, D2 decision 계산, DEV·rollout을 수행하지 않고 계약 publication과 최종 CI 확인 후 STOP한다.
