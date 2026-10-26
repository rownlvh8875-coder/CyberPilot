# S2-RI reconstruction test runner compatibility

## Identity and purpose

Test-only correction following commit 4ca083f343b8e14ca460026b74e63d8adf86a43a.
The frozen reconstruction executor, contracts, public evidence and private
stores remain unchanged.

## Original references

CI run 38241161117 completed its build and 4,154 existing tests, but failed to
collect the new reconstruction test module because pytest is not installed in
the supported CI environment. The repository uses the standard-library
unittest loader through tools/test_runner.py.

The previous local focused checks used an installed optional pytest package,
which concealed this collection dependency. The old local full-run receipt
(4,160 tests) and failed CI outcome remain point-in-time evidence.

## Changes and expected effect

Remove the test module's pytest dependency. Local fixed case metadata registers
all 64 cases as unittest methods. Assertions, parameter values and numerical
fixtures are preserved. Optional pytest invocation sees the same 64 methods
without collecting unbound parameterized functions twice. No dependency is
added and no test is skipped.

The standard runner previously discovered six new class methods locally;
it now discovers all 64 cases. Expected combined AutoTune/controls collection
therefore increases from 4,160 to 4,218.

## Regression risk and acceptance

Risks are lost parameter cases, closure capture errors and weakened exception
assertions. Verify 64 cases with pytest explicitly unavailable, through the
repository runner, and through optional pytest. Require fresh full regression
and exact-HEAD CI success. The correction does not change replay semantics,
so the two completed numerical replays are not recomputed or invalidated.

## Validation method and actual results

- Reproduced the CI collection error with pytest blocked from imports.
- Standard unittest, pytest unavailable: 64 PASS.
- Repository test runner: 64 PASS.
- Optional pytest: 64 PASS, no duplicate collection.
- Ruff: PASS.
- Full AutoTune/controls regression is rerun for this correction; its final
  result and remaining checks are recorded on the published commit's CI.
- Independent review checks discovery, parameter capture and assertion parity.

## Handoff

Reconstruction input readiness and the identical private run manifest remain
unchanged:
5452d24a4d72ee8680d3b98048c1095113ab934e9bf132f2b91740a0d3baa178.

No new model fit, normalizer fit, candidate selection, raw/qlog/HOLDOUT opening,
failure attribution or Hurdle evaluation is performed. NO_ADMISSIBLE and all
existing authority limits remain unchanged. Vehicle application is unauthorized.
