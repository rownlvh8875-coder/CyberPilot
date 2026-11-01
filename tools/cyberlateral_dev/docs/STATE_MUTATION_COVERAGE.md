# R10 — targeted caller-state mutation coverage

Closes the R9 final-review deferred test gap. These two DEV regressions use the
real public API with narrow history fault wrappers, not replacement arithmetic
or assertions about mock call counts.

## Split-only reset

`test_split_only_history_reset_rejected_at_resume_comparison` resets requested,
applied and counter history only on the ramp suffix starting at invocation1.
The invocation index stays valid. All seven full batches and isolated step
chains still match the frozen R8 golden result hashes. The real faulty resumed
commands are [2,2,4] instead of [2,4,6]. Only the resumed-batch comparison must
reject with `SPLIT_RESUME_MISMATCH:ramp:1`.

## Interleaving-only leakage

`test_interleaving_only_history_leak_rejected_at_caller_comparison` shares the
last caller's history only after consecutive index0 callers identify the fixed
round-robin phase. Initial states/indices remain valid, and all seven ordinary
batch/isolated-step golden controls remain exact. The cross-caller comparison
must reject with `INTERLEAVED_CALLER_MISMATCH`, not an earlier domain/step check.
This trigger is intentionally specific to the closed, hash-bound catalog.

## Observed sensitivity proof

Each comparison was temporarily bypassed independently in the DEV harness.
Its new test failed with `HarnessError not raised`. Each comparison was restored
with apply_patch and its test passed. Both mutations were removed before final
verification/commit. No original helper, sealed source or runtime package changed.

Restored harness SHA256:
3dddbfa7e8d3e2911dd8d429f15a1df68426e79f09ac18e1f2b33242f249daec

CI runs both committed fault regressions; source-comparison bypasses are the local
negative-control experiment, not a mode enabled in CI or the installed package.
The full component suite now has156 tests. The one-command verifier and emitted
R9 contract/status remain unchanged: R10 is a test-coverage milestone only.

No claim of exhaustive mutation testing, independent numerical certification,
physical safety or production integration follows. Actual r/T2/vehicle scale stay
null; R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO and all existing
activation prohibitions remain unchanged.
