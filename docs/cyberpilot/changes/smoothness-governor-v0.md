# Standalone Smoothness Governor V0

SG STANDALONE OFFLINE PROTOTYPE · BASELINE CORE INPUT ONLY · TA-B NOT COMPOSED · NOT VEHICLE QUALIFIED

## Identity and purpose

- Area: Cyber AutoTune / Validation; implemented SG-only development screen.
- Baseline: 53506f2af49ab52490482d3961044f33b7360235, feature/cyber-autotune.
- Selection/config/metric/scenario freeze: 8cdb4476f, before algorithm implementation.
- Implementation/execution source: cc87bde04, before official execution.
- One family, one canonical mechanism, no search, optimizer, frozen evaluation, acceptance or deployment.
- Motivation: TA-B previously showed tracking/smoothness tradeoffs. That historical result is unchanged and is not an input command to SG.
- Goal: attribute normalized-command shaping and descriptive plant cost separately from trajectory authority.

## Original references

Source repository: https://github.com/rownlvh8875-coder/CyberPilot/tree/53506f2af
at the exact baseline above. Existing licenses and attribution remain unchanged.
Relevant pinned opendbc commit: 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.

- candidate_role_contracts.py: exact frozen GovernorCommand/InterventionInput whitelist.
- candidate_architecture.py, candidate_architecture_policy.py, smoothness-governor-contract-v1.json: ownership, roles and reset boundaries.
- trajectory_authority_core.NativeBaseline: direct unchanged native controller, never Core/InnovationPID.
- latcontrol_torque.py, pid.py, opendbc interfaces/vehicle model: existing native conversion, feedback, limits and intervention behavior.
- trajectory_v0_screen.scenarios and PLANT: reuse exogenous 11-scenario inputs and descriptive coefficients only, not TA outputs/results.
- trajectory_v0_metrics: reuse pinned trajectory phase/lag/distance definitions.
- The old architecture governor identity helper is deliberately unused: it reads the historical case index.
- Execution binding records source/support SHA256, CP/profile, baseline identity, native software,
  state/reset/input/output/intervention policies, metrics/scenarios/matrix, environment and timebase.
- Profile is source Hyundai Santa Fe 2022 for reproducible synthetic context, not activation or confirmed vehicle calibration.

## Changes and expected effect

All source and evidence additions are offline-only. Existing architecture/TA contracts, detector,
holdout, calibration, pixel registration, meter diagnostics and V1/V2 evidence remain immutable.

New responsibilities:
- smoothness_v0_policy.py / smoothness_v0_freeze.py: pre-algorithm policy and external receipt pins.
- smoothness_v0_baseline.py: source-only exact NativeBaseline identity pin; TA/arbitrary core identities rejected at SG construction.
- smoothness_governor_v0.py: command-only projection, typed immutable versioned output and experiment-owned intervention audit.
- smoothness_v0_metrics.py: all-sample primary smoothness, event boundaries, tracking cross-objectives and coverage.
- smoothness_v0_screen.py: baseline command generation/freeze, three-arm plant replay, exact repeats and controls.
- smoothness_v0_publication.py: public aggregate/source/receipt validation.
- Five test modules and additive JSON receipts; no production integration point.

### Family selection and canonical configuration

**SG-A UNIT_DELTA_PROJECTOR**:
output[k] = clip(input[k], output[k-1] - 1, output[k-1] + 1) on ordinary samples.
Fresh state passes current input exactly. The sole shaping state is last output.

Radius 1 is the smallest radius whose admissible interval contains zero for every previous
normalized command in [-1,1]. It is a geometric design choice, not a measured actuator slew
rate, inferred dynamics, low-pass time constant or tuned comfort limit. Within the normalized
domain, only sufficiently large opposing commands need projection; same-sign commands pass.

SG-B lacks an independently justified general slew bound. SG-C lacks a justified time
constant and adds persistent lag/tail. SG-D lacks a justified deadband and risks bias.
These alternatives were rejected before results. Small sign chatter passes unchanged.

If previous output is 1 and current input -1, output is 0; a subsequent -1 becomes -1.
For .75 to -.75, the intermediate output is -.25. No extrapolation/authority expansion occurs.
Output lies between previous output and current input, has current-input sign or zero, and
has magnitude no greater than current input. Constant commands reach exact unity.

For a contiguous fresh sequence, triangle inequality gives:
TV(output) + abs(input_final - output_final) <= TV(input).
The implementation checks this with exact rational arithmetic. Nonzero sign reversals
cannot increase. These invariants do not guarantee a lower derivative percentile or spectrum:
splitting a rare rail reversal can increase p95 while reducing peak derivative.

### State, reset, intervention and observability

SG owns only last command. Experiment owns previous intervention/time audit. Plant owns the
sole physical actuator delay queue. SG never sees desired/actual curvature, tracking error,
lane/model/planner/candidate/reference truth, pose or plant state.

- Inactive: input must be exact zero; output zero and SG state cleared.
- Pressed: current input passthrough and state rebase on every pressed sample.
- Release/reengagement: current input passthrough and fresh rebase; no stale pre-event state.
- Experiment/scenario/config boundary: new instance; runtime config mutation rejected.
- Input time/index, active/pressed flags and derived release/reengagement must match frozen
  frames exactly. Unknown fields, subclasses, alternate core identity and gaps fail closed.
- Output receipt validates exact action/reason/reset, before/after state, projection,
  passthrough, normalized bounds and separate saturation semantics.
- CORE_INPUT_SATURATED, GOVERNOR_OUTPUT_SATURATED and GOVERNOR_LIMIT_ACTIVE remain distinct.
  Lower output rail occupancy does not mean the native core saturation was removed.
- Ordinary steps are limited to 1 normalized unit, equivalent to 100 normalized/s at 100Hz.
  Intervention/fresh passthrough is expressly exempt. Primary metrics include those boundaries.
- Unobserved native prelimit/component signals are not fabricated in SG receipts.

### Experiment and metric execution

11 fixed exogenous scenarios, 800 samples at 100Hz each, three arms, two exact repeats:
UPSTREAM_BASELINE / CYBER_CURRENT_ALIAS / SG_V0_CANDIDATE = 66 arm executions.

For each scenario, a direct native baseline operates with its own descriptive plant feedback
to generate commands. That command stream and native state trace are independently repeated,
then immutably saved **before any arm replay**. All three arm plants receive the exact same
pre-governor commands. SG plant feedback is never fed to the core. Baseline/current plant
replay exactly reproduces generation. CURRENT is the same disabled path/config/identity.

This is **frozen native command replay**, not a feedback-stability test of SG plus controller.
Tracking/heading/pose are descriptive counterfactual responses to the frozen command stream.
No command was generated from TA-B, no TA/SG composition ran, and no private input was opened.

Primary derivative is backward difference over every adjacent finite sample, including events.
Eligible active/not-pressed metrics are secondary and disclose gaps/reset masks. Quantiles use
linear interpolation, RMS is separate. Strict adjacent opposite signs count direct crossings;
nonzero reversals remove exact zeros. Spectrum is demeaned Hann, 1.2–50Hz, sum squared rFFT/N².
Event windows are fixed 100 samples with boundary jump and support separately exposed.
Settling requires an exact final constant-input span; otherwise null. Distance queries use
strictly increasing observed forward x and piecewise linear interpolation, without extrapolation.
Full-distance context is separate and never classified by the existing meter envelope.
No performance threshold, weighted score or acceptance rule was invented.

## Regression risk and acceptance

Structural criteria only: finite/bounded causal inputs/outputs, exact reset and repeatability,
identity/role purity, no new sign reversal, no authority expansion, baseline exactness.
Independent review found output-schema and frame/intervention-binding gaps before execution.
Both were reproduced as RED regressions and repaired before the official run.

Remaining risks: derivative redistribution, event passthrough jumps, phase lag, high-speed
tracking loss, baseline synthetic oscillation, and absence of SG feedback-loop stability proof.
Rollback is omission of these offline tools; production code and authority are unchanged.
Composition/search/evaluation/vehicle approval require separate explicit authorization.

## Validation method and actual results

Official command: python -B -X pycache_prefix=<fresh-empty-cache> -m
openpilot.tools.cyber_autotune.smoothness_v0_screen <local-synthetic-output>.
Execution binding was saved before command generation; each command receipt before arm replay.
Source/config/policy identities were checked before/after, with no result-driven changes.

**SG_STANDALONE_STRUCTURAL_PASS / SG_STANDALONE_EFFECT_PRESENT / SG_STANDALONE_TRADEOFF_ONLY**.

- Exact full governor state, pre/post command, applied torque, plant and metric repeats: PASS.
- Straight and low-speed exact no-output-difference; other nine scenarios show plant effects.
- No added sign reversal or authority, no inactive tail, no new output magnitude saturation.
- Requested derivative p95 drops to 100 normalized/s in nine affected scenarios.
- Reversal counts are unchanged in all 11 scenarios; small chatter is not solved.
- Total variation is nonincreasing; it is exactly unchanged in most scenarios.
- The existing baseline medium/high-speed descriptive response is strongly oscillatory and saturated.

| Scenario | Requested derivative p95 baseline→SG (normalized/s) | Output rail occupancy baseline→SG | Curvature tracking p95 baseline→SG (1/m) |
| --- | --- | --- | --- |
| gentle / medium | 117.200757 → 100 | .49625 → .49375 | .0140428845 → .0138256175 |
| sharp | 117.573102 → 100 | .4975 → .49375 | .0140783776 → .0138816909 |
| high speed | 176.350233 → 100 | .70125 → .585 | .0223295032 → .0239535032 |
| driver events | 116.571145 → 100 | .40125 → .3975 | .0140023432 → .0137465518 |

High-speed derivative RMS drops 72.312877→58.818700 normalized/s, but curvature tracking p95
increases. High-speed same-time peak pose difference is **61.276370m in this descriptive replay
plant**, not actual vehicle displacement or lane gain. Driver-event max derivative remains
120.052457 normalized/s because event passthrough is outside the ordinary projection bound.
These counterexamples prevent a blanket smoothness/performance improvement claim.

| Check / stage | Method | Actual result / limitation |
| --- | --- | --- |
| New focused | Five SG unittest modules | 97/97 PASS |
| Lateral replay | Two existing native/card unittest modules | 16/16 PASS |
| AutoTune + controls | Existing full test runner, -j1 | 2387/2387 PASS in 904.44s: AutoTune 2245 + controls 142 |
| Ruff / syntax / whitespace | Full CyberPilot scope / compileall / diff --check | PASS |
| SCons | PATH includes .venv/bin; scons -j2 | PASS |
| Publication/privacy/authority | Existing checker and regression suite | Final publication check: 888 files / 0 findings; privacy 16/16 PASS; authority/history binding PASS |
| Independent review | Separate source/pre-execution and final artifact review | Source, actual artifacts and narrative PASS; 97 tests independently rerun |
| Browser | No UI added or changed | Not applicable |
| Shadow / vehicle | No deployment or live actuation | NOT RUN / NOT AUTHORIZED |
| GitHub Actions | New pushed commit job | Checked separately after push; never inferred from local tests |

## Handoff

Machine-readable recommendation: **COMPOSITION_NOT_RECOMMENDED**, not composition authorization.
Next work, if separately authorized, must address high-speed tracking/phase cost and evaluate a
proper standalone feedback interaction before considering composition. No config was retuned.

TA-B remains TA_STANDALONE_STRUCTURAL_PASS / TA_STANDALONE_TRADEOFF_ONLY.
CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED (37 violations), MIXED_HISTORICAL unchanged.

Reference track remains separate:
CALIBRATION_UNCERTAINTY_PENDING; INDEPENDENT_CALIBRATION_VALIDATION_PENDING;
PIXEL_GEOMETRY_REGISTRATION_PENDING; METRIC_CALIBRATION_UNAVAILABLE;
INDEPENDENT_REFERENCE_UNAVAILABLE. Independent meter result and total physical bound remain null.

Sealed reference NOT_GENERATED.
Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
