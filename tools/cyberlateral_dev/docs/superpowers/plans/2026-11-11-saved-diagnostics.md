# CORE66 Saved Diagnostic Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect a SHA-pinned saved CORE64 diagnostic without model replay or writes.

**Architecture:** Reuse CORE18 bounded directory/file capture and CORE9 canonical
JSON parsing. Validate only CORE61 stored relations; a separate strict CLI emits
the inspection receipt while preserving the original stored diagnostic.

**Tech Stack:** Existing Python3.12/stdlib/unittest/Ruff/Ty/Codespell, no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-11-saved-diagnostics-design.md`

## Global Constraints

- inspect_recording_diagnostics(Path,str)->dict in integration_tools/recording_diagnostics_saved.py.
- CLI tools/recording_diagnostics_inspect.py: --input-root/--expected-sha256 exactly once, no --run.
- External DIAGNOSTICS SHA exact64lowercase first; exact2regularfiles, no symlinks; caps1048576/512.
- Reuse _directory/_read_file and _parse unchanged, root identity check and close-before-parse.
- Exact schema/typed domains/declared state links/difference order/summary as spec, no arithmetic replay.
- Receipt exactly as spec; stored history and top-level0steps distinct; stdout cap2097152.
- Valid MATCH/DIFFERENT both inspect exit0; errors2 with fixed codes, no writes/retry/cache/temp.
- Existing producers/model/codec/API/wheel and actual-use gates unchanged; preserve main/config/primary/evidence.

## Review Focus

- A captured file replaced after capture must not be reopened; test replacement and descriptor closure before parse.
- Recomputed manifest alone cannot repair wrong stored row roles/types; test deliberate rehashed schema/state/summary faults.
- Stored DIFFERENT must preserve declared next-entry state rather than computed rollout; test literal nonmatching first row followed by later rows.
- A self-consistent forged calculation can pass; test acceptance with explicit false arithmetic/origin/input verification flags.
- Inspection success differs from saved diagnostic success; test saved DIFFERENT CLI exit0 with saved_diagnostic_exit_code1 and zero new work.

### Task 1: saved-only inspection API, CLI and guide

**Files:** Create integration_tools/recording_diagnostics_saved.py,
tools/recording_diagnostics_inspect.py,project/test_recording_diagnostics_saved.py,
docs/RECORDING_DIAGNOSTICS_INSPECT_CORE66_KO.md,this spec/plan. Modify README.md
and docs/CORE_DEVELOPMENT_BACKLOG_KO.md only (8paths).

**Interfaces:** Consume unchanged CORE18 _directory(Path,dict[str,bool]) and
_read_file(int,str,int)->bytes; CORE9 _parse(bytes)->object; scenario_output
canonical/GATES. Produce inspect_recording_diagnostics(Path,str)->dict and CLI
main(argv=None)->int; no existing helper/producer edits.

- [ ] Write focused tests first: literal3row MATCH, early DIFFERENT with declared
  feed, real producer compatibility, hash-before-path/manifest/schema/domains,
  single bounded readonly captures/closure/root identity/path replacement,
  max127rows, rehashed faults/consistent forgery, strict/help/cold CLI, exit0/2,
  complete/partial/broken streams, globals restoration, deterministic subprocesses
  blocking producers/model/reference/F61/actual modules. Compare literal states
  (6,8,2,5)/(7,-8,-2,6)/(8,4,2,7), new model/reference0 for inspection.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_diagnostics_saved.py -v`.
  Expected every registered new method fails missing-feature assertions,zero errors.
  Record actual count,then commit spec/plan/tests as preregistration.
- [ ] Implement the2new modules; run same focused command. Expected all PASS.
  Parser/schema errors map to fixed codes; API never imports or invokes producers.
- [ ] Document saved MATCH/DIFFERENT/corrupt checks and run those real CLI examples
  in independent processes. Verify input bytes/modes unchanged and no new model work.
- [ ] Run configured static checks and `.venv/bin/python -B dev.py verify --output /absolute/NEW`.
  Expected2166+registered_new_methods,355compile,98Manifest and unchanged pins.
  Freeze8paths,finalfocusedPASS,commitimplementation,task-donefocusedPASS.
- [ ] One fresh whole-branch review,author-grade every finding/exclusion; one
  Critical/Important TDDfixpass+fullsuite if needed. Preserve all743baseline bytes
  outside8scope/config/primary/refs exceptnewfeature. Two deterministic ZIPs and
  independentCRC/Manifest/source/rebuild. Then follow standing authorized normal
  feature backup/main FF/automatic CI sequence with protection/concurrency gates;
  do not treat local closure as remote CI success or permit actual input/vehicle use.
