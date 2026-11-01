# R33 declared-synthetic scenario batch

## Intent and scope

Run several explicitly named R31 synthetic JSON files, independently, and link
their existing R32 reports from one Korean static index. User delegated ordinary
technical choices and asked to proceed without another approval round.
This is developer tooling, not a vehicle reader or production adapter.

## Approaches and implementer choices

1. Chosen: repeated `--input PATH` arguments, in supplied order; no discovery.
   Explicit bounded inputs avoid accidentally selecting unrelated JSON files.
2. Directory discovery would be shorter to type but creates selection ambiguity.
3. A new multi-scenario document would duplicate the established R31 schema.

Python stdlib only. Reuse unchanged R31 and R32 CLIs in fresh subprocesses,
including their identity/runtime checks. Separate workers prevent the model
imported by the producer from contaminating the data-only renderer's receipt.

## Contract

- CLI: `tools/scenario_batch.py --input A.json --input B.json --output NEW`.
- Linux CPython3.12.13/binary64, matching existing tools. No new dependencies.
- 1..32 inputs; at most8192 valid samples in aggregate, each existing R31 limit
  remains in force. Duplicate resolved input paths reject the whole request;
  distinct files may deliberately share scenario_id. No state crosses files.
- Validate output location/existence/parent before reading inputs or running a
  worker. Output cannot be within the component, nor contain an input path.
  Final input symlinks/nonregular files reject, with nonblocking bounded reads.
  Ancestor paths and the process are cooperative, not an OS security boundary.
- Preflight all named files before starting any model work. Per-file read/schema
  errors become REJECTED rows, not skipped files. Valid files still execute.
  Count/total-step/path/output errors reject the whole batch without publication.
- Own bounded original bytes first; preserve each available <=1MiB snapshot in
  the new output. Workers consume those bytes, not a later original-path read.
  Oversized/unreadable files have no full-byte digest/snapshot claim.
- Generated case-001 etc identify files; names/IDs never become output paths.
- Per-case output: R31 data, R32 report, isolated worker logs. Any unexpected
  worker/identity/publication failure aborts the batch; partial files remain,
  without the final BATCH.json completion marker. No retry/overwrite/rollback.
- Top-level BATCH.json: portable ordered rows, input basename/digest, scenario ID,
  COMPLETE/REJECTED status, rejection code, steps and relative output links.
  COMPLETE means execution/report generation, not independent numerical PASS.
  Totals, unchanged GATES and declarative-origin/time limitations are explicit.
- Top-level index.html: escaped static Korean table/cards, readable responsive
  layout, no scripts/assets/network. Links use only generated relative paths.
  No new chart implementation; reuse child reports. Structural checks do not
  constitute an actual desktop/mobile browser visual PASS.
- RECEIPT.json holds absolute input/output/source paths and execution environment.
  SHA256SUMS.txt covers every output except itself. PORTABLE_SHA256SUMS.txt covers
  BATCH/index, owned snapshots and portable R31/R32 files, excluding worker logs,
  receipts and receipt-bearing manifests. No whole-manifest equality claim for
  environment-bearing outputs. Completion marker BATCH.json is written last.
- Exit0: all complete; exit1: completed batch with input rejections; exit2:
  request/runtime/worker/publication failure. No silent success on partial output.

## Fixed boundaries

Public0.3.0 source/API/wheel/arithmetic unchanged. No r/dt/T2/vehicle-scale inputs
or fallback, F61 execution, Controller, Runtime, CAN, real vehicle data or native
qualification. Synthetic model calls are nonzero and counted per completed file;
unexpected worker failure does not assert zero work or a total. R_BUDGET remains
UNRESOLVED; Static Evidence Gate FAIL; actual r/T2/scale null; activation forbidden.

## Verification

TDD preflight/resource/path failures and no-worker tripwires; exact sign/resumed
literal regression, driver/inactive/reactivation cases; mixed/all-invalid batches;
duplicate IDs, HTML injection, snapshot ownership, deterministic portable bytes,
worker failure and publication faults. Run full component gate, unchanged wheel,
fresh committed export, one independent branch review and dedicated CI. New
branch/Draft PR only; main merge is a separate owner decision.
