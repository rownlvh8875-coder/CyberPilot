# Separate AI-assisted private pixel verification

## Identity and purpose

- Area: offline validation / local annotation UI. IMPLEMENTED; human verification PENDING.
- Baseline: f57b4fdb860705770612f78b5c6f2e32b1539d58, feature/cyber-autotune.
- Purpose: editable raw-vision ego-boundary drafts for the existing frozen 60 private frames. Explicit Accept / Modify / Reject / Ambiguous creates a distinct assisted-human receipt.
- Scope: original-image pixels only. No independent truth, metric calibration, controller tuning, vehicle qualification or sealed-reference promotion.

## Original references

CyberPilot existing private_holdout_contract.py, private_holdout_hidden.py, private_holdout_annotation.py and private_holdout_metrics.py at the baseline above. Reuse immutable writes, exact60 materialization validation, pure coordinate checks, interpolation and assignment arithmetic. No external model dependency was added. Actual drafts used the authorized Codex session native image viewer on each raw original image. The deployed model version is not exposed: identity explicitly records that limitation, and source hashes are operator attestations, not remote execution proofs.

Data flow: existing frozen materialization → separately authorized raw-image vision → immutable AI rows → local human edit/decision → separate immutable human rows → all 60 set freeze → existing frozen detector comparison. The original blind store/server remains available and unchanged; this server never invokes its recovery logic.

## Changes and expected effect

Added private_holdout_assisted.py (source/policy/model binding, immutable draft and human schemas, all 60 freeze, pixel-only comparison), private_holdout_assisted_review.py (independent loopback server/store and editable canvas), and three focused test modules. Existing blind contracts, frozen 60 selection, development240 results, hidden CLRerNet receipts, production controller, comparator and A3 policy are untouched.

AI input roles allow only RAW_ORIGINAL_IMAGE. CLRerNet, modelV2, planner/candidate/steering outputs and prior chat visibility decisions are forbidden generation inputs. Human verification starts with no default action and requires an opaque reviewer ID and explicit assisted acknowledgment. The user authorized native vision access for this separate experiment; the earlier local-only blind policy is not silently changed.

Polylines contain 3–12 points in original 526×330 pixels, strictly bottom-to-top, inside the image, with no extrapolation. Paired boundaries require common visible y support; disjoint dash spans are left ambiguous rather than extended. Confidence HIGH/MEDIUM/LOW means suggestion confidence only. No detector confidence or acceptance cutoff is tuned.

Drafts remain editable; AI and final human rows are immutable and separately hashed. Reject/Ambiguous carries no localization geometry. Pending saves lock editing, and generation/ordinal guards reject stale UI callbacks after navigation. Detector comparison is 403 until that frame's separate assisted-human first decision. Final aggregate requires all 60 explicit human decisions.

## Regression risk and acceptance

Assisted labels can share AI errors or bias; they never qualify as blind or independent human evidence. The inherited maximum-support pixel matching has no newly optimized distance cutoff. Geometry matching/availability is diagnostic, not semantic accuracy qualification. Ambiguous and unreviewable frames remain counted while excluded from localization denominators. No one-sided center inference; center uses both observed boundaries on common y support only.

Rollback: stop the new local tool; preserved original blind contracts and stores remain intact. No automatic human approval or artifact migration occurs. Source drift invalidates authorization and requires a distinct experiment, preserving old receipts.

## Validation method and actual results

Actual raw-image vision: 60/60 draft rows, human 0/60. AI states: 40 both,3 right-only,1 left-only,12 ambiguous,3 intersection/merge,1 no-clear-marking. These are unverified suggestions, not human categories or detector accuracy. Some visible dashed spans lacked common y support and were conservatively left ambiguous. No detector output was opened for draft generation.

Executed checks and final counts are recorded below after completion. Browser tests use synthetic images only; browser interactions never manufacture actual human approvals.

- TDD: new contract, store/UI and metric tests failed before implementation; final focused32/32 PASS. Replay unittest16/16 PASS.
- Actual Chrome, synthetic fixture only: all 60 frame navigation; add/move/delete/undo/clear; original-pixel mapping; zoom/pan; draft refresh persistence; immutable saved rows; all4 action accounting; detector403 before save; saved-frame comparison; cross-frame pending-save guard PASS. JS errors0, external requests0, failed local resources0. Test server shutdown confirmed.
- Same-frame pending-save edit lock: browser assertion failed before the lock fix, then passed after fix. No actual human row was created by these tests.
- Ruff on all CI CyberPilot scopes PASS; compileall PASS; publication_check712 files/0 findings; authority import AST and grep PASS; public JSON receipts valid; git diff check PASS.
- SCons with PATH=$PWD/.venv/bin:$PATH and .venv/bin/scons -j2:100% PASS.
- First full run1765 PASS/1 existing A1 worker failure during concurrent source edits. The worker binds source before/after execution; source-stable isolated repeat test then passed. Full source-stable rerun passed below; no test/policy relaxation.
- Independent review identified blind-store recovery coupling, authorization chronology and UI save races. All fixed with regression/browser checks and re-review; no unresolved finding. Reviewer did not access private stores/images.

- Final full AutoTune + controls:1766/1766 PASS in690.37s (1624 AutoTune,142 controls). No source edits during the rerun.
- GitHub Actions for the resulting commit is checked after push; its final run URL/conclusion is reported at handoff.


## Handoff

AI draft-set SHA: a40d7b2c94147d0a8358cdc36548d95fb6a22c23871484d88938127726e99150.
Frozen selection SHA: 9f7ddeeddf9e59a279e904a3ee0b1af9e4ced41a7476841b1f4010d4f30e258d.
Authorization SHA: 79d68b2ad66f0752ff3bd9dca6a8769305c31cb339e37b11bcf560ad5682c00f.
Only aggregate counts and receipt identities are published. All images, coordinates, predictions, human drafts and final annotations stay outside Git in separate private stores.

Open the assisted tool locally. Select an opaque reviewer ID; inspect each raw image and AI overlay, choose ACCEPT_AI / MODIFY_AI / REJECT_AI / AMBIGUOUS. Edit points using Add / Move / Delete, left/right clear, undo, zoom/pan; save a draft or explicitly save the immutable human decision. After save, detector comparison is available without altering the AI or human row.

## Local reviewer instructions

1. Enter a nonidentifying reviewer ID. The cyan line is the AI left-boundary draft; yellow is the right-boundary draft.
2. Accept only visible current-lane boundaries. Move/add/delete points when wrong. Clear an unsupported side and change the visibility state. Do not extend paint through a vehicle, a gap or an intersection.
3. ACCEPT_AI preserves the draft exactly; MODIFY_AI requires an actual state/coordinate change. REJECT_AI / AMBIGUOUS stores no localization polylines.
4. Check the explicit assisted acknowledgment and save the immutable decision. Before final save, an editable draft can be saved and reloaded.
5. After immutable save, optional frozen-detector comparison appears in purple. It cannot modify the AI draft or human first decision.
6. Arrow keys navigate; L/R chooses a boundary, U undoes a point edit, J jumps to unverified. Shift/right drag pans; the zoom slider changes display only.

The previous chat visibility decisions are preserved separately. Their completion is not pixel-coordinate verification and does not fill any of these new human rows.

Human verification remains PENDING. No actual assisted-human reference or holdout accuracy report has been generated. No independent blind review has been completed by this workflow.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
CALIBRATION_MEASUREMENT_PENDING / INDEPENDENT_CALIBRATION_VALIDATION_PENDING / METRIC_CALIBRATION_UNAVAILABLE.
Sealed reference: NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
