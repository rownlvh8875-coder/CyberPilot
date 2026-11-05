# R70 Recorded Trace Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans;
> owner delegated inline implementation and ordinary offline choices.

**Goal:** Explain recorded clip/state changes without rerunning the model.
**Architecture:** Existing owned-byte R31 validation, exact scalar comparisons,
small detached aggregate and separate stdout JSON/Markdown CLI.
**Tech Stack:** Existing CPython3.12.13/stdlib/dev lock/venv; no installs.
**Spec:** docs/superpowers/specs/2026-11-05-r70-recorded-trace-summary-design.md

## Global Constraints

- Base1cd6ed64b8700641875fa6d5eebf95e125e89411; local feature branch, host worktree retained.
- New backend/CLI/one test/doc and README paragraph only; no old readers/src/77/locks/workflows/profiles edits.
- Version0.3.0/frozen wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- Existing six-file bounds/schema/Manifest/alias/gate validation before counting; no path reopening/metadata IO.
- Seven event names, output fields and exact numeric/representation semantics exactly as spec.
- Cold private CLI cache; no input writes/model/reference/SDK/native/policy/actual vehicle work.
- No push/PR/main merge/HF/CI dispatch; retain all external ledger/evidence.
- Unresolved/null/FAIL/NO_GO/NOT_ALLOWED gates unchanged; unit/gate synthetic work NONZERO.

## Review Focus

- Same numeric value with different scalar kind or signed zero must not be labeled a numeric limiter change.
- Int64 outside binary64 exact-integer range must not collapse to a float-equal value during comparison.
- Late malformed rows/false gates/path tricks must not produce a partial or apparently valid summary.
- Resumed sample index and recorded suppression must not become zero-based offset, zero command or elapsed-time claims.
- Coherent resealed records and inherited source hashes are consistency evidence, not arithmetic/origin authentication or vehicle approval.

### Task1: Owned-byte recorded aggregation

**Files:** create integration_tools/scenario_trace_summary.py and project/test_scenario_trace_summary.py under tools/cyberlateral_dev.
**Interfaces:** consume scenario_report_data._files/decode_report/_json/ReportError;
produce summarize_saved_trace(Path)->dict with exact spec fields/events. Task2
consumes this function, existing canonical and ReportError; no interface conflict.

- [ ] Fresh dev.py verify baseline expected883/231/static/wheelPASS; commit spec/plan before product changes.
- [ ] Write failing real-fixture tests. Assert sign literal events0/4/4/4/0/0/0 and old inactive-change1;
  resumed fault first index5 and suppression1/final-2; coherent counter89->0 reset first5;
  signed-zero numeric equality/representation difference; 2**53+1 vs hex2**53 inequality.
  Invalid late state/false gates/unknown scalar/corrupt files reject, symlink root/parent/member
  and FIFO safe, 4096rows bounded, source unchanged/detached outputs, isolated imports no model.
- [ ] Run unittest discover -p test_scenario_trace_summary.py -v.
  Expected: missing-feature assertion RED, existing fixture setup succeeds.
- [ ] Implement only capture-once aggregate and exact rational numeric comparison, path/runtime guards.
  Focused tests expectedGREEN; all input failures before any returned result, no arithmetic oracle.
- [ ] Run complete component unittest discover -s project -v with private bytecode disabled.
  Expected883+actual new methods PASS. Run new-code Ruff/Ty/Codespell before commit.
  Commit reader/tests, ledger exact BASE/head/results and all Expected checks.

### Task2: JSON/Markdown stdout and guide

**Files:** modify new backend/test; create tools/scenario_trace_summary.py,
docs/RECORDED_TRACE_SUMMARY_R70_KO.md; modify component README.md.
**Interfaces:** consumes Task1 summarize_saved_trace and ReportError;
produces format_saved_trace(Path,output_format='json')->bytes and CLI input/format only.

- [ ] Add failing CLI/format tests before code: JSON counts/gates and deterministic relocation;
  Markdown table counts/first indices; malformed/false-gate records empty stdout/exit2;
  invalid format/abbreviations/policy/output flags rejected before absent input access;
  actual help and no-B isolated CLI preserve source/input/cache boundaries and avoid optional imports.
  Expected missing CLI/format assertions RED, Task1 stillPASS.
- [ ] Implement format function (validates format first, builds own record) and private Markdown,
  CLI cache/error/stdout boundaries. Focused tests expectedGREEN.
- [ ] Add Korean guide/README paragraph distinguishing kind/numeric changes, overlapping
  events, command units, sample index, coherent metadata and all operational prohibitions.
- [ ] Full dev.py verify expected883+actual new methods/234compiles/static/frozen-wheelPASS.
  Commit CLI/docs; postcommit full unittest + source fingerprint checks expectedPASS.
- [ ] Actual R69 saved cases with new CLI twice JSON/Markdown, plus sign/resumed literals,
  input/source hashes unchanged, zero optional model imports and malformed-input rejection.
  Expected identical repeated outputs and exact independently counted events; no new model steps.
- [ ] Final fresh whole-branch reviewer with Review Focus verbatim; root re-grades.
  One TDD fix pass for Critical/Important, defer minors, no re-review. Deterministic evidence,
  separate stdlib custody checks. Keep local branch/worktree; no publication inferred.

Self-review: Task1 produces the exact Path->dict consumed by Task2; formatting
cannot accept caller-forged summary dictionaries. All five focus items have named
real-state tests. Package/source boundaries preserve wheel and existing histories.
