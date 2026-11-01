# R34 — saved synthetic batch regression comparison

## Intent and scope

Compare a baseline and candidate R33 batch without rerunning the model. Detect
changes in saved command/state/trace values and rejection outcomes. A match means
recorded-result equivalence only, not arithmetic correctness, physical safety,
performance or vehicle approval. The user delegated technical choices and approved
the R34 proposal; the choices below are the implementer's explicit defaults.

## Approaches

Raw directory diffs include irrelevant environment receipts and HTML changes.
Rerunning the model is unnecessary and would conflate production and comparison.
Use a separate Python CLI over validated owned snapshots of two complete R33
bundles. Existing R32 consistency checks validate each completed R31 record; expose
their bytes-only decoding separately so no input is read a second time.

## Interface

`tools/scenario_compare.py --baseline DIR --candidate DIR --output NEW_DIR`

Linux/CPython3.12.13/binary64, existing pinned DEV environment, no new dependency.
Require complete R33 bundles, not portable sharing subsets. Check canonical JSON,
root and nested manifests, exact generated member paths, count/order/step/gate
invariants, raw snapshot binding, and each completed R31 record/report projection.
Do not follow paths declared in receipts or call producer/render workers.

Own bounded regular-file bytes via directory-relative nofollow/nonblocking opens.
Reject final root/member symlinks, FIFO/device files, unknown members, malformed or
incomplete bundles. Bound depth to4, members to512, each file to16MiB, aggregate
bytes to128MiB per bundle, root Manifest to128KiB, cases to32 and samples to8192.
These are DEV resource bounds, not vehicle limits. Cooperative filesystem checks
are not an atomic snapshot or authenticity/OS attestation.

## Matching and exactness

Align cases by explicit argument position, never scenario_id (duplicates exist).
Different raw inputs are INPUT_CHANGED, not a same-input regression. Added/removed
cases and status/rejection changes are explicit differences. A missing-input case
with no raw digest on either side is UNVERIFIABLE_INPUT, never a verified match.
Same saved rejected bytes and same rejection code can match as a rejection record,
not a numerical result.

For equal raw input and COMPLETE status compare the entire typed INPUT record,
each prepared input/state and every model_output trace/projection/next_state,
then final_state. Exact canonical scalar comparison preserves int/float/bool,
binary64 hex and signed zero; no tolerances. Report source identity changes
separately and never silently treat unchanged numbers as unchanged provenance.
Supported model identity remains the existing R31/R32 public0.3.0 contract.

Record every case's change count and its first change. Keep the first256 detailed
differences globally in traversal order, plus exact total and truncation flag.
List/row traversal is numeric invocation order, not elapsed time. Each detail has
case_id, sample_index when applicable, field path, before and after values.
Missing and null are distinguishable by explicit presence flags.

## Output and failure

Publish canonical COMPARE.json, SUMMARY_KO.md, separate private RECEIPT.json and
SHA256SUMS.txt into a NEW directory with existing parent, outside the component
and both inputs. Validate output location before reading inputs. Completion JSON
is written last; require successful CLI plus valid full checksums, not marker
presence alone. No overwrite/cleanup/resume/crash-atomic promise. Partial outputs
remain after write faults and cannot be reused.

Exit0: exact comparable MATCH; exit1: completed DIFFERENT (including unverifiable
input); exit2: invalid request/bundle/runtime/publication failure. Unknown options,
abbreviations, tolerance/r/dt/policy inputs are rejected. No baseline auto-update.

COMPARE.json contains portable manifest identities, comparison counts/details,
producer-identity-change flags, unchanged closed gates and new model executions0.
It does not copy raw private receipt paths. RECEIPT.json separately records actual
input/output paths, Python identity, comparator source hashes and forbidden imports.

## Non-goals and frozen boundaries

No new HTML/UI, no live/native/log/CAN reader, Controller/Runtime/F61 invocation,
vehicle input, r/dt calculation, policy tuning or deployment. Public0.3.0 source,
API, wheel and imported bytes stay unchanged. R_BUDGET=UNRESOLVED, Static Gate=FAIL,
actual r/T2/vehicle scale=null; Candidate/Runtime NO_GO; F70UH/V/F71 NOT_ALLOWED.
Tests may construct synthetic saved bundles or execute existing synthetic workers
as integration fixtures; comparator execution itself must remain model-free.
