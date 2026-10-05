# A1 bounded half-scale generic closed-loop hypothesis

## Identity and purpose

Cyber Lateral / AutoTune offline validation. Baseline
`a10cc249f5fcc8d99aa27451a230222549cbb0ce`, branch
`feature/cyber-autotune`. Status: implemented and software verification gates
complete; vehicle qualification and activation remain blocked.

The prior A1 factor/friction/combined tables are retained as rejected evidence.
This separate hypothesis asks whether exactly one-half of those synthetic
offsets can pass the unchanged per-frame admission rule across the complete
existing lateral catalog, and whether the resulting native-controller generic
closed-loop metrics satisfy the unchanged frozen policy. It is not a Hyundai
tune, profile, vehicle parameter recommendation or road-use candidate.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline
above. Reuse the existing MIT-licensed openpilot LatControlTorque path and
CyberPilot `a1_closed_loop._trace`, `a1_schedule.prepare_schedule`,
synthetic stress catalog, generic lateral plant, synthetic metrics and frozen
comparison policy. Pinned opendbc remains
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.

No third-party fork code or new dependency is introduced. The call path is:
fixed predeclared table -> unchanged schedule admission -> existing native
LatControlTorque -> existing generic plant -> unchanged lateral metrics ->
unchanged frozen comparison. Perception/model/planner, CarController/EPS, CAN,
Params and vehicle profile activation remain outside this experiment.

## Changes and expected effect

Added:
- `openpilot/tools/cyber_autotune/a1_bounded_closed_loop.py`: declares the
  fixed half-scale tables, executes all existing lateral case/delay inputs and
  compares them with the existing disabled baseline.
- `openpilot/tools/cyber_autotune/a1_bounded_closed_loop_worker.py`: fixed
  no-input bounded worker with source/policy revalidation and sanitized failure.
- `openpilot/tools/cyber_autotune/tests/test_a1_bounded_closed_loop.py`: covers
  schedule admission, complete coverage, preserved old rejection, non-noop
  execution, report authority and deterministic worker behavior.
- this feature record.

The predeclared coordinate is `BOUNDED_SCALE = 0.5`. Starting from the prior
synthetic offsets, the only new offsets are:

| Speed m/s | factor offset | friction offset |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 10 | 1/128 | 1/2048 |
| 20 | 1/64 | 1/1024 |
| 30 | 0 | 0 |

`bounded_factor`, `bounded_friction` and `bounded_combined` selectively
apply those fixed offsets. The scale was chosen before execution from the old
maximum offset versus the existing `MAX_FRAME_DELTAS`; it is not selected
from performance results. Existing wire float32 validation makes the actual
admission decision.

No warm-up, clipping, fallback, schedule ramp, parameter limit, controller,
plant, catalog, policy or metric is changed. If the half-scale table had failed
admission, the experiment would have remained BLOCKED rather than reducing the
scale. The old factor/friction/combined fixtures and their middle-speed
`A1_TRANSITION_EXCEEDED` behavior remain unchanged.

State ownership and reset behavior are inherited from `a1_closed_loop`: each
case has a fresh controller and plant, state is retained within that case, the
plant alone owns the declared physical delay, and the native .15 s reference
history compensation remains unchanged. Failure returns no vehicle authority.

## Regression risk and acceptance

Risks include accidentally weakening A1 transition admission, modifying the
old rejected fixtures, changing frozen policy/catalog input, treating complete
execution as performance acceptance, leaking source/input data, or confusing
generic-plant centering with perception/real-lane centering.

Predeclared acceptance retains the frozen policy
`4ff9dcfaa369cbdcee53f56a8db9c160efb3005a50f463e4125a1f41b74e8d35`:
no ranked regression beyond the existing numeric allowance, at least 1% primary
improvement, complete valid coverage, and the existing additional rejection for
negative lane margin or unresolved recovery. Invalid catalog inputs must remain
rejected. All vehicle/runtime/profile/CAN authorities remain false regardless
of a synthetic verdict.

Rollback is to stop invoking or revert the three added executable/test files;
there is no active state or persistent vehicle setting to undo.

## Validation method and actual results

The first attempted RED was invalid evidence: a tool-output footer was
accidentally copied into the test file and caused a SyntaxError. The test file
was restored byte-for-byte from the prepared D evidence before the real RED.

Valid test-first RED: five tests failed in 0.001 s because
`a1_bounded_closed_loop` did not exist. After the module was added, the five
tests passed in 47.186 s. The first GREEN exposed two test-design defects, not
product defects: a dataclass was passed directly to JSON canonicalization, and
a string search incorrectly rejected the required `runtime_accepted` key.
Those assertions were corrected without changing candidate values or policy.

Worker RED: one test failed in 0.001 s because the fixed worker did not exist.
After adding the worker, that test passed in 25.699 s. The complete six-test
feature module then passed in 73.512 s. Targeted Ruff and `git diff --check`
pass after renaming one unused test loop variable.

Actual complete matrix:

| Arm | valid completed | valid blocked | invalid rejected | verdict |
| --- | ---: | ---: | ---: | --- |
| baseline | 26 | 0 | 3 | reference |
| bounded_factor | 26 | 0 | 3 | REJECTED |
| bounded_friction | 26 | 0 | 3 | REJECTED |
| bounded_combined | 26 | 0 | 3 | REJECTED |

Thus the hypothesis resolves the previous startup-coverage limitation at this
fixed coordinate, but does **not** produce an acceptable performance candidate.
Reason accounting from the unchanged comparison:

| Candidate | total reasons | ranked regressions | negative lane margin | unresolved recovery | required primary improvement |
| --- | ---: | ---: | ---: | ---: | --- |
| bounded_factor | 220 | 201 | 17 | 1 | not achieved |
| bounded_friction | 129 | 110 | 17 | 1 | not achieved |
| bounded_combined | 246 | 227 | 17 | 1 | not achieved |

Representative speed-sweep values remain synthetic generic-plant evidence:

| Arm | center RMS m | minimum lane-edge margin m | steering jerk RMS deg/s^3 |
| --- | ---: | ---: | ---: |
| baseline | 0.705249180 | -0.898614445 | 98883.594450 |
| bounded_factor | 0.707212786 | -0.904131673 | 98786.024036 |
| bounded_friction | 0.703364568 | -0.893556148 | 98901.442921 |
| bounded_combined | 0.705321529 | -0.899053889 | 98803.951392 |

The bounded-friction row slightly lowers center RMS in this one scenario while
worsening jerk and retaining negative lane margin; the complete frozen-policy
matrix rejects it. No single-case improvement overrides the full verdict.

| Check / stage | Method and command | Actual result and limits |
| --- | --- | --- |
| Test-first feature RED | unittest new module | PASS as RED: 5 expected failures from missing module |
| Feature GREEN | unittest new module | 6/6 pass after worker TDD; 73.512 s |
| Fixed matrix | existing generic closed loop | 26 valid executed per arm; all three candidates REJECTED |
| Deterministic process | two fixed no-input workers | byte-identical in worker test; no external input accepted |
| Ruff / whitespace | changed Python + diff check | PASS at this checkpoint |
| Affected / AutoTune+controls | unittest A1 scope / supported runner -j2 | PASS: 31/31 and 838/838; 122.293 s / 224.95 s |
| SCons | `.venv/bin` first on PATH, `scons -u -j2` | PASS, exit0, 189 s; two earlier command-environment PATH failures preserved |
| Default verified-public-fixture suite | unchanged verified public fixture supervisor | PASS: 1745 passed / 42 skipped / 1 xfailed, exit0, 314.51 s; source/fixture unchanged |
| Privacy / independent review | publication scanner / read-only independent Codex source review | PASS: 4 files, 0 findings; APPROVE, Critical/Important/Minor none |
| Qualified replay / calibrated plant / device shadow | separate vehicle evidence | NOT_RUN |

Separate fresh-process repetition also passed after the combined suite: two
fixed no-input workers exited0 with byte-identical 350171-byte reports, SHA-256
`da51cc8c021293c04c3b36924274af31fcbdc03fc507a318a1d4bbb1b0cadce0`.
All three candidate verdicts remained REJECTED and vehicle authority remained
false. The full-suite supervisor used the previously verified 13,340,142-byte
public upstream fixture (SHA-256
`0b03d7fcf5ed7c7bf9643215259be555c78ad6205780115f29427fcfe0413e94`);
its run completed in 315.324 s without timeout or verification errors.

The first two SCons attempts are retained as environment failures, not hidden:
the first shell could not find `scons`; the second invoked `.venv/bin/scons`
without placing `.venv/bin` on child PATH, so `cythonize` and `capnpc`
were unavailable. No source was changed for either failure. The corrected
environment command built the unchanged source successfully.

## Handoff

Verified effect so far: the fixed half-scale synthetic tables remove the old
first-frame admission gap across all existing valid lateral case/delay inputs.
Verified performance effect: all three candidates are REJECTED by the unchanged
policy. Do not retune this same hypothesis after seeing these results.

This experiment does not consume `lane_visible` through perception/planning and
does not establish real lane-center truth. It also does not validate runtime
parameter provenance, a calibrated vehicle model, qualified replay, non-actuating
device shadow or physical EPS behavior.

No new driving logs, private simulator data, reserved/holdout evidence, safety
limits, device writes, CAN operations, active profile, road test, automation
restart, main/develop merge or force push are involved.

All declared software regression/build/privacy/review gates above are complete.
This remains offline synthetic evidence only and does not authorize vehicle use.
Vehicle decision remains:
`NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`.
