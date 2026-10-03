# Exact-source initial-state observation

## Identity and purpose

Cyber Validation / AutoTune. Separate observation schema implemented; fixed
exact-source adapter remains a private work artifact, not a production replay
launcher. feature/cyber-autotune HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus
uncommitted work. Purpose: learn unknown CP/cache facts without fabricating the
expected hashes required by the earlier replay admission contract.

## Original references

CyberPilot https://github.com/rownlvh8875-coder/CyberPilot, branch/HEAD above;
recorded Carrot local checkout at f5fd296cd1286f0b833d874eea4245bfe31dce81,
openpilot/selfdrive/test/process_replay/process_replay.py and migration.py,
openpilot/selfdrive/locationd/torqued.py, opendbc_repo/opendbc/car/car_helpers.py,
hyundai/interface.py. Existing source provenance is retained; no upstream/fork
algorithm copied or modified. Existing project/source licenses remain applicable.

Observed native call path: admitted compressed input -> exact schema events ->
recorded CP -> migrate_all -> generate_params_config/generate_environ_config ->
private Params -> exact get_car_params_callback -> regenerated CP. The callback
consumes recorded CAN and supplies inert send callbacks; no live transport or
process replay is started. torqued constructor/sampling/learning remain NOT_RUN.

## Changes and expected effect

- replay_admission.py: separate strict OBSERVE_INITIAL_STATE request schema,
  sharing unchanged grant/source gates; no expected initial-state fields.
- replay_input.py: retain_observation_input delegates to the same sealed-copy
  implementation. Observation receipt carries its purpose and no authority.
- tests/test_replay_input.py: observation cannot enter replay API; fabricated
  fields/unsupported purpose/protected roles or segments rejected before opens.
- Private D work adapter: exact readonly source/runtime namespace, bounded zstd
  and framing checks, source identity verification, original/migrated/initialized
  CP hashes/flags, recorded cache inventory and aggregate-only output validation.

No adapter/runtime selection API is exposed in product. Work adapter preserves
the prior source/namespace boundaries. No raw CP, CAN, GPS, video or Params value
export; only hashes, selected control-mode booleans, counts and cache timestamps.
All runtime/candidate/replay/promotion flags stay false. A callback error leaves
initialized_cp=None and initialization_status=BLOCKED, never copies expected CP.

Resource limits:64MiB compressed input,256MiB decompressed bytes,250000 messages,
512 segments per Cap'n Proto table,32 CP/cache rows,60s child deadline,64KiB
combined captured output. These are infrastructure limits, not metric acceptance.
Compressed EOF is independently checked after bounded decode; truncated streams
are never salvaged. Current adapter explicitly rejects multi-frame/trailing data.
Second pass uses identical sealed input and compares decompressed size/hash;
temporary expanded output can add up to the bounded decompressed size in memory.

## Regression risk and acceptance

Same canonical protected-role/segment/source/file checks as earlier admission.
Observation and replay schemas are intentionally not interchangeable. Existing
v1 replay initial-state validation and acceptance thresholds remain intact.
Risk: default native Params differs from the recorded driver/configuration state;
the adapter must expose that difference rather than repair it silently.
Cache timestamp comparison cannot prove clock continuity. No cache is selected
or seeded into a learner. Empty values are distinguished from absent values.

Rollback: revert this small product schema extension and remove private adapter;
there are no runtime control call sites or active profile migrations. No commit,
push, merge, deployment or device/vehicle change authorized/performed here.

## Validation method and actual results

| Check | Result |
| --- | --- |
| Observation schema RED -> GREEN | Missing API ->22 admission/input tests55subtests PASS |
| Private framing/report tests | PASS3 tests; rejects checksum-truncated and complete-message-prefix-truncated zstd, trailing/multiple frames and forged authority |
| Synthetic native integration | PASS; CP migration distinguished; missing CAN correctly BLOCKED; cache inventory present but chronology unqualified |
| Affected product runner AutoTune+controls | PASS417 tests; final execution recorded in D work verified log |
| Ruff changed product/work files; bash syntax; diff whitespace | PASS |
| Independent review | 1Important compressed EOF gap reproduced by two failing regressions, fixed; no new Minor |
| Three authorized real inputs, each twice after fix | PASS observation repeatability; see findings below |
| Qualified replay A/A / closed loop / shadow | NOT_RUN; state equivalence gate BLOCKED |
| Full default PC suite | NOT_RUN this increment; earlier unrelated environment limitations unchanged |

Real input authority: SHA-bound step8-eight-binding-20261002.json and authorized
development intake manifest, canonical membership plus reserved/ambiguous/protected
rules before file open. Only previously verified source-A development segments
6,13,19 were read; source-B and all protected inputs excluded. Raw logs unchanged.

| Segment | Event count | Repeatable | Recorded vs migrated CP | Initialized vs migrated CP |
| --- | ---: | --- | --- | --- |
| 6 |84239|Yes|Same|Different|
|13 |83270|Yes|Same|Different|
|19 |83302|Yes|Same|Different|

At least one semantic difference exists in all three: radarUnavailable changes
False -> True in native initialization. openpilotLongitudinalControl=True and
pcmCruise=False are unchanged; fingerprint and torque tuning still match expected
identity. This is an initialization discrepancy, not proof of a vehicle radar fault.
Other fields were not exhaustively diffed by this initial aggregate adapter.

Recorded initData contains CarParamsPrevRoute(1280bytes) and an empty
LiveTorqueParameters(0bytes) in all three. Cache chronology and actual torqued
restore/internal state remain unqualified; no learner was constructed.

Source investigation: Hyundai interface lines176-185 depends on CAN fingerprint,
DBC and private Params EnableRadarTracks/HyundaiCameraSCC. The default replay
parameter builder does not reconstruct those recorded settings. This is a concrete
missing-state avenue, not yet a proven attribution of the observed discrepancy.

## Review rulings and handoff

Work-only adapter was chosen to constrain runtime selection; cost is reusable
product packaging remains pending. Grant authenticity, whole dependency/build
closure, host/kernel trust and scientific cache chronology are not certified.
Qualified replay/vehicle readiness remains a separate required gate. Existing
~2MiB transient-copy-buffer Minor remains deferred, with no new Minor findings.
The pre-fix raw observation reports are retained as historical results, not final
acceptance evidence; compressed-EOF-verified reruns reproduced the same observations.

Next: inventory the specific recorded settings read by native initialization and
separate their effect from the reconstructed CAN fingerprint. Define reviewed
initialization/cache/sampling contracts before replay. Do not force radar flags,
seed an assumed cache or alter acceptance to match expected output.
Overall STEP8–10 PARTIAL / NOT_READY.
