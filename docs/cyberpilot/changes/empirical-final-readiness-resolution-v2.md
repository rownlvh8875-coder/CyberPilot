# Empirical final readiness resolution V2

## Identity and purpose

Cyber Validation / AutoTune; additive readiness resolution and future development
data admission, based on ba84b61fee7f3a2c0c2e2815c1b3a6ebdfb06eeb on
feature/cyber-autotune. The reconciliation execution receipt passed a full-route
aggregate gate and says READY. The later final assessment says PARTIAL because
the two qlogs have no contiguous causal support at the frozen timebase.
These are different claims, not alternative model readiness decisions.

The purpose is to ensure new consumers resolve final completeness from the final
assessment and cannot treat accounting-only qlog rows as model fitting, selection
or CV support. No old receipt, source file, role assignment or result is rewritten.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot; exact baseline above.
Authoritative input is empirical-qlog-final-assessment-v1.json, receipt
cd4591e909d6dd1c074b872f271a1d1d75ae8a5ae70aa17e7a6b88cf5bcad580.
The historical execution receipt is
empirical-qlog-reconciliation-readiness-v1.json, receipt
a016fd843cd4e5f7478951811127deb581cfee9870611dd9ddccd661e14156ec.
The resolver pins the complete public reconciliation chain plus rlog
route-set, authorization, coverage, extraction policy, schema, H1 mapping and
nonexecuting future-family shortlist. Exact member identities are loaded from
these receipts; no route ID is guessed from report prefixes.

The original source/schema/DBC/adapter provenance remains in the historical
receipt chain. There is no new upstream source import, dependency, submodule,
cereal or license change.

## Changes and expected effect

- empirical_final_readiness.py: exact pinned public inputs; final precedence;
  route/stream support partition; final-resolution validation.
- empirical_causal_support_guard.py: future consumer's pre-array rlog segment
  admission and byte-bound in-memory causal row/history eligibility.
- empirical_final_readiness_publication.py: aggregate contracts, two exact
  executions, atomic no-overwrite publication and exact resume.
- New focused tests and six additive JSON artifacts. Existing extractor,
  simulator, controller, visualizer and historical public/private stores remain
  unchanged.

The alternative of rewriting the old READY receipt was rejected: it would erase
execution history. The alternative of using latest filename/mtime, or falling
back to READY when final evidence is missing, was rejected: those do not prove
authoritative completeness.

## Authoritative precedence

AUTHORITATIVE_FINAL_ASSESSMENT > EXECUTION_READINESS > INTERMEDIATE_EXTRACTION_STATE.

For this pinned generation all required sources must be present and valid.
There is **no fallback** to execution READY. The final assessment's name, receipt
SHA, full input chain, status and scope are checked. A self-sealed replacement,
extra assessment, missing final, corrupt receipt, execution receipt supplied as a
resolution, or source/profile/role drift fails closed.

The three resolved states remain separate:

| Meaning | Resolved state |
| --- | --- |
| Final mixed-stream causal completeness | RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL |
| Historical selected source/grid/pair accounting | PASS |
| Exact two-qlog reconciliation | COMPLETE |

The prior execution READY and original rlog BLOCKED receipts are retained as
historical scopes. Neither grants future model authority. New automation and
model-development integrations must consume the new final resolver and admission
guard. Historical pinned publishers are not retroactively modified.

## Support partition

| Subset | Streams | Base aligned rows | Causal-valid rows | Causal runs | Future design role |
| --- | ---: | ---: | ---: | ---: | --- |
| Rich rlog subset | 154 | 916,535 | 874,568 | 41,961 | Retrospective development, conditional on new authorization/policy |
| Historical qlog subset | 2 | 11,989 | 0 | 0 | Accounting only; never fitting/selection/CV support |
| Mixed historical accounting | 156 | 928,524 | 874,568 | 41,961 | Full accounting, not full causal completeness |

Both routes' full historical reproduction passes. The qlogs add 1,201 eligible
command pairs; the mixed total is 917,842 with 100% exact Float32 bridge relation.
That relation proves logged post-CarController representation consistency,
not physical EPS application.

Qlog carControl is downsampled to nominal 10 Hz. At the unchanged 20 ms maximum
source age, latest-past request and latActive aligned coverage is zero.
No interpolation, forward fill, stale admission, source-age relaxation or
causal promotion is performed. Steering-rate aligned coverage and historical
design accounting are not independent samples or new model support.

## Future row admission

First call require_segment(resolution, historical_rlog_manifest, segment_receipt)
before loading arrays. The final resolution must exactly match the pinned public
chain. The manifest must equal the original rlog dataset manifest SHA, not the
mixed accounting manifest. The exact segment receipt must be a member of that
route in the manifest and have matching authorization, source fingerprint,
recorded/numeric adapter and config identity.

The two qlog content identities are denied before any array access, even if a
caller labels the stream as rlog. Unknown segments/routes, the old zero-support
DEVELOPMENT route and unsupported roles cannot enter this path.

After separately authorized array loading, eligible_rows requires exact sealed
array key set, dtype, shape, C order and content SHA. It retains the original
arrays and returns a mask; it never trims, fills or changes them. Required actual
steering-rate values cannot be substituted with a finite-coverage count.
Required availability, finite values, source-event valid/present/fresh/gap
status, causal validity and the unchanged legacy diagnostic mask must pass.
Clock identities and source ages are checked, including the exact 20 ms boundary.
Future messages, clock regressions and fabricated age values are rejected.

A separately frozen history length can only use valid rows in the same route,
segment, causal run and contiguous 100 Hz grid. No history length is selected
here. Causal run identity remains distinct from legacy speed-bin model runs.
No new model design support, scoring, coefficient or performance metric is
computed from historical arrays in this increment.

## Nonexecuting S1/S2/S3 admission contract

The future shortlist is preserved without choosing or implementing a family:

- S1: second-order latent state-space.
- S2: delta-angle causal model.
- S3: bounded piecewise-affine actuator with source-defined regime semantics.

The rlog dataset preserves actual steering-rate values, but the recorded DBC
unit is empty and physical rate unit/sign semantics remain unresolved. S1/S2
require a source-bound rate contract; S3 also requires proof of source-defined
deadzone/hysteresis semantics. The contract does not infer either mechanism.

Future work also requires explicit implementation/fitting authorization and a
predeclared model/config/reset/history/metric/support policy, route-disjoint
retrospective development policy and this admission guard. Minimum DEVELOPMENT
support remains 201; this increment does not compute or qualify model support.

## Regression risk and acceptance

Risk: confusing full-route aggregate field presence with per-segment causal
completeness; using base grid counts as design support; accepting qlog by a forged
extension; accepting unbound array bytes; crossing gap/route/run histories.

Acceptance: final resolution stays PARTIAL, accounting PASS/COMPLETE is separate,
qlog admission fails before array access, missing required evidence fails closed,
the richer rlog subset remains available only for separately authorized
retrospective development, and all historical bytes are preserved.
Rollback is removal of the additive consumer contracts/modules; old evidence
does not need restoration.

## Validation method and actual results

Ubuntu 24.04 via WSL, repository prepared environment, no added dependencies.
Commands below operate on public aggregates or synthetic fixtures only.
The full source remains frozen while source-binding regression suites execute.

| Check | Command/method | Actual result |
| --- | --- | --- |
| Focused | pytest new final-readiness and causal-support-guard files | 52 passed; 10 subtests passed |
| Combined empirical | pytest empirical test files | 1,016 passed; 127 subtests passed |
| Full AutoTune + controls | tools/test_runner.py both directories -j 1 | 3,875 passed (AutoTune 3,733 + controls 142), 1,579.19 s |
| Controls | tools/test_runner.py controls/tests -j 1 | 142 passed |
| Lateral replay | two Cyber lateral unittest modules | 16 passed |
| Ruff/syntax | CI-scoped Ruff; compileall | PASS |
| JSON/publication/privacy | all evidence JSON; check_publication.py | PASS; 1,277 files, findings 0 |
| Build | scons -u -j2 | PASS |
| Independent review | read-only review of new source/tests/contracts and six outputs | PASS; 52 tests; 6/6 exact artifacts |
| Exact repeatability/resume | two public-only bundles; immutable rerun | PASS; exact receipt/file bytes; read allowlist and NumPy load/lstsq traps |
| Historical preservation | Git tracked diff; input file hashes before/after | PASS; no historical tracked changes; pinned input bytes identical |
| Browser | No UI added | NOT_APPLICABLE |
| Extraction / model / simulation / shadow / HOLDOUT | No execution authority | NOT_RUN |

## Handoff

No raw log, private numeric array, private store, new route or HOLDOUT was opened.
No extraction, fitting, family selection, CV scoring, candidate or TA/SG execution
occurred. No production/controller/CAN/Params/device/vehicle source or state
changed. Existing H1/viewer and historical verdicts are immutable.

Preserved: CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED;
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT; STAGE_B_SIGNAL_ADMISSION_BLOCKED;
TA_STANDALONE_TRADEOFF_ONLY; SG_CLOSED_LOOP_TRADEOFF_ONLY;
COMPOSITION_NOT_RECOMMENDED / COMPOSITION_NOT_AUTHORIZED;
SEARCH_NOT_AUTHORIZED / FROZEN_EVALUATION_NOT_AUTHORIZED.
HOLDOUT_OPENING_CLOSED, opening_count=0, reservation=NONE,
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED.
Calibration/reference blockers remain CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING, PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE and INDEPENDENT_REFERENCE_UNAVAILABLE.
Sealed reference NOT_GENERATED; vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED. No independent qualification or vehicle authority.
