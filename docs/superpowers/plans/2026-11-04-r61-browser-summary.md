# R61 Browser Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an honest deterministic Korean reading aid to completed R60 outputs.

**Architecture:** A pure bytes renderer consumes the fresh result plus owned file
hashes. Existing exclusive publication writes summary before checksum and the
last RESULT marker. Browser observation/classification is unchanged.

**Tech Stack:** Existing stdlib Python3.12.13/cloud tests, host browser only for
explicit real verification; no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-04-r61-browser-summary-design.md`

## Global Constraints

- Baseline b01ae91e9858772099622f3c6c81a03afbe5fc04; existing linked worktree.
- No app/browser_probe/model/wheel/lock/default workflow changes.
- Preserve R60 stdout/RESULT V1 and exit0/1/2; no new reader CLI or browser calls.
- Fixed local existing links only; unknown observations are not zero defaults.
- Summary is not completion: closed checksum and last RESULT remain authority.
- No F61/actualr/dt/vehicle work, actualr/T2/scale null, closed vehicle gates.
- New external outputs only; retain evidence/old branches/environments.

## Review Focus

- Empty/duplicate/missing cases or PASS with recorded failures must not look successful.
- Global failures remain visible even when all ten case verdicts are PASS.
- Metadata markup and unknown/missing observations must not spoof facts or links.
- Missing/unsafe artifact paths must not become clickable outside the owned output.
- Summary/checksum publication errors must preserve last-marker/no-overwrite behavior.

### Task 1: Pure summary, integrated publication and proof

**Files:** Create cloud `browser_summary.py`, `tests/browser_result_fixture.py`,
`tests/test_browser_summary.py`; modify `browser_smoke.py`, its publication tests
and `docs/BROWSER_SMOKE_R60_KO.md`.

**Interfaces:** `render_summary(result: dict, file_sha256: dict[str,str]) -> bytes`
returns deterministic UTF8 Markdown or raises ValueError(BROWSER_SUMMARY_INVALID).
`publish_result(output,result)` retains its existing signature/marker contract,
adding only SUMMARY_KO.md to the complete closed output.

- [ ] Run baseline DEV883/cloud111 gates before product edits.
- [ ] Write literal independent fixture and failing tests for case table/failure
  preservation, contradictory/empty records, metadata escaping, unknown values,
  owned-only links, deterministic nonmutating output, checksum membership and
  summary-write failure without RESULT. Observe missing-feature RED.
- [ ] Implement pure renderer and minimal publication hook; expect new tests and
  entire cloud suite GREEN, with no browser import required by default tests.
- [ ] Document SUMMARY and its partial-output warning without changing old evidence.
- [ ] Run actual host browser command twice, expect10PASS each, unchanged report
  HTML/VIEW, exact summary bytes, valid links and closed manifests. Directly read summary.
- [ ] Execute old-CSS copied-source control, expect6overflow FAIL/exit1 and an
  accurately failing summary; runtime rejection remains2/no fabricated summary.
- [ ] Run final DEV/cloud full gates, Ruff/Ty/Codespell/compile and unchanged wheel.
- [ ] Commit feature, request one fresh whole-branch review; Important/Critical
  fixes in one RED/GREEN pass, record declined boundaries and deferred Minors.
- [ ] Normal feature push/Draft PR, attach, inspect actual scoped CI/artifact;
  preserve branch and seal two reproducible independently verified evidence ZIPs.
  No main merge/HF publication in this feature task.

Self-review: one task/no shared task interfaces. Each Review Focus is explicitly
owned by the renderer/publication tests or actual browser controls above.
