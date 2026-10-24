# Curvature/yaw real source audit and negative report contract

## Identity and purpose

- Area: Cyber AutoTune / Validation; implemented offline audit; software gates passed, real evidence blocked.
- Purpose: determine whether existing local evidence can supply the independent
  desired path, lane-center and lane edges required by frozen three-arm comparison.
- Branch / starting HEAD: feature/cyber-autotune,
  f71e4d7bfa713ca39a604b4d04551377fb2efe6b. Fetch and fast-forward pull confirmed
  this exact HEAD and clean working tree before changes.
- Scope: enumerated source implementations, historical local development manifests,
  pixel diagnostics and D3Y aggregate sidecars. Raw log/video contents, protected
  roles, vehicle qualification, control changes and candidate creation are excluded.
- Result: BLOCKED / REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE. This is a
  scoped negative capability finding, not proof that no possible independent
  source exists anywhere or that every historical log field was exhaustively decoded.

## Original references and audited call paths

Source: https://github.com/rownlvh8875-coder/CyberPilot at the starting HEAD,
MIT root license. No third-party algorithm is adapted. opendbc:
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. No model/dependency revision changes.

| Source | Traced capability | Why strict road reference remains unavailable |
| --- | --- | --- |
| controlsd._cyber_lateral_model_observations -> cyber_lateral/path_observer.py | modelV2.position/laneLines/roadEdges -> model-relative path diagnostic | Model path and model lanes share the model source; output is not independent truth. |
| pixel_lane_reference.py::detect_qcamera_lane_pair | caller RGB -> fixed lower-ROI pixel lane pair | Detector takes no model input, but returns px at a scanline, not aligned road geometry in metres or an independent desired path. |
| pixel_action_horizon_consistency.py and historical pixel sidecars | projected model path/calibration and pixel scalars -> descriptive agreement | Historical frame selection uses model/action/control/calibration metadata. Selection precedes image decode but does not independently freeze metric road truth; agreement cannot establish it. |
| cyber_lateral_native_experiment.py::load_development_manifest | development role, route parent and rlog hash -> replay inputs | Six development entries declare file identity, not measured road geometry. Retrospective manifests bind files and cameras, not lane/desired-path truth. |
| replay_admission.py / observation and replay_input.py | granted snapshot -> sealed bytes; CP/cache/state metadata | Initial-state observations concern CP/cache equivalence. They do not establish lateral pose against lane boundaries or reconstruct absent settings. |
| GPS/pose and D3Y documented position chain | orientation-derived local pose -> descriptive motion/calibration | Neither pose nor GPS supplies lane-center/edges/desired path. No surveyed registration or annotation contract was found in the inspected sources. |
| plant_calibration.py and D3Y aggregate admission | frozen historical model -> descriptive validation | PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT remains explicit; prospective calibration protocol cannot admit historical data. |

The seven inspected historical sidecars are represented only by aggregate artifact
byte sizes and SHA-256 values in the scope file. Private filenames, routes, absolute
paths, raw samples, coefficients and images remain local. Selected byte identities
were recorded before this audit's sidecar semantic inspection and rechecked.
This does **not** change historical semantic-open timing or retroactively create a
reference manifest freeze. Unknown leakage/order facts remain null and blocked.

Additional inspected diagnostics (action_geometry_alignment.py,
tracking_geometry_separation.py, virtual_path_recenter.py and path_tracking_timeline.py)
consume model-derived or caller-owned descriptive geometry, and provide no
independent acquisition/admission contract. Virtual recenter outputs are candidate
geometry, so they cannot supply reference truth. cereal/log.capnp::GpsLocationData
contains location/velocity/accuracy, not lane geometry; NavInstruction.Lane has turn
directions, and NavRoute has route coordinates, neither metric lane boundaries.

Aggregate artifact identities are reproducible from the public scope JSON:
PIXEL_DIAGNOSTIC selects historical_artifacts keys pixel_probe/pixel_selection;
RECORDED_REPLAY selects development_manifest/retrospective_metadata/
retrospective_content. Hash the compact sorted UTF-8 JSON mapping those keys to
their complete size_bytes/sha256 objects, without trailing LF. Other record
artifact identities are individual entries documented in the table above.

A metadata-only inventory of the two existing D-drive log roots records filenames,
sizes and modification times privately. Its digest and aggregate count are public;
it opens no raw payload. This inventory establishes inspected file scope, not
semantic absence of a field. The negative conclusion comes from traced producer
capabilities and reviewed manifest schemas. Existing protected/retrospective roles
are not converted into development or independent-reference grants.

## Real arm definitions and blockers

Intended semantic definitions for a future exact comparison:

- UPSTREAM_BASELINE: reviewed upstream native torque controller at a pinned upstream
  source/submodule HEAD, with a reviewed exact vehicle CP/profile/configuration and
  frozen common inputs, reset, plant, metric and environment.
- CYBER_CURRENT: the presently implemented Cyber controller path and exact active
  configuration/profile at the pinned Cyber HEAD, with the same common basis.
- CYBER_CANDIDATE: a separately reviewed, bounded offline change to that current
  path, with exact source/configuration/profile/request identities frozen before
  reference semantic access or comparison.

These are semantic requirements, **not executable declarations**. origin/main is
c8fb906815530460ed156f14e09e1f312bb0f851. Its latcontrol_torque.py and the audited
current file both hash to
9489bfd923246906ef543a1c305bf7a7fe534ee9754c94d8195ae98bb3a1f2cd.
controlsd._update_lateral_control delegates to the native controller;
Cyber diagnostics observe its result. curvature_yaw_native_worker directly invokes
LatControlTorque with linear conversion; it does not execute Cyber A3 preprocessing.

Consequently the current native core equals the baseline. No reviewed baseline
CP/profile/request freeze is available for this real experiment, and no distinct
feedback-bound Cyber candidate implementation is frozen. Changing CP tuning merely
to satisfy distinct identity would confound controller comparison and is rejected.
An identical baseline/current pair cannot satisfy the existing strict distinct-arm
gate; that gate is preserved.

Historical A0/A3 native card replay is a separate path: build_a3_messages transforms
recorded carControl using recorded applied output before replay. It is not a
closed-loop candidate in the current native worker. A3 performance rejection
(0/6) remains in force and is not interpreted as improvement or promotion.

## Changes, design and execution plan

Added curvature_yaw_source_audit.py: pure immutable metadata inventory, canonical
SHA binding, per-source negative findings and a report encoder. It opens no source
file, constructs no geometry, runs no worker and offers no acceptance path.
All authority fields and BLOCKED status use init=False frozen defaults.

Added test_curvature_yaw_source_audit.py: synthetic-only TDD for source capabilities,
incomplete/duplicate inventory, digest drift, tri-state unknown/leakage/open order,
role relabeling, external claims, malformed inputs, immutable authority, report
integrity and rejection by the real sealed reference admission.

Added scope/inventory/result JSON snapshots alongside this record. The scope
contains exact public producer file hashes and historical aggregate artifact
hashes. These identities substantiate the audit inputs; they do not authenticate
reviewer claims, qualify physical truth or replace a ReferenceEvidenceGrant.
Scope and review digests use compact sorted JSON without the file's trailing LF.

Execution: audit existing code and sidecars -> write/run failing tests -> implement
the minimal negative contract -> focused regression -> full AutoTune regression ->
Ruff/syntax/publication/whitespace checks -> native build -> review -> commit/push.
No existing comparator, threshold, reference admission, controller or runtime path
is modified. Alternative rejected: estimate road geometry from pixel/GPS/model
inputs or add a sealed producer without a defensible real source.

## Regression risk and acceptance

Risk: a caller can misclassify a source; inventory hashes are consistency bindings,
not authentication or semantic inspection. The report says claims_authenticated=false.
A new external geometry record receives SEPARATE_PRODUCER_REVIEW and suppresses
the scoped-unavailability conclusion. Empty/incomplete inventories also cannot
claim scoped unavailability. This negative contract never authorizes a producer.

No numeric acceptance limits or tuning constants are added. The record-count
bound covers one record per six required source families plus one external claim;
it is an infrastructure/schema bound, not a performance threshold.
State/reset/actuator delay and vehicle variants: not applicable to this stateless,
vehicle-agnostic audit. Existing comparison and calibration policies remain frozen.
Rollback: revert only the added module, synthetic tests and audit artifacts.
Review/promotion authority: software review only; no vehicle permission.

## Validation method and actual results

Ubuntu 24.04 WSL, existing .venv Python 3.12.13 and pinned submodules.

| Check / stage | Method and identity | Result and limits |
| --- | --- | --- |
| Test-first | New module absent | 11 test errors, all ModuleNotFoundError for the missing API; no production code existed. |
| Encoder hardening RED | Forged/private report content | Five failing subcases before canonical report revalidation; fixed without weakening assertions. |
| Focused source audit | python -m unittest new test module | 13/13 PASS after implementation; synthetic only. |
| Focused evidence regression | tools/test_runner.py -j2 on ten test modules: audit, evidence coordinator, three arm, comparison bridge, closed loop, native runner, plant, comparator, pixel detector, calibration | PASS: 83/83 in 7.56 s, exit 0; synthetic evidence only |
| Full AutoTune regression | .venv/bin/python tools/test_runner.py -j2 openpilot/tools/cyber_autotune/tests | PASS: 873/873 in 221.83 s; all tests passed, no skips/failures |
| Ruff / py_compile / whitespace | .venv/bin/ruff check and .venv/bin/python -m py_compile added Python files / git diff --check | PASS, exit 0; final staged check passed |
| Publication/privacy | .venv/bin/python tools/cyberpilot/check_publication.py --repo . --base origin/main | PASS: 358 changed files / 0 findings, exit 0; final staged check passed |
| SCons | export PATH="$PWD/.venv/bin:$PATH"; .venv/bin/scons -j2 | PASS: 100%, exit 0; existing non-fatal PWD warning |
| Actual independent reference / real 3-arm performance | No admissible real source or frozen real arm declarations | BLOCKED; zero real-data comparison runs |
| Vehicle replay/simulation/shadow qualification | Independent/calibration/arm gates unresolved | NOT_RUN |

Final snapshot reproduction recomputed scope/review/inventory hashes, both
aggregate artifact recipes, all 16 public source hashes and exact result JSON.
Read-only review found no Critical/Important issue; both Minor documentation
findings (entry-point name and aggregate identity recipe) were corrected.
The first focused invocation requested a nonexistent reference-input test module;
it failed import, and was replaced by the actual evidence-coordinator test module
that owns those tests. The final ten-module focused run passed without errors.
Private verification stdout and raw metadata inventory remain outside Git.

## Handoff and evidence needed

No independent road geometry was generated or admitted. To proceed with a real
producer, require raw source identity/role, an independent desired path and metric
lane-center/edges, reviewed coordinate frame/sign/units and station/time alignment,
vehicle half-width provenance, uncertainty/coverage review, producer source SHA,
manifest frozen before semantic access, output file/semantic evidence SHA and
verified absence of candidate/model/planner leakage. Pixel-based evidence may be
reviewed on its merits with independent calibration/annotation; surveyed truth is
not categorically the only possible basis. Independence and adequacy must be shown.

Existing data may still be useful if a separately reviewed independent annotation
or geometry source is found; new driving collection is not required by this change.
Prospective D3Y qualification remains a distinct blocker and protocol.

Vehicle decision remains
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Commit/push identity will be supplied in the final handoff.
