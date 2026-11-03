# R44 — Read-only saved seed-campaign comparison

## Intent and scope

Compare two complete R43 V1 campaigns in one offline DEV command. Today R34 compares
only a batch; users must manually connect every seed and can overlook campaign
configuration, saved reference findings or ERROR verdicts. User delegated routine
offline development and opted out of repeated design/permission questions. The
author selects this bounded feature; no user claim of choosing these details.

Alternatives: a shell loop around R34 (small, but lacks campaign integrity and
source-error aggregation); a second campaign runner (unnecessary model/reference
work); a separate read-only composition of existing R43/R34 validators (selected).
No new model, oracle, tolerance, minimizer, dependencies or public API/wheel changes.
Deliver a reviewed feature PR with actual CI evidence, not a main merge/HF refresh.

## Inputs and contract

`run_campaign_comparison(baseline: Path, candidate: Path, output: Path) -> dict`.
CLI `tools/scenario_campaign_compare.py --baseline DIR --candidate DIR --output NEW`.
All flags required; no abbreviations, automatic baseline, input/r/dt options.
CPython3.12.13/Linux/binary64 and existing DEV dependencies only.

Accept complete canonical R43 V1 campaign roots:1..4 unique builtin uint32 seeds,
cases1..16, steps16..256. Reject bool/unknown fields/contradictory totals/order/
status/findings/source bindings, partial or portable-only inputs. Use existing
R43 `_child` and R34 `read_batch` checks; reconstruct exact R43 root and R42 child
contracts. R43 V1 deterministic input generation/feature validation occurs in
memory for consistency, but no model, reference worker or selected-source helper
arithmetic is run. This is not a general future-generator/layout loader.

Observed producer identities remain recorded metadata, not current-code or origin
authentication. Validate known identity structure and SHA inventories without
opening caller-supplied paths. Coherent recorded identity changes are permitted
and surfaced separately; value MATCH does not imply identity equality. R38 saved
reference reports are checked for binding/shape, never recomputed as an oracle.

Reuse R43 capture/closed+nested/portable Manifest verification:8192files/512MiB
per campaign,16MiB/file/depth16; child2048files/128MiB. Reject root/ancestor/file/
directory links, FIFOs, missing/extra files, malformed canonical JSON and hashes.
Read both roots fully before output; recapture source hashes and comparator source
identity before publication. Cooperative before/after checks are not atomic OS
snapshots or defense against transient hostile writers/hard-link ownership attacks.

## Comparison and verdict

Align seeds and cases by explicit saved position, never by sorting or scenario ID.
Compare campaign parameters, run addition/removal, each run's recorded status,
model/reference/difference counts and full findings, plus R34 input/row/state/
rejection comparisons for every paired run. Reordered seeds and changed case/step
counts must not silently pair by name or inflate same-input sample counts.
Private paths/logs/Manifest hashes and producer identities are not semantic value
differences; input record/identity hashes remain separately traceable.

`regression_status` is MATCH iff recorded comparison difference_count=0, otherwise
DIFFERENT. Overall `status` preserves source findings: ERROR if either campaign
has any completed ERROR; otherwise DIFFERENT if either source is DIFFERENT or
regression differs; otherwise MATCH. Thus two identical ERROR campaigns have
regression MATCH but overall ERROR/exit2, never vacuous verification success.
Overall MATCH/Different/Error exit0/1/2. Malformed input/IO/source change rejects
with bounded `CAMPAIGN_COMPARE_*` error/exit2 and no completion record.

Retain counts and first difference exactly, with top-level256 detailed differences
and truthful truncation; each paired R34 report keeps its existing256-detail cap.
Do not invent tolerances or infer elapsed time/rate/vehicle qualification.

## Outputs

- `CAMPAIGN_COMPARE.json`: canonical `R44_SAVED_SEED_CAMPAIGN_COMPARISON_V1`,
  overall/regression/source verdicts, both parameters, input record and identity
  hashes, separate producer-identity equality, run records, exact difference and
  comparable sample counts, bounded details, source error/difference run lists,
  zero new model/reference executions, gates and exactness/time/claim boundaries.
- `comparisons/seed-NNN/COMPARE.json` plus one-entry Manifest for paired runs;
  unpaired runs have an explicit addition/removal record and no fabricated batch.
- `SUMMARY_KO.md`: source-aware verdict, parameter/order/identity/difference scope,
  relative links to child comparisons and unchanged safety limitations.
- `RECEIPT.json`: private paths/runtime, source/root Manifest hashes, comparator
  source inventory, forbidden-module observation and cooperative snapshot scope.
- root closed `SHA256SUMS.txt`. Publish CAMPAIGN_COMPARE.json last. Invalid inputs
  make no output; publication failures preserve partial data without final marker.

No upload, sharing, automatic Git action or overwrite inside the CLI. Same inputs,
code and runtime produce identical path-free comparison/summary bytes; private
receipts and complete Manifests can differ. Numerical agreement is recorded-data
comparison, not a new independent numerical result or authenticated provenance.

## Verification and restrictions

TDD reader→comparison/CLI, real saved fixtures from R43 and real R34 comparisons.
Corruption/fully rehashed contradictions, typed counts, paths/files/bounds,
source status/identity changes, positional alignment, bounded difference details,
publication failure and late source/input changes are covered. Fresh isolated CLI
must import no model/native/NumPy modules and execute no producer/reference worker.
Two comparisons of preserved main R43 runs must compare128samples/diff0/new work0;
an independently repaired saved-trace control must detect exactly one field change.
Run full DEV gate, cloud tool checks, one fresh whole-branch review, Important
findings one RED→GREEN fix pass, actual exact-head PR CI/artifact verification.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, actualr/T2/vehicle scale=null, Candidate/
Runtime NO_GO, F70UH/V/F71 and actual vehicle input/activation NOT_ALLOWED remain.
F61/actualr/dt/vehicle Controller/Runtime/CAN/candidate evaluation0; unit fixture/
full-gate synthetic model/reference work is NONZERO and counted separately.
Preserve existing worktrees, branches, main/HF backups and this plan's evidence.
