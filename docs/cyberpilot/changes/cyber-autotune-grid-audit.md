# Cyber AutoTune structural grid preview and pure audit

## Identity and purpose

- AutoTune STEP8 infrastructure, implemented; independent review complete with one minor test gap deferred.
- feature/cyber-autotune base1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Deterministic finite review-only proposal list and run-bound outcome history.
  No real identification, search evaluation, online update, storage or promotion.
- Vehicle-independent tool contract; numbers in tests are synthetic, not HKG bounds.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot at base above; existing local
  policy/profiles/contracts plus original upstream c8fb9068 retained unchanged.
- Existing opendbc4134c0d1 and all submodules/models unchanged. No new dependency.
- Independently written standard-library tools, no copied fork code or additional
  attribution requirements. Repository license applies.
- Path: GridReview + ProposalInput -> exact tuple/budget/step checks -> each value
  inspect_proposal -> all-or-nothing GridPreview. Separate AuditEvent -> chain
  structure/digest/identity/state validation -> appended immutable AuditRecord.

## Changes and expected effect

- search.py and tests/test_search.py: finite immutable sorted/unique values,
  explicit baseline, rational step grid, existing range/delta/rate/confidence guards.
  Any invalid entry blocks all entries instead of silently shrinking search.
- 256-entry ceiling is an offline tool resource cap, not scientific evidence or
  vehicle parameter. Caller budget must be explicit positive integer within cap.
- Grid step uses parameter canonical unit; decimal rational semantics match the
  proposal contract. Full review/template/ordered profile identities bind digest.
- audit.py and tests/test_audit.py: STARTED then one terminal event; per-run
  source/config/input/evaluator/profile identity fixed, sequence and hash chain
  checked, malformed/reordered/tampered records refused. Genesis previous hash is
  64zeroes only as initial marker. Reason codes are uppercase ASCII, max128chars.
- COMPLETED is a processing outcome, not qualification PASS. BLOCKED,FAILED,TIMEOUT
  and STRUCTURAL_PREVIEW are terminal outcomes too. Empty/partial chain validity
  is structural only, not a completed run. Different proposals need separate run IDs.
- No files, clocks, callbacks, actuator sinks or runtime consumers. No rollback
  store. Refuse bad data, no fallback to guessed values. No upstream edits.
- Existing metrics, acceptance, safety, controls, delay and longitudinal unchanged.
  Rollback is cease using isolated tools; actual active profile never changed.

## Regression risk and acceptance

- SHA256 verifies consistency, not provenance/authenticity. Full-chain rewrite
  requires external trusted checkpoints/signatures to detect. No trusted store yet.
- All preview authority flags remainfalse. Sample/confidence/review are asserted
  metadata; actual producer validation/real-data permission are still prerequisites.
- No holdout/private data opened and no new scientific thresholds selected.
- Requirements: deterministic order/hash; baseline retained; resource/step/range
  gates fail closed; every terminal state preserves history; forbidden names blocked.
- Final independent review and affected tests required; no activation authority.

## Validation method and actual results

| Check | Command/evidence | Actual result/limit |
| --- | --- | --- |
| TDD | unittest test_search then test_audit | each missing-module RED exit1 ->9 and10GREEN |
| Package | python -m unittest discover -s openpilot/tools/cyber_autotune/tests | 101 passed, exit0, Ubuntu24.04/Python3.12.13 |
| Ruff/whitespace | ruff check openpilot/tools/cyber_autotune; git diff --check | PASS exit0 |
| Controls regression | prepared test_runner.py with controls+AutoTune -j2 | 233 passed in18.73s, exit0 |
| Full PC | preceding nightly boundedrun, before these19tests | 1193collected,300s timeout exit124; NOT full-suitePASS |
| Independent review | whole grid/audit plan; reviewer independently ran19tests | 0Critical/Important,1Minor deferred |
| Native replay / calibrated closed loop / shadow | not invoked | NOT RUN |

## Handoff

This implements preview and in-memory audit consistency, not a completed AutoTune
optimizer. Identification, actual confidence, native adapters, evidence acceptance,
audit persistence and vehicle profile updates remain unimplemented/blocked.
STEP8 PARTIAL, vehicle NOT_READY. No commit/PR, runtime profile or device changes.
Deferred minor: grid all-or-nothing test covers delta/rate failure but not a separate
out-of-range grid fixture. Range is enforced by inspect_proposal and covered in
profile tests; no demonstrated implementation defect, no acceptance change.
Reviewer exclusions: full-chain rewrite/prefix truncation/run-ID reuse require
external checkpoint/store; physical confidence/producer/evaluator authenticity,
serialization/persistence/crash recovery, hostile remote-input resource policy and
runtime performance not assessed. This local API is not a security sandbox.
Protected7previouspackagefiles and4frozen evidence artifacts retain exact hashes.

## Subsequent test-only follow-up — 2026-10-02

The deferred range-specific fixture is now permanent in test_search.py. Synthetic
review bounds2.25..2.35 reject grids(2.2,2.3) and(2.3,2.4) exclusively for range,
while unchanged delta/rate/step checks pass. Reviewed endpoints2.2..2.4 provide a
positive control. All-or-nothing output and denied authority remain asserted.
No production code, vehicle bounds or acceptance changed. An isolated in-memory
mutant silently filtering invalid entries fails both cases; originals pass.
Focused search/comparison29tests/6subtests PASS; package246/781subtests PASS.
Final independent review0Critical/Important/Minor; fresh targeted3tests/6subtests
and isolated mutants independently verified. Default PC1285passed43skipped1xfailed,
2354.94s,exit0;1360collected. Before/after73overlayfiles and Git/submodule/index/
observer/Python identities match. Original results above remain historical.
No actual optimization or newly qualified driving evidence claimed.
