# S2-RI failure attribution: insufficient stored inputs

## Identity and purpose

Cyber Validation, baseline a50d008e76b651d02ced30dbfcd810a141850170,
branch feature/cyber-autotune. This additive increment audits whether the
immutable frozen fit/CV store supports the requested read-only failure
attribution. Final numerical attribution status is
**ATTRIBUTION_INPUT_INSUFFICIENT / ATTRIBUTION_INSUFFICIENT**.
No numerical attribution has been performed. The input audit is implemented;
this is not S2_RI_FAILURE_ATTRIBUTION_COMPLETE.

The frozen starting observations remain:

| Historical gate | Failed candidate-fold jobs |
| --- | ---: |
| One-step RMSE | 0 / 32 |
| One-step MAE | 32 / 32 |
| One-step exact hit | 32 / 32 |
| One-step p95 | 27 / 32 |
| Rollout 25-step p95 | 32 / 32 |

All 32 one-step RMSE comparisons strictly improved on HOLD_LAST. These are
existing sealed receipt observations, not new stratum scores or a new gate
evaluation. Every other historical gate count is reconciled exactly as well.

## Original references and traced storage

Repository: https://github.com/rownlvh8875-coder/CyberPilot,
exact baseline above. The original repository license and attribution remain.
No simulator or external implementation is copied, and no dependency is added.

The authoritative private fit manifest receipt is
9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97.
Six exact public artifact file hashes bind the original results, job manifest,
authorization, selection, gates and readiness. The adapter validates 16
candidates, FOLD_A then FOLD_B, all 32 job receipts, candidate/comparator anchor
digest equality and all 834 manifest-listed files. Model/normalizer arrays are
hashed as opaque bytes; no array is decoded.

The frozen call path is empirical_s2_ri_fit_cv_math.one_step and
empirical_s2_ri_fit_cv_execution.rollout → save_arrays → job and run manifests:

| Existing stored data | Missing required evidence |
| --- | --- |
| One-step continuous delta prediction, projected next tick, canonical error, comparator error | Explicit current tick and target next tick arrays |
| Rollout projected endpoint, endpoint error, comparator error | Explicit initial/target endpoint arrays; observed and projected full paths |
| Opaque ordered anchor digests and counts | Per-anchor speed, rail, command and prior-motion context |

This is an insufficient **stored representation**, not corruption or a claim
that no information could mathematically be recovered from errors. The user's
STEP 2 requires stopping when required stored targets/arrays are missing.
No algebraic recovery from error buffers, new predictions, new rollouts, or
causal/raw input reopening is used as a fallback. The original receipts and
arrays are unchanged.

## Changes and expected effect

Two new modules implement input admission and aggregate-only publication.
There are no upstream runtime integration points, controller imports or
vehicle-specific changes.

The input gate first requires the exact manifest digest, before accessing any
manifest-listed array bytes. It rejects missing jobs/files, receipt drift,
anchor conflicts, symlinks, traversal, stale saved audits and store overlap.
Read-only SHA-256 passes before and after metadata inspection prove the
manifest-listed fit store and manifest unchanged. The separate causal/qlog
stores were neither opened nor modified; this is not an independently measured
byte-identity claim about inaccessible/unopened stores.

Output stores are external, atomic, immutable and manifest-last. Two independent
processes produced the exact same audit manifest:
a72853588e5315f06076aedb22b4ea4ec67ba33a3299c755700dfd71b4ff9c77.
The audit receipt is
83056845e88b03317d365745b506f8af6622d3e6925bb8f1cfe97488b81b2c6a.
Publication requires this independently recorded manifest pin, current
policy/executor identities, exact saved files, evidence invariants and an actual
verify-only resume receipt. Nested public job fields are explicitly allowlisted.

Independent review found two publication validation gaps: stale saved bundles
could bypass identity checks, and unchecked job extensions could leak private
fields. Both were reproduced by failing tests and fixed. Initial unpublished
audit outputs were retained; both input audits were rerun into a new immutable
store after the fix. No numerical attribution or model execution occurred in
any version. A later publication scan also caught local path literals in the new\ncode; those were replaced with an explicit sibling output-layout guard. Its\nregression tests pass, and both audits were rerun again before final publication.

## Attribution coverage and unavailable analyses

All requested public output slots exist, but the six numerical analysis
artifacts explicitly contain analysis: null and NOT_RUN:

- STATIC/MOVE populations, signed/one-tick/multi-tick partitions, movement
  confusion and SAE/SSE decomposition: not computed.
- Transition subset metrics, exact-hit/within-one-tick attribution and the
  0.5-tick projection-boundary distribution: not computed.
- Endpoint/path classes, p95 tail composition, first divergence, false-motion
  accumulation and missed-motion diagnostics: not computed.
- Speed, rail, prior-motion and reversal context: not computed.
- Fixed d/L grouping: not computed; no candidate ranking.
- STATIC + MOVE reduction reconciliation: not run; no additive p95 claim.

No hypothesis was confirmed or rejected from the aggregate gate pattern alone.
HURDLE_FAMILY_DESIGN_REVIEW_SUPPORTED is **not evaluated**, represented by
null plus NOT_EVALUATED_INSUFFICIENT_INPUT, not false evidence against the
hypothesis. No redesign recommendation is inferred. There is no hurdle,
classifier, threshold, regularization or new model implementation.

## Regression risk and acceptance

The risk is mistaking an input audit or historical aggregate for per-row
attribution. Readiness explicitly remains insufficient and never advertises
complete attribution. Missing data are not represented by zeros. The policy
does not add thresholds, revise metrics, relax a gate, select a candidate or
claim a physical mechanism.

Tests cover exact public/manifest identity, 32-job order/completeness, anchor
equality, missing targets, forbidden fallback, hash drift, paths/symlinks,
immutable writes, stale saved evidence, public-field allowlists and executor
firewalls. Synthetic model/decoder traps also cover the real audit and resume.
Partition/trajectory numerical tests are not applicable because no numerical
attribution implementation is executed for the unavailable inputs.

## Validation method and actual results

Validation counts and commands are recorded in the additive
empirical-s2-ri-failure-attribution-validation-v1.json.
The focused suite contains 34 tests plus 18 subtests.
Final full regression passed: AutoTune 4,012 + controls 142 = 4,154 tests
(exit 0, 1,588.49 seconds). Combined empirical: 1,380 tests plus 321 subtests.
Lateral replay: 16 tests. Ruff, compileall/syntax, JSON receipts,
publication/privacy/authority, whitespace and SCons all passed.
The validation receipt records commands and exact implementation source hashes.

The two actual independent input audits used single-thread environment settings.
All 12 source-inspection/array/fit/predict/rollout/selection traps were active for
the completed resume. Stored audit results reproduced the same public bundle.
This establishes **input-audit repeatability**, not numerical attribution
repeatability, which is NOT_RUN.

Browser, simulation, shadow and vehicle testing are not applicable to this
read-only input gate. No claims about physical EPS application or independent
validation are made.

## Reproduction interface

Use the exact frozen fit-store repeat-1 as the explicit --source. The explicit
--output is repeat-1 or repeat-2 under a separately named sibling directory
starting with empirical-s2-ri-failure-attribution-. No directory discovery or
fallback source is implemented. The input-audit module is
openpilot.tools.cyber_autotune.empirical_s2_ri_failure_attribution.

Publication uses openpilot.tools.cyber_autotune.empirical_s2_ri_failure_attribution_publication
with --store, --output and mandatory --manifest-sha256. The manifest pin must be
the value recorded from the independent runs, not a hash newly accepted from an
untrusted replacement bundle. This interface publishes metadata only.

## Handoff and preserved authority

NO NEW FITTING. NO POLICY CHANGE. NO GATE RELAXATION.
NO CANDIDATE ADMISSION. NO HOLDOUT.

S2_RI_NO_ADMISSIBLE_CANDIDATE, MODEL_SELECTION_FAILED_CLOSED and
FROZEN_S2_RI_LINEAR_FAMILY_FAILED_RETROSPECTIVE_DIRECTIONAL_GATE are unchanged.
All historical dataset/model, S1/S2/S3, Stage B, TA/SG, composition,
calibration/reference and vehicle blockers are copied from pinned readiness.
HOLDOUT remains CLOSED with opening_count 0; final pooled refit remains
unauthorized. Vehicle authority remains absent.

Full attribution would require separately authorized provision of exact
anchor-bound target/current arrays, full observed/projected paths and context.
This increment does not authorize creating those missing inputs. No next model
design or execution starts automatically.
