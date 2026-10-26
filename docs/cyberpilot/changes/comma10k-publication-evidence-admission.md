# Public diagnostic publication evidence admission

## Identity and purpose — IMPLEMENTED
Cyber Validation, feature/cyber-autotune baselineb05921c26. Bind publication and
derived documentation to completed public evidence rather than counts alone.
No vehicle applicability, detector tuning or reference promotion.

## Original references and call path
Existing lane_public_storage.DurableRun, lane_public_batch.verify_resume,
lane_public_full_analysis, lane_tail_review_contract and lane_tail_review_ui.
CyberPilot existing project license; no external implementation adoption or new
dependencies. Source dataset/model/licenses remain the frozen comma10k/CLRerNet
identities from the previous records.
Completed store → actual index/row/artifact verification → analysis/subset parent
and comparison linkage → real cache SHA/restart proof → PUBLIC review freeze,
index and empty annotation directory → immutable metadata → artifact/source
certificate → derived immutable feature record. No upstream integration.

## Changes and expected effect
New lane_public_publication.py and tests/test_lane_public_publication.py. Reuse
existing validators; reject stale/corrupt/mixed/partial evidence rather than
publish a misleading completed report. Operational generators in external cache
use these helpers. Certificate binds every published artifact file SHA and this
admission source SHA. A document generator must verify this certificate, seals,
completion/parents/comparison and pending progress before writing completed text.

Actual completed store verification includes index, every cached row and all
bound artifacts; cached proof binds frozen actual file SHAs, run, owned-kill scope,
first bounded-window progress/result and final completed-marker/result.
PUBLIC scope and exact selected manifest/index are required. A row-before-index
orphan or any unknown annotation file prevents a zero-human-label pending report.
Environment self-SHA and full equality with frozen run.environment are required.
All derived JSON/text history refuses changed overwrites. No migration.
Text uses file fsync/atomic rename/directory fsync and refuses symlink targets.
Counters/SHAs are consistency evidence, not proof of detector or human accuracy.

State/reset/delay: not applicable; no controller, CAN, Params, CarController,
device, profile or network consumer. No production dependency/threshold change.
Maintenance: source changes require a new certificate/history version.

## Regression risk and acceptance
Risk: trusting count-only summaries, foreign parent receipts, changed cache,
TEST labels, orphan labels, stale environment and overwritten historical outputs.
No new performance threshold. Rollback removes only this offline admission helper;
old rejected candidates/comparator/A3 and frozen detector metrics remain intact.
Independent reviewer found four initial operational gaps and three follow-ups;
they were fixed with fail-closed regression coverage. Final source review: no
additional important findings. Actual full-result consistency review is a separate
pending stage at this commit, not inferred from source review.

## Validation method and actual results
TDD RED→GREEN; new12PASS independently rerun. Related focused93PASS4.19s;
stable-source AutoTune1202PASS355.23s; SCons100%PASS with .venv/bin in PATH.
Ruff/syntax PASS. Publication/privacy/authority/diff results and source/log SHAs
are in the companion validation receipt.
Tests reject wrong parent/hash/protocol, actual store artifact failure, stale input,
changed/missing cached files, foreign crash proof, altered final marker links,
TEST scope/wrong index, orphan human row, stale environment, symlink text,
changed history and tampered/partial/stale-source certificate.
Replay public11888completion is still running at this increment.
Controller simulation/shadow/vehicle stages NOT_RUN/not applicable.

## Handoff — BLOCKED / REAL VEHICLE STATUS
Full diagnostics and actual human-review artifact follow only validated completion.
TAIL_HUMAN_REVIEW_PENDING; CULane official reproduction NOT_RUN/BLOCKED.
Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
