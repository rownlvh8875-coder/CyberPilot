# R35 — fixed synthetic regression pack

## Intent and approach

Extend useful numerical/state coverage through the existing R31 → R33 → R34
workflow, without another frontend or a change to the public0.3.0 model. The
owner approved this direction and previously delegated implementation choices
without repeated approval questions. This is a small fixture/test addition.

Alternatives considered: another scenario tool duplicates existing capability;
rerunning the two old examples adds no new coverage; a fixed pack with separately
hand-derived expectations provides reviewable additional cases. Use the last.

## Deliverables

Nine explicit JSON files in examples/r35: six valid scenarios (38 total samples)
and three intentionally rejected scenarios. reference/r35_regression_expected_v1.json
contains literal row/state/selected trace expectations, not values exported by
the model. Document the derivation and explicit CLI order. Never auto-update it.

Valid cases: positive and negative asymmetric sign-crossing cycles (8 each);
inactive/reactivation with resumed history (5); angle-counter89/90/91, negative85
and below85 reset (5); fractional driver bounds/nearest-even (6); quantization
ties, binary64 decimal0.3 and signed zero (6). Rejected cases: a late integer
request token, non-adjacent index, and an extra rate-budget policy field.

Tests exercise actual parsing/model execution and fresh CLI batch/comparison.
Check distinct requested/applied history, rate bounds, driver scalar kinds,
counter/steer-request, final state, JSON/CSV/view agreement, explicit rejection
codes with zero prefix work, all output manifests, and repeat portable bytes.
The mixed batch must exit1 (six complete, three rejected), then its saved repeat
comparison must exit0/MATCH with38 samples and no new model execution.

## Constraints and acceptance

- Baseline b6731908be519a051c6ffcf9a18845284a102c20; use the existing isolated
  checkout on a new feature branch. Original checkout and laptop untouched.
- CPython3.12.13/Linux/binary64; existing pinned DEV dependencies only.
- No changes to src/, integration_tools/, tools/, public API/wheel/lock,
  existing examples, or the original F61 source. New tests are auto-discovered.
- No Controller/native qualification/vehicle Runtime/CAN/F61/r/dt work or real
  vehicle inputs. All new scenarios are manually authored synthetic data.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
  SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
- Fresh full component gate, static checks, memory compile and sealed wheel
  preservation; two complete explicit pack runs and exact R34 comparison.
- No generic independent oracle, production timing/scale, safety/performance or
  deployment claim. Narrow literal checks do not prove every output field.
- Local feature commits are allowed; no push, PR, main merge, or CI dispatch in
  this task. Keep completed outputs outside the repository.

## Builder decisions

Use the existing unittest style. Keep literal numeric expectations in one JSON
reference and projection/assertion helpers in test-only code. Do not add a new
production oracle, command, dependency or baseline-updater. Preserve test logs
and a progress ledger in the task's external evidence directory.
