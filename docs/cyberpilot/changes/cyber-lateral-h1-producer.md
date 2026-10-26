# Offline Cyber lateral H1 producer

## Identity and purpose

CYBER_LATERAL_H1_PRODUCER_IMPLEMENTED adds a detached observer to the existing
baseline-only driver_events descriptive closed loop. The experiment remains
unchanged: 100 Hz, 8 seconds, 800 rows, native baseline core, SG_DISABLED.
No TA/SG candidate, composition or search is executed. The simulator reuse audit
and CYBER_LATERAL_OBSERVABILITY_CONTRACT_V1 are immutable inputs.

The synthetic trace is T1_DESCRIPTIVE_COUNTERFACTUAL. Desired curvature is
controller intent, never an independent reference. Actual curvature is reconstructed
from the same arm's pre-step descriptive plant state. This is no physical vehicle
measurement, actuator acknowledgement or stability qualification.

## Changes and source binding

New pure contract, producer, publication and aggregate inspector modules accompany
an explicit offline experiment wrapper. Source identity binds the producer,
wrapper, native core, source vehicle profile, existing experiment, plant and reset
policy. Config identity includes scenario inputs, native identity, disabled
governor, plant config, timebase and policy. No existing source or evidence changes.

Each consumed-input snapshot contains exactly the native input and its synthetic
source time/service-health context. Its snapshot digest excludes outputs. The separate native_input_sha256 matches
the existing experiment's native input digest. A separate complete-row digest binds
outputs, provenance, config, events and timing. Rows retain distinct stage names:
native returned controller-limited/pre-governor torque, disabled-governor
post/final torque and descriptive delayed applied torque.

Requested pre-limit intent, pre-limit torque, raw CAN command, measured steering
angle/rate and driver torque are unavailable and null. Native post-limit output
cannot substitute for intent. Safety/curvature-limit flags are explicit synthetic
scenario inputs, not independently observed limiter telemetry. Rail occupancy is
normalized command magnitude, not EPS saturation. The absent message bus means
source-message timestamps and updated/alive/freqOk/valid are null with reasons.

## Timing, lifecycle and persistence

The deterministic clock uses capture = sample index × 10 ms, decision = capture
+ 1 logical ns, completion = capture + 10 ms. The 1 ns ordinal expresses ordering,
not computation latency or physical delay. Current consumed curvature precedes
decision; applied torque and plant curvature/yaw/heading/pose belong to completion.
Next capture is at least previous decision. No wall-clock identity is used.

Exact schemas reject missing/extra fields, digest/source/config drift, missing or
duplicate rows, epoch reuse, sequence gaps, invented values and inconsistent
intervention edges. New epochs restart loop/config sequence at one; config changes
require the next sequence and CONFIG_CHANGE. Ordinary, inactive, pressed, release,
reengagement and scenario-boundary records are present in the actual execution.
Synthetic tests also cover epoch and config transitions.

The wrapper persists policy/schema before execution, verifies that saved policy
still matches the execution, then runs two observed experiments and the original
unobserved run_arm. Observer records are detached copies; they never receive live
controller/plant handles. All three original experiment result byte streams must
match. Two sealed H1 packages must match in row/snapshot/config/trace/receipt bytes.

Explicit manual commands, from the configured native environment:

    python -m openpilot.tools.cyber_autotune.cyber_lateral_h1_experiment --store <explicit-external-synthetic-store>
    python -m openpilot.tools.cyber_autotune.cyber_lateral_h1_inspector --store <explicit-external-synthetic-store>/repeat-1

Outputs are atomic, immutable and cannot overwrite conflicting bytes. Paths must
be absolute, outside the repository and declared raw roots, with no symlink
components or target. Normalized '..' traversal is checked before containment.
No raw/private reader or background automation is used. Only aggregate synthetic
receipts are published; full synthetic packages remain in an explicit local store.

## Regression risk and acceptance

Risk: conflating pre-step feedback with post-step plant output, intent with
limited command, synthetic clocks with physical latency, missing health with
false, or repeatability with physical validity. Acceptance is exact trace/schema,
causal ordering and original-result noninterference. It is not candidate or
vehicle acceptance. Rollback removes additive files without production migration.

Independent review found a lexical '..' path containment bypass. Two tests
reproduced it before the canonical destination check was added. Saved-policy
drift also has a regression. Review also corrected wording distinguishing snapshot and native-input digests.
Final verification outcomes are recorded
below.

## Validation method and actual results

| Check | Actual result |
| --- | --- |
| Synthetic execution | 2 × 800 H1 rows, exact row/snapshot/config/receipt equality |
| Observer removal | Original unobserved run_arm result bytes exact |
| Events | ORDINARY 795; boundary, inactive, pressed, release, reengagement 1 each |
| Focused | 74 PASS |
| Full AutoTune / controls / lateral replay | 3,338 PASS (1,106.11 s) / 142 PASS / 16 PASS |
| Ruff / syntax / publication / privacy / authority / diff / SCons | PASS; publication findings 0; new files format PASS |
| Independent review | PASS; traversal regressions and digest wording corrected |

## Handoff and limitations

CYBER_LATERAL_H1_TRACE_REPEATABLE and VISUAL_FRAME_CONVERSION_PARTIAL apply.
Time/command/applied/curvature/yaw/heading/pose/rail/event data are available.
Missing pre-limit/CAN/measured steering and message health remain explicit.
Actual frame conversion, server and UI are not implemented.

NO PRODUCTION OBSERVER; NO VEHICLE AUTHORITY; NO HOLDOUT OPENING;
NO CANDIDATE SEARCH; NO TA/SG COMPOSITION. Holdout stays CLOSED, opening_count 0;
actual opener/journal NOT_IMPLEMENTED. No T2/T3 evidence is generated.

Preserved: SOURCE_GRID_OBSERVATION_REJECTED,
CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED,
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, CLOSED_MISSING_ADMISSIBLE_MODEL,
HOLDOUT_OPENING_CLOSED, FUTURE_UNTOUCHED_HOLDOUT_REQUIRED,
STAGE_B_SIGNAL_ADMISSION_BLOCKED, historical V3 tradeoff/attribution/causal recovery,
TA_STANDALONE_TRADEOFF_ONLY, SG_CLOSED_LOOP_TRADEOFF_ONLY,
CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED (37 violations).
Composition remains NOT_RECOMMENDED and NOT_AUTHORIZED; search and frozen candidate
evaluation remain NOT_AUTHORIZED. CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING, PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE, INDEPENDENT_REFERENCE_UNAVAILABLE; sealed reference
NOT_GENERATED; vehicle NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
