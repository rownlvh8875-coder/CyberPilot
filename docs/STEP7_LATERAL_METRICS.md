# STEP 7 Lateral Metrics and Baseline

## Measurement contract

All metric series are immutable, finite, unit-tagged and use one caller-frozen uniform time axis. Alignment delay, masks, curve phases, lane references and source identities are inputs; the metric code does not search candidate output for a favorable delay.

Lane-center and edge claims require references independent from the desired and actual path sources. Missing or dependent references produce an invalid metric rather than zero.

## Metrics

| Metric | Definition | Unit | Required source |
| --- | --- | --- | --- |
| lateral path error | actual path offset minus desired path offset | m | aligned desired and vehicle pose |
| cross-track error | caller-frozen signed cross-track series | m | independent path stationing |
| curvature tracking error | actual curvature minus requested curvature | 1/m | controller request and yaw/pose curvature |
| lane-center offset | signed offset from independent lane center | m | independent lane reference |
| inside/outside bias | lane offset normalized by curve sign | m | independent lane and requested curvature |
| left curve error | lane-center offsets where requested curvature is positive | m | independent lane reference |
| right curve error | lane-center offsets where requested curvature is negative | m | independent lane reference |
| lane-edge minimum margin | minimum independent road-edge margin | m | independent road/lane edge |
| steering jerk | third finite difference of actual steering angle | deg/s^3 | EPS steering angle |
| steering command derivative | first finite difference of normalized request | ratio/s | controller command |
| steering torque derivative | first finite difference of normalized applied torque | ratio/s | car output/applied command |
| desired-actual steering error | actual minus desired steering angle | deg | desired angle and EPS angle |
| zero-crossing frequency | command-derivative reversals above a frozen deadband divided by two and duration | Hz | normalized command |
| oscillation frequency | strongest non-DC discrete frequency of mean-centered command | Hz | normalized command |
| torque saturation ratio | fraction of caller-tagged saturated samples | ratio | controller/vehicle limit state |
| driver intervention count | rising edges of driver intervention | events | car state |
| declared-delay residual | actual curvature minus request at the declared delay | 1/m | frozen delay and phases |

Every aggregate reports count, signed mean, RMSE, p95 absolute value and maximum absolute value. Minimum edge margin and scalar frequencies use the scalar value in the same immutable result schema.

## Curve and regression strata

The evaluator must preserve separate rows for:

- straight, entry, apex and exit;
- left and right curves;
- gentle and tight curvature domains;
- low, medium and high speed domains fixed before candidate results;
- lane change, driver override, steering release and re-engagement;
- saturation and non-saturation segments.

An improvement in one stratum is not an overall pass if another required stratum regresses outside its frozen threshold.

## A/B baseline table

No real candidate result is inserted until the replay identity, speed domain, curve masks, delay and independent references are frozen.

| Variant | Center deviation | Curve error | Edge margin | Steering tracking | Jerk | Oscillation | Saturation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 baseline | NOT RUN: independent center truth missing; relative path-y reported separately | left/right/straight lateral-accel error only | NOT RUN: no independent edge truth | lateral/yaw/curvature proxies only | lateral jerk only; steering jerk unqualified | reversal-event proxy only | 0.0 applied ratio on 6 windows | strict A/A passed 6/6; frozen development baseline |
| A1 speed-aware | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | no evidence-backed speed table |
| A2 envelope | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | no HKG envelope calibration |
| A3 rate | NOT RUN: independent center truth missing | lateral-accel error regressed in curve groups | NOT RUN: no independent edge truth | lateral/yaw/curvature proxies; gate 0/6 | lateral jerk only; steering jerk unqualified | reversal-event proxy only | 0.0 applied ratio on 6 windows | repeatable 6/6; rejected, not promoted |
| A4 tune+envelope | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | prerequisites missing |
| A5 all | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | prerequisites missing |

## Approved development-log coverage

One approved development segment was fixed by a private external manifest and content digest. The public record intentionally withholds the local path and raw route identity. It has approximately 60.04 seconds and 6004 `carState` samples.

| Statistic | vEgo m/s |
| --- | ---: |
| min | 3.186 |
| p05 | 3.741 |
| p25 | 4.975 |
| p50 | 5.576 |
| p75 | 6.186 |
| p95 | 7.185 |
| max | 7.280 |

Approximately 26% is below 5 m/s, 74% is 5-10 m/s, and there is no coverage at or above 10 m/s. Absolute curvature p50/p90/p95/max is approximately 0.000416/0.001068/0.001280/0.001505 1/m. This is insufficient for production speed bins, high-speed behavior or tight-curve qualification.

Two protected holdout segments remain unopened.

## Recorded-command A0 and controller-domain evidence

The segment-29 A0 pass-through was run twice on 6,001 aligned `carControl` samples. Both ordered candidate hashes were `143572a544685ecb145fc4ebf7dcc6a616f8ae20ca6c6262127a2ad1818c856b`, with zero byte mismatches. This is a PASS for the A0 software pass-through invariant only; every lane, curve, edge, steering-response and closed-loop metric in the table above remains NOT RUN.

The recorded Carrot controller source and route-start Params use STEER_MAX 409 with raw 3/7 increments per 10 ms. The fixed Cyber candidate uses STEER_MAX 384 with the same raw increments. Across all 6,004 recorded `carOutput` samples, 6,004 matched `torqueOutputCan / 409`, whereas only 1,507 rounded to the same raw value under 384. Therefore normalized recorded output is not a valid candidate applied-command series. The new offline adapter converts through raw `torqueOutputCan` and rejects a value outside either contract; otherwise an A3 experiment would mix controller stages and could double-count rate/delay.

The A3 counterfactual used the candidate's existing 384/3/7 contract at a fixed 10 ms step. Two runs produced the same ordered hash `846f64a82ef04d8c8c8ce510dea43e16e9610422cee3dc56c63b6167e2d24af3`. The limiter intervened on 95/6,001 samples (0.0158307). Baseline versus candidate command derivative was:

| Aggregate | Baseline ratio/s | A3 ratio/s |
| --- | ---: | ---: |
| mean absolute | 0.144001 | 0.139193 |
| RMS | 0.249972 | 0.229935 |
| p95 absolute | 0.583705 | 0.574619 |
| maximum absolute | 1.823333 | 1.802382 |

Candidate-minus-requested RMS was 0.0004426 and maximum absolute error was 0.0096115. This is not steering jerk, curvature response, lane-center performance or a calibrated closed-loop result. The additional pre-controller limiter overlaps the existing Hyundai limiter, so it is not promoted on this evidence.

## Isolated native controller evidence

The replay-only `card` seam executes the fixed Cyber Hyundai interface/CarController and discards all generated `sendcan`. Its runtime contract is `HYUNDAI_SANTA_FE_2022`, torque control, STEER_MAX 384, raw 3/7 deltas, `openpilotLongitudinalControl=true`, `pcmCruise=false`, and `radarUnavailable=true`.

A0 produced 6,004 `carOutput` samples in each of two runs. Both ordered hashes were `9ecaa6a3ca0c0010876a0fa55d8f76d46159b239ecaab2adfb4ef046b9214837`, with zero normalized/raw scale mismatches. Each run generated 5,955 `sendcan` messages, all counted and discarded.

A3 used the same native path after the offline rate candidate transformed the input `carControl` stream. The 6,001 evaluated requests contained 95 changes and had ordered preprocessing hash `07b56b7c98bfb4d62953ae514c13e429707acd97f8d75e59bc691581b0df14d3`. Two native A3 runs produced the same ordered output hash `c0291a86f62b7f0d86fa1fc6e1d9a038e0f10887c43f1070b9677562bf52ec05`.

| Native aggregate | A0 | A3 |
| --- | ---: | ---: |
| normalized torque derivative mean absolute, ratio/s | 0.138342 | 0.137475 |
| normalized torque derivative RMS, ratio/s | 0.253068 | 0.249969 |
| normalized torque derivative p95 absolute, ratio/s | 0.520834 | 0.520834 |
| normalized torque derivative maximum absolute, ratio/s | 1.822917 | 1.822917 |
| saturation ratio | 0.0 | 0.0 |

A3 changed 25/6,004 raw controller outputs (0.4164%). Candidate-minus-baseline raw output had mean absolute 0.005996, RMS 0.101619, p95 0 and maximum 3. This is repeatable controller-output evidence, not a performance pass: no plant, independent lane/edge truth, curve response or driver-override benefit was measured.

The repository-owned native experiment runner at `b1473ac6947ba591cf745b53645068eccb7077d9` reproduced the same A0/A3 hashes and every aggregate above. Its evidence file contains only aggregate values; raw messages and generated CAN are not written or forwarded.

## Current verification baseline

| Check | Status | Result |
| --- | --- | --- |
| New optimizer and extended metric tests | PASSED | 24 tests |
| All Cyber Lateral tests | PASSED | 69 tests |
| Controls unittest discovery | PASSED | 133 tests, 1 skipped |
| Isolated Cyber lateral card replay tests | PASSED | 5 tests |
| Repository native experiment runner plus replay seam | PASSED | 12 tests |
| Ruff on changed Cyber Lateral Python | PASSED | no findings |
| SCons | PASSED | exit 0 with the WSL virtual-environment PATH fixed explicitly |
| Aggregate A0 recorded-command A/A | PASSED | 2 identical runs, 6001 samples each, zero mismatches |
| Recorded/candidate command-domain provenance | PASSED | 409 recorded scale verified; direct 384 reuse rejected |
| Aggregate A3 command counterfactual | PASSED | repeatable command-shape result; performance pass false |
| Private D3Y plant/axis/metric contract | PASSED | 9 selected tests; no holdout or recorded-drive test |
| Isolated native A0 controller baseline | PASSED | 2 identical runs, 6004 outputs each; `sendcan` discarded |
| Isolated native A3 controller counterfactual | PASSED | 2 identical runs; 25 raw outputs changed; performance pass false |
| Simulator fail-closed domain contract | PASSED | 8 tests; direct 7.28 m/s probe blocked with `speed_below_validated_domain`; no score emitted |
| Calibrated A0-A5 closed loop | BLOCKED | segment 29 is 3.19-7.28 m/s; plant is valid only at 15-27 m/s |
| Non-actuating shadow | NOT RUN | requires replay and simulator gates plus separate approval |
| Real vehicle | NOT RUN | prohibited at this stage |

## Corrected six-window D3Y development result

The current-schema yaw-rate and controller-delay boundary was corrected before the final gate. The frozen six-window manifest is development-only; validation and holdout remained unopened. The D3Y axis owns the 0.15 s actuator delay, while the recorded `lateralDelay` is used only by the current controller prediction path.

| Gate | Result |
| --- | --- |
| strict A0/A0 | PASSED, 6/6 windows |
| A0/A3 repeatability | PASSED, 6/6 windows |
| A3 performance | FAILED, 0/6 windows |
| applied torque saturation | unchanged at 0.0 in all six windows |
| device shadow | NOT RUN |
| independent lane-center/edge truth | NOT AVAILABLE |

Per-window A3 outcome:

| Development window | Output effect | Required-group result | Decision |
| --- | --- | --- | --- |
| development window 1 | applied output identical | no smoothness improvement | reject |
| development window 2 | changed | right-curve lateral error ratio 1.0000197 | reject |
| development window 3 | changed | right-curve lateral error ratio 1.0000155 | reject |
| development window 4 | applied output identical | no smoothness improvement | reject |
| development window 5 | applied output identical | no smoothness improvement | reject |
| development window 6 | changed | left-curve/straight error and smoothness regressed | reject |

Across the six windows, A3 changed 1/9/26/30/12/10 floating-point requests, with post-Hyundai applied-command differences of 0/2/7/0/0/34 samples. Aggregate counts do not isolate limiter-state propagation from closed-loop feedback. The STEP 8 audit found different rate units: private A3 3/7 command/s versus native 0.78125/1.8229167 command/s (raw 3/7 per 10 ms at scale 384). The tested candidate remains rejected; a blanket architecture rejection is not supported.

STEP 8 must not import the legacy simulator pass boolean as complete acceptance. The private runner reports reversals/T, whereas the public metric reports reversals/(2T); both differ from PSD oscillation frequency. It also skips missing groups and does not enforce reported path-error ratios. Preserve legacy receipts and thresholds, then validate a separately versioned evaluator with required corpus coverage and primary-metric gates. These findings do not change the existing A3 rejection.

The final corrected aggregate receipt SHA-256 is `0cc6c286264340eeca67bf306905f49fccf85fd17737d4ce5b639be0fc4b28bc`. This is relative controller/plant evidence. It is not an absolute lane-center, lane-edge, road-safety or real-vehicle qualification claim.

## Promotion rule

STEP 8 may consume these interfaces only after STEP 7 produces a frozen, repeatable dataset and metric baseline. STEP 8 must not change safety limits, learn from holdout data, write parameters without admission, or reinterpret the STEP 7 acceptance criteria.

The frozen development baseline and repeatable metric pipeline now exist, but A3 is rejected and independent lane-center/edge plus device-shadow evidence remain unavailable. STEP 8 may begin only as a separately approved offline design/analysis activity; no learner, parameter write or runtime admission is authorized by STEP 7.
