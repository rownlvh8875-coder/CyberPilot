# CORE10 Saved Sequence Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner selected delegated native offline work without repeated routine approval.

**Goal:** Locate every kind of stored-record difference without new computation.
**Architecture:** CORE9 single-capture loader extraction; recursive exact-type
comparison, deterministic bounded details, safe text formatter and thin stdout CLI.
**Tech Stack:** Existing Linux/CPython3.12.13/stdlib/unittest/Ruff/Ty/Codespell.
**Spec:** docs/superpowers/specs/2026-11-05-core10-saved-comparison-design.md

## Global Constraints

- Base7ad20857f4c07fbe79d4e82e3a93833b8d0f7133,existinglinkedworktree/localbranch.
- CORE9 capture/parser/validator/errors/output preserved; no reread after validation.
- Full INPUT/RESULTS including identity, exacttypes/presence,RFC6901/positional order.
- First256details plus fullcount/explicittruncation,never silent equality.
- Stdout JSON/Markdown,exit0identical/1different/2error;typed escaped Markdown cells.
- No model/native/checker/quantization/dt/r/actualsource/vehicle invocation or writes.
- Readernewwork0 versus fixture/unit/gate NONZERO_NOT_AGGREGATED.
- No new dependencies/network/push/merge/PR/CI/HF/cleanup; preserve old refs/evidence.
- Frozenwheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.

## Review Focus

- Changes invisible to CORE9 summary (input,opaqueidentity,bool-vs-int,missing/null) must never yield identical.
- Truncation above256 must retain exact total/section counts and difference exit1.
- Malformed side must fail before any success stdout, without executing/reopening records.
- Untrusted identity path/value Markdown,controls and pointer escaping must be safe and unambiguous.
- Saved REJECTED/DIFFERENT and operational stdout failure must not conflate saved outcome with comparison exit.

### Task 1: Single-capture saved record comparison

**Files:** modify integration_tools/core_sequence_saved.py and componentREADME/backlog;
create integration_tools/core_sequence_compare.py,tools/core_sequence_compare.py,
project/test_core_sequence_compare.py,docs/CORE_SEQUENCE_COMPARE_CORE10_KO.md.
**Interfaces:** read_saved_sequence_records(Path)->dict(input_record/result_record/summary);
compare_saved_sequences(Path,Path)->dict;CompareError.code;
render_comparison(dict,str='json')->bytes;CLI--left/--right/--format only.

- [ ] Immutable baseline fullgate1116/256/static/wheel PASS; commit spec/plan.
- [ ] Tests first with literal expectations:loader unchangedhashes,allstatuses/cases,
  input-only+identity-only,booltype,missingnull,pointerescape,positional/order,257details,
  both-sidechecksum/gate/row/IO corruptions,formatbeforeaccess,canonical/Markdown safety,
  CLI0/1/2/options/devfull,read-only8opens/freshforbiddenimports/inputunchanged.
  Run `.venv/bin/python -I -B -m unittest discover -s project -p test_core_sequence_compare.py -v`.
  Expected:missingfeature assertion RED,not fixture/import errors.
- [ ] Extract existing loader then implement comparator/renderer/CLI per spec.
  Same unittest command expected allPASS; scoped Ruff/Ty/Codespell and diffcheckPASS.
- [ ] Guide/README/backlog cover full versus truncated details,saved versus comparison,
  no arithmetic/authentication,nonzero setup versus0reader; commit stable source.
- [ ] Full `dev.py verify --output <newexternaldir>` expected1116+newtests/259/static/wheelPASS;
  one fresh whole-branch review may overlap;one TDD fix pass if needed/no rereview.
- [ ] Independently inspect historical3x3pairs API/realCLI/profiledblockedCLI twice,
  literal equality/difference checks,allcapturedinputfilespreserved,no newmodel/fixtures.
- [ ] Source533files/prior524preserved,Manifest/cloudconsumer/localrefs/links/result
  repeatcheck; external Koreanreport/ledger; clean local branch retained unpushed.

Self-review: singleworkflow/no sharedtaskinterfaces. Loader and comparator boundary
explicit, each ReviewFocus pinned by a test. No implicit case/outcome arithmetic.
