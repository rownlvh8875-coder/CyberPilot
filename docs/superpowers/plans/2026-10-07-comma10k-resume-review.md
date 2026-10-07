# Persistent comma10k evaluation and review implementation plan

> Native implementation with TDD, then independent reviewer per user instruction.

**Goal:** Complete replayable11,888-frame public diagnostics and provide a frozen human review tool.
**Architecture:** Durable file store below the existing runner; isolated review contract/UI above validated completion.
**Tech stack:** Existing Python/NumPy/Pillow; external frozen CUDA and existing browser runtime.
**Spec:** docs/superpowers/specs/2026-10-07-comma10k-resume-review.md

## Global constraints
No private data, live authority, production dependencies, invented labels, threshold
changes, ego truth or meter claims. Lost prefix cannot resume. CLRNet remains rejected.

## Review focus
Crash between row/index; stale identity with correct row SHA; duplicated/missing
ordinals; premature marker/aggregate; review source binding and browser-only TEST labels.

## Tasks
- [ ] lane_public_storage.py and tests: RED kill/restart/corrupt/identity/marker cases;
  implement atomic_json/read/store/index/complete/verify; integrate new run schema.
- [ ] Recover public cache/runtime externally, freeze all new identities; verify
  original119 correspondence and resume without inference; complete11,888.
- [ ] lane_tail_review_contract.py and tests: freeze four-per-stratum selection,
  complete manifest/input/result/tool identities, human receipt validation and pending gate.
- [ ] lane_tail_review_ui.py plus embedded local assets and tests: loopback-only
  serving and durable annotation save; real existing browser TEST_ONLY validation.
- [ ] Full summary/spatial/count buckets/subset representation comparison; no
  final taxonomy or retain/reject without real human review.
- [ ] Focused/full regression, Ruff/syntax/publication/privacy/authority/diff/SCons,
  independent review, feature records, logical commit/push and final exact clean check.
