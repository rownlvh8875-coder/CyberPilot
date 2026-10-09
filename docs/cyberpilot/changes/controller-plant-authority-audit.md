# Controller-to-plant authority audit

## Identity and purpose

Validation/UI; IMPLEMENTED, offline audit complete, independent review PASS.
Baseline branch feature/cyber-autotune at
598bd022ae2ccb49662ab7a164120b822681736c. This additive experiment explains
small historical candidate displacement without changing candidates, detector,
holdout, calibration, mapping or meter evidence.

DESCRIPTIVE PLANT ONLY. NOT REAL VEHICLE DYNAMICS. NOT CANDIDATE ACCEPTANCE.
CURRENT remains an exact BASELINE alias. V1 remains TRADEOFF_ONLY.
V2 remains REJECTED with all 37 historical metric/cell violations.
No new candidate, tuning, search, acceptance threshold or production integration.

## Original references

The audited source is the repository's existing synthetic offline chain:
[CyberPilot snapshot](https://github.com/rownlvh8875-coder/CyberPilot/tree/598bd022ae2ccb49662ab7a164120b822681736c).
Exact file SHA256 identities are in the frozen execution policy; each machine
signal-chain row binds its source SHA. Original source/license attribution is
preserved; no upstream implementation was replaced.

Native historical heads are 67cbf2a642872f8ea6ecd534b4c1a3216cfbb18e
and 3da4306c118e6953e8bb6851b9385736743cf45d. The existing recovery index binds
70 immutable case receipts, inputs, controller/configuration/reset/environment
identities and original result hashes. This audit revalidated all 70 receipts,
without rerunning a native controller. Signal decomposition uses the 11
historical EVALUATION scenarios; DEVELOPMENT/STRESS retain separate historical
identities, with no new selection or verdict.

opendbc source is pinned at 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
The controller uses the linear conversion from opendbc/car/interfaces.py.
The offline worker does not run Hyundai's carcontroller or CAN transport.

## Changes and expected effect

New controller_plant_authority.py provides finite scalar, signal integral,
observed-X query and circular-arc math. controller_plant_experiment.py exercises
the unchanged original plant and original plant_trace. controller_plant_evidence.py
revalidates old receipts and executes the separately frozen diagnostic matrix.
controller_plant_findings.py adds source-chain interpretation with evidence and
counterevidence. controller_plant_policy.py pins the complete execution policy.
controller_plant_publication.py only accepts six exact published receipts,
including nested content; resealed edits are rejected. The additive
controller_plant_visualizer.py extends existing loopback UI without editing it.

| Stage | Units, sign and scaling | Timing, clipping and reset |
| --- | --- | --- |
| Desired curvature | controller 1/m; lateral acceleration k*v² | frozen scenario, 100 Hz |
| LatControlTorque internals | acceleration-space PID, current future FF, roll*g, offset and factor-scaled friction | 0.15 s desired-reference alignment; not a second physical queue |
| Requested torque | normalized [-1,1]; returned negative acceleration-space output/factor | PID acceleration limits ±factor; fresh native controller per arm |
| Hyundai raw command | outside this harness; round(384*u), then driver/rate limits | raw3/7 counts per100 Hz, not plant amplitude or a symmetric generic limiter |
| Plant command/application | command=-requested; applied normalized=-delayed command | sole physical queue2 steps=0.02 s; out-of-domain rejected, no silent clip |
| Curvature | k[n]=.92*k[n-1]+g(v)*command[n-2]+.001*roll, g=.004+.0002*v+.002/v | discrete AR coefficients; no extra dt multiplication |
| Yaw | -k[n]*v+.75*(yaw[n-1]+k[n-1]*v) | filters yaw-target RESIDUAL, not ordinary yaw lag |
| Heading | rad; heading+=next_yaw*.01 | post-step update |
| Pose | m; x+=v*cos(updated heading)*.01; y+=v*sin(updated heading)*.01 | post-step state with frame-start timestamp label |

Controller/plant curvature is the negative of geometric circular-arc curvature.
Positive requested normalized torque drives negative plant curvature, positive
geometric yaw and positive pose-y in the flat zero-reset direct control.
The VehicleModel steering-angle degree/radian conversions only reconstruct
feedback; wheelbase/steering ratio are not multiplied into plant curvature again.

All arm queues, curvature, yaw, heading and pose reset independently. Native
buffers/PID start from new controller instances. The worker does not call the
stock inactive reset of the saturation timer. In this pinned controller that
omission affects saturation bookkeeping, not the torque/pose update. This is
an explicit historical scope limitation, not a retroactive correction.

## Actual findings

PLANT_AUTHORITY_CONFIRMED; combined attribution MIXED_OR_UNRESOLVED.
A single cause or a new arbitrary minimum-effect threshold is not justified.

| Question | Evidence and limitation |
| --- | --- |
| A: outputs nearly identical? | Scenario-dependent. Pooled nominal absolute requested delta p50=8.546167e-8, p95=.0032827748, max=.39277725 normalized. Four V2 high-speed scenarios are exact output aliases, while other transient peaks are appreciable. A whole-run peak is not an early-distance mean. |
| B: plant too weak? | Not supported. Direct positive controls and independent recurrence agree. DC curvature gain magnitudes at5/17.5/25m/s are .0675/.09517857/.1135 per normalized command. These are descriptive, not physical gains. |
| C: scale/sign/dt bug? | No defect found in the pinned descriptive chain. Actual original pose integration agrees with signed circular geometry within the analytic discrete bound. Missing384, double dt and degree/radian defects were not found. Raw actuator dynamics remain outside scope. |
| D: cancellation/filtering? | Scenario-dependent. Pose-increment signed/L1 cancellation ranges .009019–.830677 among nonzero V1/V2 scenarios. Torque sign changes reach79. Nominal delay-aligned requested/applied delta residual is exactly0 in all33 comparisons. AR .92 has Nyquist/DC magnitude ratio1/24 and pole time constant .11993s. No cancellation ratio is a probability or acceptance score. |
| E: query horizon? | Yes, it limits early effect context. Major V1 torque peaks occur at baseline observed X about44.5,53.3,63.2,73.6,74.7 and88.5m. Frozen5–30m effects stay unchanged below the envelope. Later35/40/common-maximum queries have no meter-resolution classification. |
| F: smoothness only? | Not proven. Oscillation/derivative differences coexist with nonzero pose effects and historical tracking regressions. “Pure smoothness-only” would overstate the evidence. |

The descriptive DC acceleration-equivalent gains at5/17.5/25m/s are
1.6875/29.1484375/70.9375 m/s² per normalized command, whereas the native linear
controller conversion factor is4. This mismatch is an uncalibrated plant-design
limitation, not a missing384 unit defect or a real vehicle authority estimate.
Strong descriptive feedback can coexist with tiny candidate output differences.
Native requested torque also reaches exact ±1 in167–275 frames in six V1
nominal cases (counts remain per-case in the stage ledger). This is controller
output limiting, not extra plant clipping. Historical receipts do not retain
the pre-limit PID output, so the amount of internal difference erased by native
limiting cannot be reconstructed; no such delta is invented.

The new same-time peak pose delta is about1.98484cm. The previous distance-aligned
whole-phase maximum remains about1.98636cm, unchanged. Different alignment bases
explain the small difference; neither metric replaces the historical one or
overturns rejection.

## Frozen controls and analytic consistency

Execution policy receipt:
fe4642a3dc0551110d2d9d110ff31513c5586477ef1d076bba01c493ec7dc681.

48 controls: speeds5/17.5/25m/s, 401 steps at.01s, STEP and full-duration RAMP,
both signs, amplitudes0 plus the exact historical delta p50/p95/max above.
No results-based amplitude selection. Sustained max-delta controls are diagnostic
stress inputs, not the historical candidate waveform. Zero controls reproduce
exact zero; all controls repeat byte-for-byte and all independent convolution
checks pass. Maximum recurrence discrepancy is1.554312e-15.

At fixed speed/zero reset the independently evaluated recurrence is
k[n]=-g*sum(a^(n-delay-j)*u[j]); yaw=-v*k[n].
Nine additional oracles seed the ORIGINAL plant_trace at constant steady
curvature for zero/left/right curves and all three speeds. The comparison uses
heading=k_geometric*s, x=sin(k_geometric*s)/k_geometric,
y=2*sin(k_geometric*s/2)²/k_geometric, with the straight limit.
The numerical bound is |k|*v²*T*dt/2 plus explicit floating roundoff, derived
from right-end Riemann integration. Maximum position residual about.012526m
is within its .01253125m discrete bound at the longest100.25m control.
This numerical integrator bound is not a physical measurement uncertainty.

288 control/distance queries:216 AVAILABLE,36 DISTANCE_NOT_REACHED,
36 UNCOMPARABLE_COORDINATE_BASIS. Large sustained inputs can turn beyond90°
and reverse forward X, so their nonmonotone trajectories are explicitly
uncomparable under the frozen forward-X interpolation basis. No extrapolation,
clipping, fallback or zero-filled unavailable samples.

Stage ledgers retain signed and absolute integrals, derivatives, sign changes,
delay tail, saturation occupancy and per-phase statistics. Cross-unit norm
ratios retain their units and are not causal dimensionless attenuation.
Exact zero denominators produce null; no arbitrary epsilon replaces them.
For tiny nonzero denominators the actual input/output L1 magnitudes remain
in the linked signal rows; a finite quotient makes no numerical-stability or
causal claim. There is no invented near-zero cutoff.
Disjoint phase values have no invented cross-gap derivative/sign adjacency.
Finite-amplitude pose sensitivity is labeled a secant, not a local physical
derivative.

## Regression risk and acceptance

Historical detector, holdout annotations, pixel/conditional-meter results,
candidate configuration and verdicts are untouched. New source and exact
receipt pins reject stale or coordinated resealed inputs. Publication accepts
only aggregate synthetic signals, never raw private data. Recovery files are
read-only. New receipts use atomic immutable writing; corrected experiments
cannot overwrite historical artifacts. Source-review draft runs remain local
and are not published as accepted results.

No physical/performance acceptance threshold was created. Risks include the
descriptive plant's physical mismatch, omitted raw actuator stage, timestamp
semantics, saturation-reset scope and nonmonotone query availability.
Rollback is removal of this additive audit only, retaining the last verified
historical configuration. Independent code review is required for software;
no vehicle promotion is authorized.

## Validation method and actual results

Runtime: Python3.12.13, x86_64, existing locked environment; same original plant
bytes and frozen reset. Main audit396994f4..., stage3f667f34...,
controls1500bb52..., findingsc0fde89e..., readiness7eb14c1a....
All full identities are in the committed JSON artifacts.

| Check | Actual method and result |
| --- | --- |
| New focused tests | 71 PASS, including mutation controls and original-integration defect injection |
| Full AutoTune / controls | tools/test_runner.py -j1:2102 PASS in875.44s (AutoTune1960 + controls142) |
| Lateral replay | Python unittest, both focused modules:16 PASS |
| Ruff / syntax | Full CyberPilot scoped Ruff and compileall PASS |
| Publication / privacy / authority | Staged publication_check:824 files/0 findings; publication regressions28 PASS; exact schema and no-authority-call tests PASS |
| SCons | PATH includes .venv/bin; .venv/bin/scons -j2 PASS |
| Actual browser | Chrome154 desktop/mobile,11 scenarios×7 signals,48 controls,9 oracles; no JS errors/external requests/failed resources; clean shutdown PASS |
| Independent review | PASS; regenerated complete controls exactly equal published receipt; no Important/Critical findings |
| Real vehicle / shadow | NOT RUN; not authorized |

## Handoff

Next work is not finer parameter search. Review controller-family architecture
and descriptive plant applicability in a separately declared experiment.
Do not select V3 or change existing thresholds from this audit.

REFERENCE_CALIBRATION_TRACK continues in parallel:
CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE,
INDEPENDENT_REFERENCE_UNAVAILABLE. Physical height1.385m uncertainty remains
pending; orientation remains model-derived. No new private access.

sealed reference NOT_GENERATED. Vehicle NOT_READY,
REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.

Run the additive local UI:
.venv/bin/python -m openpilot.tools.cyber_autotune.controller_plant_visualizer
then open its printed127.0.0.1 URL at /plant-authority.
No CDN, remote assets, telemetry, Params mutation, CAN output or device writes.
