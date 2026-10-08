# Private holdout: hidden computation, blind first decision

## Identity and purpose

IMPLEMENTED / REVIEWED: Validation and local UI, feature/cyber-autotune,
baseline cb4043ed57cf2165634429957971db93dd68b09f.
The user's new authorization permits early computation on the existing sixty
holdout images, with disclosure only after that same frame's immutable first
decision. Whole-set human pixel evaluation still requires all sixty decisions.
The original 240 development results, sixty selection, materialization, human
contracts, controller/candidate results, comparator and A3 rejection are unchanged.

This is an additive versioned workflow. The earlier all-sixty-before-inference
record remains historical evidence; its original producer/validator files are
unchanged. Early computation is not human exposure and is not human GT.

## Original references

Reuse the existing private_holdout_contract.py image/first-decision validation,
private_holdout_annotation.py raw-only UI/manual save, private_pixel_execution.py
privacy/prediction validators, private_pixel_executor.py frozen inference pattern,
lane_detector_runner.py runtime/weight checks and lane_public_storage.py no-follow,
writer lease, fsync and atomic immutable receipts. No external implementation is
copied into production.

CLRerNet: https://github.com/hirotomusiker/CLRerNet, Apache-2.0,
commit dae038f67da57e292e5293a68c9c1c2922de13c2,
weight SHA 424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa.
Exact source/config/environment/preprocessing/postprocessing identities are bound
in the [redacted readiness receipt](private-holdout-hidden-readiness-v1.json).
GPU environment remains Python 3.11.9, torch 2.1.0+cu121, CUDA 12.1,
mmcv 2.1.0 and mmdet 3.3.0 on the existing RTX 3050 Ti runtime.
Normal repository tests use the existing Python 3.12 virtualenv.
Pinned submodules and production dependencies were not changed.

Call flow: original materialization -> separate hidden-inference authorization ->
network-isolated exact runtime/source/weight check -> original SHA-bound PNG bytes ->
unchanged resize/pipeline/postprocessing -> two exact repetitions -> immutable hidden
receipt per frame -> complete marker after sixty validations -> raw-only manual UI ->
original immutable first decision -> separate provenance relation -> optional reveal
of this frame only -> all-sixty human-reference freeze -> pixel diagnostic metrics.

## Changes and expected effect

private_holdout_hidden.py binds separate authority, ordered sixty receipts,
optional AI declaration schema, first-decision/output relationships and post-freeze
pixel evaluation. Its new source identity covers the three new modules and the
frozen disclosure policy. It never rewrites historical first decisions or invents
post-freeze inference timestamps. Old pixel matching/interpolation mathematics and
the predeclared evaluation policy are reused without threshold changes.

private_holdout_hidden_runner.py consumes only already materialized, bounded PNG
bytes; it does not resample, search routes, decode source videos or access modelV2.
Same read buffer is size/type/SHA checked with no-follow. Before fresh work, every
cached row and image is checked; stale/unknown/corrupt rows fail closed. Source,
config, exact environment and weights are revalidated before input access and again
at completion. Existing deterministic seeds/CUBLAS/cudnn settings, sealed weight
snapshot and complete inference-state-key check are preserved. No physical delay,
controller path, CAN, Params mutation, CarController/device or production authority.

private_holdout_hidden_review.py wraps the original local UI and authoritative
save handler. GET detector/AI/comparison endpoints return 403 before the requested
frame's durable first row, before opening hidden outputs. Saved frames expose only
their own bound output; invalid/absent comparison artifacts return 409.
Host/Origin validation, POST token, CSP, no-store and 127.0.0.1 binding are reused.
No static-directory route serves the hidden store.

Before save, the UI serves raw pixels and manual drawing/state controls only.
Confidence, prediction, AI, development result, approximate geometry and automatic
hypotheses are absent. New-image navigation clears the comparison canvas/panel
immediately; response generation and loaded-frame checks discard late old-frame
responses. Human draw/zoom/pan/draft/undo/clear controls and original pixel semantics
remain unchanged. First decision is immutable; correction does not overwrite it.

After the original save is durable, a separate relation binds its hash to the
hidden receipt and actual computation timestamps. Detector computed-before and AI
computed-before are measured independently. AI NOT_RUN means
ai_computed_before_human=false, not an invented true value. Exposure-before flags
remain false and blind_human_review=true within this UI/API workflow and the
reviewer's explicit acknowledgment. An already informed reviewer must not claim
blindness; hashes do not prove external behavior or human expertise.

If optional comparison/provenance is absent, a pending marker is attempted without
altering the first receipt. Even a failed pending-marker write cannot report a
durable human save as an annotation failure. Comparison stays closed; retrying
reveal can produce the separate binding later. No incomplete relation is promoted.

## AI limitation and regression acceptance

PRIVATE_HOLDOUT_AI_PREREVIEW_V1 defines separate immutable declaration fields:
sample/image/prediction binding, frozen human visibility-state vocabulary, short
observable reason, conservative confidence, local model/version/weight/environment,
prompt/tool hashes and human_annotation=null. A declaration hash alone is not
proof of a vision invocation. This generation has no verified frozen local vision
runner: AI declarations carry AI_VISION_EXECUTION_UNVERIFIED and are rejected by
both comparison and evaluation gates, even with sixty human decisions.
Actual AI vision prereview is NOT_RUN. No private images were uploaded for remote
AI analysis; no metric heuristic or synthetic suggestion was saved as real AI.

A future verified vision producer requires a separate versioned experiment rather
than overwriting this run. AI state concordance remains a declared future contract;
no actual AI/human statistics exist here. No AI replaces human polylines.

Acceptance here is structural: exact original sixty, frozen detector identity,
finite/bounded output and exact repeatability; no quality threshold, config tuning
or confidence filtering was added. Raw holdout outcome counts, confidence or
automatic failure hints are not published while human review is incomplete.
After actual sixty-decision freeze, left/right/center pixel diagnostics may use only
observed spans and the original matching policy. One-side/ambiguous accounting,
no assumed width/extrapolation, no approximate meter conversion and no sealed
promotion remain unchanged. Public marking GT and private ego-boundary GT retain
different semantics.

## Actual execution and validation

The original selection SHA is unchanged:
9f7ddeeddf9e59a279e904a3ee0b1af9e4ced41a7476841b1f4010d4f30e258d.
Materialization receipt SHA is
6173b028db779a9c94b127baff2d89ed5cabc61e578b7b94965918709bfbaa40.
Its file SHA is separately bound; receipt identity and file bytes are distinct.

Actual GPU inference completed 60/60, two repetitions per frame, exact
repeatability PASS. A fresh process revalidated all sixty PNG/receipt/runtime
identities and reused all sixty receipts with zero new inference rows.
Human annotations remain 0/60, human reference NOT_GENERATED, evaluation NOT_RUN.
Hidden completion and authority hashes are in the redacted readiness receipt.
Actual predictions and source/image paths stay private. No human annotation was
generated by code.

Initial model initialization failed offline because the existing backbone cache
was not selected. The network namespace prevented a download before any frame
inference. Re-execution selected the already existing public backbone cache using
TORCH_HOME; source/config/environment/weights were unchanged. No download or
network permission bypass occurred. This failed attempt remains in local logs.

Actual synthetic Chrome tests use flat-color fixture images in a separate store,
never private pixels. They verified hidden/disabled default, manual original
coordinates, draft reload, immutable save, same-frame reveal, all sixty navigation,
cross-frame panel clearing, a deliberately delayed old comparison response,
refresh persistence, zero JS errors and owned server clean shutdown.
CSP/source/asset audit excludes external resources; network request tracing is
unavailable and is not claimed.

TDD includes authorization/source/input drift, repeatability, cached-only resume,
corrupt cache, AI cannot create human rows, unverified vision declarations blocked,
same-frame HTTP 403/409, first-save provenance, journal-write failures, all-sixty
metric gate and no promotion. Independent source review found the AI declaration
execution gap and durable-save response gap; both were corrected with regression
tests and independently re-reviewed. The reviewer accessed source/synthetic tests
only, never private images or outputs.

Required test/build/privacy/publication results are recorded separately in the
[validation receipt](private-holdout-hidden-validation-v1.json).
Replay vs production baseline / simulation / vehicle shadow: not applicable;
this increment changes isolated evidence/review tooling only.
Rollback removes the new modules and returns to the historical raw-only UI,
preserving all receipts and images. Maintenance is limited to explicit wrapper
compatibility with the pinned original UI; synthetic browser tests cover replacements.

## Handoff / PENDING / BLOCKED / NOT RUN / VEHICLE STATUS

Launch the repository virtualenv locally with private persistent stores:

    python -m openpilot.tools.cyber_autotune.private_holdout_hidden_review --raw-cache PRIVATE_RAW_CACHE --hidden-cache PRIVATE_HIDDEN_CACHE --port 45234

Open the printed 127.0.0.1 URL yourself. Enter stops the server. Annotate only
visible current-lane left/right spans in original pixels; choose ambiguity where
appropriate. Acknowledge no prior output exposure, then save the immutable first
decision. Only then may that frame's detector comparison be opened.
Do not open the hidden artifact directory before your decision or upload private
images. Saved-first provenance is scoped per frame, not public second-reviewer
validation. Final aggregate remains blocked until sixty actual human first rows.

HIDDEN_DETECTOR_INFERENCE_COMPLETE.
PRIVATE_HUMAN_HOLDOUT_READY_FOR_REVIEW / PRIVATE_HUMAN_HOLDOUT_PENDING (0/60).
AI prereview NOT_RUN / AI_VISION_EXECUTION_UNVERIFIED.
PRIVATE_DOMAIN_VALIDATION_NOT_RUN; qualification thresholds remain unjustified.
[Additive blocker snapshot](private-holdout-hidden-blockers-v1.json) preserves
CALIBRATION_MEASUREMENT_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE, CULANE_OFFICIAL_REPRODUCTION_BLOCKED,
INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE, ego identity/road registration/path
blockers. None is resolved by hidden inference.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
