# Replay input snapshot admission

## Identity and purpose

Cyber Validation / AutoTune, implemented local component; runtime integration pending.
Branch feature/cyber-autotune, base 1ee1eb07f6cc48526f4d61265abe317fe67cc23b;
uncommitted addition. Checks a separately granted development input before a future
torqued replay launcher. Vehicle-agnostic infrastructure; no actuator authority.

## Original references

CyberPilot https://github.com/rownlvh8875-coder/CyberPilot, current local branch/base
above, existing native_runner.py and source_imports.py. Recorded-source checkout
f5fd296cd1286f0b833d874eea4245bfe31dce81 was inspected at
openpilot/selfdrive/test/process_replay/process_replay.py (ProcessContainer,
get_car_params_callback, generate_params_config, generate_environ_config),
openpilot/common/prefix.py and openpilot/selfdrive/locationd/torqued.py.
No Carrot algorithm or third-party code copied; original project licensing retained.
No submodule revision, model, dependency lock, controller or upstream file changed.

Observed path: replay migration -> CP extraction -> Params prepopulation ->
get_car callback -> torqued constructor/cache restore -> runtime cache writes.
This motivates explicit CP/cache declarations and isolation before execution.

## Changes and effect

- replay_admission.py: inspect_replay_input(request, grants, authority_sha256)
  validates strict request/grant/state metadata before opening input bytes;
  hashes descriptor-opened regular files with symlink refusal and resource bounds;
  checks Git root/HEAD, tracked/index cleanliness, gitlinks and selected file hashes.
- tests/test_replay_admission.py: synthetic file/Git and initialization cases.
- No call site enables this API in runtime. The output always has replay_allowed,
  runtime_accepted and promotable set to False.

Bounds: 512 MiB per input, 64 MiB per selected source artifact, 256 selected source
files, 10,000 grants, 64 inspected repositories, 15 s per Git operation and 1 MiB
hash chunks. These are operational resource limits, not vehicle/metric thresholds.
Protected segments 53/71 and non-development roles are refused.

Recorded cache timestamps must precede run start; explicit reviewed-empty mode
requires absent cache fields. Review hashes and original/migrated/initialized CP
hashes are caller declarations. Their physical truth and clock identity are not
certified by this API. No random seed or first/last cache is chosen automatically.

Read-only Git checks disable fsmonitor and reject configured clean/process filters
before status. Submodule status is inspected explicitly after the same config gate
instead of asking Git to recurse into unchecked configurations.

## Regression and acceptance

Risk: a local grant can be mislabeled by its producer; authentication and adaptation
of approved private manifests remain separate. A verified snapshot can change after
return; the future launcher must reverify/retain an immutable admitted input.
Selected file hashes do not establish full runtime closure. Uninitialized gitlinks
or executable filters fail closed. Source is trusted local code, not hostile code.
No metric, holdout, acceptance threshold or reference changed.
Rollback: remove the unintegrated new module/tests/record; no runtime state migration.

## Verification

Ubuntu-24.04, Python 3.12.13, D-backed WSL. New module initially missing (RED).
10 initial tests passed; independent review exposed root discovery, fsmonitor,
exception path disclosure and clean-filter execution including nested repositories.
Five added regressions failed before fixes, then all 15 tests passed.

| Check | Actual result |
| --- | --- |
| New admission tests | PASS, 15 tests |
| tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests | PASS, 393 tests, 14.12 s, exit 0 |
| Ruff new module/tests; git diff --check | PASS |
| Independent read-only review | Important findings fixed with RED -> GREEN tests; no deferred minors |
| Full default PC suite | NOT_RUN this unit; earlier unrelated timeouts remain historical |
| Real replay / closed loop / shadow | NOT_RUN |

Separately, a work-only synthetic namespace/chroot feasibility probe passed twice:
read-only source/input, hidden host drives/unrelated homes/devices, dropped
capabilities, failed remount, private Params, and two exact module imports.
The probe is not a production launcher or replay qualification.

## Handoff

Implement and test the namespace launcher lifecycle next, then connect an exact
torqued adapter and capture actual original/migrated/initialized CP and cache epoch.
Input authority adapter must preserve existing protected roles. No real log was
read in this unit; no active profile, vehicle command, commit, push or merge.
Overall STEP 8-10 remains PARTIAL / NOT_READY.
