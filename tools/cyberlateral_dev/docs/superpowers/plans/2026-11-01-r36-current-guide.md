# R36 Current Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Track steps with checkbox (`- [ ]`) syntax.

**Goal:** Give current offline developers one accurate entry point without rewriting history.

**Architecture:** README points to a new guide and source-backed JSON inventory.
Existing R30 files remain historical and byte-unchanged. No executable behavior changes.

**Tech Stack:** Markdown/JSON; existing CPython3.12.13/Linux DEV CLI and verification gate.

**Spec:** ../specs/2026-11-01-r36-current-guide-design.md

## Global Constraints

- Reviewed baseline3da79e367fcc851377d83caa88e3665f175acff6; isolated feature branch.
- Only component README and four new docs/spec/plan/JSON files may change.
- Preserve R30 documents, all Python/tests/fixtures/lock/public0.3.0/wheel/workflows.
- No external writes, push/PR/merge/CI dispatch or notebook update in this task.
- All execution is declared synthetic; no F61/r/dt/Controller/native/vehicle Runtime/CAN.
- R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/scale null; Candidate/Runtime
  NO_GO; SOURCE_SCHEMA_UNQUALIFIED6000; F70UH/V/F71 NOT_ALLOWED.

## Review Focus

- Public wheel CLI is not the separate DEV JSON runner.
- Historical snapshots must not become false statements of current availability.
- Static inventory/snapshot counts must not pretend to be fresh execution evidence.
- Shell output paths must be fresh and outside component and inputs.
- Expected mixed exit1 and portable sharing subsets must not be treated as crashes or complete inputs.

### Task 1: Publish an accurate local current entry point

**Files:**
- Modify: README.md.
- Create: docs/OFFLINE_QUICKSTART_CURRENT_KO.md.
- Create: docs/OFFLINE_CAPABILITY_INVENTORY_CURRENT.json.

**Interfaces:**
- Consumes: existing step/simulate/fixed CLI, scenario.py/report/batch/compare,
  verify_project and R35 reference source at the reviewed baseline.
- Produces: operator instructions and SHA/symbol-backed static availability records;
  no executable module, validation API or new feature flags.

- [ ] Verify clean baseline suite; inspect actual sources/options before writing claims.
- [ ] Write guide/inventory and update README links; retain byte-identical R30 files.
- [ ] Validate cited source SHA and AST symbol/JSON pointer; validate relative links.
- [ ] Run actual CLI help; installed sealed wheel rejects --input with exit2.
- [ ] Run documented R31 sign example→R32 report; expect4 saved steps/[2,-2,0,2], renderer0.
- [ ] Run two basic R33 batches; each2complete/5steps/exit0; compare MATCH/sample5/diff0/newmodel0.
- [ ] Rehash all manifests and compare portable bytes directly; preserve original input/source bytes.
- [ ] Run fresh full dev.py verify; expect suite/static/compile/wheel PASS, dynamic counts from SUMMARY.
- [ ] Review and commit only five docs files locally, obtain one independent final review.

No new unit tests are justified for human prose. Use actual command behavior and
artifact/source checks rather than tests that grep exact documentation wording.
