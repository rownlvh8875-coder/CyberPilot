# Bounded replay process lifecycle

## Identity and purpose

Cyber Validation / AutoTune, local implementation; reviewed with fixes verified.
Branch feature/cyber-autotune, HEAD 1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus
uncommitted files. Offline Linux infrastructure, not vehicle-specific control.
This increment supplies lifecycle supervision for the upcoming replay coordinator.
It does not connect the admission receipt to native replay or authorize input use.

## Original references

CyberPilot https://github.com/rownlvh8875-coder/CyberPilot, branch/HEAD above:
openpilot/tools/cyber_autotune/native_runner.py existing owned-group helpers and
replay_admission.py's non-authoritative snapshot contract. No fork controller
logic copied; original repository license applies. Dependency locks, models,
submodules and upstream source remain unchanged.

Caller -> private trusted argv -> new process session -> bounded pipe/deadline ->
group SIGKILL/exit confirmation -> leader reap -> diagnostic outcome. Callers must
use a separately verified PID namespace launcher to contain setsid descendants.

## Changes and expected effect

- New replay_supervisor.py: bounded combined stdout/stderr, closed stdin,
  monotonic timeout, cleanup on normal/nonzero/timeout/output overflow/exception.
- New tests/test_replay_supervisor.py: real synthetic subprocess lifecycle tests.
- Existing native_runner.py and its consumers are unchanged.
- WNOWAIT observes leader exit without freeing its PID; signal and confirm owned
  group exit before reaping. Cleanup confirmation failure overrides success.
- Captured bytes are untrusted/private; this helper never publishes or logs them.
  No automatic retries, payload execution API, active runtime hook or Params use.

Infrastructure ceilings: 60 s deadline, 4 MiB combined capture, 64 KiB reads,
20 ms poll intervals, 1 s group confirmation (existing helper), 1 s reap wait.
These are not control limits, acceptance tolerances or hard-real-time guarantees.
OS spawn/kernel stalls and process enumeration cannot promise hard deadlines.

The helper rejects nondefault SIGCHLD dispositions before launch. Its caller must
preserve the default disposition and sole-waiter ownership throughout the run.
One KeyboardInterrupt during termination/confirmation/reaping is preserved while
cleanup completes, then propagated; repeated interruptions and supervisor
SIGKILL/interpreter crashes are outside ordinary Python cleanup guarantees.
The helper owns its child and must be its sole waiter. It is not a hostile-code
sandbox. Namespace containment is a separate layer, tested operationally below.
No controller, safety, override, CAN, vehicle parameter or activation path changed.

## Regression risk and acceptance

Risks: descendant-held pipes, output floods, interrupt cleanup, PID reuse,
unconfirmed kernel exit, source/runtime drift at the future coordinator boundary.
Acceptance: no truncated-output success; invalid bounds refuse before Popen;
owned descendants absent/zombie and unrelated child alive at return; exceptions
clean before propagation; exact cap accepted, extra byte rejected.

All inputs are synthetic child code/marker. No raw log, protected role, holdout,
reference or scientific acceptance changed. Rollback: remove these unintegrated
files, with no runtime state migration. Independent reviewer required before
handoff; user delegated routine implementation, not vehicle promotion.

## Validation method and actual results

Ubuntu-24.04, Python 3.12.13, D-backed WSL. New tests initially failed because the
module was absent, then passed after implementation. Follow-up fault cases cover
interruption and cleanup confirmation failure. One synthetic operational failure
was caused by stripped PATH omitting /usr/sbin/chroot; adding that directory to
the work-only harness fixed exit 127 without broadening jail mounts/permissions.

| Check | Actual result |
| --- | --- |
| pytest test_replay_supervisor.py | PASS, final 12 tests / 18 subtests, 1.11 s |
| tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests | PASS, final 405 tests, 14.32 s, exit 0 (pre-review 403 tests, 14.36 s) |
| Ruff new module/tests; git diff --check | PASS |
| Operational PID namespace setsid descendant cleanup, normal and timeout | PASS twice |
| Existing exact-f5fd296c synthetic containment probe under new supervisor | PASS twice, 307 output bytes, SHA256 9903ce1d2f7f1f5b2f5224993329cea7926ada2b9a1e7c801ef1111073549ac1 |
| Independent review | Two Important findings reproduced RED, fixed GREEN; no deferred minors |
| Full default PC suite | NOT_RUN this increment; prior unrelated environment/timeouts not resolved by this change |
| Real replay / closed loop / shadow | NOT_RUN |

Probe checks exact process_replay/torqued imports, read-only source/input, hidden
host drives/devices, dropped capabilities, remount refusal and private synthetic
Params roundtrip. Neither module import nor namespace lifecycle is a replay PASS.

Review findings: SIGCHLD=SIG_IGN could auto-reap before group signaling; custom
handlers could also violate ownership. Regression now rejects both before Popen.
A single interruption at cleanup entry left a sleeping child alive. Regression
now verifies cleanup retry and direct-child reap before interruption propagation.
Both fixes were followed by the full affected suite above; no second review was
substituted for these tests.

Review scope rulings: admission/native adaptation and scientific qualification
remain deferred, not waived; process-group escape requires the separate namespace
layer; the prior probe is operational evidence, not hostile-code security proof;
OS hard deadlines/crashes/repeated interrupts remain explicitly unsupported;
private argv/environment, stable signal disposition and sole waiter are trusted
caller obligations. Whole-suite/lint claims rely on recorded main-agent execution,
not the reviewer's independently rerun 10-test pre-fix subset.

## Handoff

Next: join authority admission to an immutable/reverified input at the fixed
namespace launcher boundary, then observe original/migrated/initialized CP,
cache epochs and sampling in the exact native adapter. This increment alone is
not that coordinator. All runtime_accepted/promotable flags remain False in
operational reports. Overall STEP 8-10 PARTIAL / NOT_READY.
No vehicle operation, active profile, commit, PR, push, merge or automation.
