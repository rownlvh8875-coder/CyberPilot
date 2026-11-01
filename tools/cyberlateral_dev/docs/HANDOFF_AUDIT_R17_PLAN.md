# Fixed Synthetic Handoff Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce validated112-row CSV/JSON and Korean handoff summaries without new model/extractor work.

**Architecture:** A stdlib report consumes the same snapshot returned by a factored strict R16 reader. Pair verification checks exact source-derived payloads and actual isolated environment; independent field-mapping tests guard the common projection.

**Tech Stack:** CPython3.12.13, stdlib, existing unchanged pinned DEV tools and package0.3.0.

**Spec:** HANDOFF_AUDIT_R17_DESIGN.md

## Global Constraints

- Fixed7 scenarios/112 rows/37 columns only; report model/extractor/F61/r/dt execution0.
- Existing R14/R15/R16 RESULTS, runtime/API/wheel0.3.0, references/goldens/deps/workflows unchanged.
- Exact input pair validation, same validated snapshot, output NEW only, AUDIT.json last.
- Actual r/T2/scale=null; R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED; no actual/native/vehicle/merge scope.
- All commits [skip ci], existing feature/Draft publication and dedicated offline CI only.

## Review Focus

- Source fields with similar names (quantized/driver/rate/limited/final/previous-requested/applied) must not be swapped: full raw-source mapping test.
- Signed zero/null and declared index1 seed must not be coerced into zero/blank/observed history: representation test.
- Validated paths changed after read must not silently change the reported snapshot/hash: snapshot test.
- Identical poisoned report pairs and rewritten checksums must not pass: all-file tamper test.
- Reports must not calculate/import the model or execute the extractor, including isolated CLI: import/call guard and installed tests.

## Task 1: Strict read-only audit projection and installed gate

**Files:** Create integration_tools/handoff_audit.py and project/test_handoff_audit.py. Modify lifecycle_validation.py, verify.py, README.md and R16 design environment wording. Add this design/plan.

**Interfaces:** read_lifecycle_pair(first:Path,second:Path)->tuple[dict,dict] returns validated snapshot and existing summary; lifecycle_pair_summary retains signature/result. write_audit(first:Path,second:Path,output:Path)->None; main(argv=None), CLI --first/--second/--output only; audit_pair_summary(first_report:Path,second_report:Path,first_source:Path,second_source:Path)->dict; verify_installed_audit(root:Path,python:Path,output:Path,cwd:Path)->dict. Private _render_audit(record:dict,source_sha:str)->dict[str,bytes] is projection, not a public arbitrary-data intake.

- [ ] RED test_complete_source_to_table_mapping:37 columns/all112 rows checked independently against source; explicit ramp first row previous null/0/0, quantized16, driver16, rate2, limited2, final2, normalized0.125, next1/16/2/0. JSON/CSV order and source SHA exact.
- [ ] RED test_signed_zero_and_declared_seed_labels: -0.0/-0x0.0p+0 preserved, prior null explicit, history seed/index1/normalized19.0; no native/time promotion.
- [ ] RED test_no_model_or_extractor_work: generate source fixtures first, then forbid model import/step/simulate/extractor; reporting succeeds with report counts0 and source counts9010 separately.
- [ ] RED test_reject_poisoned_input_before_output: bad source/gates/cuts/env/manifest and missing pair reject, no output dir. RED test_existing_output_and_failed_publication: existing file/dir/dangling/unknown flags do no work; checksum-write failure leaves AUDIT.json absent.
- [ ] RED test_report_pair_rejects_tampering: valid pair accepted then any AUDIT/CSV/SUMMARY/EXECUTION/Manifest content change, omitted/extra file, column order, prior state, seed/gate, canonical change rejects even when both reports/checksums are rewritten.
- [ ] RED test_validated_snapshot_not_reread: mutate input files after strict reader returns; output reflects only validated old snapshot/hash. RED test_isolated_installed_report_pair: two -I/-B processes/no model modules, complete pair accepted then mismatch rejected.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_handoff_audit.py -v`. Expected:8 intentional missing-feature assertion failures before implementation, not import errors.
- [ ] Implement exact interfaces/37-field projection and strict pair/source/canonical/checksum checks; update reader once-only snapshot and verifier. Correct R16 prose without behavior changes.
- [ ] Repeat8 targeted tests, then `uv run --locked python -B dev.py verify --output out/r17-run-1`. Expected:all232+8=240 PASS, Ruff/Ty/Codespell/96 owncompile/imported77/unchanged wheel/old+new pairs PASS.
- [ ] Commit planned component files with [skip ci]. Fresh minimal git archive including unchanged workflow/new DEV venv full verify. Expected240 PASS, deterministic payload/wheel equal, no whole Manifest identity claim.
- [ ] One independent whole-branch review, one RED/GREEN fix pass for Important/Critical if any; ledger rulings/minors. Push existing feature, dispatch only cyberlateral-dev.yaml, verify exact HEAD240/82 artifact entries, update existing Draft, preserve original roots/source10. Report actual final counts, receipts and restrictions.
