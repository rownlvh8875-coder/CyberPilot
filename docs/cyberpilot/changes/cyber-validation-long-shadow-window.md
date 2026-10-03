# Cyber Validation longitudinal offline shadow windows

## Identity and purpose

- Area: Cyber Validation/STEP10. Status: scheduler integrated; package/affected tests
  and independent review passed; post-extension whole-PC pending.
- Scenario: compare an immutable active requested-acceleration trace against an
  isolated native LongControl candidate using bounded offline complete windows.
- Excludes continuous/device shadow, actuator/brake commands, profile application,
  raw-log extraction, tuning, plant/physical confidence or vehicle qualification.
- feature/cyber-autotune, baseline/HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b;
  local uncommitted long_shadow.py/tests and shared shadow.py dispatch hooks.

## Original references

- CyberPilot https://github.com/rownlvh8875-coder/CyberPilot at the exact HEAD above;
  native openpilot MIT LongControl, own reviewed offline shadow scheduler and runner.
- openpilot/selfdrive/controls/lib/longcontrol.py:LongControl/long_control_state_trans;
  tools/cyber_autotune/native_long_protocol.py, native_long_runner.py and shadow.py.
- Inputs: immutable source-bound CP + exogenous frames → fresh native LongControl
  process → requested accel/state rows → aggregate comparison, never vehicle transport.
- opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged. Synthetic HKG fixture
  is not actual vehicle/firmware/model qualification; no new dependencies/fork copying.
- Reuse lifecycle and native source behavior; adapt only axis-specific contracts.

## Changes and expected effect

- long_shadow.py: admission, exact native response validation, m/s² diagnostics,
  complete comparison stripping on expiry; LongShadowSession built-in subclass.
- shadow.py: private decode/prepare/diagnose/expire/scope hooks, unchanged
  public methods and default lateral behavior. New tests cover axis/binding/faults.
- Alternatives rejected: duplicated scheduler or public arbitrary execution callbacks.
- Expected: isolated accel difference observations with bounded queues, not performance
  improvement. Constants reuse native PID envelope(-3.5,2)m/s² and supervisor bounds;
  no safety threshold or new parameter value is introduced.
- Each window resets native state. Same frames/fingerprint/control owner across arms;
  candidate source/CP identity fixed per session. Different sources/CP explicit.
- One running/one pending/one result; timeout/expiry/errors have no comparisons.
  close waits outside active loops. No hard real-time or hostile-source containment.
- No controller, CarController, Panda, opendbc, Params or CAN changes. Sync risk
  limited to offline scheduler dispatch; old lateral suite must remain unchanged.

## Regression risk and acceptance

- Risks: wrong-axis dispatch, changed longitudinal ownership, stale/forged response,
  expiry exposing old metrics, lifecycle race or mislabelled requested-stage quantities.
- Require native-equal zero difference, hand-derived nonzero m/s² differences,
  complete metric stripping on failure/expiry and old lateral tests unchanged.
- Scope: synthetic inputs only; no holdout/real log access or physical thresholds.
- Rollback: stop using this offline subclass; active controller remains unchanged.
- One independent review after implementation; no vehicle promotion from any result.

## Validation method and actual results

| Stage | Method/evidence | Actual status and limits |
| --- | --- | --- |
| TDD | new test_long_shadow.py | missing-module RED, then pre-hook RED11fail/2pass/12subtests1.05s; shared-hook fix GREEN |
| Ruff | full package; git diff --check | PASS after integration |
| Lateral+long shadow | pytest old/new test modules |17passed35subtests2.95s,exit0; original tests unchanged |
| Package/controls regression | pytest AutoTune; tools/test_runner.py AutoTune+controls |242passed765subtests27.05s;374passed14.42s; both exit0 |
| Actual native synthetic windows | current-as-candidate,11frames,3windows/4nativeprocesses | zero requested-accel/state difference, repeated trace; no candidate improvement |
| Independent review |17focused/35subtests2.73s plus6negative probes |0Critical/0Important/0newMinor; existing terminal buffered-drop counter minor retained |
| Whole PC | existing13540,1348collected | RUNNING pre-extension, cannot verify this module |
| Qualified replay/closed loop | no new candidate/plant | NOT_RUN |
| Continuous/device shadow | no active transport integration | NOT_RUN |

## Handoff

- Sequencing ruling:13540 already completed all9 old shadow tests and only lagd was
  active; shared hooks applied without restarting it. Retain13540 as PRE_EXTENSION
  evidence, never post-extension whole-suite verification.
- Focused tests establish offline window integration, not successful vehicle shadow.
- Missing physical inputs, continuous state ownership, latency/non-interference,
  actual brake/safety proximity and qualified profile evidence remain external gates.
- No commit/PR, device connection or vehicle application. Overall PARTIAL/NOT_READY.
- Review exclusions: whole-PC parent-owned; supplied trace/source authenticity not
  proven by hashes; continuous ownership/latency/device cleanup/hostile mutation,
  vehicle/physical metrics/replay/plant/profile promotion remain unqualified.
  Existing terminal BaseException buffered-result drop counter remains deferred;
  closed/terminal_fault is visible, and this extension does not change that behavior.
