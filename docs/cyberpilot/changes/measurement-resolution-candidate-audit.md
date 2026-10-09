# Measurement resolution aware candidate audit

This is a **CONDITIONAL / NON-QUALIFYING** comparison of existing descriptive plant displacement with the frozen declared-hypothesis meter diagnostic. It is **not a performance acceptance test** and does not measure real vehicle improvement.

## Frozen inputs and recovery

The meter aggregate remains 50982b711bd4348fd6fd2e9a0d70d46a8e2d2e464448b596f81c3dd2cdc59e41, with index 16741fe606e3613723cf4662667988f8c84a4fec9e5ca309bdc8f805c3777c7b, from 9a6ae36a6. Neither its values nor any detector, annotation, matching rule or candidate configuration changed.

Original full plant trajectories were no longer present in temporary storage. Public immutable archives contain 70 case summaries: 11 nominal evaluation, 36 development (nine configurations × four scenarios), and 23 stress cases. Recovery therefore re-executed only those exact archived cases, twice per arm. No search was executed.

Development native source HEAD: 67cbf2a642872f8ea6ecd534b4c1a3216cfbb18e. Nominal/stress source HEAD: 3da4306c118e6953e8bb6851b9385736743cf45d. Harness files are the original pre-commit snapshot later committed at 3667fa9c1. Historical controller/config/input/reset/environment/timebase/software/adapter/plant identities are checked before execution. Separate historical checkouts preserve import-root checks; initial setup attempts that resolved the primary checkout were rejected by those checks.

Filesystem request roots necessarily relocate. Fresh raw receipts retain their relocated root. A **comparison copy only**, never an execution input, restores original root metadata and original request hashes. Its complete result SHA and report receipt must reproduce the archived summary exactly. Numerical edits cannot satisfy this equality. All 70 cases passed, with eight native executions per case, 560 total. Persistent recovery receipts support exact cache validation. The prefrozen execution policy and recovered receipt set are bound. Historical source/result artifacts remain unchanged.

## Meaning and alignment

The quantity is **DESCRIPTIVE_PLANT_COUNTERFACTUAL_EFFECT**: candidate minus baseline/current lateral pose_y_m at the same world-forward pose_x_m. This plant is not a calibrated vehicle model or independent desired-path reference. Torque, steering and curvature alone are not converted into displacement.

At 5, 10, 15, 20, 25 and 30m, each arm independently interpolates its frozen world-forward trajectory within observed brackets only. There is no extrapolation, arc-length substitution or time-aligned shortcut. Nonfinite/nonmonotone traces and incompatible units/frame fail closed. Phase is the lower-bracket label; speed and curvature are interpolated diagnostic inputs. Phase transitions are flagged and do not establish a native held-frame label. CURRENT is the exact BASELINE alias.

Strict boundaries were frozen before recovery:

- Absolute effect below declared minimum p95: EFFECT_BELOW_DECLARED_ENVELOPE.
- Between minimum and maximum, including equality: EFFECT_OVERLAPS_DECLARED_ENVELOPE.
- Above declared maximum p95: EFFECT_EXCEEDS_DECLARED_ENVELOPE.
- Missing coverage/distance/repeatability/basis yields explicit unavailable classifications.

Effect divided by minimum/maximum p95 is a **DIAGNOSTIC_EFFECT_TO_ENVELOPE_RATIO**, not significance, confidence, probability or SNR. Signed displacement does not establish improvement. Mirrored signs are also reported with curvature-normalized signs; mixed directions describe a tradeoff, not desired-path correctness.

## Results and availability

All 198 nominal candidate/distance rows, distance/scenario classifications, speed/curvature/phase strata, development configurations and stress results are published separately. The development fourth arm is a historical family member, not a new selected V2.

Frozen reference coverage remains **44/55 both matched**, **11 center-unavailable frames**, 60 total. Fixed queries reuse 2,240 matched center residual samples under 78 declared scenarios; this is not empirical reference coverage at every query distance. Nominal observed-point support at 25m (10 points) and 30m (one point) is sparse.

Whole-run phase effects retain entry/apex/exit/reversal/re-engagement context beyond 5–30m without extrapolating the envelope. Original tracking/smoothness groups and all 37 V2 violations remain separate. Early-distance comparisons cannot erase later regressions.

Historical verdicts remain **V1 TRADEOFF_ONLY; V2 REJECTED**. Stress tradeoff results do not overturn nominal rejection. No acceptance threshold, weighted score or qualification verdict is introduced.

### Nominal distance summary

Maximum absolute displacement across available nominal scenarios, **cm**:

| Forward distance | V1 maximum | V2 maximum | Declared center p95 min–max | Available scenarios per candidate |
|---|---:|---:|---:|---:|
| 5m | 0.000041 | 0.000041 | 5.32–6.27 | 11/11 |
| 10m | 0.000389 | 0.000171 | 10.27–12.89 | 11/11 |
| 15m | 0.005657 | 0.002415 | 14.93–19.97 | 11/11 |
| 20m | 0.010879 | 0.004652 | 19.33–27.56 | 11/11 |
| 25m | 0.020074 | 0.006114 | 23.49–35.72 | 6/11 |
| 30m | 0.027558 | 0.014268 | 27.44–44.51 | 6/11 |

CURRENT minus BASELINE is exactly zero. All 168 available nominal candidate/distance comparisons lie below the declared minimum p95; 30 comparisons are DISTANCE_NOT_REACHED. At 30m the maximum effect/maximum-envelope ratios are 0.000619 for V1 and 0.000321 for V2. These numbers describe an early-distance synthetic plant scale, not a physical detection limit or a proof of equivalence.

Both V1 and V2 exhibit mixed curvature-normalized displacement signs. Whole-run phase effect maxima reach about 1.986cm outside the query window; that context is not classified against an extrapolated envelope. Small early displacement does not excuse the original 37 tracking/smoothness violations.

## Open evidence and next action

The envelope covers declared hypotheses only. Hardware crop/phase, mapping residual, distortion, static intrinsics applicability, physical pose uncertainty, road grade/camber and assisted annotation uncertainty remain open. The hypothesis set is not exhaustive. Total physical bound and independent meter truth remain unavailable.

Prioritize physical calibration evidence, formal uncertainty and validated pixel registration before interpreting small effects as real vehicle differences. Existing adverse family results remain a separate reason for redesign; this increment performs no redesign/search.

## Visualization and publication

Run the resolution_candidate_visualizer Python module, then open its printed 127.0.0.1 URL. The additive tab shows aligned trajectories, effects, p95 bands, ratios, signs, availability and original verdicts. All resources are local; loopback/origin checks remain enforced.

The builder consumes only the prefrozen policy and 70 historical synthetic recovery receipts. Publication admits exact full audit/summary/readiness receipts, rejecting unknown fields, nested private coordinates/paths and resealed numeric edits. No private image, annotation coordinate, route, timestamp or raw cache is published. No new private input is opened.

## Readiness

CANDIDATE_EFFECT_AUDIT_COMPLETE is supporting diagnostic evidence only. The existing blocker DAG is copied unchanged:

- CALIBRATION_UNCERTAINTY_PENDING
- INDEPENDENT_CALIBRATION_VALIDATION_PENDING
- PIXEL_GEOMETRY_REGISTRATION_PENDING
- METRIC_CALIBRATION_UNAVAILABLE
- INDEPENDENT_REFERENCE_UNAVAILABLE

Sealed reference: **NOT_GENERATED**.

Vehicle: **NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED**.

## Executor publication provenance

Publication auditing rejected a literal local checkout home path in the original recovery script. Its exact executed bytes remain local, with SHA 2e7e05ec92e12726cc3c006752c00b437e9ac23ef7fb62a35caca3ff370b5af0, bound by the original frozen policy. The published reader instead obtains comparison-root metadata from the runtime repository location. The audit explicitly records executed-recovery source and publication-safe reader source as distinct identities. No numeric output or original identity was edited.

The published reader refuses to execute the legacy policy under its different code SHA. Existing receipts can still be validated by the reader without replay. Normalized reconstruction requires the same historical comparison root; a relocated clone can consume published exact artifacts but needs separately supplied local historical-root metadata to reconstruct original hashes. A mismatch fails closed.

An aggregation attempt overlapping this source change was rejected by AUDIT_SOURCE_DRIFT. The final publication-safe derivative was regenerated from the same 70 immutable recovery receipts, with all rows, family summaries, phase metrics, envelopes and coverage checked identical to the pre-redaction draft.

Development context: 594 available comparisons below the declared envelope and 54 distance-unavailable comparisons; maximum available 5–30m effect is 0.122629cm. Stress context: 414/414 below-envelope comparisons, maximum 0.090933cm. These are separated by role and configuration in the audit, without rescoring or selecting a family member.

Final audit receipt: e6a0b566411beb07445d3827a321e53dddac1cf48872a2f0206bf86c648e04c0.

An exact aggregate repeat reproduced all four publication receipt hashes. Focused tests: 66 PASS; replay tests: 16 PASS. Actual Chrome 154 validation covered all 11 nominal scenarios, 18 comparison rows each, four arm trajectories, both p95 bands, desktop/mobile, refresh and meter-tab navigation. JS errors, external requests and failed resources: zero; server shutdown PASS. Independent code review found no Important/Critical findings and verified all original identity bindings, preserved violations, provenance separation and unchanged result sections.

Local release validation: AutoTune **1889/1889** and controls **142/142**, **2031 passed** in the combined full runner. Ruff, syntax, policy/evidence JSON (207 files), whitespace/diff, SCons, publication (800 files / 0 findings), privacy/publication regressions (28 tests) and independent review PASS. The exact pushed commit's GitHub Actions result is checked separately in the final handoff.
