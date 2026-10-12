# Empirical model family identifiability audit

## Identity and purpose

Cyber Validation additive increment: EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_AUDIT_V1.
Baseline: 79a7526003e13635f3b9c05b399f8e9909a2c4cb on feature/cyber-autotune.
Status: implemented and independently reviewed; local validation complete. Exact-HEAD CI is a post-push gate.

The authoritative dataset remains RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL.
Historical reproduction PASS and qlog reconciliation COMPLETE have different meanings.
This audit reads the exact original 154-rlog causal cache, resolves the final-readiness
precedence, and calls the existing causal-support guard. Both exposed routes remain
RETROSPECTIVE_TRAIN_DEV_CV_POOL, with no independent validation, qualification or
HOLDOUT authority. All prior tracked artifacts and private input bytes remain immutable.

No model, coefficients, prediction, residual, performance comparison or family winner
is produced. The fixed envelopes describe future feasibility; they do not select a
lag, history length, parameterization or fitting policy.

## Original references

Source: https://github.com/ajouatom/openpilot at exact recorded commit
18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29, independent of a moving branch name.
The published steering-rate contract binds repository, commit, tree, 13 file hashes,
reviewed source-slice hashes and exact license hash. The earlier source provenance
receipt is also bound. Git blobs are inspected; recorded code is not executed or
copied into a production controller.

The traced measurement chain is Hyundai CarState → SAS11.SAS_Speed → DBC/parser
decoded numeric value → carState Float32 → existing exact float64 cache.
The signal is little-endian unsigned 8-bit, factor 4, offset 0, empty DBC unit.
The DBC declared range and encoded numeric range differ; a reserved-code meaning
is not inferred. The downstream use of math.radians is a consumer assumption,
not independent evidence of the sensor's physical unit or signed-rate meaning.

Classification: SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL.
Neither signed physical deg/s nor unsigned physical rate magnitude is source-proven.
Finite-difference correlations are explicitly
EMPIRICAL_DIAGNOSTIC_ONLY_NOT_SOURCE_SEMANTIC_PROOF.

The S3 audit distinguishes controller error deadzone, controller friction
compensation, command saturation/slew/driver limits, display-speed hysteresis and
measurement quantization. None establishes actuator physical deadzone or EPS
hysteresis. S3_SOURCE_MECHANISM_BLOCKED; no numeric regime discovery is run.

No new dependency or submodule change. NumPy's documented numerical-rank tolerance:
[NumPy matrix_rank](https://numpy.org/doc/stable/reference/generated/numpy.linalg.matrix_rank.html).

## Changes and expected effect

Five new additive modules implement policy/source binding, input-only math,
read-only execution, exact aggregate validation and publication. Four new test
modules exercise contracts, math, execution and privacy. Existing extractors,
support guard, resolver, controllers, visualizers and historical JSON are unchanged.

Before any array deserialization, the policy is sealed outside the repository,
then the exact source contract and whole 154-segment admission are verified.
Both excluded qlog content identities are denied before array access. No array is
opened and then filtered by stream type. Each input file has an exact before/after
hash, and arrays must match recorded dtype, shape, C order and byte digests.

Base admission uses causal validity, the historical diagnostic mask, complete
source/config/profile provenance and current/past state/control/output source ages.
Unavailable or unknown values are not zero-filled. Repeated state samples do not
provide new measurement transitions. Admitted streaks break at segment, causal run,
mask, missing-clock or integer-grid discontinuity. Speed-bin changes remain a
reported context, not a new causal-run boundary.

The fixed 100 Hz/20 ms policy is unchanged. The only support gate is the existing
201 rows per route; it is a future development availability gate, not model acceptance.

### Canonical input-only forms

S1 has 21 forms, command lag d=0..20:
angle[k], source-native rate[k], logged normalized post-CarController command[k-d],
speed[k], intercept=1. Five columns. The physical state interpretation remains
blocked by rate semantics.

S2 has 45 forms, history L=1..45:
chronological L command samples, chronological L angle samples, current source-native
rate and current speed. Column count is 2L+2, with no intercept. Next delta-angle
availability is separate; no target value enters X, normalization or feature choice.

Each form reports both routes and pooled scope separately. Every nonconstant input
column is centered by its population mean and scaled by population standard deviation.
Constant columns become zero, except the declared S1 intercept remains one.
Direct float64 SVD reports the complete singular spectrum and numerical rank using
smax × max(rows, columns) × float64 epsilon. This is not an algebraic or symbolic
identifiability proof. Condition numbers have no acceptance cutoff. Constant/duplicate
columns, input variance, input correlation extrema and the standardized second-moment
digest are reported without publishing matrices or individual samples.

Next-state support requires an adjacent admitted same-run row. Rate diagnostics use
strictly positive selected-state timestamp differences. No fitted scale correction,
unit/sign promotion, target-based feature selection or controller inverse is attempted.

### Reset, timing and leakage contract

The nonexecuting family reset contract forbids carrying history or latent state across
route, segment, causal-run, inactive, override or fault boundaries. Reengagement must
start new valid history. Initialization can use current/past available information only;
a future fitting policy must freeze its precise semantics before results.

Publish-aligned request/output/state messages have no transaction identity:
REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE. The exact raw/normalized representation
bridge is not physical actuation: PHYSICAL_EPS_APPLICATION_UNAVAILABLE.
CLOSED_LOOP_IDENTIFICATION_BIAS_RISK remains unresolved. Instrumental variables,
bias correction and causal-effect estimation are not implemented.

## Regression risk and acceptance

Risks are accidental qlog promotion, target leakage, cross-boundary history, false
rate-unit proof, misleading pooled rank and private values hidden in aggregate JSON.
The exact schema rejects unknown fields, empty/incomplete envelopes, changed source
identities, nonzero raw/qlog openings, changed input bytes, malformed hashes and paths.
A complete receipt requires all 154 streams and 916,535 base rows. Individual route
structure is never replaced by pooled structure.

Acceptance is exact repeatability and correctly bounded diagnostics, not a model
performance threshold. No HOLDOUT is available or opened. Independent review found
and corrected overly permissive publication validation before policy freeze and
before real numeric access. Removing the new modules/artifacts rolls back this
additive audit without changing historical behavior.

## Validation method and actual results

First independent execution completed with result receipt
9e0d3ea76159a4d48b61124d8e222c78d1e9b0a28823417160c3252180827571.
Two independent processes produced byte-identical complete results, including
all form/scoped metrics, counts, rank spectra, admission and result receipts.
Input file hashes matched before and after both executions. Raw-reader and
coefficient-fitting APIs were trapped during execution. Publication was repeated
with exact immutable resume and all ten aggregate artifacts matched regeneration.
The first full regression run had 3,946 passes and one historical A1 worker
rejection. That worker hashes the entire AutoTune Python source tree before/after
execution; a new publication test file was edited during the first regression run.
Its redacted rejection did not preserve the exact exception, so a specific cause is
not asserted. The failing test passed in an isolated rerun without code changes.
The complete stable-source rerun passed all 3,947 tests in 1,575.82 seconds
(AutoTune 3,805; controls 142), with no concurrent diagnostic workload or source edits.
No historical worker, limit, assertion or test was weakened.

### Actual structural support

Route A/B labels below follow lexical order of the two full opaque IDs resolved
from the immutable route receipts; prefixes are display labels, not admission rules.

| Scope | Base rows | Guard-admitted rows | Adjacent pairs | L=45 windows | L=45 next-state availability |
| --- | ---: | ---: | ---: | ---: | ---: |
| A (7ae11bd9…) | 415,844 | 382,025 | 357,997 | 258,368 | 257,942 |
| B (962f2448…) | 500,691 | 328,030 | 313,516 | 196,215 | 195,505 |
| Pooled | 916,535 | 710,055 | 671,513 | 454,583 | 453,447 |

All 154 streams were checked. At L=1, admitted windows span 70 segments in A
and 75 in B; at L=45 they span 55 and 68. The base causal-valid count of 874,568
is not substituted for model-development support: the existing guard additionally
requires historical diagnostic validity, fresh/past messages and new state measurements.

| Scope | LOW admitted | MEDIUM admitted | HIGH admitted |
| --- | ---: | ---: | ---: |
| A | 36,475 | 185,582 | 159,968 |
| B | 118,882 | 127,652 | 81,496 |
| Pooled | 155,357 | 313,234 | 241,464 |

Every S1 form (21/21) and S2 form (45/45) has numerical full column rank in
each route and pooled scope. Both routes independently meet 201 next-state
availability for every form. This supports a future retrospective route-disjoint
development design, with no performance claim or winner selection.

| Scope | S1 condition-number range | S2 condition-number range |
| --- | ---: | ---: |
| A | 2.572–3.141 | 2.572–3,034.818 |
| B | 2.203–2.498 | 2.203–5,445.659 |
| Pooled | 2.280–2.576 | 2.280–4,080.819 |

These are descriptive ranges across the complete envelopes, not acceptance
thresholds or a recommendation of any lag/history. Full rank does not resolve
collinearity, latent parameterization ambiguity, measurement quantization or
closed-loop identification bias.

All 710,055 admitted angle values match the Float32 source grid. Source-native
rate has no negative admitted values. Diagnostic correlation with signed
angle finite difference is 0.0163 (A) / 0.1634 (B), while correlation with absolute
finite difference is 0.9697 / 0.9738. These observations do not establish a unit,
calibrated scale or signed physical rate; SOURCE_NATIVE_RATE_CODE_ONLY remains.

S1_PHYSICAL_STATE_INTERPRETATION_BLOCKED is retained in interpretation.
The machine-readable family states remain
S1_NUMERIC_STRUCTURE_AVAILABLE_BUT_RATE_SEMANTICS_BLOCKED,
S2_STRUCTURAL_SUPPORT_PRESENT_RATE_SEMANTICS_BLOCKED and
S3_SOURCE_MECHANISM_BLOCKED.

| Check / stage | Method | Actual result and limits |
| --- | --- | --- |
| Source/policy | Exact public Git blobs and frozen cache admission | PASS; policy 8dee196fc4905bf3da93bc4f31c8359f7030de796019c66a64ae090aa304e9fc; source contract 109bc9159d06db8ba696922b93a7dea5d5f265f2bbc0dcbf4d22aade51e2f388 |
| Input-only diagnostic | Two independent single-thread executions | PASS; exact receipt and result bytes; 154/154 input streams; 0 qlog arrays; 0 raw logs |
| Unit/regression/build | Focused, empirical, AutoTune, controls, lateral, Ruff, syntax, SCons | Focused 72 + 22 subtests; empirical 1,173 + 149 subtests; lateral 16; Ruff/syntax/SCons PASS. Full suite PASS: AutoTune 3,805 + controls 142 (3,947 total) |
| Replay vs baseline | Existing regression suite only | No new candidate replay |
| Simulation/closed loop | Not run | No candidate/plant execution |
| Shadow/vehicle | Not run | No production or vehicle authority |
| Browser | Not applicable | No UI change |
| Publication | Exact aggregate schema, privacy and historical diff | PASS; 10/10 artifacts reproduce; zero privacy findings; no tracked historical edits |
| GitHub Actions | Exact pushed HEAD | Required post-push gate; exact run and conclusion reported in completion handoff |

### Reproduction interface

The operator supplies explicit absolute external stores; no discovery or raw root
scan is performed. Equivalent manual CLI commands, with local paths kept private:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m openpilot.tools.cyber_autotune.empirical_identifiability_execution --input-store "$CAUSAL_STORE" --output-store "$AUDIT_STORE" --source-repo "$RECORDED_SOURCE" --replica repeat-1
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m openpilot.tools.cyber_autotune.empirical_identifiability_execution --input-store "$CAUSAL_STORE" --output-store "$AUDIT_STORE" --source-repo "$RECORDED_SOURCE" --replica repeat-2
    python -m openpilot.tools.cyber_autotune.empirical_identifiability_publication --store "$AUDIT_STORE"

Actual execution used the same entry point inside a raw-access/fitting-API
exception firewall. Source/policy/environment drift or conflicting existing output
bytes fail closed. This generation has no model implementation or extraction path.

Regression command: python tools/test_runner.py openpilot/tools/cyber_autotune/tests
openpilot/selfdrive/controls/tests -j 1. Lateral replay uses the existing
test_cyber_lateral_card_replay and test_cyber_lateral_native_experiment unittest modules.
Independent code and final aggregate reviews both passed after pre-execution
publication-hardening fixes; the minor table-rendering finding was corrected.

## Handoff

Fitting, selection, CV scoring, predictions, residuals, model acceptance, TA/SG execution,
composition, HOLDOUT opening and production/device writes remain NOT_RUN or unauthorized.
Opening count remains zero; FUTURE_UNTOUCHED_HOLDOUT_REQUIRED. The closed simple-model
track, Stage B signal block, TA/SG tradeoff verdicts and all calibration/reference
blockers remain unchanged; sealed reference is NOT_GENERATED.

The next trigger is a separately authorized model-development policy after source
semantics and parameterization questions are resolved. Input rank alone cannot supply
that authorization or remove the closed-loop bias risk.
