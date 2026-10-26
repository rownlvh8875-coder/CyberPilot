# Track F7 — Non-binding offline multi-objective evaluator

## Identity and purpose

- Area: Cyber Validation. Implemented diagnostic tool; publication requires review and exact-HEAD CI.
- Repository: https://github.com/rownlvh8875-coder/CyberPilot
- Branch: feature/cyber-autotune. Control-source baseline: `66bb193e13ca9f17beb73badb6f2a94a67faa2da`.
- Scope: read-only analysis of the preserved public synthetic F5 archive under the exact F6 proposal.
- No controller execution, candidate generation, optimization, qualification, ranking or selection.
- Vehicle applicability: none. Mathematical synthetic results do not establish vehicle behavior or safety.

## Original references and identity

- F6 contract: [byte-exact preserved proposal](track-f7-offline-multiobjective-contract.json).
- Contract file SHA256: `8e944560d7fd369b7f345a72ad031c1e090e4d8b4e5bafbf43e4fde61eacb2a9`.
- Proposal receipt: `ed5fe97d2e4a634da12e629a30251db7cf15c13619f1c806fea82fbd69c6b393`.
- F5 archive manifest SHA256: `37bb761c4eb6eeb92bf68db7d34577831b409103c5bc3ee05ceae6bfc58ee681`.
- F6 independent arithmetic sources are identified in the new module docstrings. Adaptation adds checked records and independently derived reset events.
- The original project license is MIT. No external controller or Native algorithm is imported or executed.
- Historical source/receipt identities remain historical. The new evaluator has its own module SHA256 map in every report.
- Existing six submodule pins and all models/Native artifacts are outside this tool's execution path and unchanged.

## Changes and responsibilities

All files are new, outside the Frozen source set:

- `tools/cyberpilot/offline_multiobjective_v1.py`: bounded explicit-file reader, trust-anchor verification, CLI, deterministic report receipt.
- `tools/cyberpilot/offline_multiobjective_gates_v1.py`: private checked Frame records and source-specific arithmetic/state/time/domain checks.
- `tools/cyberpilot/offline_multiobjective_metrics_v1.py`: exact F6 metric slots, numerical summaries and descriptive same-input comparisons.
- `openpilot/tools/cyberpilot_tests/test_offline_multiobjective_v1.py`: self-contained targeted unittest suite, collected by upstream Unit.
- This feature record and the unchanged copied proposal.

No original workflow, test runner, controller, planner, Native kernel, Replay reference, assertion or receipt changes are required.
The two fixed Legacy/V2 test directories are untouched. New tests must not alter their 5,960 current IDs or 5,927 historical IDs.

## Trust boundary and input contract

`Explicit request + SHA256 -> pinned archive/source verification -> private decode -> runtime/arithmetic validation -> frozen Frame tuple -> metrics -> diagnostic JSON`

V1 intentionally supports the known F5 archive adapter. Arbitrary self-signed JSON, copied policy labels, or a caller-provided hash alone do not establish public historical execution.
A different archive/source adapter needs separate versioned review. There is no CLI or environment option to replace the production manifest trust anchor.

The request is JSON with exactly these fields:

- `schema: CYBERPILOT_OFFLINE_EVALUATION_REQUEST_V1`
- `scope: PUBLIC_SYNTHETIC_ONLY`
- `manifest: {path: ABSOLUTE_FILE}`
- `artifacts: [{id: ARCHIVE_RELATIVE_ID, path: ABSOLUTE_FILE}, ...]`
- `source_files: [{id: SOURCE_ID, path: ABSOLUTE_FILE}, ...]`
- `traces: [{result_id, repeat_result_id, case_id, trace_id, repeat_trace_id}, ...]`

Paths are explicit file capabilities, never recursively discovered or executed.
Artifact IDs must match entries in the fixed manifest. Every selected trace requires both original result records and both independently archived repeat files.
Unused or duplicate mappings are rejected. Runtime source IDs are `runtime:` plus the pinned source name; repository source IDs use `original:`.
All required source paths are supplied explicitly. Archived source code is only hashed, never loaded as Python.

The CLI never echoes input paths, raw JSON, exceptions containing private values or full source contents.
There is no controller callback, CAN, Params, network or hardware API in the tool.
Reading an approved artifact is not permission to publish it. No raw trace or generated report is committed.

## Invocation and output

Run from the repository root in the existing supported Python environment:

```bash
python3 -B -m tools.cyberpilot.offline_multiobjective_v1 \
  --request /explicit/isolated/request.json \
  --request-sha256 EXPECTED_REQUEST_SHA256 \
  --output-dir /explicit/isolated/new-output-directory
```

The complete mapping is deliberately explicit; the CLI does not search for local F5/F6 folders.
Request paths are local-only inputs and must not be checked into the public repository.

Output is one `diagnostics.json` in a newly created private directory. Existing output directories are rejected.
Source-tree output is rejected. CLI output under the manifest/input archive tree is rejected.
No input or historical receipt is rewritten. Reports contain hashes and derived diagnostics, not file paths.
The receipt hashes canonical sorted compact JSON excluding its own receipt field.
No timestamps, wall-clock durations or absolute output paths enter the report receipt.

Exit 0 means only `STRUCTURALLY_VALID`; exit 2 means `STRUCTURALLY_BLOCKED`.
Neither result performs performance qualification. Every report contains:

- `PERFORMANCE_NOT_QUALIFIED`
- `THRESHOLD_APPROVAL_REQUIRED`
- `effective=false`
- `selected_candidate=null`, `selected_policy=null`
- D2 `PERFORMANCE_NOT_EVALUATED`, Private E2 `NOT_AUTHORIZED`, HOLDOUT `CLOSED`, vehicle authority `NONE`

## Exact F6 metric semantics

All 28 names, axes, definitions and unavailable threshold states come from the exact copied contract.
The tool returns `METRIC_COMPUTED` or `METRIC_UNAVAILABLE` per slot.
Full frequency response, settling qualification, complete transition coverage, varying-speed/uncertainty coverage,
nonzero initial-state robustness and measurement noise/bias/latency/freshness remain unavailable where the supplied records cannot establish them.
Unavailable is not a silently imputed value or an implementation promise of performance.

Important distinctions:

- Curvature RMSE does not cancel signs. Signed area includes positive, negative, absolute and net area plus cancellation fraction.
- Heading is unwrapped and integrated from the recorded Plant Yaw recurrence, not assumed from curvature at varying speed.
- Normal position is the error projected onto the current reference normal; XY is time-aligned Euclidean distance.
- Closest finite-polyline distance is auxiliary and never substitutes for time-aligned metrics.
- Command variation/derivatives include `u[-1]=0`; reset and transition samples remain included.
- Saturation frames use exact source rails. The occupancy denominator is every retained evaluation frame.
- An episode is a contiguous signed rail run; a change from +1 to -1 starts a new episode. Opposite-rail transitions are reported separately from all-command direction reversals.
- Spectra are full supplied-window, DC-removed, one-sided amplitude/bin power/PSD with Parseval checking; no vehicle stability margin is inferred.
- 10/20/40/80-second prefixes are computed only when actually present.
- Crossing times are descriptive prefix-SSE changes. The F6 nontrivial after-10-second slice and all early crossings are both reported.
- Comparison preserves matched exogenous input, initial state, Native identity and Plant; no arbitrary time shift is allowed.
- Comparison tables contain scalar summaries and matched Horizon prefixes; full spectra/event vectors remain in each trace metric, avoiding duplicated bin-by-bin comparison payloads.
- Descriptive lower/higher numbers and `TRADEOFF_OBSERVED` / `HORIZON_DEPENDENT_TRADEOFF` never select a winner.

## Ten Hard Gates and their limits

The exact HG01..HG10 purposes, source contracts and conditions are copied into each result.
The validator checks pinned sources/receipts, finite non-boolean inputs, exact sequence/time, declared normalized command bounds,
actual mathematical Plant configuration, own-arm feedback/delay/reset and applicable candidate arithmetic.
Reset events are derived from input transitions. The explicit controller-reset case is pinned to sequence800 by the historical producer source. First/explicit resets require the independently source-derived fresh Native state, including pending reason and empty reference/PID history.
A2 static demand exceeding the unchanged development envelope yields `A2_DOMAIN_INSUFFICIENT`, not success.
This static condition is necessary, not sufficient for dynamic or vehicle feasibility.

Recorded Native function profiles and repeat files prove only the scope of the pinned historical evidence.
They are not new Native executions. The evaluator reports `new_controller_executions=0`.
The A3 optional rate contract is not a global downstream vehicle safety rate.
High rail occupancy is observed without an invented acceptance threshold; exceeding the existing normalized bound is a structural error.

Reader limits (64MiB file, 128MiB decoded trace, 1MiB request, 512-entry explicit catalogs, JSON depth64, 20,000 frames) are resource controls, not scientific performance thresholds.
The abs/rel 2e-12 arithmetic comparison is inherited from the F6 Oracle, not a new control acceptance budget.

## Regression risk, tests and actual verification

Risks include malformed/untrusted JSON, bool/nonfinite confusion, forged receipts/reset flags, mismatched source/version,
accidental path disclosure or overwrite, event/frame confusion, improper positional metrics and unsupported qualification claims.

The standalone Unit suite exercises these boundaries, spectra for odd/even lengths, independent metric examples,
same-horizon crossings and a miniature mathematical archive.
Its trust-root substitution is a `unittest.mock.patch` confined to tests; that fixture is not historical Native execution evidence.
The production root rejects the miniature self-attested archive without the test patch.
No local F5/F6 files or silent skips are needed for GitHub Unit tests.

Targeted command:

```bash
python3 -B tools/test_runner.py openpilot/tools/cyberpilot_tests -j 2 -v
```

Local actual-F5 integration reproduces R2 cancellation `0.9995223567492582`, 511 signed rail episodes,
2,862/8,000 rail frames, normal RMS `0.0785161241467245m`, XY RMS `0.18481499134043247m`.
The A0/A3 common entry trace reproduces normal/XY prefix crossings `50.81s / 61.20s`.
These are historical-input recalculations, not new controller/Plant experiments.
Final test counts, source hashes, independent review and exact-HEAD CI evidence belong in the task handoff; prior success is not a new-HEAD result.

| Stage | Method | Status / scope |
|---|---|---|
| Targeted Unit / negative controls | Original runner, standalone new directory | Local checks required before publication; actual final count in handoff |
| F6 numerical comparison | Explicit real F5 archive, repeated fresh processes | Local diagnostic reproduction; no public raw-evidence upload |
| Source / IDs | Frozen231, LFS252, six gitlinks, fixed Legacy/V2 targets | Must remain unchanged |
| Replay / closed loop | No new control behavior | Not run as a new control experiment |
| Exact-HEAD CI | Unit, V2, LegacyV2, Numerical3, Native | Required after feature publication; final conclusions in handoff |
| Vehicle/shadow actuation | None | Not authorized |

## Handoff and rollback

This adds an optional offline reader, not a Runtime integration. Normal operation remains unchanged.
Rollback is a normal revert/removal of the new files after separate authority, preserving all archived results and receipts.
Do not rewrite history or old source identities, disable workflows, change Required Checks, select a candidate or activate Runtime.
Future performance thresholds, additional public robustness inputs, new archive adapters or original controller research each need separate approval.
