# F-70U Static Vehicle and Control Context Binding Contract

## Identity and purpose
Cyber Validation. User-authorized static schema and validator; no vehicle activation or rate-budget computation.
Base: `deeb6442394468b4759081aa74e6e889f78357da`.
Branch: `feature/f70u-static-context-binding-contract`.
Acceptance: valid schema, exact provenance, deterministic generation, new tests, unchanged exact61/compat2/83, quality gates and exact-head CI.
`CONTRACT_SCHEMA_VALID` and `STATIC_CONTEXT_INSTANCE_UNRESOLVED` are separate results.

## Original references
Official opendbc is pinned to the baseline gitlink `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
Every source record carries repository, exact commit where tracked, path, symbol, line range, full-file SHA256 and excerpt hash.
The external sealed F61 API is not a tracked baseline file. Its full-file hash matches F68 E02;
its commit is null rather than falsely assigning it to the baseline tree. It was read statically and never imported.
F70PR reference and workflow are immutable inputs. The compatibility checks are two executable gates in the old workflow;
its separate local two-test file was external evidence, not a tracked baseline file.

## Changes and expected effect
New independent documents, JSON contracts, validator, tests and CI only. Existing files remain unchanged.
Owner statements: Hyundai, 더뉴싼타페 TM, 2021, 2.2 diesel, Prestige. Region is unknown.
These statements authorize neither firmware matching nor selection of flags, safety parameters or control modes.
Four Santa Fe catalog records remain separate. A 2021-23 alias is a documentation hint, not owner identity evidence.
Candidate exclusions and applicable years are descriptive; no fixture or numeric performance result enters selection.

### Schema and instance
The schema fixes field names/types, null rules, provenance grades, static/dynamic boundary and selection rules.
The instance contains registered facts and explicit unresolved values. Schema-valid does not mean vehicle-bound.
`static_context_input_template.json` is an unresolved schema-shaped template, not an owner approval.
`static_context_contract.json` is the current versioned static record. Future owner facts require F70U-A and a new version;
the validator never turns null into a default or accepts an unregistered vehicle value as authority.
Unknown keys are rejected at every object boundary, including nested metadata. JSON duplicate keys, floats,
NaN/Inf, non-UTF8 and non-string object keys are rejected. Integers and JSON booleans retain distinct types.
Canonical JSON: UTF-8, sorted keys, compact separators, no float representations, exactly one LF. No normalization of owner text.
SHA256 covers these exact canonical bytes. No wall clock, PID, locale, absolute worktree or cache paths enter outputs.
The JSON Schema uses the documented subset `type/properties/required/additionalProperties/items/const` of Draft 2020-12.
The standard-library validator implements that subset and additional semantic cross-field rules; it is not a general JSON Schema engine.

### Selection and provenance rules
Platform: exact pinned platform ID plus independent owner scope authority and unique firmware/fingerprint mapping.
Safety: exact pinned `CarInterface._get_params` derivation and approved static inputs, never execute CarInterface.
Modes: versioned explicit owner configuration; stock ACC, pcmCruise and openpilot longitudinal must be consistent.
No marketing-name fallback, cross-platform fallback, dynamic observation or test fixture can establish a required binding.
Each field has required_for_contract, required_for_r_budget, required_for_runtime, static_or_dynamic, current_status,
evidence_class and provenance IDs. Unknown values use UNRESOLVED; TEST_ONLY, DOCUMENTATION_ONLY and INFERRED cannot authorize required values.
Catalog alternatives are not two accepted conflicting owner bindings. Actual contradictory assertions are rejected;
the current instance has no selected platform and no contradictory accepted claims.
Source hashes and excerpts are locked in the schema source registry. Validation detects a changed source/field record.
This detects mutation against the registered version; it does not independently prove institutional owner authority.

### Signals and time
F61 `FeasibilityInput.native` and previous_command are caller-declared normalized scalars in [-1,1].
Its rate_budget_per_s is a caller-supplied finite nonnegative scalar in normalized_command/s; no default and no approved project budget.
F61's stage is its public synthetic input before interval feasibility, with mathematical sign only.
No physical left/right mapping, production clipping/filter stage or actual controller consumption is attested.
F70PR consumes a caller-declared synthetic interval, exact rational endpoints and adjacent integer-nanosecond timestamps.
Its context_id is a synthetic label, not a vehicle identifier. Its output is interval/nonemptiness evidence, never an actuator command.
F70U defines canonical ns and exact positive endpoint delta divided by 1000000000 seconds; no F61 float rounding is added.
The physical control period remains null. Upstream DT_CTRL=0.01 is a source nominal, not proof of the user's vehicle timing.
F70U does not execute the reference with a newly constructed production context or compute a new r.
The preserved synthetic regression suite still executes its original declared synthetic fixtures.

### Limiter boundary
The unbound source candidate is opendbc/car/lateral.py::apply_driver_steer_torque_limits at the pinned commit.
Caller: Hyundai CarController.update multiplies normalized requested torque by STEER_MAX, rounds to integer,
applies driver-torque and state-dependent slew limits, then fault/inactive gates, previous-state storage and CAN encoding.
DELTA_UP is magnitude-increase related; DELTA_DOWN is not a universal negative-direction rate.
No raw DELTA values are assigned to signed L_up/L_down. No production limiter is imported or called.
Static requirements include exact platform, complete flags, modes, normalization/stage mapping and limiter parameters.
Dynamic requirements are names only: requested torque, previous applied torque, driver torque, latActive,
steering angle, fault counter, reset state and sample endpoints. None are supplied as current static values.
HDA labels do not prove CAN-FD or SCC origin. Camera/radar SCC booleans refer to SCC command origin,
not the mere physical presence of both camera and radar sensors.
The schema rejects incompatible architecture assertions or an HDA2 assertion without pinned applicable authority;
it does not invent a universal HDA2-to-CAN-FD rule.

## Regression risk and acceptance
Fail closed on missing required definitions, unknown keys, wrong baseline/repository, false resolved claims,
unregistered values, conflicting evidence, unsafe dependencies, contradictory SCC/architecture/control-mode assertions,
invalid normalization/time, dynamic state disguised as static input and changed provenance hashes.
All five dependency flags are false. Validator source imports only standard-library JSON/hash/dataclass/path utilities.
No Controller/Runtime/RLOG/private source loader is imported. Only reviewed metadata files are read.
No threshold, acceptance criterion, reference formula, test ID ledger, physical setting or safety enforcement is changed.
No blanket test discovery: the exact approved Controller-free suites and the new F70U suite define verification scope.
Rollback: discard this new branch's additions; no existing path needs repair.

## Validation method and actual results
Actual commands and results are in external F70U evidence and exact-head CI; this preregistered spec does not predict counts.
Local generation emits schema, input template, candidate map, validation result, canonical contract bytes, hash and final result twice.
The generator consumes the immutable schema/record as authoritative definitions; it does not discover a vehicle or solve r.
Replay, simulation, shadow, hardware and road application: NOT_RUN / not authorized.

## Handoff
Preserve F64 historical failure, R_BUDGET_UNRESOLVED, SOURCE_SCHEMA_UNQUALIFIED=6000,
candidate NO-GO, D2 PERFORMANCE_NOT_EVALUATED, F19_LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY_NOT_PROVEN, RUNTIME_NO_GO and incomplete prospective/actual performance evaluation.
F71 remains unauthorized. With an unresolved instance the next permitted stage is F70U-A owner static context decision/approval.
No new vehicle data collection is requested or authorized. Missing static evidence stays missing.

## Attribution
opendbc excerpts are static evidence only and retain the following upstream license notice.

```
Copyright (c) 2020, Comma.ai, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

```
