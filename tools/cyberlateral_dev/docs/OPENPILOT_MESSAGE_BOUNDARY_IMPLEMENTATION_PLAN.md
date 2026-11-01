# R14 Synthetic Message Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans, inline TDD plus one fresh final review. FUTURE plan, NOT executed in R13. Routine questions are delegated; native/schema and vehicle restrictions remain binding.

**Goal:** Implement the R13 pure synthetic extraction contract, not an actual openpilot object reader.
**Architecture:** Exact immutable nested source-shaped carriers -> validating/copy-only extractor -> prepared public sample/state with explicit declared-only claims. Separate installed-wheel DEV probe. Keep R12's fixed registry/advance intact.
**Tech Stack:** Existing CPython3.12.13/uv0.12.23/stdlib and unchanged CyberLateral0.3.0; no dependency additions.
**Spec:** OPENPILOT_MESSAGE_BOUNDARY_DESIGN.md, OPENPILOT_MESSAGE_BOUNDARY_CONTRACT.json and OPENPILOT_MESSAGE_BOUNDARY_TEST_SPEC.md in this directory.

## Global Constraints

- No original/native/schema/Controller/Runtime/CAN/F61 import/execution/compile, actual/raw input, r/dt calculation, observer/capture, vehicle install or main merge.
- Preserve existing187 tests,77 imported bytes, runtime API/version/dependencies and sealed wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c (46646 bytes/27 RECORD).
- R12 DEV bridge/harness/registry and its golden records remain byte-unchanged. Do not route new arbitrary synthetic frames into R12.advance or relabel them as its fixtures.
- Only exact records defined in the spec; no duck typing, native objects, dictionaries/JSON/log/data loaders, callbacks or default/coercion/normalization/clamp recovery.
- Extraction performs zero step/simulate/quantization/model transitions. Output is NOT F61 constructor input, actuator output, next state, history proof or native qualification.
- Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL; Candidate/Runtime=NO_GO; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
- Native Q01-Q06 remain NOT_AUTHORIZED/NOT_RUN. They are not executable tasks of this plan; actual-reader API/runtime types stay null until separate qualification/amendment.

## Review Focus

- Nested foreign/subclass/property objects must reject before any foreign attribute/metadata operation (Task1 B03/B04/B07).
- Default-valued synthetic data must not be presented as native explicit-field presence evidence (Task1 B02/B23, Task2 B27; nativeQ03 stays closed).
- A valid alternative prior integer candidate is only a declaration, not verified history; labels must not promise R12-like prefix proof (Task1 B17).
- Initial index0 canonical custody vs resumed index1 state/changed scale must not be conflated or reset (Task1 B10/B14-B18).
- Signed-zero and Float32-style values must preserve exact supplied bits without native ABI/serialization claims (Task1 B19-B21, Task2 B27).

## Task1 — immutable carriers and pure extraction

Create integration_tools/message_boundary_types.py, integration_tools/message_boundary.py,
project/test_message_boundary.py. No other Python changes in this task.

Interfaces consumed: public Limits/LateralState/LateralInput from pure package0.3.0.
Full exact record field lists and constants are in the spec. Produces all seven
proposed records, MessageBoundaryError(code), and
extract_synthetic_message(frame:SyntheticBoundaryFrameV1)->PreparedLateralInputV1.

- [ ] Write failing B01-B24 tests with the exact names/assertions from the test spec, using literal controls, not expectations built by the extractor.
- [ ] Run `uv run --project tools/cyberlateral_dev --locked python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_message_boundary.py -v`.
  Expected: assertion FAIL for missing planned module/function, not an accidental import typo.
- [ ] Implement exact frozen/slots/no-default records and stable error.code. Verify builtin/exact nested types before attributes/operations, then the exact seven-code validation order. No original import, calls to properties or model work.
- [ ] Implement field-preserving pure mapping to LateralInput with provenance SYNTHETIC_ONLY, state unchanged, and exact declared-only output claims. No R12 API edits.
- [ ] Literal B01 assertion: prepared.sample equals LateralInput(0,1.0,0.0,0.0,True,Limits(16,2,5,7,1,3),SYNTHETIC_ONLY); state equals LateralState(0,None,0,0); custody_claim equals SYNTHETIC_DECLARATION_ONLY.
- [ ] B14 control: resume state(1,16,3,0) with explicit source applied2 rejects BOUNDARY_CUSTODY. B17 control: valid candidate15 with applied2/counter0 is preserved, never labeled history-verified. B18 keeps declared applied100/current scale5 without producing95 or19.0.
- [ ] B19/B20 assertions: -0.0 hex=-0x0.0p+0 and0.3 hex=0x1.3333333333333p-2 remain distinct from supplied0.30000001192092896. No Float32 coercion and no tolerance.
- [ ] B22 uses real valid extraction while package step/simulate/quantize are guarded to raise; prepared result still matches the literal. No expected assertions on mock behavior alone.
- [ ] Run targeted tests again and full component discovery. Expected all PASS, including all existing187; inspect output and actual test count.
- [ ] Run the existing full one-command gate at NEW output. Expected unit/static/owncompile/import/wheel/report/numeric/harness/R12 bridge PASS. Commit only these DEV files/tests with message `feat: add pure synthetic message boundary extraction [skip ci]`.

## Task2 — isolated prepared-input probe and acceptance

Create integration_tools/message_boundary_probe.py, project/test_message_boundary_probe.py,
reference/message_boundary_expected_v1.json. Modify integration_tools/verify.py and
README/docs only; no existing golden/runtime/dependency/workflow changes.

Consumes Task1 extract_synthetic_message and the exact records. Produces no-arg
run_message_boundary_probe()->dict and CLI main(argv=None) accepting only --output NEW;
verifier functions message_boundary_pair_summary(first:Path,second:Path)->dict and
verify_installed_message_boundary(root:Path,python:Path,output:Path,cwd:Path)->dict.

- [ ] Write RED tests B25-B28. Missing module/acceptance function must fail for the intended missing feature. Include full-artifact tampering of fields, float hex, custody/native claims and safety gates with recomputed checksums.
- [ ] Implement exactly four fixed probe frames from literal controls: base, resume, history-scale-change, signed-zero (base with request-0.0). Each has unique ASCII sequence label matching its previous record. Emit complete asdict prepared records plus separately recorded request/driver/angle float.hex and state/limits/labels; no model outputs.
- [ ] Author expected canonical payloads from the spec's literals independently of extraction. Persist their exact hashes in the new golden reference; do not call the extractor to generate its own expected answer. Keep the sealed imported reference entries untouched.
- [ ] CLI rejects existing files/directories/dangling links and unknown data/log/source/native/time/r options before work. Stage full payload, write SHA256SUMS, publish RESULTS.json last. Failures never publish designated PASS.
- [ ] Run fixed probe twice with the unchanged wheel offline/no-deps in an empty venv under -I/-B from unrelated cwd. Add only DEV glue path for script import, never src/reference/native selectors. Require actual installed package identity, NumPy absent and forbidden original modules absent.
- [ ] Acceptance verifies canonical JSON, full literal prepared records/hashes, exact source/profile/claims/gates, matching output pairs and Manifest; status/count-only or identically corrupted pairs reject. Retain current R12 gate unmodified and run both gates.
- [ ] Run full component gate from original and relocated minimal repository (include unchanged dedicated workflow fixture). Expected all existing187 plus actual new tests PASS; Ruff/Ty explicit config/Codespell/owncompile and sealed wheel PASS. Compare deterministic payloads, not whole timing/install logs.
- [ ] One fresh whole-change review; fix Critical/Important RED->GREEN in one pass, record Minor. Scoped skip-ci feature commit/push, explicit offline final-HEAD CI and downloaded checksums, existing Draft PR update. Do not merge/activate. Suggested commit: `feat: verify isolated synthetic message extraction evidence [skip ci]`.

## Native qualification is a separate future scope, not Task3

Q01-Q06 require actual installed/native/schema evidence. Native import prohibition
is not lifted by this plan, a module name, owner delegation or synthetic PASS.
Do not implement a pretend native reader using the new synthetic carrier classes.
After permitted qualification provides exact native APIs/classes/schema/presence/
ownership/precision facts, write a separate source-derived reader contract/plan.

## Plan self-review

Task1 produces exact records/extractor consumed by Task2; names/signatures match.
B01-B24 cover validation/mapping; B25-B28 cover installed artifacts/reproduction;
Q cases remain explicit unexecuted gates. Source-only Float32 declaration does not
become actual ABI proof. No guessed native signature or hidden data/time/r policy.
Routine local helper factoring/test grouping is left to the builder, not authority
selection, default values or native permissions. R13 does not execute this plan.
