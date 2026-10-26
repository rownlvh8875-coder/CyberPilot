# Cyber Long replay preparation and qualification gates

Status: preparation only, 2026-09-29. No qualified Cyber Long process replay,
vehicle-specific closed-loop or shadow run was performed by this preparation.
Phase B remains unimplemented. No active control, safety or acceptance change.

## Frozen source and intended evidence

- Repository baseline: `c8fb906815530460ed156f14e09e1f312bb0f851`.
- Candidate: existing uncommitted Phase A/C source, identified by the eight
  file SHA-256 values in the local preparation manifest. HEAD alone is insufficient.
- Preserve all six baseline submodule pins; use the prepared native Ubuntu 24.04
  environment, not Windows Python or an incidental mounted source package.
- Reference rules: [implementation verification](CYBER_LONG_IMPLEMENTATION_VERIFICATION.md),
  [design](../../CYBER_LONG_DESIGN.md),
  [process replay instructions](../../../openpilot/selfdrive/test/process_replay/README.md).
- Bind each future run to source/submodule/model/configuration hashes, actual
  environment, input byte hashes, start/warm-up masks, commands, exits, nonzero
  expected case counts, output hashes and isolation evidence.
- Never commit private routes, CAN/GPS/video, configuration or simulator evidence.
  A private validation repository may consume an explicitly frozen source tree;
  its code and empirical evidence are not authorized for public import.

## Current upstream runner behavior

Sources at the baseline are `openpilot/selfdrive/test/process_replay/test_processes.py`,
`process_replay.py` and `compare_logs.py`. Read actual config and dispatch logic
before choosing commands. README route examples alone do not define the matrix.

- With `radard`, `plannerd`, `controlsd` and all default car labels, this revision
  schedules 20 component cases: 16 controlsd plus two each for radard/plannerd.
- The car whitelist uses fixture labels, not arbitrary opendbc fingerprints.
  `HYUNDAI_SANTA_FE_2022` matches zero listed fixtures at this revision.
  Empty results must be rejected even if the CLI exits successfully.
- The regular CLI replays processes independently. Its controlsd case consumes
  the recorded longitudinalPlan, not the plan just emitted by another test.
  Component regression therefore does not prove the new longitudinal call chain.
- The multi-process replay API can route new internal outputs between processes.
  This still is software replay, not a vehicle-response closed-loop simulation.
- Default plannerd constructs the existing planner in DISABLED mode. Running the
  stock CLI does not enable OBSERVE_ONLY or establish observer non-interference.
- Stock comparison ignores/tolerances remain unchanged. Do not use update-refs,
  additional ignores or threshold relaxation to make a mismatch pass.
- Output names based on HEAD do not distinguish uncommitted candidates. Use
  separate immutable run directories plus explicit candidate/input identities.
- Logged modelV2 is not newly executed modeld inference. Preserve this distinction
  in the report; do not claim camera/model provenance from planner replay alone.

## Public input metadata preflight, not replay

The observed process-replay artifact branch was
`eab2cc2b1f6de3773617937868442520c7ef554c`; its pinned ref_commit contents name
the same `c8fb906815530460ed156f14e09e1f312bb0f851` baseline.
The small ref_commit file was fetched and validated. HTTP HEAD checks succeeded
for two public input routes and six corresponding component reference files.
Neither input bytes nor reference-log bytes were downloaded by this preflight.
URL, length or ETag alone is not a frozen content identity.
These generic public Hyundai/Toyota fixtures are not the target vehicle's logs.

## Ordered gates before behavior implementation/promotion

1. Freeze actual target CarParams, firmware/source revision, recorded model and
   settings, and authorized development routes. User vehicle descriptions or
   supported model names cannot establish openpilotLongitudinalControl or radar
   availability. Preserve sealed holdout; do not consume it for development.
2. Acquire and hash authorized inputs and exact references into isolated local
   storage. Confirm expected cases and warm-up requirements before execution.
3. Replay baseline against itself with fresh process state (A/A), then the
   default-disabled candidate. Investigate nondeterminism before comparison.
4. Approve a test-only observer injection and replay full process OFF/ON with
   identical input order, timing and warm-up. Observe existing values without
   extra solver/getter/clock calls. Compare controller outputs, message counts,
   ordering, state transitions and reset behavior. Diagnostic counters must not
   feed controls. Exact non-interference and stock-reference tolerances are
   distinct checks; do not substitute one for the other.
5. Run coupled radard/plannerd/controlsd development replay with preserved
   schema meanings and explicit output routing. Keep hardware/CAN writers out
   of the process set. Archive fresh identity-bound receipts and differences.
6. Qualify the external longitudinal plant's calibration/input boundary, delay,
   vehicle domain and timestep before closed-loop testing. Planner acceleration,
   LongControl output and vehicle actuator commands are not interchangeable.
7. Only after replay, run reviewed vehicle-specific closed-loop cases; then
   non-actuating shadow under separate explicit device/vehicle authority.

## External simulator interface requirements (not an implemented adapter)

Keep the world/lead scenario separate from the vehicle plant and controller.
An adapter must state which acceleration/actuator boundary it consumes, SI units,
sample times, delay ownership, resets, saturation, failure paths and calibration
provenance. Do not count delay or gas/brake compensation twice.
Reject incompatible schemas, non-finite/stale inputs and out-of-domain requests.
Synthetic fallback or teacher forcing cannot qualify real dynamics or tuning.
Report their use explicitly; never silently treat such steps as closed-loop data.
Define requested and executed horizon and reject silent empty/partial runs.
Version-specific Carrot replay producers cannot be plugged into this baseline
without mapping actual message fields and validating their consumer meanings.

## Metrics and acceptance authority

For observer parity, compare actuator/plan outputs, shouldStop transitions,
publication order/count, state and resets. For later behavior evaluation record
speed/acceleration/jerk, follow gap/headway, lead transitions, stop position,
restart latency, saturation, intervention, plant-domain violations and phase lag.
Define units, derivative filtering, valid masks and event denominators first.
These are proposed measurements, not proven improvements or numeric acceptance.
Use existing reviewed criteria unchanged where applicable. Missing criteria or
calibration is an incomplete gate, not PASS; safety limits are never AutoTune.

## Remaining inputs and authority

Target raw logs/runtime configuration, actual longitudinal mode, calibrated plant
and model identities, observer adapter approval and qualification criteria remain
unestablished. Existing private synthetic/CI summaries are not fresh execution
evidence for CyberPilot. No private result is promoted, no branch is restored,
and no source import, deployment, road approval or commit/push is performed here.
