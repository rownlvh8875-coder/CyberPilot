# Retrospective causal TRAIN/DEV data generation

## Identity and purpose

Cyber Validation / AutoTune, EMPIRICAL_CAUSAL_TRAIN_DEV_GENERATION_V1.
Baseline b9a3df4c242345906e28d961d1bad9c3964a5e83, feature/cyber-autotune.
Startup fetch verified exact local/origin equality, clean tree/index, minimum
ancestor and exact-HEAD CyberPilot Actions run 38134726166 completed/success.

The increment implements and executes extraction, provenance and causal-context
preservation. It does not implement or fit a model. Existing high-support old
data remains useful for retrospective development because measured command,
steering and context can be recovered without changing historical roles or
results. Prior numeric exposure prevents either route from being HOLDOUT,
independent evaluation or qualification evidence.

**Final dataset status: RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED.**
The authorized rlog subset was actually extracted twice. The complete historical
source-set reproduction gate cannot pass because two historical segments are
qlogs, outside this request's rlog-only numeric reopening authorization.

## Original references

The V2 split, V3 folds/coverage, source reclassification, equivalence classes,
plant profile, causal schema V2 and lateral H1 contract are exact receipt-pinned
in empirical-causal-train-dev-policy-v1.json. No route prefix was used to resolve
inputs. Two V2 TRAIN members exactly equal the inverted V3 route-CV pair.
The zero-support historical DEVELOPMENT route remains context only.

Recorded public source:
[ajouatom/openpilot at 18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29](https://github.com/ajouatom/openpilot/tree/18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29).
The existing exact public-origin attestation, source fingerprint, schema blobs,
dependency closure and source-specific metadata adapter are inputs, not regenerated
source-audit results. The new signal-provenance receipt binds exact public paths,
file/symbol/source hashes and license evidence. Public source blobs are retained
only in the external local evidence store; no upstream source was copied into
the repository.

Call chain: exact public route resolution → historical private manifest/receipt
verification → private route-set/authorization seal → recorded-schema whitelist
reader → all-row alignment → immutable arrays/origins/context → legacy accounting
→ independent repeat/resume verification → aggregate publication.

No production caller, controller, plant, model asset or submodule is changed.
Existing empirical, H1/viewer, TA/SG and calibration/reference evidence is
immutable. No new dependency is introduced.

## Changes and expected effect

Six additive modules separate policy/admission, numeric reading, alignment,
immutable storage, execution and aggregate publication. The policy and exact
route-set/authorization were sealed before opening raw numeric payloads.

A metadata preflight rejected the assumption that all 156 historical selected
streams were rlogs. The first route has 70 rlogs. The second has 84 rlogs and
two qlogs. The aborted preflight policy and blocker remain immutable. A separate
rlog-only execution store was sealed before numeric opening, authorizing exactly
154 content hashes and explicitly listing the two exclusions. No qlog numeric
payload, alternative route, third route or V1 raw log was opened. The route was
not renamed or split to conceal its incomplete authorized source set.

The two members retain RETROSPECTIVE_TRAIN_DEV_CV_POOL roles. Neither is assigned
permanently to TRAIN or DEVELOPMENT. Both have holdout_allowed,
independent_validation_allowed and qualification_allowed false.

### Command and measurement provenance

Three distinct command stages are stored with their own event clock, validity,
age, presence and source provenance:

- controller request: carControl.actuators.torque;
- logged post-CarController normalized output: carOutput.actuatorsOutput.torque;
- logged raw output representation: carOutput.actuatorsOutput.torqueOutputCan.

Runtime STEER_MAX is bound to allowlisted initData settings and the exact source
default branch. Both routes resolve to 409. The normalized/raw Float32 relation
is a CarController representation relation, not physical EPS acknowledgement.
Physical application remains null.

Request and output are independently latest-past aligned to the selected state
publish time. There is no transaction ID. The stored difference is named
PUBLISH_ALIGNED_REQUEST_OUTPUT_DIFFERENCE, never exact limiting delta. Safety,
curvature, rate-limit and driver-limit causes remain null/unavailable.

Actual steeringAngleDeg **and actual steeringRateDeg samples** are preserved.
The rate is not a finite-coverage count substituted for a value.
SAS11.SAS_Angle is source-bound to signed16, factor0.1, offset0, unit Deg.
SAS11.SAS_Speed is unsigned8, factor4.0, offset0, with an **empty DBC unit**.
The schema name is steeringRateDeg, but confirmed physical degree/s or signed
steering-rate semantics are not claimed. This limitation matters for future
state-space families that require a signed physical derivative.

ESP12.YAW_RATE retains decoded raw values, factor 0.01 / offset −40.95 and empty
DBC unit; physical unit/frame remain unresolved. Direct gyro retains device xyz,
source, acquisition and publish clocks, validity and age. IMU-to-vehicle transform
is UNVERIFIED. No yaw/gyro correlation, unit selection or Stage B analysis occurs.

Only the five declared control Params are read. Full Params dumps, modelV2,
planner/path/lane, fused pose, calibration, images/video and GPS bodies are never
dereferenced. Other union envelopes can be encountered without reading their bodies.

### Timing, runs and H1 mapping

The base dataset preserves every 100 Hz integer-grid row, including inactive,
override, invalid and gap rows. It uses latest-past only, a 20 ms age gate and
strict per-stream increasing source clocks. There is no interpolation, trimming,
cross-route or cross-segment history.

Unavailable values use explicit availability masks and NaN/negative-index
storage sentinels defined as null. Known false or zero values remain distinguishable
from missing data. Source event valid/present/new-event/age/gap fields are not
live SubMaster alive/freqOk/updated; those live fields remain null.

CAUSAL_CONTINUITY_RUN breaks on segment, source gap, invalid/unavailable required
causal input or reset. Speed-bin/intervention labels do not themselves split it.
LEGACY_V2_MODEL_RUN separately uses diagnostic-valid, same-speed-bin,
segment-local rows. History 45 is used only to count historical support; no
design matrix, supervised target, fit or CV score is produced.

Each row binds route/segment receipts, source SHA, ordinal, aligned/global index,
both run identities and within-run indices, selected message indices/clocks/ages,
source/profile/config/policy and an exact consumed-input snapshot digest.
Per-segment manifests provide constant row identities without repeating large
strings in each array. Config sequence stays 0 unless configuration changes;
segment rotation alone does not increment it. Configuration drift blocks the route.

H1 mapping implements the available request/output/raw command, angle/rate,
pressed/driver torque/active, config and snapshot identities. Desired/actual
curvature, physical applied torque, controller decision clock and unavailable
live-health fields remain null. This is provenance mapping, not a production
observer or an invented live H1 transaction.

## Actual extraction and legacy reproduction

Route A/B below are the canonical lexical members of the full-ID route-set
artifact. Public artifacts include opaque full route IDs, never private names
or source paths.

| Quantity | Route A | Route B |
| --- | ---: | ---: |
| Authorized rlogs extracted | 70 | 84 |
| Historical selected streams | 70 | 86 |
| Excluded qlogs, not opened | 0 | 2 |
| All aligned rows | 415,844 | 500,691 |
| Diagnostic-valid rows | 382,025 | 328,030 |
| Actual aligned angle/rate availability | 415,837 | 500,683 |
| Request availability | 415,787 | 500,622 |
| Normalized/raw output availability | 415,844 | 500,691 |
| Causal required-valid rows | 391,181 | 483,387 |
| Causal continuity runs | 24,659 | 17,302 |
| Valid gyro xyz rows | 414,122 | 498,345 |
| Eligible command pairs | 415,896 | 500,745 |
| Exact Float32 bridge rate | 100% | 100% |
| Extracted-segment legacy equality | PASS | PASS |
| Full historical route reproduction | PASS | BLOCKED |

Both command bridges are ROUTE_COMMAND_BRIDGE_CONFIRMED. Domain/sign conflicts
and gyro acquisition clock regressions are zero. Source-age distributions,
request/output publish-order taxonomy, optional-field coverage, run lengths,
mask causes and intervention transitions are aggregate-published.

The two excluded qlogs account for 11,989 historical grid rows and 1,201 command
pairs. Their omission is explicit, not a silent skip. Both routes retain the
historical diagnostic-valid counts and all common support counts:

| Historical accounting only | Route A | Route B | Pooled count |
| --- | ---: | ---: | ---: |
| LOW common rows | 27,217 | 85,107 | 112,324 |
| MEDIUM common rows | 146,878 | 79,278 | 226,156 |
| HIGH common rows | 80,971 | 29,975 | 110,946 |

For every extracted segment, grid/state clock/order, diagnostic mask/reason bits,
speed bin, valid angle/raw-command projection, contiguous-run/common-row counts
and command bridge counts exactly match its immutable V2 cache receipt.
Route A also reproduces the full route. Route B fails full selected-segment-set,
total-grid and command-pair count equality. No historical value is overwritten.
Support equality alone does not override this stricter integrity gate.

## Regression risk and acceptance

The principal risks are source/schema drift, missing actual rate, incorrect
publish alignment, context loss, stale resume and false complete-route claims.
Unknown source, dirty build, profile/config drift, aliases, source hash changes,
conflicting atomic bytes and bridge/reproduction conflicts fail closed.

Each segment commits its receipt last after deterministic NumPy arrays and field
manifests. Arrays use exact dtype/shape/C-order/file and payload SHA. External
stores reject aliases and overlap with raw roots, historical stores and repository.
Resume verifies opening/config/array/source-command receipts and source hashes.

The current result is BLOCKED, although useful causal rows were preserved.
No replacement model family is selected or implemented. Existing simple-track
closure and Stage B blockage remain unchanged. Model fitting/selection, TA/SG,
candidate search/evaluation, HOLDOUT opening and vehicle authority are not run.

Rollback is to stop this standalone extractor; no production integration exists.
Historical receipts remain the baseline. Future numerical work needs separately
authorized model policy and explicit resolution of the rlog-only versus full
historical stream-set mismatch. A new data collection is not assumed necessary
for retrospective TRAIN/DEV; untouched HOLDOUT remains a separate requirement.

## Validation method and actual results

Two independent raw extractions produce identical array dtype/shape/order/bytes,
origins, causal/legacy runs, config/snapshot digests, coverage, bridge results,
route receipts, manifest and complete replica trees. The second execution traps
NumPy least-squares and model fit/select/design/evaluate/rollout APIs. Extraction
completes without invoking them. Exact resume succeeds with the raw event decoder
forced to raise, leaving its complete output tree unchanged.

Both raw-source hash sets and historical V2/V3/source-store byte trees are
identical before/after. Dataset manifest:
c584e2031baf144103c20ca76974c53a9ea614babdf9c865936675474742bba8.
Aggregate repeatability receipt:
51f525ed7b3b560b856fe62018471613935892554b0d86f8ebddb58400b886ad.

| Check | Actual result |
| --- | --- |
| New focused synthetic tests | 86 pass |
| Combined empirical discovery | 899 pass |
| Full AutoTune + controls | 3,731 pass in 1,645.59 s: 3,589 AutoTune + 142 controls; the 27 subsequently added admission/publication tests also pass in the final 86-test and 899-test focused runs |
| Controls test runner | 142 pass |
| Lateral replay | 16 pass |
| Ruff | Pass on all CI-scoped CyberPilot sources/tests |
| SCons | Pass, targets built |
| Syntax / publication / privacy / diff | Pass; 1,245 files scanned, zero findings; 11 exact public receipt chains; staged diff clean |
| Independent review | Pre-opening and final correctness/privacy/publication review passed |
| Browser | NOT_APPLICABLE, no UI added |
| Final exact-HEAD CI | Verified after commit/push in delivery record; no historical CI result substitutes for it |
| Simulation / candidate / shadow / vehicle | NOT_RUN, outside extraction scope |

Validation commands (existing virtual environment, single BLAS thread):

~~~sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -s openpilot/tools/cyber_autotune/tests -p 'test_empirical*.py'
python -m unittest -q openpilot.tools.cyber_autotune.tests.test_empirical_causal_dataset
python -m compileall -q openpilot/tools/cyber_autotune tools/cyberpilot
python tools/cyberpilot/check_publication.py --base origin/main
git diff --cached --check
scons -j2
~~~

Ruff and lateral replay use the exact scopes in the existing CyberPilot workflow.
No browser check applies because this increment adds no UI.

Public evidence contains
aggregate counts, source facts and receipt hashes only. Full rows, values,
timestamps, private paths, origins, arrays and config values remain external.

## Handoff

HOLDOUT_OPENING_CLOSED, opening_count = 0, reservation = NONE,
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED and NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT remain.
The two exposed routes cannot become engineering or independent HOLDOUT.

TA-B remains TA_STANDALONE_TRADEOFF_ONLY. SG-A remains
SG_CLOSED_LOOP_TRADEOFF_ONLY. COMPOSITION_NOT_RECOMMENDED,
COMPOSITION_NOT_AUTHORIZED, SEARCH_NOT_AUTHORIZED and
FROZEN_EVALUATION_NOT_AUTHORIZED remain.

CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE remain. Sealed reference is NOT_GENERATED.
Vehicle remains NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

No actual HOLDOUT opener, production observer, model/candidate authority or
vehicle deployment is introduced.
