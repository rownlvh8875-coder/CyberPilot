# Empirical Stage A causal context recovery

## Identity and purpose

- Area: Cyber Validation / AutoTune; cache-only retrospective diagnostic.
- Status: implemented; exact mapping and two-run repeatability verified.
- Baseline: feature/cyber-autotune at
  608fbd3d091a6ae0dca292152dd1bfb87e6b1ac5. Delivery commit is the commit
  containing this additive record and the seven versioned evidence artifacts.
- Purpose: recover prior command/measurement/context that the selected V3
  derivatives did not retain, then audit six predeclared single conditions.
- Vehicle scope: source-audited legacy torque-control Santa Fe empirical profile.
  No raw log opening, fitting, coefficient/config change, threshold search,
  sequential selector, holdout opening, Stage B, TA/SG or vehicle operation.

## Original references

- Input evidence: immutable V2 train/development generation, V3 retrospective
  route CV and Stage A error-regime attribution. Their public pins are checked
  through the existing publication modules and remain unchanged.
- Recorded origin: https://github.com/ajouatom/openpilot, exact commit
  18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29. Branch and remote evidence remain in
  the pinned source-semantics audit; source audit was not regenerated.
- Source measurement: opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc,
  SAS11.SAS_Angle, signed little-endian 16-bit, factor 0.1, offset 0, unit Deg.
  Exact DBC SHA:
  1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a.
  CarState direct copy and Float32 schema identities are bound by the existing
  source quantization receipt. License SHA:
  716ce815a0467219c59ec2433e6bce7f32efc45240725c6d3141a52b111d2558.
- Traced path: sealed V2 aligned cache -> same segment-local valid same-bin
  runs -> HISTORY45 design -> frozen selected ARX1/delay5 derivatives ->
  private origins and prior context -> independent branch metrics.
- Reuse: existing policy, metrics, receipt verification and atomic no-overwrite
  persistence. The V3 raw-file rehashing cache loader is deliberately not called.
  NumPy 2.5.3 / Python 3.12.13, one BLAS thread, no solver and no RNG.
  Existing submodules, models, runtime interfaces and licenses are unchanged.

## Changes and expected effect

- Added empirical_causal_policy.py, empirical_causal_recovery.py,
  empirical_causal_analysis.py and empirical_causal_publication.py, four test
  modules, seven aggregate JSON artifacts and a scoped implementation plan.
- No upstream integration point. Inputs and output are separate private stores
  outside the repository, with overlap/symlink rejection and immutable writes.
- Recovery policy SHA:
  1f1f286f42371935d24081302a2214ec2389df0e1a92fe2b1d089a8ec6ac2ad8.
  This policy was persisted before the successful execution deserialized aligned
  numeric cache values or selected arrays.
- An initial executor contract omitted the existing intercept=true field and
  stopped at the selected-fold config identity check before derivative analysis.
  Failed policy 2dba14f9a31115126153c6106e4ff67c46bc5324eceed24cf4661aafceac245c
  and its failed execution were retained separately. The corrected policy binds
  the complete existing selected config and the failure receipt. No condition,
  metric, threshold, source config or coefficient changed after observing results.
- Constants: HISTORY45, ARX1 delay5, 100 Hz grid, maximum publish age20ms,
  source-bound raw rail409, source half quantum0.05 degrees and minimum branch
  support201. These come from the frozen input contracts or this request.
- State/reset: each segment and each valid same-speed-bin run owns its history.
  No history crosses a segment, route, mask or speed-bin boundary. Private
  origins retain segment receipt, run and aligned row identities.
- Raw-source integrity is the prior V3 source-hash attestation plus exact cached
  opening/route/segment receipts and byte-identical cache trees. Current raw
  source-file freshness was not rechecked because raw paths are forbidden.
- Safety boundaries: no controller, CAN, Params, CarController, device, safety
  configuration or production path changed. Maintenance is limited to this
  separate offline evidence consumer.

### Previous limitation and available fields

Previous attribution could evaluate model-derived condition F, but selected
derivatives lacked command/angle history, aligned origins and intervention
context. That historical MIXED_OR_UNRESOLVED result is unchanged.

The V2 cache preserves raw command, measured angle, speed, reasons and
state/command/control/grid publish timestamps. Recovery restores u[k-1], u[k-2],
u[k-5], u[k-6], y[k-1], y[k-2], prior speed, normalized prior commands, rail and
run/segment boundary identities. Active/no-override context is inferred only
from the preserved reasons in the selected valid runs. Intervention transients
are outside that support. Unknown safety/curvature limits remain null.

Actual steeringRateDeg samples were not retained: only finite coverage counts
exist. Steering-rate zero/nonzero remains UNAVAILABLE_NOT_PRESERVED.

### Exact origin proof and causal time

For every segment, reconstruct the original valid same-bin runs and k=44..end
design rows in the original manifest order. Match float64 dtype, shape, C-order
bytes and row ordering for target, previous measurement, design and selected
prediction, recomputing only the frozen-coefficient dot product for identity
proof. This is not a refit or a new model evaluation.

All 449,426 rows matched exactly:

| Development route (opaque prefix) | Fold | LOW | MEDIUM | HIGH |
| --- | --- | ---: | ---: | ---: |
| 962f2448… | FOLD_A | 85,107 | 79,278 | 29,975 |
| 7ae11bd9… | FOLD_B | 27,217 | 146,878 | 80,971 |

Full IDs are read from the pinned V2 split, never hard-coded from these prefixes.
For each prior row used by a condition, command/control time <= prior state time
<= prior grid time, source age <=20ms, and prior state time < target state time.
Run grids are 10ms and measured publish times increase strictly. Publish-time
causality is verified; sensor acquisition timing remains unverified.

No y[k], current ambiguous u[k], target change label, residual, win/loss or
future event participates in condition assignment. Raw/normalized command change
is an exact injective Float32(raw/409) alias on the observed integer domain and
is counted once.

### Conditions and branch support

C1: latest prior command changed; C2: delayed model input changed; C3: latest
prior nonzero command reversal; C4: past measured angle changed; C5: prior raw
command at rail; C6: existing ARX predicted movement >=0.05 degrees. C6 is
model-derived and distinct from source measurement conditions. No combinations
or route/speed-specific thresholds were tested.

Each cell is TRUE / FALSE support; minimum201 applies to both branches of
every route/bin scope.

| Fold / bin | C1 | C2 | C3 | C4 | C5 | C6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A LOW | 50,948 / 34,159 | 50,908 / 34,199 | 405 / 84,702 | 14,803 / 70,304 | 11 / 85,096 | 18,424 / 66,683 |
| B LOW | 18,615 / 8,602 | 18,597 / 8,620 | 204 / 27,013 | 6,084 / 21,133 | 0 / 27,217 | 4,785 / 22,432 |
| A MEDIUM | 46,324 / 32,954 | 46,317 / 32,961 | 757 / 78,521 | 9,389 / 69,889 | 0 / 79,278 | 3,393 / 75,885 |
| B MEDIUM | 89,971 / 56,907 | 89,983 / 56,895 | 1,523 / 145,355 | 22,809 / 124,069 | 0 / 146,878 | 1,500 / 145,378 |
| A HIGH | 16,573 / 13,402 | 16,575 / 13,400 | 465 / 29,510 | 3,316 / 26,659 | 0 / 29,975 | 0 / 29,975 |
| B HIGH | 47,727 / 33,244 | 47,694 / 33,277 | 1,112 / 79,859 | 8,702 / 72,269 | 0 / 80,971 | 0 / 80,971 |

### Strict separator outcome

True must favor ARX on RMSE strictly and MAE/p95 non-strictly; false must favor
hold-last on all three non-strictly. All six scopes must pass with shared support.

| Condition | Passing scopes | Interpretation |
| --- | ---: | --- |
| C1 | 0/6 | ARX true-branch RMSE lower but MAE higher in all six scopes |
| C2 | 0/6 | Same directional tradeoff; no strict separator |
| C3 | 0/6 | Reversal support sufficient, ARX true-branch MAE higher throughout |
| C4 | 1/6 | Only FOLD_A LOW passes both branches; route/speed partial |
| C5 | 0/6 | Rail true branch has only11 samples in one scope and0 elsewhere |
| C6 | 0/6 | HIGH true branches empty; remaining scopes fail directional gate |

C4 true branches favor ARX on all three metrics in both LOW scopes, but FOLD_B
LOW false-branch p95 favors ARX rather than hold-last. MEDIUM/HIGH true-branch
MAE still favors hold-last. Thus a target-independent dynamic indicator does
not establish a globally consistent selector.

Full same-support RMSE/MAE/median/p95/bias/correlation, win/tie/loss,
absolute/squared contributions, fractions and coverage are published per
route/fold/bin in empirical-stage-a-causal-condition-results-v1.json.
Equal-route metric means per speed are primary; averaged route p95 values are
explicitly not pooled quantiles. Constant-signal correlation is null, not zero.

Final: CAUSAL_CONTEXT_RECOVERED_PARTIAL.
No predeclared condition passes globally. Branch insufficiency and the C4
partial result prevent exhaustive track closure. No selector counterfactual or
V4 contract was generated. This neither admits a model nor rejects all possible
actuator models or hybrid architectures.

### Future extraction contract

EMPIRICAL_CAUSAL_CONTEXT_SCHEMA_V1 defines private per-design-row origins,
command/angle history, normalized command, speed, reasons, source clock ordering,
rail/intervention context and source/profile/policy identity. Actual steering
rate requires an explicitly authorized future reader extension.
FUTURE_GENERATIONS_ONLY: historical V2/V3 evidence is not regenerated.

## Regression risk and acceptance

- Risks: wrong row order, lost mask/segment boundary, timing leakage, stale cache,
  schema drift, privacy leakage and over-interpreting partial branch evidence.
- Acceptance: exact origin/prediction bytes, immutable input trees, deterministic
  two-run results, six conditions only and strict source-bound criteria above.
  No new performance epsilon, percentage threshold or tuned boundary.
- Coverage: two previously analyzed routes, three existing speed bins, frozen
  selected ARX1/delay5 only. No independent validation and no new route use.
- Rollback: remove this additive consumer and evidence; all historical artifacts
  and native controller behavior are untouched.
- Independent reviewer checks code and public evidence only; promotion authority
  remains the user. Composition and vehicle operation remain unauthorized.

## Validation method and actual results

Ubuntu24.04 WSL, pinned Python3.12.13/NumPy2.5.3 and one BLAS thread.
Persistent private logs bind the commands, counts, identities and exit codes.

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Focused new tests | unittest four test_empirical_causal_* modules | New consumer and negative controls | 102 PASS |
| Full empirical regression | unittest discover test_empirical*.py | Historical pins and additive evidence | 693 PASS |
| Full AutoTune | tools/test_runner.py openpilot/tools/cyber_autotune/tests -j1 | Same checkout and complete suite | 3062 PASS |
| Controls | tools/test_runner.py openpilot/selfdrive/controls/tests -j1 | Native baseline regression | 142 PASS |
| Replay vs baseline | Two explicit cyber lateral replay unittest modules | Existing references unchanged | 16 PASS |
| Static/build/publication | Ruff, compileall, SCons, check_publication, git diff --check | Additive files only | PASS; publication1094 files /0 findings |
| Independent review | Separate reviewer, code/public evidence/document | No private cache access | PASS; two defects corrected before successful freeze, regressions added |
| Cache execution | Two full passes under forced raw-decoder/path exceptions | Result a5ad3f0cb7f9eb8657fe9b47390b328e543b0e9856526d9e2779f277ca762d06 | Exact repeatability PASS; all input trees unchanged |
| Simulation / closed loop | Not applicable: no new model/controller execution | Sequential selector and Stage C forbidden | NOT_RUN |
| Shadow | Not applicable: no vehicle/candidate authority | Offline private cache consumer only | NOT_RUN |

Input tree identities before and after both passes are identical:
V2 1269f43d7e2c542d7a9c069caad8d9616b495617b38e05de877751f67318cf78;
V3 513b75f722bcab24364cbc715b3b77e1d1535e552f83aa1c6002d8fde03570a4;
attribution b2eb8690096893580c20cdd600f039ab9f41e2180e9536de6f48f74eff052fc3.

## Handoff

- Verified: exact origin and prior context recovered for all selected rows;
  steering-rate unavailable; no globally admitted single-condition separator.
- Future package remains CLOSED_MISSING_ADMISSIBLE_MODEL,
  NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, HOLDOUT_OPENING_CLOSED and
  FUTURE_UNTOUCHED_HOLDOUT_REQUIRED. No new route opening is authorized.
- Historical V3 STAGE_A_CV_TRADEOFF_ONLY and previous
  STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED remain immutable. Stage B remains
  STAGE_B_SIGNAL_ADMISSION_BLOCKED.
- TA-B TA_STANDALONE_TRADEOFF_ONLY; SG-A SG_CLOSED_LOOP_TRADEOFF_ONLY;
  CURRENT BASELINE_EXACT, V1 TRADEOFF_ONLY, V2 REJECTED. Composition remains
  NOT_RECOMMENDED / NOT_AUTHORIZED; search and frozen candidate evaluation
  remain unauthorized.
- Calibration uncertainty, independent calibration validation and pixel geometry
  registration remain pending; metric calibration and independent reference
  remain unavailable. Sealed reference NOT_GENERATED. Vehicle NOT_READY /
  REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
- Next work requires separate authorization and a frozen new development policy.
  This diagnostic grants no V4 implementation, fitting, rollout or holdout
  authority. Commit/push and exact-head CI are verified at delivery.
