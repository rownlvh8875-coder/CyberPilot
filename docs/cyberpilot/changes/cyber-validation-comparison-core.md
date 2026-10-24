# Cyber Validation three-arm comparison core

## Identity and purpose

- STEP9 local comparison/report layer, implemented; independent review completed.
- feature/cyber-autotune base1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Compare declared upstream baseline, Cyber current and candidate receipts while
  rejecting malformed experiments, nondeterminism and metric regressions.
- This is not yet an execution runner or native replay/simulator qualification.
  No raw input, controller, device, network, filesystem or actuation API introduced.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot at base above. Existing contracts.py
  MetricContract/MetricBatch and preflight.check_metric_pair reused unchanged.
- v2 lateral measurements retain public cyber_lateral.metrics formulas. Earlier
  Step7 D3Y6/6 A/A and0/6 A3performance remain historical; no baseline replacement.
- Original upstream c8fb9068 and opendbc4134c0d1 unchanged. No new dependencies,
  copied fork algorithms or licensing additions. Repository license applies.
- Path: ComparisonPolicy + exact RunReceipt matrix -> shape/identity/gate checks
  -> per-arm repeatability -> candidate against both references -> local result
  -> JSON-compatible dictionary or Markdown string. No runtime consumer.

## Changes and expected effect

- comparison.py: immutable binding/policy/group/receipt/result interfaces,
  source/config/input/reset/mask/metric/adapter/plant/domain/environment/timebase
  identities, exactly3arms x2repetitions pergroup, bounded64group resource cap.
- Groups are predeclared comparisons with complete producer-calculated metrics,
  not necessarily individual route windows. No averaging RMSE/percentiles, new
  grouping algorithm, sample independence estimate or invented missing coverage.
- Explicit per-arm software/profile/config/adapter identity may differ; common
  input/reset/mask/metric/plant/domain/environment/timebase must match.
- Ordered trace hashes AND metric records/coverage must repeat. Summary equality
  cannot hide trace differences. Missing/bad basis blocks before physical claims.
- Hard violations FAIL; timeout/failure/malformed/incomplete evidence requires
  revalidation. Current-vs-upstream regressions are diagnostic; candidate must
  satisfy unchanged strict no-worse against both references. No weighted sum.
- Primary center-RMSE improvement by explicit positive reviewed minimum must occur
  in at least one predeclared group, with no regressions in other groups/metrics.
  This is descriptive, not uncertainty qualification or comfort ranking.
- reports.py invokes comparator itself. Only hashes/generated issue codes are
  emitted; invalid raw names/paths are not reflected. No persistence/parser.
- Tests test_comparison.py,test_reports.py. No prior source/controller/metric edits.
- All-local success still returns REVALIDATION_REQUIRED with authenticity,
  uncertainty and longitudinal-adapter pending. All authority outputs fixedfalse.
- No state/reset ownership change, extra delay, safety/override/actuator or
  longitudinal behavior changes. Rollback: cease importing standalone tools.

## Regression risk and acceptance

- Matching hashes and caller metadata do not prove producer truth or execution.
- Labels/group counts do not establish independent routes/days/vehicles. No real
  cohort, speed bins, bounds, confidence threshold or tuning profile is approved.
- Preserve metric v2 coverage and no-worse criteria. Missing primary/phase/coverage,
  NaN/bool,0-to-positive regression, wrong source and incomplete arms fail closed.
- Actual native runner, immutable artifact ingestion, isolation, longitudinal
  extraction, uncertainty and report persistence remain future integration work.
- No holdout/validation data or frozen acceptance references touched. Final
  independent code review required, not real-vehicle approval.

## Validation method and actual results

| Check | Method/evidence | Result/limit |
| --- | --- | --- |
| TDD | test_comparison then test_reports | missingmodule RED ->17 and5GREEN |
| AutoTune package | existing venv Python3.12.13 unittest discover | 123passed exit0 |
| Ruff / whitespace | ruff check package; git diff --check | PASS exit0 |
| controls+AutoTune | prepared test_runner.py -j2 | 255passed,19.91s,exit0 |
| Default PC | instrumented existing runner, bounded300s | 1237collected; timeout exit124, no final counts |
| Independent review | one final whole-plan review | 0Critical/Important;1Minor deferred |
| Native replay / calibrated closed loop / shadow | not invoked | NOT RUN |

## Handoff

The last pending full-PC test was TestLagd.test_read_invalid_saved_params;
live worker HTTPS sockets were observed. This does not establish an assertion
failure or definitive network root cause. Interrupt-time cleanup exceptions are
not a successful run. The owned runner exited; no runner process remained.

Deferred minor: permanent two-group fixtures do not cover one improved plus one
unchanged/regressed group; reviewer in-memory probes passed both behaviors.
Native producer truth/authenticity, pooled-cohort uncertainty, longitudinal
adapters, persistence and vehicle qualification were not established by review.

STEP9 PARTIAL. Local comparison functionality is not an automated qualified
three-controller replay pipeline. STEP8 PARTIAL; A3 still rejected. Overall
vehicle readiness NOT_READY. No commit/push/deployment or live controller change.

## Subsequent test-only follow-up — 2026-10-02

Two permanent synthetic multi-group fixtures resolve the deferred coverage gap:
improved+unchanged retains local improvement with REVALIDATION_REQUIRED, while
improved+regressed fails irrespective of group order. Each asserts12receipts,
two repeatable groups and no qualification/runtime authority; adverse group and
both baseline identities remain in regression diagnostics. No metric/threshold or
production implementation changed. Isolated in-memory accumulator-overwrite and
per-group regression-reset mutants fail one order each; originals pass.
Focused search/comparison29tests/6subtests PASS; package246/781subtests PASS.
Final independent review0Critical/Important/Minor; fresh targeted3tests/6subtests
and isolated mutants independently verified. Default PC1285passed43skipped1xfailed,
2354.94s,exit0;1360collected. Before/after73overlayfiles and recorded identity fields
match. Synthetic fixtures are not independent real routes, primary truth, plant
calibration or candidate acceptance.
