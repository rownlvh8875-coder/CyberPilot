# Controller-to-plant authority audit plan

Additive offline audit from 598bd022a. Historical source, candidate configurations,
70 repeat receipts, calibration and meter results remain immutable. CURRENT is
BASELINE; V1 TRADEOFF_ONLY; V2 REJECTED (37 violations).

1. Pin the 70 recovered synthetic receipts against the published recovery index.
   Use the 11 EVALUATION cases for per-stage candidate decomposition; all roles
   retain separate provenance. No native/controller rerun or private data access.
2. Before new plant execution freeze the original descriptive plant/reset,
   speeds 5, 17.5, 25 m/s (existing scenarios), 401 steps at 0.01 s, step and
   full-duration ramp, mirrored signs. Amplitudes: zero plus the exact pooled
   nominal V1/V2 absolute requested-torque delta p50, p95 and maximum.
   These are diagnostic inputs, not candidates or physical actuator estimates.
3. Verify constant-curvature geometry against a circular-arc oracle, accounting
   for right-end Euler position integration and the plant kinematic curvature
   convention k_geometric = -curvature_1pm. Analytic discrete recurrence verifies
   step response, delay and curvature gain independently of the plant primitive.
4. Decompose desired/requested/applied/curvature/yaw/heading/pose deltas, signed
   and absolute integrals, derivative and sign changes. No cross-unit ratio is
   called dimensionless attenuation. Ratios with zero denominators are null.
   Delay alignment is 2 samples in the nominal plant; controller reference delay
   is a separate native setpoint operation, not a second physical actuator queue.
5. Report observed 5–30 m plus 35/40 m and common maximum-x context without
   extrapolation or extending the meter envelope. Keep error/coverage/verdicts
   separate. A small effect is not an acceptance criterion.
6. Add a loopback-only public synthetic visualizer; no private coordinates/images.
   Freeze aggregate receipts, test, independently review, commit/push, await CI.

Expected limits: descriptive plant only, no real vehicle dynamics or candidate
acceptance. Reference calibration track remains blocked independently.
