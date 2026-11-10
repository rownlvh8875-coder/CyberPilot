# CORE30 — closed rollout full-output reference audit

Builder-selected next offline increment under the user's standing delegation; no new approval menu.

## Intent and approaches

CORE29 proves fixed saved bytes, not arithmetic. CORE27's MATCH compares entry/saved-state
fields, not full model outputs. Add a separate explicit audit against hand-derived closed vectors.
Considered generic saved JSON replay (larger intake/authority surface), another byte report
(no numerical assurance), and fixed literal full-output audit (selected). This is a small Python
API increment, not a generic oracle, new model, CLI or F61 implementation.

## API and authority

`audit_rollout_case(case_id: object) -> dict` accepts exact built-in strings sign-cycle,
declared-difference, late-invalid; reject before reference I/O, catalog or execution otherwise.
Load SHA-pinned `reference/core30_rollout_expected_v1.json` via separate model-free reference
module; verify hash before JSON decode and before catalog/model work. Reference bytes are
developer-owned data, not arbitrary caller intake. Validate regular bounded capture with unchanged
CORE18 reader (single parent root using known filename; no caller paths). Expected assembly uses
only preregistered literals, structural mapping and float.fromhex restoration, never target helpers.

Before execution, build one closed case and compare its CORE28 `_input_record` canonical bytes
size/full SHA against the historical frozen input identity in the vector. This serializer is shared
structural code, not independent numerical authority. Catalog drift blocks instead of silently
running a different fixture. Run unchanged CORE27 once. Normal cases execute3 public synthetic
model steps; late-invalid is expected ROLLOUT_INPUT:2:MODEL_DRIVER with0model steps but nonzero
numeric preflight. Only that exact case/error becomes an observed rejection. Other exceptions
raise RolloutAuditError with WORK_MAY_BE_NONZERO; no partial success or false zero.

Observation compares rollout status/rejection/counts, initial/final states, per-row model index,
declared/computed entry, declared saved state, both difference lists, row status, full LateralOutput
(projection, quantization, driver/rate clips, fault/request/final command/next state), and CORE27
authority flags/contract metadata. It does not compare every prepared/input object; frozen input
identity is the separate guard. Reference and observation use exact built-in types; float equality
uses float.hex (no tolerance; distinguish signed zero). JSON-pointer differences contain paths
only, deterministic sorted object keys/positional arrays; report first256, count all, mark truncation.

Receipt: contract CORE30_CLOSED_ROLLOUT_REFERENCE_AUDIT_V1; audit_status
CLOSED_REFERENCE_MATCH/DIFFERENT, audit_exit_code0/1 independent of observed rollout
MATCH/DIFFERENT/REJECTED. Include case/reference SHA, input identity, observed rejection,
model step count, expected_reference_model_steps0, explicit numeric preflight nonzero, paths/counts,
false source/prehistory/F61/V4/vehicle flags, unchanged gates. No raw output or private paths in errors.
Pure in-memory audit except owned reference read; no output files/cache/temp in API invocation.
Import/initial bytecode are caller-managed (-I -B). No publication/deployment/vehicle qualification.

## Hand derivation

Scale16, UP2, DOWN5, allowance7, factor1, multiplier3, driver1.5, angle85, active true.
Driver raw bounds are16+(7+1.5)*3=41.5 and-16+(1.5-7)*3=-32.5; clamp to[-16,16].
Current requests1/2,-1/2,1/4 yield exact products8,-8,4 (no rounding ambiguity).
Computed previous applied-2,2,-2 gives directional bounds[-4,2],[-2,4],[-4,2], so outputs2,-2,2.
Normalized outputs±1/8 have binary32 words3e000000/be000000; integer±2 words40000000/c0000000.
State indices5,6,7 advance to6,7,8; counters4,5,6 advance to5,6,7; fault condition true,
steer_request true (counter<=89). Fault/request flag never substitutes for inactive gating.
Sign-cycle declarations match. Declared-difference entries-2/10/5 and saved10/5/4 yield entry
differences at1/2 and output at0/1/2 without reseeding. Late-invalid driver0.1 violates dyadic<=256
and all-input preflight rejects before any model step. These literals are not copied model outputs.

## Scope and completion

New vector, independent reference module, audit module, test file, guide, spec and plan (7files).
Only prior README/backlog/CORE27 guide links may change; all model/producer/CORE29 helpers
and frozen wheel stay byte-identical. TDD, deliberate live-output mutations, deterministic two-run
acceptance, full DEV gate, source/ref custody and one fresh whole-branch review precede sealing.
Actual r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL, SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71 NOT_ALLOWED. Original F61/Controller/Runtime/CAN/
actual inputs/r/dt0. No merge/push/PR/CI/HF writes. Model execution is explicitly synthetic/nonzero.
