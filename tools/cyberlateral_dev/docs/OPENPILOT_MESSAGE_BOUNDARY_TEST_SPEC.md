# R13 — future boundary tests, NOT executed tests

Every case below is NOT_IMPLEMENTED_NOT_RUN. R13 adds zero executable tests.
The existing187 regression tests are separate execution evidence, not these cases.
Authoritative record fields/validation order: OPENPILOT_MESSAGE_BOUNDARY_DESIGN.md.
No new numerical oracle, F61 inputs, output commands or r/dt result is expected.

## Literal controls for future pure extraction

Base frame: schema1, exact metadata from design, sequence A, invocation0;
cc=SyntheticCarControlV1(SyntheticActuatorsV1(1.0),True);
cs=SyntheticCarStateWrapperV1(SyntheticCarStateValuesV1(0.0,0.0));
consumed_limits=Limits(16,2,5,7,1,3);
previous=SyntheticPreviousV1(ENTRY_BEFORE_CURRENT_LIMITER,A,None,0,0,
LateralState(0,None,0,0)). Explicit metadata strings are required, not defaults.
Expected sample=LateralInput(0,1.0,0.0,0.0,True,limits,SYNTHETIC_ONLY),
state=LateralState(0,None,0,0), with the declared-only claims from the design.
No call to step/simulate is permitted in extraction; command2 is NOT its output.

Resume control: invocation1, previous_invocation_index0, previous source applied2/
counter0, model state(1,16,2,0), same A. Preserve that state, do not reset it.
History control: invocation1, scale5/UP5/DOWN5/ALLOWANCE0/FACTOR1/MULTIPLIER1,
request0.0, previous source applied100/counter0, state(1,100,100,0), previous index0.
Preserve applied100 despite current scale5; do not calculate a new output.

## Synthetic test cases (28)

| ID | Future test name | Exact behavior / assertion |
| --- | --- | --- |
| B01 | test_literal_nested_field_mapping | Base control returns exact sample/state and metadata; no original objects |
| B02 | test_records_immutable_and_closed | Frozen/slots; no defaults; absent/extra kwargs TypeError; input unchanged |
| B03 | test_native_like_and_subclass_rejected_before_properties | Raising-property object or record subclass -> BOUNDARY_RECORD_TYPE without callback |
| B04 | test_missing_nested_record_no_defaults | None at cc/actuators/cs/out/previous/limits/state -> BOUNDARY_RECORD_TYPE |
| B05 | test_scope_and_representation_rejected_first | Production/schema-bool/wrong context/settings/representation -> BOUNDARY_SCOPE even with later faults |
| B06 | test_source_profile_and_package_identity | Wrong profile/source-set or package version -> BOUNDARY_SOURCE_PROFILE, no auto-upgrade |
| B07 | test_builtin_metadata_before_operations | Hostile str/int/field objects never receive comparison/hash/regex/coercion callbacks |
| B08 | test_sequence_ascii_and_cross_caller | Empty/Unicode/65 chars/subclass/mismatched previous sequence -> BOUNDARY_SEQUENCE;1/64 ASCII accepted |
| B09 | test_order_is_explicit_not_elapsed_time | Bool/negative/4096 current index, gap/duplicate/reset or different state.index -> BOUNDARY_ORDER |
| B10 | test_first_and_resume_adjacency | Base previous index None; resume previous index0; wrong/missing index -> BOUNDARY_ORDER |
| B11 | test_all_numeric_domains_without_coercion | Request/driver/angle NaN/inf/text/int/NumPy or active nonbool -> BOUNDARY_DOMAIN; no model work |
| B12 | test_limiter_domain_no_vehicle_fallback | Missing/wrong scale, MAX0/2049, UP/DOWN/ALLOWANCE65/250, FACTOR/MULTIPLIER9 -> BOUNDARY_DOMAIN; no409 fallback |
| B13 | test_state_field_domains | Prior applied/candidate outside[-2048,2048], bool, counter91, index0 candidate non-None or index1 None -> BOUNDARY_DOMAIN |
| B14 | test_mismatched_source_previous_applied | Resume model applied3 vs explicit source2 -> BOUNDARY_CUSTODY, not repair/reset |
| B15 | test_mismatched_source_counter_or_phase | Resume counter1 vs source0 or wrong entry stage -> BOUNDARY_CUSTODY |
| B16 | test_noncanonical_first_state | At index0 nonzero applied/counter -> BOUNDARY_CUSTODY; missing state never auto-initializes |
| B17 | test_prior_candidate_is_declaration_not_proven_history | Valid resume candidate15 vs16 is preserved with SYNTHETIC_DECLARATION_ONLY, never falsely history-certified |
| B18 | test_resume_history_survives_scale_change | History control preserves100 and scale5; no clamp, rescale or new output |
| B19 | test_signed_zero_exact_bits | request-0.0 remains hex -0x0.0p+0; driver/angle signed-zero bits preserved too |
| B20 | test_binary64_not_implicitly_float32 | request0.3 remains hex0x1.3333333333333p-2; supplied0.30000001192092896 is distinct and not coerced back |
| B21 | test_driver_angle_dyadic_subset | driver/angle0.1 rejected BOUNDARY_DOMAIN;0.5 accepted; request0.1 allowed within its distinct domain |
| B22 | test_extraction_no_model_or_native_execution | Patch real package step/simulate/quantization to raise; valid extraction still prepares exact input, imports no original modules |
| B23 | test_no_time_r_or_output_actuator_api | r/dt/frame/timestamps/CC.enabled kwargs TypeError; output has no command/CAN/F61 args/next_state |
| B24 | test_retry_and_interleaved_extraction_have_no_hidden_state | Same frame deterministic, caller A/B independent, no session manager/writeback or persistence claim |
| B25 | test_empty_installed_environment_probe | DEV-only fixed probe under -I/-B with unchanged installed wheel, unrelated cwd, no NumPy/native/source selectors |
| B26 | test_new_output_only_and_last_publication | Existing file/dir/dangling link/unknown log/data/native mode rejects before work; checksum write failure publishes no RESULTS.json |
| B27 | test_full_artifact_and_gate_acceptance | Exact prepared sample/state/hex/claims/gates and Manifest; two identically corrupted outputs with recomputed checksums reject |
| B28 | test_pair_reproduction_and_unchanged_wheel | Fixed probe twice byte-identical; existing187 discoverable;77 imports and sealed0.3.0 wheel unchanged |

B17 deliberately marks the limit of this boundary: it cannot verify past arithmetic
from a supplied state. Do not turn this into permissive native acceptance or weaken
R12's trusted-prefix rejection tests. Native actual custody remains unresolved.

## Native qualification cases (6), separately scoped and NOT_AUTHORIZED

| ID | Future qualification | Required observation, never assumed from mock/source |
| --- | --- | --- |
| Q01 | closed_runtime_and_schema_receipt | Actual installed/native hashes, loader/CarState/CarControl schema closure including c++.capnp; missing/mismatch blocks |
| Q02 | real_reader_builder_schema_and_lifetime | Actual API/classes/schema identities, ownership and lifetime/error behavior; wrong-schema generic class rejected |
| Q03 | explicitly_written_fields_vs_defaults | Independent controlled construction ledger; missing torque/active cannot pass because default0/False looks valid |
| Q04 | float32_assignment_and_readback | Record actual type/hex/sign before/after owned serialization for0.3,-0.0,+/-1, subnormal/normal boundary, NaN/inf/overflow; IEEE references are not observed ABI results |
| Q05 | coherent_call_entry_capture | Synthetic CC, CS.out, consumed limits/source-state/model-bookkeeping share one controlled boundary; crossed/mutable/concurrent capture rejects |
| Q06 | fail_closed_native_profile | Missing qualification/wrong schema/unsupported numeric readback cannot activate reader or widen model domain; no actual inputs/Controller/r/dt |

Q cases do not enter R14's executable task list. A future native-only scope and
source-derived amendment are necessary before an exact reader API can be specified.
No passing status is assigned until real permitted execution supplies evidence.
