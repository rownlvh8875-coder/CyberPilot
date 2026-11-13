# CORE70 — One-run reference audit publication

The author's next-feature choice under standing autonomous user instructions is a
usable retained result of CORE69: complete audit JSON, readable Korean Markdown
and checksum in one fresh external directory. This is not a new user-authored
requirement or a new authority claim. Keep existing Python/runtime/dependencies.

Approaches: shell redirection needs callers to manage incomplete files and has no
summary; a saved-result reader would need a new untrusted-record schema; directly
publish the one fresh CORE69 result using the existing exclusive publisher.
Choose the third: bounded complete output and no repeated arithmetic/admission.
The private summary consumes only the freshly returned trusted checker record.
There is no public renderer accepting arbitrary saved JSON in this feature.

## API and files

`integration_tools/recording_reference_workflow.py` exports
`publish_recording_reference(input_file: Path, input_sha256: str,
diagnostics_root: Path, diagnostics_sha256: str, output_root: Path) -> dict`.
Validate both exact lowercase64 digests before any caller paths. Reuse existing
CORE16 `_output` for absent/new external directory with existing parent before
input capture or reference work. Call unchanged CORE69
`check_recording_reference(input_file,input_sha256,diagnostics_root,diagnostics_sha256)`
exactly once. CORE69 retains whole admission/capture/source/worker/result checks.
No model step, fallback, input inference or extra worker invocation.

Serialize complete untouched result to `REFERENCE_AUDIT.json` using canonical
JSON with newline,1..2097152bytes. Generate `SUMMARY_KO.md`,1..65536UTF8bytes:
audit status/exit separate from saved/reference diagnostic statuses; input and
diagnostic SHA; historical model steps separate from new model0/reference steps;
shared admission and bounded declared-state/first-anchor/prehistory limitations;
all header difference names; all saved/reference diagnostic differing indices;
first20audit differing transitions with exact entry/next/saved state from both
sides and differing row field names. Missing sides explicit. Count total/shown/
omitted precisely; full JSON retains every row. No tolerance or repair.

Human-facing verdict labels: `참조 대조: 일치` or `참조 대조: 차이 있음`;
`저장 진단`, `참조 진단` retain MATCH/DIFFERENT. A genuine DIFFERENT diagnostic
can reference-match; report must not imply saved results are all successful.
No arbitrary input/context strings are interpolated; only checker-owned enums,
field names, digests, finite bounded integer state and counts. No HTML report,
browser visual qualification, or physical torque/time interpretation.

`SHA256SUMS.txt` contains sorted SHA lines for the two complete files. Construct
receipt and serialize <=16384bytes before mkdir. Receipt contract
`CORE70_REFERENCE_AUDIT_WORKFLOW_V1`,status `REFERENCE_AUDIT_PUBLISHED`,audit status/
exit, saved/reference statuses, two input identities, recorded_model_steps,
new_synthetic_model_steps0,new_reference_steps,helper counts,shared admission,
false six CORE66 authority flags,gates and hashes/byte_size of all three files.
Then reuse unchanged CORE16 `_publish(target, files)` exactly once and return.
No added source identity beyond what CORE69 already observes; hashes on new
files are integrity,not authenticated origin/build/vehicle provenance.

No overwrite/cleanup/retry. Existing `_publish` requests directory0700/files0600,
exclusive no-follow writes,complete readback and layout/directory identity checks.
Partial directory/files can remain on late errors;not atomic or fsync durable,
not hostile-host race qualification. No input copying,extracting,cache or temp
files by the workflow. Source/wheel/model/helper/prior API/schema remain unchanged.

## CLI and errors

`tools/recording_reference_workflow.py` requires exactly one each `--run`,
`--input-file`,`--expected-input-sha256`,`--diagnostics-root`,
`--expected-diagnostics-sha256`,`--output-root`. No abbreviation,duplicates or
r/dt/context overrides. Usage/SHA syntax checks before project imports. help0
does no work. After successful API publication,canonical receipt stdout<=16384.
Positive short writes finish;0/negative/error exits2,possibly preserving prefix
and full published directory. Never rerun checker on output failure. Restore
sys.path/dont_write_bytecode from cold entry. Audit0/1 only after publication;
all usage/operational failures2 with fixed code,never raw caller content.

API invalid pin: `RecordingReferenceError(RECORDING_REFERENCE_EXPECTED_SHA256)`.
Forward existing known checker/publisher errors without a success receipt.
New size/summary/receipt preparation failures use `ReferenceWorkflowError`:
`REFERENCE_WORKFLOW_PREPARATION_FAILED_WORK_MAY_BE_NONZERO`.
CLI usage: `REFERENCE_WORKFLOW_USAGE_NO_EXECUTION`.
CLI unknown error: `REFERENCE_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO`.

## Acceptance and exclusions

Test-first real fixture and worker: full literal3transition saved JSON,model0/
reference3,one checker+publish call;true diagnostic DIFFERENT/auditMATCH;coherent
forgery audit1;both missing/extra row sides;>20 differences and exact truncation;
both pins before paths;output path errors before capture/worker;late preflight
failure prefix0;unchanged originals;one capture each;serialize failures before
mkdir;size guards;publication/readback late failures preserve partial output;
CLI opt-in/unique flags/help/exit0/1/2/short/broken stdout/global restoration;
different output destinations yield identical three files/receipts. Prove no
hidden checker/worker retry. All old recording/source-reference tests remain.

Full DEV gate after freeze;expected363+3=366own compiles,2277+actual new tests,
unchanged wheel/reference pins and98Manifest. Fresh whole-branch review,normal
feature backup/main fast-forward and push under standing authority,then exact
main/push DEV+Cloud CI/artifact verification. Preserve external evidence.

R_BUDGET=UNRESOLVED,STATIC_EVIDENCE_GATE=FAIL,actual r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/RuntimeNO_GO,F70UH/F70V/F71/actual
activationNOT_ALLOWED. Actual Controller/Runtime/CAN/F61/vehicle input/capture/
actual r/dt/install/deploy0. Synthetic reference/helper/test work is nonzero and
whole-suite totals unaggregated. No full-domain/trace/rollout/first-anchor/
prehistory/security/origin/vehicle/performance qualification is inferred.
