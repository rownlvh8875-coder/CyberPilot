# CORE69 — Selected-source reference for declared synthetic diagnostics

## Intent and choice

CORE68 reproduces current public-model arithmetic. Add a separate selected-source
reference audit of the same SHA-pinned complete synthetic input and saved diagnostic.
This is the author's next-feature choice under the user's standing autonomous
execution instruction, not a newly user-authored product requirement.

Approaches: more saved-only presentation does not check arithmetic; a new oracle
duplicates existing qualified references; reuse the integer-bit quantization oracle
and original hash-pinned selected limiter/fault helpers in a fresh worker. Choose
reuse. Unlike R38 computed-state rollout, each reference step uses that transition's
declared entry state. Never silently reseed later steps with computed outputs.

This is independent of public-model arithmetic, not independent of all software or
of input admission. CORE55/46/5 preflight remains shared and may import the model
and current quantizer for validation; it must execute zero model steps. A bug in
admission may reject a valid input before reference work. The worker may not import
the public model/validator, openpilot/opendbc/cereal/capnp, F61 or actual runtime.

## API and capture

`check_recording_reference(input_file: Path, input_sha256: str,
diagnostics_root: Path, diagnostics_sha256: str) -> dict` in
`integration_tools/recording_diagnostics_reference.py`.

Validate both lowercase64 SHA strings before caller paths; unchanged CORE66 captures
and validates the two saved files once. Reject declared input SHA mismatch; capture
input once with existing CORE61 `_capture`, verify actual SHA/declared byte size;
decode/preflight all CORE55 bytes before worker launch. All malformed/late-invalid
input and saved structural errors reject without model/reference steps. Numeric
validation itself is nonzero. Never reopen captured artifacts.

Build private canonical wire `schema_version=1`,
`scope=CORE69_DECLARED_REFERENCE_INPUT_V1`, `rows`1..127. Each row contains `state`
(index/previous_requested/previous_applied/angle_counter), request/driver/angle hex,
lat_active, six integer limits in STEER_MAX/UP/DOWN/allowance/factor/multiplier order,
and `saved` (saved_limited_state/saved_angle_counter). Values come directly from
decoded declarations and binary32 unpacking, never saved computed output or model.step.

Check existing R38 imported source identity plus all new bridge/worker/CLI and
consumed capture/admission/saved-reader source hashes before/after the worker.
Changed/missing reference identity blocks; no fallback or source-pin update.

## Reference worker

`tools/recording_diagnostics_reference_worker.py` is private stdin/stdout, invoked
as same Python `-I -B` from the trusted component cwd, timeout60s. No temp/cache or
result files. Bound stdin and accepted stdout to1048576bytes. Trusted fixed worker
output is captured before size checking; this is not an adversarial process sandbox.
Use strict canonical parser; independently validate the complete primitive wire
before initializing helpers. Project function
`reference_declared_states(payload: object) -> dict` in
`project/recording_diagnostics_reference.py` constructs independent State/Sample/
Limits records and calls existing NormalizedReference once per declared transition.

Runtime CPython3.12.13/Linux/binary64, numpy2.5.3, worker optimize0. Guard forbidden
imports and verify none loaded. Import existing reference code only after imported
byte-identity verification. Kernel itself checks exact helper SHA/size before compiling
its two permitted definitions; original Controller/module is not compiled/executed.

Return closed worker record schema_version1,
contract_id=CORE69_DECLARED_REFERENCE_STATES_V1, `states`, `reference_steps`,
`helper_counts`, `python`, `numpy_version`, `forbidden_modules_loaded`.
Expected helper counts: compile_calls1,selected_definitions_compiled2,
limiter_direct0,limiter_tracedN,fault_explicitN,fault_default0,traced_clip_calls2N.
Parent checks exact keys/types, states/counts/bounds/index increments/runtime and
declaration correspondence before using results. Failed workers/results/late source
changes are operational errors with possibly nonzero reference work, never MATCH.

## Projection and result

Assemble reference CORE61-shaped diagnostic projection from validated fixed saved
metadata, actual input identity/counts and independent states plus declared input
entry/saved states. This is a comparison projection, not a new producer invocation.
Compute per-row saved-versus-reference differences/status and aggregate diagnostic
status. Compare all canonical headers and rows, including absent rows in either
direction; no tolerance, data repair or truncation.

Public record contract CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1:
`audit_status=REFERENCE_MATCH|REFERENCE_DIFFERENT`, `audit_exit_code=0|1`,
separate saved/reference diagnostic statuses, input/diagnostics identities,
`stored_record`, `reference_projection`, sorted differing_header_fields and ascending
differing_transition_indices. Report recorded_model_steps separately;
new_synthetic_model_steps0,new_reference_steps=N,reference_helper_counts,
reference_identity/runtime/forbidden_modules_loaded, shared_admission_preflight=True,
reference_independence=EXISTING_SELECTED_SOURCE_AND_INTEGER_BIT_ORACLE_NOT_PUBLIC_MODEL,
numeric_validation_work=NONZERO_NOT_AGGREGATED. Keep six CORE66 authority flags false,
source-identity reauthentication false, gates unchanged. Scope is bounded declared
next-state parity, not complete output/trace/controller/vehicle or origin proof.
Reproduced diagnostic DIFFERENT remains DIFFERENT even when audit exits0.

CLI `tools/recording_diagnostics_reference.py`: required exactly-one --run,
--input-file,--expected-input-sha256,--diagnostics-root,--expected-diagnostics-sha256.
No abbreviation/policy/context override. Usage/SHA checks before project imports;
canonical stdout <=2097152bytes, exit0/1 by audit, errors2/fixed codes only. Positive
short writes complete; late stdout failure preserves prefix and possibly nonzero
reference work without retries. Restore sys.path/bytecode settings; no result writes.

## Acceptance and exclusions

Test-first literals cover real reference MATCH, true saved DIFFERENT with declared
feed, coherent corruption, a public-model arithmetic fault still found by reference,
both row-count directions, late preflight zero prefix, source/worker faults and typed
protocol rejection, negative/signed-zero/rounding/inactive/fault-counter boundaries,
maximum127steps, CLI opt-in/output errors and repeated-process determinism. Existing
CORE61/64/66/68 and R38 references remain unchanged. Run static checks, full DEV gate,
one fresh whole-branch review, normal publication and exact CI/artifact verification.

No dependencies/model/wheel/reference helpers or existing schemas change. Actual
r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,Candidate/Runtime=NO_GO,
F70UH/F70V/F71 and actual activation NOT_ALLOWED. Actual vehicle input/capture/
Controller/Runtime/CAN/F61/actualdt/r/install/deploy=0. Selected helper/reference work
is explicitly nonzero; it is not whole-domain numerical, performance, source/build,
first-anchor/prehistory, hostile-filesystem or safety qualification.
