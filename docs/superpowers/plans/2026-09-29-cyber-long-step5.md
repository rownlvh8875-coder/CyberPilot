# Cyber Long Step 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for direct execution after plan/method approval, or superpowers:subagent-driven-development if the user chooses delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 최신 upstream을 변경 최소화로 유지하면서 Cyber Long Phase A의 baseline/관찰-only 연결과 비작동 AutoTune admission 계약을 구현한다.

**Architecture:** stock planner candidates를 immutable observation으로 읽고 기존 min/stop-OR/clipping/LoC/CAN 경로는 유지한다. default는 disabled이며 observation-only도 actuator candidate를 만들지 않는다. Carrot control 코드 복사는 없으며 Phase B 활성화는 별도 근거 gate다.

**Tech Stack:** Python >=3.12.3,<3.13, stdlib dataclasses/enum/math/unittest; 통합 테스트는 기존 numpy/cereal/opendbc/acados 및 tools/test_runner.py.

**Spec:** [승인된 Step 4 설계](../../CYBER_LONG_DESIGN.md). 사용자의 2026-09-29 “STEP5 진행해” 요청은 설계 기반 작업 승인이며, 이 실행 계획과 실행 방식 검토는 아직 대기다.

## Global Constraints

- Preserve upstream layout/history/gitlinks/LFS/schema field meanings and existing interfaces.
- Do not wholesale copy/merge Carrot; source license remains a gate before any code adaptation.
- Do not modify panda/opendbc safety, actuator limits, DM, brake/cancel, engagement, fault handling.
- AutoTune must not change safety limits/models/flags/CAN permissions.
- Hot path has no Params/network/file IO; no device/vehicle writes, deployment or road test.
- No test deletion/acceptance relaxation/automatic replay reference updates.
- Disabled and observation-only retain stock float arithmetic order, candidate ordering, tie behavior, stop OR and feedback.
- Bounds/confidence/evidence not reviewed means admission denied, not unbounded.
- UTF-8/LF, two-space Python indentation, configured Ruff rules; no new product dependency.
- Leave commit-ready local changes. No automatic commit, push, merge or speculative module/daemon.
- Runtime findings, synthetic contract findings, replay, simulation and shadow are reported separately.

## Review Focus

1. Non-winning candidate shouldStop must still participate in the stock OR: Task 2 tests it.
2. Disabled mode must not read new model/provenance fields or fail on observation-only inputs: Tasks 1/2.
3. Invalid/stale/reset/clock reversal/observer exception must not hold a previous diagnostic as fresh or disturb stock output: Tasks 1/2.
4. Published MPC trajectory differs from final target; parity must compare both without redefining schema: Task 2.
5. Wrong vehicle/model/config binding, non-finite proposals, unknown/safety/user-preference parameter must never gain write authority: Task 3.

## 0. Preflight, execution choice and environment

### Verified in this turn

- branch develop; local HEAD c8fb906815530460ed156f14e09e1f312bb0f851.
- All tracked/staged diffs empty. Existing untracked Step 2/3/4 documents are user work and preserved.
- git ls-remote --symref openpilot HEAD: actual default master, c8fb906815530460ed156f14e09e1f312bb0f851.
- git fetch --no-tags --no-recurse-submodules openpilot master: exit 0, FETCH_HEAD unchanged baseline.
- feature/cyber-long is already present at the same baseline; no permanent new branch needed.
- Six gitlinks unchanged and uninitialized. No deeper AGENTS.md found under planned edit directories.
- WSL distro Ubuntu is **Ubuntu 26.04**, system Python **3.14.4**. tools/README.md recommends Ubuntu 24.04.
- Installed uv-managed **Python 3.12.14** satisfies the project Python range. scons/ruff were not found on the inspected WSL PATH.
- Windows Python 3.14 and Ruff exist; their use is auxiliary, not supported openpilot runtime evidence.

### Before implementation

- [ ] User reviews this plan and chooses direct execution or subagent execution.
- [ ] User chooses current checkout on feature/cyber-long or a managed isolated worktree.
- [ ] Recheck status/HEAD/remotes/gitlinks and verify correct base before branch/worktree change.
- [ ] If isolated worktree chosen, use Codex worktree tools, not manual git worktree add. Preserve/carry only authorized local instruction/design documents; never assume an untracked document was copied.
- [ ] No OS/distro replacement/install as an incidental step. A new Ubuntu 24.04 environment requires a separate explicit choice.
- [ ] Portable stdlib contract tests may run on existing WSL Python 3.12.14 with Ubuntu 26.04 **limited-environment** labeling. Full native/replay/build promotion stays unverified until supported environment/dependencies/assets are prepared.
- [ ] Record submodule/model/config/input identities and available assets before native runtime checks. Do not initialize/update gitlinks merely to make a test green.

Recommended execution: direct in this chat, current checkout on feature/cyber-long, preserving all untracked design documents. An isolated worktree is also valid if selected.
No product code has been changed in this planning turn.

## File structure

| File | Responsibility |
| --- | --- |
| openpilot/selfdrive/controls/lib/cyber_long/types.py | Frozen config/context/observation and binding/proposal/result records; no schemas or actuator handles |
| openpilot/selfdrive/controls/lib/cyber_long/policy.py | Disabled/observation-only observer, finite/identity/reset checks, diagnostic ownership |
| openpilot/selfdrive/controls/lib/cyber_long/params.py | Read-only metadata and fail-closed proposal assessment; no Params write/load or CP modification |
| openpilot/selfdrive/controls/lib/longitudinal_planner.py | Minimal constructor option and isolated observer call before existing arbitration |
| openpilot/selfdrive/controls/tests/test_cyber_long.py | Stdlib-only real observer/admission tests, synthetic values explicitly labeled |
| openpilot/selfdrive/controls/tests/test_cyber_long_integration.py | Actual planner/LoC differential tests vs frozen upstream source; native dependency requirements |
| docs/cyberpilot/changes/cyber-long-phase-a.md | Completed feature-change record with actual results and limitations |
| docs/cyberpilot/changes/cyber-long-autotune-admission.md | Separate non-actuating metadata/admission record |
| docs/cyberpilot/analysis/CYBER_LONG_IMPLEMENTATION_VERIFICATION.md | Commands, counts, failures, SHA/patch/input/environment evidence |

No empty package placeholder is necessary: use repository package conventions.
long_mpc.py, longcontrol.py, controlsd.py, card.py, cruise.py, modeld, cereal, opendbc_repo and panda stay unchanged.

## Task 1: Phase A observer contracts and diagnostic lifecycle

**Files:** Create types.py, policy.py and test_cyber_long.py above; add the phase-a feature record before behavior edits.

**Interfaces:**

- CyberLongMode is DISABLED or OBSERVE_ONLY; there is no ACTIVE/comfort mode in this change.
- Frozen CyberLongConfig(mode=DISABLED, configuration_epoch=0); configuration_epoch is an identity counter, not a control constant.
- Frozen StockCandidate(accel_mps2: float, source: str, should_stop: bool); source is diagnostic text, not a new stock enum.
- Frozen LongContext carries candidates tuple; input_valid/reset_state/brake_pressed/gas_pressed/long_active; model/carState/radar monotonic timestamps; v_ego_mps/a_ego_mps2/v_cruise_mps; force_decel/personality; vehicle/config binding.
- Frozen LongObservation records current input identity, stock winner source/acceleration, stock stop OR, mode and accept/reset reason. It does not represent a final actuator target.
- CyberLongPolicy(config: CyberLongConfig) owns last_observation and monotonic identity state.
- CyberLongPolicy.observe(context: LongContext) -> None never returns or writes an actuator candidate.
- CyberLongPolicy.reset(reason: str) -> None clears prior observation and timestamp/binding state. No callbacks, network, Params or file IO.

No new numeric freshness threshold: use current upstream validity checks and monotonic/new-sample checks. Failure resets diagnostics, not stock control.
Model timestamp must strictly increase; carState/radar timestamps must not reverse. Equal radar/carState timestamps can be normal asynchronous reuse when upstream checks remain valid; do not reject that as a duplicated model frame.
Unsupported/unknown provenance is marked incomplete rather than fabricating a model/firmware SHA. These observations cannot qualify empirical evidence.

- [ ] **Step 1: Write behavior tests first.**
  - test_disabled_bypasses_observation: last_observation None, candidate tuple unchanged;
  - test_observation_has_no_actuator_authority: hand-derived winner/OR, observe returns None;
  - test_invalid_context_clears_previous_observation: empty/NaN/Inf candidate or input_valid=False clears state;
  - test_driver_or_stock_reset_clears_observation: brake/gas/long-inactive/reset clears prior observation;
  - test_replayed_or_reversed_model_time_resets: duplicate/reversed model timestamp cannot retain fresh diagnostics;
  - test_asynchronous_radar_reuse_is_not_model_replay: same valid radar/carState timestamp with a new model is allowed;
  - test_binding_change_resets_observation: changed vehicle/config binding clears old-identity state;
  - test_context_and_config_are_immutable: mutation raises FrozenInstanceError.
- [ ] **Step 2: Run RED using WSL Python 3.12.14.** Missing new API is expected; native dependency/import failure unrelated to the API is environment failure, not RED evidence.
- [ ] **Step 3: Implement only these contracts/lifecycle.** No comfort algorithm or delay/gain override.
- [ ] **Step 4: Run new tests GREEN and configured Ruff.** Expected no failed contract tests; count exact tests/subtests and name any errors.
- [ ] **Step 5: Record results and leave focused diff commit-ready.** No commit unless requested.

Hand-derived observer fixture:

```python
candidates = ((-0.4, "lead0", False), (0.2, "cruise", True))
# Observation: winner lead0 / -0.4, should_stop True; actuation candidate always None.
# A tie [lead0=-0.4, cruise=-0.4] preserves the first stock source.
```

Test names must catch a missing reset, a stale observation, input mutation or accidental actuation—not mere source text changes.

## Task 2: Minimal planner seam and baseline connection/parity

**Files:** Modify longitudinal_planner.py only among upstream runtime files; create test_cyber_long_integration.py; update phase-a record.

**Consumes:** Task 1 config/context/policy contracts.
**Produces:** LongitudinalPlanner(CP, init_v=0.0, init_a=0.0, dt=DT_MDL, *, cyber_long_config=None), backward-compatible existing positional arguments.

- [ ] **Step 1: Add failing integration tests.**
  - Default-disabled and explicit OBSERVE_ONLY produce identical planner control outputs/state to frozen upstream for the same message sequence.
  - Acc/experimental modes, lead present/loss/brake, stop/go, forceDecel, pitch/coast/throttle, turn limiting, unset cruise, reset and tie cases.
  - Non-winning stop candidate still sets stock stop OR. Example candidates [-0.4/False, 0.2/True] yield -0.4 and True.
  - Observer invalid-input/reset does not change aTarget, shouldStop, source, FCW, allowThrottle or MPC trajectories.
  - Inject an observer RuntimeError at the optional boundary; current stock outputs remain baseline-identical, diagnostic cleared and fault recorded.
  - Feed baseline and modified planner targets to the same real LongControl and compare accel/state over stop/start sequences.
- [ ] **Step 2: Run RED against the real planner when dependencies are available.** A missing solver/cereal/native import is recorded BLOCKED, never substituted with a fake runtime PASS.
- [ ] **Step 3: Add minimal seam.**
  - Construct independent policy; default disabled avoids new context fields/read/check work.
  - With OBSERVE_ONLY, freeze the stock candidates and build observational context after stock candidates exist, before the existing min/OR/clipping/feedback.
  - Pass source as diagnostic str only, never rewrite stock candidates/source enum.
  - Isolate optional observer failures from stock calculation; record fault/reset without external IO.
  - Keep original min/OR/clipping and float arithmetic untouched; no observer result is consumed by actuator planning.
- [ ] **Step 4: Run parity and upstream tests.** Require exact control scalar/state equality and np.array_equal for trajectories in deterministic runs. Nondeterministic wall-clock/solver timing fields are identified in advance, not silently ignored.
- [ ] **Step 5: Record diff/commands/counts and leave commit-ready.**

Baseline oracle: git object c8fb906815530460ed156f14e09e1f312bb0f851, original planner and LongControl, same inputs/config/solver.
Load actual frozen upstream source in a test-only namespace; retain MIT attribution.
Do not compute expected output through the modified helper. Controlled arbitration fixtures may isolate the boundary, but are not whole-native-planner validation.
The test fixture may create test-local cereal data; it must not open sendcan or apply vehicle controllers.

Phase A completion requires the native connection/parity checks above. If only independent unit checks run, report **implementation with integration verification pending**, not Phase A fully validated.

## Task 3: Phase C non-actuating metadata/admission boundary

**Files:** Add params.py, extend types.py/test_cyber_long.py, create autotune-admission feature record.
**Consumes:** frozen binding/config contracts, stock CP observations.
**Produces:**

- ParameterMetadata: name/unit/source/default/vehicle_specific/category/online_allowed/offline_allowed/min/max/rate_of_change_limit/confidence_requirement/safety_related/read_only.
- ParameterProposal: name/value/unit/binding/evidence identity/confidence.
- assess_tuning_proposal(proposal: ParameterProposal, expected_binding: ParameterBinding) -> ProposalAssessment.
- ProposalAssessment is immutable and **accepted=False** for every proposal in this initial version; reason distinguishes unknown/forbidden/non-finite/binding mismatch/unreviewed bounds/tuning disabled.
- Registry owns metadata and cannot be replaced by caller-supplied permissive metadata.
- The observer can expose stock metadata/binding for offline consumers; admission results have no link to CP/Params/CAN writes.

- [ ] **Step 1: Write failing admission tests:** NaN/Inf, wrong units, missing/mismatched model/vehicle/config identity, unknown name, safety and user-policy name, null bounds/rate/confidence, forged permissive metadata.
- [ ] **Step 2: Run RED for missing API only.**
- [ ] **Step 3: Implement read-only metadata and rejection assessment.**
  - Never introduce active tuning or assume UI bounds are validated.
  - Physical delay and current-controller gains are research metadata, not live overrides.
  - Safety/engagement/CAN/DM/takeover and user personality/headway have no writable admission.
  - Do not port Carrot speed-PID units, RadarReactionFactor or global LongActuatorDelay.
- [ ] **Step 4: Run GREEN and regression.** Every proposal rejected; no state/config/control change from assessment.
- [ ] **Step 5: Complete feature record and leave commit-ready.**

This is a real fail-closed offline interface, not an empty future module.
Phase C's offline admission contract may be exercised without enabling Phase B, because it has zero actuator authority.
Online learning and accepted parameter application remain separate designs/approvals.

## Task 4: Whole change verification and handoff

**Files:** verification document and existing change records only, plus local outputs handoff.

- [ ] Run new portable contract suite using installed WSL Python 3.12.14; mark Ubuntu 26.04 as limited environment.
- [ ] Run native integration and affected upstream controls tests when prepared; otherwise report exact BLOCKED/NOT RUN reasons.
- [ ] Run project runner without targets in prepared environment; full unit results do not cover replay/sim.
- [ ] Run configured Ruff, diff whitespace checks including new files, Python3.12 syntax/import checks and link/scope checks.
- [ ] Compare baseline pin identities and byte/hash preservation of all prohibited-change files and prior documents.
- [ ] Bind evidence to Git SHA plus uncommitted patch/file hashes; record environment, commands, exit codes, test counts and synthetic input identity.
- [ ] Whole-change review after tests: direct mode still uses one fresh reviewer at end if chosen under executing-plans; no code reviewer before implementation in this planning turn.
- [ ] Report A implemented/verification status, B deferred gate, C non-actuating status separately. Do not claim all Step 5 phases complete when B/native verification remain pending.
- [ ] No commit/push/deploy/vehicle operations.

Expected commands, from repository root in a properly prepared environment:

```bash
python tools/test_runner.py openpilot/selfdrive/controls/tests/test_cyber_long.py
python tools/test_runner.py openpilot/selfdrive/controls/tests/test_cyber_long_integration.py
python tools/test_runner.py openpilot/selfdrive/controls/tests
python tools/test_runner.py openpilot/selfdrive/test/longitudinal_maneuvers/test_longitudinal.py
python tools/test_runner.py
scons -u
python openpilot/selfdrive/test/process_replay/test_processes.py --whitelist-procs plannerd controlsd radard
```

Replay requires approved inputs/model/config and supported native environment; it is not replaced by synthetic messages.
Closed-loop simulation and non-actuating shadow follow replay. No device/live shadow run without separate target authorization.

## Phase B gate — no implementation in this initial plan

No evidence-qualified Carrot cut-in improvement exists yet in the Step 4 findings.
Comfort activation needs license/source confirmation, target vehicle/firmware, reviewed numeric
bounds/acceptance, fixed baseline replay and closed-loop evidence.
The user's Step 5 request does not erase the approved design's evidence gates.
Do not add a dormant copy of unqualified Carrot control code to suggest B is implemented.
After Phase A/contract results, recommend one specific comfort experiment if its required inputs exist.

## Self-review and handoff

Spec coverage: initial A and non-actuating C have concrete tasks; B is explicitly deferred by the design.
No controller/stop-authority/CAN changes are hidden in observer/admission interfaces.
Task 2 uses Task 1 exact names/types; Task 3 consumes the same immutable binding identity.
Unknown model/firmware provenance fails qualification rather than masquerading as a known value.
Native parity and full suites cannot be claimed from portable tests. Current environment gaps remain explicit.
No implementation, dependency installation, submodule initialization, branch change or commit has occurred in this planning turn.

Please review this plan and choose execution:
1. Direct execution in this chat (recommended), current checkout on feature/cyber-long; optional managed isolation if preferred.
2. Subagent execution with review gates; execution/worktree choice must be explicit before dispatch.
