# CORE26 Saved Preflight Report Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read-only cross-check a saved CORE25 report against its explicitly supplied original ZIP/full SHA.

**Architecture:** Reuse unchanged CORE23 Path report and CORE18 directory/bounded capture,then exact artifact/manifest/root identity comparison. Thin CORE25-style no-cache CLI; inspection0 independent from current preflight0/1.

**Tech Stack:** Configured Linux CPython3.12.13,stdlib/unittest/Ruff/Ty/Codespell,frozen wheel.

**Spec:** [design](../specs/2026-11-06-core26-preflight-package-inspect-design.md)

## Global Constraints

- SHA before caller path work;root/layout before archive capture;one report/capture/verifier/renderer;three regular saved members once each with expected-size caps.
- Exact original JSON/MD/sorted2-entry manifest,selfexcluded;final rootfd/path identity;no arbitrary JSON input reader.
- Inspection success0,currentpreflight0/1 separate;errors2/no successprefix/rawpath. Receipt/diagnostics exactly per spec.
- Exactlyone --input-root/--archive/--sha256,help/syntaxbeforeproject/pathwork,coldbytecode suppression,globalrestoration,no temp/cache/probe/writes/extraction/cleanup.
- No old computational/API/CLI/helper edits,producer/publisher/model/ref/F61/actualr-dt/vehicle work;numeric/unitfixture NONZERO separately.
- Actualr/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL,denialgatesretained;keep localbranch/worktree/evidence,no remote/integrationwrites.

## Review Focus

- A consistent saved rejection must inspect successfully without becoming current-compatible or inheriting historical labels as authority.
- Coherently rechecksummed edits,wrong original ZIP,missing/extra/nonregular files and short/growing reads must not become false consistency.
- SHA/root/archive/report ordering,single captures and final root/layout checks must avoid unsafe reads or partial success under supported changes.
- Cold syntax/import/error/help/stdout/stderr paths must preserve caller globals and operational2 without filesystem writes or cache/temp probing.
- Owned result regeneration and receipt authority flags must not introduce producer/publisher/model/reference/F61 work or claim source/arithmetic/vehicle proof.

### Task 1: Read-only saved preflight inspection API and command

**Files:** Create integration_tools/core_sequence_preflight_inspect.py,tools/core_sequence_preflight_inspect.py,project/test_core_sequence_preflight_inspect.py,project/test_core_sequence_preflight_inspect_cli.py,docs/CORE_SEQUENCE_PREFLIGHT_INSPECT_CORE26_KO.md;modify README/backlog/CORE25guide links.

**Interfaces:** Consumes CORE13 _expected(str),CORE23 report_preflight_archive(Path,str)->(dict,bytes),CORE18 _directory(Path,dict[str,bool])/_read_file(int,str,int)->bytes,CORE12 _path(Path,str)->Path,canonical(dict)->bytes. Produces inspect_preflight_report(Path,Path,str)->dict,PreflightInspectError(code),CLI main(argv=None)->int as spec.

- [ ] Step1: Write API/CLI tests pinning all five Review Focus classes,real published fixtures,literal verdict/counts/error/file semantics;guards verify no new execution/writes and boundedreads.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_preflight_inspect*.py' -v`;Expected FAIL absentmodule/command.
- [ ] Step3: Implement minimal composition/API and local thin no-cache CLI;Expected new tests PASS.
- [ ] Step4: Run new+old228 preflight,26 report,25publication and35 CORE18tests (read actual count),Ruff/Ty/Codespell;Expected PASS. Add guide/links.
- [ ] Step5: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`;Expected1616+actualnew tests/304own compiles/staticPASS,frozenwheelunchanged.
- [ ] Step6: Preserved original CORE25 doc-output+CORE17 CURRENT.zip API/direct/blocked/cold twice,help/usage/missing/mismatch;Expected inspection0/currentpreflight1,receiptbytesidentical,pathindependent,archivecapture1/reportfiles3,oneverifier/renderer/cases3/quantizer8,no commandwrites/newfixtures/model/ref;sourcebytesmodeslayoutunchanged.
- [ ] Step7: Source630/protected620/refs29,cloudconsumer/Manifest/links,localcommit,freshwholebranchreview,unsignedZIPseal;Expected cleanbranch,noCritical/Important,no remote/integrationwrites.
