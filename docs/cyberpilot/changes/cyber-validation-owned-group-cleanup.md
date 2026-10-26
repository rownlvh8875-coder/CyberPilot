# Confirm owned process-group exit after timeout

## Identity and purpose

- Cyber Validation offline lifecycle correction; implemented/reviewed, full-PC pending.
- feature/cyber-autotune HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus local changes.
- Existing timeout test failed because direct-child wait/pipe EOF preceded descendant kernel
  exit. Bounded10000/dev/null-FD child reproduced8/10, stateR+PF_EXITING then absent by5ms.
- No vehicle applicability claim: this is Linux laptop offline process management.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot above branch/HEAD, locally introduced
  openpilot/tools/cyber_autotune/native_runner.py and its existing test_native_runner.py.
- Call path: lateral/longitudinal native supervisor -> private _run_process -> owned Popen
  session -> communicate timeout/exception -> exact PGID SIGKILL -> parent reap -> group exit.
- Existing native dependencies/submodules unchanged, no Carrot/Sunny/Mazda code copied.
- Python3.12.13 subprocess/os/time, Linux procfs; no new package or external service.

## Changes and expected effect

- Modify native_runner.py only: _owned_group_running/_wait_owned_group_exit/
  _terminate_owned_group; named1s cleanup confirmation budget and1ms polling interval.
- Add test_native_cleanup.py. Existing tests/assertions unchanged, including immediate
  descendant absent/Z assertion. No sleep added to make that test more lenient.
- Check group membership before selected owned stat; membership rechecked in stat. Ignore
  normal disappearing PID races; malformed/inaccessible verification fails closed.
- SIGKILL only exact owned group created by start_new_session. No global subreaper,
  process-name kill, unrelated-group signals or vehicle process interactions.
- Timeout/exception cleanup now waits for all observed group members absent/zombie, not
  merely pipe EOF. Direct child still reaped. Ordinary successful execution path unchanged.
- Cleanup confirmation failure raises OSError/TimeoutError; existing native supervisors
  return generic WORKER_UNAVAILABLE without samples/authority. No claimed safe completion.
- Resource timeout is not a control/safety threshold; no native limits, Params or CAN changes.
- Maintenance cost: Linux procfs scan on timeout/exception. Trusted fixed worker only;
  malicious group escape/container proc visibility are not sandbox guarantees.

## Regression risk and acceptance

- Unrelated processes must remain alive, confirmed parent must be reaped, descendants
  absent/Z immediately at successful timeout return. Verification must be bounded.
- Existing runner tests plus8 repeated delayed-exit cases, proc membership parsing,
  controlled confirmation timeout and both public supervisors on forced cleanup failure.
- Synthetic ephemeral processes only; no personal/holdout data. No baseline controller changes.
- Rollback does not touch active control (tool has no runtime consumer). Reverting this
  fix would reintroduce the observed cleanup defect, so retain until replaced/tested.
- One final independent read-only review; no vehicle promotion authority.

## Validation method and actual results

| Stage | Result |
| --- | --- |
| Reproduction | original affected run352PASS1FAIL; controlledprobe8/10 nonterminal |
| Added regression RED |6/8 subcases nonterminalR before fix |
| New+existing runner focused |13 tests27subtests PASS5.17s,exit0 |
| Ruff/diff |PASS after explicit test-string concatenation correction |
| Full package/controls |225passed725subtests29.75s /357passed14.83s,exit0 |
| Independent review |0Critical0Important0Minor;13focused27subtests4.94s plus8 fault probes |
| Qualified replay/closed loop/continuous shadow |NOT_RUN; lifecycle tests cannot qualify these |

## Handoff

- Root cause proven and original assertions preserved; package/affected/review complete,
  current full-PC pending. Original352/1failure retained as pre-fix evidence.
- Confirmation polling is bounded; communicate/kernel stalls are not hard-real-time bounded.
  Ordinary EXITED-path descendants and malicious group escape are unchanged/out of scope.
- Malicious-code sandbox/authenticated evidence/real-time/device qualification not supplied.
- No commit/PR/push/merge, device connection or private-data access. Overall NOT_READY.
