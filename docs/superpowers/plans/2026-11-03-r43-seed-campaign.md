# R43 Seed Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** One bounded multi-seed synthetic run with validated child evidence and an honest aggregate verdict.

**Architecture:** Sequential unchanged R42 calls; a bounded evidence helper verifies saved bytes and closure before the runner aggregates. Thin opt-in CLI, no public model change.

**Tech Stack:** Existing CPython3.12.13/stdlib, unchanged DEV dependencies and R40/R39 workers.

**Spec:** docs/superpowers/specs/2026-11-03-r43-seed-campaign-design.md

## Global Constraints

- Builtin list1..4 unique uint32 seeds, cases1..16, steps16..256; explicit order, max16384samples.
- Public0.3.0 model/API/wheel, oracle/generator, locks/dependencies unchanged; no actual vehicle/F61/r/dt/native work.
- Child capture2048files/128MiB,16MiB/file/depth16; campaign root8192files/512MiB. No-follow regular files only.
- All closed gates exact, whole reproducers/state preserved, no tuning/minimization/elapsed-time claim.
- New output only; fatal/malformed/source/child changes preserve partial data without CAMPAIGN.json.
- Publish reviewed feature PR only; main/HF stable97191972 stays unchanged; preserve worktree/evidence.

## Review Focus

- Later completed ERROR must outrank an earlier numerical DIFFERENT without losing either finding.
- Duplicate/bool/subclass parameters and malformed child record/count types cannot inflate successful coverage.
- Rehashed contradictory/extra/missing/late-mutated child files and linked directories cannot qualify as complete.
- Whole reproducer/seed/source bindings and final-marker ordering must survive partial worker/IO failures.
- Aggregate portable determinism must not claim private logs/receipt Manifest equality or physical/rate-policy authority.

## Task 1: Complete campaign runner, evidence boundary and CLI

Files create integration_tools/scenario_campaign_evidence.py, scenario_campaign_run.py,
tools/scenario_campaign.py, project/test_scenario_campaign_evidence.py,
project/test_scenario_campaign.py, project/test_scenario_campaign_cli.py under tools/cyberlateral_dev.
Modify tools/cyberlateral_dev/README.md; create docs/SCENARIO_CAMPAIGN_R43_KO.md.
Interfaces exactly as spec; evidence helper→runner→CLI, no other task dependency.

- [ ] Evidence tests first: closed real files/nested/portable hashes; modified/extra/missing bytes,
      file/directory symlinks/FIFO, size/count bounds. Run focused evidence module: expected RED (missing module), then GREEN.
- [ ] Runner tests first: real2seeds[42,43]/1case/16steps→MATCH/model32/reference32;
      strict bad parameters create no output; unchanged gates, order and deterministic records.
      Actual wrong saved projection under real R39→DIFFERENT, full reproducer16samples;
      reference worker ERROR for first seed still preserves later seed; both statuses visible.
      Fatal second seed preserves first with no marker; late source/child mutation and malformed returned/saved
      fields fail closed. Run focused runner: expected RED then GREEN.
- [ ] CLI tests first: real command32steps, help/unknown flags/missing/duplicate seed/output collisions,
      real error exits and no forbidden frontend imports. Expected RED then GREEN.
- [ ] Add thin CLI/source identity and Korean docs, re-run all campaign tests (expected all PASS).
- [ ] Full unchanged component gate (all discovered tests/static/own compile/wheel checks PASS),
      full cloud ci_verify (91/static/12compile PASS), explicit two campaigns [42,43]/2cases/32steps
      each128 model/reference + R34 MATCH64samples per seed, no tolerance. Log actual totals.
- [ ] Commit implementation; fresh whole-branch reviewer from97191972. Important fixes ONE RED→GREEN
      pass + full green suite; minors/rulings ledgered. No second reviewer.
- [ ] Normal push/new PR/attach, verify exact-head cloud/app/root CI and artifacts; do not merge main or upload HF.

## Bookkeeping

Native inline under prior user delegation; existing clean named linked worktree reused.
Cloud skill helpers expose no local executable path; equivalent briefs/BASE/commands/outcomes
are recorded in this plan's external ledger. Baseline9 generator cases PASS; real R42 smoke next.
One task so setup/docs stay with the deliverable rather than creating artificial review boundaries.
