# V4 two-context exact fitting feasibility and causal state review

V4의 가장 작은 후보는 직전에 관측된 source-grid 조향 tick이 변했는지에 따라 두 개의 threshold를 사용하는 방식이다. 하지만 threshold가 두 개가 되면 후보 조합이 매우 커진다. 이번 작업은 실제 주행데이터에서 성능을 시험하는 것이 아니라, 조합을 대충 샘플링하지 않고 정확한 최적해를 증명할 수 있는 계산 방법을 확인한다.

첫 순간에는 관측된 과거 tick 변화만 사용하고, 이후 시뮬레이션에서는 projection이 끝난 예측 tick 변화만 상태로 사용한다. MOVE gate가 열렸더라도 반올림 후 tick이 같다면 다음 상태는 STATIC이다.

결론은 **인과 상태 계약은 성립하지만, joint two-threshold fitting의 실용적 계산량 보장은 아직 성립하지 않았다**는 것이다. 구현한 인증 탐색기는 완료하면 정확한 답을 반환한다. 그러나 최악에는 모든 threshold 쌍을 확인해야 한다. 따라서 Option A의 알고리즘 자격과 V4 architecture 선택은 계속 미확정이다. 실제 V4 성능은 측정하지 않았다.

## Scope and work plan

Baseline: `ae8c2b9e7d602c655d352abeb4983b10ab4c320b`. Startup fetched origin, verified ancestry, clean local/origin equality and exact-HEAD Actions success (run `38538745247`). Existing evidence and V1/V2/V3 code are immutable inputs.

The authorized sequence was: lock seven public review artifacts; trace anchor/history construction; implement synthetic canonical metrics and causal state witnesses; certify a policy-neutral rectangle search against the exhaustive oracle; examine six algorithm families and counterexamples; run deterministic medium/large synthetic checks; obtain two independent read-only reviews; run full validation and publish additive evidence.

Private numeric array opens, raw/qlog/HOLDOUT openings, prediction replay, actual model fitting, actual threshold search, actual rollout and actual candidate selection are all **0** in this increment. Synthetic functions accept explicit synthetic roles and have no filesystem/private source or execution authorization API. These tags are interface containment, not a mechanism that can authenticate the provenance of arbitrary arrays supplied by a caller. No existing private executor is integrated or changed.

## Why this question remains

V1, V2 and V3 used the same fixed scalar Stage1 score and single global cutoff. V2 reduced STATIC/exact-hit loss by suppressing almost all MOVE. V3 restored TRAIN TP coverage but worsened DEVELOPMENT exact-hit in all 31 comparable jobs. All three remained NO_ADMISSIBLE.

`GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED` remains an **EMPIRICAL_PROJECT_POLICY_CLOSURE**, under current data, fixed score, Hurdle composition and frozen final gate. It is not proof that every threshold, objective or model must fail.

Existing public temporal evidence shows approximately 55% MOVE onset and 45% continuation, with approximately 64% of MOVE fragments lasting one step. Conditional DEVELOPMENT ranking is above chance but weak. Persistence motivates examining a causal context; it does not establish hysteresis performance or solve the onset problem.

## Causal state proof

For the decision from tick[k] to tick[k+1]:

```
delta_prev[k] = int64(tick[k]) - int64(tick[k-1])
z[k] = int(delta_prev[k] != 0)
gate[k] = score[k] > theta[z[k]]
```

The bit has no sign or magnitude. It describes a source-grid tick change, not physical EPS movement, `steeringRateDeg`, or physical steering rate. Command semantics remain logged post-CarController normalized command, not measured physical applied EPS torque. No new rate/sensor dependency is added.

The static trace, file SHA locks and required-history table are in [causal state contract](empirical-hurdle-stage1-v4-causal-state-contract.json). Hurdle delegates anchors/features to S2-RI. Required eligible history is `R=max(d+L,L+1)`. For every L=1/5/15/45 and d=0/5/10/20, R>=2; therefore an admitted anchor k has k-1. For every H in {1,25,50,100,200}, anchors also require `streak[k+H]=streak[k]+H`, excluding continuity breaks throughout the horizon. L=1 requires two ticks rather than zero padding. The feature layout already contains the signed increment ending at k. The data loader validates streak continuity per segment using eligibility, 10ms grid adjacency, causal run identity and within-index adjacency. Anchors are constructed per segment before concatenation.

| L | d=0 R | d=5 R | d=10 R | d=20 R |
|---|---:|---:|---:|---:|
| 1 | 2 | 6 | 11 | 21 |
| 5 | 6 | 10 | 15 | 25 |
| 15 | 16 | 20 | 25 | 35 |
| 45 | 46 | 50 | 55 | 65 |

This proves construction invariants, not actual private array availability or context-specific fitting support. Array primitives rely on admitted provenance/streaks; they do not authenticate source files. The predecessor is the contiguous source-grid predecessor, not the previous stored row after anchor filtering. No anchors are added, dropped or reordered.

One-step TRAIN and DEVELOPMENT use already-observed tick[k-1], tick[k]. Target tick[k+1] is scoring only. Missing predecessor, nonfinite/out-of-range tick or broken route/segment/run/eligibility/grid continuity fails `OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT`; there is no silent STATIC/MOVE initialization.

## Recursive context

Existing rollout construction supplies L+1 initial observed ticks, including tick[-1] and tick[0], even for L=1. Existing recursive code initializes `past=np.diff(initial_ticks)` and updates the latest increment using projected `new-current`.

```
z[0] = int(observed_tick[0] - observed_tick[-1] != 0)
z[h] = int(projected_tick[h] - projected_tick[h-1] != 0), h>=1
```

Future measured steering ticks, deltas and MOVE labels never update the bit. Existing logged command/vEgo exogenous replay remains permitted under its frozen contract. A MOVE branch with delta=0.5 at tick=0 rounds half-even to tick=0, giving next z=0. The predicted gate itself never becomes movement state.

The synthetic state witness invalidates on caller-signaled route, segment, causal-run, eligibility or grid boundary and requires fresh observed initialization. It is not an automatic boundary detector or an implementation change in existing rollout. Tests cover observed MOVE/STATIC initialization, held projections, alternating movement, repeated stationarity, forbidden measured feedback, malformed frame metadata, missing/nonfinite ticks and all boundary types.

## Canonical finite domain and policy separation

For each context z, `Tz=sorted_unique({0,1} union finite scores in Cz)`. Empty contexts retain the two endpoints. Decisions use strict `score>threshold`; equality is STATIC. There is no epsilon, nextafter expansion, default0.5 or fallback.

The oracle evaluates every pair in T0×T1. It builds integrated continuous deltas in original row order, applies frozen direct binary64 addition and half-even signed16 projection, then computes ALL and TRUE MOVE RMSE/MAE/p95. Exact-hit, within-one and projected STATIC false-move counts use integer projected ticks. Confusion and gate counts are Python integers, globally and per context. Empty TRUE MOVE metrics are undefined, not replaced with zero.

The four layers are separate:

1. `PAIR_METRIC_EVALUATOR`
2. externally declared feasibility predicates
3. externally declared lexicographic objective
4. externally declared total parameter tie key

The implemented interface supports whitelisted count/metric comparisons and signed metric keys. Other policies require a separately reviewed extension; arbitrary callbacks cannot assert that a float objective is an additive count. Two external axis tie orders, STATIC_FIRST and MOVE_FIRST, produce different legitimate winners in a tied synthetic fixture. Neither is adopted as V4 policy. V4 feasibility, objective, TP floor, support minimum and pair tie order remain **UNFROZEN**. Every benchmark has `FEASIBILITY_BENCHMARK_ONLY_NO_V4_POLICY_AUTHORITY`.

## Why context subtotals and quantiles are insufficient

For binary64 `[1,2^-53,2^-53]` in original order, NumPy sum is 1.0. Summing context0 `[1]` and context1 `[2^-53,2^-53]` separately then adding gives 1.0000000000000002. Mathematically additive real SSE/SAE do not authorize changing canonical reduction order. The concrete MAE witness is also tested.

Context p95 values cannot identify pooled p95. Synthetic distributions `[0,20]` and `[10,10]` have the same context p95s as `[19,19]` and `[0,200/19]`, but the pooled p95s differ. Exact ordered values and NumPy-compatible interpolation are necessary. Even algebraically equivalent interpolation formulas can round differently in binary64.

The implemented solution preserves exactness by calling the pinned NumPy reduction and pooled `percentile(abs(error),95,method='linear')` on canonical full arrays at every evaluated leaf. It does not use float bounds, approximate quantiles, context p95 substitution or context float subtotals for pruning.

## Certified rectangle algorithm

The search partitions index rectangles into two disjoint children. Stable equal-score transitions precompute all eight exact integer count contributions for each context threshold. Range-maximum trees bound signed primary count objectives.

Two pruning rules are implemented:

- Every pair is infeasible when a declared `TP>=integer_floor` clause has rectangle TP upper bound below that floor.
- A rectangle cannot beat a canonical feasible incumbent when its exact integer primary objective upper bound is **strictly** below the incumbent primary value.

Primary equality never prunes: later objective terms and the external total tie key may change the winner. Float primary objectives receive no objective pruning. No objective prune occurs before a feasible incumbent exists.

The certificate records rectangle partitions, canonical leaf metrics, exact bounds, incumbent references and policy hash. Verification reconstructs the domain, rejects cycles/shared/unreachable nodes, checks every split partitions its expected rectangle, recomputes every visited leaf and bound, and validates result scope/schema/types. A mere sum of rectangle areas is insufficient. The full tree provides disjoint, gap-free coverage. Objective-pruned domains may contain feasible pairs, so total feasible-pair count is reported unknown in that case.

If node budget ends before certification, status is `V4_TWO_CONTEXT_FITTING_INCONCLUSIVE_RESOURCE_BOUND`. Selected pair, selected metrics, selected key and total feasible count are null. The proof retains pending domain records for audit, but publishes no partial winner or false NO_FEASIBLE result.

## Algorithm families and limits

| Family | What it establishes | Remaining limitation |
|---|---|---|
| Certified rectangle B&B | Exact winner/no-feasible on complete coverage | Cartesian worst case |
| Pareto/dominance index | Additive integer dominance with sufficient statistics | Full frontier can contain all pairs; local p95/float sums insufficient |
| Persistent order statistics | Exact pooled order-statistic queries for context versions | Does not itself optimize all pairs or preserve SAE/SSE reduction |
| Original-order reduction tree | A specified arithmetic DAG can be maintained | A generic tree is not proven equivalent to NumPy's pinned kernel |
| Offline multidimensional dominance | Certain fixed-dimensional additive policies | No general reduction for pooled percentile/canonical floats established |
| Independent separable context fitting | Exact bounded additive integer benchmark | New fitting policy; not joint pooled feasibility |

Let P=T0*T1, L be evaluated canonical leaves and V be visited rectangles. Preprocessing costs O(NlogN+T0+T1). Search costs O(LN+Vlog(T0+T1)); the numeric workspace is O(N+T0+T1), and retained certificate memory adds O(V). Worst case is O(NlogN+T0+T1+NP) time and O(N+T0+T1+P) total memory. The constant-primary adversary tests all P leaves even when pruning is enabled.

Public historical TRAIN counts give `Tz<=Nz+2` and, without opening context arrays, pair upper bound `(floor(N/2)+2)*(ceil(N/2)+2)`. Across 32 public jobs these upper bounds range from 8,437,800,306 to 28,382,983,256 pairs; their sum is 514,877,326,458. They are conservative cardinality bounds, not actual unique-score counts.

## Synthetic certification and scale check

Small fixtures cover endpoints/equality/ties, empty and rare contexts, positive/negative and multi-tick deltas, held projections, interleaved/grouped row order, opposite cutoffs, TP boundaries, empty feasible sets, signed zero, adjacent binary64 values, p95 interpolation/repetition, unsafe schema mutation and exhaustive parity. A medium fixture has 78 rows and 40×40=1,600 pairs: full-oracle winner/metrics/key parity and coverage verification pass. Twelve canonical leaves and ten pruned rectangles certify this benchmark. A separate constant-primary fixture evaluates all 56 pairs, showing worst-case behavior.

Large local synthetic check: 200,003 rows, 64×64=4,096 pairs, node budget32. It visits32 rectangles and12 leaves, prunes0, retains41 certificate records and leaves4,084 pairs unresolved. Search-only tracemalloc peak was14,183,774 bytes, excluding initial population allocation; elapsed time was approximately6.12 seconds. This is a descriptive memory/exhaustion check, not a speed gate or practically-bounded proof. No large Cartesian oracle or historical numerical data was used. Publication validates the exact aggregate schema and source/input/policy identities, reconstructs the deterministic certificate and independently verifies it; an arbitrary report cannot supply a trusted PASS or extra private fields.

## Separable alternative

An unconstrained additive-integer lexicographic benchmark separates exactly into two 1D maximizations, O(NlogN+T0+T1). The implementation verifies that narrow result against the joint oracle. It does not inherit global task feasibility.

A counterexample makes the difference explicit: context0 has actual deltas1 and branch deltas5, context1 has actual deltas10 and branch deltas10. Opening MOVE worsens context0 RMSE from1 to4, while improving context1 from10 to0. Pooled constraints can permit the pair although a context-local strict RMSE-improvement policy has no feasible context0 threshold. Local policy changes discard cross-context tradeoffs and pooled distribution information.

Result: `SEPARABLE_TWO_CONTEXT_FITTING_ALGORITHMICALLY_FEASIBLE_POLICY_UNFROZEN`. No local BA, V2 objective or TP floor is adopted.

## Independent reviews and validation

Two independent read-only reviews cover algorithm/numerical proof and causality/authority. The numerical review identified certificate authority relabeling and bool/int alias acceptance; strict schema/scope and canonical type-sensitive comparisons now reject them. The causal review requested malformed metadata and missing/nonfinite tick guards; these are implemented and tested. A stale source line citation was corrected to projected history update line284. Pareto output-size lower bounds are distinguished from a generic algorithmic upper bound.

Final local validation: **4,832 full AutoTune/controls tests PASS**; **1,973 combined empirical PASS**; **45 new focused PASS**; **160 prior V3/V4 focused PASS**; **16 lateral replay PASS**. Ruff, compileall, all679 policy/evidence JSON files, publication/privacy/authority audit, staged `git diff --check` and SCons all pass. Both independent reviews approve the corrected result. No historical tracked file is modified.

Commands: `tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j4`; pytest on `test_empirical*.py`, the new two-context test, and prior `test_empirical_hurdle_v3*.py` plus `test_empirical_hurdle_v4_review.py`; the two existing Cyber lateral replay unittest modules; the existing branch Ruff, compileall, publication and SCons targets. Python3.12.13/NumPy2.5.3, single BLAS thread. Legacy D-only synthetic fixture tests use a private user/mount namespace with an empty D mount, avoiding Windows D-to-E junction aliases without changing global mounts, historical guards or test assertions. Repository/temp storage remains E-backed WSL; no actual D/E private data is opened.

## Result and next step

- `STAGE1_V4_TWO_CONTEXT_FEASIBILITY_REVIEW_COMPLETE`
- `V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED`
- `V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE`
- `OPTION_A_ALGORITHMIC_ELIGIBILITY_NOT_ESTABLISHED`
- `OPTION_A_CURRENT_EXACT_FITTING_BLOCKER_REMAINS`

This is not an impossibility claim. A stronger exact optimizer may still be proved for a subsequently frozen policy. The next authorized design question is whether to define a separable policy with explicit changed scientific semantics or review another bounded architecture. Neither decision is made here. No Option A architecture, V4 fitting policy, nonlinear model or model artifact lifecycle is frozen or started. Hugging Face is **NOT_NEEDED**.

V4 fitting/DEVELOPMENT/rollout/performance/selection remain **NOT_RUN**. Historical S2-RI and Hurdle V1/V2/V3 NO_ADMISSIBLE and MODEL_SELECTION_FAILED_CLOSED records remain immutable; Stage2 long-horizon residual risk remains. No future-HOLDOUT model is admitted. Pooled refit remains unauthorized. HOLDOUT remains CLOSED, opening/discovery0. Vehicle authority remains NONE, NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
