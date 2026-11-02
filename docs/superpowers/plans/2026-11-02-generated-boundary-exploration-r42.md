# R42 Generated Boundary Exploration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministic bounded synthetic input generation, existing independent checks and complete failing-case reproductions.

**Architecture:** Pure generator feeds the existing R40 workflow unchanged. A DEV wrapper preserves all verdicts/counts, snapshots source/input identities and publishes final JSON last; CLI is a separate opt-in tool outside the public wheel.

**Tech Stack:** CPython3.12.13, existing stdlib/SHA256/canonical R31 JSON, pinned DEV dependencies and NumPy2.5.3 reference worker.

**Spec:** `docs/superpowers/specs/2026-11-02-generated-boundary-exploration-r42-design.md`

## Global Constraints

No public0.3.0 model/API/wheel/lock changes or new dependencies. Seed builtin int0..2**32-1; cases1..16; steps16..256; full generated JSON goes through existing R31 parser. No actual vehicle/log/native/F61/r/dt/Controller/Runtime/CAN/candidate work. All existing closed gates unchanged. New output only, no overwrites, no automatically shared personal receipts, exact comparisons/no tolerance.

## Review Focus

- Bool/subclass/oversize parameters and unsafe output paths must reject before model work or output creation.
- All advertised generated boundary features must exist in actual input values, without claiming exhaustive branch coverage.
- Coherent wrong stored numerical fields must become DIFFERENT with whole original sequence preserved, not metadata-only success.
- Reference errors, zero completed cases and contradictory counts must never be promoted to MATCH; preserve failed-work uncertainty.
- Mid-run source/input changes and partial worker/IO failures must prevent root completion; repeated output may differ only in private receipts.

## Task1: Pure deterministic generator

**Files:** Create `tools/cyberlateral_dev/integration_tools/scenario_explore_generate.py` and `tools/cyberlateral_dev/project/test_scenario_explore_generate.py`.

**Interfaces:** Produces `generate_cases(seed,cases,steps)->dict[str,bytes]` and `generation_record(seed,cases,steps,payloads)->dict`; consumes existing `parse_scenario` and `canonical`.

- [ ] Write tests before code: generation file exists; same parameters preserve exact bytes and distinct seeds change samples; strict type/range rejection; all16*256 upper-bound inputs parse; canonical JSON preserves float signed zero and distinct prior requested/applied; fixed boundary prefix/observed feature counts validated with independently derived values.
- [ ] Run `python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_scenario_explore_generate.py -v`. Expected: RED missing generator assertion.
- [ ] Implement pure SHA256-indexed generation and metadata as specified. No model/reference import or external files.
- [ ] Repeat test command. Expected: GREEN; barrier subprocess confirms generator cannot load model/NumPy/native.
- [ ] Commit task1 after fresh targeted tests and Ruff.

## Task2: Existing workflow integration, failure preservation and CLI

**Files:** Create `integration_tools/scenario_explore_run.py`, `tools/scenario_explore.py`, `project/test_scenario_explore.py` under `tools/cyberlateral_dev`.

**Interfaces:** Consumes Task1 payloads and unchanged `run_workflow`; produces `run_exploration(seed,cases,steps,output)->dict`, `.code` rejection API and `exit_code(record)->int`. CLI requires all four explicit flags.

- [ ] Write tests before implementation for real16-step MATCH/JSON/reports, repeat equality, real coherent wrong float32 saved field yielding DIFFERENT with identical full JSON reproducer, worker ERROR yielding exit2, all output guards, bad parameters, source/input mutation, partial failure without completion, complete Manifest closure and forbidden frontend imports.
- [ ] Run `python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_scenario_explore.py -v`. Expected: RED missing runner/CLI assertions.
- [ ] Implement preflight, source snapshot, exclusive generation, real R40 composition, case findings/reproducer copies, Korean links/Manifest/final record; no arithmetic reimplementation or new oracle.
- [ ] Repeat tests. Expected: GREEN, actual negative controls detect one or more numerical fields and preserve ERROR uncertainty; CLI rejects unsupported r/dt/input flags without traceback/output.
- [ ] Commit task2 after targeted regression tests and Ruff/Ty.

## Task3: User documentation, full verification and delivery

**Files:** Add `tools/cyberlateral_dev/docs/SCENARIO_EXPLORATION_R42_KO.md`; update component README only to link the opt-in feature. External evidence and execution ledger stay outside repository.

- [ ] Document exact required command, seed/caps/catalog semantics, independent-source limits, unchanged model/vehicle gates, reproducer re-run via existing R40, full vs portable Manifest/private boundary, expected exits and failure handling. No physical safety or elapsed-time claims.
- [ ] Fresh full `dev.py verify` must PASS all component tests/static checks/own compilation and exact existing wheel. Run existing cloud-tool tests separately and record actual counts.
- [ ] Run explicit seed42/cases4/steps128 twice; expected512 model/512 reference each, total1024/1024, same portable bytes; R34 compare complete newly generated batches must MATCH512/diff0/new models0. Inspect generation feature counts and4 profiles/boundaries as applicable without inventing universal coverage.
- [ ] Independent whole-branch review per requesting-code-review skill; fix Important/Critical once with RED→GREEN regression and green suite; ledger any deferred minors.
- [ ] Preserve source identities; seal allowlisted evidence; verify private HF content-addressed upload by exact re-download. Commit feature/docs, push feature branch and open/attach PR after verification; do not force/admin merge or change existing protected branches. Report main remains unchanged until normal review/merge stage.
