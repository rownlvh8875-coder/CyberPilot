# R49 Current Offline and Cloud Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Current entry points describe and demonstrate the reviewed R48 offline/cloud workflow.

**Architecture:** Documentation-only revision of the existing quickstart/inventory,
DEV README and cloud README. Explicit pinned baseline; reuse every existing CLI.

**Tech Stack:** Existing Bash, uv0.12.23, CPython3.12.13, stdlib verification.

**Spec:** `docs/superpowers/specs/2026-11-03-r49-current-cloud-guide-design.md`

## Global Constraints

- No product code, model/reference/generator/limiter, wheel0.3.0, lock/dependency,
  CLI/schema, archive format or CI implementation changes.
- Reviewed baseline d599d53c96dd965545da368ea699b661d1d07907; historical records preserved.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null.
- Candidate/Runtime NO_GO; F70UH/F70V/F71 and actual activation NOT_ALLOWED.
- No F61/actual r/dt/vehicle/Controller/Runtime/CAN execution.
- Feature PR only; no main merge/HF write, credentials or environment publication.

## Review Focus

- A static pinned inventory must not be mistaken for fresh execution or current HEAD.
- Complete campaigns/comparisons and portable subsets are not interchangeable.
- R46 report exit0 must not promote source ERROR/DIFFERENT to numerical success.
- Invocation counts are not elapsed time; recorded equality is not a new oracle.
- Reusing existing outputs or editing a registered restore snapshot must be discouraged.

---

### Task 1: Update and execute current usage entry points

**Files:**
- Modify: `tools/cyberlateral_dev/docs/OFFLINE_QUICKSTART_CURRENT_KO.md`
- Modify: `tools/cyberlateral_dev/docs/OFFLINE_CAPABILITY_INVENTORY_CURRENT.json`
- Modify: `tools/cyberlateral_dev/README.md`
- Modify: `tools/cyberlateral_cloud/README_KO.md`

**Interfaces:**
- Consumes: existing R31–R48 CLIs, source-pinned d599d53c Git objects and verified
  private R48 HF receipts. No new runtime interface is introduced.
- Produces: copyable Bash examples and static source inventory; external execution
  receipts/closed Manifest verification only, not new model/reference behavior.

- [ ] Verify clean named linked worktree, new branch from exact origin/main;
  run existing R44 tests. Expected:41PASS and no user changes.
- [ ] Update the four entry points and inventory source records at the pinned
  baseline. Expected: no runtime source changes or credential/private paths.
- [ ] Execute literal quickstart Bash blocks in order, excluding no commands;
  retain output logs and validate R31/R33/R34 plus R43 two128-step campaigns,
  R44 MATCH/128/diff0 and same-input R46 repeat HTML/VIEW equality.
  Expected: existing paths not overwritten; closed Manifests; source immutable.
- [ ] Verify every inventory path/hash/symbol against baseline Git bytes and every
  local guide link. Expected: complete known capability/source references.
- [ ] Run full `dev.py verify` and cloud `ci_verify.py` in new external directories.
  Expected: all existing804DEV/91cloud tests,225/12compiles and static PASS,
  unchanged public wheel SHA; read actual counts, never manufacture them.
- [ ] Commit docs; completion check reruns inventory/link/output verification.
  Expected: no stale anchor/hash and no runtime diff. Read the whole diff in a
  fresh final branch review; preserve scoped findings/rulings.
- [ ] Create feature PR and attach it; verify actual exact-head CI/artifacts;
  seal two identical evidence ZIPs and independently verify SHA/CRC/Manifest.
  Expected: feature delivered, main/HF unchanged in this stage.
