# CORE1 F61 Signal Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans;
> the owner delegated inline execution and waived repeated approval questions.

**Goal:** Integrate the already approved synthetic request-pair projection into DEV.
**Architecture:** Frozen data constants, pure adapter, test-only independent IEEE
oracle; no public model, production reader or calculator changes.
**Tech Stack:** Existing CPython3.12.13, stdlib unittest, pinned Ruff/Ty/Codespell.
**Spec:** docs/superpowers/specs/2026-11-05-core1-f61-signal-binding-design.md

## Global Constraints

- Base eed06ee21765d9f61d0691824146725c1767e18d; existing isolated worktree, feature branch.
- Preserve original V4 API/return keys/codes/order/domain; relative imports and formatting only.
- F70UGHR ZIP a2686fe18fe094ef3a9a5b452c71fd36b19f5d340e4aa90d3e95e4abfa879192.
- F61 original SHA f343b0edd5578348c570692f05d655dee8e2b1555492a1d99b218d3f81fab035; 6735 bytes; AST only.
- No new dependencies/CLI; public0.3.0/imported77/old readers/locks/workflows/profiles unchanged.
- Frozen wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- In-memory synthetic-only partial projection, never actual data or 18-field calculator args.
- Exact binary32 embedding/native signed-zero preservation; exact positive second delta only.
- No r/nominal-dt/scale fallback, actual gate bypass or production capture/activation.
- No push/PR/merge/HF/CI dispatch; local commits and retained external evidence only.

## Review Focus

- Synthetic labels and caller-asserted PASS must never become actual-production authorization.
- Previous request must not be replaced with limited/applied state or inferred prehistory.
- 10ms, near-binary32 values and huge epochs must not be rounded to a convenient accepted value.
- Domain/source/epoch mismatches and malformed built-in types must reject with no partial projection.
- Partial fields and preserved flags must not be mistaken for F61 constructor arguments or feasibility results.

### Task 1: Integrate the existing pure boundary and document the core backlog

**Files:**
- Create: tools/cyberlateral_dev/integration_tools/f61_signal_contract_v4.py
- Create: tools/cyberlateral_dev/integration_tools/f61_signal_adapter_v4.py
- Test: tools/cyberlateral_dev/project/test_f61_signal_adapter.py
- Test utility: tools/cyberlateral_dev/project/f61_signal_oracle.py
- Create: tools/cyberlateral_dev/docs/F61_SIGNAL_ADAPTER_V4_KO.md
- Create: tools/cyberlateral_dev/docs/CORE_DEVELOPMENT_BACKLOG_KO.md
- Modify: tools/cyberlateral_dev/README.md
- Modify: tools/cyberlateral_dev/integration_tools/verify.py (additive count-scope labels only)

**Interfaces:** Consumes original frozen V4 constants/`adapt(object)->dict` and
independent `oracle(object)->dict`; produces the same adapt API at the DEV relative
import path. No downstream task or public runtime interface change.

- [ ] Verify linked worktree and clean source base; create feature branch/external ledger.
  Run `python -B dev.py verify --output NEW_BASELINE` with existing .venv.
  Expected:904 tests,234 own compiles,Ruff/Ty/Codespell/frozen wheel PASS.
- [ ] Verify canonical archive CRC/Manifest/seal, F61 SHA/6735bytes/18 AST fields,
  and original adapter/contract/oracle bytes. Expected: complete exact custody, no F61 execution.
- [ ] Write unittest cases before new runtime files. Expected literal projection:
  current0.5,previous-0.25,previous_time0,current_time=dt=1/512,
  scale1/offset0/no rounding/no clipping; always calculator_invocation_allowed=false.
  Add previous-request stage rejection, actual/forged-gate rejection, source/domain/
  sequence mismatch, signed zero, finite/built-in/binary32 boundaries, flags-only
  preservation, invalid rate input, exact10ms/1ns rejection and huge integer epochs.
  Run `.venv/bin/python -B -m unittest discover -s project -p test_f61_signal_adapter.py -v`.
  Expected: missing-adapter assertion RED, not unrelated import/setup errors.
- [ ] Migrate frozen data subset, adapter and independent oracle with relocated imports.
  Add literal fixture helper only in tests, not runtime. Expected: focused tests GREEN;
  independent oracle does not import adapter or share validation/numeric helpers.
- [ ] Compare original and migrated AST after import-only normalization; data assignments
  identical and adapter/oracle algorithms identical. Exercise original sealed fixture
  corpus plus extra input variants on migrated adapter/oracle; exact bits/hex/fields/codes
  agree, inputs unchanged. Expected: exact repeatable parity, no model/F61 work.
- [ ] Add guides/code mapping/backlog with confirmed-vs-proposed scope and explicit
  completion criteria; document current absence of actual binding and no duplicate validator.
- [ ] Full `dev.py verify` from existing locked venv to NEW_FINAL output.
  Expected:904+actual new test methods PASS,238 own compiles,static/wheel PASS.
  Existing registered source bytes/modes unchanged except component README and
  the additive verifier count-scope clarification below.
  Integration clarification: a real emitted-summary test must first fail for an
  unscoped dt=0, then pass for explicit F61/actual-only scope and synthetic pair-time
  work NONZERO_NOT_AGGREGATED. Rerun full gate after the additive verifier edit;
  preserve all other old registered source except README and this verifier.
- [ ] Commit spec/plan and then completed implementation/tests/docs on the local feature branch.
  Run one fresh whole-branch reviewer with Review Focus verbatim and ledger; re-grade
  findings, one Critical/Important TDD fix pass if needed; no repeat review.
- [ ] Record final Git preservation, fresh verification evidence and scoped result outside
  repo. Keep feature branch/worktree/evidence; report next concrete core task, not publication.

Self-review: one task owns adapter plus its oracle/tests/docs, so no shared task
interfaces. All five Review Focus classes have named observable tests. The scope
is migration of an approved reference, not creation of a production policy/parser.
