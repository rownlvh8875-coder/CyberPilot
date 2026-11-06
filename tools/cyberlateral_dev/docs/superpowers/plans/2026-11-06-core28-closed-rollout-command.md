# CORE28 Closed Rollout Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly run a closed CORE27 synthetic example and preserve canonical input/results/checksum in a new checked folder.

**Architecture:** Closed catalog + unchanged CORE27;new owned-result projections + unchanged CORE16 exclusive/readback publisher. Thin proven no-cache CLI requiring --run;publication success separate from result0/1/2.

**Tech Stack:** ConfiguredLinuxCPython3.12.13,stdlib/dataclasses/unittest/Ruff/Ty/Codespell,frozenwheel.

**Spec:** [design](../specs/2026-11-06-core28-closed-rollout-command-design.md)

## Global Constraints

- Exactclosedcase before outputpath;NEWexternaloutput validation before factory/model;INPUTencoding before rollout;allartifactserialization/status beforemkdir.
- ExactlyINPUT.json/RESULTS.json/SHA256SUMS.txt,newCORE28tags/losslesshex,allrecord/receiptfields as spec;no genericreader/actualdata/sourceidentity claim.
- Onecatalog/CORE27call,completed3steps,rejectedpreflight0steps;never classifyexecution failure as preflight rejection;otherworkmaybenonzero.
- ReuseCORE16_output/_publish,exclusive0700/0600/readback3/rootidentity,nooverwrite/cleanup/retry;failedpublication/stdoutcanleavepartial/completeoutputandnonzero work.
- CLIexactone --case/--output-root/--run,help/syntaxbeforeproject/path/model,coldbytecode/globalrestore/no tempcacheprobe,failedstreamsoperational2.
- No existing model/helper/CORE27/CLI/wheel edits,F61/actualr-dt/vehicle0,gatesunchanged;retainbranch/worktree/evidence,nointegration/remotewrites.

## Review Focus

- Missing/duplicated run intent or malformed case/output options must not execute a model or access caller output paths.
- Intentional preflight rejection must publish a truthful zero-model record,while model/serialization/publication failures must never become false saved rejection or zero-work success.
- Serialized entry/computed/saved roles and binary32/binary64 precision must retain CORE27 literal state-feed semantics without reusing CORE8 schemas or granting source/vehicle authority.
- Existing-output rejection,exclusive races,short/partial writes,readback/root replacement and post-publication stdout failure must preserve files and truthful work/exit uncertainty.
- Cold help/import/error/failed-stream paths and repeated runs must restore caller settings,avoid cache/temp probes,and keep model execution and writes scoped to the explicit requested run.

### Task 1: Closed execution/export API and explicit-run CLI

**Files:** Create integration_tools/core_rollout_run.py,tools/core_rollout_run.py,project/test_core_rollout_run.py,project/test_core_rollout_run_cli.py,docs/CORE_ROLLOUT_RUN_CORE28_KO.md;modify README/backlog/CORE27guide links.

**Interfaces:** Consumes CASE_IDS/build_case(str)->(frames,contexts),CORE27rollout_synthetic_sequence(object,object)->result/SequenceRolloutError,CORE16_output(Path)/_publish(Path,dict[str,bytes])/ArchiveWorkflowError,canonical(dict)->bytes. Produces run_rollout_case(object,Path)->publicationreceipt/RolloutRunError andCLI main(argv=None)->int as spec.

- [ ] Step1: Write API/CLI tests exercisingall5ReviewFocusclasses,real3cases/files and literalstates/counts/precision/errors/sideeffects.
- [ ] Step2: `.venv/bin/python -B -m unittest discover -s project -p 'test_core_rollout_run*.py' -v`;Expectedabsentmodule/commandFAIL.
- [ ] Step3: Implement minimalserializer/runner and explicit no-cacheCLI;ExpectednewtestsPASS.
- [ ] Step4: CORE27/CORE16+newregression/Ruff/Ty/Codespell,guide/links;ExpectedPASS.
- [ ] Step5: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`;Expected1697+actualnewtests/310owncompiles/staticPASS,frozenwheelunchanged.
- [ ] Step6: IndependentpriorsealedCORE27artifactassembly,API/direct/blocked-cold3casesx2 NEWfolders;Expected exactfiles/receipts/pathindependence,models3/3/0pervariant,readback3/mkdir1,sourceunchanged;help/usage/existing0model,failedstdoutcompletefiles,actualdoccommand.
- [ ] Step7: Source642/protected632/refs31/cloudconsumer/Manifest/links,localcommit,onefreshreview,unsignedseal;Expectedcleanbranch/noCriticalImportant/no remote writes.
