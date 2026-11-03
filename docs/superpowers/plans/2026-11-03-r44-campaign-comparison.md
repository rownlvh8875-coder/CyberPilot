# R44 Saved Campaign Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Compare complete R43 campaigns without rerunning model/reference work or hiding source errors.

**Architecture:** A bounded R43 reader reuses child validation and R34 saved batches;
pure aggregation reuses R34 differences; thin exclusive-publication CLI. No old
producer, public package, oracle, generator, dependencies or CI configuration edits.

**Tech Stack:** Existing CPython3.12.13/Linux/stdlib and pinned DEV tools.

**Spec:** docs/superpowers/specs/2026-11-03-r44-campaign-comparison-design.md

## Global Constraints

- Complete canonical R43 V1,1..4 unique uint32 seeds/cases1..16/steps16..256.
- 8192files/512MiB per input,16MiB/file/depth16; child2048files/128MiB.
- Positional alignment, typed exact differences, top256 details, no tolerance.
- Overall ERROR > DIFFERENT > MATCH preserves source verdicts; regression separate.
- New output only, no final marker on invalid/late-mutated/failed publication.
- Zero model/reference-worker/F61/actualr/dt/native/vehicle work in comparison.
- Full0.3.0 API/wheel/math/oracle/generator/locks/dependencies/CI unchanged.
- Reviewed feature PR only; no main merge/HF writes or workspace/evidence deletion.

## Review Focus

- Identical source ERROR/DIFFERENT records must not become overall numerical MATCH.
- Reordered seeds/added runs/changed cases cannot disappear through zip truncation or sorting.
- Rehashed root/child/source/reference contradictions cannot masquerade as valid snapshots.
- Changed or missing producer identities are distinct from unchanged values, never current-source authentication.
- Late changes/publication failures cannot leave a valid-looking completion marker or modify inputs.

## Task 1: Complete read-only campaign comparator

Create under tools/cyberlateral_dev:
integration_tools/scenario_campaign_compare_input.py (typed campaign reader),
integration_tools/scenario_campaign_compare_run.py (comparison and publication),
tools/scenario_campaign_compare.py (isolated CLI),
project/scenario_campaign_compare_fixture.py (test-only complete fixtures),
project/test_scenario_campaign_compare_input.py,
project/test_scenario_campaign_compare_run.py,
project/test_scenario_campaign_compare_cli.py,
docs/SCENARIO_CAMPAIGN_COMPARISON_R44_KO.md. Add one README feature section.

Interfaces: reader defines CampaignCompareError(code) and read_campaign(path:Path)->dict
with validated record/runs/batch snapshots/hash map. Runner defines
run_campaign_comparison(baseline:Path,candidate:Path,output:Path)->dict and exit_code(record)->int.
CLI consumes those interfaces, no alternative schema.

- [x] Baseline: `.venv/bin/python -B -m unittest discover -s project -p 'test_scenario_c*.py' -v`.
  Expected: existing R34/R43/CLI tests PASS before new product code.
- [ ] Reader tests first: real2seed32sample complete snapshot accepted with unchanged
  bytes; exact root/child totals/canonical shape, fully rehashed false counts/gates/
  findings/reference/hash/paths rejected; symlinks/FIFO/caps/portable-only rejected.
  Run input module: Expected RED missing reader assertion. Implement smallest bounded
  reader using existing R43/R34 checks; Expected GREEN.
- [ ] Runner/CLI tests first: real same pair MATCH/32samples/diff0/new model/ref0;
  coherent saved trace mutation DIFFERENT/one exact field; positional seed reorder,
  run add/remove and changed config visible; identical ERROR->overallERROR/regressionMATCH,
  identical DIFFERENT->overallDIFFERENT; identity-only change remains separate.
  Include detail truncation, output guards, source/input changes, publication failure,
  independent repeat/canonical manifests and isolated forbidden-module observation.
  Expected RED missing runner/CLI. Implement aggregation/CLI; Expected all focused GREEN.
- [ ] Korean docs/README match actual command and limits. Run focused suite + Ruff/Ty/
  Codespell; Expected PASS. Do not alter old source/fixture expectations to obtain PASS.
- [ ] Explicit read-only comparisons2 against preserved main R43 campaigns:
  each128samples/MATCH/diff0/model0/ref0, input hash maps unchanged, portable parent
  comparison/summary equal. Repaired trace control DIFFERENT/one exact field/exit1;
  corrupted input exit2/no output. Expected independent saved Manifest checks PASS.
- [ ] Full `dev.py verify --output NEW_EXTERNAL`, cloud ci_verify; Expected actual
  complete test ledger/static/own compiles PASS, original wheel3f3db...7c4d73c unchanged.
- [ ] Commit; one fresh whole-branch reviewer from e2cf1ea9 on most-capable allowed
  model. Re-grade findings, Important ONE RED→GREEN fix pass/full suite, defer Minors
  and ledger all rulings. No second reviewer.
- [ ] Normal push/new PR/attach; actual exact-head app/cloud/root enabled CI and
  artifact checks PASS (existing simulator skip not PASS). No merge/HF refresh.

## Execution bookkeeping

Reuse existing named linked worktree; preserve old R43 branch and its environments.
User opted out of repeated choices; author chooses native inline execution with one
final fresh reviewer. All evidence is external and preserved; cloud-only skill
helper scripts have no local executable path, so record equivalent briefs/BASE/
test commands/outcomes directly in the ledger. One task, no cross-task interfaces.
