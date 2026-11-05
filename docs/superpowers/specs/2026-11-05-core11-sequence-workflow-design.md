# CORE11 — Closed Sequence Execution/Inspection/Comparison Workflow

Baseacd03844f6d227dcf79a191dc2da91b94a38e58f. Owner delegated ordinary offline
development without repeated questions; author chooses native Linux/CPython3.12.13
stdlib workflow on the existing linked worktree. No new policy/vehicle authority.

## Approach and intent

Shell chaining existing CLIs is possible but reopens baseline/input between stages
and scatters diagnostics. A new calculator would duplicate trusted existing code.
Choose a thin single-command coordinator over unchanged CORE8 producer/CORE9 loader/
CORE10 comparison logic, with explicit check versus run modes and owned captures.
No implicit execution when checking. Baseline absent means no regression comparison,
not a default baseline. Full-record comparison includes source metadata; a new
development source inventory can differ from historical baseline without arithmetic
regression. Do not suppress identity changes or imply numeric equivalence.

## APIs and files

New integration_tools/core_sequence_workflow.py:
WorkflowError(ValueError).code;
check_saved_sequence(input_path:Path,baseline:Path|None=None)->dict;
run_closed_sequence(case_id:object,output:Path,baseline:Path|None=None)->dict;
exit_code(report:dict)->int. Imported module is inert(no producer/model imports).
New tools/core_sequence_workflow.py: required subcommand check or run,
check --input required,optional --baseline;run --case CASE_IDS and --output required,
optional --baseline. allow_abbrev=false at root and subparsers; JSON stdout only,
no implicit output,format,actual input/rate/vehicle/execute overrides.
New project/test_core_sequence_workflow.py and Korean guide; README/backlog updated.
In existing core_sequence_compare.py extract current comparison body into private
_compare_captured(lhs,rhs)->dict for already validated loader-owned records only.
Existing compare_saved_sequences(Path,Path) still captures each side once and
delegates; JSON/Markdown/errors/exit unchanged. This is not external dict intake.
Expected9paths/3newPythonfiles,539registered/prior530preserved,262owncompiles.

## check semantics

Read current via CORE9 exactly once; optional baseline once. Preserve full current
CORE9 summary as inspection and optional baseline summary as baseline_inspection.
Compare baseline(left) and current(right) through _compare_captured without reopening
files or running calculator/model/reference/native/quantization/dt/r. Same path
captures independently per role. Both three-file guards/caps/canonical/types/gates
remain unchanged. Invalid side errors are WORKFLOW_INPUT:<INSPECT_CODE> or
WORKFLOW_BASELINE:<INSPECT_CODE>,fixed code/message,no partial success stdout.

## run semantics

Reject nonbuiltin/unknown case with WORKFLOW_CASE before baseline access/import/work.
If provided,capture/validate baseline before importing producer/creating output/
new model work; keep that owned record through completion (no reread). Only then
lazy-import CORE8 run_sequence_case and DemoError; invoke existing closed producer.
CORE8 remains authority for output guards: new folder,existing nonsymlink parent,
outside checkout,no overwrite; guards precede model execution. Do not duplicate
producer/scaling/limiter logic or relax guards. Exactly its3portable files persist;
workflow receipt is stdout,never an extra file inside package. No rollback/delete/
automatic retry/partial folder reuse on errors.

After run,read generated package once through CORE9. Canonical exact equality of
producer returned record and captured RESULTS required; otherwise
WORKFLOW_GENERATED_RECORD_MISMATCH_WORK_MAY_BE_NONZERO. Inspection/compare use the
same captured output. Compare with pre-captured baseline,never current disk baseline.
Producer DemoError => WORKFLOW_RUN:<DEMO_CODE>:WORK_MAY_BE_NONZERO(conservative even
if its guard actually did0work); generated read error =>
WORKFLOW_GENERATED:<INSPECT_CODE>:WORK_MAY_BE_NONZERO. Unexpected API errors propagate.
No erroneous0work claim after publication/inspection/compare/output failure.

## Report and exit contract

schema_version1,contract_id CORE11_CLOSED_SEQUENCE_WORKFLOW_V1;
mode CHECK_SAVED_ONLY or RUN_CLOSED_SYNTHETIC;execution_requested exactbool;
workflow_status SAVED_RECORDS_INSPECTED(no baseline) or CORE10comparison_status;
case_id,saved_status,saved_rejection_code,recorded_model_steps(currenthistorical);
new_synthetic_model_steps0incheck and captured recordedsteps inrun(3/3/0closedcases);
reader_model_executions0,reader_reference_executions0;
inspection(currentCORE9summary),baseline_inspection(summaryornull),comparison(CORE10ornull);
gates unchanged GATES;source_identity_reauthenticatedfalse;
scope INTEGRATED_CLOSED_SYNTHETIC_WORKFLOW_NOT_VEHICLE_OR_ORIGIN_AUTHORITY.
No caller paths/timestamps in receipt (stored opaque metadata remains stored data).

Exit0 valid orchestration/no baseline or identical baseline;exit1 baseline differs;
exit2 invalid/operational,no success receipt. This deliberately differs from CORE8:
saved DIFFERENT/REJECTED may validly exit0,including run. Read saved_status separately;
exit0 is not new numeric MATCH,approved r,regression arithmetic oracle or vehicle PASS.
Without baseline there is NO regression comparison. No hidden expected-output policy.
CLI ordinary errors fixed WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION or
WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO; WorkflowError retains fixed code.
Direct descriptor write loop inside handler handles partial writes/device failures;
already delivered partial bytes cannot be retracted; discard exit2 output.
Cache creation failure before dispatch:WORKFLOW_CACHE_IO_NO_MODEL_EXECUTION.
Private temporary cache prefix restored; no persistent check/output writes besides
explicit new run package. SystemExit/KeyboardInterrupt remain normal.

## Tests and verification

Missing-feature RED then literals for checkM/D/R0newwork,fullsummary,baseline0/1,
single8opens/noreopens,baselinecapturedbeforeexecution,numericvsmetadata distinctions;
run3/3/0modelcalls,exact3files,returnedvsrecord guard;invalidcase/baseline/output0work;
post-work source/publication/corruption/unexpected failures conservatively labeled,
partial output preserved. Real CLIcheck/run0/1/2/help/options/stdoutfailure;fresh
check import guard;canonicalrepeat,oldCORE10compat,inputbytes/modespreserved;
no calculator/runtime/CAN/r/actualinput. Unit fixtures/gates synthetic work nonzero.
Immutable baseline1147tests/259compile then final1147+newmethods/262/static/wheel;
one fresh reviewer/one RED->GREEN Critical/Important fix pass,no rereview.
Independent real API+CLI checks/runs twice,profile actual public synthetic steps,
oldmetadata expected to differ if source inventory changes,not numeric failure.
Source/Manifest/cloud consumer/refs/links checks;localcommits/keep-as-is,no approvalmenu.

## Unchanged boundaries

No installs/network/push/merge/PR/CI/HF writes/deletion. Preserve hostworktree/oldrefs/
evidence. Frozenwheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Inherited directCORE9 tupleminor remains,JSONintake builtin. Cooperative filesystem
not atomic/hostileFS/atime attestation;metadata not source authentication;positional
comparison and256detail/fullcount fromCORE10 remain. No new browser/visual claim.
Actualinput/F61/Controller/Runtime/CAN/actualr0;wholeunit/gate/setupsyntheticwork
NONZERO_NOT_AGGREGATED. R_BUDGET UNRESOLVED;StaticGateFAIL;r/T2/vehicle_scale null;
SOURCE_SCHEMA_UNQUALIFIED6000;Candidate/RuntimeNO_GO;D2PERFORMANCE_NOT_EVALUATED;
F19LEGACY_UNRESOLVED;NATIVE_EXACT_REPLAY NOT_PROVEN;F70UH/V/F71/activationNOT_ALLOWED.
