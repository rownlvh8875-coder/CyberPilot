# CORE12 — Bounded Closed Three-Case Suite

Base5c464c56e45e80dc67eee7031723423cc0c237b7. Owner delegated ordinary offline
development/no repeated approval questions. Author selects native CPython3.12.13/
Linux/stdlib,existing linked worktree/no installs/network. This is not new vehicle,
F61,rate policy or original-source authority.

## Approach and intent

Choose exactly the existing CASE_IDS in fixed order:sign-cycle,declared-difference,
late-invalid. A shell loop would scatter accounting and permit executing a prefix
before discovering a bad late baseline;arbitrary batch manifests add intake scope.
Use a bounded three-case coordinator with all-input preflight,captured records,
CORE11 per-case reports and explicit aggregate work/comparison counts instead.
Subset/custom case selection is not supported;CORE11 remains available for onecase.

## Files and interfaces

New integration_tools/core_sequence_suite.py:SuiteError(ValueError).code;
check_closed_suite(input_root:Path,baseline_root:Path|None=None)->dict;
run_closed_suite(output_root:Path,baseline_root:Path|None=None)->dict;
exit_code(report:dict)->int. Imports are inert(no producer/model/execution imports).
New tools/core_sequence_suite.py:required check/run subcommand;check --input-root,
run --output-root;both optional --baseline-root. JSON stdout only;allow_abbrev=false
at every parser. No cases/manifests/r/vehicle/format/output-summary overrides.
New project/test_core_sequence_suite.py,Korean guide,spec/plan;README/backlog updated.
In core_sequence_workflow.py extract post-baseline run body unchanged into private
_run_captured(case_id,output,captured_baseline)->dict;public CORE11 validates case,
captures baseline/applies overlap guard then delegates. Suite uses private _report
and _run_captured on loader-owned records only,not new arbitrary dict intake.
No changes to calculation/CORE8/CORE9/CORE10. Expected9paths/3newPythonfiles;
545registeredfiles/prior536preserved;265owncompiles(base262).

## Suite root capture

Each root contains exactly CASE_IDS child directories,nothing else. Each child is
an unchanged CORE8 exact3file package whose stored case_id equals its directoryname.
Require Path,UTF8/noNUL,nonsymlink root/parents. Open rootdirectory readonly with
O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC;list exactnames,stat each child directory
relative fd/follow_symlinks=false. Reject childlinks/files/FIFO/extra/missing case.
Inside root context read each child via CORE9 once;recheck root layout thenclosefd.
No recursive scan/manifest traversal. Current/baseline root each once with3child
directoryopens+9memberopens;bothroles=26opens(2roots+6childdirs+18members),not rereads.
FD rooted layout and Path child capture remain cooperative,not atomic/hostileFS
attestation. Same input/baseline path captured separately perrole.

Root errors SUITE_INPUT_ROOT/SUITE_BASELINE_ROOT;layout errors
SUITE_INPUT_LAYOUT/SUITE_BASELINE_LAYOUT. Child errors
SUITE_<ROLE>:<CASE_ID>:<INSPECT_CODE>;caseid mismatch
SUITE_<ROLE>_CASE_ID:<CASE_ID>. Fixed codes/messages only,no callerpaths/rawvalues.
All current and optional baseline records are captured before constructing reports.
Saved REJECTED is a validcase,not an operationalerror or skippedcase.

## Explicit check and run

check captures current and optional baseline,then builds3CORE11 check reports from
those same records with0newsteps. No producer import/model/native/reference/dt/r.
No output creation or optional execution fallback.

run preflights NEW output root:Path/UTF8/noNUL,noexistingpath/danglinglink,no
symlinkparents,existingdirectoryparent,outsidecheckout. Fixed output errors
SUITE_OUTPUT_ROOT/EXISTS/PARENT/LOCATION. Validate/capture ALL3baselinecases before
outputrootcreation,producerimport,ornewsteps. Reject output equal/nestedbaseline
root:SUITE_OUTPUT_BASELINE_OVERLAP_NO_MODEL_EXECUTION. No oldfolder overwrite,
automatic parentcreation,retry,cleanup/rollback or incomplete suite reuse.
Rootmkdir(exist_ok=false) failure SUITE_OUTPUT_CREATE_NO_MODEL_EXECUTION.

Run fixedcases in CASE_IDS order into output_root/case through CORE11 _run_captured,
passing captured baselinecase orNone. CORE8 retains child outputguards/publication;
CORE11 retains returned-vs-generated/case guard and single generated capture.
Reuse each returned CORE11report,no second reads of casefiles. At end check only
outputroot names/childdirectory kinds(no file reopens),then summarize.
Wrap caseWorkflowError as SUITE_RUN:<CASE_ID>:<WORKFLOW_CODE>:WORK_MAY_BE_NONZERO.
Post-run root errors SUITE_GENERATED_ROOT_WORK_MAY_BE_NONZERO or
SUITE_GENERATED_LAYOUT_WORK_MAY_BE_NONZERO. Unexpected API exceptions propagate.
Abort on first operationalfailure:preservecompletedcases/currentpartialroot and
do not start later cases. No success receipt/errorcase counted as validcompletion.
All generated/case/root/stdout/cache failures after run may have nonzero prefixwork,
including failure in a0-step finalcase after prior6steps. Never claim global0then.

## Aggregate report

schema_version1,contract_id CORE12_CLOSED_SEQUENCE_SUITE_V1;
mode CHECK_SAVED_SUITE or RUN_CLOSED_SYNTHETIC_SUITE;execution_requested bool;
case_ids listCASE_IDS,case_count3,all_cases_processedtrue;
suite_status SAVED_SUITE_INSPECTED(no baseline),SAVED_SUITE_IDENTICAL or
SAVED_SUITE_DIFFERENT;baseline_comparison_requestedbool;
saved_status_counts actualMATCH/DIFFERENT/REJECTED counts from3reports;
comparison_counts NOT_REQUESTED/IDENTICAL/DIFFERENT;
new_synthetic_model_steps=sum3newsteps;recorded_model_steps=sumcurrenthistoricalsteps;
reader_model_executions0,reader_reference_executions0;
difference_count null withoutbaseline else sumexactdifferencecounts;
difference_counts null withoutbaseline else sectionINPUT/RESULT/IDENTITY sums;
reports list3CORE11report,not only a lossy aggregate;gates unchangedGATES;
source_identity_reauthenticatedfalse;
scope CLOSED_THREE_CASE_SYNTHETIC_SUITE_NOT_VEHICLE_OR_ORIGIN_AUTHORITY.
No callerpaths/timestampmetadata (stored opaque paths remain stored data).

Exit0 valid inspected/no baseline or all identical;exit1 ANYcase differs;exit2
invalid/operational,no success summary. Saved D/R counts never become errors/PASS
authority. No baseline means comparison NOT_REQUESTED3/null differences,not zero
regression. Full metadata comparisons may differ after development source inventory
changes;no silent identityignore/numeric regression or performance inference.

CLI follows fixed CORE11 operational boundary:cache creation failure
SUITE_CACHE_IO_NO_MODEL_EXECUTION;cleanup completes before success stdout;prefix
restored;directdescriptorwrite loop+exit calculation inside operation handler.
Ordinary check error SUITE_CHECK_FAILED_NO_MODEL_EXECUTION;run error
SUITE_RUN_FAILED_WORK_MAY_BE_NONZERO;SuiteError retains fixedcode. Preserve normal
SystemExit/KeyboardInterrupt. Delivered stdout bytes cannot be retracted;discard
exit2 partialoutput. JSONreceipt stays stdout/outside suite;root has only3casefolders.

## Verification and preserved scope

TDD missingfeature then exactcaseorder/statuscounts/6recorded/check0/run6observed;
baseline0/1 andpercase18diff;no-baseline nullvs0;allbaselinepreflight beforework;
wrongcase/layout/links/FIFO/corruptthird reject0;baselinecaptured before external
test actor mutation;26readonlyopens/no reopening;inputbytes/modespreserved;
guard0/overlap/existing/rootlayoutpostwork;prefixpartialfailurepreservation/later
case notrun;newwork not hiddenby finalR;realCLI0/1/2,options/help,stdout/cachecleanup
failure, freshblockedcheck;deterministicJSON,CORE11bytecompat afterprivateextraction.
No originalF61/Controller/Runtime/CAN/vehicle/r execution. Unit/gate/setupsynthetic
work NONZERO_NOT_AGGREGATED. Immutable baseline1180/262;final1180+actualnew/265,
Ruff/Ty/Codespell/frozenwheel/source/Manifest/cloudconsumer/refs/links;onefreshreview,
one RED->GREEN Critical/Important fixpass/no rereview. Independent API/CLI suite
runs/checks twice with measuredstepcounts andbaselinepreservation.

No installs/network/push/merge/PR/CI/HFwrites/deletion. Preservehostworktree/oldrefs/
evidence;nativekeep-as-is/no routineapprovalmenu. Frozenwheel
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Inherited directCORE9tupleminor/owned-dicthelpers/cooperativeFS/nooriginproof remain.
R_BUDGET UNRESOLVED;StaticGateFAIL;actualr/T2/vehicle_scale null;
SOURCE_SCHEMA_UNQUALIFIED6000;Candidate/RuntimeNO_GO;D2PERFORMANCE_NOT_EVALUATED;
F19LEGACY_UNRESOLVED;NATIVE_EXACT_REPLAY NOT_PROVEN;F70UH/V/F71/activationNOT_ALLOWED.
