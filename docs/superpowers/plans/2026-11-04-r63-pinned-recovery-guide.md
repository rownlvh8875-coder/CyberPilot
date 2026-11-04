# R63 Pinned Recovery Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the verified dual-pinned recovery recipe in Git and make it easy to find.

**Architecture:** Documentation only: exact sealed recipe copy and an early README
link/context paragraph. Existing code, historical instructions and anchors unchanged.

**Tech Stack:** Markdown; existing Git/locked SDK/app/explicit host browser consumers.

**Spec:** `docs/superpowers/specs/2026-11-04-r63-pinned-recovery-guide-design.md`

## Global Constraints

- Baseline1b244fe8e2dee8636ce7811529978d9499cfedc8, existing linked worktree.
- Copy exact canonical R62-main note; no new source/API/config/policy functionality.
- Fixed tool/source identities are different and must remain so; no mutable latest.
- Historical README body/anchors, HF objects and old evidence preserved.
- No product Python/locks/workflows/root README edits, new permanent tests, fake RED,
  new DEV gate/build claim, main merge/HF write or vehicle activation.

## Review Focus

- Documentation revision mistaken for tool/source commit: explicitly distinguish all three.
- Existing R48 guide/anchors damaged: old README bytes must survive unchanged.
- Copy/paste commands rely on old workspaces: actual bash consumer in fresh roots.
- False scope from PASS: model/host/CI/vehicle boundaries remain explicit.
- Broken discoverability: new relative link resolves to the exact pinned recipe.

### Task 1: Durable recipe and consumer proof

**Files:** create `tools/cyberlateral_cloud/docs/RECOVERY_R62_KO.md`; modify cloud
`README_KO.md`. No new public signatures or runtime imports.

- [ ] Baseline full cloud gate122/19compile expectedPASS; verify clean base.
- [ ] Verify canonical parent ZIP SHA/CRC/closure and note hash; copy exact UTF8
  note bytes with apply_patch. Expected same guide hash, not a rewritten recipe.
- [ ] Insert early README link/current-vs-historical/document-vs-tool paragraph;
  expected original complete body/anchors unchanged after removing that insertion.
- [ ] Execute the repository document's exact single bash block twice in fresh
  roots; expected distinct Git/SDK/app roots, archive sourceR61/toolR62,441actual
  records/bytes/modes equivalent to pinned tool export, R41PASS, browser10PASS each,
 37closed entries/18links, exact summary/fourHTML/VIEW across both and sealed parent.
- [ ] Full cloud gate122/static19 expectedPASS; product Python/DEV/locks/workflows
  diff empty. Full cloud unit repeat expected122PASS, new unit methods0.
- [ ] Commit documentation; one fresh whole-branch review with five focus checks.
  Important/Critical fixes only, Minor ledgered; no re-review round.
- [ ] Normal feature push/Draft PR/attach/exact-head CI artifact; main/HF unchanged.
- [ ] Two identical deterministic evidence ZIPs; independent bounded verification.

Self-review: one task/no shared interfaces. Focus checks map to context paragraph,
byte preservation/link validation, actual consumers and scope review. Human prose
is verified through its consumers rather than source-text unit tests.
