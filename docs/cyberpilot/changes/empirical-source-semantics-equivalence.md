# Empirical source semantics equivalence

## Identity and purpose

Validation, metadata/source-only additive increment from feature/cyber-autotune
baseline 14adf02f286a8d55ff8a6152b9f50a31a90a1c42. The earlier 178 groups and
66 buckets remain immutable metadata observations, not 178 independently validated
drives. Different full commits can preserve the specific signal-producing code
needed for empirical identification. Similar versions, nearby commits and matching
filenames alone do not establish equivalence.

This increment audits predeclared selected generations, revalidates metadata with
exact source schemas, and defines future untouched holdout admission. It authorizes
no numeric inspection, support calculation, fitting, selection, holdout opening,
TA/SG execution or vehicle authority.

## Original references

Public origin is [ajouatom/openpilot](https://github.com/ajouatom/openpilot).
Exact GitHub commit API identities were matched to recorded commits; local objects
alone are not public-origin attestation.

| Selected primary commit | Public reference | Result |
| --- | --- | --- |
| 18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29 | [exact source](https://github.com/ajouatom/openpilot/tree/18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29) | Scoped equivalent pair member |
| 6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90 | [exact source](https://github.com/ajouatom/openpilot/tree/6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90) | Scoped equivalent pair member |
| a28ba306e4b8e0ea5f84f934fe962ad3d7ba9c7a | [exact source](https://github.com/ajouatom/openpilot/tree/a28ba306e4b8e0ea5f84f934fe962ad3d7ba9c7a) | SOURCE_AUDIT_PARTIAL; unreviewed differences |
| defcfe812a64e0e1646d33b4e712f928428f9ef4 | [exact source](https://github.com/ajouatom/openpilot/tree/defcfe812a64e0e1646d33b4e712f928428f9ef4) | SOURCE_AUDIT_PARTIAL; unreviewed differences |

The fingerprint artifact binds exact repository/commit/path, raw file SHA256,
Python symbol source-slice/AST hashes, schema dependencies, sensor producers and
license-blob hashes. Python comments/formatting use AST normalization. C++,
Cap'n Proto and DBC retain raw bytes, preserving preprocessor constants and token
boundaries. Upstream public source retains its MIT notice; tooling records source
identities rather than replacing production controller code.

Required roles include logger.cc/.h, loggerd.cc/.h, cereal log/car/custom/deprecated
schemas, service selection, card.py, Hyundai controller/limits/helpers/CAN builders,
CarState/interface, generic DBC and sensor producers. Explicit path migrations
resolve Python sensord and car CRC locations without dropping required roles.
Supplemental manifests bind CAN parser/packer/DBC loader, profile/VehicleModel
helpers, Params implementation/keys, checksum helpers, messaging/msgq transport,
clock dependencies and package-lock identities. Native binaries, OS scheduling,
CAN acquisition age and physical hardware remain outside equivalence.

## Changes and expected effect

Additive modules separate frozen triage, fingerprints, dependency closure,
source-bound metadata adapters, restartable private execution and whitelisted
aggregate publication. Existing results/contracts are unchanged.

Triage was sealed before source inspection:
43966d3f7a1416653da32907137c8dd223184af252aab97112b2dd37b6f8dd2f.
Five clean DIFFERENT_SOURCE groups identify four primary generations. The top-three
secondary count/segment/id ranking is sealed but unexecuted: the primary pool has
three candidates. No tertiary bucket proves schema-only failure. Only four
generations/commits were audited, within the ten-generation cap; the other observed
commits were not broadly audited.

### Scoped equivalence

Only 18c07cfa and 6ca11a4a are combined, under
LEGACY_HYUNDAI_SANTA_FE_2022_SIGNAL_CONTENT_AND_LOGICAL_PUBLICATION_ONLY.
They are not globally equivalent controllers or physically attested runtimes.

Exact reviewed differences:

- Car schema removes RadarPoint.radarSource and HUDControl.leadLimiting; retained
  lateral field IDs/types are unchanged.
- DBC loader removes a VW MEB checksum branch; selected Hyundai parsing is unchanged.
- Cruise changes are guarded by a Volkswagen-MEB predicate false for this profile.
- Radar initialization/filtering changes materially; RadarData/liveTracks and
  longitudinal behavior are explicitly outside the equivalence claim.
- Torque override removes a Volkswagen ID4 entry; Santa Fe's resolved entry remains
  unchanged, including substitution-table resolution.
- Params keys remove a UI trajectory option; CustomSteerMax and key-based Params
  implementation remain unchanged.

All differing relevant files bind exact Git diffs and independent source review.
Diff policy fixes --abbrev=8, --no-color, --no-ext-diff, --no-textconv and --unified=3.
Equal supplemental producer/transport/clock files are required before pool admission.
The other two primary commits remain partial. Matching their manifest alone does
not prove complete signal semantics.

### Logger, schema and signal semantics

The reviewed LoggerState creates initData once and reuses serialized metadata when
rotating segments, for rlog and qlog. Restart creates a new logger-start identity;
segment ordinal is not a new route. Adapters bind exact source fingerprints,
schemas and adapter code SHA. Unknown source has no generic fallback.

Source-specific replay read initData, CarParams and message envelopes only. It
revalidated 662 compressed sources against compressed hashes, original logger-start
identity, full CarParams SHA, envelope ranges and message counts. No driving-message
body was opened. Raw identities/timestamps, metadata blobs and paths stay private.

Command source publishes normalized torque from raw apply_torque divided by runtime
STEER_MAX; static profile branches and CustomSteerMax override capability are
separate. Runtime value is pending; no numeric command bridge is retested. Logged
post-CarController representation does not prove EPS acknowledgement.
card.state_update publishes previously retained actuator output before the current
controls_update; logical publish order is not actuator acquisition timing.

The signal matrix retains schema field IDs/types and DBC message/address/signal
context. It selects SAS11, ESP12 and WHL_SPD11, preserving other same-named wheel
signals separately. ESP12 YAW_RATE keeps factor 0.01, offset -40.95 and empty unit.
Source availability does not resolve yaw physical unit/sign/frame. The reviewed
gyro producer converts 8.75 mdps/LSB to rad/s and maps device axes [y, -x, z].
IRQ acquisition timestamp and publish event clock are distinct. This does not
provide an independent IMU-to-vehicle transform. Unreviewed primary classes keep
producer semantics pending.

### Empirical profiles and route reclassification

EMPIRICAL_PLANT_PROFILE_V1 binds relevant fingerprint/control, geometry, torque
tuning, safety/flags and steering fields. Bus configuration and runtime STEER_MAX
are separately source-bound with runtime confirmation pending. Full CarParams
identities are retained. Equal relevant subsets cannot merge differing full
CarParams without an exact reviewed irrelevant-field proof. The admitted pool has
matching full CarParams; no relaxation was used.

Of 18 metadata groups in selected generations:

| Additive source-audited classification | Count |
| --- | ---: |
| IDENTITY_COMPLETE | 5 |
| INCOMPLETE | 12 |
| IDENTITY_AMBIGUOUS | 1 |

Three complete groups share the scoped equivalence class and empirical/full
CarParams profile: TRAIN/DEVELOPMENT candidates only. Two complete groups remain in
partial source classes. No ambiguous group is resolved; the original 77 ambiguous
and 95 incomplete counts are unchanged. Truncation, missing segments/metadata,
clock regression and overlap conflicts cannot be repaired by schema compatibility.

All old non-V1 groups remain ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN. None becomes
UNTOUCHED. V1 remains planning context, excluded from new fitting and holdout.
No numeric split or full route-disjoint split is created.

### Future untouched holdout contract

FUTURE_EMPIRICAL_HOLDOUT_ADMISSION_V1 requires compatible source semantics and
empirical profile, completed source/metadata audit, distinct complete lineage,
required messages, no prior analysis and numeric payload previously unopened.
Whole-route role must be assigned before numeric inspection. Every requirement
must be an explicit boolean; unknown fails closed. Three old routes cannot replace
a future untouched holdout.

Reference/calibration and candidate architecture are separate tracks. All five
reference blockers, sealed reference NOT_GENERATED and NOT_READY /
REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain. TA-B/SG-A tradeoffs,
V1 TRADEOFF_ONLY, V2 REJECTED (37 violations), CURRENT=BASELINE_EXACT and
composition/search/frozen-evaluation restrictions remain unchanged.

## Regression risk and acceptance

Risks include broad equivalence, stale receipts, duplicate admission, numeric
access and accidental holdout promotion. Exact source/diff/schema bindings and
fail-closed APIs address these. No performance threshold or model gate changes.
Rollback removes only this additive increment; historical evidence is unchanged.

Private execution is persistent, per-source sealed, source-hash verified and
atomic/no-overwrite. Publication uses opaque identities and aggregate counts.
Stale adapter/source hashes are rejected. There is no production injection,
CAN/Params write or candidate executor. Independent review specifically checks
dependency closure, DBC duplicate names, source origin, role leakage and holdout
promotion; defects require regression tests.

## Validation method and actual results

Ubuntu 24.04 WSL / prepared Python 3.12 virtual environment. All source and
historical receipts are hash-bound; no dependency/runtime upgrade was performed.

| Check / stage | Command / method | Actual result |
| --- | --- | --- |
| New focused contracts | unittest discover, test_empirical_source*.py | 104 PASS |
| Combined empirical | unittest discover, test_empirical*.py | 399 PASS |
| Full AutoTune + controls | tools/test_runner.py, both test directories, -j 1 | 2,910 PASS: AutoTune 2,768 (+104), controls 142 |
| Lateral replay regression | unittest, both cyber_lateral replay modules | 16 PASS; synthetic regression only |
| Privacy/authority | 15 publication/policy unittest suites | 223 PASS |
| Ruff | CI's full CyberPilot source/test paths | PASS |
| Syntax | compileall for cyber_autotune and tools/cyberpilot | PASS |
| Publication | check_publication.py | 1,022 files, zero findings |
| Native build | PATH includes .venv/bin; scons -j2 | PASS |
| Exact private resume | 662 source hashes and sealed source-specific caches | identical receipts |
| Aggregate repeat | two derivations and published receipts, canonical JSON bytes | exact equality |
| Independent review | 332 exact public Git blob bindings; contracts and sealed artifacts | PASS |
| Browser / simulation / shadow / vehicle | no UI, no new plant or vehicle execution | NOT_RUN / not applicable |

The publication test's synthetic private-home literal was removed after scan
detection. A later pre-publication review removed literal approved-root paths from
the executable code too: CLI roots are explicit and checked against the unchanged
hashed two-root allowlist before private reads. Three regression tests cover this.
The intermediate full run was intentionally interrupted for that privacy hardening;
the final run holds HEAD/source fixed. Neither change affects adapter semantics,
source receipts or route classification.

Only initData/CarParams/envelopes are revalidated. Resume verifies source hashes
and existing exact adapter bindings; it is not a claim of two independent raw
metadata parses. Public aggregate repeatability uses frozen canonical JSON bytes
(regex tuples serialize as arrays). No driving payload is accessed.

For private reuse, supply --store, --historical-store, --source-repo, --commit and
two explicit --root arguments. The private store and receipt blobs stay outside
the repository. Missing/unknown roots, source drift, schema drift and immutable
receipt conflicts fail closed. Numeric execution remains absent.

## Handoff

SOURCE_SEMANTICS_EQUIVALENCE_AUDIT_COMPLETE.
SOURCE_AUDITED_TRAIN_DEV_POOL_AVAILABLE: three old metadata candidates.
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED.

This is not model readiness or numeric authorization. Coverage/support, command
numeric validation, yaw/gyro crosschecks, fitting/selection/model metrics and holdout
opening remain null/NOT_RUN. A later increment needs explicit numeric authorization
and a compatible future untouched holdout. Current source is not inserted as an
existing dataset member; a future route's exact commit/profile must pass admission
again.
