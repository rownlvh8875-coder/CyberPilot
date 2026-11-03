# R55 — Producer path boundaries and durable overlong coverage

## Goal and baseline

Continue offline development from actual main
`1a82a91d885142af95798eee097606e616154ef2` (tree
`88afdc7831c7f673ef4269a8ba265d56df3c8167`). R54 source is separately pinned for
its continuing backup/recovery operations; this is the single active development
worktree. The owner delegated ordinary execution without repeated approvals.

Five actual raw ValueError reproductions: batch/workflow/exploration/campaign NUL
output paths and batch capture NUL input. Workflow baseline NUL also escapes its
resolution boundary. Existing behavior is not replaced by a new path policy.
Source-authorized generator parameters are seed0..2**32-1/cases1..16/steps16..256;
the first external steps1 probe correctly hit parameter rejection before paths.

## Task 1 design

### Batch capture and preflight

In `scenario_batch_input._read`, preserve ScenarioError first and normalize only
unclassified descriptor/snapshot ValueError alongside existing OSError/AttributeError
to SCENARIO_INPUT_FILE with the original cause. Parsing is outside this boundary.
An unavailable input still becomes the existing per-file rejected BatchInput with
raw/digest/spec null. Workflow still refuses unavailable raw input globally.

Extract `prepare_batch`'s existing prefix, through all path/count/alias checks
before `items = []`, into a private preflight helper without changing its body,
validation order or signature assumptions. Public prepare_batch wraps only that
call: BatchError first, then OSError/ValueError → one new DEV code BATCH_IO with cause.
The batch CLI previously printed raw OSError text and workflow used a generic
WORKFLOW_IO fallback; inherited batch-preflight faults now carry explicit BATCH_IO.
This deliberate diagnostic refinement is documented, not mislabeled as an old code.
Capture, parsing, sample-total cap and return behavior stay outside the wrapper.
Retain UTF8 receipt checks before the existing output guards, final-component
no-follow semantics and duplicate handling. Do not add path repair or NUL labels
as filesystem authority; failed-open metadata is not a valid input or origin proof.

### Workflow baseline

Add WorkflowError-first and ValueError to the existing baseline encoding/
resolution boundary, after the existing UnicodeError mapping. Preserve
WORKFLOW_PATH_ENCODING/WORKFLOW_BASELINE_LOCATION and original objects/causes.
Owned baseline acquisition/snapshot/parse and later identity/work remain outside.
Batch preparation errors continue carrying their existing batch codes.

### Exploration and campaign

Wrap only exploration's existing `_preflight(output)` call with ExplorationError
first, then OSError/ValueError → existing EXPLORATION_IO. Preserve prior seeded
in-memory generation and parameter validation order; no model worker may run.

Campaign preserves its parameter check, seed copy and existing ExplorationError
prefix mapping/cause. Add own CampaignError-first and ordinary OSError/ValueError
→ existing CAMPAIGN_IO around that preflight call only. No later catch-all and
no new generator/limiter/reference formula or state semantics.

## Task 2 — R54-M1 permanent coverage

Add an actual 256-byte-component input/output test for R38 and R39 APIs and real
OS-argv CLIs to the existing committed reference-path test module. Long outputs
reject before acquisition with REFERENCE_IO/BATCH_REFERENCE_IO; non-strict input
resolution may legitimately reach owned readers, returning REPORT_INPUT_FILE /
COMPARE_INPUT_FILE. Preserve that distinction rather than impose a new contract.

This is existing-behavior coverage, expected GREEN on the baseline. Demonstrate
the API output protection retrospectively against exact pre-R54 source when
practical (expected RED), then current source GREEN. An external draft/probe does
not discharge the debt: require actual permanent source commit, test ledger and
historical custody receipt before labeling R54-M1 addressed. Do not rewrite R54.

## Verification / constraints

TDD real NUL/permission paths and typed metadata faults, classified original
object/cause, existing guard/parameter/encoding priorities, parser/later-fault
propagation, invalid CLI bounded exit2, Unicode positive controls and no premature
identity/model/reference workers. Compare moved batch preflight and later bodies
AST-exact, all generator/model/reference/worker/parser bytes unchanged. Same-input
successful output comparison permits only proven orchestration identity deltas.

No public wheel/API/dependency/lock/schema/cloud/CI changes. Old branches,
environments/source snapshots/evidence retained; command-local LFS skip. Full
locked DEV/cloud gates, fresh completion after each task, one final whole-branch
review, real exact-head CI and normal guarded main/private-HF workflow.

R_BUDGET unresolved, StaticFAIL, actualr/T2/scale null, Candidate/Runtime NO_GO,
SOURCE_SCHEMA_UNQUALIFIED6000, F70UH/V/F71/actual activation prohibited. No actual
F61/r/dt/vehicle/Controller/Runtime/CAN. Synthetic work is separately accounted;
passing IO tests supplies no vehicle/source-authenticity/atomicity qualification.
