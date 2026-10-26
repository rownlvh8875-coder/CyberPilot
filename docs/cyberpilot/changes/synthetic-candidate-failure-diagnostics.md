# Frozen synthetic candidate failure diagnostics

## Identity and purpose

Cyber Validation / AutoTune, continuation from `cfa169896ad2efd913ec2f99e968ece1fed8c475`
on `feature/cyber-autotune`. Bounded diagnostic extension; it does not complete the
remaining active Cyber Long/Lateral features or vehicle qualification.
The user delegated intermediate implementation decisions and asked to continue
with existing code/data only. No new driving data is requested or consumed.

## Original references and traced boundary

Reuse CyberPilot's `synthetic_pipeline.evaluate`, `synthetic_native_v2` and frozen
`synthetic-stress-candidate-v2.json`, from the baseline above. No external code,
Carrot/Sunny/Zoom constants or license changes. Native references remain upstream
`c8fb906815530460ed156f14e09e1f312bb0f851` and opendbc
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.

Existing report bytes → duplicate-key rejection → existing full matrix/evidence
validation → exact recomputed verdict match → per-axis, case, delay and metric
diagnostics. Controller/plant execution is not invoked by this reader. It cannot
write Params, CAN, profiles or replay references. Content digests identify bytes,
not authenticated producers; retrospective parsing is not a fresh native rerun.

## Design and changes

- Add `synthetic_diagnostics.py` and its targeted tests. Runtime integration: none.
- Keep the existing acceptance function and policy unchanged. Diagnostic output
  retains original reasons and cannot promote or select a candidate.
- Separate all 50 declared case/delay variants, including seven rejected-input
  cases; never merge delay epochs. Count regressions per metric per variant.
  Existing verdicts de-duplicate case/metric reasons across delays, so those
  counts are intentionally different, not newly discovered gate failures.
- Record changed output-trace and changed CarParams counts independently.
  Lateral Kp is held on a fresh PID instance rather than CarParams, so an
  unchanged CP digest alone cannot prove an ineffective candidate.
- Positive oriented delta means worse under the frozen lower/higher direction.
  Preserve units in metric names; do not sum losses across different units.
  Null is unavailable, not zero. Percent changes require a positive baseline.
- Read at most eight bounded worker payloads (four arms, two repetitions).
  Invalid JSON, duplicate fields, unreadable/oversized/symlink inputs, forged
  verdicts and nonrepeatable evidence produce a redacted BLOCKED result.
- No parameter search, bounds, model output, actuator delay or control behavior
  changes. Alternative rejected: change gains/thresholds before explaining the
  existing failed experiments. Existing policies/evidence remain immutable.

## Regression risk and acceptance

The main risks are reversed metric direction, collapsing distinct delays,
claiming no-op candidates improve behavior, treating missing metrics as zero,
or summarizing mismatched evidence. Tests use actual native synthetic fixtures
and invalid-input mutations; hand-derived metric cases cover sign/zero/null/
overflow. Test-fixture duplicate arms are not repeatability evidence. Historical
fresh-worker artifacts are separately read without regeneration or modification.

Acceptance: deterministic read-only report; exact original candidate verdicts;
no authority flags true; malformed evidence has no partial metric output.
Frozen numerical allowance is 1e-9, unchanged; no new performance threshold.
Rollback is omission of this standalone reader; no active controller changes.
Independent review and final checks are recorded below after execution.

## Findings from the preserved synthetic report

Both candidates remain REJECTED. Neither is a vehicle tune.

| Observation | Gentle | Firm |
| --- | ---: | ---: |
| Lateral completed variants / changed traces | 26 / 25 | 26 / 25 |
| Longitudinal completed variants / changed traces | 17 / 0 | 17 / 0 |
| Lateral regressions, per metric and delay variant | 213 | 151 |
| Lateral regressions, unique original gate reasons | 192 | 133 |
| Longitudinal regressions | 0 | 0 |

The gentle verdict additionally retains `NO_REQUIRED_PRIMARY_IMPROVEMENT`.
In the constant-left fixture, center RMS is 0.712548 m baseline, 0.719712 m gentle,
0.705624 m firm. Requested-command derivative RMS is 1.353919, 1.284536 and 1.423625
per second respectively. These illustrate tracking/smoothness trade-offs in this
generic plant, not the user's vehicle or independent lane truth.

The longitudinal result has a concrete configuration explanation: native
`CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)` has `kiV=[0]`.
`_longitudinal_trace` multiplies that vector by 0.95 or 1.05 before constructing
`LongControl`; both still produce `[0]`. Thus all 17 completed longitudinal
traces and candidate CP digests are unchanged. This grid has not tested a
nonzero longitudinal feedback candidate. No nonzero value is invented to force
a different output; such a change requires separately designed, bounded offline
experiments and cannot overwrite this frozen grid.

These observations do not establish the causal origin of every lateral loss.
The native controller receives supplied curvature rather than a closed-loop
path planner, so center error cannot be cured by assuming a controller-gain
change solves path/pose bias. Full planner-coupled validation remains separate.

## Validation method and actual results

Initial test-first run: six missing-module errors (new API absent), exit 1.
First implemented targeted run: six passed, exit 0. CLI boundary additions plus
the existing AutoTune/controls tests passed 615 tests, exit 0 (116.62 s), before
the final review fixes and feedback-loop extension.

Independent review reproduced a diagnostic defect: an evaluator may complete
while rejecting incomparable plant/reset/CP bindings. The initial reader still
summarized those metrics. A new regression failed with DIAGNOSTIC_ONLY instead
of BLOCKED; the reader now blocks non-performance/non-availability comparison
  errors before any metrics. The original acceptance function/policy is unchanged.
The isolated regression passed after correction, and review accepted the fix.

The preserved report was read three times; output bytes matched exactly with
SHA-256 `76b91bffaa30725f3e76175767b9c3680c16cda5d6ff055942758b7c39905396`.
This is reader repeatability over historical evidence, not a new native rerun.
Ruff and SCons passed. Final combined regression/full-suite status is recorded
in the continuation section of the remaining-work audit.

Read-only invocation (write stdout only to an approved local artifact location):

```sh
python -m openpilot.tools.cyber_autotune.synthetic_diagnostics synthetic-report.json
```

Exit 0 means diagnostic generation succeeded, not candidate acceptance. Exit 1
means BLOCKED. This command never executes the native worker or requests logs.

## Handoff

Next engineering priorities: validate candidate effectiveness before an expensive
search, then design planner-coupled longitudinal synthetic validation to exercise
actual lead/stop planning rather than supplied acceleration alone. The rejected
gain grid is not a reason to weaken the frozen zero-regression policy.
Real-vehicle readiness remains NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED. Live shadow, vehicle-calibrated qualification and
actual activation/rollback are NOT_RUN here. No commit/push in this continuation
unless separately recorded after verification.
