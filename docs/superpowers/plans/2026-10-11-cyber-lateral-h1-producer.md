# Cyber lateral H1 producer implementation plan

> Use superpowers:executing-plans task by task, TDD, then a fresh independent reviewer.

Goal: generate deterministic offline lateral observations without changing the experiment.
Spec: the user's CYBER_LATERAL_H1_TRACE_V1 request and immutable simulator reuse contracts.
Architecture: new pure schema/producer, a detached baseline-only offline experiment wrapper,
immutable synthetic package writer and aggregate inspector/publication. No existing file changes.
Tech stack: existing Python/native test environment and SHA-256 canonical receipts.

## Global constraints
- Start from dd054f21443fbe02ee2fb585b76bec070bb56269 or a verified descendant; no reset.
- Preserve all historical receipts, contracts, production code, submodules and experiments.
- Existing driver_events scenario, unchanged baseline arm, disabled governor only.
- Experiment-relative 100 Hz integer clock; decision at capture+1 logical ns, never wall time.
- Pre-step consumed input and post-step plant output have distinct time/identity.
- No raw log reader, source copy, CAN/Params/device writes, opener, optimizer or composition.
- Unknown stage/sensor/service values are null with exact unavailable reasons.

## Review focus
- Input snapshot digest must exclude outputs and match the actual native input digest.
- Post-step curvature/application must not masquerade as current consumed feedback.
- Digest resealing must not bypass schema, provenance, source/config or timing checks.
- Missing first/interior/final rows and epoch/config sequence drift fail closed.
- Observer owns detached immutable copies; no callback receives a live core or plant.

## Task 1: Schema and producer
Files: cyber_lateral_h1_contract.py, cyber_lateral_h1_producer.py, test_cyber_lateral_h1.py.
Interfaces: policy(), schema(), Producer(policy, binding, configs), append(row), finish().
- [x] Write RED tests for exact schemas, digests, clocks, null/provenance and authority.
- [x] Implement pure checks, state ownership, sequence/config/epoch lifecycle and immutable finish.
- [x] GREEN on synthetic fixtures; persist policy before actual offline execution.

## Task 2: Detached offline experiment and inspector
Files: cyber_lateral_h1_experiment.py, cyber_lateral_h1_inspector.py.
Interfaces: execute(observer=True), persist(store, package), inspect(store); explicit local CLI.
- [x] Use baseline Arm.advance unmodified; copy returned rows into H1 records.
- [x] Compare two observed runs and observer-disabled run canonical experiment bytes.
- [x] Atomic no-overwrite package outside repository; reject symlink/path/identity drift.
- [x] Aggregate inspector only, no raw/private reader, UI/server or holdout opener.

## Task 3: Evidence, publication and review
Files: cyber_lateral_h1_publication.py, five requested JSON artifacts and feature record.
- [x] Pin policy/schema/source and synthetic trace/repeatability receipts.
- [x] Independent review, regression tests for defects, full required checks.
- [x] Report visual conversion PARTIAL if unavailable stages/sensors remain.

## Task 4: Delivery
Delivery evidence (commit/push, exact HEAD CI completed/success, fresh fetch,
local/origin equality and clean tree) is recorded in the final handoff after push.
Historical tracked files and submodule pins remain unchanged.
