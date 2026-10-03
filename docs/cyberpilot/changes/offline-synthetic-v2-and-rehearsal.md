# Offline synthetic v2 and snapshot rehearsal

## Identity and purpose

Validation/AutoTune extension on `feature/cyber-autotune`, resumed from
`abdcb5e88acc24c8567accc949c2b7740b3ef02a`. Final results are recorded in the
branch-completion document; implementation/test work is not vehicle qualification.
Complete deterministic supplied-plan controller-core experiments and defensive
offline publication/recovery paths without requesting new driving data.

## Original references

Reuses this repository's native torque/LongControl workers, generic lateral plant,
immutable proposal codec and Linux archive primitives. The native controller core
derives from upstream baseline `c8fb906815530460ed156f14e09e1f312bb0f851`.
Pinned opendbc revision: `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
No new Carrot/Sunny/Zoom code or constants are copied. Existing source licenses and
attribution remain unchanged. No model inference is executed by the new runner.

Call path: declared synthetic frames → fresh native controller → one generic
plant-owned physical delay → generic response → native-model inverse steering
feedback or longitudinal state → versioned metrics → frozen comparison policy.
Requested commands never reach vehicle CarController, CAN, Params or active profile.

## Changes and expected effect

- `synthetic_stress_catalog`: formula-based 26 lateral/18 longitudinal cases,
  no RNG, complete input-byte hashes, 50 independent delay variants.
- `synthetic_metrics`: absolute nearest-rank P95, RMS/max, derivative diagnostics,
  signed bias/edge margin, event-local recovery and explicit null coverage.
- `synthetic_native_v2`: fresh per-case CP/controller/plant, supplied plan,
  memory-only gain variants. Preserve native torque/PID acceleration limits.
- `synthetic_pipeline`/worker: isolated fresh interpreters, source/config/input/
  reset/plant/metric bindings, full catalog comparison, exact repeated outputs.
- `worker_resources`: worker-entry CPU/address-space/core-dump ceilings only;
  parent control process is not modified. Native supervisors retain owned-group
  timeout/cleanup. This is not a hostile-code sandbox or real-time scheduler.
- `profile_rehearsal`: immutable prior/candidate proposal snapshots, ordered audit
  receipts, denied activation even after confirmation, memory-only rollback.
- Shadow integration tests reuse existing scheduler; no duplicate runtime hook.
- Publication guard and CI inspect history, staged and untracked changes; errors
  and findings are redacted and unsupported artifacts fail closed.

Synthetic constants are stress fixtures, not reviewed vehicle tuning bounds:
10 ms timestep; 0/30/150/300 ms plant-delay variants; 200 ms response lag; generic
plant geometry and normalized command response inherited from v1; +/-5% PID gain
scales around the native core in fresh memory only. No safety parameter is tuned.
The lateral controller's 150 ms reference-history compensation is separately
reported and is not a second physical actuation queue. State is reset before each
variant. Input commands refer to interval start; resulting state to interval end.

## Regression risk and acceptance

Frozen policy SHA:
`4ff9dcfaa369cbdcee53f56a8db9c160efb3005a50f463e4125a1f41b74e8d35`.
Catalog SHA:
`30cafc16d93e006fd00fc67377edeec2083f294381f169697ebbee583e2f3de4`.
No relative regression allowance; numeric allowance 1e-9; required primary
improvement 1%. All cases/delay variants and two repeats per arm are required.
Added descriptive jerk P95/max and event duration metrics do not retroactively
alter this frozen ranking policy. Candidates rejected by any listed regression
remain rejected. No holdout/private driving input is consumed by this extension.

Baseline/current here are independent identity runs of the same native core,
not a full upstream/Cyber fork A/B. Lane visibility and radar/model disagreement
are supplied metadata with no perception consumer; their behaviors remain
unavailable. Lane-loss recovery is always null. The pose-value jitter fixture is
distinct from supplemental timestamp-jitter rejection testing. Supplied avoidance
and signal-stop fixtures do not claim obstacle or signal recognition.

## Validation method and actual results

Test-first failures were observed for missing catalog binding, changed executed
inputs, feedback conversion, time stage, incomplete evidence, invalid metric
domains and missing state-machine behavior. Fixes did not relax thresholds.
Independent review accepted metrics/catalog, native adapter, pipeline corrections,
publication guard and profile rehearsal after the fixes.

The initial complete synthetic matrix passed identity/repeatability checks and
rejected both gain candidates. Final source-bound reruns, build/test counts and
publication evidence belong in the completion report, not inferred from this
incremental result. No replay references or historical private simulator outcomes
are regenerated or relabeled.

## Handoff

Rollback of this development is normal Git history review, not destructive reset.
Runtime defaults remain upstream-compatible/disabled. Snapshot `ROLLED_BACK` means
offline selection of verified prior bytes only. Corrupt/missing/version/source
mismatched receipts fail closed; unverified crash residue is retained, not repaired.
Local process-crash and fsync tests do not establish hardware power-loss durability.
Real-time jitter, actual message-bus consumption and on-device shadow are NOT_RUN.
Vehicle application is blocked; public publication is not road-use approval.
