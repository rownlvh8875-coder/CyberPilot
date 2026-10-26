# Additional private-root empirical metadata inventory

## Identity and purpose

Cyber Validation / AutoTune, metadata inventory only.
Baseline feature/cyber-autotune: 9d3df6222afcd954fe9ff91d59cb41e3e62113fa.
The earlier WAITING_FOR_NEW_ROUTE_DATA receipt described only the first approved
storage root. It is preserved exactly, not generalized to other storage.
The user now explicitly authorizes a second root. Root-policy V2 records two
opaque root identities and their Windows/WSL alias hashes: each alias pair
represents one storage root. Exact local paths remain private.

The increment inventories ordinary subfolders inside those exact roots. No
parent, whole-disk, home, cloud, network or archive traversal is permitted.
No driving numeric body, image/video, GPS, model/path, gyro, yaw, steering,
torque or wheel-speed values are accessed. Numeric coverage remains null.
No fitting, yaw crosscheck, support-row computation or holdout opening occurs.

## Original references

Existing MIT CyberPilot implementation at the baseline commit:
empirical_dataset_v2_policy.py, empirical_dataset_v2_inventory.py and
empirical_dataset_v2_publication.py, reused read-only.
Recorded source:
https://github.com/ajouatom/openpilot/tree/5a970f1ad25d9f07d055955d7a7c14603b6b7813
including cereal/log.capnp, car.capnp, Hyundai values.py/carcontroller.py and
openpilot/system/loggerd/logger.cc. Exact source-contract blobs and logger
blob are checked before metadata parsing. Existing submodule gitlinks,
dependencies, runtime controllers and source attribution remain unchanged.

LoggerState in that recorded source constructs init_data once and reuses it
across segment rotation. Other recorded commits require their own logger/schema
source audit; metadata parse success does not validate their signal semantics.

## Changes and expected effect

New additive modules:
- empirical_additional_root_policy.py: versioned allowlist, compatibility and
  conservative metadata split rules.
- empirical_cross_root_inventory.py: bounded discovery, metadata-only parse,
  cross-root deduplication, generation buckets, immutable private receipts.
- empirical_export_metadata.py: separately bound metadata receipts for exported
  rlog filenames, combined without overwriting canonical inventory.
- empirical_metadata_copy_variants.py: hash-only matching of copied-log filename
  layouts; unmatched files remain unresolved, never new/untouched routes.
- empirical_cross_root_publication.py: explicit aggregate/redacted projection
  and pinned public receipts.

No production integration, state, actuator delay or reset ownership changes.
Inventory state belongs only to private immutable filesystem/binding/segment
receipts. Source changes or stale/conflicting receipts fail closed. A repeat
revalidates selected compressed source bytes and the final filesystem snapshot.
No existing V2, Stage A, yaw, TA/SG, candidate, detector, annotation, calibration
or pixel-registration artifact is rewritten.

The canonical scanner opens rlog.zst/qlog.zst content. A separate additive
reader covers filenames ending in rlog.zst, including route/segment exports.
Only the same initData/CarParams/envelope allowlist is used. Unstructured export
names retain unknown segment ordinal; filenames never establish route identity.
Other files are counted as filesystem metadata. Neither reader opens archives,
images or videos.
The maximum directory depth is 32, a bounded traversal guard fixed before
log metadata execution. Symlink aliases and nonregular sources are rejected.
When qlog and rlog coexist in one segment directory, qlog is the preferred
metadata envelope stream; the alternative is explicitly counted as not parsed.
No qlog sample-rate or numeric-continuity inference is made.

## Route identity, copies and generations

Route group identity binds source commit, fingerprint, full serialized CarParams
SHA, software/profile hash, OS and logger-start identity. A separate identity
receipt binds segment lineages and monotonic envelope ranges. Names, folder dates
and filesystem access times never establish independence or untouched status.

Identical metadata, renamed/recompressed copies, equal logger starts and
overlapping qlog/rlog alternatives at the same ordinal do not create new routes.
Appended segments stay with the same logger-start group. Conflicting overlaps,
lineage/start conflicts, dirty metadata and mixed generations remain ambiguous.
A failed member makes its matching route lineage incomplete. Missing mandatory
metadata is retained as a failure, never silently discarded.
Unknown-schema parsing failures are not proof of physical log corruption.

Generation buckets keep commits, OS, vehicle, CarParams and control profiles
separate. Mixed metadata has an explicit ambiguous bucket preserving all observed
generation identities. Static STEER_MAX source/override knowledge is distinguished
from runtime STEER_MAX; runtime value is null without direct admitted evidence.
No raw-to-normalized numeric bridge is checked in this increment.

## Untouched and split readiness

V1's entire route remains V1_PLANNING_CONTEXT_ONLY, including copied, renamed,
recompressed or appended members. Its exact previous inventory/logger-start
exclusion anchor is reused without reopening driving numeric payloads.
Other routes default to ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN. The filesystem and
metadata cannot prove absence of earlier analysis in another project.
Unknown history cannot become untouched or a HOLDOUT candidate.

A technical minimum of three proven untouched compatible whole routes permits
one TRAIN, one DEVELOPMENT and one HOLDOUT role. Larger sets use the existing
frozen hash ordering and 60/20/20 allocation with at least one DEV and HOLDOUT.
Quality/result cannot change roles; one route cannot cross roles. The frozen
201 support minimum and ARX1/FIR25 delay policy remain unchanged and are not run.
A metadata split never opens numeric payloads or authorizes a model experiment.

## Regression risks and acceptance

Primary risks: copied data counted as new evidence; schema/source confusion;
clock/lineage collisions; false untouched history; private-field publication;
stale cache; crossing roots through aliases.
Acceptance is metadata integrity and disclosed uncertainty, not model readiness.
Existing pinned evidence is the rollback/context baseline; new artifacts can be
ignored without altering it. No vehicle promotion authority is granted.

Independent review initially found clock regression, lineage conflicts, dirty
duplicate hiding and mixed-generation bucket loss. Each was reproduced with a
failing test and fixed before metadata execution. Later projection review found
malformed-source and nested-field publication paths; regression tests now enforce
redaction/whitelists. Reviewer never accessed private roots, receipts or logs.

## Validation method and actual results

Ubuntu 24.04 / Python 3.12.13, existing virtual environment and dependencies.
Actual metadata outcome:

| Item | Count/state |
| --- | --- |
| Filesystem files, both roots | 15,320 |
| Canonical rlog / qlog files | 4,694 / 908 |
| Export rlog files | 15 |
| Copy-layout files, exact existing compressed-byte matches | 4 / 4 |
| Selected metadata streams | 5,549 |
| Alternative canonical streams explicitly not parsed | 68 |
| Selected metadata parsing failures | 213 |
| Distinct metadata segments after deduplication | 5,321 |
| Repeated selected metadata members | 15 |
| Logger-start metadata route groups | 178 |
| Existing V1 route group excluded | 1 |
| Different-source route groups without identity/incomplete blocker | 5 |
| Identity ambiguous / metadata incomplete route groups | 77 / 95 |
| Source/OS/CarParams/profile identity buckets | 66 |
| Observed source commits | 45 |
| New compatible V1-generation routes | 0 |
| Compatible untouched routes | 0 |
| Other routes with unknown prior-analysis history | 177 |
| Route-disjoint metadata split | UNAVAILABLE |

The 15 exports add repeated metadata, not additional route groups. Four copy-layout
files are exact compressed-byte copies of already inventoried logs; they are also
excluded from new-route counts. The 213 parsing failures are file outcomes, not
213 extra routes; failures whose lineage matches a route make that route incomplete.
Other-source logger-start semantics are not independently source-audited yet:
178 means metadata groups, not 178 proven independent drives.

Outcome: ADDITIONAL_ROUTES_FOUND_DIFFERENT_GENERATION.
Next: EMPIRICAL_DATASET_V2_NEW_SOURCE_AUDIT_REQUIRED.
All 177 non-V1 groups record prior-analysis history UNKNOWN. No homogeneous
compatible untouched set is admitted, so no metadata split, numeric split or
model artifact is generated. Earlier first-root WAITING readiness remains intact.

Empirical focused: 295 tests plus 29 subtests PASS. Lateral replay: 16 PASS.
Ruff, syntax, initial publication/privacy/authority checks and SCons PASS.
Final source-stable full regression: 2,806 PASS (AutoTune 2,664 + controls 142),
including 59 new tests over the 2,605 AutoTune checkpoint. Final lateral replay:
16 PASS. Privacy/authority/publication-focused: 322 tests plus 149 subtests PASS.
Publication scan: 998 files, zero findings. Ruff, syntax and diff checks PASS.
Final SCons full targets PASS with the existing virtual environment on PATH;
an earlier invocation lacked capnpc/cythonize on PATH and changed no dependencies.
Independent source/test/public-evidence reviews PASS. No existing file is modified
relative to the checkpoint; all changes are additive.

One intermediate full run had two worker failures because HEAD changed between
repeat invocations during local commits. The traces show the different commit
identities; the same two tests passed with HEAD held fixed. No historical worker
or criterion was changed. The complete source-stable suite is rerun before push.
Browser: NOT_APPLICABLE, no UI.
Simulation/shadow/vehicle: NOT_RUN, outside metadata-only authority.

## Handoff

Public receipts pin the private combined inventory
e4c796ef3211e8c0d7be1094e80e8e4845ba255398764992b1da5db640e46c2b.
The canonical and export parent receipts are preserved. Per-segment sealed caches
are revalidated against current compressed source hashes and filesystem snapshots;
stale source, binding or parent identity is rejected. Copy-layout V2 was repeated
with exact receipt 659658bc57ca31a568c4e3fd043a5180556f18b7cc98a9fe7d89d42f53e025c6.
Aggregate derivation repeated exactly and all four public receipt pins verified.
An independent combined-inventory repeat completed with exactly the same
e4c796ef3211e8c0d7be1094e80e8e4845ba255398764992b1da5db640e46c2b receipt.
It revalidated the original compressed files, immutable segment caches, parent
bindings and filesystem snapshots, not just the aggregate JSON. Additional source generations require a separate source
audit; compatible routes still require prior-analysis provenance and a separately
authorized numeric experiment. Metadata inventory alone cannot admit a plant.

TA-B and SG-A tradeoff verdicts, V1/V2 historical verdicts, composition prohibition,
candidate search/frozen evaluation prohibition and all five calibration/reference
blockers remain unchanged. Sealed reference remains NOT_GENERATED. Vehicle remains
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Private CLI invocation (operator supplies paths, never commit their values):

~~~sh
PYTHONPATH="$PWD" .venv/bin/python -m openpilot.tools.cyber_autotune.empirical_cross_root_inventory \
  --private-root "$EXISTING_LOG_ROOT" --private-root "$ADDITIONAL_LOG_ROOT" \
  --private-store "$NEW_PRIVATE_METADATA_STORE" \
  --recorded-source "$RECORDED_SOURCE" --previous-store "$PREVIOUS_PRIVATE_V2_STORE"
~~~

The exported-log supplement is frozen before its own metadata execution and
preserves the initial canonical receipt. Its combined derivative binds both
parent receipt hashes and repeats grouping against the exact V1 exclusion anchor.
Copy-layout suffixes with route/segment prefixes are included in a separately
versioned V2 hash-only receipt. The preliminary bare-filename V1 receipt remains
private historical evidence and is not substituted for V2.
Canonical cached metadata is reused only after compressed source hash and parent
binding verification; an unknown or stale parent fails closed. No signal values
are inferred from export filenames.

~~~sh
PYTHONPATH="$PWD" .venv/bin/python -m openpilot.tools.cyber_autotune.empirical_export_metadata \
  --private-root "$EXISTING_LOG_ROOT" --private-root "$ADDITIONAL_LOG_ROOT" \
  --private-store "$NEW_PRIVATE_METADATA_STORE" \
  --recorded-source "$RECORDED_SOURCE" --previous-store "$PREVIOUS_PRIVATE_V2_STORE"
# Once canonical inventory is complete, repeat the command with --combine.
~~~
