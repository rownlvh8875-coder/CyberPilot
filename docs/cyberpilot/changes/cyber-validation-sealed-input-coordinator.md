# Sealed input-only isolation coordinator

## Identity and purpose

Cyber Validation / AutoTune, implemented locally and independently reviewed.
feature/cyber-autotune HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus uncommitted
changes. Ubuntu24.04/Linux infrastructure, not vehicle control or replay approval.
Join existing input admission and bounded process lifecycle without permitting
the worker to reopen a mutable raw-data path or receive a host-directory FD.

## Original references

CyberPilot https://github.com/rownlvh8875-coder/CyberPilot, branch/HEAD above,
local replay_admission.py and replay_supervisor.py; existing D work-only namespace
probe. Linux UAPI linux/fcntl.h and asm-generic/fcntl.h establish F_ADD_SEALS1033,
F_GET_SEALS1034 and WRITE/GROW/SHRINK/SEAL mask15. The pinned standalone Python
does not export these fcntl symbolic names; verified kernel operations use the
documented ABI, not a weakened fallback. No Carrot algorithm copied; project
license retained. No dependency/model/submodule/upstream revision changed.

Call path: run_input_probe -> validated development grant -> no-follow regular
file -> sealed memfd -> explicit FD inheritance -> fixed private namespace and
chroot -> stdlib input hash/seals/isolation verifier -> exact aggregate response
-> post-use source check -> non-authoritative result. No log decoder or learner.

## Changes and expected effect

- replay_input.py: copy authorized bytes, verify size/hash/stable file metadata,
  seal all mutation, context-managed FD lifetime, source checks around use.
- replay_coordinator.py: fixed input-only launcher, sealed launcher/worker assets,
  type-sensitive output contract, private errors suppressed, no arbitrary argv API.
- replay_input_namespace.sh: user/mount/PID/net/IPC isolation, minimal read-only
  system Python3.12 userspace, private tmp/SHM, dropped caps/no-new-privileges.
- replay_input_worker.py: sealed input identity and operational isolation checks.
- replay_supervisor.py: explicit pass_fds argument; default still passes no FDs.
- tests/test_replay_input.py, tests/test_replay_coordinator.py: synthetic tests;
  tests/test_replay_supervisor.py: allowlisted descriptor inheritance test.

No raw pathname, source directory FD or source code is exposed inside this
input-only worker. Selected source HEAD/hashes are checked by the parent, not
executed or claimed to be the system-Python runtime. CP/cache hashes are opaque
declared request bindings, not observed truth. replay_allowed, replay_executed,
runtime_accepted and promotable remain False even on successful input checking.

Infrastructure bounds: existing512MiB input cap; 1MiB read chunks; transient copy
buffers can approach2MiB (deferred Minor below); 256KiB per shipped launcher asset;
16KiB combined child output; existing60s maximum worker deadline; private96MiB
root tmpfs and64MiB SHM. Preparation/Git checks are not under the worker deadline.
memfd avoids an intentional persistent input copy, but does not promise no OS
swap backing or secure erasure. Assets/grant authenticity and local runtime are
trusted; no claim of security against a malicious/privileged host or kernel.

## Regression risk and acceptance

Risks: original file changes during/after copy, inherited directory descriptors,
file/FIFO/symlink confusion, output mismatch, source drift, incorrect promotion.
Acceptance: explicit role/segment denial before opens; no-follow regular files;
sealed copy unchanged after original overwrite/unlink; kernel refuses write/
grow/shrink; no descriptor leaks on mismatch/consumer failure; response mismatch
and child failure cannot succeed; source drift prevents result return.

Tests only use temporary synthetic3-byte input and Git fixtures. Existing tests,
holdout roles, acceptance references and scientific thresholds unchanged.
Rollback: remove new unintegrated modules/assets/tests and pass_fds extension;
no active runtime call site or state migration. No vehicle activation authorized.

## Validation method and actual results

| Stage | Actual evidence |
| --- | --- |
| RED | New modules absent; explicit FD passing unsupported before implementation |
| Environment failure | Python fcntl seal symbols missing; fixed using locally verified Linux UAPI constants |
| Focused unit suite | PASS22 tests42subtests,1.62s |
| Full affected runner AutoTune+controls | PASS415 tests14.67s,exit0 |
| Ruff touched Python; bash -n launcher; git diff --check | PASS |
| Actual namespace integration | PASS2 tests; positive probe twice; unsealed, wrong-size and wrong-hash rejection cases |
| Independent review | 0Critical,0Important,1Minor; reviewer independently ran9 new tests |
| Full default PC suite | NOT_RUN this increment; previous unrelated environment/timeouts unchanged |
| Real driving replay / simulation / shadow | NOT_RUN |

Deferred Minor: Python retains the previous block while allocating the next read
and retains the final copy block across the context yield. Memory remains bounded
(about2MiB transient copy buffers in addition to the sealed input), but the plan's
literal single1MiB block target is not met. Clear block references in a separately
verified follow-up; not an admission, seal or promotion failure.

Review scope rulings: grant/review-hash authenticity, malicious host/runtime/kernel,
whole-runtime closure, swap persistence and end-to-end preparation deadlines are
external assumptions, not proven properties. Native decoding/CP/cache/replay/
vehicle qualification remain required downstream gates, not waived. Final full
affected/lint/integration evidence is main-agent execution, not independent rerun.

## Handoff

Implement an exact-source observation adapter next: original carParams -> replay
migration -> initialized Params CarParams, plus cache times and restoration state.
Do not fabricate unknown initial-state hashes to run a real log. The existing
v1 contract requires expected hashes; an observation-stage contract must explicitly
separate unknown observations from replay admission, without granting authority.

Recorded f5fd296c code reinspection confirms get_car_params_callback can regenerate
CP via get_car; get_custom_params_from_lr first/last selection is not proof of a
pre-run cache epoch; torqued restore key includes fingerprint/tuning/friction/
factor/version and may restore points/decay independently of liveValid filter
values. Preserve those distinctions; no arbitrary seed/cache/CP substitution.
Overall STEP8–10 remains PARTIAL/NOT_READY. No raw logs, vehicle writes, active
profiles, commit/push/merge/public upload or automation in this increment.
