# Configuration provenance boundary coverage

## Identity and purpose

AutoTune/Validation test-only increment on feature/cyber-autotune, baseline
5a15ae1d31016d66f26ea5bae59232cea3ef44ea. Status: reviewed and verified offline.
Protect existing fail-closed boundaries when effective runtime configuration is
unknown; do not infer continuous settings from a logger-start snapshot.
All inputs are synthetic. No driving logs, device or vehicle applicability claim.

## Original references

Reuse CyberPilot evidence.py and torque_identification.py at the baseline above;
no external code or tuning constants imported. Existing MIT attribution unchanged.
Manifest + trusted policy -> preflight key/digest checks -> bounded file integrity
-> non-authoritative report. Frozen torque points + declared provenance/stage ->
input validation -> TLS diagnostic -> permanently non-qualified report.
No submodule/model/interface/schema changes.

## Changes and expected effect

- tests/test_evidence.py: require each configuration/runtime epoch/signal-stage/
  timestamp-alignment binding before artifact I/O; changed binding invalidates the
  prior reviewed manifest even if other metadata is unchanged.
- tests/test_torque_identification.py: missing bindings and wrong sign, requested
  command stage or double-delay declarations block before SVD. Syntactically valid
  hashes for unknown snapshot/epoch semantics do not turn a numerical estimate
  into qualification, confidence or candidate/runtime authority.

No production code change or new writer/adapter/optimizer. Tests exercise existing
validation before observable I/O/SVD; constants, ranges, reset rules and controller
behavior unchanged. Caller assertions are not authenticated by a SHA256 format.
Correct signal-contract text cannot prove that samples obey its sign/stage/delay.

## Regression risk and acceptance

Risk is misleading test coverage or qualification claims, not changed control.
Existing tests and criteria are retained. Test sensitivity is checked with private
in-memory fault injection and pristine reruns; no weakened code is saved or shipped.
No holdout, evaluation authority, private route identities or raw data is published.
Rollback is reverting this test/document-only commit; no active profile changes.
Acceptance requires targeted, combined AutoTune/controls, default suite, Ruff,
SCons, deterministic rerun, publication audit and independent review before push.

## Validation method and actual results

Ubuntu24.04 prepared Python environment; existing public fixture and criteria
unchanged. Five added tests and all32 existing tests in the affected files pass.

| Check | Actual result |
| --- | --- |
| Two-file unittest command | 37 PASS, exit0 |
| AutoTune + controls test runner,2workers | 674 PASS,148.54s,exit0 |
| Default test runner,2workers | 1,581 PASS /43skip /1xfail,418.23s,exit0 |
| Ruff, changed Python files and private validation helpers | PASS |
| SCons -u -j2 | PASS,exit0; PWD-directory mismatch warning retained |
| Transient fault sensitivity | All5 injected faults detected; pristine before/after PASS |
| Fresh-process deterministic rerun | Exact full-report equality |
| Independent review | 0Critical/0Important/0Minor; reviewer context reused due capacity |
| Publication audit and diff whitespace | PASS; only synthetic tests/documentation |

Default supervisor completed419.0759s without timeout and confirmed unchanged
source overlay/public fixture. ReceiptSHA
`c71442d4d0cc2acb66515d7837790fd9c1a36207112ab7ad9b0de491f2643c89`.
Identical final sensitivity-reportSHA
`5b1d8deeb2eee0f4c08c20b9fe973f550bf879d9ac3c828a2a0e71dcdaec115f`.
Test sourceSHA(test_evidence.py)
`2e251f6b1c05562194f2d25557861e2fa7fb8f09ec91ca5a5823fafe757fe15f`;
test sourceSHA(test_torque_identification.py)
`60f4d08807f60ca33765bad614fb420518f2812265f3640cb5a8c04cd49d9ade`.

The first private mutation harness failed its sensitivity check: two faults
triggered other guards instead of isolating the intended guard. That failed
receipt is preserved privately. Only the transient injection contexts were
corrected; production code and tests were not weakened. Final injected-fault
failures are intentional sensitivity evidence, not production failures or newly
fixed vulnerabilities. No mutation code is included in the public change.
Final documentation closeout follows the runtime gates; executable files remain
the same verified hashes, with a final publication/whitespace check before push.

Replay, calibrated closed-loop and non-actuating device shadow NOT_RUN by this
test-only increment. Existing qualification gaps and safety constraints remain.

## Handoff

This is coverage reinforcement, not proof of effective runtime configuration,
accepted speed-aware tuning or completion of the original vehicle objectives.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain in force.
No activation/deployment approval follows from any unit-test count.
