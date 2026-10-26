# Frozen Hurdle retrospective fit and CV V1

The frozen Hurdle family completed retrospective fitting and cross-validation,
but none of its 16 structures passed the predeclared acceptance gate. The first
stage classifies whether the next measured source-grid tick changes. The second
stage predicts signed delta only when the predicted gate is MOVE. Evaluation
must protect actual MOVE rows and moving rollout paths as well as the overall
population. These are retrospective development results, with prior exposure to
both routes; they do not qualify a model for a vehicle or an untouched HOLDOUT.

## Scope and provenance

Source: CyberPilot, feature/cyber-autotune,
baseline 15b75a14bad91cb4c04391526318abe0bd9ebf1d, existing repository MIT license.
No external implementation is adapted and no dependency or submodule is changed.
The affected call path is isolated under openpilot/tools/cyber_autotune:
metadata admission → separate authorization → read-only derived fields →
TRAIN fits and threshold → integrated development/rollout → frozen gate →
retrospective selection → immutable private receipts → aggregate publication.

The exact 13 Hurdle policy receipts remain immutable, as do all S2-RI fitting,
reconstruction and attribution evidence. Historical S2-RI remains
S2_RI_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED.

## Predeclared implementation and validation

Python 3.12.13, NumPy 2.5.3, single-thread OpenBLAS/OMP, float64 and no RNG.
The logistic Newton loop checks the gradient after update 100. Line search
tries exponents 0 through 20 and fails immediately on a nonfinite trial.
There is no regularization, damping, alternative solver or tolerance retry.

Stage1 uses all candidate-specific TRAIN anchors. Threshold selection uses
only TRAIN probabilities, strict p > threshold and exact Python-integer
BA_NUM → TN → higher threshold ordering. Stage2 uses true MOVE TRAIN rows
and its own normalizer. DEVELOPMENT is opened only after TRAIN threshold
determination. Coefficient, normalizer and threshold values and per-anchor arrays are not printed or published.

The acceptance contract has exactly 32 clauses per fold: five integrated
one-step metrics, three true-MOVE protections, twelve overall rollout clauses
and twelve PATH_MOVED clauses. Both folds must pass. Oracle Stage2 diagnostics
never enter admission or ranking. Numerically executable horizons continue even
when an earlier gate or diagnostic-definedness check has failed.

Private persistence includes one-step truth, probabilities, gate, predictions,
errors and context, plus complete observed/projected/hold-last paths and gate
paths for every horizon. Receipt and manifest writes are atomic and immutable.
Two independent complete executions must have identical file hashes and
receipts. Verify-only resume traps all numeric loading, fitting, prediction,
projection, rollout, scoring and selection.

Risks: numerical nonconvergence, gate/projection inconsistencies, leakage from
development into threshold selection, future measured steering leakage,
incomplete private attribution inputs and accidental public numeric disclosure.
Synthetic tests, exact policy binding, independent review, two-run byte equality,
input preservation, regression and publication checks address these risks.
Actual run results and validation are recorded below.

## Authority

The fitting executor performs no pooled refit, HOLDOUT file or metadata discovery, raw rlog or qlog opening,
controller integration, TA/SG execution, composition, device writes or vehicle
activation. HOLDOUT remains CLOSED with opening_count = 0. No model is admitted
for future HOLDOUT. Vehicle: NOT_READY, REAL_VEHICLE_UNVERIFIED,
VEHICLE_ACTIVATION_BLOCKED. Closed-loop identification bias and all historical
rate/calibration/reference blockers remain in force.

## Numerical and decision semantics

Stage1 minimizes mean(logaddexp(0, X beta) - y * X beta), with a sign-branch
stable sigmoid. It starts from zero coefficients, uses the mean gradient and
Hessian, and solves H direction = gradient. Full effective rank and at least
201 observations in each TRAIN class are required before Newton execution.
Convergence is max(abs(gradient)) <= 1e-8, with at most 100 accepted updates.
Armijo uses c = 1e-4 and alpha = 0.5**j, j = 0..20. No fallback is permitted.

Threshold candidates are the unique finite TRAIN probabilities plus 0 and 1.
A sorted cumulative confusion sweep exactly reproduces brute-force strict
p > threshold decisions. Selection maximizes TP*N + TN*P with Python integers,
then TN, then the numerical threshold. The threshold number is private.
Development precision is undefined if no MOVE is predicted: that invalidates
the fold while retaining every other numerically executable evaluation.

Stage2 requires at least max(P, 201) true MOVE TRAIN rows, P = 2L+3.
Both normalizers use their own TRAIN population mean and population standard
deviation, with intercept unscaled. Exact constant columns are detected before
division and dropped from the effective coordinate; their nominal coefficients
are zero. Nonconstant zero variance is a numerical failure. Full rank is checked
before and after np.linalg.lstsq(..., rcond=None).

The integrated STATIC branch returns delta 0 and the unchanged current tick.
The MOVE branch calls Stage2 and rounds current + delta directly to the
half-to-even integer source-grid tick. MOVE does not force a minimum tick change.
Continuous one-step error is predicted delta minus observed delta, preserving
the historical float64 operation order. There is no probability-weighted blend.

Recursive steering state consists exclusively of projected integer ticks and
their differences after initialization from measured history. Recorded normalized
post-CarController command and vEgo advance as exogenous inputs. This is
LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT. Observed future ticks and MOVE labels
are used only for scoring. Horizons are 25, 50, 100 and 200 transitions at 100 Hz.
PATH_MOVED means any observed tick in the H+1 path differs from its initial tick.

An admissible candidate passes every frozen clause in both route folds.
Among admissible candidates, selection orders worst PATH_MOVED rollout RMSE
ratio, worst overall rollout RMSE ratio, worst integrated one-step p95 ratio,
total nominal parameter count, L, d and lexical candidate ID. For ratios, 0/0 is
1 and positive/0 is a tagged positive infinity; negative or nonfinite input
metrics invalidate the candidate. Zero admissible candidates produce null
selection and MODEL_SELECTION_FAILED_CLOSED without policy adjustment.

Neither coefficients nor the probability threshold identify physical actuator
parameters or an EPS deadzone. Command means logged normalized post-CarController
command, not measured physical torque. Angle increments are measured source-grid
transitions, not a recovered steering-rate channel. steeringRateDeg and SAS_Speed
are absent from admission, features, targets, normalization, threshold, rollout
and selection. The Hurdle change does not remove closed-loop identification bias.

## Independent review and clean execution provenance

Pre-execution review required preserving integrated evidence on an oracle-only
diagnostic failure, additive repeatability invalidation with null selection,
and exact clause-definition/order validation. All were fixed before the first
actual run. Synthetic tests exercise these failure paths.

A subsequent review identified a report-only constant-column drift issue:
population mean rounding can differ from an exact constant TRAIN value.
The implementation now persists the exact TRAIN reference separately and uses
it only for that diagnostic. Frozen population means/stds and predictive
transformations are unchanged. The regression checks identical constant 0.1,
its adjacent binary64 value, both stage-specific normalizers, and byte-identical
predictions after changing a dropped constant input.

The first partial pair was stopped and preserved, never reused.
Invalidation receipt:
02d40e1ffd6fe46d522ee49d12086f0cd9bef5a8691a7e60b807a914ad66c502.
The next authorization was
aa4780b222147e7bb73e47a5bcd134c1adc8885cdde4748141af6611f21194b0.
That replacement pair was interrupted by Windows host-volume exhaustion.
Neither incomplete pair supplies published selection or repeatability evidence.
The old virtual-filesystem free-space check did not represent host capacity.
Both incomplete stores were losslessly archived, checked against every original
file, and removed from the working volume under separate cleanup authority.
Their archives and incident records remain private; historical input stores
were preserved.

## Lossless storage recovery

The user separately authorized compressed persistence, with no numerical policy
change. Every private array is canonical C-order NPY inside deterministic gzip:
compression level 1, timestamp zero, no embedded filename. Persistence streams
directly to the compressed temporary member; it does not create an uncompressed
temporary copy. An independent decompression verifies the exact original NPY
SHA before atomic publication. Receipts bind dtype, shape, C order, raw array SHA,
decoded NPY SHA, compressed-file SHA and the lossless verification result.
The zlib runtime version is bound in the private environment identity.

The output lives in a separate external store on the host volume with sufficient
capacity. Each write reserves 20 GiB plus the worst-case member size on its output
volume. Windows host-volume checks run independently of WSL virtual free space;
a WSL-backed output also reserves its worst-case member size on the host volume.
A space failure aborts execution without clipping, dropping rows or reusing
partial jobs.

Synthetic tests cover deterministic compressed bytes in independent directories,
dtype/shape/value-byte equality including signed zero, exact canonical NPY bytes,
empty arrays, tampering, object rejection, no overwrite, symlink/traversal
rejection and separate host/output free-space checks. An actual host-filesystem
synthetic smoke test verifies the atomic commit and read path. Independent review
identified the generic WSL-host reservation gap; it was fixed and its regression
passed before the new execution authorization.

A compressed attempt under authorization
c2a08eef99ad5f825fafbac861503d1549a54ff3b508fdd05d84ef4f8d8a7d42
was interrupted when the user required all result storage on drive D. Its partial
outputs were relocated to D and every file SHA verified; that attempt is invalid
and supplies no selection or repeatability evidence. C is no longer a result
location. All 772 authorized source files and 1081 derived files had matched their
frozen hashes before that attempt.

Final storage permits only drive D and the independently verified D-backed WSL
root filesystem. C and other mounted filesystems are rejected before writes.
Historical reconstruction, attribution and fit stores are preserved as verified
lossless archives under the user's separate storage authority. Their original
receipts and payload bytes are unchanged inside the archives; current causal and
derived fitting inputs stay available unchanged. Any final fitting attempt uses
a new output identity and authorization, restarts both full 32-job replicas and
never reuses partial jobs or models.


A D-backed trial under authorization
9b3121f0375ad1923a624af3a605c0290c0072f437fc5d0acfa61765ce8cbe58
also stopped at the host-capacity guard while storage maintenance was still in
progress. It is invalid and archived without reusing partial jobs. Storage
maintenance and verification must finish before the final pair begins.
The three historical fit/reconstruction/attribution stores contain
144,301,389,186 original bytes, preserved in 4,184,679,228 compressed bytes.
Archive extraction hashes and every source-file hash matched before originals
were removed. This is storage representation only, not a change to their
historical receipts or verdicts.

The final independent pair uses authorization
e4eeaca2f891cc9fdb1370b7ae735d963287af6c09cca85dc689c8e9c560c6ea
and direct drive-D compressed storage. A real filesystem smoke test verified
atomic compressed persistence and exact decoding before authorization. All 772
source and 1081 derived file hashes were checked again before either replica.

Storage-maintenance scope exception: an initial broad directory-size inventory
included protected-directory names and aggregate sizes. No protected content or
numeric arrays were opened, used, archived or modified. Subsequent maintenance
used explicit path allowlists. The executor's zero HOLDOUT-discovery counter is
limited to fitting/CV execution; it is not a task-wide claim that maintenance
never encountered protected metadata. HOLDOUT data opening count remains zero.

## Actual retrospective outcome

All 16 structures completed both route folds in each of two independent runs. All 32 jobs are EXECUTED_COMPLETE, with no precondition, numerical, support or diagnostic-definedness failure. No fold passed all acceptance clauses. The admissible count is 0 and selected_candidate is null: HURDLE_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED.

In plain language, separating the movement decision from the delta prediction did not produce an admissible model. The integrated predictions protected true MOVE rows under all three frozen metrics, but every candidate-fold lost exact next-tick hits on the complete population. Several long-horizon tests also failed. These observations do not authorize threshold changes, alternative fitting or a relaxed gate.

TRAIN populations span 183,711–336,941 anchors, including 157,814–288,710 STATIC and 25,897–48,231 MOVE anchors. Development populations have the same ranges under the reversed route folds. Stage2 used exactly its TRAIN MOVE subset. Every Stage1 and Stage2 effective design had full rank, with separate normalizer receipts. All 32 logistic models converged after exactly 5 accepted updates; final maximum absolute gradients span 4.9141382695530806e-14–4.4458397828045203e-13.

TRAIN threshold searches contained 183,713–336,889 unique boundary candidates. Actual threshold values remain private. TRAIN confusion counts across jobs span TP 5,931–26,208; TN 145,469–244,418; FP 11,010–117,808; FN 19,966–36,373. These are ranges across different candidate-specific populations, not pooled confusion counts.

Development Stage1 diagnostics (ranges across all 32 jobs):

| Diagnostic | Range |
|---|---:|
| false_move_rate | 0.0187247–0.557334 |
| missed_move_rate | 0.344026–0.926023 |
| precision | 0.163427–0.435183 |
| recall | 0.0739773–0.655974 |
| specificity | 0.442666–0.981275 |
| balanced_accuracy | 0.527626–0.563501 |

STATIC diagnostics distinguish predicted gate movement from projected tick movement; a MOVE gate does not force a tick change. All per-job aggregate diagnostics are published in the results artifact. Stage2 oracle diagnostics are shown below only to describe the conditional regressor; they were not used for admission, ranking or selection.

| True-MOVE oracle diagnostic | Range |
|---|---:|
| rmse | 0.928011–1.5588 |
| mae | 0.753209–1.1647 |
| p95 | 1.80403–2.86889 |
| sign_accuracy | 0.661822–0.853953 |
| exact_hit | 0.183387–0.380818 |
| within_one_tick | 0.736762–0.911841 |

Frozen gate failures, out of 32 jobs (0 means every job satisfied the clause):

| Population | RMSE | MAE | p95 | Exact hit | Within one tick |
|---|---:|---:|---:|---:|---:|
| Integrated one-step ALL | 4 | 20 | 16 | 32 | 8 |
| Integrated true MOVE | 0 | 0 | 0 | — | — |
| Overall rollout 25 | 15 | 23 | 21 | — | — |
| PATH_MOVED rollout 25 | 14 | 23 | 21 | — | — |
| Overall rollout 50 | 16 | 22 | 24 | — | — |
| PATH_MOVED rollout 50 | 16 | 22 | 23 | — | — |
| Overall rollout 100 | 20 | 23 | 25 | — | — |
| PATH_MOVED rollout 100 | 19 | 23 | 25 | — | — |
| Overall rollout 200 | 21 | 22 | 18 | — | — |
| PATH_MOVED rollout 200 | 21 | 22 | 17 | — | — |

All four horizons were evaluated for every job despite earlier gate failures. Overall rollout support ranges are 174,252–268,108 (25), 167,526–255,466 (50), 157,408–240,329 (100), and 143,260–219,711 (200). PATH_MOVED ranges are 117,224–187,822; 137,229–218,264; 147,470–230,669; and 141,142–218,761 respectively. Every population exceeds the frozen support minimum. Candidate and comparator anchor SHAs match throughout.

The machine-readable results retain each candidate/fold metric, population count, model/normalizer/threshold receipt and all 32 clause decisions. No inadmissible candidate is ranked, and no oracle or pooled score overrides a failed fold. Historical S2-RI remains NO_ADMISSIBLE independently of this new family result.


## Exact repeatability and validation

Both independent full runs produced manifest
c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6.
All 5,250 files per replica matched, including compressed array bytes, model and
normalizer coefficients, private thresholds, probabilities, full paths, gates,
receipts and null selection. HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS is bound by
receipt 3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b.

Verify-only resume returned the same manifest while derived loading, both fits,
threshold computation, prediction, projection, rollout, scoring and selection
were hard-trapped. Source, derived and public policy file hashes matched before
and after actual execution. No byte-identity claim is made for unopened raw/qlog
stores. All result data remains compressed on drive D.

Validation on the final executor source: 63 focused tests and 65 subtests;
1,578 combined empirical tests and 450 subtests; 4,437 full AutoTune/controls
tests; 16 lateral replay tests. All passed. Ruff, compileall and SCons passed.
Independent source/storage review and final aggregate/document review found no
remaining actionable issue. The final publication/authority audit is recorded
in empirical-hurdle-fit-cv-validation-v1.json. Exact commit CI is checked after
push, separately from this pre-commit local validation evidence.

No further model design, pooled refit, HOLDOUT work or vehicle integration is
authorized by completion of this increment.
