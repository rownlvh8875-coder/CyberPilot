# Frozen comma10k human-review workflow

## Identity and purpose — IMPLEMENTED
Cyber Validation/UI, branch feature/cyber-autotune, baseline b49c67dee8052077b7afdc6158a1f4801fb01238.
That result commit was pushed first; fetch confirmed exact local/origin equality and clean tree.
Provide a usable human workflow around the already frozen 29 public frames.
Actual human labels remain 0/29. No final classification experiment/result has been produced.

## Original references and call path
Reuse CyberPilot/openpilot MIT source at the baseline: lane_tail_review_contract.py,
lane_tail_review_ui.py, lane_public_storage.py, lane_tail_diagnostics.py,
lane_public_batch.py and existing sealed public evidence. No external implementation,
new dependency or submodule change. Public comma10k MIT and official CLRerNet Apache-2.0
identities remain as recorded in comma10k-completed-full-evaluation.md.
The independent source review reported one persistent-freeze guard gap, repaired with RED/GREEN tests.

Completed full run → byte-identical frozen selected manifest → original V1 ReviewSession →
companion workflow freeze/progress/export/guide → explicit user save →
immutable V1 annotation rows/index → conditional bound raw-pool aggregation.
No inference, profile, device, CAN, Params, CarController or production controller integration.
The tool reads only public selected images and public cached metadata.

## Changes and expected effect
Add lane_tail_review_workflow.py and tests/test_lane_tail_review_workflow.py.
The frozen original UI, annotation schema, taxonomy, policy, frame list and all helper files
are unchanged. Their existing tool identity remains 6b0ec140be7fe6862a071da3adf4da3ebc31f2de995067d7c1a9cadf9e4bec1f.
Manifest SHA 82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10; selection-policy SHA ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54.
Workflow source file SHA b39b7537ad3bb2b38e7472cb67992b6e2942da036955b0906136b666b16dc937; composite identity 0d2da9a9725f53a0c41232d44662b65b1b08285bb9b7f0c4db3ab459d3c7fc90;
workflow policy SHA 0671199096d2a4e47919e8cc07923d13d228435175f1954483bd62070bf1dbff. Changing source blocks existing workflow freeze reuse;
no silent migration or deletion of freeze files is allowed.

The companion preserves original loopback Host/Origin/nonce/body bounds/CSP,
image decode/race protection and durable save/index recovery. It adds reviewer instructions,
N/29 progress, Previous/Next, jump to unresolved/unreviewed, jump to worst directional tail,
and JSON export. Source/frozen-manifest guards precede every request.
Stored V1 annotations are neither re-sealed nor overwritten by export. Each export row
contains its original annotation and null reviewer confidence: NOT_RECORDED_V1_SCHEMA.
Reviewer confidence was not part of the immutable V1 schema; no confidence is inferred.
Any future field collection requires a separate declared version.

Atomic file/parent fsync, immutable rows and writer leases remain owned by the original store.
No physical actuator delay/state/reset applies to independent image review.
Cache and human annotation directories remain external; only public identifiers/hashes and
public review metadata are committed. Browser screenshots stay outside Git.

## Regression risk and predeclared rules
Require the exact previously published manifest SHA and 29 frames for PUBLIC scope.
Unknown, duplicated, stale, malformed or unacknowledged rows fail closed.
28/29 cannot finalize and does not open metric samples. COMPLETE is annotation coverage,
not necessarily resolved causes. UNRESOLVED, OTHER or unreviewable rows prevent a resolved tail verdict.
TEST_ONLY rows can exercise all mechanics but never human evidence or an explained causal verdict.

The descriptive strict-majority rule concerns grouped human labels within this selected,
stratified diagnostic sample only. It is not a detector acceptance threshold or population estimate.
No justified estimator promotion/rejection criterion is invented. At most the conditional
report can say PUBLIC_DIAGNOSTIC_RETAINED; actual current verdict stays TAIL_UNRESOLVED.
Official CULane remains NOT_RUN/BLOCKED. PUBLIC_GT_QUALIFIED and reference/vehicle promotion
are unavailable regardless of sample taxonomy.

Aggregation validates the completed index SHA and original row receipt before accessing pools.
Prediction→GT and reverse summaries must exactly match the frozen frame. Same-point 2D retains
its original cached samples. Category median/p95 are linear quantiles of pooled samples,
not average frame percentiles. Empty samples stay null. Scores use unchanged public bins
and frame median score; these are diagnostic associations, not optimized thresholds.
Directional versus same-point p95 subtraction is never a causal matching-error magnitude.
Y-region counts are original supported prediction sample counts. Representatives use sorted IDs,
not manual cherry-picking. All categories account for every reviewed sample frame.

Rollback removes the companion only; original UI/result/history remains intact.
No comparator/A3/candidate/CLRNet rejection change. No qualification threshold relaxation.

## Validation method and actual results
TDD: initial feature absence RED, 17 tests GREEN; persistent manifest deletion/tamper RED
from independent review then GREEN; completed-index symlink RED then nofollow GREEN.
Final new suite: 27 tests PASS. Related suite: 72 PASS / 49 subtests in 13.19 seconds.
Full AutoTune: 1229 PASS in 286.49 seconds, increased from 1202.
Commands: .venv/bin/python -m pytest affected tests; .venv/bin/python tools/test_runner.py -j2
openpilot/tools/cyber_autotune/tests; Ruff whole AutoTune; compileall; PATH with .venv/bin then
.venv/bin/scons -j2. SCons 100% PASS, Ruff/syntax PASS. Companion validation JSON binds logs/source.

Actual Chromium/Chrome browser:
all 29 PUBLIC frames navigated, original image decoded, GT/prediction overlays toggled,
raw/display frame/mask/prediction/result SHA and metrics equal, taxonomy/guide/jumps/export/progress PASS.
Public POST count 0, human labels created 0, JS errors 0, external requests 0,
failed local resources 0. No raw human judgment inferred.
Separate TEST_ONLY 29-frame fixture exercises save/refresh and owned-process restart;
one synthetic UNRESOLVED/unreviewable row persists byte-identically. It is not human evidence.
The initial public browser probe occurred before full-store startup verification was ready,
was excluded, and its owned browser process tree closed. Clean rerun after readiness passed.
Both loopback servers were stopped and confirmed unreachable.

Final publication/privacy/authority/diff and independent result review are recorded in validation JSON.
Replay/simulation/shadow/vehicle stages: NOT_RUN / not applicable to a human-review interface.

## Handoff — HUMAN REVIEW PENDING / BLOCKED / REAL VEHICLE STATUS
See comma10k-human-reviewer-guide.md for stable taxonomy and exact local command.
The UI starts only after full-store verification; use the printed 127.0.0.1 URL and Ctrl+C to stop.
Immutable workflow/source binding is stored alongside the original review freeze.
Progress is NOT_STARTED, 0/29 reviewed, 29 unreviewed; TAIL_HUMAN_REVIEW_PENDING.
No final tail taxonomy or final detector classifier artifact was generated.
Human review must be performed by a person; no automatic replacement labels.

Full history is unchanged: 11888 completed; median 4.962068 px, directional p95 666.974077 px,
same-supported-point spatial p95 154.371065 px. Original lost temporary 10336-prefix record,
owned SIGKILL after 128 durable rows, restart/runtime identity revalidation and unchanged 9472
cached receipts before final completion remain documented, never rewritten.
Historical repeatability is 119×2 only; full population is single pass.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
Official reproduction, ego-lane identity, independent metric calibration/extrinsics, road registration,
desired path and private human validation remain missing. No private diagnostic exception.
Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No real lane-centering, meter accuracy, driving improvement or ground-truth qualification.
