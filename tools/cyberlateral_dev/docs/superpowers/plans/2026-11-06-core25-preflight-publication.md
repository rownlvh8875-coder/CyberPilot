# CORE25 Preflight Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save unchanged input preflight JSON/Korean Markdown/checksum through a single exclusive checked local workflow.

**Architecture:** One corresponding CORE23 call, all serialization before mkdir, unchanged CORE16 output validation/publisher; deterministic receipt with current compatibility separate from publication success. Thin CORE24-style CLI, no numerical/publisher rewrites.

**Tech Stack:** Configured cooperative Linux CPython3.12.13,stdlib/unittest/Ruff/Ty/Codespell,frozen wheel.

**Spec:** [design](../specs/2026-11-06-core25-preflight-publication-design.md)

## Global Constraints

- SHA format before all caller path work; existing/invalid output before capture; complete report/serialization/status before mkdir.
- Exactly PREFLIGHT.json/SUMMARY_KO.md/SHA256SUMS.txt,unchanged CORE21/23 artifacts; sorted2entry checksum,self excluded.
- Reuse unchanged CORE16 _output/_publish/error codes; exclusive0700/0600,exact bounded readback/root identity,no overwrite/automatic cleanup/retry.
- Path/time-independent CORE25 receipt,publication status separate from current preflight0/1; six authority flags false/GATES unchanged.
- CLI exactly one --archive/--sha256/--output-root,help/syntax before imports/access,no temp/cache,cold flag/path restoration,robust descriptor output/operational2.
- No existing computational edits/extraction/new model/ref/F61/actualr-dt/vehicle work; numeric and fixture work separately NONZERO.
- Actualr/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL/denial gates retained; no merge/push/PR/CI/HF writes,keep branch/worktree/evidence.

## Review Focus

- Publication success must not imply input compatibility; historical REJECTED/current-compatible and all/current rejection must retain exact original artifacts and correct exits.
- SHA/output/preflight/serialization ordering must prevent unsafe path access,extra capture,overwrite or mkdir before a complete valid result.
- Partial writes,exclusive-creation races,readback corruption/nonregular files/root replacement and post-publication stdout failure must never become false success or trigger destructive cleanup.
- Cold help/usage/import/failure paths must preserve caller flags without temp/cache work,while real failed stderr/help/stdout keep operational2.
- One preflight/report/renderer and bounded publisher readback must not add producer/reference/model/F61 execution or source/arithmetic/vehicle authority.

### Task1: Exclusive preflight package workflow and command

**Files:** Create `integration_tools/core_sequence_preflight_workflow.py`,`tools/core_sequence_preflight_workflow.py`,`project/test_core_sequence_preflight_workflow.py`,`project/test_core_sequence_preflight_workflow_cli.py`,`docs/CORE_SEQUENCE_PREFLIGHT_WORKFLOW_CORE25_KO.md`; link README/backlog/CORE23 report guide.

**Interfaces:** Consumes CORE13 `_expected(str)`,CORE23 `report_preflight_archive(Path,str)->(dict,bytes)`,CORE16 `_output(Path)->Path`/`_publish(Path,dict[str,bytes])->None`/ArchiveWorkflowError,canonical(dict)->bytes. Produces `publish_preflight_report(Path,str,Path)->dict` and CLI main(argv=None)->int with exact schema/files/errors as spec.

- [ ] Step1: Write API and CLI tests for all five Review Focus classes,real archive/output artifacts,literal status/exit/file sets/error controls and guarded side effects.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_preflight_workflow*.py' -v`; Expected all new methods FAIL because module/command absent.
- [ ] Step3: Implement small publisher composition and command,sharing existing filesystem/numeric behavior unchanged.
- [ ] Step4: New focused+old172 preflight/26 report/25 publication regressions and Ruff/Ty/Codespell; Expected PASS. Add guide/links.
- [ ] Step5: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected1560+actual new tests/300 own compiles/static PASS,frozen wheel.
- [ ] Step6: Preserved original CURRENT.zip API/direct/blocked/cold runs twice to new destinations; Expected receipts/files path-independent,JSON/MD exact prior evidence,two-entry manifest/full3-file receipt verified,permissions/readbacks/capture counts/source preservation,no new fixture/model/ref work. Include help/usage/bad-input/existing-output and stdout failure boundary proof.
- [ ] Step7: Source623/protected613/refs28,links/cloud consumer,local commit,one fresh final review/unsigned seal; Expected clean branch,no unresolved Critical/Important,no remote publication.
