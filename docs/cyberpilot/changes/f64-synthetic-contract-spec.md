# F-64 Synthetic Source / integer time / metric contract

## Authority and scope
User authorizes this isolated implementation, two local commits, procedural holdout and local checks. No Controller import/initialization/call, actual RLOG analysis, old6000 requalification, candidate, runtime or vehicle IO. Original feature worktree and F60..F63 seals remain untouched. New branch: feature/f64-synthetic-contract-oracle, base588d6b21c21089065a7d9165d6e7a438e8aa6297.

This document and artifacts/f64/preregistered_contract.json are normative ONLY for new F64 public synthetic waveform observations. No old schema is relabeled. Definitions with pre/post trajectory ambiguity are excluded, not silently chosen. Numeric command-shaped fixtures are inert observations, never actuator/controller output.

## Source and time
The machine contract enumerates exact fields/dtypes/shapes/units/ranges/error codes. Canonical JSON is sorted ASCII UTF-8, compact separators, single LF, no floats, no duplicate keys or unknown keys. Raw order is preserved; timestamp sorting is forbidden. Value is numerator/positive denominator, exactly in [-1,1], inherited synthetic normalized domain. Count1..8000 inherits F10's descriptive horizon, not a vehicle limit.
Canonical timestamp and interval are nonnegative signed int64 ns (strictly positive intervals). Existing F10 time_ns and F60 TIME_NS provide the ns convention. Maximum interval10000000ns is the existing nominal10ms; F64 explicitly allows shorter intervals without claiming hardware timing. Starts are preserved, not normalized. Valid irregular input alternates half/full nominal periods. No old F61 float time mutation.
Only exact integer external ns/us/ms/s inputs convert; multipliers are explicit. Reject floats including integral float/NaN/Inf, negatives, overflow and nondivisible inverse conversion; no rounding. Duplicate, reversal, excessive gap are distinct fixed errors. int64 arithmetic is checked using Python integers before narrowing.

## Metrics and independent implementation
Selected metrics are adjacent N-1 rate RMS (encoded by exact rational mean-square radicand), absolute rate p95/p99 linear quantiles, max absolute rate/delta, counts/support/duration. Units are normalized_command/s, squared units, and ns. Equal pair weights, no implicit prepended0, missing invalid values rejected, one sample returns null pair metrics and INSUFFICIENT_PAIRS.
Existing F60 pure attribute_samples provides independent production-compatibility evidence on uniform synthetic input. Its exact source9ff1a333dcc45d14577246651f88b28d5935a6dce954b308bb90b1d3f4ccf018 is copied without changes into THIS branch, not moved from original. No old log/CLI path is invoked. F64 irregular sampling is a new explicit extension; F60 grid restrictions are not weakened.
New F64 production arithmetic uses Fraction. The independent oracle uses integer gcd/lcm/common-denominator sums and linear interpolation; no production/generator helpers or Fraction shared. Uniform expected MSE/support is additionally compared to exact unchanged F60 output. RMS is an algebraic square root, so no ad hoc float tolerance. The diagnostic RMS threshold1 only tests unit comparator boundaries; it is NOT r, a performance threshold, or a candidate budget. Exact equality zero-error is the software acceptance criterion.
Trajectory/curvature/heading/position metrics have no defined reference in this scalar Source and remain outside scope. No estimates or fabricated truth replace them.

## r
F61 exposes a caller-declared synthetic rate_budget_per_s; no independent project-wide justified prospective r/budget exists in the inspected frozen evidence. F64 keeps R_BUDGET_UNRESOLVED and budget=null. No observed result, percentile/max, or trivial domain bound is used to approve a budget. Full F64 PASS is prohibited. If all other bounded contracts pass, final status is F64_PARTIAL_PASS_R_BUDGET_UNRESOLVED.

## Generation and split
Seven valid families: constant, linear ramp, piecewise constant, piecewise linear, deterministic pulse, bounded noise, irregular valid. Additional invalid schema/time fixtures are explicit. Formulae, seed encoding/amplitude/count are fixed in the machine contract and implementation before commit. SHA256 counter expansion uses explicit bytes/modulo, no OS randomness or wall clock; no cryptographic/statistical quality claim. Public seeds0/1; public count17, with count1 and8000 tested separately.
Existing exposed F10/F60/F62 cases stay development/regression forever. No original outputs are regenerated here. New holdout uses exactly two seeds derived after PRE_HOLDOUT_COMMIT via SHA256 of ASCII F64_HOLDOUT_V1: plus lowercase40hex commit SHA (no newline); bytes0:8 and8:16 unsigned big endian. All source/tests/criteria and public evidence are in that commit.

## Single adjudication and reproducibility
The user requires both one holdout evaluation and two independent reproductions. This preregistration resolves that at the execution-protocol level: ONE nonadaptive adjudication cohort with TWO preplanned fresh-directory reproduction passes, both complete BEFORE results are inspected. Each pass generates fixtures and computes each path once. A single combined verdict checks both and byte equality. No selection among runs, retry, tuning, tolerance/seed/rule change after inspection. If either fails or differs, seal failure without code changes. CI may subsequently verify immutable sealed outputs; that is reproduction, never a new selection opportunity.
This holdout is procedurally separated from development, not external secret data, not real driving, not Controller performance, not candidate generalization, and not Private E2/HOLDOUT access.

## Controller isolation
Static AST walks local project imports and restricts imports/call surfaces. Controller/system/car/submodule/simulator roots and controller-coupled metric modules are forbidden. Dynamic guarded runs reject forbidden imports before load and process/network/native-loader/private-log events. Already-loaded controller modules cause failure. Synthetic sentinel self-tests intentionally attempt rejected imports/processes; blocked probes are separate from actual Controller initialization/calls, which must stay0. Python instrumentation is not an OS sandbox against arbitrary hostile interpreter behavior; results apply to reviewed code/dependency graph.

## Acceptance and freeze
All tests collected/executed with exact ledger and no skip/fail/error; exact Source/time/error boundary results; independent oracle equality; existing uniform F60 equivalence; canonical bytes deterministic; Controller loaded/called0; protected old308 file hashes unchanged; no raw data/secrets. Current r unresolved prevents total PASS.
AST/source/criteria/test/dependency manifests are sealed before deriving holdout. After cohort begins no code/docs/criteria/threshold/seed/pin edits. Final evidence/report/ZIP only may be added, with fixed ZIP member ordering/timestamp/mode. Commit2 contains evidence only. No wall time/temp directory names in canonical artifacts; external development logs are excluded and identified.
CI is an independent new workflow/job; existing Exact157/Exact27 and historical workflows remain byte-identical. No push/manual dispatch authority is inferred from historical approvals. If current push authority remains uncertain: PUSH_NOT_RUN_AUTHORITY_UNCONFIRMED / CI_NOT_RUN_AUTHORITY_UNAVAILABLE.

## Source provenance
MIT repository license applies. F10 metric contract and F60 pure arithmetic are read-only references; F61 Source/floating-time contract remains unchanged. Original4 untracked files remain original4. New F64 branch may track an exact-byte dependency copy; original branch Git state is unchanged.

## Implementation plan
- [ ] Record/verify baseline and old308 artifacts before changes.
- [ ] Seal this document/machine contract hash before implementation.
- [ ] Write focused Source/time/metric/isolation tests, observe RED with absent API.
- [ ] Implement only inert generator, production metrics, independent integer oracle, isolation and runner; observe GREEN.
- [ ] Run related Controller-free regressions and static checks; independent code review before holdout.
- [ ] Commit source/contracts/public fixtures/criteria as PRE_HOLDOUT_COMMIT.
- [ ] Derive seeds after commit and run one two-pass cohort without inspecting intermediate results.
- [ ] Freeze outputs; verify old hashes, repeatability, canonical ZIP, privacy, report; commit evidence only.
- [ ] Leave push/remote CI unexecuted absent current authority.
