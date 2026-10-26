# V4 two-context fitting policy decision review

두 threshold 방식은 인과적으로 사용할 수 있지만, 기존 pooled 평가를 그대로 유지하면서 정확하게 최적화하려면 최악의 경우 너무 많은 조합을 확인해야 한다.

context별 목적·제약으로 따로 threshold를 고르면 계산이 쉬워질 수 있지만, 이것은 단순한 최적화 기법이 아니라 학습정책 자체를 바꾸는 것이다. 반대로 같은 additive global 목적을 정확히 분리 계산하는 경우에는 정책이 유지될 수 있다. 이번 검토는 계산이 쉬운 쪽을 무조건 택하지 않고, 그 정책이 지금 관측된 실패에 대응할 근거가 있는지 확인한다.

결론은 **OUTCOME C: V4_TWO_CONTEXT_POLICY_DECISION_INCONCLUSIVE**이다. Context-local balanced accuracy처럼 근거가 있는 분류 surrogate는 존재한다. 그러나 그 목적을 CyberPilot의 integrated TRAIN 목표보다 우선해도 되는지, 두 context 사이의 보상을 버려도 되는지는 현재 evidence만으로 정해지지 않는다. 이 미확정을 반증으로 바꿔 two-context track 전체를 닫는 것도 정당화되지 않는다.

따라서 separable policy를 채택하거나 동결하지 않았고, two-context track도 종료하지 않았다. 새 Stage1 representation을 검토할 신호는 성립하지만, 이것은 track 종료나 새 모델 선택과 다른 판정이다. 실제 V4 fitting·DEVELOPMENT·rollout·성능·selection은 모두 NOT_RUN이다.

## Decision record and authorized plan

Baseline `cfea011d68f28a5c907a3cef17a76e1fa29bf58a`; branch `feature/cyber-autotune`. Startup fetched origin, checked baseline ancestry, local/origin equality and clean index/tree, and verified exact-HEAD CI success (run `38552151833`). Existing evidence, numerical models, executors and contracts remain immutable.

The work plan was: lock the requested public artifacts and relevant existing conditional score aggregates; define joint/separable semantics; construct mathematical counterexamples without fitting or threshold search; review five local objective families and route-transfer relevance; apply the supplied scientific-first decision rule; obtain independent research and authority reviews; validate and publish additive records.

All input access is to public receipts/static code. Sixteen exact file/receipt hashes are in [input lock](empirical-hurdle-stage1-v4-policy-decision-inputs.json), including singleton audit, both review validations and the existing V3 onset/continuation aggregate ranking receipt. Reading a public report of a historical private audit does not repeat that audit. Current private numeric opens, raw/qlog/HOLDOUT opens, source writes, model/normalizer fits, prediction replay, actual threshold fitting, pair search, DEV, rollout and selection are all0. No Hugging Face operation occurred.

The new mathematics module has no filesystem, optimizer, model or rollout API. Its toy cutoffs are declared constants used to demonstrate decision properties, never selected from labels or used as a real-performance proxy. Schema tags identify the intended interface scope; they do not authenticate arbitrary caller-supplied arrays as synthetic.

## What historical evidence establishes

The fixed global threshold track remains `GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED`: an empirical project-priority closure under current data, fixed score, Hurdle composition and frozen gate. It is not a theorem that all thresholds, objectives or Stage1 models fail.

V1 had comparatively high MOVE coverage and poor STATIC/exact-hit behavior. V2 suppressed over95% of DEVELOPMENT MOVE in all32 jobs and improved exact-hit/rollout. V3 restored the immutable V1 TRAIN TP floor: missed MOVE improved in all31 comparable jobs, but projected exact-hit worsened in all31. V3 complete fold gates remained0/16 in both folds. S2-RI and Hurdle V1/V2/V3 all remain NO_ADMISSIBLE, selected candidate null and MODEL_SELECTION_FAILED_CLOSED.

These results expose an operating-point tradeoff. They do not identify a winning two-context objective, refute every classification surrogate, or prove an information-theoretic limit of the features.

## Joint pooled versus separable fitting

Joint fitting chooses one pair `(theta0,theta1)` using the entire original-order TRAIN population, global continuous metrics, pooled p95, projected hit counts, global TRUE MOVE metrics and counts. Cross-context compensation is permitted if global constraints allow it.

Separable fitting chooses theta0 using context0 and theta1 using context1. Context-local constraints disallow compensation during fitting. Runtime still uses the same two cutoffs, the same Stage1 score, same Stage2 and the established causal bit. Separable fitting does not imply separate runtime models.

The existing certified B&B is exact on complete domain certification but remains Cartesian in the worst case. Canonical leaf evaluation makes the worst-case time O(N*T0*T1), beyond threshold-pair counting alone. Public cardinality upper bounds are not actual unique-score counts. No practically bounded exact joint fitter has been established; none has been proved impossible.

Global pooled **final evaluation** remains mandatory: unchanged V1 32-clause gate per fold, both folds required, unchanged selection rule. It does not logically follow that the TRAIN fitting objective must itself equal that gate. A classification surrogate can be scientifically legitimate, provided its loss/alignment principle is justified and frozen before any performance run.

### An important separability qualification

Unconstrained additive integer objectives can separate exactly. With global positive/negative counts P,N>0:

```
pooled BA = (N*TP + P*TN)/(2*P*N)
TP = TP_0 + TP_1; TN = TN_0 + TN_1
```

With an uncoupled parameter domain, maximizing `N*TP_z+P*TN_z` independently preserves that pooled BA primary objective exactly. Context-local BA instead uses `TP_z/(2*P_z)+TN_z/(2*N_z)` and different class weights. Both have interpretable classification targets without a new numerical recall floor. Neither automatically preserves integrated continuous feasibility or pooled p95. Adding coupled constraints or global tie rules needs a separate equivalence proof. Undefined local class support cannot be silently imputed.

Consequently, not every separable policy discards every global objective, and independent context optimization is not automatically equal context weighting. No BA variant or tie rule is adopted here.

## Four mathematical witnesses

All examples in [compensation evidence](empirical-hurdle-stage1-v4-cross-context-compensation.json) are synthetic mathematical values, not driving rows or fitted policy outcomes.

1. **RMSE compensation:** reference errors `[1,1,10,10]`, candidate `[2,2,0,0]`, contexts `[0,0,1,1]`. Context0 RMSE worsens1→2 while context1 improves10→0. Global RMSE improves from sqrt(50.5) to sqrt(2). A strict context0 constraint rejects what pooled RMSE permits.
2. **Local p95 can pass while pooled fails:** candidate errors `[0,20]` in each context give local linear p95=19. References `[19,19]` give local p95=19 too. Both local comparisons pass, but pooled candidate p95=20 exceeds pooled reference19. This is finite linear-percentile behavior, not an approximate quantile.
3. **Support weighting:** two declared coupled alternatives have supports100 and1, exact-hit counts `(100,0)` versus `(98,1)`. Population counts prefer100 over99; equal-context rates prefer0.99 over0.5. This illustrates weighting among declared alternatives, not an alleged failure of unconstrained additive-count separability. With no coupled restrictions, independently maximizing additive counts preserves their sum.
4. **Float reduction:** reference errors `[1,2^-53,2^-53]`, candidate each value moved one binary64 step toward zero, contexts `[0,1,1]`. Both local MAEs strictly improve, but original-order global NumPy MAE is unchanged. Combining context subtotals reports a different change. No epsilon or threshold perturbation is introduced; nextafter is used only to construct error-value evidence.

These witnesses prove inequivalence/rounding limitations. They do not establish whether the scientific loss of compensation is acceptable, or predict which real policy would pass.

## Temporal relevance and route score transfer

Both routes show approximately9.25% MOVE after STATIC and44–45% after MOVE. Onset contributes54.67–55.53% of true MOVE; approximately64% of eligible observed MOVE fragments have length1. These are eligible observed fragments, not complete raw-route runs. The causal state therefore distinguishes label-frequency regimes. It does not establish a route transport mechanism.

Public transition denominators give previous-STATIC context supports288,588/336,941 and257,170/300,569, approximately85.56–85.65% of rows. Previous-MOVE supports are48,353 and43,399. This establishes the population imbalance without opening private counts. Equal-context weighting would be a distinct scientific weighting choice; independent maximization of an uncoupled additive objective does not itself impose such weighting.

Fold A TRAIN reference recall37.01–54.34% becomes V3 DEV recall57.16–65.60%; mean scores shift upward. Fold B reference16.36–23.64% becomes DEV7.40–12.08%; mean scores shift downward. Existing public conditional score aggregates additionally show the same shift direction within both previous-STATIC and previous-MOVE populations. Thus a simple change in the mixture of state frequencies does not describe away the observed conditional score shifts. These are descriptive aggregates, not a causal mediation analysis. Rank degradation and score mean shift coexist; calibration alone is not a proven cause.

Relevance verdict: `TEMPORAL_CONTEXT_PARTIALLY_RELEVANT_BUT_NOT_ROUTE_TRANSFER_EXPLANATION`.

A fixed pair of absolute TRAIN cutoffs has `NO_STRUCTURAL_CORRECTION` for a general monotonic route score shift. Synthetic binary fractions retain their ordering after a uniform up/down shift but cross the fixed context cutoffs. Co-transforming the cutoffs would restore decisions, but no such adaptation is present or authorized. Lack of invariance does not prove two contexts cannot improve transfer on a particular dataset.

## Onset and ranking limitation

Within a fixed state, `p_i<=p_j` and `p_i>theta_z` implies `p_j>theta_z`. Threshold choice cannot reorder the existing score. Binary gate output may coarsen distinctions into ties; this is not a claim that its binary AUC must equal the raw-score AUC.

`TWO_CONTEXT_FIXED_SCORE_CANNOT_IMPROVE_WITHIN_STATE_RANKING` therefore holds. Different cutoffs can still change decisions or ordering **between** states, so this is not a proof that Option A is useless.

Previous-STATIC DEVELOPMENT conditional AUC is0.5361146–0.5508682; previous-MOVE0.5378383–0.5949007. They are weak above-chance signals in the supplied review context, not validated good classifiers. Above0.5 describes the locked empirical rows; it is not a significance test or proof about randomness. No subjective AUC-quality cutoff is used. Most MOVE onset depends on the previous-STATIC branch, so continuation-only improvements do not automatically solve onset. Public receipts do not yet attribute all integrated failures to onset versus continuation or show that better ranking is the only remedy.

## Local objective families reviewed

| Family | Scientific basis | Remaining question |
|---|---|---|
| Context BA | Class recall/specificity balance; historical V1 classification target | Global vs local normalization; projected-task and long-horizon alignment |
| Context task exact-hit | Direct projected tick counts; historical V2 task target | STATIC dominance can remain; no all-metric guarantee |
| MOVE protection plus exact-hit | HOLD_LAST-referenced error protection | Local constraints are a new policy and may exclude pooled benefits; exact float/p95 proof required |
| Proper-loss-derived threshold | Proper losses assess probability quality | With fixed scores the loss has no threshold parameter; hard Brier becomes0/1 error, hard log loss may be infinite |
| Reference-constrained local policy | Could protect an immutable context reference | Global V1 TP references are not context references; no invented allocation/floor |

No numerical target, context objective, TP floor, prevalence target, cutoff default, weighting or tie rule is selected. The narrow additive benchmark's complexity cannot be transferred silently to every constrained local objective.

Stage1 classification quality and integrated Stage2 task quality are both legitimate targets. Historical failure of V1, V2 and V3 does not by itself settle which surrogate is appropriate. Keeping the final global gate prevents unauthorized admission; it does not decide whether a scientifically promising but cross-context-compensating TRAIN pair should be excluded from research.

## Decision rule and outcome

Priority order is scientific failure relevance, interpretability, no arbitrary new target, route-transfer relevance, exactness, then complexity. Speed cannot resolve an unknown scientific premise. Evidence is tri-state: true established, false refuted, null unknown.

For separable review support, an independently justified classification surrogate exists in principle; no new numeric target is necessary, the final gate can stay fixed, and route limitations are documented. Two requirements remain unknown: direct state-specific failure linkage, and acceptable sacrifice of integrated compensation. Review-only A does not require proven improvement. The missing principle concerns task alignment and acceptable compensation sacrifice, rather than the existence of a principled classification loss.

B needs an affirmative project-priority closure rationale. An unavailable practical joint bound plus an unresolved separable proposal does not refute the two-context family or automatically justify its closure. The evidence motivating causal context has not disappeared.

The exact selected outcome is therefore **C**, not A or B. Unknown acceptability is not NOT_ACCEPTABLE. No transport explanation is not proof of no possible transfer improvement. No final fitting objective or architecture is frozen.

All six predeclared representation-review conditions are satisfied: global threshold priority closed, joint practical fitting unresolved, no structural shift correction, fixed within-state ordering, majority onset, and the supplied weak-above-chance previous-STATIC ranking evidence. Accordingly the separate reasoning signal `NEW_STAGE1_REPRESENTATION_REVIEW_SUPPORTED` is true. It does **not** select B, close the two-context threshold track, choose a model or start a review automatically. The weak characterization is descriptive; no invented numeric AUC cutoff is embedded in the trigger.

## Next decision and authority

The next useful step is an explicit loss/alignment principle: whether a Stage1 classification surrogate may replace integrated TRAIN constraints, and which cross-context compensation sacrifices are acceptable. State-specific projected loss/MOVE gain attribution is a named evidence requirement, not assumed available and not gathered privately here. A future bounded representation architecture review is supported as a separate direction, with the smallest change capable of altering within-state ranking as its question. No interaction logistic, polynomial model, MLP or other classifier is ranked or selected in this increment.

Hugging Face setup/login/repo/upload/download remain untouched. The Outcome B registry trigger does not fire because B was not selected. If a later model-artifact stage is authorized, registry review and beginner step-by-step instructions will be required.

## Validation and independent review

The new focused suite covers all four counterexamples, exact BA decomposition, support weighting, monotonic shift sensitivity, within-state ordering, distinct state decisions at equal score, onset partition reasoning, A/B/C paths, UNKNOWN handling, representation-signal/closure separation and execution/private I/O traps. Final local results: **4,860 full AutoTune/controls PASS**, **2,001 combined empirical PASS**, **28 new focused PASS**, **205 prior V3/V4/two-context focused PASS**, **16 lateral replay PASS**. Ruff, compileall, all690 JSON files, publication/privacy/authority audit, `git diff --check` and SCons pass. Both independent read-only reviews approve after the documented prose corrections.

Commands: `tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j4`; pytest on `test_empirical*.py`, the new policy review test, and `test_empirical_hurdle_v3*.py` plus prior V4 review/two-context tests; the two existing Cyber lateral replay unittest modules; branch Ruff/compileall/publication/SCons targets. Python3.12.13, NumPy2.5.3, single BLAS thread. Full/legacy regression uses a private user/mount namespace with empty D tmpfs to isolate existing D-to-E junction aliases in synthetic fixtures, without changing global mounts, historical guards or assertions. Repository/temp storage is E-backed WSL; no actual private D/E data is opened.

Historical NO_ADMISSIBLE records, MODEL_SELECTION_FAILED_CLOSED, fixed-family project closure, V4 architecture INCONCLUSIVE, established causal state, Cartesian exact-fitting limitation and Stage2 long-horizon risk remain immutable. HOLDOUT remains CLOSED with opening/discovery0. No future-HOLDOUT model is admitted. Pooled refit is NOT_AUTHORIZED. Vehicle authority NONE; NOT_READY, REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED remain.
