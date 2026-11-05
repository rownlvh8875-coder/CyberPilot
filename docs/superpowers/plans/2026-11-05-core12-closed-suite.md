# CORE12 Closed Three-Case Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline work/no repeated approval questions.

**Goal:** Fixed three-case suite summary with explicit newwork,history,comparison.
**Architecture:** Root preflight/capture,CORE11 owned-record report/run helper reuse,
bounded3case aggregation andJSONstdoutCLI;no new calculator or externalmanifest.
**Tech Stack:** Existing CPython3.12.13/Linux/stdlib/unittest/Ruff/Ty/Codespell.
**Spec:** docs/superpowers/specs/2026-11-05-core12-closed-suite-design.md

## Global Constraints

- Base5c464c56e45e80dc67eee7031723423cc0c237b7,existinghostlinkedworktree/localbranch.
- ExactlyCASE_IDS in fixedorder,rootexact3dirs/eachchildexact3files/no subset/fallback.
- check no producer/modelimports;run ALLbaselinevalidatedbefore ANYoutput/newwork.
- Ownedcaptures once/no casefile reopening;privateCORE11body extraction unchanged.
- Explicit counts/newsteps/history/savedstatuses/compare separated;null withoutbaseline.
- Postwork failures conservativeMAYBENONZERO,partialrootpreserved,no laterwork/retry.
- Cacheteardown/exitmappingbeforestdout/insidehandler;errors2/no successreceipt.
- No newdependencies/network/F61/Controller/runtime/CAN/vehicle/r/push/merge/PR/CI/HF/deletion.
- Frozenwheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.

## Review Focus

- A bad last baseline must prevent all new steps/output,not merely its owncase.
- Saved REJECTED,zero finalcase,newprefixwork,and no-baseline null must never hide work or imply regressionPASS.
- Extra/missing/linked/wrongcase roots and output-baseline nesting must not mutate inputs or admit mislabeled cases.
- Captured baseline/current records must not be reopened or replaced with later filesystem contents.
- Partialcase/root/cache/stdout failures must return2,retain outputs,and publish no premature success receipt.

### Task 1: Bounded suite coordinator and CLI

**Files:** new integration_tools/core_sequence_suite.py,tools/core_sequence_suite.py,
project/test_core_sequence_suite.py,docs/CORE_SEQUENCE_SUITE_CORE12_KO.md;
modifycore_sequence_workflow.py/README/backlog;spec/plan committedfirst.
**Interfaces:** SuiteError.code,check_closed_suite(Path,Path|None=None)->dict,
run_closed_suite(Path,Path|None=None)->dict,exit_code(dict)->int;
CORE11private_run_captured(case,output,ownedbaseline)->dict andexisting_report helper.

- [ ] Immutable baseline `dev.py verify --output <newdir>` expected1180/262/static/wheelPASS.
- [ ] Testsfirst:literal3caseorder/counts/check0/run6;no-baseline null/diffs18baseline;
  exactlayout/caseidentity/corruption/links/FIFO/26opens;baselineallpreflight0work;
  snapshotreuse/inputpreservation;rootguards/overlap0;partial2nd/lastR failurehonesty;
  postlayout/CLI0/1/2/options/stdout/cachecleanup/freshblockedcheck/canonical/compat.
  Run `.venv/bin/python -I -B -m unittest discover -s project -p test_core_sequence_suite.py -v`.
  Expected:missingfeatureRED,not fixture/importerrors.
- [ ] Extract unchangedCORE11runbody;implementrootcapture/suiteaggregate/CLI per spec.
  Samecommand expectedallPASS;Ruff/Ty/Codespell/diffcheckPASS.
- [ ] Guide/README/backlog showrootlayout,explicitall3/newsteps/nostatuspromotion,
  nullbaseline,preflight/failurepreservation;commitstableimplementation.
- [ ] Fullgate expected1180+new/265/static/wheelPASS;onefreshwholebranchreview;
  one TDDfixpass ifCritical/Important,no rereview.
- [ ] Independent realAPI/directCLI/profiledCLI suites twice,allpacketmanifests,
  actual6steps/runset/check0,baselinepreserved,CORE11oldCLIcompatibility.
- [ ] Source545/prior536preserved,Manifest/cloudconsumer/refs/links,reproducible
  externalreport/result/ledger;keepbranch/evidence,no remote publication.

Self-review:onecohesivecoordinator task;owned-capture andprivate-run interfaces match.
Every ReviewFocus mappedto realtest above;no unrelated arithmetic/refactoring work.
