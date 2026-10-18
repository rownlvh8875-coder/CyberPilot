# E2 V2 Q1 reference-path diagnostic

## Identity and purpose

Cyber Validation; additive one-job numerical diagnostic, pre-execution validation.
Mission `STAGE1_V4_E2_V2_Q1_REFERENCE_PATH_DIAGNOSTIC`; baseline
`45d1425047c725aab27f3075964f881190929f1a`, branch `feature/cyber-autotune`.
Identify the failed TRAIN job from the sealed abort, never from public Q1 2/32.
No D2 selection, DEV, rollout, refit, numerical-contract amendment or adoption.
No vehicle applicability or road-safety claim.

## Original references and traced computation

Source: [CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot), verified
feature branch above; original V4 `bd8045ef2a0da62a92603439f38e7740f5923622`;
failed V2 execution `2335a8d618530185f09781ea6cb44bceb921516c`.
Use original MIT-licensed repository code; no external implementation copied.
The diagnostic protocol pins 57 source/test files and immutable V2 lineage.

`empirical_s2_ri_fit_cv_math.transform` normalizes each row independently.
`empirical_hurdle_fit_cv_math.predict_delta` returns `transform(x, norm) @ coefficients`.
Original `integrated` collects whole-job MOVE rows in original order, invokes
Stage2 once, then projects current tick plus continuous delta. It does not run
Stage2 separately on the selected rows inside each 512-row chunk.

- A: unchanged V2 `potentials`, original segment order, all rows in fixed512 chunks.
- C: unchanged V2 `qualification(Q1)` and `full_design`, whole-job D0-selected rows.
- Compare C to A at exactly the same selected original-order rows.
- B, W and canonical rowwise inference are forbidden in the private diagnostic.

Q1 includes dtype, shape, signed zero and all raw bits. Projected-tick equality,
small ULP distance and `allclose` cannot establish its byte-exact requirement.
NumPy documents that [matmul uses optimized BLAS when possible](https://numpy.org/doc/stable/reference/generated/numpy.matmul.html).
The source provides no fixed reduction-order guarantee across these batch shapes.
This observation does not identify a specific BLAS kernel, FMA or CPU instruction.

## Changes and expected effect

New core observes the unchanged frozen predictor/transform call and returns the
exact original objects; RAM-only xa/za/xc/zc witnesses compare feature and transformed
rows. It records private layout/alignment context and aggregate float/projection
differences, never row vectors. Observation buffers and a fresh one-job process
can change allocator context relative to the original 32-job run. Failure to
reproduce is a reproduction conflict, not a retroactive PASS; no second attempt.

New private adapter authenticates current grant/reviews/CI before source metadata.
Old B0/B1/C/E1/V2 receipts establish identity only. It binds one failed job,
TRAIN route, exact segment IDs and eight causal/derived fields; three TRAIN
fields and six Stage2 model/normalizer arrays complete the capability.
Metadata-derived raw hash/dtype/shape/order/caps are sealed, file/directory-fsynced
and read back before arrays are enabled. Existing openat2, no-alias/hash/NPY/gzip
checks remain unchanged. Mixed TRAIN carrier, directory discovery and DEV are denied.
Python audit and exact reader checks are defense in depth; no OS sandbox is claimed.

Frozen bounds: N<=336,941, features<=93, source rows<=916,535, segments<=154,
chunk512, one worker/thread; analytical live bound 6,086,568,806 bytes including
10 matrix workspaces, source/cache base and 2GiB native/runtime reserve, AS8GiB.
CPU900s, wall1800s, 1,600 source opens/8GiB input, 8MiB/file, 32MiB total output,
2GiB disk reserve. Original source writes0. Exclusive 0700/0600 private outputs.
No chunk, batch, normalization or coefficient substitution to force agreement.

## Regression risk and predeclared acceptance

Keep V2 failure, original models, D2 selector, objective/guards, frozen32 gate,
controller, workflows and historical public results unchanged. There is no new
performance acceptance. A/C input mismatch, numerical mismatch and reproduction
conflict have separate statuses. A failure cannot start D2 or another experiment.
Rollback is removal of this additive diagnostic only; no source evidence changes.
Two independent final-byte scientific and authority/privacy approvals plus
pre-execution exact-head CI success are mandatory before numeric input reads.

## Validation method and actual results

Public synthetic fixtures are fixed before execution: original60, parity60,
additional aligned60 (same seeds/shapes/scales/masks; synthetic-only canonical
left-to-right multiply/add reference). No seed search or favorable subset.

| Fresh public synthetic set | C/A byte mismatch fixtures | Max ULP C/A | Transformed C/A rows |
| --- | ---: | ---: | --- |
| Original60 | 21/60 | 12 | exact |
| Frozen parity60 | 42/60 | 16 | exact |
| Aligned60 | 21/60 | 12 | exact |

Aligned C vs synthetic canonical reference differs in 60/60 fixtures (max7261ULP).
That canonical reference is a diagnostic contrast, never an adopted D0 substitute.
A separate 1ULP half-tick fixture changes projected tick; a 1ULP non-boundary
fixture keeps the same tick while failing raw-byte equality. Synthetic findings
cannot establish the actual private failed job or another job's Q1/Q3 status.

New focused synthetic contract tests: 41 PASS. Metadata lifecycle covers exact
route/field plan, pre-readback array denial, descriptor/model/anchor/count mutation,
review/CI/source-policy failure before historical controls, and forbidden paths.
Existing focused suites, full AutoTune/controls, lateral, Ruff, compileall, SCons,
publication/source pins and exact-head CI are required; final results follow after
execution/publication. Replay, simulation/closed-loop, shadow and road use are
not authorized and not performed; unit/CI success cannot substitute for them.

## Numerical feasibility and remedies (assessment, no adoption)

| Option | Original D0 numerical meaning / comparability | D2 implications and approval gap |
| --- | --- | --- |
| A: retain byte-exact Q1/Q3 | preserves original selected-row reference; repeated stops remain possible | empirical per-mask qualification, no universal cross-batch guarantee proven; fresh execution requires explicit grant |
| B: canonical batch-independent kernel | may differ from historical BLAS output, continuous delta and projection | new numerical policy, source pins and D0/D1 revalidation plan required; fixed per-row losses could be defined consistently only under that new contract |
| C: new consistency definition | cannot be represented as existing byte-exact PASS | tick equality alone insufficient for SSE/SAE, zero-tolerance guards and lexicographic winner; separately approve quantitative error/decision-impact contract |
| D: redesign cache around original reference | keeping D0 selected rows preserves that one mask only | arbitrary D2 masks remain unproven; per-threshold inference would violate frozen bounded sweep; new cache/policy feasibility proof and explicit approval required |

Q1 success for D0 would not certify the different D2 mask in Q3. If a retained
row's Stage2 delta depends on the packed selected batch, fixed per-row potential
leaves and independent context sweeps are not automatically equivalent to that
selected-row computation. Original D0 numerical meaning plus a universally
batch-independent cache is NOT_PROVEN. Changing only storage does not prove it.
No option, tolerance, canonical kernel, new decision or policy is implemented.

## Handoff and preserved state

Private diagnostic: PENDING final reviews, Commit A and exact-head CI.
Public output is restricted to qualitative classification, never failed-job ID,
row counts/positions, ULP values, private hashes, decisions or model values.
This preserves joint C/E/E2 complementary suppression without adding private cells.

Historical E2 V1/V2 remain
`E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`.
D2 `PERFORMANCE_NOT_EVALUATED`; selected_candidate=null, selected_policy=null.
Historical TRAIN gate NOT_SAVED; whole-replica equality not fully reverified.
HOLDOUT CLOSED, vehicle NOT_READY/authority NONE, pooled refit/composition/V5
NOT_AUTHORIZED; Hugging Face NOT_REQUIRED/NOT_USED. Source-grid tick is not
physical EPS motion; logged command is not applied EPS torque.
Stop after one bounded diagnosis and public-safe publication. No automatic remedy,
E2 resume, D2 selection/evaluation, HOLDOUT or vehicle action.
