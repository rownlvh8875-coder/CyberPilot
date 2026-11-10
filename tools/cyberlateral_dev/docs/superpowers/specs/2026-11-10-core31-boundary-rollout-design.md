# CORE31 — closed boundary rollout reference audit

User accepted the proposed boundary extension and delegated routine offline decisions.
Small Python-only increment; preserve CORE30, original model, arithmetic, producers and CLIs.
Considered modifying CORE30 pins (reject: breaks its historical contract), generic replay
(reject: unnecessary intake surface), and a separate closed set (selected).

## Three new cases

All use synthetic scale16, UP2/DOWN5, driver allowance7/factor1/multiplier3 and driver1.5.
Driver bounds independently derive to[-16,16]. Inputs are explicit snapshots, not captures.

- inactive-resume: three transitions, current requests1/2,-1/2,1/4 and active false/true/true.
  Seed(index5,previous_request-4,previous_applied-2,counter4). Limited2/-2/2 but final0/-2/2;
  computed previous applied becomes0 before the resumed call. Rate bounds[-4,2],[-2,2],[-4,2].
  Angle85; counters0/1/2 and steer request false/true/true. Keep pre-gate limited and final separate.
- fault-reset: four transitions, requests1/2,-1/2,1/4,-1/4; active true,angle85.
  Seed(index5,-4,-2,88); outputs2/-2/2/-2 with counters89/90/0/1 and steer true/false/false/true.
  Model rule is counted<=89 for request and reset at counted91; false steer request does not
  zero active final torque. These are synthetic model boundaries, not hardware safety limits.
- rounding-ties: six transitions, requests1/32,3/32,-1/32,-3/32,+0,-0; active true,angle0.
  Seed(index5,0,0,0); exact products1/2,3/2,-1/2,-3/2,+0,-0 round ties-to-even to0/2/0/-2/0/0.
  Bounds[-2,2],[-2,2],[-2,4],[-2,2],[-4,2],[-2,2]. Counters0,steer true,fault false.
  Binary32 request words3d000000/3dc00000/bd000000/bdc00000/00000000/80000000 preserve signed zero.
  Integer zero and projected output zero are positive zero; request/product negative-zero hex persists.

## Interfaces and authority

`core_boundary_cases.build_boundary_case(case_id:object)` returns exact tuples of existing typed
frames/contexts; no model/quantizer call. Closed immutable literal tables, fresh objects per call.
First frame is a declaration anchor, not an executed/verified transition. Context/sample timestamps
are declared invocation-order markers, not elapsed dt, actual timing or policy period evidence.
`input_record(case_id,frames,contexts)` uses unchanged CORE28 structural serializer but explicitly
retags contract as CORE31_CLOSED_BOUNDARY_INPUT_V1; these are not additional CORE28 accepted cases.

`boundary_reference.expected_boundary(case_id:object)->dict` assembles full output records from
SHA-pinned hand vectors only. Reuse model-free CORE30 representation helpers, no model/oracle/
quantizer/rollout imports or calls while assembling expected records. Use bounded regular-file
single capture/hash-before-decode. Freeze vector and structural input identities after factory
TDD and before the first new boundary model/audit execution. Input hashes are structural guards
generated from factory bytes, not independent arithmetic or external source authority.

`core_boundary_audit.audit_boundary_case(case_id:object)->dict`: exact built-in closed case check
before reference I/O/catalog; reference identity then factory canonical input identity guard before
CORE27 once; reuse unchanged CORE30 `_observe`/`_paths` for complete selected records/full
LateralOutput, exact types/float.hex, sorted escaped pointer paths, count all/report first256.
No expected rejection case: all execution failures raise fixed BOUNDARY_AUDIT_EXECUTION_FAILED_
WORK_MAY_BE_NONZERO; result/comparison failures use RESULT_FAILED_WORK_MAY_BE_NONZERO.
BaseException propagates. No partial success, retry, fallback or replacement r/policy.

Receipt CORE31_CLOSED_BOUNDARY_REFERENCE_AUDIT_V1: audit status CLOSED_BOUNDARY_REFERENCE_
MATCH/DIFFERENT and audit_exit_code0/1; separate observed rollout status/exit, reported synthetic
model steps3/4/6, reference model steps0, numeric preflight nonzero, input/reference identities,
difference counts/paths, false source/prehistory/V4/F61/vehicle flags and unchanged gates.
Counters rely on unchanged CORE27; independent profiling is separate proof, not runtime attestation.
No arbitrary-object validator, Python/filesystem sandbox, atomic snapshot, timeout or signed provenance.
Fixed public error messages do not redact retained chained developer tracebacks.

## Files, proof and constraints

New factory/reference/audit modules, one two-class test file, vector JSON, Korean guide, spec/plan
(8newfiles). Only previous README/backlog/CORE30 guide links change. Keep all other prior bytes/modes/
refs/evidence. No new CLI/install/network/HF write/merge/push/PR/CI. TDD phases, two-run profiled
acceptance incl inactive/fault/zero mutations, fresh complete DEV gate, custody and one fresh
whole-range review precede unsigned evidence sealing. Existing baseline tests already executed;
preregistration is not blind/external validation. Only current fixed cases, not universal correctness.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71 NOT_ALLOWED. Actual inputs/F61/Controller/Runtime/CAN/
actual r/dt0; synthetic model and fixture work explicitly nonzero.
