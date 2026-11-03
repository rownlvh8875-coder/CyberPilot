# R48 — Preserve R44 results after diagnostic failures

R44 publishes CAMPAIGN_COMPARE.json last, but its late cleanup warning and CLI
cache warning can raise under warnings-as-errors or a failing warning hook.
The user delegated next-step implementation decisions and opted out of repeated
design questions. Extend R47's bounded post-result behavior to this remaining
offline comparator, with no calculation/verdict/schema changes.

## Author-selected design

Move the existing R47 helper unchanged into private integration tooling
`result_diagnostics.py`, import `_warn_after_result(message: str) -> None` into
both R44 and R46 runners, and use the R44 runner's imported helper in its CLI.
Keep the R46 module's private name importable so its existing CLI is unchanged.
The shared helper uses RuntimeWarning first; ordinary delivery exceptions get
one best-effort stderr line. An unavailable sink may lose the diagnostic but
cannot replace a determined result. Never catch BaseException or mutate filters.

Alternatives: copying the helper duplicates policy; importing the R46 frontend
from R44 inverts dependency direction. One stdlib-only shared helper avoids both.
No generic logging framework or new public wheel API is introduced.

## Boundaries

- Preserve completed MATCH0, DIFFERENT1 and ERROR2, including real closed files.
- Preserve rejected input2 with its original rejection code and no completion.
- Before marker/result determination, errors still reject; do not catch defects
  from validation/comparison/rendering. KeyboardInterrupt/SystemExit propagate.
- Default warnings/codes remain observable. No guaranteed diagnostic delivery.
- R46's R47 behavior remains covered by its complete38-test regression suite.
- Public wheel0.3.0, model/reference/producer/limiter, locks/dependencies,
  input/output schema and rendering remain unchanged. Receipts legitimately
  reflect changed tooling-source identities and private paths.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null.
- No F61/actual r/dt/vehicle/Controller/Runtime/CAN execution or activation.
- Feature PR only; no main merge or live HF write in this stage.

## Proof

Inject only cleanup/diagnostic I/O faults around real complete fixtures and
real publication. Check closed root/nested Manifests, returned verdicts and
isolated CLI exit codes, not mock calls. Record source and input immutability.
Compare baseline/fixed saved-value comparison records/summary/child reports and
same saved-input R46 HTML/VIEW byte-for-byte. No fresh browser check is required
when those presentation bytes remain identical. Full dev/cloud gates, one fresh
whole-branch review, actual exact-head CI/artifacts and two deterministic evidence
ZIPs finish the feature stage. No claim of vehicle qualification or provenance
authentication follows from these software checks.
