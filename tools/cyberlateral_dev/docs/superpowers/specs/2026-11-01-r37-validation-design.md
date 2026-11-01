# R37 — Declared-synthetic input validation without model execution

## Intent and authorization

The owner approved validation-only and delegated routine choices without repeated
questions. Add a small stdlib DEV CLI preflight for editors of R31 V1 JSON.
Baseline:main6fed18cb92bcd3f95a2e46fe2cefc593d4328e8e.

## Approaches

- Executor-selected:--validate-only in tools/scenario.py, reusing read_scenario.
  One familiar CLI, no duplicated schema or model dependency.
- A separate CLI duplicates argument/cold-cache machinery and discovery.
- Running the model to validate cannot substantiate zero imports/executions.
  A web editor is outside this small change.

## Command and result

`python -B tools/scenario.py --input <V1 JSON> --validate-only` needs no --output.
Combining --validate-only with --output is usage error before input read.
Normal execution still requires --output with prior exit/output behavior.
CLI misuse/unknown options retain argparse stderr/exit2, not validation JSON.

Well-formed validation requests emit exactly one canonical stdout JSON line:
accepted exits0; existing ScenarioError rejection exits2/stderr empty. Unexpected
bugs are not relabeled as success or fallback. No result/report/receipt/manifest
or output directory is created. Existing temporary cold-cache scope is allowed.

Fields:schema_version1, contract_id F70UGZ_R37_SCENARIO_INPUT_VALIDATION_V1,
status SCENARIO_INPUT_VALID or SCENARIO_INPUT_REJECTED, accepted bool,
rejection_code null or unchanged SCENARIO_* code, validation_scope
INPUT_SCHEMA_AND_DOMAIN_ONLY_NOT_MODEL_RUNTIME_OR_ORIGIN,
input_origin CALLER_DECLARATION_NOT_AUTHENTICATED,
time_semantics INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME, model_executions0,
input_raw_sha256/scenario_id/sample_count/first_index/last_index and copied GATES.
All five input identity/count/index fields are null on rejection. Accepted SHA
names the bounded reader snapshot, not atomic filesystem or origin authentication.

## Architecture and boundaries

integration_tools/scenario_validate.py:validate_scenario(input_path:Path)->dict
consumes the unchanged reader and inert scenario_output canonical/GATES. It
never imports model, engine, runner or source/runtime verifier. Fresh import
barrier and a minimal model-free export must validate successfully.
Schema/coercion/domain/state/order/size/file rules stay exactly R31; no new fields.

Acceptance is input-contract validation only, not model/source/runtime readiness,
output correctness, feasibility, origin or vehicle approval. A model-free export
can validate while being unable to execute. Normal execution retains verification.

Public0.3.0 source/API/sealed wheel remain unchanged. Adding DEV source changes
observed producer hashes in ordinary R31/R33 results, not model math. Do not
promise old RESULTS bytes remain identical. Refresh CURRENT guide/inventory
against the committed feature source, preserving historical R30/R31 records.
No dependency/lock/workflow/native changes or notebook update. Implement, commit
and obtain one final review locally; publication is a subsequent integration task.

Actual r/T2/scale null; R_BUDGET UNRESOLVED; Static Gate FAIL;
SOURCE_SCHEMA_UNQUALIFIED6000; Candidate/Runtime NO_GO; F70UH/V/F71 NOT_ALLOWED.
F61/r/dt/Controller/vehicle Runtime/CAN/actual input/candidate performance work0.
Existing suite/gate does declared-synthetic model work NONZERO.

## Verification

RED→GREEN real CLI/helper tests:valid/resumed, invalid late sample, bad types/
state/order, unknown policy, JSON/non-finite, missing/nonregular/oversize files,
mutually exclusive CLI modes before reads, canonical repeat/move/no-write behavior.
Fresh-process import barrier and missing model payload prove no model dependency.
Full suite/static/own compile/reproducible wheel gate; ordinary sign→report and
two basic batches→comparison preserve exact numerical results and closed gates.
