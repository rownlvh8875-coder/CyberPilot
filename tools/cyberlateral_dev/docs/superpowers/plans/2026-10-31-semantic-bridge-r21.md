# R21 Synthetic Semantic Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare unchanged public synthetic input/state dataclasses from declared Float32 readback, with independent oracle parity and no model work.

**Architecture:** Pure typed bridge and independently implemented integer-based
oracle share only data classes. Explicit native mode supplies readback from closed
fixtures using exact installed pycapnp/public-wheel identity and isolated imports.

**Tech Stack:** CPython3.12.13, dataclasses/unittest, struct vs integer-ratio oracle,
unchanged cyberlateral-dev0.3.0 and separate pycapnp2.1.0 environment.

**Spec:** ../../SEMANTIC_BRIDGE_R21.md

## Global Constraints

- Public0.3.0 API/wheel/lock/references/default pure CI unchanged.
- New model/F61/Controller/Runtime/CAN/actual input/r/dt execution=0.
- No R14 fallback, normalization, clipping, rounding, sign changes or state inference.
- Declared bindings do not authenticate bytes/call custody/history.
- Static Gate FAIL, R_BUDGET UNRESOLVED; actual activation/F70UH/F70V/F71 prohibited.
- Existing isolated feature/inline workflow; one fresh final reviewer; [skip ci] commits.

## Review Focus

- Float32 validation must reject binary64-only values without silently rounding.
- Signed zero must survive exact parity, not disappear in numerical equality.
- Oracle must not import/reuse the bridge logic or hide common wrong field mapping.
- Prior state/readback stamps and hashes must not be inferred or mismatched.
- Default R19/R20 and pure CI must not auto-import native or require the new wheel.

### Task 1: Pure bridge and independent oracle

**Files:** Create integration_tools/semantic_types.py, semantic_bridge.py,
semantic_oracle.py and project/test_semantic_bridge.py.
**Interfaces:** ScalarReadback/PreparedSemanticInput and prepare_semantic_input
exactly as spec; oracle_prepare(frame,readback)->(LateralInput,LateralState),
OracleRejection.code; oracle requires structurally valid R20 envelope.

- [x] Write missing-feature RED tests plus literal field/state/limits mapping,
  signed zero/subnormal/native0.3 vs binary64-only0.3, nonfinite/type/domain/dyadic/
  metadata binding rejection, no step/simulate/initial_state calls, oracle parity
  and deliberate swapped mapping detection against literals.
- [x] Implement minimal typed validation/copy bridge and independent ratio oracle.
- [x] Run targeted tests and full dev.py gate, all static/own compile, wheel identity.
- [x] Commit and ledger counts/results with [skip ci].

### Task 2: Closed native producer, reproducibility and publication

**Files:** Create native_qualification/semantic_demo.py and test_semantic_observations.py;
modify owned_demo.py private factory, worker.py/run.py for explicit mode and
public-wheel verification; add project/test_semantic_mode.py, docs/results/README.
**Interfaces:** demonstrate(car)->dict, --semantic-bridge --package-wheel; default
R19/R20 unchanged; installed public package guarded before importing bridge/oracle.

- [ ] Write RED missing-mode/demo/wheel tests and literal eight-case output tests.
- [ ] Implement explicit mutually-exclusive mode and exact public-wheel preflight,
  closed readback producer, exact oracle comparison and fail-closed output.
- [ ] Build/verify/install sealed public wheel + pinned pycapnp into new native env;
  run two workers/output assertions, unchanged R19/R20 SHA controls, full pure gate,
  explicit native Ruff/Ty/Codespell/own compile and fresh source/new-env reproduction.
- [ ] Commit and request one fresh whole-branch review; fix Important/Critical in
  one RED/GREEN pass, ledger all scope rulings/deferred minors.
- [ ] Publish existing feature/Draft only; exact-head pure CI/downloaded manifest,
  original-tree/hash guards, external evidence seal and final scoped handoff.

Self-review: mapping/data-only constructors/native-wheel identity/independent
oracle/precision/signed-zero/no-model boundaries covered. Post-commit publication
and archive receipts live in the external task ledger.
