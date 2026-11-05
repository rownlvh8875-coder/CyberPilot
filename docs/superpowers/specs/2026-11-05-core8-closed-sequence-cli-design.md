# CORE8 — Closed Synthetic Sequence CLI

## Intent and approaches

Make CORE3~7 usable from one offline command with reproducible saved input,
diagnostics and checksums. Author chooses a **closed fixture catalog**, not a
new arbitrary JSON/log/vehicle reader. Fixed examples demonstrate MATCH,
DIFFERENT and late preflight rejection without inventing external provenance
or input policy. Arbitrary intake would need a separate schema/trust boundary;
stdout-only output would not retain a shareable checked package. Owner delegated
native offline decisions and opted out of repeated routine approval questions.

No model/CORE1~7/public-wheel changes. Existing CPython3.12.13 Linux/stdlib and
source loader; no installs/network/actual inputs/F61/Controller/Runtime/CAN/r.

## Files and APIs

- `integration_tools/core_sequence_cases.py`: inert CASE_IDS tuple
  ('sign-cycle','declared-difference','late-invalid') and build_case(case_id:str).
  No model imports until build_case is called after the existing loader.
- `integration_tools/core_sequence_run.py`: DemoError(ValueError).code,
  run_sequence_case(case_id:object,output:Path)->dict and exit_code(record:dict)->int.
  Lightweight import before model loading; fixed case validation and output guards
  before loader or calculation. Reuse scenario_run.load_model/source_identity and
  scenario_output.GATES/canonical, without modifying them.
- `tools/core_sequence.py`: argparse --case (required fixed choice), --output
  (required new directory), allow_abbrev=false, isolated cold private cache prefix
  like existing DEV CLIs. No --input/vehicle/r/time/scale options. Restore cache
  prefix in finally. Existing -I -B invocation supported from arbitrary cwd.
- One test module `project/test_core_sequence_run.py` and Korean usage guide.

## Fixed input examples

Four frames/three contexts, exactly the CORE7 literal fixture: raw requests
be800000,3f000000,bf000000,3e800000; sequence0..3, times1_000_000_000 through
1_030_000_000; same declared live context, synthetic scale16/16, up2/down5,
allowance7/factor1/multiplier3. Anchor entry7/saved-2,counter3/saved4; next entry/
saved commands-2/2,2/-2,-2/2 and counters4/5,5/6,6/7. All request/gate active true,
override/reset false. Context indices5/6/7, previous integer requests-4/8/-8,
driver1.5,angle85. These are fixture constants, not actual vehicle/T2/r authority.

- sign-cycle: states(6,8,2,5),(7,-8,-2,6),(8,4,2,7), allMATCH,3modelsteps,exit0.
- declared-difference: first target saved10; second entry10/saved5; third entry5/
  saved4. States(6,8,2,5),(7,-8,5,6),(8,4,4,7), statusesD,M,M, indices[0],
  aggregateDIFFERENT,3steps,exit1. Do not repair declarations or roll computed state.
- late-invalid: final context current_driver0.1, other fields unchanged;
  SEQUENCE_INPUT:2:MODEL_DRIVER, REJECTED, no completed transitions/rows, public
  modelsteps0 (validation/previous quantization may be nonzero),exit2.

## Guards, source and failure semantics

Require exact str case_id in catalog or DEMO_CASE, before touching output/model.
Output must be Path; reject existing target including dangling symlink
(DEMO_OUTPUT_EXISTS), nonexistent parent(DEMO_OUTPUT_PARENT), any symlink parent
or resolved target inside the checkout(DEMO_OUTPUT_LOCATION). Validate UTF8/noNUL;
other path/type/OS resolution errors ->DEMO_OUTPUT_PATH. No output creation or
model load/calculation on guard failure. Cooperative filesystem boundary, not
hostile-concurrency sandbox.

Use unchanged scenario_run.load_model(ROOT) to verify pinned runtime, imported
source hashes, package version/origin. Include its source_identity plus SHA of
tools/core_sequence.py as observation; recompute after calculation and reject
DEMO_SOURCE_CHANGED if different. Loader ScenarioError wraps as DEMO_SOURCE:<code>.
These are local byte observations, not source authenticity or vehicle qualification.

Call unchanged CORE7 on built fixtures. Only known preflight SequenceCheckError
codes (SEQUENCE_INPUT:*,SEQUENCE_MODEL_ORDER:*,SEQUENCE_TYPE/CONTAINER/COUNT)
produce saved diagnostic REJECTED with modelsteps0. SEQUENCE_TRANSITION:* or
other checker errors ->DEMO_CHECK_FAILED_WORK_MAY_BE_NONZERO with no package.
Unexpected runtime errors propagate in API; CLI reports fixed operational failure
exit2, no success artifact. No failure is converted to MATCH or silently skipped.

Assemble all bytes and check unchanged source before creating output directory.
Create directory exclusively; write fixed files exclusively, Manifest last.
OSError ->DEMO_PUBLICATION_FAILED_WORK_MAY_BE_NONZERO. Preserve any partial new
directory, do not delete/overwrite/resume or advertise it complete. Validation of
all Manifest members and file closure is required before trusting package integrity;
existence of any one file is not completion/authentication. No atomic rollback,
signed seal, hostile racing-directory guarantee or persistent run registry.

## Portable schema

Exactly INPUT.json, RESULTS.json, SHA256SUMS.txt. Canonical JSON sorted keys,
UTF8, no NaN, compact separators,newline. No timestamps/absolute workspace,
executable/output/cache paths in portable records, enabling same-source repeats.
Manifest contains exact sorted SHA256 entries for INPUT.json/RESULTS.json only.

INPUT: schema_version1, contract_id CORE8_CLOSED_SYNTHETIC_SEQUENCE_DEMO_V1,
case_id, scope CLOSED_DECLARED_SYNTHETIC_FIXTURE_ONLY, frames and contexts.
Preserve every dataclass field except raw requested_binary32 is explicitly named
requested_binary32_be_hex; driver/angle stored as current_driver_hex/
current_angle_deg_hex (exact binary64 hex), not decimal-reformatted authority.

RESULTS: same schema/contract/case/scope; status,rejection_code,sequence_completed,
frame_count,declared_transition_count,completed_transition_count,model_steps,
differing_transition_indices,rows,identity,gates (copy of unchanged GATES),
validation_claim ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT,
anchor_transition_checked=false,prehistory_checked=false,source_authenticated=false.
Each row: transition_index,status,model_index,entry_state,computed_next_state,
declared_saved_state{saved_limited_state,saved_angle_counter},differences (field/
declared/computed). Completed rows retain every CORE6 diagnostic. Rejected input
has sequence_completed=false, rows=[],counts0 and the exact rejection code;
it is not vacuous MATCH. CLI prints canonical summary(case_id,status,model_steps,
completed_transition_count), maps statuses0/1/2; operational errors print fixed
REJECTED code to stderr/exit2 and do not publish a success package.

## Verification and preservation

TDD real API/CLI tests: three literal outcomes/row values/inputs/source/gates,
two new dirs byte-identical, Manifest closure, unknown case/path guards before
import/steps, no overwrite/symlink/inside-checkout write, source change and
non-preflight failure no package, partial publication retained, fresh-process
light imports/help/invalid args, actual three exit codes and -I -B arbitrary cwd.
No mocks as numerical expectations; fault injection only IO/source/error boundaries.

Baseline1065tests/248compiles; final1065+actual new tests/252own compiles,
fullgate/static, independent actual CLI runs twice with literal output assertions,
one fresh whole-branch review, source custody/Manifest/refs/cloud consumer.
Frozen wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
Base82754868d8dd4d6824f1361419ebeecc96f93dd0, host linked worktree/local stacked
branch, preserve old runtime/CORE1~7/src/locks/workflows/imports/profiles. Only
four new Python files, guide/spec/plan and component README/backlog change.
No push/merge/PR/CI dispatch/HF/network/cleanup; retain all evidence.

Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED; STATIC_EVIDENCE_GATE=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; F70UH/F70V/F71/actualactivation=NOT_ALLOWED.
Synthetic model/quantization work nonzero; actual input/F61/Controller/Runtime/
CAN/actual r calculation0. This stage adds no general input origin certification.
