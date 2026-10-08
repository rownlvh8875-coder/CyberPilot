# First bounded private pixel diagnostic

## Identity and purpose

IMPLEMENTED: a separately authorized PRIVATE_PIXEL_DIAGNOSTIC_ONLY exception,
encoded camera metadata selection, persistent offline inference and a local
read-only viewer. This is a detector-domain diagnostic, not calibration,
qualification or reference evidence. Branch feature/cyber-autotune; exact
pre-execution baseline 8ed6b1200c7bcad1f09c5bb04b0814d60de72024.
Executed source identity and frozen detector identity are in the redacted
authorization binding and aggregate. Original contracts and historical results
are unchanged; new authorization applies only to this increment.

## Original references and call flow

CyberPilot repository https://github.com/rownlvh8875-coder/CyberPilot, baseline
above. Reuse existing lane_detector_runner.py runtime inspection, sealed weight,
network isolation, deterministic settings and lane_public_protocol.py sampling;
lane_public_storage.py fsync/atomic receipts; native_protocol.py canonical SHA.
No external detector source is copied. CLRerNet Apache-2.0, official
https://github.com/hirotomusiker/CLRerNet commit
dae038f67da57e292e5293a68c9c1c2922de13c2 and original CULane checkpoint SHA
424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa.
Exact completed public environment remains pinned; Python3.11.9,
torch2.1.0+cu121, CUDA12.1, mmcv2.1.0/mmdet3.3.0, RTX3050Ti. Normal tests use
existing Python3.12 environment; no package/lockfile changes.

Call flow: metadata-only root existence check -> frozen bounded metadata policy ->
directory discovery and encoded TS/PES/SPS/AUD/PTS parser ->
immutable selected DEVELOPMENT/HOLDOUT
manifest -> separate explicit user authorization binding -> runtime/file hash
revalidation -> immutable encoded-video snapshot -> ordinal decoding ->
unchanged public detector preprocessing/model/postprocessing -> two exact
repetitions -> private per-frame/image cache -> immutable completion marker ->
aggregate whitelist. No log-message/modelV2/candidate parser is present.
Source stream role is audited from loggerd.h qNarrowRoadEncodeData; this is
source-based role evidence, not per-unit sensor verification or independent
camera geometry.

Submodules remain unchanged: msgq0e266c1, opendbc4134c0, panda92eb565,
rednose8671, teleop1aa8, tinygrad9d044; full gitlinks retained.
Production LatControlTorque, comparator/A3 rejection, candidate history,
physical calibration admission and private qualification gate are untouched.

## Changes and predeclared constraints

New private_pixel_execution.py defines the diagnostic exception, exact detector
binding, private-root separation, bounded selection and prediction-only schema.
private_pixel_executor.py handles encoded-only planning and isolated inference.
private_camera_metadata.py rejects unsupported/corrupt encoded metadata instead
of invoking a decoder during planning. private_pixel_analysis.py supplies common
prediction statistics and hypothetical geometry probes; private_pixel_review.py
is a loopback read-only development viewer.

Sampling policy V2: at most60 segments,5 fixed positions per segment,
ordinal floor((2*slot+1)*frame_count/10); slot4 is unopened holdout, other4
development. Round-robin sorted opaque route IDs and sorted opaque segment IDs.
No image/confidence/result-based selection. 300-frame bound is a first-run
resource limit, not a qualification threshold. Encoded-invalid sources receive
explicit hash/size/reason dispositions before selection. No silent skip.

Only DEVELOPMENT selected frames are retrieved/materialized. A video codec
must traverse preceding packets to address an ordinal; intermediate codec
frames are not cached, inspected or inferred. Stream supports approximately
20fps H264,526x330. Original-frame ordinals use decoded presentation order,
not encoded packet order. Sparse five-position sampling does not support a
consecutive-frame temporal stability claim: temporal analysis NOT_EVALUATED.
Normalized geometry is spatial prediction behavior, not tracking truth.

Each new frame is inferred twice and canonical prediction bytes must match.
Raw PNG and detector polyline rows are local/private, outside Git. No CAN,
Params/CarController/device/Jetson writes, injection, profile change, tuning,
ensemble, threshold change, telemetry or network acquisition. Inference runs
in a Linux user/network namespace with loopback as the only interface.

No physical-delay/controller state is introduced. Per-frame receipts bind
input image, source video, exact manifest/authorization/detector, dimensions,
confidence and prediction geometry. Atomic image and receipt writes use fsync;
image writes use no-follow directory handles. Corrupt/stale/unknown cache
rows reject; no migration. Completed marker is written last after row/artifact
verification. Publication never includes private sample IDs, paths, raw names,
timestamps, source-file hashes, GPS/EXIF, images or video.

## Actual diagnostic results and limits

Inventory: one route,95 qcamera sources;94 encoded-eligible,1 malformed/truncated
TS source explicitly unavailable.96 cabin streams excluded, not decoded.
Frozen selected samples:300 from60 segments;240 DEVELOPMENT and60 HOLDOUT.
240/240 development decoded/inferred;37 no-output,15.4167%.
Lane counts0/1/2/3/4:37/9/49/96/49.591 predicted lanes; per-lane confidence
median0.647315,p95 0.823050; no GT localization/error/recall/precision exists.

Public comparison scans all11,888 completed public per-frame detector records,
including their stored per-lane points and scores; it does not invent confidence
for the earlier119-pair pooled-only artifact. Public no-output3285/11888
(27.6329%), lane counts0/1/2/3/4:3285/1047/1616/3110/2830.
Public per-lane confidence median0.649535,p95 0.834531.
These are FULL_PUBLIC vs METADATA_SELECTED_SINGLE_PRIVATE_ROUTE distributions,
not matched-domain evaluation, independent accuracy or a causal domain-gap rate.
DOMAIN_SHIFT_DIAGNOSTIC_ONLY; PRIVATE_DOMAIN_DIAGNOSTIC_FEASIBLE does not qualify
the detector. Existing public directional median4.96px/p95 666.97px and
same-point p95 154.37px remain untouched and are not compared to private GT.

Hypothetical projection uses both static ar0231-family and os04c10 camera cases.
Actual sensor, actual image crop/mapping and distortion remain unverified.
Full-image linear resize and undistorted pinhole are algebraic assumptions,
not facts about this log. Roll0°,pitch2.34°,yaw0.2° retain MODEL_DERIVED prior;
mount-y0 retains user declaration; height1.40m retains coarse user-approved
prior. Height grid1.33/1.35/1.375/1.40/1.425/1.45/1.47m was frozen before run.
Fixed rays scale±5%; near-horizon/outside nominal5–30m points are explicitly
unavailable/out-of-domain. Distance groups are assigned at nominal height;
scaled points can leave their nominal group/domain. These are sampled
hypothetical sensitivity envelopes, never meter error or physical uncertainty.
No private pixel is routed through the independent geometry/reference gate.

## Failed preflight and persistence history

Initial one-file OpenCV property inspection was intended as metadata, but
independent review established that VideoCapture can internally decode during
stream probing. No image was retrieved/visually inspected or inferred.
That preflight is INVALID_METADATA_PREFLIGHT, excluded from ordered execution
evidence; its limitation is retained in a separate public disposition receipt.
It must not be described as a proven no-decode probe.

A subsequent encoded-only plan failed closed on an incomplete TS file before
manifest/inference. Eligibility/disposition policy was versioned BEFORE the
fresh metadata selection; no detector result drove this revision. A stale
unexecuted lint-only source freeze was preserved and not reused. The actual
encoded experiment froze policy/selection/auth before opening its selected
development frames. No prior image/result inspection informed selection.

The owned inference process was deliberately killed after8 durable rows,
then resumed with those8 unchanged receipts and exact revalidated identity.
Final240-row completion followed;60 holdouts were not materialized. A completed
producer re-entry exposed Python integer-vs-JSON string dictionary-key comparison
in the immutable aggregate export. It failed closed without rewriting the
aggregate or marker. A separate canonical, read-only completed-cache audit
verifies existing receipts/inputs/environment and avoids rerunning inference;
operational resume and completed read-only audit are distinct paths.

A further independent review found that the first audit reused a storage
verification API whose failure path could rewrite an invalid index. Its actual
successful verification did not mutate the valid cache; that historical proof
is preserved. The corrected V2 audit uses pure read-only verification and an
existing read-only shared lock. Both success and validator-failure tests assert
original index/marker/artifact bytes are unchanged. The actual V2 audit verified
all240 receipts/source/image/environment bindings with zero frame decode or
inference, preserving completion and aggregate identities. See
[additive correction proof](private-pixel-cache-audit-correction-v2.json).

## Regression risk and acceptance

Structural identity/determinism do not prove camera truth or independence.
Missing streams, malformed transport, unsupported SPS/AUD/PTS or nonfinite
predictions fail closed. Holdout endpoints remain closed in the viewer; it
creates no annotations and does not satisfy human validation.
Future actual holdout materialization needs separate authorization and immutable
blind-first human labels, with no detector reselection or confidence filtering.
Source pins intentionally reject changed executors/config/env; new experiments
must preserve historical selection/execution receipts. Rollback removes these
isolated tools; no production integration exists.

No new detector acceptance threshold. Public official CULane reproduction,
pixel qualification threshold justification, blind reviewer, ego boundary
identity and independent calibration remain blockers.

## Validation method and actual results

Validation commands and final counts/log hashes are in
[validation receipt](private-pixel-first-run-validation-v1.json).
Tests cover auth/freeze boundaries, exact identities, dev/holdout disjointness,
SPS geometry, invalid transport, symlink privacy, corrupt/resumed receipt,
no-GT/publication fields, hypothetical projection and loopback UI.
Independent reviewer found and verified fixes for premature decoder invocation
and symlink image writes. No private pixels were sent to a vision model.
Actual browser validation uses a clearly synthetic300-entry fixture:
selector, Previous/Next, holdout-unopened behavior, overlay, reload,526x330 canvas,
JS errors0; CSP/source asset audit is recorded, network trace unavailable.
Loopback test server cleanly terminated.

During an earlier full suite, concurrent source edits caused existing
source-binding guards to reject three tests. Those results are not presented
as passing regression; the final full suite is run with code frozen.
SCons uses exported .venv PATH and .venv/bin/scons -j2.

## Handoff: BLOCKED / NOT RUN / VEHICLE STATUS

PRIVATE_PIXEL_DIAGNOSTIC_COMPLETE is non-qualifying.
PRIVATE_HUMAN_HOLDOUT_PENDING; PRIVATE_DOMAIN_VALIDATION_NOT_RUN.
CALIBRATION_MEASUREMENT_PENDING; INDEPENDENT_CALIBRATION_VALIDATION_PENDING.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference NOT_GENERATED.
CULANE_OFFICIAL_REPRODUCTION_BLOCKED, INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE,
COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE and
PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED remain unresolved.
No automatic threshold, confidence optimization or controller acceptance follows.

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No vehicle activation is authorized. Next evidence work is blind human review
of the already-frozen60 holdouts and actual independent physical measurements,
not another detector search on these private outputs.
