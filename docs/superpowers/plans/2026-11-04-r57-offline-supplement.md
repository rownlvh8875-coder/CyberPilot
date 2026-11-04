# R57 Offline Supplement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Make existing R50–R56 offline error boundaries discoverable without rewriting historical authority.
**Architecture:** One pinned human supplement and two entry paragraphs; existing implementation unchanged.
**Tech Stack:** Markdown, existing CPython3.12.13/uv0.12.23/stdlib verification.
**Spec:** docs/superpowers/specs/2026-11-04-r57-offline-supplement-design.md

## Global Constraints

- Base6dfb5174a6516c53f64cc0351ac10382cc9485ef; original feature branch/env/evidence preserved.
- Only new supplement, two entry paragraphs and this spec/plan. No permanent tests of prose.
- Inventories byte-exact; old quickstart/README bytes exact after removing the new paragraphs.
- No product/math/schema/wheel/lock/dependency/cloud/CI or live HF changes.
- r/T2/scale null, StaticFAIL, Candidate/Runtime NO_GO, no vehicle/F61 activation.

## Review Focus

- R37 JSON rejection versus other CLI stderr, especially exit2/no identity/no model.
- Valid surrogateescape reader support versus UTF8 execution/receipt constraints.
- R54 overlong input can reach the owned reader; do not overclaim pre-read rejection.
- R56 constructor handler versus later cleanup/primary stderr failure propagation.
- Historical review/test/restore identities versus current HEAD and vehicle authority.

### Task 1: Publish the bounded human supplement

**Files:** Create tools/cyberlateral_dev/docs/OFFLINE_HARDENING_R56_KO.md;
modify tools/cyberlateral_dev/README.md and docs/OFFLINE_QUICKSTART_CURRENT_KO.md.
**Interfaces:** Consumes existing source/guide contracts. Produces human entry links
and literal Bash examples, not a new API or schema.

- [x] Snapshot baseline/historical hashes and read original source boundary blocks.
  Expected exact baseline and clean scoped branch; no shared task interfaces.
- [x] Write the guide and two entry paragraphs only. Expected accurate code/ordering
  table, explicit limitations and three literal executable blocks.
- [x] Execute the blocks in one fresh shell and external output directory; assert
  valid R37 exit0, missing-input R37 exit2/null identity/model0/empty stderr,
  R56 ten existing methods PASS, immutable source/examples and no product outputs.
  Expected controlled exit2 remains visible; no new mathematical example.
- [x] Check every local entry/supplement link; compare old inventories and remove
  only the exact new paragraphs before comparing historical entry-file hashes.
  Expected no broken link or other old-document changes.
- [x] Run locked full DEV883/cloud91, Ruff/Ty/Codespell and compiles; compare stable
  numerical/report/wheel hashes with sealed R56 baseline. Expected PASS/unchanged.
- [ ] Commit scoped docs; fresh committed command/link recheck, one independent
  whole-branch review, at most one Important/Critical correction pass with proof.
- [ ] Normal feature push/create/attach PR, actual CI/artifacts and deterministic
  delivery seal. Expected explicit skips separate, main/HF unchanged.
