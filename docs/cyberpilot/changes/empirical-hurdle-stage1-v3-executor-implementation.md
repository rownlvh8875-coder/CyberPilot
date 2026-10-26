# V3 executor implementation and validation

V3의 규칙은 이미 정해져 있다. 이번 단계에서는 실제 주행데이터를 돌리지 않고,
다음 실행에서 그 규칙을 정확히 적용할 실행기를 만들었다. V3는 V1 모델을 그대로
사용하면서 TRAIN에서 V1이 잡았던 MOVE TP 이상을 유지하는 threshold만 허용한다.
실제 V3 성능은 아직 측정하지 않았다.

## Identity and purpose

Cyber Validation; synthetic implementation verification. Branch `feature/cyber-autotune`,
baseline `c7514cbea0f87a21acae15593e63c4af70f59dee`. Existing V3 design,
fitting and execution contracts are the specification. No new research choice,
private source access, model fit, HOLDOUT or vehicle authority is authorized.

## Original references

CyberPilot repository, same branch and baseline; existing repository license.
Reuse `empirical_hurdle_v2_threshold.py` numerical primitives, V1 Hurdle
math/data/gates, V2 read-only lineage/storage helpers, and all 21 frozen V3
contracts. No upstream integration or dependency/submodule change.
Caller path: explicit sealed authorization → metadata preflight → immutable
model/source loading → TRAIN replay/decision finalization → DEV/rollout → frozen
gate/selection → compact store. This increment exercises synthetic inputs only.

## Implementation plan

Goal: implement the frozen executor with no actual private experiment.
Architecture: additive modules; preserve all historical code and public evidence.
Tech stack: Python 3.12.13, NumPy 2.5.3, existing deterministic storage helpers.

- [x] Task 1: `empirical_hurdle_v3_threshold.sweep(probability, branch_delta,
  current, target, *, reference_tp, role, observer=None)`. Reuse V2 sum/order
  statistics and canonical metrics; add TP count/floor only. RED/GREEN tests
  compare every threshold and selected result with the exhaustive V3 oracle,
  test exact boundaries and zero-reference V2 parity in the internal numeric core.
- [x] Task 2: `empirical_hurdle_v3_io.preflight(...)` consumes an externally
  supplied authorization and trusted receipt SHA. Verify public pins, HEAD,
  seal, explicit roots, D volume, overlap, capacity, runtime, source metadata,
  models/anchors/reference before numeric access. Add strict source/storage
  adapters and no-refit firewall. RED/GREEN authorization and storage tests.
- [x] Task 3: `empirical_hurdle_v3_execution.run(...)`, `execute_job(...)`,
  `resume(...)`, `repeatability(...)`; TRAIN finalization precedes DEV loading.
  Reuse existing prediction, rollout, 32-clause gate and selection semantics.
  Add report-only comparison and allowlisted aggregate publication modules.
  RED/GREEN synthetic private-shaped runs, leakage, repeatability and resume traps.
- [x] Task 4: independent numeric and authority reviews; fix important findings
  with reproducing tests. Run focused/combined/full regression, replay, build,
  Ruff, syntax, JSON, publication and whitespace checks. Publish 13 additive
  implementation evidence artifacts, commit/push and verify exact-HEAD CI.

Review focus: binary64 reduction boundaries; missing/forged authorization before
source reads; partial threshold writes and early DEV access; job/reference row
reordering; forged/incomplete saved output during resume. Each is tested at the
owning boundary. Native inline implementation; two separate independent reviews.
The existing prepared feature checkout is reused to honor the requested branch
and D-storage constraint. No new worktree or storage migration is created.

## Changes and expected effect

New threshold, authorization/I/O, orchestration and publication modules plus
synthetic tests. Scaffold remains unchanged as the small-fixture oracle.
One new feasibility clause: TP >= frozen V1 TRAIN reference. All model,
normalizer, feature, candidate, fold, metric, projection, gate and selection
semantics remain frozen. No fallback or tunable constant is introduced.

## Regression risk and acceptance

Baseline: full 4,680; replay 16; prior focused 53; combined empirical 1,821.
Acceptance is exact synthetic parity, enforced authorization before numeric
opens, unchanged historical files, no source fitting, byte-exact repeatability,
verify-only resume, and all requested checks. Actual improvement is unknown.
Rollback is removal of the additive implementation; historical policies remain
authoritative. D-only results; no private result migration or source scan.

## Validation method and actual results

Startup: fetch, local/origin equality, clean tree, baseline ancestor and
exact-HEAD CI run 38428358912 SUCCESS verified. New focused executor tests:
51 PASS, 81 subtests PASS. All V3 focused regression: 104 PASS.
Full AutoTune+controls: 4,731 PASS. Combined empirical: 1,872 PASS.
Lateral replay: 16 PASS. Ruff, compileall, JSON, publication/privacy/authority,
diff check and SCons: PASS. The initial SCons invocation lacked activated venv
PATH; activation fixed it without source changes. Two independent reviews and
all finding regressions completed. Exact-HEAD GitHub CI is checked after push and reported in the final handoff.
Replay/simulation here are synthetic offline checks. Shadow, HOLDOUT, actual
V3 private performance and vehicle execution remain NOT_RUN / NOT_AUTHORIZED.

## Handoff

Target: READY_FOR_SEPARATE_RETROSPECTIVE_EXECUTION_AUTHORIZATION.
Future actual execution requires a separately supplied sealed authorization
binding current HEAD, code, policies, all roots/models/anchors, runtime and D
capacity. HOLDOUT CLOSED, opening/discovery 0; vehicle authority NONE.

## Numerical implementation

The bounded sweep imports V2 OrderedSum, OrderStatistics, candidate construction,
canonical one-threshold calculation and objective ordering. Original-row binary64
pairwise reduction and exact linear percentile interpolation are retained.
Only a Python-int TP counter and the frozen TP feasibility clause are added.
The synthetic exhaustive scaffold remains unchanged. Zero-reference V2 parity
is tested only through the internal numeric core; the authorized API always
enforces the positive reference and `20 * reference_tp > positive_count` guard.

Every synthetic threshold matches the exhaustive oracle, including reduction
boundaries, ties, adjacent binary64 probabilities, signed zero, half-even
projection, TP equality/one-below, rare/isolated/burst MOVE, score ordering and
calibration shifts. The real-sized deterministic synthetic benchmark used
200,003 rows and 200,004 thresholds: 2.611 seconds, 83,504 KiB maximum process
RSS. These are observations, not new performance gates or private-data results.
Allocation instrumentation rejects multidimensional sweep allocations.
Storage of rollout paths is O(anchors × horizon), as required by evidence,
and is separate from the O(N+T) threshold engine.

## Authorization, causality and immutable reuse

There is no grant-minting command or private path default. Future `run` requires
an external sealed authorization and separately trusted receipt SHA, explicit
source/causal/derived/output roots, and a replica name. Public contracts and HEAD
are checked before the authorization document. Root identity, D backing,
non-overlap, mount topology, capacity and exact environment precede source
metadata admission. All 32 model/normalizer/anchor/reference identities are
admitted before numeric payload access. Wrong or missing authority fails closed.

The supported path topology is WSL root plus the explicit D mount; additional
ancestor mounts are rejected to prevent hidden source-descendant bind aliases.
The API registry prevents forged unregistered permits. It is a process/API
boundary, not a sandbox against arbitrary Python code with module-global access.

Stage1 replays the unchanged V1 model; saved TRAIN probabilities, if present,
must match byte-for-byte. Stage2 predicts every TRAIN anchor, including STATIC,
using the immutable MOVE-only normalizer. No fit or normalizer recomputation is
called. TRAIN finalization is persisted before DEV loading. Its complete schema,
finite private threshold and byte hash, job/anchor/model/reference bindings,
selected TP and receipt identity are checked before DEV or historical numeric
threshold comparison. The selector API cannot accept DEV or HOLDOUT inputs.

DEV and all four rollout horizons reuse V1 helpers and exact anchors. Recursive
inference receives only initial steering history and logged exogenous inputs;
future truth is used for scoring. A failed performance clause does not stop
remaining metrics. The unchanged 32-clause gate and both-fold selection rule
remain authoritative. V1/V2/V3 comparisons are report-only.

## Storage, repeatability and resume

Only V3-specific TRAIN gates/projected ticks, DEV predictions/errors and rollout
projected/gate paths/end errors are persisted. V1 model/truth/HOLD_LAST/exogenous
payloads remain references. Arrays are C-order NPY, deterministic gzip level 1,
mtime zero and empty filename, with compressed, decoded and content hashes.
Signed16 persistence follows range checks. Capacity reserves both complete runs,
atomic-member peak and metadata/safety budgets; payload omission is forbidden.

Writes are exclusive, receipt/job/run manifest-last; files and newly created
ancestor directory entries are fsynced. Two independent synthetic 32-job runs
produce byte-identical evidence. Resume checks trusted manifest/authorization/
output identity before reading members, then verifies only saved V3 bytes with
all source loaders and computation paths trapped. Source references are inert.
Cleanup eligibility checks durable exact-equality evidence, safe D scratch and
non-overlap; this increment implements no deletion and performs none.

## Independent reviews and fixes

Review A independently checked numerical parity, p95, bounded memory, reference
identity, no fallback and no refit; no important numerical finding remained.
Review B reproduced and prompted fixes for direct-reader early DEV access,
incomplete threshold markers, resume trust ordering, new-directory durability,
unchecked public count fields and descendant bind-mount aliases. Each fix has a
synthetic reproducing regression; no actual private source was opened.
Publication projects aggregate fields and rejects private values, raw numerical
sequences, unknown metric fields and non-count validation metadata.

## Actual execution and next step

Actual private source access and discovery: 0. Actual V3 TRAIN parameter choice,
DEV, rollout and model selection: NOT_RUN; actual threshold NOT_COMPUTED.
Historical S2-RI/V1/V2 failures and all frozen V3 public contracts are unchanged.
No pooled refit, source migration, HOLDOUT discovery/opening or vehicle authority.

Next: request separate retrospective execution authorization binding the final
HEAD and executor source hashes, exact successful V1/derived identities and D
roots, all 32 model/normalizer/anchor receipts, exact runtime/BLAS, deterministic
storage schema and measured free-space preflight. Implementation readiness
does not establish V3 performance or candidate admission.

Final authority follow-ups also pin the exact precheck order (D proof before
non-overlap), verify decoded kernel mount source is the Windows D drive with
matching device identity, and map compressed-model/source-feature integrity
errors to V3 machine statuses. Missing metadata fails source-unresolved.
The final full suite is rerun after these changes. No numerical algorithm,
policy reference, gate or selection semantics changed.
