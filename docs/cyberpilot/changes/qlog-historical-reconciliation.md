# Exact historical qlog reconciliation

The authoritative final causal-completeness verdict is
**RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL**.
**QLOG_HISTORICAL_RECONCILIATION_COMPLETE** and
**LEGACY_ALIGNMENT_REPRODUCED** are established: both routes now reproduce the
entire historical selected-stream set, integer grid, command-pair accounting and
per-bin legacy support. The two qlogs add **zero contiguous causal model support**
at the unchanged 20 ms source-age limit.

This increment does not fit or select a model. HOLDOUT remains CLOSED, opening
count 0, reservation NONE. The previous blocked 154-rlog extraction and every
historical artifact remain immutable. This additive reconciliation does not
retroactively replace their authorization or verdict.

## Identity and authorization

Startup fetched origin, verified local/origin equality and a clean tree/index at
7e1f6c1739eb8baf57b0e032aa822fd033ce8df6, checked the minimum ancestor and
confirmed exact-HEAD Actions run 38142400526 completed/success.

The two routes are resolved from the sealed causal route set, V2 TRAIN selection
and V3 route-CV inputs. Exact qlog identities come exclusively from the prior
excluded-source list and V2 selected-stream manifest. No filename-prefix inference,
glob, other route discovery, alternate stream substitution or raw rlog reopening
occurs. Both routes remain RETROSPECTIVE_TRAIN_DEV_CV_POOL, with prior numeric
exposure; neither can be HOLDOUT or independent validation.

The new private policy, source audit and authorization were committed before
numeric decoding. Authorization binds exactly two content hashes, selected stream
locations privately, metadata/opening receipts, recorded commit, full CarParams,
empirical profile, schema closure, adapter, signal whitelist, alignment code and
output-store identity. Independent pre-opening safety review passed.

## Recorded-source logging audit

Repository: https://github.com/ajouatom/openpilot

Exact commit: 18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29

The source audit binds complete blob SHA and reviewed source-slice SHA for:

- openpilot/cereal/services.py
- openpilot/system/loggerd/loggerd.cc
- openpilot/system/loggerd/logger.cc
- openpilot/system/loggerd/logger.h

The existing source fingerprint binds the exact schema/import closure, command,
CarState, DBC, gyro producer and license/provenance receipts. No upstream source
is executed. The service table is statically parsed, including annotated literal
assignment, constant frequency division and finite integer-valued decimation.

| Service | Nominal source Hz | qlog decimation | Nominal qlog Hz |
| --- | ---: | ---: | ---: |
| carState | 100 | 10 | 10 |
| carControl | 100 | 10 | 10 |
| carOutput | 100 | 10 | 10 |
| gyroscope | 104 | 104 | 1 |
| carParams | 0.02 | 1 | 0.02 |

Ordinary retained events are byte copies: logMonoTime, event.valid and payload
semantics are preserved. Each service has its own counter, initialized at loggerd
startup and retained across segment rotation. These phases need not align.
Per-service arrival order is preserved; no globally sorted timestamp stream,
controller transaction identity or same-tick request/output guarantee is implied.

LoggerState builds initData once and reuses it for every segment. Both streams
open with shared segment ordinals and receive initData and route/segment
sentinels. CarParams decimation is one. Services without qlog selection are
excluded, but other forbidden services can still be present in qlog; the reader
checks the union discriminant and never dereferences forbidden bodies.

The field equivalence matrix classifies retained carState/carControl/carOutput
and gyro fields as DOWNSAMPLED_BUT_SEMANTICALLY_EQUIVALENT. This describes message
meaning, not an equivalent sampling process or 100 Hz causal support.

## Extraction and causal limitations

The exact recorded adapter and existing whitelist reader/alignment code are
reused without modification. The new adapter gate accepts only the two excluded
qlogs. Image/video, GPS/location, modelV2, planner/path/lane and all nonallowlisted
bodies are unopened.

The alignment remains 100 Hz integer grid, latest-past only, maximum age 20 ms,
strict source clocks, no interpolation/fill and no route/segment history crossing.
All rows, including invalid/gap/missing rows, are preserved with availability
masks and reasons. Actual steeringRateDeg samples are stored, never substituted
with a finite-count statistic. Its source DBC unit remains empty and physical
signed-rate semantics unresolved. Yaw/gyro physical/frame limitations remain
unchanged; no correlation or Stage B analysis occurs.

The qlogs provide 1,201 unique finite source steering-rate events. They produce
2,398 age-admissible aligned steering-rate entries; these are not 2,398 independent
measurements. Request and latActive events are present in each stream, but their
latest-past ages relative to selected state events exceed 20 ms. Their aligned
availability is therefore zero, as is aligned gyro availability. No stale value
is treated as usable.

| Added qlog scope | Grid rows | Source rate events | Aligned rate availability | Eligible bridge pairs | Causal-valid rows | Causal runs | Legacy design rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| First historical exclusion | 6,000 | 601 | 1,200 | 601 | 0 | 0 | 0 |
| Second historical exclusion | 5,989 | 600 | 1,198 | 600 | 0 | 0 | 0 |
| Total | 11,989 | 1,201 | 2,398 | 1,201 | 0 | 0 | 0 |

Unknown limiter reasons, physical EPS application and live SubMaster
alive/freqOk/updated remain unavailable. Logged raw/normalized command relation
is a CarController representation relation, not EPS acknowledgement.
Request/output alignment remains PUBLISH_ALIGNED_REQUEST_OUTPUT_DIFFERENCE
with REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE.

## Additive merge and historical reproduction

The new manifest references 154 immutable rlog segment receipts and arrays, plus
two new qlog packages. It does not copy or rewrite old arrays. Old stored global
indices remain unchanged. A separately named reconciled-route index overlay
defines full ordinal order using the segment-local aligned index. It is local
only and is never used to join histories across segment boundaries.

Route A/B below refer to canonical route order resolved from the immutable inputs.

| Reconciled route | rlogs | qlogs | Grid rows | Aligned rate availability | Eligible bridge pairs | Causal-valid rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 70 | 0 | 415,844 | 415,837 | 415,896 | 391,181 |
| B | 84 | 2 | 512,680 | 503,081 | 501,946 | 483,387 |
| Total | 154 | 2 | 928,524 | 918,918 | 917,842 | 874,568 |

Both route bridges are ROUTE_COMMAND_BRIDGE_CONFIRMED, with runtime STEER_MAX
409 and exact Float32(raw/409) agreement on 100% of eligible pairs. Both full
source-set SHA, segment counts, grid counts, diagnostic-valid counts, bridge
counts and per-bin accounting match history. Each new segment's target clocks,
mask/reasons, speed bins, valid angle/raw values and legacy support exactly match
its historical cache.

The 449,426 legacy common design rows remain unchanged:

| Route | LOW | MEDIUM | HIGH |
| --- | ---: | ---: | ---: |
| A | 27,217 | 146,878 | 80,971 |
| B | 85,107 | 79,278 | 29,975 |

No fitting/design matrix generation or CV scoring was performed to obtain these
accounting counts.

## Final assessment and receipt interpretation

The sealed extraction readiness receipt passes the inherited **full-route
aggregate field-presence plus legacy-accounting gate**. That narrow READY value
does not establish per-segment causal completeness.

Independent final review identified this distinction after extraction. Its
additive final assessment binds all ten preceding artifact receipts and reports:

- QLOG_HISTORICAL_RECONCILIATION_COMPLETE
- LEGACY_ALIGNMENT_REPRODUCED
- RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL
- QLOG_CAUSAL_CONTEXT_UNAVAILABLE_AT_FROZEN_TIMEBASE

The initial execution receipt is preserved, not rewritten to a new rule.
The final assessment is authoritative for causal completeness of the mixed
156-stream dataset. This post-extraction completeness audit does not alter
model policy, thresholds, timebase, source-age limits or historical evidence.
The 154-rlog rich causal subset remains useful for separately authorized
retrospective development. The qlogs restore accounting, not model support.
Changing cadence or stale-message admission would require a separate policy and
authorization, not a silent relaxation here.

## Repeatability, storage and privacy

Two independent decodes produce identical array dtype/shape/order/bytes,
config/snapshot/run/origin identities, segment/route receipts, manifest and
replica tree SHA. Resume with the raw-event decoder patched to raise succeeds
with identical bytes. Model fitting/selection entry points are patched to raise
through both full extraction passes and resume.

Atomic immutable array writes, receipt-last per segment and manifest-last commit
support interrupted exact resume; conflicting bytes, source drift, adapter/
config drift, symlinks, traversal and overlapping stores fail closed. Exact
qlog hashes and all four historical private-store trees match before/after.

Full arrays, timestamps, source locations and per-row origins remain in explicit
external local stores. Public output contains only aggregates, opaque route IDs,
source/receipt hashes and status. Existing raw rlogs and the third zero-support
route were not reopened. There is no UI or browser validation in this increment.

## Validation

| Check | Result |
| --- | --- |
| New qlog-focused tests | 65 pass |
| Combined empirical focused | 964 pass |
| Full AutoTune + controls, frozen final sources | 3,823 pass in 1,578.99 s: 3,681 AutoTune + 142 controls |
| Separate controls | 142 pass |
| Lateral replay | 16 pass |
| Previously affected bounded-A1 module, stable-source rerun | 6 pass |
| Ruff / compileall / JSON / public receipt chain | Pass |
| Publication/privacy/authority | 1,264 files checked, findings 0 |
| git diff --check / historical tracked preservation | Pass; all 19 changed files additive |
| SCons | Pass |
| Independent review | PASS, including source audit, final completeness and 65 focused tests |
| Browser | NOT_APPLICABLE |

An earlier regression run was invalidated by repository edits during execution:
two source-binding checks and one fixture loaded before validator hardening failed.
No historical code was changed to suppress them. With final sources frozen, the
complete 3,823-test rerun above passes. Extraction receipts and input-store
integrity were unaffected. Exact-HEAD GitHub Actions completion is independently
checked after push and reported with its run link in the completion report.

Commands use explicit operator-provided paths; they never search for stores:

    python -m openpilot.tools.cyber_autotune.empirical_qlog_reconciliation \
      --store <NEW_ABSOLUTE_EXTERNAL_STORE> --causal <IMMUTABLE_CAUSAL_STORE> \
      --v2 <IMMUTABLE_V2_STORE> --v3 <IMMUTABLE_V3_STORE> \
      --source <IMMUTABLE_SOURCE_STORE> --source-repo <EXACT_PUBLIC_GIT_OBJECT_STORE> \
      --root <APPROVED_ROOT_ONE> --root <APPROVED_ROOT_TWO> \
      --replica repeat-1 --prepare-only

Preparation freezes policy and exact identities. Only the explicitly authorized
operator may continue with repeat-1/repeat-2 extraction. The source audit is a
precondition; metadata-only preparation alone does not authorize other streams.

## Unchanged limits and next trigger

No model fitting, model selection, candidate execution, TA-B/SG-A execution,
composition, new route search or HOLDOUT opening occurred.
CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED,
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, STAGE_B_SIGNAL_ADMISSION_BLOCKED and
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED remain.

TA-B and SG-A retain their historical standalone tradeoff verdicts. Composition,
search and frozen candidate evaluation remain unauthorized. Calibration/reference
blockers, sealed reference NOT_GENERATED, vehicle NOT_READY,
REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED remain unchanged.

Next model-family work requires separate authorization and a frozen development
policy. This reconciliation neither creates model coefficients nor supplies an
untouched HOLDOUT.
