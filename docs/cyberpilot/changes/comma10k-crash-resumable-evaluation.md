# Crash-consistent public comma10k evaluation

## IMPLEMENTED
Baseline187b2515c; offline validation only. The existing metric/detector/thresholds
and rejected CLRNet history remain unchanged. New durable plain-file storage uses
fsync(file), atomic rename, fsync(directory), including newly-created parent links.
The storage schema and source SHA bind FULL_PUBLIC_RUN_FREEZE_V2; no silent migration.
A writer lease prevents concurrent producers.

Immutable per-frame receipts explicitly distinguish COMPLETED and
REFERENCE_UNAVAILABLE. Hard detector failures cannot complete a run. Recovery
checks exact freeze/input order, canonical ordinal filename, unique indexed rows,
outer/nested identity and input/metric replay before resumed inference. Valid
orphan rows from a crash before index publication are recovered; corrupt/stale/
missing rows become PARTIAL_INVALID. Recovery retains only row metadata at scale.
Index writes can batch32durable rows; orphan rows remain independently recoverable.

A completed marker binds all rows, index and aggregate file SHAs and is written
LAST. Pre-marker progress says ALL_FRAMES_STORED_AGGREGATION_PENDING. Existing
completed artifacts cannot be overwritten. Completed reuse verifies actual weight,
image and mask bytes, every cached receipt and artifact SHA, with full active
source/environment guards before and after the audit. It does not rerun inference.
Source drift status uses durable writes and cannot promote reference evidence.

## DIAGNOSTIC PUBLIC GT
The prior lost10,336prefix is not recovered or reused. Rebuilt official source/
weight/packages/toolchain/backbone stay in persistent external storage. Recompiled
NMS has a newly declared environment identity. Acquisition is separate from the
network-isolated detector runner. Full11,888execution and distributions are pending
at this increment; numerical full result must be recorded only after marker proof.

## Validation
TDD RED→GREEN: real SIGKILL before rename and after row/before index; restart,
corruption/missing/duplicate and Unicode ordinal alias; stale identity fields;
early/immutable marker; actual image/mask/weight corruption/deletion on completed
reuse; source drift during completed audit; parent directory fsync, freeze-only directory durability and final pre-marker guard failure.
Focused91PASS; AutoTune1144PASS; SCons100%PASS; Ruff/syntax/diffPASS.
Publication/privacy/authority and independent review recorded in companion receipt.

## BLOCKED / REAL VEHICLE STATUS
TAIL_HUMAN_REVIEW_PENDING; official CULane reproduction NOT_RUN remains BLOCKED.
Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No production/controller/comparator/A3 changes. Rollback removes only these offline
modules; new-run directories remain identifiable rather than silently migrated.
