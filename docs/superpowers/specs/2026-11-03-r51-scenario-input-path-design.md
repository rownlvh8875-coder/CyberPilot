# R51 — Bound scenario input path failures at file open

## Intent and authority

The user delegated routine offline next-step decisions and explicitly opted out
of repeated approval questions. Continue from R50 main
`db7011a35f10dc021158a1ff86a25d48e7f09373`, without repeating its completed work.
Real reproduction: `read_scenario(Path('invalid\0path'))` raises unclassified
ValueError; an unencodable surrogate raises UnicodeEncodeError. The same errors
escape `validate_scenario` and `run_scenario` before model loading. The reader
only translates OSError/AttributeError, while both consumers expect ScenarioError.

## Selected approach

Translate unclassified ValueError raised by **os.open only** into the existing
`ScenarioError('SCENARIO_INPUT_FILE')`, preserving the original cause. Re-raise
an existing ScenarioError unchanged before this catch because it is a ValueError.
Retain the surrounding existing OSError/AttributeError handler and file flags,
bounded read, regular-file check, descriptor ownership and parser placement.

Alternatives: CLI-only handling leaves the reader and validator inconsistent;
catching ValueError across the whole reader risks hiding parser/downstream
defects. No new helper, fallback, schema, dependency or CLI redesign is needed.

## Proof and limitations

Eight regression methods cover actual NUL/unencodable paths; injected open
failures and classified-error identity; programmer/interrupt/parser propagation;
R31 rejection before model/output; R37 canonical rejection with null identity;
isolated real CLI main in both modes with model-import barriers; valid Unicode
and Linux surrogateescape file names; actual unprivileged unreadable-file CLI.
The NUL cannot be passed through an OS argv, so the fresh-process test constructs
it inside Python and calls the actual CLI main; do not claim an impossible shell
NUL argument. Ordinary permission tests use actual OS argv and mode000 bytes.

Existing input/CLI/validator suites stay active. Compare valid baseline/fixed
R31 and validation outputs on the same declared-synthetic inputs: INPUT/TRACE/
SUMMARY and RESULTS without identity exact; allow the truthful observed source
identity/receipt/Manifest changes. Full DEV/cloud gates, unchanged public wheel,
one fresh final branch review, actual exact-head PR CI artifacts, two identical
bounded delivery ZIPs and independent SHA/CRC/Manifest/seal verification.

Do not expand R31 output-path handling, parser semantics, batch/campaign APIs,
public0.3.0 wheel/API, model/reference/generator/limiter, source registry, locks,
cloud tools, CI, runtime or publication/race/crash/rollback guarantees.
Feature PR only: no main merge/HF write in this stage. Preserve old branches,
environments and evidence. R_BUDGET unresolved, StaticFAIL, actualr/T2/vehicle
scale null, Candidate/Runtime NO_GO, F70UH/V/F71 and activation prohibited.
No F61/actualr/dt/vehicle/Controller/Runtime/CAN; synthetic unit/gate work is
NONZERO/unaggregated. Error probes have zero model/reference execution.
