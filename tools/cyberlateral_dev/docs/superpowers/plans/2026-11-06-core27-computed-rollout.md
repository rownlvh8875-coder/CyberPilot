# CORE27 Computed-State Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate pure synthetic computed-state chain that preserves declarations and records entry/output differences.

**Architecture:** Whole-input CORE5 preflight before any model.step,seed from first declared entry,then identical computed next-state objects only. Existing model/CORE6 result validation reused;CORE7 unchanged.

**Tech Stack:** Configured Linux CPython3.12.13,stdlib/dataclasses/unittest/Ruff/Ty/Codespell,frozen wheel.

**Spec:** [design](../specs/2026-11-06-core27-computed-rollout-design.md)

## Global Constraints

- Exact tuples2..4096frames,contextsframes-1,exact carriers,full CORE5 preflight thenmodelorder beforesteps.
- First supplied declared state only;subsequent entry IS previous output.next_state,no reseed/repair/retry/fallback.
- Rowentry3/output2fieldcomparisons and all derived fields/errorcodes exactly as spec;MATCH is not fulltrace/source/history/vehicle proof.
- Every completed transition executes one public model.step;successsteps=frames-1,failurework may be nonzero;no partialresult.
- Existing model/CORE3~26/API/helper/CLI/wheel unchanged,no new CLI/file/stream/checkpoint/production reader.
- F61/actualr-dt/Controller/Runtime/CAN/vehicle0,actualr/T2/scale=null,R_BUDGETUNRESOLVED/StaticGateFAIL/denialgatesunchanged.
- Keep branch/worktree/evidence,no integration/remote writes. Source635/protected627/refs30,306owncompiles.

## Review Focus

- An early saved-state difference must propagate computed state,never silently reseed from later declared entries or repair the original snapshots.
- Later invalid inputs/order/reset/settings must reject before all model calls,while execution failures must not return partial success or claim zero prefix work.
- Entry divergence and current saved-output divergence must be reported separately and completely,including inactive and faultcounter boundaries.
- First declared seed and successful synthetic chain must never imply anchor/prehistory/full-output/source/native-replay/vehicle authority.
- Direct construction,foreign/subclass inputs,maximum index/count and malformed model outputs must retain the explicit cooperative API/error/work contract.

### Task 1: Pure computed-state rollout and literal regression proof

**Files:** Create integration_tools/synthetic_sequence_rollout.py,project/test_synthetic_sequence_rollout.py,docs/SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md;modify README/backlog/CORE7guide links.

**Interfaces:** Consumes CORE5 prepare_model_input(object,object,object)->PreparedSyntheticModelInputV1,publicmodel.step(LateralInput,LateralState)->LateralOutput,CORE6 _next_state(output,index)->LateralState. Produces rollout_synthetic_sequence(object,object)->SyntheticSequenceRolloutV1 and immutable result/step/difference records as spec.

- [ ] Step1: Write tests for all five Review Focus classes,literal3stepstates,divergentdeclaredcase,edgecounter/gating,inputdomain/fullpreflight,model failures,immutability/work/flags/no IO.
- [ ] Step2: `.venv/bin/python -B -m unittest discover -s project -p 'test_synthetic_sequence_rollout.py' -v`;Expected absentmodule failures.
- [ ] Step3: Implement minimal coordination/derived records;Expected newtestsPASS,no existing arithmetic edits.
- [ ] Step4: Run CORE5/6/7+new and saved/preflight regression,Ruff/Ty/Codespell;ExpectedPASS. Add guide/links.
- [ ] Step5: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`;Expected1665+actualnewtests/306owncompiles/staticPASS,wheelunchanged.
- [ ] Step6: Independent literal oracle existing3cases API/constructor/blocked twice;Expectedsame receiptbytes/sourceunchanged,modelsteps3/3/0pervariant,validationNONZERO,no actualwork/IO;documentedexample actual3steps.
- [ ] Step7: Source635/protected627/refs30,cloudconsumer/Manifest/links,localcommit,onefreshwholebranchreview,unsignedseal;Expectedcleanbranch/noCriticalImportant/no remote writes.
