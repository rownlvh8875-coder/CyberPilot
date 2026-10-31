# R15 Fixed Synthetic Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans, inline TDD and one fresh final review. User delegated routine choices; native execution remains prohibited.

**Goal:** Exercise unchanged R14 extraction -> pure model step -> owned continuation on the fixed catalog.
**Architecture:** A separate fixed runner emits full source/prepared/result traces; stdlib artifact validation reconstructs them from sealed inputs/results. Existing extractor/model remain untouched.
**Tech Stack:** Existing CPython3.12.13/uv0.12.23/stdlib/pure0.3.0, no new dependencies.
**Spec:** MESSAGE_HANDOFF_R15_DESIGN.md in this directory; existing R13/R14 contracts remain binding on their components.

## Global Constraints

- Preserve existing215 tests,77 imported bytes, runtime0.3.0 API/dependencies, R9/R12/R14 code/probes/goldens/catalog and wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
- No original/native/schema/Controller/Runtime/CAN/F61 execution/import/compile, actual inputs, r/dt, policy values, capture, deploy or main merge. Native Q01-Q06 remain NOT_AUTHORIZED/NOT_RUN.
- R14 copy-only0 steps is unchanged. New fixed runner has112 synthetic steps/process and0 prefix recomputation; not aggregate tests or actual time.
- Actual r/T2/scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual activation/F70UH/F70V/F71=NOT_ALLOWED.

## Review Focus

- A valid same-index but wrong prior candidate/counter/applied state returned by extraction must reject before the new model call, not self-heal.
- Incorrect source encoding or metadata/negative-zero substitution must reject before model work, even if types remain valid.
- history-scale starts at declared index1 seed; it must not be labeled observed prehistory, reset or clamped.
- Two identically altered frame/prepared traces with correct checksums must fail the complete acceptance gate.
- R14 extractor/probe0-transition contract and native/F61 prohibitions cannot be widened by adding the separate runner.

## Task1 — closed runner, full trace gate and installed integration

Create integration_tools/message_handoff.py, integration_tools/handoff_validation.py,
project/test_message_handoff.py. Modify integration_tools/verify.py and README/docs only.
Consumes R14 extract_synthetic_message(frame)->PreparedLateralInputV1, existing p.step
and fixed_catalog plus existing frozen golden; produces run_handoff_chain()->dict,
HandoffError, output-only main, handoff_pair_summary(first:Path,second:Path)->dict,
verify_installed_handoff(root:Path,python:Path,output:Path,cwd:Path)->dict.

- [ ] RED test_fixed_chain_full_golden_and_owned_trace:7/112 exact frozen results; ramp commands[2,4,6], inactive[2,0,0,2], history-scale command95/normalized19.0 with unobserved seed label, complete prepared state matches immediate prior output.
- [ ] RED test_catalog_or_version_drift_before_work: bad identity rejects before extract/model; test_source_encoding_mismatch_before_model: changed valid request fails HANDOFF_PREPARED_MISMATCH with no model call.
- [ ] RED test_wrong_owned_state_is_not_repaired: modify valid resumed prior candidate only; fail HANDOFF_PREPARED_MISMATCH after exactly one previous call. test_model_error_and_output_corruption_reject: chained ValueError, wrong output type and altered result reject without fallback.
- [ ] RED test_trace_and_gate_tampering_rejected: full independent frame/prepared/catalog/result/seed/claims/gates and canonical JSON checks, including identical poisoned pairs with recomputed checksum. test_existing_outputs_and_failed_publication: output guards/unknown modes/last publication.
- [ ] RED test_isolated_installed_pair: actual empty-venv wheel, -I/-B, no NumPy/original imports, same bytes; test_repeat_has_no_hidden_state: deterministic independent runs.
- [ ] Run `uv run --project tools/cyberlateral_dev --locked python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_message_handoff.py -v`. Expected intended missing-feature assertion failures, not typos.
- [ ] Implement exact runner/trace/state/seed/error contracts from spec, then stdlib artifact reconstruction/acceptance. Keep validation outside existing large verify.py; add thin installed-stage wiring there. Do not produce expected results from the runner itself.
- [ ] Repeat targeted and full tests. Expected all existing215 plus actual new tests PASS; inspect count/logs. Run full one-command gate at NEW output, explicit Ruff/Ty/Codespell/owncompile/import/wheel/all pair checks PASS.
- [ ] Commit scoped skip-ci feature work, run full gate in separate archive/new venv including unchanged dedicated workflow. Compare deterministic payloads, not full logs/installation Manifest identity.
- [ ] One fresh whole-change review; fix Critical/Important RED->GREEN in one pass, ledger Minor/declined scope. Scoped push/explicit final-HEAD offline CI/downloaded checksums/existing Draft PR update, no merge or native activation.

## Self-review

One coupled deliverable: runner traces consumed by independent JSON gate and installed
wrapper; signatures match. Each Review Focus line has a named negative test above.
Only controlled synthetic owned continuation is newly established; first seeds,
native custody, rate policy and actual vehicle readiness are explicitly not proven.
Helper factoring and descriptive test grouping are local choices, not authority.
