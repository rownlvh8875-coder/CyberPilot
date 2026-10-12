# S2-RI rate-independent model design

## Identity and purpose

This additive AutoTune/Validation increment defines S2_RI_V1, a rate-independent
logged-command to measured-steering-angle increment family. It does not fit,
select, predict, score, simulate or authorize a controller.
Baseline: 7d0fa0223888e49dc2e17f002e10e24ef1aabdbf,
branch feature/cyber-autotune. Execution and validation results follow below.
Browser testing is not applicable.

The authoritative overall dataset remains
RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL. Only the exact 154 historical
rlog streams are admitted. The two qlogs remain historical accounting only,
with zero model, target, fitting, selection or CV support. Both routes have
prior numeric exposure and remain a retrospective TRAIN/DEVELOPMENT pool.

## Original references

The immutable source audit binds
[ajouatom/openpilot](https://github.com/ajouatom/openpilot) commit
18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29, its exact source files and license.
empirical-steering-rate-semantics-v1.json records the chain from Hyundai
CarState through the DBC/parser and Float32 carState storage. The new signal
contract pins those source-file hashes without executing upstream code.

SAS11.SAS_Angle is signed 16-bit, little endian, factor 0.1, offset 0 and
declared unit Deg. SAS11.SAS_Speed has an empty DBC unit and no proven signed
physical-rate semantics. Original S1/S2 therefore remain rate-semantics
blocked; S3 remains source-mechanism blocked. Empirical rate correlation
does not establish source units or sign. This work creates a separate
family rather than changing those historical findings.

Existing final-readiness resolution and require_segment protect admission
before arrays. Historical metadata/cache hash readers and the target-independent
direct-SVD helper are reused with their hashes bound. The old generic row
guard and its rate-based feature forms are not used. No new dependency,
upstream integration point, production source change or submodule change
is introduced.

## Changes and expected effect

New empirical_s2_ri modules divide policy, pure grid/history math,
admission, immutable execution, aggregate schema and publication.
Private source arrays are read-only. Derived identities and targets are
stored in a separate explicit external store, with immutable per-array
dtype/shape/order/content/file hashes and per-segment receipts.
Results are committed last; exact resume accepts identical bytes only.

The primary input is carOutput.actuatorsOutput.torque, the logged
post-CarController normalized command. Raw torqueOutputCan verifies
Float32(raw / 409) == normalized but is not a second feature.
Controller request is not a feature or continuity prerequisite.
Publish alignment does not supply a transaction ID or physical EPS
acknowledgement. Command offset means COMMAND_HISTORY_OFFSET_SAMPLES,
not a measured physical actuator delay.

### Source grid and target

The canonical angle representation is signed integer source ticks.
Candidate coordinates are accepted only when finite, within signed16 bounds,
and Float32(code * float64(0.1)) converted to float64 equals the original
cached value exactly. There is no tolerance, silent clipping or acceptance
by rounding alone. Invalid coordinates have an internal sentinel accompanied
by a mandatory validity mask; that sentinel is never admitted as an observation.

The future target is delta_tick[k] = tick[k+1] - tick[k], a measured
0.1-degree source-grid increment per 10 ms sample, not an instantaneous
physical rate measurement. Target availability requires two eligible,
consecutive samples in one S2-RI run and segment. Last rows, gaps and
interventions have no padded target.

The conceptual feature order is intercept, logged normalized command history,
past observed increments with j >= 1, current angle tick and current vEgo.
The target increment at k never enters X. Driver torque is integrity/context,
not a feature. There are no speed interactions, per-bin models or
request/output-difference inputs. The original zero-heavy distribution is
preserved: no jitter, smoothing, interpolation or resampling.

### Additive causal identity

The user explicitly approved a necessary distinction: historical
causal_required_valid, causal_run_id and within_causal_run_index require
rate availability. They are immutable reference evidence, never gates for
S2-RI. Their associated run-boundary and consumed-snapshot arrays are also
excluded from the new numerical dataflow.

EMPIRICAL_S2_RI_CAUSAL_IDENTITY_V1 defines a
FAMILY_SPECIFIC_DERIVED_ADMISSION_IDENTITY, not a correction to the
historical dataset. Its required fields are speed, angle, driver pressed/
torque, gear, temporary/permanent EPS faults, raw/normalized output and
latActive. Neither state.rate nor control.requested availability is required.

The causal layer requires explicit availability, finite values, valid/present/
fresh/no-gap source health, latest-past timestamp identities and source age
at most 20 ms. Repeated state measurements are ineligible; regressing source
clocks are hard failures. Segment/route boundaries and 100 Hz grid gaps split
continuity. Active, pressed and fault context changes split the new runs.
No separately observable reset event exists in this cache; the contract
does not invent one. Available segment, source-gap and context boundaries
are enforced, while source/config/profile drift fails before arrays.

The model layer additionally requires the historical rate-independent
diagnostic mask, exact source-grid angle, active control, no override,
no EPS faults, drive gear and vEgo >= 5 m/s. Excluded rows remain in source
storage and are counted. Reengagement accumulates fresh history.
The all-active and non-rail scopes are both predeclared; neither is selected.

### Fixed structural envelope and future contracts

The permitted envelope is d=0..20, Lu=1..45, Ldelta=1..45.
Only four boundary forms are audited:
(0,1,1), (0,45,45), (20,1,1), (20,45,45).
They require max(d+Lu, Ldelta+1) contiguous eligible samples.
No history, offset, scope or family winner is selected.

Input-only rank uses deterministic population centering/std, constants
separately identified and an unscaled intercept. Direct NumPy SVD uses its
documented default numerical-rank tolerance. This is an audit coordinate
transform, not a fitted training normalizer. Each route and pooled data are
reported separately. Condition numbers have no acceptance cutoff.
Numerical full rank is not symbolic/physical identifiability or predictive
performance proof.

Future route folds invert the two exact opaque route IDs. Future normalizers
must use TRAIN-route statistics only; DEVELOPMENT/HOLDOUT/pooled normalization
is forbidden. A finite fitting candidate set and exact directional acceptance
rule must be separately frozen before performance is seen.

Future metrics are defined but NOT_COMPUTED: delta and next-angle RMSE/MAE/p95,
grid hit and within-one-tick rates, and 0.25/0.5/1/2-second rollout angle
metrics. HOLD_LAST_ANGLE is the sole required comparator. No old ARX/FIR
model is automatically revived. Future continuous delta and source-grid
observation channels are separate. The historical ties-to-even emission
rule is reused as a definition only, with explicit tick-to-degree conversion;
no projection or rollout is executed here.

Closed-loop driving data retain CLOSED_LOOP_IDENTIFICATION_BIAS_RISK.
Future parameters may be empirical predictive parameters only. This work
does not establish causal effects, physical EPS truth, an independent reference,
or solve feedback bias.

## Regression risk and acceptance

Main risks are hidden rate dependencies, tick-unit confusion, off-grid
acceptance, cross-boundary history, future target leakage, qlog disguise and
false complete publication. Tests cover these gates and immutable storage.
The 201-row minimum is inherited support feasibility, not model acceptance.
Ready-for-separate-fitting-policy requires both routes to have support and
all predeclared forms to have full numerical rank, plus exact rate invariance,
source-grid consistency and no model operation.

Independent review identified an auxiliary read-allowlist mismatch and
incomplete derived-proof checks. Both were fixed before the first private
array access: rate reads are separately declared adversarial-only, and every
derived receipt/field/dtype/shape/hash/source association is checked.
The preliminary emission-unit ambiguity was fixed with an explicit
tick-to-degree contract and regression test.

Rollback consists of ceasing use of these additive modules/artifacts.
Historical datasets, roles, verdicts and source policies remain byte-identical.
Future fitting is a new authorization boundary.

## Validation method and actual results

Validation ran in the prepared Ubuntu 24.04 WSL environment with the repository
virtual environment, OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. No Python
source/test files were edited during the full regression.

| Check | Method | Actual result |
| --- | --- | --- |
| Focused S2-RI | pytest test_empirical_s2_ri files | 60 passed, 67 subtests |
| Combined empirical | pytest all empirical test files | 1,233 passed, 216 subtests |
| Full AutoTune + controls | tools/test_runner.py, one worker | 4,007 passed in 1,570.31 s: AutoTune 3,865 + controls 142 |
| Lateral replay | explicit card-replay and native-experiment unittest modules | 16 passed |
| Ruff | repository CyberPilot/AutoTune/controls/replay scope | PASS |
| Syntax | compileall AutoTune and tools/cyberpilot | PASS |
| JSON | parse public change-record JSON files | PASS |
| Publication/privacy/authority | check_publication.py against HEAD and origin/main | zero findings |
| Build | scons -j2 | PASS, targets built |
| Independent review | separate read-only reviewer, tests for findings, full regression after fixes | completed, no unresolved findings |
| Repeatability | two complete private audits; per-segment adversarial identities/X; three SVD repetitions per form | exact PASS |
| Browser, new simulation, shadow, vehicle execution | outside authorized scope | NOT_RUN / NOT_APPLICABLE |

The additive regression receipt binds log hashes without publishing private
paths or logs. GitHub Actions for the committed HEAD is verified separately
after push. Historical tracked inputs have zero modifications.

## Actual immutable data audit

Final design verdict: **S2_RI_MODEL_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY**. This is permission to prepare a separate fitting policy, not model readiness.

Both complete executions matched exact derived array bytes, support, input matrices, singular values, condition numbers and receipts.
The original/deleted/NaN-unavailable/arbitrary-finite rate views and missing-request view preserved the new identities and X bytes.
Each boundary-form rank was independently recomputed three times. Original input file hashes were identical before and after each execution.

Route A: 7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677.
Route B: 962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c.

| Scope | Route A | Route B | Pooled |
| --- | ---: | ---: | ---: |
| Base rlog rows | 415844 | 500691 | 916535 |
| Rate-free source-valid rows | 391181 | 483387 | 874568 |
| S2-RI causal runs | 24854 | 18066 | 42920 |
| All-active model-eligible rows | 382025 | 328030 | 710055 |
| Available source-grid compliant angles | 415837 | 500683 | 916520 |
| All-active eligible | 382025 | 328030 | 710055 |
| All-active target-available | 357997 | 313516 | 671513 |
| Non-rail eligible | 382015 | 327998 | 710013 |
| Non-rail target-available | 357986 | 313481 | 671467 |

All 916,520 available angle observations matched the source grid; 15 missing observations were not filled.
All-active target counts: zero 575,338; positive 48,382; negative 47,793. Only aggregate counts are published.
The eligible count happens to equal the previous generic guard count. This does not establish dependency: the new masks were recomputed independently and adversarially verified.
New run count differs because active/pressed/fault transitions explicitly split the family-specific identity.

| Rail scope | (d, Lu, Ldelta) | Route A windows | Route B windows | Rank / columns, each route and pooled |
| --- | --- | ---: | ---: | --- |
| all | (0, 1, 1) | 336941 | 300569 | 5 / 5 |
| all | (0, 45, 45) | 257518 | 194807 | 93 / 93 |
| all | (20, 1, 1) | 272366 | 221278 | 5 / 5 |
| all | (20, 45, 45) | 250451 | 183711 | 93 / 93 |
| non-rail | (0, 1, 1) | 336929 | 300531 | 5 / 5 |
| non-rail | (0, 45, 45) | 257518 | 194710 | 93 / 93 |
| non-rail | (20, 1, 1) | 272364 | 221210 | 5 / 5 |
| non-rail | (20, 45, 45) | 250451 | 183595 | 93 / 93 |

No scope/form winner, normalizer, model coefficient, prediction, residual or performance score was produced.
Qlog model support and raw-log opens are zero. Dataset completeness remains PARTIAL.

- Audit result SHA: 58546988e7458ce3406c64e015edee0f2c09ec1af681fb99eb62840ece61526c
- Derived identity/target array set SHA: edc4463d90219ff8f3ef330d076d2e33e40ae599c151527002a897accc310849
- Readiness receipt SHA: df79966d0f2daedba0a6e798a91b277ee2325ee9e5e303069e3b4287e695d9b4
- Validation receipt SHA: 8f2d8be144c28bdb9c9192fca3e8e60b64a95b6937f2e501b0c620aa5df0a191

## Handoff

Historical simple-observation track closure, S1/S2/S3 blockers, Stage B block,
TA/SG tradeoff verdicts and composition prohibition remain unchanged.
HOLDOUT is closed with opening count zero. Calibration/reference blockers
remain; sealed reference is NOT_GENERATED. Vehicle remains NOT_READY,
REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED.

The next trigger is a separately approved fitting-policy increment with a
finite candidate set, training-only normalization, recursive-state semantics
and predeclared multi-metric directional gates. This task does not start it.
