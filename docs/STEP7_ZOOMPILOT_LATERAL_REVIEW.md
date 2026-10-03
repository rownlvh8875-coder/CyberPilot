# STEP 7 ZoomPilot Lateral Review

## Status and fixed identities

This review extends the existing STEP 7 DISABLED/OBSERVE_ONLY implementation. It does not replace the STEP 6 architecture, change the native controller output, or qualify active lateral control.

- CyberPilot fixed base: `19062e9b0bfc98a132e0fd8a2e2e540fe8fdeeeb`
- Local continuation branch: `feature/cyber-lateral`
- Offline optimizer orchestration commit: `ea98cdf5369b72cee2eb48e8dce86f632fd623f6`
- Offline command-domain adapter commit: `b1901e7dcae69a845c9995bc45c9b7a0ddc36c9e`
- Remote `feature/cyber-lateral` observed at: `c8fb906815530460ed156f14e09e1f312bb0f851`
- ZoomPilot `develop`: `32252d207dddce2755a1fc9174a92c2e3c943739`
- ZoomPilot opendbc `develop`: `cf894611bfdde26e8e4eef28169216cbad2f1648`
- CarrotPilot `carrot-wip`: `abe1a232d81fd5b0f8db4b7212587952514e0274`
- Sunnypilot `master`: `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56`

No holdout route was opened for this review. No Mazda constant or code was copied into the CyberPilot implementation.

## 1. Current lateral data flow

```text
camera/model
  -> modeld path and desired curvature
  -> controlsd curvature selection and clip_curvature
  -> one CarParams-selected upstream lateral controller
  -> normalized steer request
  -> Hyundai CarController rate/driver/torque constraints
  -> panda/opendbc safety
  -> EPS

post-publication diagnostic branch only:
  -> CyberLateralCoordinator
  -> immutable observations and offline metrics
  -> no actuator, Params, CAN, or safety write path
```

The recorded development vehicle resolves to `HYUNDAI_SANTA_FE_2022` with torque control. The recorded `steerActuatorDelay` is 0.1 s and `steerLimitTimer` is 0.4 s. Two controller contracts must not be conflated:

- recorded Carrot source `5a970f1a`: route-start Params and source resolve to STEER_MAX 409, DELTA_UP 3 and DELTA_DOWN 7;
- fixed Cyber candidate source: STEER_MAX 384, DELTA_UP 3 and DELTA_DOWN 7.

All 6,004 recorded `carOutput` samples satisfy `torque == torqueOutputCan / 409` after float serialization tolerance. Only 1,507 happen to round to the same raw value under 384, so direct normalized-output reuse for A3 is prohibited. Any A3 replay adapter must start from recorded `torqueOutputCan` and normalize with the candidate's 384 contract. Neither set of limits was changed.

## 2. Architecture comparison

| Project | Planning/path | Controller and tuning | Vehicle output boundary |
| --- | --- | --- | --- |
| OpenPilot | model path and desired curvature | CarParams-selected torque/PID/angle/curvature controller | brand CarController followed by panda/opendbc safety |
| Sunnypilot | upstream-compatible extensions | optional controller features including future-jerk concepts | existing vehicle and safety constraints retained |
| CarrotPilot | custom lane/model blending and runtime path offsets | runtime factor/friction/gain and jerk extensions | fork-specific vehicle integration |
| CyberPilot current | upstream OpenPilot path unchanged | native controller exactly once; observer runs after output | no Cyber actuator authority |
| ZoomPilot | upstream-derived path | Mazda speed-bin learning, torque ceiling and rate-limit state handling | Mazda EPS-specific ceiling and matching safety implementation |

## 3. Planning problem versus controller problem

The optimizer must not treat every inside-curve or edge bias as a controller error.

- Planning evidence: model path relative to independently observed lane center and road edge, lane probability/std, and lane-change state.
- Controller evidence: desired-versus-actual curvature or steering angle after a declared alignment delay, saturation, rate limiting and driver override.
- Vehicle/plant evidence: command-to-yaw/curvature response inside a calibrated speed, curvature, delay and friction domain.

An arbitrary lateral offset is forbidden when the independent lane reference is missing. Reusing the desired model path as the lane-center reference invalidates the lane metric.

## 4. ZoomPilot lateral architecture findings

### Speed-dependent torque authority

ZoomPilot's Mazda implementation maps the controller request with a flat steering scale and then clamps it to an interpolated speed-dependent EPS ceiling before generic driver/rate limits. Its ceiling and rate values describe measured Mazda EPS behavior, not a portable HKG tune.

Transferable concept: record requested, envelope-capped and actually applied command separately, including whether a gap came from an envelope, vehicle rail, rate limit or driver limit.

### Speed-dependent lateral tuning

ZoomPilot maintains independent per-speed-bin fits for lateral acceleration factor and friction. It publishes bin centers, values and validity, validates a cached identity, and falls back to vehicle/global values when a bin is invalid. The controller interpolates only valid learned data.

Transferable concept: a versioned, provenance-bound offline table with explicit qualified speed coverage, interpolation and exact baseline fallback.

Non-transferable content: Mazda bin centers, seeds, convergence filters and live learner/cache behavior.

### Steering command rate

ZoomPilot distinguishes rate-limited, rail-limited and driver-limited mismatch so deeper controller state is not allowed to wind up blindly. It also documents that clamping one software command to another applied value does not by itself prove a plant improvement.

Transferable concept: limit-cause telemetry and an offline rate candidate evaluated for response and smoothness together.

### Steering self-tune

The live bin learner, convergence policy, cache and runtime parameter update are automatic optimization. They are explicitly deferred to STEP 8. STEP 7 supplies immutable observations and fail-closed table evaluation only.

## 5. CarrotPilot findings

CarrotPilot can blend lane-line and model paths and apply runtime offsets. It also contains runtime torque factor, friction, gain, steering-ratio and jerk-related choices. These are useful references for observability and feature taxonomy, but copying the planner or adding an offset would mix planning correction with controller correction and could hide the actual cause.

## 6. KEEP / ADAPT / REJECT / DEFER

### KEEP

- Existing upstream model/planner/controller pipeline.
- Existing Cyber exactly-once native controller seam and read-only observers.
- Current vehicle, CarController and panda/opendbc limits.
- Existing STEP 6 simulator criteria and frozen comparison semantics.

### ADAPT

- Deterministic command/torque derivatives, steering tracking, reversal, frequency, curve-side and edge metrics.
- Offline `SpeedAwareTuneTable` with explicit provenance, domain and fallback.
- Offline `TorqueAuthorityEnvelope` that cannot exceed the existing vehicle limit.
- Offline `SteeringRateLimits` that cannot use faster rates than the existing controller.
- Exact A0-A5 feature matrix with `offline_only` execution and no live authority.

### REJECT

- Mazda speed bins, EPS ceiling, torque/rate constants, fingerprints, CAN, radar and safety changes.
- Mazda Alpha Longitudinal, ICBM, Smart Cruise, button control and Curve Speed Solver.
- Carrot planner replication, arbitrary lane offset and wholesale runtime-tune copy.
- Model output modification to hide controller error.
- Torque or rate-limit expansion.

### DEFER

- Online learning, convergence, parameter writes and automatic table updates to STEP 8.
- HKG production bins/envelopes until an approved non-holdout corpus covers the required speed and curve domains.
- Active controller integration, device shadow and real-vehicle candidate promotion until replay and calibrated closed-loop gates pass.
- Jetlink/Accelerator Link to the separate Jetson/model architecture work.

## 7. Proposed CyberPilot structure

```text
CyberLateralOptimizer (offline experiment boundary)
  |- SpeedAwareTune        immutable table evaluation and fallback
  |- TorqueAuthorityEnvelope non-increasing authority candidate and cause telemetry
  |- SteeringRateController non-faster offline slew candidate
  |- CurveErrorObserver    left/right and phase-separated tracking metrics
  |- CenteringObserver     independent lane/edge measurements
  `- SafetyLimiter         existing CarController and panda/opendbc only
```

The first three components are independent pure modules. They are not imported by `controlsd`, have no Params key, and cannot publish an actuator command.

## 8. A/B experiment matrix

| Variant | Speed-aware | Authority envelope | Rate candidate | Current status |
| --- | ---: | ---: | ---: | --- |
| A0 | off | off | off | recorded-command A/A, isolated native `card`, and corrected D3Y strict A/A passed |
| A1 | on | off | off | offline primitive implemented; replay NOT RUN |
| A2 | off | on | off | offline primitive implemented; replay NOT RUN |
| A3 | off | off | on | corrected D3Y A/B repeatable on 6/6 development windows; performance 0/6, rejected and not promoted |
| A4 | on | on | off | composition implemented; replay NOT RUN |
| A5 | on | on | on | composition implemented; replay NOT RUN |

All variants declare `execution_stage=offline_only` and `live_actuator_authority=False`.

## 9. Safety implications

- No change exists under panda, opendbc, Hyundai CarController, cereal schema, modeld or plannerd.
- The authority envelope constructor rejects any point above the supplied existing vehicle limit.
- The rate candidate rejects any rate faster than the supplied existing controller rate.
- An out-of-domain speed tune returns the exact caller-supplied baseline tune.
- None of these constraints substitutes for panda or vehicle safety; they are offline research guards only.

## 10. Data coverage and evidence limits

Approved development segment 29 contains 6004 `carState` samples over approximately 60.04 seconds. Its speed distribution is approximately min 3.186, p05 3.741, p25 4.975, p50 5.576, p75 6.186, p95 7.185 and max 7.280 m/s. About 74% of samples are 5-10 m/s and none are at or above 10 m/s.

This segment cannot define medium/high-speed bins or validate tight, left/right-balanced curves. No production HKG speed table or authority envelope is therefore provided.

The aggregate-only A0 runner executed twice over 6,001 aligned `carControl` samples. Both ordered candidate digests were identical and all candidate commands were byte-identical to baseline. This proves only the A0 optimizer pass-through contract; it is not native controller replay, lane-center evidence or closed-loop evidence.

Controller-output provenance was resolved separately over all 6,004 `carOutput` samples. The recorded 409 normalization was verified exactly at the raw-command boundary, while the candidate 384 normalization was not interchangeable. An offline-only adapter now translates through integer `torqueOutputCan`, rejects commands outside either fixed controller limit, and exposes the candidate's normalized 3/7 rates without importing cereal, Params, CAN or a controller callback. This prevents a misleading direct A3 comparison; it does not make A3 a native controller replay.

The A3 aggregate counterfactual was then executed twice with a fixed 10 ms step and the candidate's existing 384/3/7 contract. The two ordered hashes were identical. The additional pre-controller limiter changed 95 of 6,001 samples (1.583%). Command-derivative RMS changed from 0.249972 to 0.229935 ratio/s and p95 absolute derivative from 0.583705 to 0.574619 ratio/s, while maximum candidate-minus-requested error reached 0.0096115. These are command-shape observations only. Because the extra limiter overlaps the downstream Hyundai limiter and no native controller or plant response was executed, A3 receives no performance PASS and is not promoted to active control.

An isolated native `card` replay seam was then added for this test only. It fixes the recorded Santa Fe fingerprint and candidate CarParams, bypasses replay-time device/ECU initialization, and executes the unmodified Hyundai interface and CarController. The seam is accepted only under `REPLAY=1`, `SIMULATION=1`, and `PROC_NAME=card`; generated `sendcan` is counted and discarded. It does not exist in the production process configuration and grants no actuator authority.

The A0 native baseline produced 6,004 `carOutput` messages in each of two runs with identical ordered hash `9ecaa6a3ca0c0010876a0fa55d8f76d46159b239ecaab2adfb4ef046b9214837`. The runtime CarParams identified `HYUNDAI_SANTA_FE_2022`, torque control, STEER_MAX 384, raw deltas 3/7, `openpilotLongitudinalControl=true`, `pcmCruise=false`, and `radarUnavailable=true`. All 5,955 generated `sendcan` messages per run were discarded.

The same native seam was used for A3 twice. Both candidate runs produced the identical ordered hash `c0291a86f62b7f0d86fa1fc6e1d9a038e0f10887c43f1070b9677562bf52ec05`. Preprocessing changed 95 of 6,001 `carControl` requests, but the downstream native controller changed only 25 of 6,004 raw outputs (0.4164%), with maximum raw difference 3 and no saturation in either series. Normalized torque-derivative RMS changed from 0.253068 to 0.249969 ratio/s; p95 and maximum were unchanged. This qualifies native replay repeatability and quantifies downstream effect, but it still does not establish lane-center, curve-response, override, or calibrated-plant improvement. A3 remains unpromoted.

The A0/A3 orchestration now lives in the repository as an aggregate-only CLI rather than only in private scratch scripts. At clean candidate `b1473ac6947ba591cf745b53645068eccb7077d9`, it reproduced the same A0/A3 hashes, counts and metrics exactly. It rejects every variant except A0/A3, requires the exact approved segment/head/SHA and a clean checkout, refuses to write aggregate evidence inside the source tree, and considers differing discarded-`sendcan` counts nonrepeatable.

The preserved lateral simulator has a previously documented 15-27 m/s plant domain and can measure relative path/response quantities. It lacks independent lane/GPS truth for absolute lane-center or lane-edge qualification. Its acceptance criteria were not changed.

## 11. Verification and implementation decision

- New optimizer/metrics unit tests: PASSED, 24 tests.
- All Cyber Lateral unit tests: PASSED, 69 tests.
- Controls unittest discovery: PASSED, 133 tests with 1 skip.
- Isolated Cyber lateral card replay tests: PASSED, 5 tests.
- Repository native experiment runner plus replay seam: PASSED, 12 tests.
- Ruff for changed Cyber Lateral Python: PASSED.
- SCons: PASSED, exit 0 after the WSL virtual-environment PATH was fixed explicitly.
- Aggregate recorded-command A0 A/A: PASSED, 2 identical runs, 6,001 samples each, zero mismatches.
- Aggregate A3 command counterfactual: PASSED for repeatability only, 2 identical runs; performance qualification NOT RUN.
- Preserved private D3Y plant/axis/metric contract tests: PASSED, 9 tests; no holdout or recorded-drive test selected.
- Isolated native A0 controller baseline: PASSED, 2 identical runs, 6,004 outputs each.
- Isolated native A3 controller counterfactual: PASSED for repeatability and output-effect measurement only; performance qualification remains NOT RUN.
- A0-A5 simulator comparison: NOT RUN.
- Device shadow and real vehicle: NOT RUN and not authorized.

Decision: retain the new modules as offline research infrastructure. A0 command pass-through, the recorded/candidate command-domain boundary, the offline raw-command adapter, and a repeatable isolated native A0/A3 controller seam are now resolved. Do not connect the optimizer to active control or declare STEP 7 complete until an evidence-backed speed/curve corpus, calibrated closed-loop comparison and regression matrix are available.

The approved segment-29 speed domain is 3.19-7.28 m/s, while the preserved D3Y plant is validated only from 15-27 m/s. Feeding segment 29 into that plant would be an out-of-domain pseudo-result, so calibrated closed-loop remains NOT RUN rather than being forced through the simulator.

The preserved simulator's existing fail-closed contract was executed directly at the segment-29 maximum speed of 7.28 m/s against the declared 15-27 m/s plant domain. It returned `speed_below_validated_domain`, raised before the plant step, and emitted no performance score. The simulator contract suite passed 8 tests. No duplicate CyberPilot admission module was added because the existing simulator already owns this boundary.

## 12. Corrected D3Y development gate and final STEP 7 decision

The later frozen development manifest supplied six non-holdout, in-domain D3Y windows. Holdout segments 53 and 71 remained unopened. The current-schema adapter was corrected before interpreting performance:

- preserved Carrot `ESP12.YAW_RATE` is degrees per second and is normalized exactly once to radians per second;
- recorded `lateralDelay` is forwarded to the current Cyber `LatControlTorque` prediction input;
- the D3Y axis remains the only actuator-delay owner at 0.15 s;
- all output remains aggregate-only, `sendcan` is discarded, and no Params, vehicle, CAN or safety write exists.

Two complete corrected runs produced byte-identical receipts with SHA-256 `0cc6c286264340eeca67bf306905f49fccf85fd17737d4ce5b639be0fc4b28bc`. Strict A0/A0 passed on all six windows, and A0/A3 was repeatable on all six. A3 passed the frozen performance gate on zero of six windows. Three windows were output-identical and therefore provided no smoothness improvement. Two right-curve windows obtained only small derivative/zero-crossing reductions while lateral-acceleration error regressed. The remaining window regressed both left-curve/straight tracking and command smoothness. Saturation did not increase.

The STEP 8 contract audit clarified that private A3 uses 3/7 normalized command per second, whereas native raw 3/7 per 10 ms with scale 384 corresponds to 0.78125/1.8229167 normalized command per second. The earlier description of identical 3/7 limiters was incorrect. Many transformed requests were removed by quantization or downstream limiting. One window had eight quantized request changes and 34 applied-command differences; aggregate counts alone do not isolate downstream limiter state from controller/plant feedback. This candidate remains rejected, but these results do not establish that all pre-limiter architectures fail.

Final implementation decision:

- **KEEP** A0 pass-through, immutable metrics, provenance checks, current-controller bridge, aggregate-only runner and fail-closed safety boundaries.
- **REJECT** A3 as a control candidate. It remains testable research infrastructure only and is not enabled or promoted.
- **DEFER** A1/A2/A4/A5 until HKG-specific, non-holdout speed/tune/authority evidence exists. Mazda constants and live self-tune remain excluded.
- **DEFER** a tracking-aware adaptive smoother to a separately reviewed design. It would require declared curve/tracking inputs and new acceptance tests rather than another rate constant.

STEP 7 infrastructure is implemented within the tested scope. **Overall STEP 7 completion remains PARTIAL**: A1/A4/A5 lack native speed-tune application, HKG calibration and required regression coverage remain incomplete, and independent lane-center/edge truth plus device shadow are unavailable. No experimental lateral behavior is a real-vehicle candidate.

The STEP 8 entry audit also found that the private evaluator reports reversal events/s under an Hz field, skips missing groups, and reports path-error ratios without enforcing them in its legacy pass condition. Existing rejected receipts remain frozen, but the legacy boolean is not an AutoTune promotion gate. A versioned metric/coverage contract must be validated before automatic candidate selection.

STEP 8 automatic optimization must not start from the rejected A3 result. It may use the immutable metadata and metrics interfaces only after a separately approved STEP 8 design, and it must preserve the same holdout, safety and admission boundaries.
