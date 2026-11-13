# Product live monitoring implementation plan

Spec: `docs/superpowers/specs/2026-11-13-product-web-integration-design.md`
Baseline: 03636da474c4126010acffd610744fcd011633c8.
Execute inline without routine approval pauses; user explicitly authorizes
sequential completion and normal publication. Preserve prior evidence and all
existing lateral dev/cloud bytes. Do not execute vehicle launch/manager/F61.

## Task 1 — State and read-only collectors

Interface: Store.update(topic,data,event_ns,valid), Store.snapshot(); independent
monotonic freshness and schema v1. Collectors poll host or injected SubMaster.
Write failing unittest cases for null/invalid/stale/out-of-order, int64 strings,
finite metrics, real host source, source mapping and failed Cereal initialization.
Run unittest discovery (Expected: RED missing module), implement, run full new
suite (Expected: all PASS). Commit telemetry state/collectors and tests.

## Task 2 — HTTP and mobile web

Consumes Task 1 snapshots. Private token initialization/load, read-only HTTP,
auth, fixed routes, thread limits, TLS, CLI and responsive assets. Write tests
first for unsafe credentials, authentication, rejected methods/routes/query,
security headers, real host status and no secret logging. Expected RED, then
GREEN. Real browser tests: login, actual host values, mobile/desktop readability,
per-topic stale, connection loss and logout. Inspect screenshots. Commit.

## Task 3 — Product integration and distribution

Consumes Task 2 serve config; daemon reads explicit env, no manager argv.
Write RED tests for default-off process registration, safe daemon configuration,
missing launch resource, deterministic bundle/extracted smoke and not-qualified
readiness. Resolve/test AGNOS compatibility symlinks; fix only a demonstrated defect; implement opt-in manager entry, readiness,
bundle tools, locked dev environment, CI and Korean usage/remaining-work docs.
Run all new tests/static/compile/browser/bundle checks (Expected PASS). Commit.

## Final review and publication

One fresh whole-branch reviewer, explicit strongest available model. Review
focus: token/path/HTTP exposure, slow/stale/invalid topics, clock precision,
misleading actual-device claims, manager failure modes, installer side effects,
portable bundle and CI completeness. Record rulings and fix Important findings
with observed RED/GREEN plus whole suite. No repeat review. Preserve workspace
as user-reviewable evidence under existing custody preference.
Normal feature backup and main fast-forward/push; inspect exact workflow result
and artifact. Finish with implemented scope, verification, physical blockers and
links. Do not claim full openpilot native build or vehicle readiness.
