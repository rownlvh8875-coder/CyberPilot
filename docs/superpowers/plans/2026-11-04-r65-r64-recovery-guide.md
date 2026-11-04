# R65 Pinned R64 Recovery Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans; owner already delegated inline execution.

**Goal:** Make pinned cloud recovery include the merged passive saved-browser check.

**Architecture:** Documentation only: new versioned R64-tool/R61-source recipe,
current README body update with historical R62 link; existing runtime unchanged.

**Tech Stack:** Markdown, existing Git/locked SDK/app/explicit host browser tools.

**Spec:** docs/superpowers/specs/2026-11-04-r65-r64-recovery-guide-design.md

## Global Constraints

- Base/tool af4523c05c24ea2c9368a869c0cf9f4df0f54590 / tree a2cab555bc0e74c633aa7d118c15f8f307d59dde.
- Archive source e5b76678cff4d45a4915da0f9b26982711167b1d, existing SHA/revision per spec, no relabeling/latest.
- No Python/API/tests/app/locks/workflows/rootREADME/old-guide edits or HF writes/main merge.
- Reader stdout outside closed browser root; failures preserve partial outputs and omit completion marker.
- Existing prepared Linux host/uv/Python/auth/proxy/browser prerequisites, no global/browser install or implicit Python download.
- Preserve all workspaces/evidence and closed vehicle/r/static gates; DEV883/wheel inherited only.

## Review Focus

- Three identities confused: document, tool and archive source must remain explicit and independently checked.
- Reader receipt contaminates closed tree: outside output path and byte-preservation check, never place debug files in browser/.
- Failure mislabeled success: set-eu/nonzero propagation and separate WORKDIR versus final completion marker; no skip/fallback.
- Historical instructions broken: old R62 guide byte-exact, current heading/anchor and remaining README body preserved.
- Scope inflation: actual two logical roots share a physical host, R41 is synthetic nonzero, reader/browser claims do not grant source/vehicle authenticity.

### Task 1: Versioned workflow and real consumers

**Files:** create tools/cyberlateral_cloud/docs/RECOVERY_R64_KO.md; modify current
section body of tools/cyberlateral_cloud/README_KO.md. No new production signatures.

**Interfaces:** existing cloud_restore CLI with old-source --commit; browser_smoke
CLI and browser_verify --input. No inter-task/shared interfaces.

- [ ] Baseline full cloud gate, expected141/21/static PASS; commit spec/plan.
- [ ] Write exact pinned single Bash recipe per spec and current README update.
Expected four Markdown paths only including spec/plan; no historical guide edit.
- [ ] Execute actual new document block twice in fresh roots. Expected441source
records/bytes/modes, R41 portable26PASS, browser10PASS/37closed entries/18links,
reader0/recordedPASS/38files/false source authentication, zero browser mutations.
Compare summary/HTML/VIEW bytes to canonical R64 feature proof and both runs.
- [ ] Verify all current local links, old guide SHA, preserved README section
heading and all following bytes/anchors; all21Python/app/context/locks/workflows
Git equality. Full cloud141/21/static expectedPASS, no new unit methods/RED claim.
- [ ] Commit documentation and run full cloud unit repeat141PASS; ledger completion.

## Finish

- One fresh whole-branch review; Important/Critical fixes only, no re-review;
all declined assurances ruled and minors deferred.
- Normal feature push/Draft PR/attach and actual exact-head CI artifact, remaining
checks success/SKIP. Main and HF remain unchanged.
- Two deterministic ZIPs, independent bounded closure/identity/consumer checks,
final live Git/PR/HF receipt outside immutable ZIP. Retain evidence workspace.

Self-review: one task/no shared interfaces; each focus has a specific document,
preservation or actual consumer check. Human prose earns no artificial unit tests.
