# R52 — R31 execution-path preflight before model work

## Intent and observed cause

Continue routine offline development under the user's explicit instruction to
proceed without approval prompts. Base main:
`29a8885581b91adbf255b2f202038ef70d630ee4`. Use existing Python/unittest/stdlib.

Real NUL/unencodable output Path values reach read_scenario: exists/is_symlink
can swallow ValueError and the parent is valid. A real surrogateescape input file
is correctly accepted by the generic reader/R37 but R31 reaches load_model even
though its UTF8 JSON receipt cannot encode that pathname. Read/load barriers
reproduced both ordering defects without executing a model or creating output.

## Selected approach

At run_scenario's preflight only, preserve existing output exists/symlink/parent
checks and their precedence, then qualify the output pathname for UTF8 JSON and
NUL absence. Re-raise existing ScenarioError unchanged; classify otherwise
unhandled OSError/ValueError as chained SCENARIO_OUTPUT_PATH. Then qualify the
input pathname for the same receipt representation, classifying OSError/ValueError
as chained existing SCENARIO_INPUT_FILE. Only afterward call read_scenario and
load_model. Do not normalize, resolve, repair or replace either supplied Path.

Alternatives: CLI-only catching leaves the public frontend API and pre-read
ordering wrong; a whole-function catch hides later defects; reusing R34 preflight
would impose unrelated location/runtime policy. Choose narrow R31 boundaries.
SCENARIO_OUTPUT_PATH is one documented new DEV rejection code, not a new model API
or payload schema. The generic reader/R37 retain valid filesystem/surrogateescape
input support; R31 execution needs the stricter receipt representation.

## Proof

Ten regression methods cover invalid outputs before input reads; unsupported
execution inputs before reads; classified object/code/saved-cause and old-code
precedence; ordinary filesystem classification; programmer/interrupt propagation;
later reader/loader ValueError propagation; fresh actual CLI main with import
barriers; real unprivileged permission output; actual Unicode execution with
literal final commands [2,-2,0,2]; unchanged R37 surrogateescape validation.
NUL cannot enter OS argv, so construct it inside a fresh child and call actual
main(argv). Use real OS argv for ordinary permission and valid filenames.

Keep reader/R31/R37 suites active. Compare same declared-synthetic normal inputs
at base/fixed: INPUT/TRACE/SUMMARY and RESULTS excluding identity exact; R37 JSON
exact. Record truthful changed source identity, never whole RESULTS/receipt parity.
Run full DEV/cloud gates, unchanged public wheel, one fresh final review, actual
exact-head CI/artifact verification and deterministic evidence; continue normal
guarded main/HF integration rather than asking the user to approve each phase.

## Boundaries

No changes to generic reader, validator, parser, model/reference/limiter/generator,
public0.3.0 wheel/API, input/output payload keys, locks, cloud tools/CI, shared
R34/R44/R46 helpers, source/runtime environment identity or publication/crash/
rollback guarantees. TypeError/BaseException and post-preflight defects propagate.
Do not qualify every possible source-root/interpreter metadata environment here.
Existing source copies, branches, environments and evidence are preserved.
R51-M1 stays deferred; no unrelated test polishing in this task.

R_BUDGET unresolved, StaticFAIL, actualr/T2/vehicle scale null, Candidate/Runtime
NO_GO, F70UH/V/F71 and actual activation prohibited. No actual F61/r/dt/vehicle/
Controller/Runtime/CAN work. Error probes model/reference0; valid fixtures and
unit/gate/CI work NONZERO/unaggregated, not physical timing/performance evidence.
