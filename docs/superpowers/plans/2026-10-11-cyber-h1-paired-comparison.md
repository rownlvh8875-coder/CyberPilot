# Cyber H1 paired comparison implementation plan

**Goal:** Two separate frozen TA-B / SG-A T1 campaigns, exact paired traces and a read-only synchronized browser inspector.

**Architecture:** Add versioned modules and assets; preserve all historical files. Execute each arm with its own frozen controller/governor/plant state, attach detached H1 V1 row observers, validate shared exogenous stimulus separately from arm-specific consumed snapshots, persist immutable paged pairs outside the repository.

**Spec:** User's CYBER_H1_PAIRED_COMPARISON_V1 instructions; historical receipt chains are authoritative. Native/TA/SG/plant behavior and metrics remain unchanged.

## Constraints and review focus

- Exactly TA-B vs baseline and SG-A own-feedback vs baseline, 11 frozen scenarios each, two repeats each arm; no CURRENT, composition, search, acceptance or holdout.
- INPUT/COMMAND k versus PLANT completion k+1; null unavailable values, T1 only.
- Reject independently resealed source/page drift, cross-arm state or stimulus contamination, fake candidates, extra arms, private publication.
- No raw logs/device writes, external assets/network bind; actual HTTP browser verification and clean/equal remote SUCCESS required.

## Tasks

- [x] Write failing producer/pair tests; implement historical bindings, detached observers and exact exogenous pairing. Verify frozen historical result hashes and enabled/disabled bytes.
- [x] Write failing adapter/store tests; implement same-phase null-safe deltas, aggregate statistics, exact immutable page/catalog resume.
- [x] Write failing HTTP tests; implement new loopback-only GET/HEAD server and independent synchronized UI.
- [x] Freeze policy privately before execution; execute 88 packages and 44 paired conversions, verify exact repeats and no observer interference.
- [x] Verify both campaigns/all scenario catalogs, first/middle/final, playback/scrubber/events/overlays/deltas/null/evidence in actual browser; shut down and verify closed port.
- [x] Publish only aggregate receipts, add feature record; independent review and regressions for findings.
- [x] Run focused/full AutoTune/controls/lateral/Ruff/syntax/publication/privacy/SCons/diff.
- Final delivery gate after commit: push, latest exact-HEAD CI SUCCESS, clean/equal local/origin. Report the verified commit/run in the delivery message.
