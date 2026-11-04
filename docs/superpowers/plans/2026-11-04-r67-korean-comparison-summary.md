# R67 Korean Comparison Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans;
> owner delegated inline execution without repeated permission questions.

**Goal:** Read R66 saved-byte comparison results as Korean Markdown without a new quality verdict.

**Architecture:** One pure renderer consumes the existing validated comparison
record. One optional CLI format switch selects UTF-8 Markdown; default JSON and
all comparison/validation/exit semantics remain unchanged.

**Tech Stack:** Existing CPython3.12.13, stdlib, cloud unittest/Ruff/Ty/Codespell.

**Spec:** docs/superpowers/specs/2026-11-04-r67-korean-comparison-summary-design.md

## Global Constraints

- Base ef90e61b719701096a982b96f3e2a24594c809da; clean existing linked worktree,
  new feature branch; preserve all source/evidence/environments/verification records.
- `render_comparison_summary(result: dict) -> bytes`: deterministic UTF-8 LF,
  final newline, no I/O/links/raw content or new quality/origin assessment.
- `--format json|markdown`, default json; unchanged R66 JSON/API/0-match/1-diff/
  2-invalid semantics; safe empty-stdout input rejection and no file outputs.
- Validate consumed schema, counts, sorted fixed-path deltas, full hashes/size,
  and original receipts; no partial report/fallback/coercion/repair.
- No producer/verifier/probe/old-summary/artifacts/app/lock/workflow/old-guide edits.
- No new browser/F61/vehicle work, HF writes or main merge; full cloud unit/gate
  synthetic work remains NONZERO_NOT_AGGREGATED. Actual r/T2/scale=null;
  R_BUDGET=UNRESOLVED, Static Gate=FAIL, activation NOT_ALLOWED.

## Review Focus

- MATCH of two recorded FAIL bundles must display both FAILs, not quality PASS.
- Global FAIL with zero failed cases must retain the global failure-record count.
- Default JSON/explicit JSON must remain R66-byte-compatible; Markdown must use the same single comparison result, not reopen inputs.
- Invalid operands/formats or malformed renderer records must never produce partial stdout, unsafe active content or a normal DIFFERENT result.
- Human report must preserve sorted full SHA/size and baseline/candidate direction without suggesting visual or origin qualification.

### Task 1: Pure summary and optional CLI presentation

**Files:** create tools/cyberlateral_cloud/browser_compare_summary.py,
tests/test_browser_compare_summary.py, docs/SAVED_BROWSER_COMPARE_SUMMARY_R67_KO.md;
modify browser_compare.py, tests/test_browser_compare.py and cloud README.

**Interfaces:** consumes `compare_saved_browser(Path, Path) -> dict` schema1;
produces `render_comparison_summary(result: dict) -> bytes` and the optional CLI
format. One cohesive deliverable, no inter-task shared interface.

- [ ] Step 1: Run full baseline gate with ci_verify.py (existing app/SDK interpreters).
  Expected: 161 tests / 23 own compiles / Ruff, Ty, Codespell PASS. Commit spec/plan.
- [ ] Step 2: Write literal renderer tests for full MATCH/DIFF facts, same/global
  FAIL, direction, full SHA/size, deterministic non-mutating bytes, invalid records
  (types/bools/counts/order/path/hash/receipts/provenance); run new suite.
  Expected: RED assertions for missing renderer, not fixture errors.
- [ ] Step 3: Implement the pure renderer only. Run new renderer suite.
  Expected: GREEN, no input mutation or file/browser/model access.
- [ ] Step 4: Add real-file CLI tests for Markdown MATCH/DIFF/FAIL, deterministic
  UTF-8 under ASCII locale, corrupt/partial either side, invalid format, default/
  explicit JSON parity and import isolation. Run comparison suite.
  Expected: new Markdown tests RED on absent format switch; old R66 tests GREEN.
- [ ] Step 5: Implement `--format` choices with default json; render once inside
  the existing guarded comparison call, write UTF-8 bytes only for Markdown.
  Run renderer+comparison suites. Expected: GREEN; JSON/default/exit semantics unchanged.
- [ ] Step 6: Write new Korean guide and README link (no tests of human prose).
  Run full cloud gate. Expected: 161 + actual new methods, 25 own compiles, static PASS.
- [ ] Step 7: Run actual retained saved inputs twice each: self/copy MATCH,
  two valid different bundles, identical global FAIL, both-side corrupt/partial;
  expected 0/1/2 and independent raw hashes/sizes/recorded states, same output
  twice, unchanged input content/modes/path sets and R66-default-JSON bytes.
- [ ] Step 8: Commit feature; rerun full gate and record task completion.
  Expected: fresh all PASS; focused actual consumers involve no new model/browser.

## Finish

Fresh whole-branch review with Review Focus and ledger decisions; re-grade,
Critical/Important fixed in one TDD pass, minors deferred. Keep feature locally
with verified report/evidence and clearly state whether GitHub/CI were run.
No main merge/HF publication this task. Seal two deterministic evidence ZIPs;
verify CRC/closed Manifest/source/recorded consumers independently. Preserve scratch.

Self-review: all requirements and five review-focus lines map to real behavior
tests and saved consumers. One task, no cross-task interfaces or hidden new policy.
