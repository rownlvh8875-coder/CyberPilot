# R30 Offline Development Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** source-backed bounded offline acceptance, usable quickstart and Draft preparation.

**Architecture:** documentation-only additions and README navigation; existing
runtime/build/test/native code stays byte-identical. Fresh relocated execution
and actual remote receipts substantiate acceptance, not new wrapper APIs.

**Tech Stack:** existing CPython3.12.13/uv0.12.23/public0.3.0/pinned native tools.

**Spec:** `docs/superpowers/specs/2026-10-31-r30-offline-acceptance-design.md`

## Global Constraints

- No existing Python/reference JSON/model/build/lock/workflow changes; no new runtime API.
- Baseline cc8d294a0312e1cc3316aafacb7a76ac1fe54024; exact source SHA/symbol citations.
- Fresh full pure440 tests/141 own compilations; public wheel identity exactly as spec.
- Native only explicit pinned fresh environment; historical portable outputs unchanged.
- No F61/Controller/Runtime/CAN/actual input/r/dt/main merge/install/activation.
- R_BUDGET UNRESOLVED, Static Gate FAIL; only bounded offline milestone accepted.
- Whole CyberPilot product requirements NOT_ESTABLISHED, not guessed from upstream README.

## Review Focus

- An implemented programmatic API must not be reported missing merely because CLI is fixed.
- Inherited upstream openpilot capabilities must not be claimed as newly implemented CyberLateral features.
- Guide commands must select the isolated component and run from a fresh path without root dependency setup.
- Native input observations must not promote model output to CAN wire or actual-history custody.
- Local test success must not imply exact-final-head CI success, main merge permission or product completion.

### Task 1: source inventory and quickstart

**Files:** create `docs/OFFLINE_CAPABILITY_INVENTORY_R30.json`,
`docs/OFFLINE_ACCEPTANCE_R30_KO.md`; modify component `README.md` navigation only.

**Interfaces:** source citations consume existing module functions/config/CLI;
guide produces existing root-level pure/report/native commands, no new interfaces.

- [ ] Record goal authorities, exact source hashes/symbols, implemented/limited/unestablished statuses; verify against current code.
- [ ] Write guide pure/install/report/native commands with fresh output paths and explicit prerequisites, no hardware setup.
- [ ] Document scoped acceptance vs product/merge/vehicle limits and prospective synthetic-CLI recommendation.
- [ ] Validate JSON, citations and Markdown links; Codespell and existing provenance tests PASS. Commit `[skip ci]`.

### Task 2: fresh acceptance and handoff

**Files:** create `docs/OFFLINE_ACCEPTANCE_R30_RESULTS.md`; external workspace preserves all evidence.

**Interfaces:** consumes Task1 commands and unchanged runners, yields actual acceptance/CI/Draft receipts.

- [ ] Archive committed component/workflow/root README to a fresh path, create fresh dev/native/runtime envs.
- [ ] Execute guide pure440-test command, standalone build/install/report, optional fixed R27/R28/R29; exact expected bytes/manifests/data checks pass.
- [ ] Check all native static/compile, baseline code/wheel/original10 guards and complete report equality.
- [ ] Fresh whole-branch reviewer; adjudicate all exclusions and fix only Important/Critical once if needed.
- [ ] Commit actual results, normal feature push, exact-final-head pure CI PASS with94 artifact hashes verified; Draft PR2 preserved/updated, no merge.
- [ ] Seal evidence deterministically twice; fresh extraction/CRC/all checksum manifests PASS; final scoped report, no whole-product completion claim.
