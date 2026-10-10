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

Implementation and executed checks will be recorded after verification.
No rollback of historical evidence is needed: all new files are additive.
Required independent review concerns route leakage, privacy, source identity,
causal support and holdout opening. Vehicle application is not authorized.
