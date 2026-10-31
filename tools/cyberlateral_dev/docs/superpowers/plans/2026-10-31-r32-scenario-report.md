# R32 Scenario Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** verified saved R31 data→graphs/state table, no new model invocation.

**Architecture:** separate bounded data reader/validator, static HTML renderer,
exclusive publisher and thin DEV CLI. Preserve old producer/public/native code.

**Tech Stack:** pinned CPython3.12.13 stdlib, unittest, existing pinned DEV tools.

**Spec:** `docs/superpowers/specs/2026-10-31-r32-scenario-report-design.md`

## Global Constraints

- Exact6 source files; five-entry canonical SHA manifest before validation/render.
- Caps INPUT/TRACE1MiB, RESULTS16MiB, SUMMARY16KiB, RECEIPT512KiB, manifest4KiB.
- Strict canonical JSON, float128/int32 token chars/nesting64; exact types/hex/R31 domains.
- Check full row shapes, stored aliases/state chain and inert R31 byte projections;
  never re-evaluate model math or authenticate declarations/producer raw-input SHA.
- Separate portable index.html/VIEW.json and actual receipt; output checksum3entries.
- Escape all HTML, static SVG/CSP, invocation-order axis, no JS/network/external assets.
- Guard output before input read; no output under input, overwrite or destructive rollback.
- No changes to public source/wheel, R31 producer, old native/workflow/build/lock.
- No new model/native work in renderer. Existing unit/CI model work is additional.
- Closed production gates unchanged. Final publication receipts are external to
  avoid HEAD/CI/seal self-reference; plan is preregistration, not future PASS.

## Review Focus

- Rehashed but internally inconsistent source records must reject; consistent
  fabrication must never be presented as authentic or independently calculated.
- Historical R31 producer inventory must not be confused with current renderer identity.
- Final symlinks/FIFO/oversize/missing/extra files and output inside source must not read/write unexpectedly.
- Single/flat/4096-call/resumed/signed-zero views must retain exact data and distinct requested/applied history.
- Renderer must not import/run model or follow recorded paths; no private receipt data in portable HTML.

### Task 1: bounded R31 result reader and consistency projection

**Files:** create `integration_tools/scenario_report_data.py`,
`project/scenario_report_fixture.py`, `project/test_scenario_report_data.py`,
`project/fixtures/r31_report/{sign,resumed}/{INPUT.json,RESULTS.json,TRACE.csv,SUMMARY_KO.md}`
and fixture provenance README.

**Interfaces:** `ReportError(code)`, `read_report(path:Path)->dict` containing
`view` (validated internal dict) and `source_hashes` (all6 owned hashes).
No model imports. Task2 renders only this internal view, not arbitrary dicts.

- [x] Capture8 immutable portable fixture files from sealed R31 examples; construct
  receipt/manifest only in test helper. Literal sign final[2,-2,0,2], resumed counter90/bitfalse.
- [x] Write failing reader tests: real fixture values, canonical checksum JSON,
  rehashed mismatch in CSV/summary/flags/types/shape/state/final/identity/gates,
  unknown root/nested keys, caps/duplicates/nonfinite/depth, symlink/FIFO/extras,
  old producer hashes accepted as metadata, no model/native import.
- [x] Run `uv run --locked python -B -m unittest discover -s project -p test_scenario_report_data.py -v`;
  Expected: missing reader FAIL. Implement reader and exact stored-data crosschecks.
- [x] Same command and targeted Ruff/Ty/Codespell:PASS; commit `[skip ci]`.

### Task 2: static report renderer and file CLI

**Files:** create `integration_tools/scenario_report_html.py`,
`integration_tools/scenario_report_run.py`, `tools/scenario_report.py`,
`project/test_scenario_report_cli.py`.

**Interfaces:** `_render_html(view:dict)->bytes` internal validated data only;
`run_report(input_path:Path,output_path:Path)->dict` consumes Task1, emits4 files
index.html/VIEW.json/RECEIPT.json/SHA256SUMS.txt, index last.

- [x] Write failing tests for two graphs/table/counts, exact literal stages,
  resumed/single/flat/signed zero, escaping/CSP/no external paths, source untouched,
  moved-bundle portable equality/receipt difference, invalid-last rejection,
  existing/dangling/missing-parent/nested output guards, IO fault/late collision,
  CLI argument behavior and fresh-process import tripwire.
- [x] Run `uv run --locked python -B -m unittest discover -s project -p test_scenario_report_cli.py -v`;
  Expected: missing CLI FAIL. Implement data-only renderer/publication/bootstrap.
- [x] Both new test files and targeted static:PASS; commit `[skip ci]`.

### Task 3: usage, complete checks and handoff

**Files:** create `docs/SCENARIO_REPORT_R32_KO.md`, `docs/SCENARIO_REPORT_R32_RESULTS.md`;
update component README navigation. No other legacy edits.

**Interfaces:** Task2 CLI, same saved R31 examples for all direct renderer runs.

- [ ] Document root-relative producer→reader quickstart, new-output guards,
  integrity-vs-authority limits and view semantics. No r/time/scale fallback.
- [ ] Full `uv run --locked python -B dev.py verify --output NEW` local and
  committed fresh snapshot:PASS; unchanged wheel77 imported files/old source guards.
- [ ] Renderer two examples x2 repeats x2 locations exact portable2 files; all
  source/output manifests, forbidden imports and zero new renderer model calls PASS.
  Inspect retained R31 native evidence pins/manifests/data-only tests; no new native execution.
- [ ] One fresh whole-branch review, dispositions; Important/Critical one TDD fix
  pass if needed, full suite green. Commit final docs, fast-forward feature push,
  exact-head pure CI/artifact, preserve Draft PR2 and main.
- [ ] Twice deterministic ZIP, CRC/fresh extraction/all manifests PASS; final
  external receipt/ledger closes publication without claiming future completion.
