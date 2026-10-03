# Offline feature-branch release checklist

This is an engineering publication gate, not deployment or vehicle activation.
The completion report records executed outcomes; unchecked items here remain
requirements, not implied PASS claims.

## Before publication

- Preserve frozen v1 evidence, policies, private simulator state, holdout/H1/H2.
- Keep experimental control defaults and all six vehicle authority flags false.
- Inspect staged content, branch history, source provenance and no new LFS objects.
- Run AutoTune + controls through `python tools/test_runner.py ... -j 1`.
- Run both focused Cyber lateral process-replay test modules explicitly.
- Run Ruff on changed Python; parse new policy/receipt JSON; `git diff --check`.
- Activate the existing supported environment, then finish `scons -j2` to 100%.
- Execute `python -m openpilot.tools.cyber_autotune.synthetic_pipeline` twice;
  compare complete canonical output bytes, not rounded metrics or selected cases.
- Verify 26 lateral / 18 longitudinal fixture cases, 50 separate delay variants;
  each arm repeats twice, nominal execution and actual invalid-input rejection.
- Preserve rejected candidates. Synthetic acceptance cannot activate a profile.
- Test shadow failure/restart/noninterference, worker timeout/reap and snapshot
  corruption/interruption/recovery. Distinguish local process tests from power loss.
- Independent review; no unresolved blocking correctness/privacy findings.
- `python tools/cyberpilot/check_publication.py --base origin/main` must report
  zero findings for history, index and working tree. Review human-readable diffs too.
- Fetch origin; require target branch to be an ancestor; ordinary fast-forward push
  to `feature/cyber-autotune` only. No main/develop merge, no force push, no deployment.
- Verify remote equality and clean tracked/untracked state after publication.

## Scope that remains unverified

Real vehicle calibration, independent lane truth, full perception/planner replay,
live scheduling/transport effects, actuator behavior and road performance are not
established by this checklist. Their absence does not require collecting more data
to run the offline engineering suite, but continues to block vehicle activation.
Hosted CI execution must be reported separately from local workflow syntax/tests.
