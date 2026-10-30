# R9 synthetic caller integration harness

## Purpose and boundaries

Exercise the existing installed CyberLateral0.3.0 API as a caller, not redesign its
arithmetic or production adapter. User delegated routine design/execution choices.
Implement inline with TDD and one independent final review. Continue the existing
isolated feature branch/Draft PR, using skip-ci commits and explicit offline CI.
No main merge or vehicle execution is authorized by this scope.

Approaches considered: extending the runtime package would change the sealed
wheel without a runtime requirement; adding more simulate unit tests alone would
not verify an isolated installed caller. Chosen: a stdlib-only DEV harness script
run twice by the existing verifier inside its empty installed-wheel environment.
The package/API/version,77 imported files and exact wheel remain unchanged.

## Contract

- Only the existing seven fixed catalog scenarios/112 invocations. No external
  input/log/source-root/vehicle/policy/time parameter or captured data option.
- A golden record freezes fixture identity and full scenario result hashes from
  the R8 validated report. This is regression evidence, NOT an independent oracle
  or a new production equivalence claim. Existing independent numerical tests stay.
- Compare single-step chaining, every internal two-chunk split (105 total) and
  round-robin independent callers against each scenario's full batch and golden
  result. Compare all output/state fields exactly; no tolerance/clamp/defaults.
- Verify input/state immutable; reject missing state, reset mid-sequence, gaps,
  duplicate invocation, missing limits/history, nonfinite request, exhausted state,
  wrong scope and empty/non-tuple batch. Record exact observed exception classes
  and codes from the existing model; never label them original Controller/F61 APIs.
- Record synthetic checks only. Invocation index is NOT seconds; actual r/T2/scale
  null, R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO and all
  activation/F70UH/F70V/F71 prohibitions remain unchanged.
- New-path-only output: reject files/directories/dangling links before package
  import/work; reserve the directory without overwrite. On failed verification,
  never write PASS. Success emits canonical RESULTS.json and SHA256SUMS.txt.
- Script uses public step/simulate/types plus the fixed catalog, not private
  arithmetic, original helpers, NumPy, Controller, schema, CAN or F61.
- The verifier runs the harness twice with installed Python -I -B from an unrelated
  cwd; byte comparison is part of its success gate. Logs/summary/Manifest include
  the actual harness results; report/wheel/runtime behavior stays unchanged.

## Files

integration_tools/synthetic_harness.py owns fixed caller checks and CLI;
reference/synthetic_harness_expected_v1.json owns the reviewed R8 golden identity;
project/test_synthetic_harness.py covers real behavior, error guards and isolation;
integration_tools/verify.py runs isolated pairs and propagates their success;
README/docs explain scope and artifact meaning. No dependency or CI workflow edits.

## Completion

All inherited140 tests plus new behavioral tests PASS; full verifier/static checks,
exact wheel and two-run harness artifacts PASS; independent review addressed;
scoped skip-ci commit/push and explicit dedicated CI PASS recorded in the existing
Draft PR. Keep old evidence/main checkout unchanged; retain this audit workspace.
