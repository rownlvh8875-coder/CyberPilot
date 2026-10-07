# Public diagnostic identity and persistence guard

## IMPLEMENTED

The restartable offline full runner rejects canonical volatile artifact paths
(/tmp, /run and /dev/shm) before semantic reads. Public data, weights, manifests,
runtime and raw receipts stay in persistent storage outside this repository.
Every batch checks the frozen producer/metric/report source hashes, actual pinned
detector HEAD and complete environment identity, including indirect preprocessing,
legacy metric, configuration and extension/kernel sources. Startup and pre/post
aggregation checks use the same full guard. Source drift produces
FAILED_SOURCE_IDENTITY_DRIFT, closes promotion and preserves any earlier summary
under its content SHA instead of leaving a misleading completed summary.

The regression test changes only an indirect diagnostic environment source during
a partial batch, leaving direct hashes/HEAD unchanged. It failed before the final
guard fix and passes afterward. Source/config changes require a new frozen run.

## DIAGNOSTIC PUBLIC GT

The old bounded GPU attempt acquired all11,888pairs (23,776files,11.32GB) and
observed10,336processed in1,800.46seconds, hard failures0, then returned partial.
The cache had been placed on volatile storage. A subsequent WSL cold restart and
cache absence were observed; boot cleanup configuration is consistent with the
loss, but no journal proves the exact cleanup operation. This was a storage
placement failure. No missing inputs or receipts are invented or reconstructed.

All full raw receipts/runtime were lost. Surviving committed119numerical reports
remain valid; observed full progress is explicitly NOT_REPLAYABLE. The hardened
runner was not executed on GPU because its external environment is now missing.
Fresh unit/full regression checks do not substitute for GPU or full evaluation.
See comma10k-full-attempt-availability.json for exact observed identities and
comma10k-tail-validation.json for software verification.

## BLOCKED

BLOCKED_EXTERNAL_PUBLIC_CACHE_LOST_ON_WSL_RESTART prevents full quantiles,
full-vs-subset comparison and post-run identity verification. Restore independently
verified public artifacts into persistent external storage or freeze a new runtime
experiment. Missing receipt trees require restarting all11,888frames; observed
prefix counts cannot be used for resume admission.

CULANE_DATASET_UNAVAILABLE remains official reproduction NOT_RUN. The official
Baidu alternate is access-unverified; no unknown mirror or quota bypass was used.
comma10k unfinished-mask provenance and lack of ego identity also remain explicit.
No PUBLIC_GT_PASS, detector winner, private input, reference JSON or confidence
threshold optimization. Human review is metadata-manifest only and still pending.

## REAL VEHICLE STATUS

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Production controller, candidate history, comparator and A3 policy unchanged.
