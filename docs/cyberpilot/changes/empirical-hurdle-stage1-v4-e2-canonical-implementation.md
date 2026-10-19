# Standalone canonical Stage2 and offline numerical CI

## Identity and purpose

Mission: `STAGE1_V4_E2_CANONICAL_STAGE2_IMPLEMENTATION_AND_OFFLINE_CI`.
Branch `feature/cyber-autotune`, baseline `d9d6b6f2747925fc386af4dbf44145861d8c6a01`.
Standalone arithmetic status: `EXPERIMENTAL_NON_WIRED`.
This increment implements the frozen `V4_E2_CANONICAL_STAGE2_NUMERICAL_DESIGN_V1`
as a separate in-memory Python API and adds an independent public/synthetic CI.
Original Stage2, V4/E2 executors, selector, acceptance, full workflow, LFS
configuration/pointers and historical artifacts are unchanged.
No private handoff, model, TRAIN/DEV, raw/qlog, HOLDOUT or vehicle was accessed.

## Original references

Original V4: `bd8045ef2a0da62a92603439f38e7740f5923622`,
https://github.com/rownlvh8875-coder/CyberPilot, verified branch above.
Original math `empirical_hurdle_fit_cv_math.predict_delta` and
`empirical_s2_ri_fit_cv_math.transform` retain historical BLAS semantics.
The root MIT license, Copyright 2018 Comma.ai, Inc., and existing attribution
are preserved. No native kernel or third-party implementation is copied.
No submodule revisions or model assets are changed.

Frozen design raw SHA256:
`8701a98aa49307b9e785ce871aecad2fc35c4da2f804cff6a90471a7d9bb86c3`.
Independent oracle raw SHA256:
`85f4cb7363b28c1dafd8f9e2b3b479400f2b83f0d0080ea050d5b53f547be39e`.
Both remain immutable. The new implementation lock binds new source/workflow/
tests/dependency hashes and historical source/public-contract hashes.
The lock does not contain a self-referential new commit or final CI run ID;
post-push observations belong in the final handoff.

## Changes and expected effect

`empirical_hurdle_v4_e2_canonical_stage2.canonical_predict_delta(x, model)`
accepts ordinary native-endian float64 NumPy matrices with 5/13/33/93 columns,
the frozen five-field normalizer and float64 coefficient vector. It returns
an original-order float64 vector, including a valid zero-row result. It has no
file/model/network loading API or automatic caller integration.

Validation checks finite inputs, intercept input, normalizer fields/shapes,
constant mask/std consistency, ascending effective indices exactly corresponding
to that mask, first effective index 0 and coefficient length/dtype/finite values.
These are structural in-memory checks. They do not authenticate a private model,
anchor or feature's physical meaning; future authorized callers must bind exact
source/model/normalizer receipts and original feature order.

Each row starts with positive zero. Intercept normalization yields positive one
without subtraction/division. Every other effective column performs separate
binary64 subtraction and division, followed by separate product and left-to-right
addition. Constant columns are excluded, and `constant_reference` is validated
metadata rather than an arithmetic operand. Signed-zero operation results are
preserved. Nonfinite input/intermediates fail closed; no clipping, row dropping,
tolerance, FMA, dot/matmul, sum/fsum, reassociation or lower precision is used.
Projection is not reimplemented: consumers must retain the existing frozen
project/nearest-ties-even/signed16 behavior.

The module independently implements this arithmetic. It does not import or call
the test-local oracle, and the oracle is not changed to call the new module.
Rational FMA and associativity witnesses, invalid-domain and rounding-boundary
cases help detect shared assumptions or arithmetic mutations.

### Environment and resource scope

The module checks CPython 3.12.13, NumPy 2.5.3, Linux x86_64, binary64 format and
double storage, Linux FE_TONEAREST, gradual-underflow bit witnesses and a separate
multiply/add witness. It queries fenv and never sets it. Failure is
`CANONICAL_STAGE2_ENVIRONMENT_NOT_QUALIFIED`. Compatibility is limited to tested
builds/environments; these checks are not universal CPU/compiler certification.
The local tested interpreter reports Clang 22.1.3. Ubuntu 24.04 is the development
and CI runner; API gates do not attempt distro authentication through file reads.

Time is O(NP). Output/model scalar storage is O(N+P); validation also creates an
N*P boolean temporary, so current auxiliary complexity is O(NP). At maximum
predeclared N=336,941 and P=93 that temporary is 31,335,513 bytes.
One fresh process per declared synthetic benchmark, seed 20261019, one worker/
BLAS thread, CPU cap120s, wall cap180s and address-space cap8GiB:

| N × P | Kernel wall | Kernel CPU | Linux peak RSS | Input / output bytes |
| --- | ---: | ---: | ---: | ---: |
| 8,192 × 93 | 0.16854s | 0.17201s | 49,356 KiB | 6,094,848 / 65,536 |
| 336,941 × 93 | 7.27119s | 7.27017s | 526,872 KiB | 250,684,104 / 2,695,528 |

RSS includes synthetic generation and runtime. Both output SHA256 values exactly
match the frozen independent-oracle benchmark digests. These single measurements
are not statistical timing bounds or a full E2 resource qualification. Feature
assembly, selector, DEV and recursive workload remain unmeasured here. Native
optimization is not implemented or authorized.

### Independent workflow boundary

`.github/workflows/cyberpilot-numerical-offline.yaml` reports
`OFFLINE_STATIC_NUMERICAL_CI` under the name
`CyberPilot Offline Static Numerical CI`. It uses pinned checkout/setup-python
commits, Ubuntu24.04, exact Python3.12.13, fetch-depth0 and source-only checkout
with LFS/submodules/persisted credentials disabled. It never runs op.sh setup,
explicit LFS pull, full openpilot installation or model download.

Only NumPy2.5.3, Ruff0.16.7 and PyYAML6.0.3 are installed from official PyPI,
using exact Linux/CPython wheel hashes, binary-only and require-hashes. Official
Python artifact and wheel availability were checked before implementation.
[Python artifact manifest](https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json),
[NumPy](https://pypi.org/project/numpy/2.5.3/), [Ruff](https://pypi.org/project/ruff/0.16.7/),
[PyYAML](https://pypi.org/project/PyYAML/6.0.3/).

`tools/cyberpilot/run_numerical_offline.py` selects the entire new tests module,
the unchanged design tests21 and public TestNumericalDiagnostic14. It also
executes fixed Original60, Parity60 and Aligned60 helpers. Legacy public helpers
transitively import reader/executor definitions; no entry point is executed.
Their external closure is stdlib+NumPy; workflow parsing explicitly adds PyYAML.
Private adapters, controller/system imports, Python socket operations, model
payload reads and file writes are denied. Only read-only git-show object queries
and their read-side FIFO descriptors are admitted as child operations. NumPy's
own public `testing._private` helpers are allowed, distinct from private scientific
adapters. Negative tests verify the boundary rather than skipping failures.

This Python-level audit/import boundary is not an OS sandbox or complete network
air gap. Checkout/package installation use network. No personal credentials or
new Secrets are supplied; checkout uses only repository read permission and
persists no credentials. Scoped Ruff, compileall, JSON/source/pointer integrity,
publication/whitespace and clean-workspace checks remain mandatory.

## Regression risk and acceptance

Historical D0/D1 results remain BLAS references; canonical output is a distinct
prospective definition even with identical coefficients. Differences do not show
which value is physically more accurate. No mismatch count/ULP from historical
BLAS is used as an acceptance cutoff. One ULP can cross a half-tick boundary;
continuous SSE/SAE and eventual threshold winners can change even when ticks do
not. Stage2 row independence alone does not qualify Stage1 or full recursion.
The safe rollback is non-adoption: no original caller is wired to this module.

Existing 32 clauses, 22 domains, support201, epsilon0, same-anchor HOLD_LAST,
both folds and H25/50/100/200 OVERALL/PATH_MOVED are unchanged. D2 remains
PERFORMANCE_NOT_EVALUATED; scientific acceptance has not been executed.

## Validation method and actual results

The fixed60 configurations reuse12 input/model pairs, not60 independent samples.
Tests compare the new kernel with the unchanged oracle and check600 original-order
batch/layout/neighbor conditions. Additional cases cover zero batches, normalizer/
effective-index mutations, signed zeros, subnormal/underflow, each nonfinite stage,
separate-vs-fused arithmetic, reassociation and frozen projection boundaries.
Original60/Parity60/Aligned60 are executed with unchanged seeds/shapes/masks.

- New standalone/authority/workflow/legacy fixtures module: 26 tests within the 61-test offline suite.
- Clean venv installed only the three pinned wheels; the full offline suite: 61 PASS / 20.957s, private adapters imported0.
- Full-population oracle parity60/60, batch conditions600/600 and oracle normalization vs original transform60/60 PASS. A separate test observes the new kernel normalization locals for three rows at each of four dimensions, with constant exclusion and unscaled intercept, and compares their bytes directly with original transform and the independent oracle.
- New vs historical BLAS: byte mismatch60/60, max7,261 ULP and max absolute1.3642420526593924e-12 in this observed fixed run. Projected tick differences0/60; this is not a required equality or a physical-accuracy verdict.
- Lateral synthetic40 PASS. AutoTune Ruff, compileall and prepared-workspace SCons PASS.
- Fresh LOCAL_FULL_REGRESSION: **5,763 PASS / 614.21s**, exit0, skipped0, at implementation HEAD `92098ebd331ed2a19945847a8db37fc7eec4b94f`. Command: `python -B tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j4`. D/E mount roots were masked read-only in a mount namespace. It includes relevant E/D2/Q1/Q3/B0/B1/C/E1/attribution and controls tests; it does not constitute private empirical replay or full E2 evaluation. No executable source changed after this run.
- Initial implementation-head [offline CI 39209370644](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39209370644): completed/SUCCESS, 61 PASS / 24.338s, private adapters imported0, Ruff/syntax/publication/clean checks PASS.
- Same-head [FULL_CI 39209370573](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39209370573): completed/FAILURE at `Set up openpilot development environment`, 15 unique LFS OIDs returned HTTP404. Later build/test steps were skipped by setup failure. No LFS or workflow remedy was applied.
- Source-freeze scientific and authority reviews: both APPROVED for exact seven-file aggregate `6e28fb52e25dd1828a28e25ffb194ee4ee143711559d664ab741767b8daee656`. Review receipt SHA256 values are in the lock. The two-document actual-result delta is independently re-reviewed before publication; final review receipts belong in that commit/handoff, avoiding a self-referential receipt cycle. Final exact-head CI remains separately observed after publication.


Empirical replay, vehicle simulation and shadow validation are NOT RUN and NOT
AUTHORIZED. Offline CI SUCCESS, if observed, cannot stand in for FULL_CI or
LOCAL_FULL_REGRESSION. Final exact-head offline and full CI are observed separately after publication;
its upstream LFS failure history and missing15/252-pointer inventory are unchanged.

## Future canonical D0/D1/D2 qualification plan

Separate source/numerical-policy approval must define a new canonical D0 TRAIN
guard reference. Never mix historical BLAS deltas with canonical D2 loss leaves.
Preserve the five objective priorities and four guard recipes, while acknowledging
that values, feasibility and winner can change. Canonical D0/D1 replays are new
numerical reference results under the same three policies, not historical rewrites.

A fresh private E2 grant and exact reader/resource/privacy binding must precede
any real input access. Qualify all32 jobs, frozen source/model/anchors/Stage1,
canonical cache vs whole-job D0 selected rows (Q1), then64 TRAIN decisions and
canonical cache vs final D2 selected rows (Q3). Require all32 qualifications and
durable TRAIN seal/readback before DEV. Then perform same-anchor one-step,
all four full-state horizons, unchanged frozen32/22, two independent byte-exact
repeats, verify-only and protected publication. This increment authorizes none
of those private operations. HOLDOUT remains CLOSED and vehicle authority NONE.

## Handoff

New API: standalone implementation only. Original scientific sources/models/
normalizers/results/full workflow/LFS files are unchanged; no private input was
opened. Two independent final-byte reviews bind source/workflow/tests/docs and
are reported with receipts in the publication commit/final handoff. Final exact-
head offline/full CI outcomes are reported there without hash cycles in the lock.
Policy/candidate selections remain null; pooled refit, composition, vehicle and
V5 remain unauthorized. STOP after final publication verification.
