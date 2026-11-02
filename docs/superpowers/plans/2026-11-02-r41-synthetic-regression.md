# R41 Synthetic Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a fixed interacting-boundary and longer-state synthetic regression pack.

**Architecture:** Reuse the existing JSON parser, pure model, R40 workflow, and
R38/R39 selected-source checker. New artifacts are fixtures, independent selected
expectations, tests, and usage documentation; no production/API changes.

**Tech Stack:** Existing locked CPython3.12.13 DEV environment, unittest and stdlib.

**Spec:** `docs/superpowers/specs/2026-11-02-r41-synthetic-regression-design.md`

## Global Constraints

- Wheel/model/API/CLI/reference source and existing examples unchanged.
- Three valid scenarios: 12 + 128 + 184 = 324 synthetic invocations per workflow.
- Hand-derived expectations before the first execution; no tolerance or auto-update.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale=null; no vehicle activation.
- No F61/r/dt/Controller/Runtime/CAN/real data/candidate evaluation/push/merge/CI.
- Unit/gate synthetic work is additional and must not be labeled zero computation.

## Review Focus

- Repeated cycles must carry applied state rather than restart each cycle.
- A suppressed fault request must not be confused with inactive zero torque.
- Driver clipping/rounding followed by rate clipping must preserve exact types.
- A coherent wrong saved history must not become the independent reference's input state.
- Portable equality must not be overclaimed as private receipt/runtime identity.

### Task 1: Preregister the pack and literal behavioral tests

**Files:** Create `tools/cyberlateral_dev/project/test_boundary_regression_pack.py`,
`tools/cyberlateral_dev/examples/r41/{combined_boundaries,repeated_inactive_crossing,long_fault_cycles}_v1.json`,
`tools/cyberlateral_dev/reference/r41_regression_expected_v1.json`.

**Interfaces:** Consumes unchanged `read_scenario(Path)` and
`evaluate_scenario(ScenarioSpec) -> dict`; produces three valid input files and
hand-derived selected output contracts for Task2.

- [x] Write tests: typed complete selected rows for12/128 cases; whole184 command,
  flag/counter sequences; selected fractional/signed-zero traces; final states.
- [x] Run `python -B -m unittest discover -s project -p test_boundary_regression_pack.py -v`.
  Expected: assertion failures for absent preregistered fixture/expectation artifacts.
- [x] Add exactly the fixed scenarios and independent expected rows/rules from the spec.
- [x] Run the same focused command. Expected: all new unit tests PASS.
- [x] Record focused RED/GREEN and baseline650 evidence; local commit at final delivery.

### Task 2: End-to-end parity, mutation controls and usage

**Files:** Create `tools/cyberlateral_dev/project/test_boundary_regression_workflow.py`,
`tools/cyberlateral_dev/docs/SYNTHETIC_REGRESSION_PACK_R41_KO.md`;
modify `tools/cyberlateral_dev/README.md` to link the pack.

**Interfaces:** Consumes Task1 fixtures/contracts. Reuses
`run_workflow(inputs, output, baseline=None) -> dict`, `check_saved(input, output)`
and existing test-only saved-record render/rehash utilities. No new product interfaces.

- [x] Write workflow tests: two independent workflows and
  one complete baseline workflow, all VERIFIED/exit0/3complete/324model/324reference.
- [x] Assert selected saved rows and VIEW match independent literals, per-case
  reference MATCH/zero differences and fresh-reference helper counts324.
- [x] Assert all nested manifests/closure, 3 root portable records and every batch
  portable byte reproduce across the two independent runs; compare-only model0.
- [x] Inject coherent applied-history and fault-counter errors into separate saved
  copies; expect DIFFERENT and a difference naming the next prepared state.
- [x] Assert original inputs/reference unchanged, closed gates, and no time/r policy.
- [x] Run focused workflow tests. Expected: PASS; negative mutants are detected.
- [x] Document exact commands, counts, expected boundaries, and non-goals; link README.
- [x] Run the complete existing `dev.py verify --output <new-external-path>` gate.
  Expected: all inherited/new tests, Ruff/Ty/Codespell, compile and unchanged wheel PASS.
- [x] Run two explicit R40 workflows in external evidence directories. Check complete
  manifests, canonical portable hashes, and input preservation; record actual counts.
- [ ] Review the complete branch with a fresh reviewer, resolve important findings,
  rerun verification as needed, and commit locally without push/merge/CI.

## Execution notes

Task1's eight-test fixture RED/GREEN preceded Task2 consumer-test writing rather
than both test files preceding the first fixture execution. No new product code
was introduced; real coherent saved-copy mutations prove checker sensitivity.
Final gate:665 tests, Ruff/Ty/Codespell,195 own compiles, unchanged sealed wheel
PASS. Two explicit workflows:324 model/reference steps each;26 portable payloads
repeat exactly. Fresh review:0 Critical/Important,1 nonblocking metadata-only
drift guard deferred in the fixed long-case test helper; no runtime defect found.
