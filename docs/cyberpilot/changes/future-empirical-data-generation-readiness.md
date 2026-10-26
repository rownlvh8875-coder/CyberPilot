# Future empirical data generation readiness

## Identity and purpose

Cyber Validation / AutoTune, branch feature/cyber-autotune, baseline
46e41ad2f2e11cd4aee926b47d037c46d226108c. This increment implements future
metadata admission, immutable whole-route roles, enriched causal-row contracts,
synthetic eligibility checks and a closed future HOLDOUT contract. The readiness
scope is contracts and synthetic validation. It does not include a raw log
extractor, an empirical model or a HOLDOUT opener.

The finalized source-grid result remains SOURCE_GRID_OBSERVATION_REJECTED
(1/6 strict scopes passed). CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED
covers ARX1/FIR25, their declared delays, single-condition selectors and fixed
source-grid emission. It makes no claim about every actuator model. Historical
V1/V2/V3 evidence, attribution, causal recovery and source-grid artifacts remain
byte-identical. No old route is reanalysed.

## Original references

Source: [CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot),
feature/cyber-autotune at the exact baseline above; inherited MIT license and
submodule attribution remain unchanged. The authoritative inputs are the public,
receipt-pinned empirical-causal-context-schema-v1.json,
empirical-source-signal-matrix-v1.json, source equivalence/fingerprint/route
reclassification artifacts, cross-root metadata inventory and source-grid
readiness. Their existing exact public-source provenance remains authoritative;
this increment does not repeat that audit or infer current carrot-wip equivalence.

The known scoped equivalence class contains only its exact audited commits,
fingerprints and adapters. Full CarParams and empirical profile must match the
admitted profile. An unknown exact source remains SOURCE_AUDIT_PENDING; a wrong
adapter needs SOURCE_ADAPTER_REQUIRED; incompatible vehicle/control/dirty source
is SOURCE_INCOMPATIBLE. New source audit templates require logger/schema,
command path, CarState/DBC, sensor producer units/axes/clocks, runtime STEER_MAX,
profile and reviewed scoped equivalence before future numeric opening.

No submodule, native controller, model asset, dependency or upstream interface
changes are required. The existing eligibility support function is reused
without modifying it.

## Changes and expected effect

Seven additive public JSON contracts bind the finalized closure, context V1,
source matrix, existing source identities, executor hashes, route policy and
unchanged calibration blockers. They publish zero admitted routes and null
numeric coverage. The modules have these responsibilities:

- future_empirical_contracts.py defines versioned policies and the nonexecuting
  model shortlist.
- future_empirical_admission.py validates sealed metadata/history receipts,
  distinctness, source/profile compatibility and immutable roles.
- future_empirical_context.py validates synthetic future causal rows and routes
  them through the frozen eligibility support accounting.
- future_empirical_cli.py provides explicit manual metadata commands.
- future_empirical_publication.py verifies the seven exact public contracts and
  their historical source-grid chain.

The future private causal schema preserves opaque route/segment/run/design-row
identity, requested and post-controller torque, raw command and runtime scale,
command/angle history, actual steeringRateDeg sample, driver/EPS context, speed,
wheel speeds, gear, active/intervention/mask/boundary context, raw yaw, direct
gyro source/xyz, source-proven lateral acceleration and acquisition/publish/state/
command/control/grid clocks. Missing values remain null, never fabricated false
or zero. Unknown safety/curvature limits remain unknown.

The source observation is SAS11.SAS_Angle at 0.1 steering-wheel degree, Float32.
Steering-rate schema values must be preserved as actual samples; physical unit
review remains explicit. ESP12 yaw retains its empty DBC unit limitation.
Device-axis gyro is not promoted to calibrated vehicle yaw. Optional sensor
fields unavailable from an exact source adapter remain null.

Rows must use an exact source-specific adapter and role receipt. Targets,
future values, model/planner/lane/fused pose, detector/human references and
candidate result labels are forbidden. At the 100 Hz integer grid, command and
control clocks cannot exceed state time, state cannot exceed grid time and the
prediction target time must be strictly later. Maximum source age is 20 ms;
there is no gap interpolation. Reused source clocks require unchanged source
values; regressions, reordered/duplicate rows and scope reentry are rejected.
History cannot cross route, segment or run. Explicit or unknown gap/intervention
boundaries and unknown masks break valid support. LOW is 5–15 m/s, MEDIUM
15–25 m/s, HIGH at least 25 m/s; support minimum remains 201.

### Metadata admission and roles

Before its first write, the command verifies the full published historical
pin chain and all seven exact future contracts. A locally changed and resealed
source artifact is rejected even for a fresh store. The command then consumes
an operator-provided sealed source-specific metadata receipt. It never traverses the raw root. Only the two previously approved
storage-root aliases are accepted. Directory/date names do not establish
identity. New-route admission receipt binds exact source, OS, fingerprint, full CarParams,
empirical profile, logger-start hash, complete segment lineage, adapter, message
envelopes and prior-analysis/numeric-open state.

Distinctness requires the full historical metadata registry. Each old logger
identity preimage must match its published identity hash; old segment hashes
must match the separately pinned, immutable private metadata inventory. Equal
logger identity or any overlapping segment rejects renamed/copied/appended
routes. No historical inventory was opened during this increment; the workflow
accepts this already-sealed metadata proof when an operator later supplies it.

Required Stage A fields must be source-schema AVAILABLE and required message
envelopes present. This proves metadata readiness, not numeric coverage or an
actual command bridge. Unknown presence stays pending. Prior analysis must be
NONE and numeric-open state explicitly false. Existing old routes cannot become
future HOLDOUT.

At least three complete compatible distinct routes are required: one TRAIN,
one DEVELOPMENT, one HOLDOUT. Five or more are preferred; five gives 3/1/1.
Canonical opaque-route lexical ordering and floor 60/20/remaining allocation
with at least one each are deterministic. Whole routes are assigned once.
Segments/time blocks cannot create fake independent routes. Receipts use the
existing atomic no-overwrite persistence; exact resume is permitted, changed
roles are rejected.

### Closed HOLDOUT contract

The default is CLOSED. Future admission requires a new distinct logger identity,
complete lineage, exact compatible source/profile/adapter, no prior analysis,
previously unopened numeric payload, role fixed before inspection and required
signals. A model family/config/model/metric/support freeze must precede a
separate authorized one-time opening receipt. Unknown requirements do not pass.
No refit, reselection, threshold or family change is permitted after opening.

This increment has no opener. The planning function remains
CLOSED_MISSING_ADMISSIBLE_MODEL without a model, or
CLOSED_FUTURE_AUTHORIZATION_REQUIRED with a synthetic freeze proof.
The historical package stays CLOSED_MISSING_ADMISSIBLE_MODEL.
HOLDOUT_OPENING_CLOSED and FUTURE_UNTOUCHED_HOLDOUT_REQUIRED remain in effect.

### Local manual workflow

Set PRIVATE_ROOT to an exact approved alias and PRIVATE_STORE to a new private
store outside the repository and raw roots. Explicitly supply sealed JSON
metadata/history receipts inside that store. No default discovery, parent-disk
crawl, background watcher or scheduled automation exists.

    python -m openpilot.tools.cyber_autotune.future_empirical_cli source-template --private-root "$PRIVATE_ROOT" --private-store "$PRIVATE_STORE" --source-commit "$EXACT_COMMIT"
    python -m openpilot.tools.cyber_autotune.future_empirical_cli inventory --private-root "$PRIVATE_ROOT" --private-store "$PRIVATE_STORE" --metadata-receipt "$METADATA_RECEIPT" --history-metadata "$HISTORY_RECEIPT"
    python -m openpilot.tools.cyber_autotune.future_empirical_cli assign --private-root "$PRIVATE_ROOT" --private-store "$PRIVATE_STORE"
    python -m openpilot.tools.cyber_autotune.future_empirical_cli inspect --private-root "$PRIVATE_ROOT" --private-store "$PRIVATE_STORE"

Inventory is metadata-only; assign seals roles before any future numeric
inspection. The extract command deliberately rejects execution. A future
source-specific extractor and separate numeric authorization are still needed.
The eligibility facade reports schema field presence and synthetic support;
actual speed/active/no-override numeric potential is null until separately
authorized data exists. It cannot fit a model.

### Safe passive collection and nonexecuting shortlist

Prefer ordinary legal commuting or daily driving, with traffic and safety
taking priority. Do not perform artificial abrupt steering, S-shaped maneuvers
or performance tests. Naturally occurring straight roads and gentle left/right
curves are useful. Different dates/roads and naturally available low/medium/
highway speeds are preferable to one short repeated route. Normal lateral-active
sections with little driver override can be useful. Never drive dangerously for
data, and do not collect a route merely to satisfy a maneuver.

S1 is a second-order latent angle/rate state-space idea; S2 is a causal delta-angle
idea using command history, measured rate and speed; S3 is a bounded
piecewise-affine idea contingent on source-defined deadzone/hysteresis evidence.
The shortlist records required fields, state/reset obligations, symbolic
parameter-count scope, failure modes, fitting complexity and holdout risks.
No family, parameter count, algorithm, threshold, fitting method or reset
implementation is selected. No neural model is introduced.

## Regression risk and acceptance

Risks include forged or stale source proofs, renamed/appended routes, role
reassignment, unknown-to-false substitution, clock age/order mistakes and
mistaking contract readiness for model readiness. Acceptance requires synthetic
fail-closed tests, exact public pin checks, independent review and unchanged
historical files. No empirical performance threshold is added.

Rollback consists of removing this additive future-only workflow. There is no
production integration or active configuration to roll back. Source/profile
changes require a fresh audit and versioned adapter; they do not silently
extend the known class. No private paths, raw metadata blobs, signal traces,
coefficients, images, GPS or timestamps are published.

## Validation method and actual results

Prepared Ubuntu 24.04 WSL environment, Python 3.12.13, unchanged pinned
submodules. All new data fixtures are synthetic; raw/numeric readers are forced
to fail in firewall tests.

| Check | Method | Actual result |
| --- | --- | --- |
| Focused | unittest test_future_empirical_data and test_future_empirical_publication | 85 PASS |
| Combined empirical | Existing empirical suites plus the new suites | 826 PASS (81.695 s) |
| Full AutoTune | tools/test_runner.py, single worker | 3,195 PASS (975.99 s); source before/after hashes exact |
| Controls / lateral replay | Existing controls and explicit lateral replay suites | 142 / 16 PASS |
| Ruff / syntax / publication / authority / diff | CI-equivalent Ruff scopes; compileall; check_publication --base origin/main; seven-contract firewall; git diff --check | PASS; zero publication findings; 346 valid JSON documents; only new files |
| Native build | Activated prepared venv, scons -u -j 4 | PASS |
| Independent review | Separate reviewer; synthetic fixtures and public source only | Final PASS, including fresh-store pin verification |
| Browser | No UI added | NOT_RUN_NO_UI_CHANGE |
| Real replay / simulation / shadow / model / holdout | Outside authorization | NOT_RUN |

Review regressions cover path traversal/symlinks, historical segment proof
binding, clock regression/reused sample semantics, gap/intervention support
breaks, interleaved scope reentry and resealed source-proof startup rejection.
The first full AutoTune run was interrupted to add this startup integrity fix;
final results below refer to the complete run on the corrected, fixed source.

## Handoff

New readiness is FUTURE_EMPIRICAL_DATA_PIPELINE_READY,
EMPIRICAL_CAUSAL_CONTEXT_V2_DEFINED, FUTURE_ROUTE_ADMISSION_READY and
FUTURE_HOLDOUT_CONTRACT_READY, scoped to contracts and synthetic validation.
NO_NEW_ROUTE_ADMITTED, NO_NUMERIC_EXTRACTION, NO_MODEL_FITTING and
NO_MODEL_SELECTED remain explicit.

Stage B remains STAGE_B_SIGNAL_ADMISSION_BLOCKED. TA-B remains
TA_STANDALONE_TRADEOFF_ONLY and SG-A remains SG_CLOSED_LOOP_TRADEOFF_ONLY.
Composition is NOT_RECOMMENDED / NOT_AUTHORIZED; candidate search and frozen
evaluation remain NOT_AUTHORIZED. All calibration/reference blockers remain
unchanged; sealed reference is NOT_GENERATED. Vehicle remains NOT_READY,
REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED.

The next trigger is a genuinely new complete route with exact source/profile
audit, distinctness proof and an immutable role assignment before numeric
inspection. Actual extraction/model development requires separate authorization.
No vehicle application is authorized.
