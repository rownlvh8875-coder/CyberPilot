# R53 — Saved-report path diagnostics

## Goal and authority

Continue offline development from R52 main `fdb78740afc429da4578c688c5d42fb6bd591179`.
The owner explicitly delegated routine design/execution and opted out of repeated
approval questions. This specification does not authorize vehicle activation.

Actual baseline reproduction: `read_report(Path('nul\0source'))`, R32 input NUL,
and R32 output NUL raise unclassified `ValueError`. Existing R32 tests30 PASS.
The shared reader's descriptor boundary catches OSError/AttributeError but not
ValueError; R32 input resolution excludes ValueError, and output metadata and
resolution lack an output-specific error boundary. Valid filesystem
surrogateescape paths can also fail late when written into strict UTF8 receipts.

## Design

### Bounded recorded-data reader

Inside `scenario_report_data._files` retain all descriptor/no-follow/nonblocking,
exact member-set, regular-file, byte-cap, close and checksum behavior. Preserve
already-classified `ReportError` first, then normalize unclassified ValueError
along with the existing OSError/AttributeError to `REPORT_INPUT_FILE`, chaining
the original exception. No broad catch around `decode_report` or report parsing.

Direct `read_report` does not create path-bearing receipts: real Linux
surrogateescape directory names remain valid. No new filename/encoding policy
for this generic reader. Consumers get the same classified reader exception;
their separate frontend preflights are not redesigned.

### R32 receipt-producing frontend

Maintain output guard order: existing path/broken symlink → OUTPUT_EXISTS,
missing parent → OUTPUT_PARENT. Then require the literal absolute output string
to be strict UTF8 and NUL-free, before any input read/render. Metadata and
representation OSError/ValueError become new `REPORT_OUTPUT_PATH` with cause.

Require the input's literal absolute string to be strict UTF8/NUL-free, then
resolve it under a narrow OSError/RuntimeError/ValueError → REPORT_INPUT_FILE
boundary. Resolve the output separately under REPORT_OUTPUT_PATH; retain the
existing nested-input output rejection REPORT_OUTPUT_LOCATION. Preserve
ReportError objects/codes/saved causes before broader ValueError handlers.

Only preflight operations are covered. TypeError, KeyboardInterrupt/SystemExit,
later reader/decode/renderer/source/publication failures are not relabeled as
path failures. Do not repair, normalize away or replace caller Path objects.

### Historical test debt

R51-M1 compared `caught.exception.__cause__` with the same aliased exception's
cause. Save the cause independently before injection and compare against that
variable. This is test polish only; explicitly mark the old debt addressed in
new evidence without rewriting R51/R52 historical packages.

## Unchanged contracts / exclusions

No numeric/model/reference/limiter/generator/public wheel, F61 source/API,
payload/VIEW/HTML, clock/rate/normalization policy, dependencies/locks/cloud/CI
or generic parser changes. Successful saved-input HTML/VIEW remain byte-exact.
Existing output/parent/location codes keep precedence. No path safety/atomic
snapshot/symlink-race/crash recovery/physical-machine independence expansion.

R_BUDGET unresolved, StaticFAIL, actual r/T2/scale null; Candidate/Runtime NO_GO.
No actual F61/r/dt/vehicle/Controller/Runtime/CAN or F70UH/V/F71 activation.

## Verification and delivery

TDD actual invalid paths + injected boundary faults, independently saved causes,
real descriptor cleanup, existing classified codes, Unicode/surrogateescape
distinction, pre-read/render barriers, fresh-child actual CLI.main for impossible
NUL argv and real mode000 API/OS-argv CLI. Saved fixtures create no model work.
Baseline/fixed saved-input portable rendering exact; manifests/source immutable.
Full locked DEV/cloud gates, one fresh final reviewer, real exact-head PR CI and
bounded artifact checks, normal exact-head merge/private append-only HF backup
and two fresh cloud recoveries. Keep old source/evidence/environments intact.
