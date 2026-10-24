# Empirical lateral Dataset V2 readiness

## Identity and purpose

Cyber Validation / AutoTune; additive offline eligibility tooling.
Baseline: feature/cyber-autotune, 03ea6ba14f3e96b2d4cee9164e27cfeca385cdf2.
Prepare EMPIRICAL_LATERAL_DATASET_V2 without reopening V1 numeric payloads.
The approved metadata-only root is operator-supplied privately and checked
against an exact allowlist. Windows and WSL aliases describe one storage root.
No explicit additional sibling root was present in the existing experiment
receipts; no parent-directory, home, disk, cloud or network crawl is permitted.

## Design and original references

Reuse existing empirical receipt hashing/atomic persistence, recorded schema
and source contracts read-only. Source:
https://github.com/ajouatom/openpilot/tree/5a970f1ad25d9f07d055955d7a7c14603b6b7813
including cereal/log.capnp, Hyundai carstate.py/carcontroller.py/values.py,
car.capnp, hyundai_kia_generic.dbc and card.py. MIT upstream attribution stays
in place. Existing source and publication receipts bind exact file hashes.
Current submodules remain pinned and unchanged.

Metadata discovery -> source/profile identity -> conservative route grouping ->
V1 exclusion -> hash-ordered route split -> future numeric eligibility.
No production integration points; no controller, actuator or model fitting.
State consists only of immutable private metadata/split/coverage receipts.
Resume must revalidate source bytes and reject stale or conflicting receipts.

Route identity combines source commit, vehicle fingerprint, full CarParams SHA,
software/profile identity, logger-start identity and segment lineage with
monotonic envelope ranges. Directory names alone never establish independent
routes. Duplicate content, same logger-start identity and overlapping lineage
cannot create additional routes. Ambiguous identity remains blocked.

## Regression risks and predeclared gates

V1 contains one route. Its actuator strict READY gate failed; yaw design support
reached only 82 TRAIN rows against the frozen 201 minimum. These findings explain
the need for a new generation and do not authorize changing gates or reusing
TRAIN/DEVELOPMENT/HOLDOUT/EMBARGO. V1 is PLANNING_CONTEXT_ONLY.

At least three distinct untouched compatible routes are required for one route
in each role. Hash ordering assigns whole routes before numeric inspection;
60/20/20 rounded allocation reserves at least one DEVELOPMENT and HOLDOUT route.
Quality cannot change roles. Fewer routes means ROUTE_DISJOINT_SPLIT_UNAVAILABLE.
No V2 split artifact is published unless a split actually exists.

Homogeneity requires the exact recorded source, Santa Fe 2022 legacy torque
profile, full CarParams identity, command bridge source and runtime STEER_MAX
provenance. Other commits/profiles require a separate source audit. The existing
ARX1/FIR25 × delays 0/5/10/20 policy and 201 minimum remain unchanged.
Unknown limits remain unknown; no clean-mask claim is inferred.

Future eligibility uses latest-past 100 Hz alignment, maximum age 20 ms,
strict increasing clocks, no gap interpolation and no cross-segment history.
Missing measurements are null. Numeric HOLDOUT eligibility is itself an opening
and requires a complete model/unit/metric/support freeze and one-time receipt.
Wheel-speed and lateral-acceleration crosschecks require source-proven units,
signs, track width or acceleration frame; otherwise they remain blocked.
Device gyro correspondence never supplies a calibrated vehicle frame.

## Safe passive collection guide

Use only normal, legal commuting or everyday driving. Traffic conditions and
driver attention take priority. Do not make sharp steering inputs, artificial
S-curves or performance maneuvers for logging. Naturally occurring straight
roads and gentle left/right curves, with normal lateral control engagement and
few driver overrides, can provide useful support. Low, medium and highway-speed
coverage is useful when it occurs naturally. Several ordinary routes on
different dates and roads are preferable to repeatedly splitting one short
route. Never drive dangerously to improve logging coverage. This increment
does not request or perform new data collection.

## Validation and handoff

The implementation, actual metadata outcome and executed checks are recorded below.
No rollback of historical evidence is needed: all new files are additive.
Required independent review concerns route leakage, privacy, source identity,
causal support and holdout opening. Vehicle application is not authorized.

## Actual metadata outcome

EMPIRICAL_DATASET_V2_WAITING_FOR_NEW_ROUTE_DATA.
One existing V1 route, 95 rlog files, 191 video files counted as filesystem
metadata only; zero new untouched compatible routes. All V1 route members stay
PLANNING_CONTEXT_ONLY. The previously rejected truncated V1 segment is not
reopened or re-admitted. Fresh metadata failure count zero means no fresh-route
metadata failures were encountered; it is not a revalidation of V1 log integrity.

The V1 ordinal-zero log supplies only initData/CarParams and message envelopes
for a logger-start exclusion anchor. No driving numeric body is accessed.
Recorded logger.cc builds init_data once per LoggerState and writes that same
message on each segment transition. This source path is checked against the
exact recorded commit before parsing. Renamed and recompressed V1 copies share
the start identity; identical-byte copies also map through the pinned content
SHA. Appending segments cannot rename a route. Segment lineage and monotonic
ranges remain separate identity evidence.

Policy values were frozen before metadata execution. The unpublished draft
policy commit was amended solely to remove a forbidden-path example in a test;
policy values/source stayed identical. The final policy commit is 121df82a4,
and final metadata resume was repeated after that cleanup.
The first process stopped at Git ownership validation before any receipt or
payload access; a command-scoped safe.directory option resolved it. A preliminary
metadata-only receipt remains preserved. Final source revision ran twice in a
separate private store with identical result:
ea213824ccaefd075bbd29c1fa8ade47ac0494e91c84d6fd8c00732049969d61.
No private output store resides in Git.

No route-disjoint split was instantiated. V2 numeric extraction, crosscheck,
fitting, model selection and holdout opening/evaluation are NOT_RUN.
Numeric coverage is null, not zero. No empirical model or selection/holdout
artifact is fabricated. Full plant readiness remains false.

## Future tool operation

Run from the supported checkout with operator-managed private environment
variables. These variables are supplied locally and never stored in public
receipts:

~~~sh
PYTHONPATH="$PWD" .venv/bin/python -m openpilot.tools.cyber_autotune.empirical_dataset_v2_inventory \
  --private-root "$PRIVATE_LOG_ROOT" --private-store "$NEW_GENERATION_STORE" \
  --v1-store "$V1_STORE" --recorded-source "$RECORDED_SOURCE"
~~~

A changed snapshot/source/policy requires a new generation store; existing
receipts cannot be overwritten. A restart with identical identities recovers
atomic receipts before payload parsing. The final snapshot is checked again.

After at least three untouched metadata-compatible routes and an immutable split
exist, TRAIN/DEVELOPMENT eligibility can be audited locally:

~~~sh
PYTHONPATH="$PWD" .venv/bin/python -m openpilot.tools.cyber_autotune.empirical_route_eligibility \
  --private-root "$PRIVATE_LOG_ROOT" --private-store "$NEW_GENERATION_STORE" \
  --route-id "$OPAQUE_ROUTE_ID" --recorded-source "$RECORDED_SOURCE"
~~~

The auditor never fits or selects models. HOLDOUT numeric auditing is explicitly
denied here; it must be incorporated into a later one-time frozen model
evaluation, after unit/sign/model/metric/support identities are complete.
Metadata compatibility does not establish numeric eligibility or model readiness.

Each segment is hashed before and after numeric extraction, including resumed
receipts. Numeric reads and metric computation repeat exactly twice on eligible
TRAIN/DEVELOPMENT data. Gyro acquisition/publish clock failures only disable gyro
support. Direct wheel speeds and steering rate may be observed; track-width and
lateral-acceleration source/frame evidence remain unavailable, so those optional
yaw checks are blocked. The numeric signal matrix distinguishes observations,
static priors and missing fields; safety/curvature limits stay null.

Common support uses the frozen model's HISTORY=45 (44 previous plus current)
and eight unchanged configurations. No window crosses a timestamp gap, mask,
speed-bin change or segment boundary. The 201-row minimum is unchanged.
Active/no-override durations integrate only contiguous valid publish intervals,
with a 20 ms maximum interval; gaps and unsupported endpoints contribute no time.
This is publish-clock eligibility, not acquisition-time physical validation.

## Preservation and independent review

Historical publication loaders verify exact source and receipt pins for Stage A,
yaw crosschecks, TA-B/SG-A and V1/V2 context. No historical controller/model,
calibration, detector, annotation or registration evidence is modified.
Command bridge representation remains confirmed without an EPS/application claim.
Stage A strict READY failure, yaw unit/frame limitation and unavailable yaw model
remain unchanged.

Independent read-only review found and resolved V1 renamed-copy exclusion,
copy deduplication, command bridge row shape, history indexing, timestamp duration,
gyro producer binding, source-change integrity and publication enum/count checks.
Each behavioral defect has a regression test. Reviewer accessed no private data.
No remaining blocking finding.

TA/SG execution, composition, search, frozen candidate evaluation and production
authority remain forbidden. Reference/calibration blockers, sealed reference
NOT_GENERATED and vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED remain unchanged. This passive eligibility tool is
not a scheduled automation and does not collect logs.

## Validation record

Ubuntu 24.04 / Python 3.12.13 in the prepared repository environment.
No new dependency, submodule, LFS object or native/runtime authority is added.

| Check | Actual method | Result |
| --- | --- | --- |
| Full AutoTune + controls | tools/test_runner.py, one worker, fixed single-thread BLAS environment | 2747 passed in 902.21 s: AutoTune 2605 + controls 142 |
| Empirical focused | pytest test_empirical*.py | 236 passed, including 49 new V2 tests; 9 subtests |
| Privacy / authority / publication focus | pytest AutoTune tests with privacy/authority/publication selection | 308 passed; 140 subtests |
| Lateral replay | unittest card replay and native experiment modules | 16 passed |
| Ruff | existing CyberPilot/AutoTune/control/replay scope | PASS |
| Syntax | compileall applicable modules | PASS |
| Native build | scons -j2 | PASS |
| Publication | check_publication.py --base origin/main | 982 files, 0 findings |
| Repeat/resume | same final private inventory twice, plus unchanged resume | exact receipt SHA match |
| Independent review | read-only source/tests review, no private access | no remaining blocking findings |
| Browser | no UI changes | NOT_APPLICABLE |
| V2 fitting / holdout | no new routes / no route-disjoint split | NOT_RUN |
| Candidate simulation / shadow / vehicle | outside this authorization | NOT_RUN |

One initial full-suite attempt was deliberately interrupted after discovering
the publication test-fixture issue; it is not counted as a passing run. The
final full regression uses the corrected, fixed source tree.
