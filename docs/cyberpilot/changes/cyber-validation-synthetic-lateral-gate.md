# Frozen synthetic lateral candidate gate

## Freeze-before-candidate rule

The relative candidate policy was committed and pushed before any new candidate
execution:

```text
policy SHA-256  ae4ad7f1cad3e4e5f138df2d4ef8feae17e881a951a5b37caa481fd124ba2a62
policy commit  f118bb5a467944e5711af4768e9372eb3165d067
```

The policy is stored at:

```text
docs/cyberpilot/policies/synthetic-lateral-nonregression-v1.json
```

It binds the 14-scenario order, catalog/CarParams identities, sample counts, fault
outcomes, left/right symmetry and the frozen baseline report. It grants no
physical-performance, candidate-generation, shadow, runtime or vehicle authority.

## Non-regression limits

The candidate may not materially regress lateral RMSE/max error, heading error,
steering jerk, saturation, requested torque, command reversals or inactive torque.
Relative tolerances are paired with small absolute tolerances so a zero baseline
cannot be converted into an arbitrary nonzero result. Fault scenarios must remain
rejected and all scenario identities must remain unchanged.

For a synthetic improvement pass, each declared stress scenario must improve at
least one of lateral RMSE, max lateral error, steering jerk or saturation by at
least 10%, while all non-regression and symmetry checks remain satisfied.

## TDD and self-check

```text
RED                    10 failures: gate module absent
GREEN                  10 passed / 9 subtests
AutoTune + controls    541 / 541 passed
Ruff                   PASS
SCons                  100% complete
privacy audit          191 files / 0 findings
```

The frozen baseline was rerun on committed source HEAD
`1a4d3a55921f29516d0b004fbd6c7c104299198c`. Its internal report SHA remained:

```text
2421a5399f33fb7b523f8f4b4e486c0f9d717c70edd3a89750cbe49c03e8bdfd
```

Baseline compared with itself returned:

```text
SYNTHETIC_NONREGRESSION_PASS
no_regression_pass     true
improvement_pass       false
symmetry_pass          true
fault_identity_pass    true
```

The self-check repeated byte-for-byte with result SHA-256:

```text
3d07f9be8afa562333db535755c8f97d86fb476d204b9592f3cc5f0ae3c7f559
```

No candidate was executed by this self-check. `STRESS_IMPROVEMENT_INCOMPLETE`,
`SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION` and
`CANDIDATE_GENERATION_NOT_AUTHORIZED` correctly remain.
