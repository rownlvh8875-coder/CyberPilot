# R56 producer CLI cache-entry implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline.

**Goal:** Bound only producer CLI TemporaryDirectory constructor OS failures.

**Architecture:** Existing argparse → scoped constructor try → existing with-body.
No generic lifecycle helper, broad later catch, cache fallback or new IO code.

**Tech:** Pinned CPython3.12.13/Linux/stdlb/unittest and existing locked tools.

**Spec:** docs/superpowers/specs/2026-11-03-r56-cli-cache-entry-design.md

## Global constraints and review focus

- Existing four prefixes/codes/argparse priority and complete with-bodies retained.
- Only constructor OSError is consumed; entry, exit, later output/worker, non-OS
  errors and BaseException retain their old propagation semantics.
- No source/authenticity/atomicity or cleanup-reliability guarantee added.
- New BATCH_IO already belongs to R55; do not claim another new code.
- No math/schema/wheel/dependency/lock/cloud/CI or real policy/vehicle changes.
- Same host worktree reused, R55 read-only snapshot protected; no main advance
  until its sealed delivery. Keep all earlier branches/environments/evidence.

### Task 1: Bound four cache constructors

**Files:** Modify tools/cyberlateral_dev/tools/scenario_batch.py,
scenario_workflow.py, scenario_explore.py, scenario_campaign.py; create
project/test_scenario_producer_cli_cache.py; update the R33/R40/R42/R43 KO guides.

- [ ] Record exact main/same-tree873 baseline reuse and actual four mode000 failures.
  Expected no new baseline tests, input/model imports/output0.
- [ ] Write focused constructor/priority/propagation/state tests and run RED.
  Expected missing stable IO handling, existing controls green.
- [ ] Minimal four constructor boundaries and accurate limited docs, run GREEN.
  Expected stable existing IO/exit2; no capture of later defects/cleanup failures.
- [ ] With-body AST proof and same-path successful CLI parity with strict SHA
  dependency substitutions, closed manifests and immutable inputs/source.
- [ ] Full DEV/cloud gates, commit and fresh committed focused completion.
- [ ] One final whole-branch review; at most one TDD Important/Critical fix pass,
  ledger every minor and declined-to-judge boundary.
- [ ] Normal push/create/attach PR, actual CI/artifacts, deterministic seal;
  guarded main/private HF/two fresh restores after R55 operations finish.
