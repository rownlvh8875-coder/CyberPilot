# CORE64 Recording Input Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save one explicitly executed SHA-pinned synthetic diagnostic without overwriting existing data.

**Architecture:** A new workflow reuses unchanged CORE61 once and CORE16 exclusive
publication; a separate strict CLI keeps the old stdout command unchanged.

**Tech Stack:** Existing Python3.12/stdlib/unittest/Ruff/Ty/Codespell, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-recording-input-save-design.md`

## Global Constraints

- API publish_recording_input(Path,str,Path)->dict in integration_tools/recording_input_workflow.py.
- New tools/recording_input_workflow.py requires --run/--input-file/--expected-sha256/--output-root exactly once.
- Exact64lowercase SHA first; existing CORE16 output preflight before unchanged CORE61 once.
- DIAGNOSTICS.json canonical 1..1048576bytes and SHA256SUMS.txt only; all serialization before mkdir.
- CORE64_RECORDING_INPUT_WORKFLOW_V1 receipt and CLI fixed codes exactly as spec.
- MATCH0/DIFFERENT1/failure2; no overwrite, cleanup, retry, input copy or implied atomic/durable transaction.
- Existing source/model/API/codec/math/wheel and actual-use gates unchanged.
- Preserve linked checkout/primary/config/history/evidence; main integration first, then new feature.

## Review Focus

- Bad output must fail before synthetic work; exercise existing dir/symlink/missing parent/checkout destination.
- Different is saved, not repaired or truncated; test literal late rows and actual public step counts.
- Late serialization/publication failure may leave work/partial files; inject serializer/write/readback failures and retain output.
- CLI stdout failure after publication must report failure without recompute/deletion; test short and broken streams.
- Saved bytes must match returned checksum and all false authority flags; verify complete two-file layout and independent canonical literals.

### Task 1: explicit complete-input diagnostic save API and CLI

**Files:** Create integration_tools/recording_input_workflow.py,
tools/recording_input_workflow.py,project/test_recording_input_workflow.py,
docs/RECORDING_INPUT_WORKFLOW_CORE64_KO.md,this spec/plan. Modify README.md and
docs/CORE_DEVELOPMENT_BACKLOG_KO.md only.

**Interfaces:** Consume run_recording_input(Path,str)->dict, CORE16 _output(Path)
and _publish(Path,dict[str,bytes]), scenario_output.canonical/GATES. Produce the
API and CLI main(argv=None)->int specified above. No existing producer edits.

- [ ] Write tests first: real literal MATCH rows (6,8,2,5)/(7,-8,-2,6)/(8,4,2,7),
  DIFFERENT first row saved10/computed2 and all3rows retained, model3/simulate0;
  exact2files/fullchecksum/receipt/gates/modes/input custody/single capture;
  SHA-before-path, mismatch/malformed/late semantic0 and no output; existing,
  symlink/missing-parent/checkout/bad path0; size/serialization before mkdir;
  short/nonpositive/write/readback errors preserve partial files and work;
  strict/help/cold CLI, canonical exits0/1/2, no temp/forbidden imports,
  short/broken stdout/globals restoration, independent process determinism.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_input_workflow.py -v`.
  Expected missing-feature assertion failures,zero errors. Commit design/plan/tests.
- [ ] Implement only two new modules with unchanged producers; rerun focused
  command. Expected all new tests PASS, no warning. Document and actually execute
  MATCH/DIFFERENT/rejection guide examples in new external folders.
- [ ] Run configured statics and `.venv/bin/python -B dev.py verify --output /absolute/NEW`.
  Expected2166tests (2133+33new),352 own compiles,98Manifest and unchanged pins.
  Freeze eight scoped paths; focused tests PASS again; commit implementation.
- [ ] One fresh whole-branch review; author-grade findings and declined scopes.
  One Critical/Important fix pass RED→GREEN+full suite if required; ledger minors.
  Preserve all737 baseline sources outside8scope, all prior refs except new branch,
  main7fe/config/primary. Two deterministic evidence ZIP builds and independent
  CRC/fullManifest/source/rebuild verification. No actual input/vehicle use.
