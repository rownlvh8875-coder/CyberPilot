# V4 actual-execution preflight repair

## Identity and purpose

Cyber Validation, pre-execution implementation repair. Baseline: `7820931e442adaafd209c7892c566b642a8363c6`, branch `feature/cyber-autotune`.
The separately authorized retrospective increment must abort on infrastructure conflicts and report attempted head preconditions even when a head fails before prediction. Synthetic regressions reproduced violations before any actual V4 numeric access or external authorization.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above. Existing MIT-licensed V4 executor, immutable V4 fitting-policy module, V1 numerical helpers and 32-clause gate are reused. Call path: external preflight → job → TRAIN → head certificates/Newton → global TRAIN threshold → durable finalization → DEV/rollout → frozen gate/selector. No submodule code or dependency changes.

## Changes and expected effect

The executor adds attempted support, rank, separation and convergence accounting. An unreached check remains `NOT_REACHED`; it is never inferred to pass or fail. Failed proofs remain private. Successful coefficients, scores, threshold and predictive computations retain the existing call order and algorithms.

Identity/authority/storage errors and unknown ValueErrors propagate as run aborts. Only recognized scientific/numerical failures become fail-closed job results. A DEV output write failure can no longer produce a completed run with an inadmissible candidate verdict.

The public executor code map is resealed to the repaired source identity. No new fitting constants, features, normalization, regularization, fallback, threshold objective, candidate, gate clause or selector are introduced. Runtime/controller/vehicle code is unaffected.

## Regression risk and acceptance

The failure accounting is additive. Broad catches must not accidentally accept an infrastructure error; synthetic injected failures test the actual job boundary. No actual execution is permitted until the repair is committed, pushed, exact-HEAD CI succeeds, tree/index are clean and all execution bindings are rebuilt.

Frozen numerical/policy files and historical V1/V2/V3 evidence must remain byte-identical. HOLDOUT is CLOSED with opening/discovery zero, pooled refit remains unauthorized and vehicle authority is NONE. Rollback of the repair is a separate pre-execution source operation; it never changes an authorized running replica.

## Validation method and actual results

Four synthetic regressions failed on the baseline for the expected reasons: normalizer conflict swallowed; DEV storage failure swallowed; failed-head checks absent; exact rank subcause absent. After the initial repair the four tests and existing executor tests passed (20 tests). Full validation and independent reviews are pending and will be recorded in the companion validation receipt before commit.

Replay is limited to the existing offline lateral regression; new simulator, shadow and vehicle testing are outside scope. No actual private V4 fitting, threshold search, DEV, rollout or selection has occurred in this repair.

## Handoff

This is a prerequisite repair, not retrospective scientific evidence. Actual execution must use the subsequent clean CI-success HEAD, not the baseline or an uncommitted tree. Hugging Face is NOT_REQUIRED and unused. The authorized actual retrospective mission remains pending.

## Independent review refinements

The external authorization schema now adds `executor_contract_receipts`: all 13 current executor documents are bound by their file SHA256 and canonical receipt. This map remains separate from the foundational 23 immutable policy inputs, avoiding self-referential publication. Preflight verifies the map and stored source code map; every live permit validation rechecks the document identities. The final external one-shot grant must use this current schema.

Generated rank status is retained separately when verification rejects a proof. Combined score failures cannot overwrite already-proven head convergence. A failed proof whose integers exceed the authorized cap retains its certificate hash and an explicit payload-omission status; the operational fail-closed result remains unchanged.

## Pre-numeric resource bound

Every finite binary64 feature is `U/2^1074`, with `abs(U)<2^2098`. For at most P=93 and n<=336941 rows (the frozen public job metadata), active Gram integer entries are less than `P*2^4196`, and the integer RHS is bounded by `P*n*2^4196`. Cramer's rule bounds determinants/numerators by `P!*(P*n*2^4196)^P`. A common determinant denominator suffices for every active correction, so canonicalization does not multiply independent denominators. Residual direction integers add at most 2098+bit_length(n)+bit_length(P)+4 bits. The resulting conservative authorized ceiling is **395253 bits** per proof integer; it also exceeds the rank-minor numerator/denominator bound. gcd reduction can only decrease integers. Generator incompleteness and Python decimal conversion limits remain operational fail-closed outcomes.

The nonproof ceiling reuses the entire historical V2 metadata ceiling **134217728 bytes per job**, conservatively, rather than dividing it among jobs. Fixed V4 metadata contains at most two heads, 93-element basis/rank lists, 100 accepted Newton exponents per head, 32 gate clauses, fixed population metrics and fixed output manifests; no row-valued numeric JSON or threshold-sweep list is stored. Proof payload allowance separately covers failed proof copies. The reserve reuses the explicit historical V2/V3 **2147483648-byte** storage reserve. These values are fixed before actual numeric access and cannot be adjusted after results. Fresh capacity and live E identity must be checked again before the grant is sealed.

## Completed prerequisite validation

Validation: focused 64, prior 315, combined 2147, full 5006, lateral 16, ruff PASS, compileall PASS, json 731, publication PASS, diff-check PASS, scons PASS. Ruff, compileall, publication/privacy, diff-check and SCons exited zero. Two independent numerical/authority reviews and separate external-helper reviews approved the final repair. All checks used public inputs or synthetic fixtures; actual authorization and private numeric execution remained absent. The companion validation receipt records command/log hashes and current source bindings. Only a subsequent clean exact-HEAD CI success permits execution authorization.
