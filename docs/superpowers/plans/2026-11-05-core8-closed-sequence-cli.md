# CORE8 Closed Synthetic Sequence CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline execution without repeated approval questions.

**Goal:** Run three closed synthetic sequence fixtures and retain portable diagnostics/checksums.
**Architecture:** Inert case catalog and frontend, verified existing local model
loader, unchanged CORE7, exclusive three-file publication and a thin CLI.
**Tech Stack:** Existing CPython3.12.13/stdlib/unittest/Ruff/Ty/Codespell; no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core8-closed-sequence-cli-design.md

## Global Constraints

- Base82754868d8dd4d6824f1361419ebeecc96f93dd0, existing host worktree/local stacked branch.
- Only named built-in cases, exact literal fixtures/status/exit/schema/guards from spec; no input/r options.
- Case/output guard before model load/calculation/publication; whole CORE7 preflight remains unchanged.
- Persist raw/hex/declared/computed roles, no repair/rollout or empty-input MATCH.
- Source before/after and CLI hash observed, not vehicle/authenticity authority.
- Exclusive new outside-checkout directory, three canonical files, Manifest last; no overwrite/cleanup.
- Non-preflight/model/IO failure cannot masquerade as zero-work rejection or completed package.
- No old CORE1~7/runtime/src/lock/workflow/imported/profiles/public-wheel changes.
- Frozen wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- Existing unresolved/null/FAIL/NO_GO/NOT_ALLOWED gates retained; no actual input/F61/runtime/r.
- No push/merge/PR/HF/CI/network/cleanup; retain prior refs/worktree/evidence.

## Review Focus

- Unknown cases/invalid output/CLI help or syntax must not load/run the model or write source/existing output.
- Saved DIFFERENT and REJECTED must retain exact distinct semantics/exit codes, not success or repaired data.
- Source or late calculation failure must not publish completed zero-work artifacts; partial IO remains explicit/untrusted.
- Portable hex data/rows/Manifest must be canonical, complete, repeatable and preserve raw input roles.
- Local source bytes and checksums must not grant anchor/history/actual-source/r-policy/vehicle authority.

### Task 1: Closed sequence execution/export

**Files:** create integration_tools/core_sequence_cases.py,core_sequence_run.py,
tools/core_sequence.py,project/test_core_sequence_run.py,
docs/CORE_SEQUENCE_CLI_CORE8_KO.md in component; modify component README/backlog.
**Interfaces:** CASE_IDS/build_case(str), run_sequence_case(object,Path)->dict,
DemoError.code,exit_code(dict)->int; CLI --case/--output. Existing loader/CORE7 unchanged.

- [ ] Immutable baseline fullgate1065tests/248compiles/static/wheel PASS.
- [ ] Commit spec/plan before code; external ledger/BASE for non-mounted skill scripts.
- [ ] Tests first for exact3literal cases/states/exits, rawhexinput/differences/gates,
  canonical repeat/Manifest, guard failures before model, no source/overwrite/symlink writes,
  loader/source drift/nonpreflight failure/partial IO, fresh lightweight import/help/unknownargs,
  realCLI -I -B from arbitrarycwd and byte-identical outputs. Expect missing-feature RED.
- [ ] Implement inert catalog/frontend/exclusive publication/thin CLI per spec;
  focused GREEN/scoped Ruff/Ty/Codespell PASS. Numerical expectations use literals.
- [ ] Usage guide/README/backlog include exact runnable command,3exit codes,
  integrity/partial-work/fixture-only/source-authority limits and maintained gates.
- [ ] Commit implementation; clean source fullgate1065+actual new tests/252compiles/
  static/wheel PASS. One fresh read-only whole-branch review may overlap.
- [ ] Independent fresh actualCLI 3cases twice; exact literal outcomes and byte/
  Manifest equality, guard checks. One TDD fix pass if Critical/Important; minors ledgered.
- [ ] Actual source custody/Manifest/wheel/refs/cloudconsumer checks, external
  report/result; preserve local branch/evidence, no remote publication.

Self-review: one independently testable workflow task; no cross-task conflicts.
All5Review Focus classes have concrete tests. No arbitrary external reader or new model policy.
