# Source-bound native lateral worker

## Identity and purpose

- Cyber Validation STEP9 execution component; implemented and independently reviewed, blocking findings fixed.
- feature/cyber-autotune HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Real native requested-torque computation in isolated offline processes; not full
  process replay, plant evaluation, shadow mode or profile activation.
- HYUNDAI_SANTA_FE_2022 torque interface only, explicit caller CP. No firmware claim.

## Original references

- CyberPilot at above HEAD; baseline comma openpilot c8fb906815530460ed156f14e09e1f312bb0f851.
- opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76: interfaces.py linear conversion,
  vehicle_model.py, car.capnp; controller latcontrol_torque.py and native PID/filter.
- Existing licenses retained; no fork/private simulator algorithm copied. Reuse
  native symbols through an explicit original adapter. No new dependencies/models.
- Caller frozen JSON/CP -> validation/source binding -> fresh controller/VM state ->
  native update -> requested-torque/estimated-curvature trace -> supervisor checks.

## Changes and expected effect

- native_protocol.py: exact fields, strict JSON, CP digest, time/type/source contract.
- native_worker.py: standalone selected-root native import/execution; fresh state,
  supplied CP only. No online parameter update or guessed defaults.
- native_runner.py: fixed worker child command, Linux owned-process-group lifecycle,
  timeout/interruption cleanup, response/digest binding. Blocking offline API only.
- tests/test_native_worker.py and test_native_runner.py use real native modules and
  synthetic CP/frames, plus controlled subprocess faults. No raw route reads.
- 4MiB request/response,1MiB CP,10000frame/60second caps are development resource
  limits, not vehicle safety thresholds or hostile-process resource containment.
- Time10ms, normalized requested torque[-1,1]; no limiter bypass or applied-torque
  claim. Controller prediction delay is input; no physical plant-delay queue.
- Fixed CP owns torque parameters throughout run. Dynamic recorded learner updates
  and candidate-profile injection require later separately reviewed adapters.
- Rollback: stop standalone caller. No active controller state or profile changed.

## Regression risk and acceptance

- Selected-file/revision hashes and root checks are NOT exhaustive dependencies,
  build/firmware authenticity or correct input provenance. Trusted local code only.
- Process supervision is NOT an active-loop scheduler or hostile-source sandbox.
- Native requested torque cannot substitute for post-Hyundai-limiter plant input,
  actual vehicle response, lane-center truth or longitudinal metrics.
- Strict identity/CP/type/time validation; no altered baseline/reference/acceptance.
- Existing private clean-check/masks/domain/measurement logic untouched. User dirty
  work preserved; no holdout/H1/H2 access. All authority flags permanentlyfalse.
- One independent final review required before component handoff; real replay,
  closed-loop, shadow and platform fault containment remain unqualified.

## Validation method and actual results

| Check | Evidence | Result/limits |
| --- | --- | --- |
| TDD | protocol/worker missingmodule ->10tests; runner missingmodule ->9tests | focused19PASS |
| Native boundary finding | actual numpy.float64 torque output rejected by exact external type check | normalized only trusted native output; external validator unchanged |
| Package / Ruff / controls | prepared Python3.12.13/Ubuntu24.04 | 144packagePASS;276controls+packagePASS15.64s;Ruff/diffcheckPASS |
| Independent review | one whole-plan review | 2Important fixed with2RED tests/14subfailures;1Minor deferred |
| Source-isolated integration | selected upstream/current roots,2runs each | 4completed,20synthetic samples each, identical ordered traces |
| DefaultPC before final fixes | 1256collected, bounded300s | interrupted at deadline; outer shell exit1; no final test counts |
| Real replay / calibrated loop / vehicle shadow | not executed | NOT RUN |

The review found invalid CP physics and finite-input overflow after native wire/
arithmetic conversion. The worker now validates positive finite vehicle properties,
center-of-mass geometry, post-wire values, derived numerical quantities and native
state/log values. No vehicle control limit or calibration threshold was loosened.
Cross-source integration initially failed closed because the parent's editable
opendbc took precedence; explicitly selecting the requested dependency root fixed
that issue, verified by the same failed-then-passed four-process integration check.

Deferred Minor: importing native_worker directly prepends its protocol directory;
direct execute_request calls set sys.dont_write_bytecode without restoring it.
Use run_native, which starts a fresh worker and does not import native_worker into
the caller. This is a documented direct-call hygiene limitation, not live readiness.

DefaultPC ended during public fixture tests test_read_invalid_saved_params and
test_direct_parsing_1. Interrupt-time END records/EOFError are not passed tests.
No runner remained after termination. Initial affected invocation failed in shell
PATH quoting before tests; existing helper retry passed and final post-fix run
passed276. No test assertions/ignores/references were changed to obtain these results.

## Handoff

STEP9 PARTIAL. No accepted tune, new physical-performance evidence or deployment
permission. Native worker enables subsequent source-isolated arm integration;
three-arm scheduling, complete metrics, longi/plant adapters and asynchronous
non-actuating shadow/promotion remain required. Vehicle readiness NOT_READY.
