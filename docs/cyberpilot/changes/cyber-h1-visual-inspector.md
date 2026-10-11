# Offline single-arm H1 visual inspector

## Identity and purpose

Cyber Validation / UI; CYBER_H1_VISUAL_INSPECTOR_V1. Implemented as additive
modules on feature/cyber-autotune, baseline
ed3f673b3d4cb2f30839d2b4a3dc8914899f537a. Final checks are recorded below.
The operator can explore exactly the existing 800-row driver_events synthetic
H1 trace: UPSTREAM_BASELINE_CLOSED_LOOP, SG_DISABLED, 100 Hz, eight seconds.
There are no CURRENT or CANDIDATE traces. Comparison is disabled with
PAIRED_MULTI_ARM_H1_TRACES_NOT_AVAILABLE.

This is T1_DESCRIPTIVE_COUNTERFACTUAL, NOT VEHICLE QUALIFIED and NOT A PHYSICAL
EPS MODEL. Desired curvature is controller intent, not an independent reference.
Applied torque is the descriptive plant's delayed command, not EPS acknowledgement.

## Original references

Source: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Immutable inputs are cyber_lateral_h1_contract/producer/inspector/publication,
the five H1 aggregate receipts, CYBER_VISUAL_ADAPTER_CONTRACT_V1 and
CYBER_SIMULATION_FIDELITY_CONTRACT_V1. Their exact receipt digests are in the new
visual policy. Existing native core, plant, opendbc and cereal are neither edited
nor executed by conversion/server. Submodule gitlinks remain unchanged.
Repository MIT attribution remains applicable.

The UI, SVG rendering, HTTP routing and assets are independently authored.
No Carrot simulator HTML/JS/CSS or plant coefficients are copied.
No external dependency, CDN, font, map, road, lane or image is used.

Call path: explicit external sealed H1 package → exact source validation →
pure row mapping → immutable pages/catalog → verified in-memory HTTP view →
same-origin browser rendering. Public aggregates cannot substitute for full rows.

## Changes and expected effect

New cyber_h1_visual_adapter and cyber_h1_visual_catalog modules copy each row
without interpolation, smoothing, trimming, resampling, missing-value fill or
pose reconstruction. The policy binds source/schema/config/experiment identity,
all row/snapshot digests, mapping and adapter/catalog source digests. Each frame
retains row identity and consumed-input snapshot digest. Exactly 800 rows become
800 frames in eight pages of 100. Source drift, missing rows, reshaped pages,
changed values, reordered rows and conflicting immutable files fail closed.

The source experiment clock is relative and deterministic: capture = k × 10 ms,
decision = capture + one logical ns, completion = capture + 10 ms. The one ns
encodes ordering, not measured latency. INPUT and COMMAND belong to sample k;
applied torque, curvature, yaw, heading and pose belong to completion k+1.
Charts use capture, decision and completion as separate x coordinates and expose
PRE-STEP / COMMAND / POST-STEP labels. Pose copies the completion state and uses
metres with equal axis scale.

Six unavailable fields remain null: requested pre-limit torque, pre-limit torque,
torqueOutputCan, measured steering angle/rate and driver torque. Every field keeps
its exact reason and provenance. carState/carControl/carOutput message health and
source-message times stay null. Synthetic safety/curvature flags are labelled
scenario context; normalized rail state is not physical EPS saturation.

External output is atomic, immutable, no-overwrite and symlink-free. A manifest
is written last; an interrupted store cannot load until complete. Exact reruns
can complete missing pages; stale .atomic files and changed physical JSON bytes
are rejected. Read-only catalog entries contain no private paths. Page digests,
row counts and the complete pinned frame digest are revalidated at server start.

New cyber_h1_visual_server exposes only GET/HEAD at root, catalog, run metadata,
bounded frames, individual frame and health. Other methods receive 405, unknown
resources 404 and invalid paths/queries 400. Bind/Host/Origin are loopback-only,
with no CORS, upload, shell, optimizer, controller editing or device endpoint.
CSP permits only same-origin scripts/styles/fetches; nosniff and no-referrer are
set. A verified immutable in-memory view is served until manual shutdown.

Self-contained static/cyber_h1_visual HTML/CSS/JS provides playback, stepping,
frame/time scrubber, event jumps, four playback speeds, synchronized curvature
and torque charts, descriptive pose/heading, state, availability and evidence.
Evidence banners remain visible. Nulls are displayed as unavailable with reasons,
never as zero. No signal or candidate comparison is invented.

Manual commands in the configured native environment:

    python -m openpilot.tools.cyber_autotune.cyber_h1_visual_adapter --source-store <explicit-external-H1-store>/repeat-1 --output-store <explicit-external-visual-store>
    python -m openpilot.tools.cyber_autotune.cyber_h1_visual_server --store <explicit-external-visual-store> --host 127.0.0.1 --port 0

Use the printed loopback URL. Stop the foreground process with Ctrl-C.
No background watcher, remote tunnel or cloud service is installed.

## Regression risk and acceptance

Acceptance is exact input/frame integrity, timing honesty, deterministic
conversion and actual browser usability. It is not controller, model, physical
plant, stability or vehicle acceptance. Risks are phase confusion, fabricated
nulls, source/page drift, false comparisons and accidental external access.
Tests reject each boundary. Rollback removes only new modules/assets/receipts/docs.

Independent review reproduced and corrected resealed frame-value/metadata drift,
page repartitioning, physical byte resume drift and server/static source drift.
Further regressions cover interrupted stores, atomic resume, Origin/Host, bounds
and symlinks. No historical files, native output or production source are changed.
Publication permits aggregate synthetic identities and counts only; full source
rows, frames, predictions and private paths remain outside the repository.

## Validation method and actual results

| Check | Method / actual result |
| --- | --- |
| Full source conversion / exact resume | Two executions, 800 frames / eight 100-frame pages; all 12 output files byte-identical; input and output bytes unchanged after browser use |
| Actual HTTP browser | Codex in-app browser on 127.0.0.1; first0/middle400/final799, scrubber, play/pause, four speeds, step and event jump PASS |
| Rendering / integrity | Three curvature paths, three torque paths, one pose path/marker; six null cards and all message-health null/reasons; integer ns ordering visible |
| Browser errors / shutdown | JS0, network0, external0, console warnings0; foreground server stopped and both tested ports closed |
| Focused adapter / server / publication | 39 + 8 = 47 PASS |
| Full AutoTune | 3,385 PASS in 1,389.75 s (test_runner.py, one worker) |
| Controls / lateral replay | 142 PASS / 16 PASS |
| Ruff / syntax / publication / diff / SCons | PASS; publication files1,170 / findings0; new Python formatting, compileall and JS syntax PASS |
| Independent review | PASS, no remaining implementation/publication findings; byte and identity links independently reconciled |

No physical shadow/vehicle stage was run; it is outside authorization. No new
controller, candidate, plant fitting or model result is produced. The only source
experiment remains the historical baseline H1 trace. Current-source claims are
bound by policy/source digests, not by unverified branch labels. Server startup
also verifies the fixed public server/static contract pin, rejecting jointly
changed local contract and assets.

Actual browser testing found and fixed delayed number-input refresh; the final
input handler updates immediately. Timing-panel integer strings preserve the
logical +1ns decision ordinal. All browser checks were repeated against the final
source-bound server after these changes. Earlier local execution versions were
retained rather than overwritten.

Commit/push and exact latest-HEAD CI are delivery gates, checked after local
validation. Their final commit/run references are provided in the handoff.

## Handoff

CYBER_H1_VISUAL_FRAME_ADAPTER_IMPLEMENTED and
CYBER_H1_SINGLE_ARM_VIEWER_IMPLEMENTED describe available T1 fields only.
VISUAL_FRAME_CONVERSION_READY_FOR_AVAILABLE_T1_FIELDS coexists with
VISUAL_DATA_COMPLETENESS_PARTIAL and
MULTI_ARM_COMPARISON_BLOCKED_NO_PAIRED_TRACES.

NO PRODUCTION OBSERVER; NO VEHICLE AUTHORITY; NO HOLDOUT OPENING;
NO CANDIDATE SEARCH; NO TA/SG COMPOSITION. Actual holdout opener/journal remain
NOT_IMPLEMENTED, CLOSED, opening_count 0. No T2/T3 evidence is generated.

Preserved: CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED,
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, CLOSED_MISSING_ADMISSIBLE_MODEL,
HOLDOUT_OPENING_CLOSED, FUTURE_UNTOUCHED_HOLDOUT_REQUIRED,
STAGE_B_SIGNAL_ADMISSION_BLOCKED, TA_STANDALONE_TRADEOFF_ONLY,
SG_CLOSED_LOOP_TRADEOFF_ONLY, COMPOSITION_NOT_RECOMMENDED,
COMPOSITION_NOT_AUTHORIZED, SEARCH_NOT_AUTHORIZED,
FROZEN_EVALUATION_NOT_AUTHORIZED; historical CURRENT=BASELINE_EXACT,
V1=TRADEOFF_ONLY, V2=REJECTED (37 violations).

CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE remain. Sealed reference NOT_GENERATED;
vehicle NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
