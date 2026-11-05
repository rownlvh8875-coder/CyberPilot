# CORE2 — Observation-record to V4 contract reconciliation

Base `f3ac2341cd62f50ded786dc1f8d205cf7aeb45e3`, stacked local branch
`feat/core2-observation-binding-contract`. Owner delegated ordinary offline choices
and waived repeated approval questions. This is a documentary/data-contract task,
not a reader/adapter/observer implementation or permission to run actual records.

## Intent and author choice

CORE1 integrated the approved UGHR synthetic reference. CORE2 identifies exactly
which STEP7 observation fields could supply each of its inputs, what cannot be
substituted, and what evidence or explicit capture is still missing. Directly
converting the STEP7 draft to V4 would invent source identity/flags. Rewriting the
UGZ checker would duplicate a different consistency checker. Chosen: a closed
static field map, role dispositions and fail-closed design obligations; no runtime
transformation or new sample/record instances.

## Authorities and constraints

Verify the exact UGHR, UGY and UGZ_R1 sealed archives, complete CRC/Manifest/seal,
their four identical UGY documentary JSON members and seven STEP7 reference files.
Only source/AST inspection; never import/execute/bytecode-compile target sources.
Current V4 constants and adapter bytes must stay unchanged. UGY is per-file content
from different observations, not a coherent snapshot, commit or deployment receipt.
Compare the six shared paths with both UGHR commits and mark the seventh path
absent from that archive, not absent from all Git history or equivalent by symbol.

Create `tools/cyberlateral_dev/docs/F61_OBSERVATION_BINDING_CORE2.json` and companion
Korean guide. Cover all 41 leaf fields in V4's closed input schema, allowing grouped
current/previous rows, and all 35 UGY roles. Each mapping has explicit record
selector/pointer or null, documentary authority, candidate transformation and
unresolved conditions. Null means no permitted binding in this draft, never a
runtime default. All mappings remain ineligible to emit a V4 payload.

Required distinctions: same-stage previous request vs current limiter previous
limited argument; readBits32 word vs Python float; int64 text vs exact Python int;
declared clocks vs verified time; request-stage active vs later multiple active
reads; driver torque/fault/longitudinal override vs F61 override metadata;
generation equality vs explicit reset semantics; CANFD bit13 vs torque-control
mode; request identity scale1 vs integer STEER_MAX and rate policy.

UGZ pair acceptance only orders timestamps; it does not establish V4's exact
seconds subset. Its active-only subset is narrower than V4's preserved flag domain.
Do not turn its synthetic PASS or fake receipt references into authentication,
actual input eligibility or calculator authority. Explicit synthetic declarations
are new fixture metadata, not derived from UNQUALIFIED_OBSERVATION_CANDIDATE.

## Deliverables and completion

Add source/field comparison and rejection obligations, mark the bridge
NOT_IMPLEMENTED/BLOCKED_FOR_EXISTING_OBSERVATION_RECORD, and update the core backlog
and component README. Include a concrete CORE3 entry boundary: an explicit
counterfactual request snapshot must carry source/profile, same-stage active and
override, reset/loss/config/controller/clock context and raw request/time. It does
not retrofit missing flags into the sealed UGY schema or broaden V4's source pins.
Write an implementation-ready CORE3 plan only after those design facts are settled;
CORE2 completion does not require guessing its API now.

Verify static coverage/pointers/authority hashes/source comparisons, negative
metadata controls, canonical JSON, repeated-process deterministic audit and
preservation of every existing Python/lock/workflow/profile. No new runtime feature
tests or full model suite are needed for this data/docs-only change; do not claim
the historical 927 tests were rerun. Use scoped Codespell/JSON/link/diff checks and
one fresh builder check of the finished design. Keep all evidence and local branch.

No push/PR/main merge/HF writes/CI dispatch. No records, V4 payloads, calculator
args, native conversions, source arithmetic, dt/r calculations or source imports.
R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/F70V/F71 NOT_ALLOWED.
