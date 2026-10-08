# Frozen private holdout: blind ego-boundary pixel annotation

## Identity and purpose

IMPLEMENTED: separate raw-only materialization authorization and local manual
annotation tooling for the exact historical sixty HOLDOUT samples. Baseline
da08c12b3ae7f403c4423fbb0b35581935fff89d, feature/cyber-autotune.
This is preparation for private pixel-domain evidence, not meter calibration,
detector qualification or vehicle activation. The 240 development results,
300-sample manifest, 60-holdout selection and public/assisted evidence are unchanged.

## References and call flow

Reuse private_pixel_execution.py manifest/detector validation,
private_pixel_executor.py encoded-source sealed memfd snapshots and atomic PNG
writes, lane_public_storage.py no-follow JSON, writer lease/fsync, and existing
canonical SHA-256 receipts. No external detector code is copied or changed.
Future inference must use the original frozen CLRerNet
https://github.com/hirotomusiker/CLRerNet, Apache-2.0,
commit dae038f67da57e292e5293a68c9c1c2922de13c2 and weight
424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa.
Original environment and preprocessing/postprocessing remain bound separately.

Existing frozen manifest -> exact original HOLDOUT plan -> explicit separate
authorization -> source snapshot hash/size validation -> retrieve selected
original presentation ordinals -> durable private PNG + immutable image receipt ->
60-row materialization package -> raw-only human UI -> immutable first decisions ->
ALL 60 reference freeze -> separate future frozen-detector inference -> pixel metrics.

Intermediate codec frames must be traversed to address selected ordinals; they
are not retrieved for annotation, cached, visually inspected or inferred.
Materialization ran without networking in a Linux user/network namespace.
No route discovery, new sampling, modelV2/candidate reads or detector invocation.

## Changes and contracts

private_holdout_contract.py defines raw-only authority, exact original 60 binding,
coordinate/state rules, immutable first decisions, separate corrections, reference
freeze and comparison gate. Completion reconstructs the exact original ordered
materialization package; duplicated, missing, unknown or stale receipts fail closed.
Freeze cannot predate any first-decision saved_at. Hashes establish bytes and
declared provenance; they do not prove human expertise or a tamper-proof environment.

private_holdout_materializer.py consumes the historical manifest/holdout plan,
stores outside Git, verifies source videos even on resume, and completes only after
all 60 image receipts validate. Original development artifacts are read-only.
An orphan image after a crash is deterministically regenerated; complete image
receipts are revalidated/reused. No silent skipping or schema migration.

private_holdout_annotation.py binds only 127.0.0.1, validates Host/Origin and a
per-server POST token, uses CSP/no external assets, and serves bounded no-follow
image bytes whose hash is verified on that same buffer. UI displays only raw image
and the user's own drawing. No detector/confidence/AI/model/development/geometry
interface is exposed before all 60 decisions freeze; biasing interfaces always 403.
The detector endpoint for a saved frame remains 403 until ALL 60 decisions freeze.
After freeze the detector endpoint 409 explicitly reports that separate inference
has NOT_RUN. This increment does not implement or execute the post-freeze detector
producer: the current automatic endpoint is READY_FOR_REVIEW, not evaluated.

Zoom/pan, per-side undo/clear, Previous/Next, frame selector, unreviewed jump,
keyboard shortcuts and editable drafts are available. Loading a new image resets
acknowledgment and disables saves; POST envelopes bind the exact image receipt.
First decisions are immutable; correction receipts preserve the original and are
not substituted into primary blind evaluation. Startup recovers a missing set-freeze
marker only from sixty validated durable first rows, and rejects missing rows in a
previously frozen set. Provenance flags remain detector/AI/model exposure=false;
the reviewer must explicitly attest this. An operator who has already seen outputs
must not claim blind evidence merely because the tool contains a checkbox.

## Pixel semantics and future evaluation

Coordinates are ORIGINAL_IMAGE_PIXEL, TOP_LEFT_PIXEL_CENTER, x right, y down,
finite subpixel floats. Each visible side has 3–12 observed control points in strictly
decreasing y, no duplicate y, inside original 526x330 bounds. BOTH requires left<right
through their shared observed support. One side and ambiguous/intersection/no-marking/
unreviewable states are retained without forced completion.
No automatic snap, assumed width, invisible extrapolation or AI drawing.

private_holdout_pixel_metrics.py is predeclared post-freeze deterministic metric
math, exercised only with synthetic fixtures here. It accepts separately declared
post-freeze prediction receipts, not proof that a detector actually generated them;
actual inference/runtime/repeatability evidence must be supplied by a future
producer. No real holdout inference or localization results exist in this increment.

Matching maximizes eligible observed-y-overlap match count, then minimizes summed
mean absolute lateral pixel cost, then lane index; each detector lane is used at most
once. No confidence/acceptance threshold or nearest ego-side heuristic is introduced.
This overlap-only rule can assign a remote line; report its error rather than call
the match proof of reliable ego identity. Zero-overlap unmatched lines are unsupported
by observed support, not automatically false-positive truth. All thresholds remain
unjustified for qualification.

Interpolation uses integer image-y rows within observed support only. Left/right
and combined median/p90/p95 are pixel distances. Center uses both human boundaries
and two distinct matched detector boundaries within shared support, never a single
side or assumed lane width. Ambiguous/intersection/unreviewable/no-clear-marking
counts remain in total accounting and outside localization denominator. Human-visible
side unavailability is reported separately. Approximate geometry is excluded.
Public all-marking GT and private human ego-boundary GT have different semantics;
they cannot be advertised as one shared accuracy benchmark.

## Actual execution and persistence

[Authorization public binding](private-holdout-authorization-public-v1.json) contains
only whole-set receipt hashes and source/policy identities, no private sample list.
[Readiness receipt](private-holdout-ready-v1.json): materialized 60/60; first pass 60 new,
resume 60 verified existing and 0 new. Original 253 development JSON artifacts were
rehashed and unchanged. Original selection SHA remains
9f7ddeeddf9e59a279e904a3ee0b1af9e4ced41a7476841b1f4010d4f30e258d.
Images, source bindings, human coordinates and exact private paths remain local.
The original stream is qcamera narrow-road per source role evidence; actual camera
sensor/calibration/mapping is not independently validated.

Actual human annotations 0/60; human reference NOT_GENERATED;
holdout detector/AI inference NOT_RUN; private pixel evaluation NOT_RUN.
No human annotations were generated by code. Synthetic browser tests explicitly
use generated flat-color images and fixture decisions in a separate store.

## Validation, independent review and limits

TDD covered authorization, source/config drift, exact60, privacy directories, resume,
corrupt inputs, units/coordinates, one-side/ambiguous handling, crossing, immutable
draft/first/correction distinction, 60-only gate, pixel metrics and no sealed promotion.
Review found and fixed stale-image UI binding, missing freeze crash recovery,
image hash/read race, duplicated materialization gate, and backdated reference freeze;
each has a regression test. Independent source re-review found no remaining
actionable issue and independently passed 53 focused tests without private access.

Actual synthetic Chrome validation covers raw-only default, manual points with exact
original coordinates, undo/clear, pan inverse mapping, zoom, draft reload, immutable
save/reload, 60 selectors, post-all-60 NOT_RUN comparison gate, JS errors 0 and owned
loopback server shutdown. CSP/source asset audit forbids external assets; browser
network request tracing was unavailable and is not claimed.
Full tests, Ruff, syntax, publication, authority/privacy, whitespace and SCons evidence
is recorded in [validation receipt](private-holdout-validation-v1.json).
Rollback removes isolated offline tools; no production path was changed.

## Handoff / PENDING / BLOCKED / NOT RUN / VEHICLE STATUS

See [Korean reviewer guide](private-holdout-reviewer-guide.md).
Launch with the private persistent cache from the repository virtualenv:

    python -m openpilot.tools.cyber_autotune.private_holdout_annotation --cache PRIVATE_CACHE --port 45234

Open the printed 127.0.0.1 URL locally; press Enter in the console to shut down.
Do not upload private images or use an AI to generate first-decision polylines.
All60 human decisions must precede any detector inference. Later corrections
do not erase the historical first decisions. Real post-freeze inference is a
separate future increment with the frozen detector, not an automatic invocation.

PRIVATE_HUMAN_HOLDOUT_READY_FOR_REVIEW / PRIVATE_HUMAN_HOLDOUT_PENDING.
PRIVATE_DOMAIN_VALIDATION_NOT_RUN / pixel qualification BLOCKED.
[Additive blocker snapshot](private-holdout-blocker-snapshot-v1.json) preserves
CALIBRATION_MEASUREMENT_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE, CULANE_OFFICIAL_REPRODUCTION_BLOCKED,
INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE (uninformed public second reviewer),
COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE and unjustified public pixel thresholds.
Private blind holdout does not automatically resolve any of these.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
