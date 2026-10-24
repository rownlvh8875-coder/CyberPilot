# Stage2 deterministic numerical design

## Identity and purpose

Status: `E2_DETERMINISTIC_NUMERICS_DESIGN_FROZEN_IMPLEMENTATION_PENDING`.
Mission: `STAGE1_V4_E2_DETERMINISTIC_NUMERICS_DESIGN_AND_CI_LFS_TRIAGE`.
Area: Cyber Validation / AutoTune. Design and public synthetic evidence only.
Repository: https://github.com/rownlvh8875-coder/CyberPilot, branch
`feature/cyber-autotune`, baseline `602855e53fe1f66bbb8c4a99e6d8841b4a6c2afc`.
No private handoff, E-drive, driving array or private model was opened.
No runtime, selector, model, normalizer, workflow or LFS configuration was changed.
The only executable addition is a test-local synthetic oracle, never imported by a scientific runtime.

## Original references

Original V4 execution: `bd8045ef2a0da62a92603439f38e7740f5923622`.
The companion JSON binds raw mathematical/writer/diagnostic/selector source hashes,
seven public protocol/result identities and all 22 future validation domains.
Original `empirical_hurdle_fit_cv_math.predict_delta` calls
`empirical_s2_ri_fit_cv_math.transform(x, normalizer) @ coefficients`.
The caller gathers whole-job MOVE rows in their original order. The E2 cache calls
that same function on original segment/order 512-row all-row chunks.
The original upstream openpilot/CyberPilot source and its existing license notices
are preserved (root LICENSE: MIT, Copyright 2018 Comma.ai, Inc.); this design copies no third-party native kernel. There are no new
submodule or dependency revisions.

The prior public one-job Q1 finding is immutable:
`E2_V2_Q1_BATCH_LAYOUT_NUMERICAL_DIFFERENCE_CONFIRMED`. Source rows,
selected rows, coefficients, normalizer and transformed rows matched; Stage2
float64 values and bytes differed, beyond signed zero; projected ticks matched
in that observed job. This task does not reopen its private evidence. A particular
OpenBLAS kernel, FMA instruction or relative physical accuracy was not identified.
NumPy documents that matmul uses optimized BLAS when possible; this is not a
promise of identical reductions across batch shapes. [NumPy matmul](https://numpy.org/doc/stable/reference/generated/numpy.matmul.html)

Historical D0/C means the original selected-row BLAS output. Proposed canonical
output means a new, prospective numerical definition. Identical model parameters
do not make these two outputs identical. Neither definition is shown closer to
physical EPS movement by the available evidence.

## Changes and expected effect

The JSON contract defines `CANONICAL_STAGE2_SEPARATE_BINARY64_LEFT_FOLD_V1`:

1. Require finite binary64 input, the exact frozen five-field normalizer and
   coefficient identity, original feature order and effective indices.
2. Preserve the intercept as positive `1.0`; do not normalize it. Constant
   columns are excluded by frozen effective indices; their std must be zero.
   Effective non-intercept std must be positive. `constant_reference` is identity
   metadata, not an arithmetic operand in the original transform.
3. For each non-intercept effective column, round subtraction, then division,
   separately to binary64 nearest/ties-even. Traverse original effective order.
4. Start the accumulator at positive zero. Round each multiplication, then each
   left-to-right addition, separately to binary64. Never fuse or reassociate.
5. Preserve IEEE signed-zero operation results and gradual underflow. Reject
   nonfinite input or intermediate values; no clipping or row dropping.
6. Preserve original projection: binary64 current-tick plus delta, ties-to-even
   `rint`, signed16 range validation and fail closed on overflow.

Given the same row and model, induction over these fixed column operations
makes every intermediate independent of adjacent rows or batch length. This
argument assumes a qualified environment implementing those exact operations;
it does not prove arbitrary compilers or architectures equivalent.

The test oracle uses separate CPython float subtraction/division/product/add
operations, with no BLAS or reduction primitive. CPython's common binary64 model
and per-operation rounding are documented, but deployment still needs pinned
build/ABI, rounding mode and subnormal checks. [Python floating point](https://docs.python.org/3.12/tutorial/floatingpoint.html)
Host checks here are synthetic preconditions, not a complete MXCSR or platform
certification. A native implementation must additionally test FTZ/DAZ, generated
code, CPU features, compiler/linker/runtime versions and binary identity.
No cross-platform byte-equality claim is made.

| Approach | Original numerical meaning | Feasibility / limitation | Recommendation |
| --- | --- | --- | --- |
| A: scalar fixed-order reference | New prospective values; historical bytes need not match | Simple row-independence proof, O(NP), measured below; runtime overhead remains | Use this precise definition as oracle for a separately approved numerical branch |
| B: deterministic native loop | Same proposed definition only after exact oracle qualification | Pin build/CPU, prohibit fast-math, reassociation and FMA contraction; no implementation or speed measurement here | Optional optimization after A is accepted; not required merely by current TRAIN timing |
| C: keep BLAS with new consistency contract | Retains historical call semantics but all-row/selected output may differ | Need explicit ULP/loss/guard/winner/projection/recursive analysis; tick equality is insufficient | Do not adopt a tolerance or delete Q1/Q3 to restart E2 |

Candidate native flags include `-fno-fast-math`, `-ffp-contract=off`,
`-fno-associative-math` and `-frounding-math`. Flags alone do not establish exact
rounding on every target. [GCC optimization options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
No native code was compiled or installed by this change.

### D2, historical comparisons and new invariants

Using the same canonical kernel for TRAIN potentials and selected-row inference
can define fixed per-row HOLD/MOVE losses. However, canonical delta can change
continuous SSE/SAE, guard feasibility, lexicographic ties, the selected decision,
projected hits near half-ticks and recursive history. Keeping coefficients frozen
is insufficient to claim unchanged scientific semantics.

The five objective priorities and four D0-relative guards remain the design
recipe. A future amendment must explicitly define the guard reference as a new
canonical D0 TRAIN numerical reference with the same reconstructed D0 gate.
It cannot silently compare canonical D2 with historical BLAS D0 deltas. New
canonical D0/D1 replays would be distinct numerical reference results under the
same three policies, not additional policy arms. Historical D0/D1 results remain
immutable and must be shown separately. Same-anchor coverage, Stage1 scores,
normalizers, commands, features and comparators must also be qualified.

Do not simply remove Q1/Q3. A new numerical contract must require canonical cache
vs canonical whole-job D0 selected-row byte equality, then canonical cache vs
final D2 selected-row byte equality, including dtype, order, shape and signed zero.
It must additionally qualify feature assembly, indexing, model receipt, Stage1
routing/score repeatability, projection and recursive state. Row-independent
Stage2 arithmetic alone does not certify the caller or complete rollout.

## Regression risk and acceptance

The existing 32 clauses (5 one-step, 3 TRUE MOVE, 24 rollout), support 201,
epsilon 0, same-anchor HOLD_LAST, both-fold requirement, H25/50/100/200 and
OVERALL/PATH_MOVED are unchanged. All 22 domain definitions remain referenced
without marking performance PASS. D2 is still `PERFORMANCE_NOT_EVALUATED`.
No numerical tolerance, model refit, threshold adjustment or policy arm was added.

A future experiment needs explicit approval of the new source and numerical
policy/guard reference, a qualified implementation, exact input/resource/privacy
binding and fresh execution authority. It then needs 32-job qualification,
64 TRAIN decisions, final selected-path qualification, durable TRAIN seal before
DEV, full rollout, two fresh byte-exact repeats and verify-only. It remains an
exploratory retrospective comparison; untouched evidence is still required.
Rollback here is simply non-adoption: no production hook exists.

## Validation method and actual results

Fresh public synthetic checks ran on WSL Ubuntu-24.04, CPython 3.12.13,
NumPy 2.5.3, OpenBLAS 0.3.34.106.0, x86_64, one worker/BLAS thread.
The 60 mask configurations reuse 12 unique `(L, scale)` full input/model pairs
(and four full X populations). These descriptive counts include repeated inputs,
not 60 independent samples. Seeds/shapes/scales/masks were declared before execution;
there was no adaptive seed or batch search. Original60, Parity60 and Aligned60
were rerun; their present results are not substituted for earlier observations.

| Public synthetic set | Actual result |
| --- | --- |
| Original60 | B/A mismatch 0/60; C/A mismatch 21/60 |
| Parity60 | B/A mismatch 44/60, max 80 ULP; C/A mismatch 42/60 |
| Aligned60 | C/A mismatch 21/60, max 12 ULP |
| Proposed canonical60 | 60/60 normalization byte parity; 600/600 batch checks PASS |
| Canonical vs historical BLAS | Byte mismatch 60/60; max 7,261 ULP, max absolute difference 1.3642420526593924e-12 |
| Same 60 projected outputs | No observed tick difference in these fixtures |
| Fixed-tree synthetic continuous loss | SSE differs in 10/60; SAE differs in 10/60 |
| Dedicated half-tick case | One ULP can change the projected integer tick |

The 600 batch checks cover single rows, full population, 512-row chunks,
fixed segment partitions, sparse/dense/alternating/first-last masks, unrelated
adjacent rows and Fortran layout. Synthetic targets are `(row_index % 5) - 2`,
not driving truth. Edge tests include signed zero, separate-vs-fused arithmetic,
subnormal/underflow, constant/intercept handling, invalid normalizers, each
nonfinite/overflow stage and signed16 projection. None proves empirical gain.

One timed scalar pass per declared benchmark:

| N × P | Kernel wall | Process CPU | Linux peak RSS | Input / output bytes |
| --- | ---: | ---: | ---: | ---: |
| 8,192 × 93 | 0.13645 s | 0.15052 s | 55,252 KiB | 6,094,848 / 65,536 |
| 336,941 × 93 | 5.38050 s | 5.63041 s | 532,816 KiB | 250,684,104 / 2,695,528 |

Peak RSS includes synthetic input generation. Time is O(NP); additional oracle
storage for the fold/output is O(N+P). The current test oracle also allocates an
O(NP) finite-validation boolean temporary (max 31,335,513 bytes); optional
transformed-row diagnostics are O(NP) too. Total auxiliary complexity of this
test implementation is therefore O(NP), excluding the input.
A linear estimate gives 172.18 seconds for one max-N/max-P pass over 32 jobs,
or 516.53 seconds for three worst-case TRAIN passes (cache/Q1/Q3). These are
estimates, not measurements or a complete E2 resource guarantee. Feature
assembly, D2 selection, Stage1 and recursive cost are unmeasured here. No
supported native speedup estimate is available. Existing 8 GiB and CPU/wall
contracts need a new caller lifetime/resource qualification before use.

Local focused, full regression/build, JSON/pins/privacy and independent-review
results are recorded below after actual execution. Replay vs empirical baseline,
vehicle simulation and shadow validation are NOT RUN and NOT AUTHORIZED.

- New focused tests: 21 PASS (`python -B -m unittest ...deterministic_numerics_design`).
- Fifteen focused public/synthetic modules: 520 PASS, 24.875 seconds, with E/D mounts masked read-only.
- Lateral closed-loop/gate/plant/scenarios synthetic modules: 40 PASS.
- Ruff on AutoTune: PASS; compileall: PASS; local `scons -u -j4`: PASS (prepared workspace, not a fresh LFS fetch).
- JSON parse: 833 files PASS; canonical receipts/source/index-pointer pins are asserted by the new tests.
- Full local AutoTune/controls: 5,737 PASS at `bbb7ee02e61fd394a817ef6d69ef4a776cfc5b12`, with four workers and E/D mounts masked read-only. This is `LOCAL_FULL_REGRESSION`, not GitHub FULL_CI.
- Final independent approvals bind the five final file digests in the publication commit and final handoff. Final exact-head Actions outcome is observed after push and reported there; no success is inferred in advance.
- All actual private/scientific forbidden-operation counters in the numerical contract are zero.


## Handoff

Five additive files carry this design, the machine contract, CI triage/inventory
and one synthetic test module. Historical scientific sources/results, failed Q1,
workflow and LFS pointers remain unchanged. Future numerical implementation and
CI repair are two separate approval scopes; private E2 execution needs a third
explicit grant after those prerequisites. HOLDOUT remains CLOSED, vehicle
NOT_READY/authority NONE, selected candidate/policy null. No performance or
vehicle-readiness claim follows from this design. STOP after publication.
