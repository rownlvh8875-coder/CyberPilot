# CyberPilot Full CI V2: runtime and public Native fixture repair

## Identity and purpose

Branch feature/cyber-autotune, baseline 5af7b52d9fd16f43e1def6f9b75e9f7913d14f53.
Scope PUBLIC_FULL_CI_RUNTIME_AND_NATIVE_FIXTURE_REPAIR_ONLY. Implements additive CI infrastructure;
no scientific assertions, model, controller, private readers, or empirical results are changed.
The legacy run39322724644 exceeded its original45-minute job cap during regression after setup/build.
It did not complete5927 tests; six required postchecks were automatically skipped.

## Original references

Original tools/test_runner.py owns unittest collection, class/module fixture groups, process-pool batches,
capture and result semantics. The unchanged legacy cyberpilot.yaml is frozen at
30fbd6d6138fd4b44b9371ce0f803ed500bf662d287463d4a28a0585654d28d4 in multiple historical contracts.
V2 is a separate workflow and source-pin amendment; no historical pin is rewritten.
The existing public Native C11 builder and receipt loader remain authoritative, GCC13.3.0,
CPython3.12.13/NumPy2.5.3 qualified Ubuntu24.04/x86_64. Original upstream MIT attribution is retained.

## Changes and expected effect

V2 retains recursive checkout, original LFS fetch/setup, SCons-j2, scoped Ruff, pytest preparation,
all AutoTune/controls tests, attribution95, lateral16, syntax/whitespace, all policy/evidence JSON,
publication before/after and clean-tree checks. Fresh Native artifacts stay in RUNNER_TEMP, are
verified by the existing loader, and are supplied explicitly to all test children through the two
existing receipt environment variables. No .so is committed, uploaded or shared with the gate.

The first candidate uses the unchanged runner-j2-v. Test manifest and verbose result evidence must
prove baseline5927 IDs are retained, every current collected ID ran exactly once and passed,
and zero collection errors/skips/xfailed/xpassed. The one-time ID condition applies to the
complete regression; the original dedicated attribution95 stage remains a separate additional run. No -k or target filtering exists in the wrapper.
A separate always-run gate requires the producing job and every required stage to succeed. It downloads
only the producer's explicit artifact ID from the same run and compares the exact bundle SHA from job
outputs before interpreting it. HEAD, run ID, native receipt/source/ABI/flags, source pins and current
manifest are bound. Missing/partial/timed-out evidence fails. Each job retains45 minutes.

## Regression risk and acceptance

Parallel tests may create additional child processes or share external state. Worker2 does not imply
process2. Original fixture grouping and all assertions remain unchanged. Prefer simple worker2 only
if full stable-source local and clean GitHub evidence show it suffices; otherwise module-atomic
sharding requires explicit disjoint/complete assignment evidence. No speculative shard framework
has been added. The first baseline probe recorded5926 PASS /1ERROR in1116.79 seconds, all5927 IDs once.
The traceback was SOURCE_CHANGED_DURING_COMFORT_MATRIX: development changed the new test file; broad source
binding makes that snapshot unstable, so its results must be retained as a failed/inadmissible probe,
not used to certify parallelism. The controlled full-current-ID run after source freeze passed all5954 IDs with no source change.

## Validation method and actual results

New infrastructure focused tests27 PASS, including exact ID set/duplicates/nonpass/partial logs,
real public Native receipt, wrong receipt hash, native/compiler/authority changes, fixture lifecycle,
artifact ID/SHA preflight, wrong HEAD/run/stage/job and no-follow evidence reads. Source/receipt checks passed:231 frozen pins,252 fresh index pointers,251 original materialized
payloads122,052,386 bytes (the original773,082,315-byte exclusion is unchanged).
Controlled full local regression5954/5954 PASS, each ID once, missing0/duplicate0/skip0/error0; baseline5927 retained. Exact-head Actions remains pending at this prepublication snapshot.
The baseline ID digest is e293db84c944594175ed50bba9d98408692ecd63054e17c96656a2bf004c870b.
Tests and fixture paths are public/synthetic only; private host drives remain hidden in local tests.

Resource observations report CPU vs wall separately and sample the regression child family only.
RSS/virtual sums double-count shared pages and can miss250ms transients; they do not prove complete
job or future private E2 memory/time bounds. Setup/build/postcheck timing comes from actual Actions
step timestamps. The unmodified runner does not expose individual worker exit codes; its main exit
and exact complete per-test records are required. No unsupported worker-exit0 claim is made.

## Handoff

Separate results: LEGACY_FULL_CI, FULL_CI_V2 and all four independent numerical workflows.
Only completed successful V2 jobs plus the coverage gate can establish FULL_CI_V2_COMPLETED_SUCCESS.
V2 does not reinterpret the legacy workflow's historical failure or authorize private E2, model
selection, Native production integration, HOLDOUT, vehicle authority, pooled refit/composition or V5.
All historical research results and selections null remain unchanged. STOP after publication,
actual exact-head Actions observation, two final-byte reviews and clean worktree verification.

## Controlled local full-run evidence

Unmodified runner-j2-v: wall1116.72s, userCPU2001.15s, systemCPU57.48s. Sampled child-family peak RSS1313476KiB and virtual3364616KiB; sampling limitations above apply. Host CPUs12; local timing is not the GitHub VM timing.

Actual5954 sorted-ID digest 2885fda977a795a36b64fe713f859d1c0b2bf4bccd652057ef1946872aa8cd47. Manifest receipt 8be0af7af4b1278e8629781ee781ed22414d90f83d8f7947bb4ad7c6beebb1e2; complete result receipt 66e1fab4ba6125b72570dd2d5b090e4d17fafaecd011323ffbb338111e3a54ff. The local run used baseline HEAD plus the exact reviewed additive source-lock bytes, and identical scientific source fingerprints before/after; it is precommit tree verification, not a claimed final GitHub HEAD run.

Longest reported test: openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v3_execution.TestV3CompleteRuns.test_32_jobs_two_independent_runs_and_trapped_resume (75.38s). Original runner does not expose fixture-inclusive per-module wall or individual worker exits; those values are not inferred. SCons-j2, attribution95, lateral16, focused27 and compileall were actually rerun successfully in this increment. Original Python/Native/scientific source hashes remain unchanged.

The failed initial development probe remains in results as5926 PASS/1ERROR with source mutation; it is not reused as a passing regression. No matrix shards are introduced unless actual GitHub worker2 evidence proves insufficient. Final GitHub run IDs/results are reported in the immutable final handoff to avoid a commit/run hash cycle.
