# CORE28 Closed synthetic rollout execution and publication

Builder-selected small offline increment under delegated execution/approval opt-out.
Make CORE27 reproducibly usable from an explicitly executing development command.

## Approaches and choice

A generic external-input reader would open new unqualified intake and is excluded.
Shell-only invocation leaves persistence and overwrite handling to users. Chosen:
closed three-case API/CLI using unchanged catalog,CORE27 and CORE16 safe publisher.
No new arithmetic,CORE27 modification,stream/checkpoint,vehicle input or rate policy.

## API and ordering

`integration_tools.core_rollout_run.run_rollout_case(case_id: object, output_root: Path)->dict`.
Exact built-in str in existing CASE_IDS sign-cycle/declared-difference/late-invalid;
invalid case ROLLOUT_RUN_CASE before output path/factory/model work.
CORE16 _output validates NEW external path/existing parent before case assembly;
existing/symlink/badtext/missingparent/in-checkout output errors preserve original
ArchiveWorkflowError codes and execute zero model work.
Build the selected fixed case once,serialize INPUT bytes BEFORE model execution;
invalid input encoding ValueError/TypeError/ArithmeticError ->ROLLOUT_RUN_INPUT_ENCODING.
Call unchanged CORE27 rollout_synthetic_sequence exactly once. SuccessMATCH/DIFFERENT
has3modelsteps. Catch only CORE27 type/container/count/input/order errors as a saved
REJECTED result with steps0;numeric preflight work is NONZERO. Other CORE27 errors
->ROLLOUT_RUN_EXECUTION_FAILED_WORK_MAY_BE_NONZERO,no files published.
Other unexpected internal errors propagate from API;CLI conservatively reports2.

## Saved artifacts

Three files ONLY: INPUT.json,RESULTS.json,SHA256SUMS.txt. Canonical UTF8 JSON,newline,
sorted keys,no NaN. Sorted two-entry checksum,selfexcluded. All artifact serialization
finishes before mkdir. No original source identities authenticated or added.

INPUT schema_version1,contract_id CORE28_CLOSED_COMPUTED_ROLLOUT_INPUT_V1,case_id,
scope CLOSED_COUNTERFACTUAL_COMPUTED_ROLLOUT_FIXTURE_ONLY,frames/contexts.
Owned dataclasses projected losslessly: request.requested_binary32 becomes
requested_binary32_be_hex;context.current_driver/current_angle_deg become
current_driver_hex/current_angle_deg_hex. No rawfloat fields/coercion/defaults.

RESULTS schema_version1,contract_id CORE28_CLOSED_COMPUTED_ROLLOUT_RESULT_V1,
same case_id/scope,status,rejection_code,sequence_completed,frame_count4,
declared_transition_count3,completed_transition_count,model_steps,
initial_declared_state/final_computed_state(state dict or null),
entry_differing_transition_indices/output_differing_transition_indices/
differing_transition_indices,rows. Each row:transition_index,model_index,status,
declared_entry_state,entry_state,computed_next_state,declared_saved_state
(saved_limited_state/saved_angle_counter),entry_differences/output_differences
(field/declared/computed dicts). Full output trace/projection is NOT exported/claimed.
source_rollout_contract_id CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1,
requested_state_feed_rule FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED,
computed_state_fed=sequence_completed,anchor_transition_checked/prehistory_checked/
source_identity_reauthenticated/v4_payload_allowed/f61_input_allowed/
actual_activation_allowed false,gates unchanged. SavedREJECTED hasno rows,
completed/modelcounts0,seed/finalnull,all differenceindicesempty,originalfixedcode.

Post-model record/serialization ValueError/TypeError/ArithmeticError ->
ROLLOUT_RUN_RESULT_FAILED_WORK_MAY_BE_NONZERO. Validate result status mapping0/1/2
before publish. Reuse unchanged CORE16 _publish once (new0700/0600,exclusive/nofollow,
shortwrite completion,exact bounded readback3/fileset/rootidentity). Wrap its error as
ROLLOUT_RUN_PUBLICATION:<originalcode>:WORK_MAY_BE_NONZERO. Never cleanup/retry/overwrite.
Failure may leave absent/empty/partial/complete folder and executed model prefix.

Return after successful publication only: schema_version1,
contract_id CORE28_CLOSED_COMPUTED_ROLLOUT_RUN_V1,status COMPUTED_ROLLOUT_RUN_PUBLISHED,
case_id,result_status/result_exit_code0or1or2,execution_requested true,
sequence_completed,model_steps,completed_transition_count,computed_state_fed,
files all3 sha256/byte_size,source_identity_reauthenticated/prehistory_checked/
v4_payload_allowed/f61_input_allowed/actual_activation_allowed false,
gates unchanged,scope same. No output path/time. Receipt is stdout,not fourthmember.

## CLI

`tools/core_rollout_run.py::main(argv=None)->int`: exactlyone --case/--output-root
and exactlyone --run. No check/default-run/abbreviation/duplicate/positional/
externaldata/rate flags. Fixedcase choices literal before project import.
Help/syntax before project/path/model work. Usage ROLLOUT_RUN_USAGE_NO_MODEL_EXECUTION/2.
Known RolloutRunError/ArchiveWorkflowError preservecodes2;other ordinary failures
ROLLOUT_RUN_FAILED_WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST/2.
Successpublication returns current result exit0/1/2. REJECTED2 with a complete
stdout publication receipt and saved files is intentional preflight rejection,
not necessarily an operational failure. Never turn backendfailure into saved rejection.
Cold parser-through-output bytecodesuppressed,globalsrestored,no temp/cache/probe;
shortwrites/failedstdoutstderrhelp operational2,best-effortdiagnostic,BaseException
restores thenpropagates. Post-publication stdoutfailure can leavecomplete3files.
Initialimports caller-managed(-I -B). No raw paths/error text in diagnostics.

## Verification and boundaries

TDD all3cases/literalstate/differences/serialization/counters/rejectedzero,
case/output/encoding order,one factory/rollout/publisher/readbacks,determinism,
modelerror/unknownstatus/encodingfail,race/partial/readbackfailurepreservation,
explicitrun/syntax/cold/globals/noexternalexecution/failedstreams/partialstdout.
Existing CORE27 and CORE16 publication regression,full1697+actualnewtests,
310owncompiles/static/frozenwheel. Independent expected artifacts assembled from
priorsealedCORE27 inputs/fullresults,not new runner or model;API/CLI/blocked-cold
two runs to NEWdestinations,identical receipts/files,exactcounts/custody,doccommand.
Source642/protected632/refs31,onefinalfreshreview,unsignedseal.
Synthetic model/quantizer work explicitlyNONZERO for completed cases;not actual
F61/r/dt/Controller/Runtime/CAN/vehicle work. Actualr/T2/scale=null,R_BUDGETUNRESOLVED,
StaticGateFAIL/denialgatesunchanged. No origin/history/fulloutput/native-replay/
physicalperformance proof. CooperativeLinuxCPython3.12.13,noatomic/fsync/crash/
adversarialhooks/concurrentglobals/path-race/atime/otherplatform guarantees.
Keep hostworktree/branch/evidence,no merge/push/PR/CI/HF writes.
