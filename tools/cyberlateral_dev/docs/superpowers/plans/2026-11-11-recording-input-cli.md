# CORE61 Recording Input Diagnostic CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly diagnose a SHA-pinned saved complete synthetic input without a hand-written caller.

**Architecture:** A bounded single-capture reader calls unchanged CORE58 once and
projects its actual diagnostic. One strict --run CLI emits canonical stdout; no
new math, model/API schema changes, persistence or implicit codec execution.

**Tech Stack:** Existing Python3.12/stdlib/unittest/Ruff/Ty/Codespell; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-recording-input-cli-design.md`

## Global Constraints

- run_recording_input(input_file:Path,expected_sha256:str)->dict in integration_tools/recording_input_run.py.
- CLI tools/recording_input_diagnostics.py: exactly one --run/--input-file/--expected-sha256.
- Exact64lowercase hex before path; regular nonsymlink file, no symlink ancestors,1..1048576bytes.
- Single O_RDONLY/O_NOFOLLOW/O_NONBLOCK/O_CLOEXEC capture,cap+1 actual-read guard,close/hash before unchanged CORE58 once.
- CORE61_COUNTERFACTUAL_RECORDING_DIAGNOSTICS_V1 projection exactly as spec; canonical stdout cap1048576.
- MATCH0/DIFFERENT1/failure2; no raw data in errors; no result on pre-output failure; partial stdout cannot retract.
- Fixed pre-execution codes; other failure RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO; no retry.
- Cold bytecode suppression and process-global restoration; no temp/env/cache-prefix changes.
- N-1 real synthetic steps, full preflight0, declared feed and all differences preserved; no input/policy inference.
- All actual-use gates remain blocked; local feature only, preserve main/config/primary/evidence.

## Review Focus

- A replaced path after capture must not change decoded bytes or induce reopen; test_single_capture and replacement test.
- A misleading fstat size or short reads must not bypass actual cap or truncate silently; bounded growth/short-read tests.
- Late errors must not claim zero work or leak source values; late model/serialization/stream failure tests.
- Invalid flags/help must not import project or access files, and must restore globals; strict parser/cold tests.
- Canonical output is a bounded projection, not input roundtrip/origin/vehicle authority; literal rows, all false gates and max127 test.

### Task 1: explicit bounded saved-input diagnostic and CLI

**Files:** Create `integration_tools/recording_input_run.py`,
`tools/recording_input_diagnostics.py`,`project/test_recording_input_cli.py`,
`docs/RECORDING_INPUT_CLI_CORE61_KO.md`,this spec/plan.
Modify `README.md`,`docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.

**Interfaces:** Consume check_serialized_recording_input(raw:object)->SyntheticSequenceCheckV1
and scenario_output.canonical(value)->bytes/GATES. Produce run_recording_input(Path,str)->dict
and CLI main(argv=None)->int; public diagnostic/codec/model bodies unchanged.

- [ ] Write20 reader/projection tests and24CLI tests: literal3-row MATCH,
  early DIFFERENT complete declared feed, strict digest-before-path, mismatch0,
  single capture and path replacement,empty/oversize/special/symlink inputs,
  readonly/relative paths, malformed/late semantic/wrong format0, false authority,
  max127, exact bytes, late execution failures, read failure/short reads/misreported
  size; strict/help/cold parser, exact JSON/exits, unknown output, output bounds,
  short/nonpositive/partial/broken streams, global restoration, no temp/forbidden
  imports, independent subprocess determinism. Assert literal states above,
  model3/simulate0; no expected output derived from the new producer.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_input_cli.py -v`.
  Expected44 missing-feature assertion failures,zero errors. Commit spec/plan/tests first.
- [ ] Implement the two named modules only; rerun same command. Expected44PASS.
  API file error codes RECORDING_DIAGNOSTICS_INPUT_SHA256/INPUT_FILE/INPUT_SIZE/INPUT_CHECKSUM;
  CLI usage RECORDING_DIAGNOSTICS_USAGE_NO_MODEL_EXECUTION; codec/preflight codes unchanged.
- [ ] Document full synthetic input generation and --run example; execute literal
  example twice in separate processes, byte-identical stdout. Run independent
  controlled changed-input/digest rejection; preserve output and nonzero work scope.
- [ ] Run configured static checks and `.venv/bin/python -B dev.py verify --output /absolute/NEW-output`.
  Expected2133tests/349compiles/98Manifest,unchanged wheel/CORE32 pins. Freeze8paths;
  final focused44PASS; commit implementation on the existing isolated feature.
- [ ] One fresh whole-branch review; author-grade all findings and exclusions.
  One Critical/Important fix pass via RED→GREEN+whole suite if needed; ledger minors.
  Preserve731baseline files outside8scope,main/config/primary and refs except newfeature.
  Seal two identical evidence ZIPs and separately verify CRC/Manifest/source/rebuild.
  Do not push/PR/merge/dispatch/enable actual use in this local implementation task.
