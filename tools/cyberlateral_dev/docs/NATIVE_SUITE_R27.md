# R27 — explicitly selected fixed R19–R26 native suite

Baseline1441749ad5ec4fe7355b0435d18151dea42b1890. User approved the proposed
offline integrated gate:one command, fail closed on missing/mismatched records,
one report distinguishing verified fixed cases from unsupported real capabilities.
Ordinary design/inline/feature-Draft choices remain delegated to the executor.

## Approach

Keep every existing qualifier/worker/model/reference/API/default pure CI unchanged.
Add a separate stdlib-only parent runner that calls the existing qualifier eight
times in fixed order. Adding this to default CI would silently open native work;
merely concatenating PASS strings would not verify artifacts. Neither is chosen.
No stage selector/skip/override/actual data/r/dt flags; no dependency installer.

CLI: native_qualification/suite.py --fixed-native-suite --python /abs/native-python
--wheel /abs/pinned-native.whl --package-wheel /abs/sealed-public.whl
--output /abs/NEW-suite-dir. Output parent must already exist. Missing explicit
opt-in/non-bool API selection, existing/dangling output, wrong wheel/schema or
missing interpreter reject before any worker. Native/runtime guards stay in the
existing qualifier. Parent imports no capnp, NumPy, model or original application.

## Registry and data authority

reference/r27_suite_profiles_v1.json is SHA-pinned and contains exactly ordered
R19,R20,R21,R22,R23,R24,R25,R26; their mode keyword/status/complete observation
SHA/case-record count/model steps per worker/reference SHA/exact tool-source keys.
These are retained identities, NOT a new numerical oracle or physical claim.
Source:previous sealed R26 ZIP3b90aed1c3a445312967ad3fdb219ca0391410929f9b5589c0b09272b6e70d4f.
Test-only r27_stage_records_v1.json retains complete canonical observation and
summary records from those eight outputs, not private environments or executable
archive contents. Tests label fake process receipts explicitly; they do not claim
native execution. Existing R22–R26 references remain authoritative for arithmetic.

suite_profiles.py: frozen Profile records,load_profiles()->tuple[Profile,...],
get_profile(stage_id)->Profile; no caller-supplied registry, SHA pin/fresh loads,
exact fixed IDs/modes. Metadata is committed before any R27 suite execution.

## Stage validation

suite_validation.validate_stage(directory:Path,stage_id:str)->dict.
Require exactly OBSERVATIONS.json,SUMMARY.json,RECEIPT_1.json,RECEIPT_2.json,
SHA256SUMS.txt; regular non-symlink files, bounded2,000,000 bytes each. Compare
the exact four-line manifest, not unchecked paths supplied by it. Every JSON must
be canonical and a dict. Complete observation SHA must match its historical pin.
R22–R26 must additionally pass existing validate_coverage (including full input,
output, adjacency, claims and reference checks). No PASS-by-worker-agreement only.

Compare the entire summary with expected exact typed fields:status, observed SHA,
workers2,byte-identical true,reader NOT_IMPLEMENTED,actual input NOT_ALLOWED,
R_BUDGET UNRESOLVED,Static Gate FAIL,F61/r/dt0,derived model count. Numerical
modes also require exact per-worker count/scope/reference. Tool-source key set
must match the profile; each digest must match current bounded trusted source
bytes, resolving run.py/worker.py aliases only inside the component. No arbitrary
path read from untrusted manifests. Receipt dictionaries are retained, NOT OS or
execution authentication. Failures never become a successful row.

Stage row fields:stage_id,status,observations_sha256,summary_sha256,reference_sha256,
case_count,worker_processes,model_execution_per_worker,model_execution. No
environment-dependent receipt hashes in the portable summary.

## Suite orchestration, report and publication

suite.run_suite(python:Path,wheel:Path,package_wheel:Path,output:Path,*,enabled:bool=False)->dict.
Validate preflight once, run all8 stages sequentially in a private temporary
sibling directory, then validate each stage and its returned-summary hash.
Abort on first failure; do not run later stages, publish a partial PASS, retry,
or fall back. Existing per-mode output bytes and behavior must remain unchanged.

suite_report.build_summary(rows:list[dict])->dict and render_report(summary)->str
require exact ordered8-row coverage and strict counts/pins. Summary/report state
8 stages/16 workers and model calls0/0/0/10/8/198/40/198=454 for THIS suite only.
Two designated fresh suites total908 model calls; unit/reviewer/CI work additional,
not an aggregate total. No new native numerical domain or original reader opens.
Capability inventory separates fixed synthetic qualification from generic native
reader NOT_IMPLEMENTED,actual custody NOT_QUALIFIED,r policy UNRESOLVED,Static
Gate FAIL and deployment NOT_ALLOWED. Case counts are cases-array records, not
test totals or all construction/rejection experiments; R19 has no such array.

After all8 pass, create SUITE_REPORT_KO.md,SUITE_RECEIPT.json,SUITE_SUMMARY.json
and root SHA256SUMS.txt in staging. Receipt holds environment paths and per-stage
manifest/receipt hashes; no receipt equality or OS attestation claim. Root
manifest covers43 files (8*5+3), excluding itself. Reserve final dir with exclusive
mkdir; hard-link staged files on the same filesystem without overwrite, summary
last as the atomic success marker. Failure before publication leaves no final
dir; link failure may retain an explicitly incomplete dir WITHOUT summary. No
whole-directory atomicity/concurrent-host security claim. Never reuse outputs.

## Reproduction and gates

Public0.3.0/source/API/lock/wheel/default pure workflow/frozen77 and original
10 source guards unchanged. Native suite stays explicit and native GitHub CI
NOT_RUN. Full pure tests/static/wheel gates, fresh primary+archived new dev/native
env suites, independent data checks, one fresh final review, exact-head pure CI,
Draft PR update and deterministic external evidence seal are required.
Success:F70UGZ_R27_FIXED_NATIVE_SUITE_PASS; existing individual status strings
retained. Pure default status does not become native qualification.

No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment/main merge.
R_BUDGET=UNRESOLVED;Static Evidence Gate=FAIL;r/T2/vehicle scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000;Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED;F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN;activation/F70UH/F70V/F71=NOT_ALLOWED.
