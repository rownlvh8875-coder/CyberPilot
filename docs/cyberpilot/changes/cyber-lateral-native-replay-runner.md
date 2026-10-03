# Cyber Lateral native replay runner

## Identity and purpose

- Feature / area: Cyber Validation for Cyber Lateral STEP 7.
- Status: implemented; fixed segment and external frozen-development manifest execution complete; performance qualification pending.
- Purpose and concrete scenario: replace private scratch orchestration with a repository-owned, repeatable aggregate-only A0/A3 native `card` replay runner.
- Scope, exclusions and vehicle applicability: fixed `HYUNDAI_SANTA_FE_2022` replay seam, approved development segment 29 or an external frozen-development manifest, A0 and A3 only. A1/A2/A4/A5, plant simulation, live CAN, device control, parameter tuning and deployment are excluded.
- CyberPilot branch / baseline SHA / candidate SHA or uncommitted patch identity: `feature/cyber-lateral`; baseline `1ab50986eb193506b9acce17b65f60cb27531f3e`; fixed-segment candidate `b1473ac6947ba591cf745b53645068eccb7077d9`; manifest-capable candidate `706fa6fa25c79a9a61afb6b8694e82d12e82019c`.

## Original references

- Source repository URL / verified branch / exact commit SHA: CyberPilot fixed base `19062e9b0bfc98a132e0fd8a2e2e540fe8fdeeeb`; recorded Carrot source identity `5a970f1a`; no external runner code copied.
- Source files, symbols and license / attribution requirements: reuses CyberPilot `command_domain.py`, `optimizer.py`, `steering_rate.py`, and the replay-only `cyber_lateral_card.py` seam under the repository's existing license.
- Traced callers → input data / state → algorithm → outputs / consumers: CLI → identity gate → `LogReader` messages → optional A3 offline request transform → native replay-only `card` process → `carOutput` aggregate/hash → JSON stdout.
- Relevant submodule SHAs, model identity and external dependencies: existing pinned repository submodules; no model execution or new dependency.
- Adoption decision: implement a CyberPilot-native runner around the existing replay seam. Reject untracked scratch scripts as the durable verification interface.

## Changes and expected effect

- Added `openpilot/selfdrive/test/process_replay/cyber_lateral_native_experiment.py`: exact input identity validation, A0/A3 orchestration, deterministic aggregate comparison and CLI. Optional aggregate output uses exclusive creation outside the clean source tree, so child-process diagnostic output cannot corrupt the JSON evidence file. A later focused extension accepts an external manifest only when it declares development role, records unopened holdout and validation authority, and binds the selected route parent and SHA; private manifests remain outside the repository.
- Added `openpilot/selfdrive/test/process_replay/test_cyber_lateral_native_experiment.py`: identity, aggregation, transformation, comparison, fixed-input CLI and external-development-manifest contract tests.
- Minimal upstream integration points and alternatives considered: no production process registration is changed. The runner calls the existing copy-local replay process configuration. Duplicating simulator admission logic or adding a runtime hook was rejected.
- Expected observable effect: a clean fixed candidate and exact approved rlog produce two repeatable native traces; A3 additionally reports downstream raw-output and command-derivative differences. No result is labeled a performance pass.
- Constants / parameters: recorded contract STEER_MAX 409 and raw 3/7 steps per 0.01 s from Carrot `5a970f1a`; candidate contract STEER_MAX 384 and raw 3/7 steps per 0.01 s from the fixed Cyber Hyundai path. Vehicle applicability is the replay-fixed Santa Fe only.
- State initialization, reset, delay assumptions and failure/fallback behavior: a new offline optimizer is created for every A3 transformation. Missing state, invalid command domains, nonfinite output, count/timestamp mismatch, wrong SHA/head/segment, dirty source, a non-development/opened-validation manifest or nonrepeatability fail closed.
- Safety boundaries: `sendcan` messages are counted and discarded; reports fix `sendcan_forwarded=false`, `live_can=false`, `vehicle_write=false`, and `promote_to_active_control=false`. Panda, opendbc, CarController and safety limits are unchanged.
- Upstream synchronization conflicts and maintenance cost: the new tool depends on process-replay message names and `carOutput.actuatorsOutput`; schema or replay orchestration changes may require isolated test updates.

## Regression risk and acceptance

- Potential regressions: excessive memory use from whole-segment loading, altered replay message ordering, accidental state reuse, command-domain scale confusion, raw message disclosure, unsupported variant execution, or evidence output dirtying the candidate checkout.
- Baseline comparison and predeclared acceptance thresholds: A0/A3 repeated output rows, ordered hashes and discarded `sendcan` counts must be identical within each variant. A3 baseline/candidate counts and timestamps must match. Repeatability alone never sets `performance_pass=true`.
- Holdout / scenario coverage and input provenance: one approved development segment is bound by an external private manifest. The manifest supplies the local path, route identity and expected content digest without committing them. Protected holdout inputs remain prohibited and were not accessed.
- Rollback method and last validated configuration: revert the focused runner commit; existing replay seam and production configuration remain unchanged.
- Required reviewer / promotion authority and decision: no active-control promotion. Calibrated closed-loop and separate user authority remain required.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | runner + seam unittest; controls discovery; Ruff; `git diff --check`; SCons in Ubuntu 24.04 / Python 3.12 venv | fixed candidate `b1473ac69`; manifest candidate `706fa6fa25` | PASSED: original runner + seam 12 tests; manifest extension runner + seam 16 tests; controls 132 passed on the manifest candidate; Ruff and diff check clean; SCons exit 0. |
| Replay vs baseline | repository CLI A0 and A3 on fixed segment 29, clean HEAD and exclusive aggregate output | candidate and fixed rlog SHA above | PASSED for repeatability: A0 hash `9ecaa6a3...` twice; A3 hash `c0291a86...` twice; 6,004 outputs and 5,955 discarded `sendcan` per run. A3 changed 25 raw outputs; performance pass remained false. |
| Simulation / closed loop | existing frozen D3Y contract | segment 29 3.19-7.28 m/s vs plant 15-27 m/s | BLOCKED out of domain; this runner does not change that result. |
| Shadow | non-actuating device shadow | not applicable to this offline runner | NOT RUN and not authorized. |

## Handoff

- Verified effect vs expected effect: repository-owned A0/A3 execution exactly reproduced the earlier scratch evidence, including hashes, counts and A3 aggregate metrics.
- Failed, blocked or not-run checks and missing inputs: the original fixed segment remains outside the frozen plant speed domain. In-domain private development replay is kept outside the repository, while a coupled Cyber-controller-to-D3Y adapter is not yet implemented; lane/edge/curve/override performance is not measured.
- Remaining regression risks and next verification: review and approve a fail-closed offline adapter that feeds Cyber A0/A3 controller commands into the frozen D3Y plant with exactly one actuator-delay model before any closed-loop performance claim.
- Commit / PR references: local implementation commits `b1473ac6947ba591cf745b53645068eccb7077d9` and `706fa6fa25c79a9a61afb6b8694e82d12e82019c`; no PR or push.
- Vehicle application decision: not authorized.
