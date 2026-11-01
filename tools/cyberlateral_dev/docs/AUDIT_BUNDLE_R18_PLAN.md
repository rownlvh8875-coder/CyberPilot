# Portable Fixed Audit Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export and validate one deterministic data-only fixed R16/R17 ZIP with no new model work.

**Architecture:** Snapshot-returning R17 acceptance feeds a canonical ZIP writer. Bounded exact-name/CRC/size/layout validation rematerializes only hardcoded data into private temp space and reuses complete existing authority checks.

**Tech Stack:** CPython3.12.13 stdlib zipfile/io/hashlib/tempfile/argparse; existing pinned DEV tools, unchanged package0.3.0.

**Spec:** AUDIT_BUNDLE_R18_DESIGN.md

## Global Constraints

- ZIP17 members, archive Manifest16 entries, copied data14; archive/total8MiB/member4MiB caps; ZIP_STORED/sorted/fixed1980 time/mode0100644.
- Only exact fixed R16/R17 pair data; no code/wheel/secrets/absolute paths in archive. Repository verifier required, not standalone authentication.
- Export/verify model/extractor/F61/r/dt work0; source9010 labeled separately. Existing producers/results/runtime/reference/goldens/deps/workflow unchanged.
- NEW export directory only; final ZIP published last. Verify read-only permanent state, private bounded temps only, no extractall.
- Actual r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED. No native/vehicle/main merge.
- [skip ci], existing feature/Draft publication, dedicated offline CI only.

## Review Focus

- Archive names may duplicate/traverse/alias/claim directories or executable modes: exact member list and layout rejection tests.
- Small compressed archives may declare huge unpacked data: size/compression/read caps test before materialization.
- Rewritten metadata/Manifest/paired report checksums must not promote poisoned evidence: complete payload tamper tests.
- Source paths may change after snapshot capture: snapshot/zero-work guard test.
- ZIP format timestamps/trailing bytes/environment differences must not masquerade as sample time or reproducible identity: canonical format/determinism test.

## Task 1: Snapshot exporter, bounded verifier and installed integration

**Files:** Create integration_tools/audit_bundle.py, project/test_audit_bundle.py. Modify handoff_audit.py (read_audit_pair wrapper), verify.py and README.md. Add this design/plan.

**Interfaces:** read_audit_pair(first_report:Path,second_report:Path,first_source:Path,second_source:Path)->tuple[dict,dict[str,bytes],dict]; audit_pair_summary retains existing return. write_bundle(evidence:Path,output:Path)->None; verify_bundle(path:Path)->dict; bundle_pair_summary(first:Path,second:Path)->dict; verify_installed_bundle(root:Path,python:Path,output:Path,cwd:Path)->dict; CLI main(argv=None) export/verify only. Private _collect_snapshot(root)->dict[str,bytes], _archive_bytes(payloads)->bytes, _verify_bytes(raw)->dict used by real boundaries and tests.

- [ ] RED test_export_and_verify_exact_payloads:14 source bytes preserved,17 exact members,16-entry Manifest, source SHA d6dfe2ba..0035fe/audit b3c41ca1..96d71a7,7/112/37, work0, unchanged gates, valid verification result.
- [ ] RED test_canonical_zip_metadata_and_determinism: repeat export bytes exact, sorted entries,1980 timestamp/mode0100644/stored, no volatile data/code/wheel, noncanonical headers/trailer rejected.
- [ ] RED test_reject_corrupt_source_before_output: bad report/source/gates/checksum/missing pair reject before output mkdir.
- [ ] RED test_snapshot_not_reread_and_zero_model_work: generate trusted fixtures, capture then mutate source paths; export uses old validated bytes while imports/step/simulate/extractor are forbidden.
- [ ] RED test_archive_member_and_path_rejections: missing/extra/duplicate/../absolute/drive/backslash/directory/symlink names reject before data materialization.
- [ ] RED test_archive_content_and_metadata_tampering: CRC, both poisoned source reports with rewritten checksums, BUNDLE gate/hash/README/Manifest edits all rejected.
- [ ] RED test_archive_resource_limits: archive8MiB+1/total>8MiB/member>4MiB/compressed payload rejects before private data validation.
- [ ] RED test_existing_output_and_failed_publication: output file/dir/dangling guard before source read; checksum-write failure leaves final ZIP absent.
- [ ] RED test_isolated_installed_bundle_pair: two exports+two verify processes in empty installed venv/-I/-B/no forbidden modules; full pair exact; altered receipt/output rejected.
- [ ] RED test_cli_verify_is_read_only_and_invalid_flags: verify prints canonical result/environment, archive bytes unchanged/no permanent output; invalid archive and unsupported --data/--native/--r/--dt/--extract flags reject.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_audit_bundle.py -v`. Expected10 planned-module assertion failures, no import errors. Implement exact interfaces minimally, rerun10 PASS.
- [ ] Run `uv run --locked python -B dev.py verify --output out/r18-run-1`. Expected240+10=250 PASS, Ruff/Ty/Codespell/98 owncompile/imported77/unchanged wheel/old+new pairs PASS, global Manifest94 entries. Commit only planned component files [skip ci].
- [ ] Fresh minimal git archive including unchanged workflow/new DEV venv full gate250 PASS; payloads/whole ZIP equal, not full log/install Manifest identity. One fresh whole-branch review; one RED/GREEN fix pass for Important/Critical if any, ledger rulings/minors.
- [ ] Push existing feature, dispatch cyberlateral-dev.yaml only; verify exact HEAD250 tests/94 Manifest entries/ZIP SHA, update existing Draft and external receipts. Preserve original source10/root statuses. No vehicle/main merge.
