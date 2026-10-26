# A1 native experiment failure transport

## Identity and purpose

AutoTune/Validation bounded maintenance on feature/cyber-autotune, baseline
0f4a1b8691e3c5e4cd0eca8a13ff2481c3393f9c. Status: implemented and software-verified; independent scoped code review approved.
Git delivery is recorded separately after final publication checks.
Preserve the observed direct-child return code that the A1 supervisor previously
omitted from failure receipts. This addresses the deferred transport-reporting
minor in [A1 native integration](a1-native-speed-tune.md), not a control defect.
No vehicle applicability, tune acceptance or performance improvement is claimed.

## Original references

Reuse this repository at the baseline above: native_runner.ProcessOutcome and
_run_process, and a1_experiment.run_experiment. Existing repository/native MIT
attribution is unchanged; no external code, dependencies, model or submodule
changes. The inherited opendbc pin remains
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
Call path: owned synthetic request -> existing isolated worker lifecycle ->
ProcessOutcome -> A1 response validation or fixed-authority failure dictionary.
No runtime controller, Params, device, CAN or active-profile consumer is added.

## Changes and expected effect

- a1_experiment.py adds worker_returncode to failure dictionaries only. Integer
  means an observed direct-child return code; negative follows the Linux/POSIX
  signal convention. null means no ProcessOutcome was returned, not successful
  exit and not proof that a child never started.
- TIMEOUT remains TIMEOUT even when cleanup observes a negative return code.
  Exit 0 with empty, oversized, malformed, duplicate-key, wrongly bound or
  otherwise invalid output remains INVALID_RESPONSE, never success.
- test_a1_experiment.py adds five tests: actual ordinary/signal/timeout subprocess
  outcomes, unobserved results and invalid zero-exit responses. Exact failure
  dictionaries exclude stdout, stderr, PID, paths and exception messages.
- Success response keys, native controller state, limits, timing, child cleanup,
  A1 schedules, old v1 runner and generic closed-loop interfaces are unchanged.
  There is no new tuning parameter, physical unit conversion, delay or fallback.

Alternative considered: change the shared v1 runner or build a second supervisor.
Rejected as unnecessary scope expansion: the existing ProcessOutcome already
contains the required observation. Maintenance is limited to A1 failure metadata.

## Regression risk and acceptance

Failure-dictionary consumers must allow the added worker_returncode field;
success payloads and status precedence retain their previous meanings. The
repository's A1 callers/tests were inspected before editing. Unknown outcomes
must not be invented, and no output content may be echoed. Existing admission,
resource caps, controllers, safety, driver override and frozen references stay
unchanged. Tests use only synthetic inputs, not user logs or protected evidence.
Rollback is reverting this offline-only delta, not applying a vehicle profile.
Publication requires affected tests, AutoTune+controls, default suite, Ruff,
SCons, deterministic rerun, privacy checks and genuinely independent review.
Self-review is not independent approval. No vehicle authority follows from any gate.

## Validation method and actual results

Prepared Ubuntu 24.04/Python 3.12.13 environment, with the existing virtual
environment activated and no forced TMPDIR. Historical counts in earlier change
records are not test results for this patch. All new diagnostics are retained
privately under a new no-overwrite evidence namespace.

| Check | Actual result and limit |
| --- | --- |
| TDD before implementation | Five new tests, ten failing assertions, exit 1; missing worker_returncode reproduced |
| A1 experiment and schedule unittest modules | 18 tests PASS, exit 0; 13.322 s |
| AutoTune+controls supported runner, two workers | 679 PASS, 135.12 s, actual exit 0 |
| Default supported runner, two workers, verified public fixture | 1,586 PASS / 43 skipped / 1 xfailed, 314.09 s, actual exit 0 |
| Ruff / SCons -u -j2 / whitespace | PASS, exit 0; build completed 100% |
| Deterministic failure-report rerun | Six cases, two fresh processes, exact whole-byte equality |
| Publication scanner | Three public changed files, zero findings; final index/history rechecked before delivery |
| Independent review | APPROVE: no Critical/Important/Minor findings in supplied public code; no reviewer test execution |
| Qualified replay / calibrated vehicle simulation / device shadow | NOT_RUN; not established by these tests |

The default suite must reuse the unchanged verified public-fixture gate with a
new evidence name; it does not include full process replay or simulator coverage.
Existing success parity and fresh-process checks remain in the affected tests.

## Handoff

All software gates above are complete for the uncommitted source overlay.
Only an ordinary feature-branch commit/push is authorized after final checks;
actual delivery is separately recorded, not assumed from this document.
No PR, deployment, activation or automation action is authorized by these results.
Failure diagnostics do not authenticate settings, qualify an empirical tune or
reopen completed presence/provenance experiments. Original rejected candidates,
unknown effective runtime configuration and all physical qualification gaps remain.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED stay in force.


## Source-bound closing evidence

Default supervisor: 314.966 s, actual exit 0, no timeout, source and verified
public fixture unchanged. Receipt SHA256:
`a2fba38349c145219b674b91c7378cc843e2feb9d9363ab6e04cc8323312c52e`.
Failure reports: 2,234 bytes each, six cases, identical SHA256:
`26a30a0ec0f7336fc523ad7e21fde626e47a7cf61129baf0053ce94ae8e1be77`.
Executable source SHA256:
- a1_experiment.py: `60033e6d96ea3873785739f12410d464eba358403dbafae83a4b96283f49bc44`.
- test_a1_experiment.py: `e9b1ed623636cbe3412b4784d446c9d6e0acf848a5eda2060e9abae9f0ed5cd5`.

The reviewer received the exact public before/after source, diff and supporting
modules as input, with read-only sandbox and no tool execution. Host verification
bound that input to the tested source. Independent approval covers code only;
reported runtime gates are host-observed evidence, not reviewer-executed tests.
Optional TIMEOUT-with-zero-returncode coverage was suggested, explicitly not a
bug or finding; existing branch ordering already preserves timeout precedence.
No extra production or test change was made to manufacture a cleaner verdict.

Earlier review attempts are retained privately: one waited for stdin EOF and
was terminated as an owned process; a script launch was blocked by execution
policy; a file-reading reviewer could not access artifacts under its read-only
policy and returned BLOCKED. Its launcher also lacked an observed exit code.
None counts as a successful review. Final directly supplied-code review completed
with observed exit 0, without relaxing sandbox or execution policy or reading
credentials. The original TDD RED remains expected failing evidence, not a
failure of the final implementation.

Existing tests and non-supervisor functions were AST-compared with the baseline;
all were unchanged. Only the three declared public paths changed; index was empty
and all six submodule pins matched the initial inspection. No frozen policy,
protected input, raw user log or runtime configuration was read or changed.
Source/request digests intentionally reflect the new source; cross-version whole
success-receipt byte equality is not claimed. This result-only documentation
closeout follows the source-bound run and review; executable hashes remain the
same. Links, whitespace, final source bindings and publication scope are checked
again before delivery. It does not satisfy any real-vehicle qualification gate.
