# R32 — read-only custom synthetic scenario report

User approved the proposed R32: read saved R31 results, verify checksums, show
requested→integer→limited→final graphs and prior state/inactivity/request-bit table
without rerunning the model. Standing delegation opts out of further design menus.

## Approach

Choose a separate stdlib DEV CLI `tools/scenario_report.py --input DIR --output NEW`.
Do not change the frozen package/wheel/fixed-catalog HTML or R31 producer. Reusing
the fixed-catalog analyzer would mislabel arbitrary scenarios as its seven closed
fixtures; importing the public renderer loads the model package unnecessarily.
A small data-only renderer therefore consumes validated R31 projections and
shares the existing inert R31 JSON/CSV projection helpers, not model arithmetic.

## Input custody and interpretation

Linux/CPython3.12.13/binary64, cooperative process/filesystem. Exactly6 regular
R31 files: INPUT.json, RESULTS.json, TRACE.csv, SUMMARY_KO.md, RECEIPT.json,
SHA256SUMS.txt. Open final directory nofollow and members relative to its fd with
nofollow/nonblocking; reject symlink/FIFO/device/directory members, extras/missing.
Bounded snapshots: INPUT/TRACE1MiB each, RESULTS16MiB, SUMMARY16KiB,
RECEIPT512KiB, manifest4KiB. Caps are DEV resource limits, not vehicle constraints.
Manifest must be the exact sorted five SHA256 lines for these names, no traversal,
duplicate, alternate paths or additional file access. Validate before rendering.

Strict canonical UTF-8 JSON: no duplicate/nonfinite/overflow/BOM/trailing data,
numeric tokens128(float)/32(int) characters, nesting64; reuse inert R31 guards.
INPUT typed projection is reconstructed into the existing frozen ScenarioSpec and
preflighted with validate_spec, preserving exact canonical finite float hex and
signed zero.1..4096 samples, adjacency/state/limit domains remain R31's.

Validate full recorded row shapes and primitive types without importing model:
prepared sample/state, quantization, downstream clips/flags/state, projection.
Check stored aliases, initial/next state chain and final state; no recomputation of
quantization, limiter, gate, fault or Float32 formulas. Re-render the inert R31
INPUT/RESULTS/CSV/SUMMARY with the supplied recorded outputs and compare exact
bytes, binding all redundant views, keys, scopes, gates and identities. This is
cross-record consistency, NOT independent numerical validation or authentication.

Producer identity must declare unchanged0.3.0/frozen imported source/wheel identity;
its observed DEV hashes remain metadata, never paths to open or execute. Accept
saved older R31 outputs: new DEV modules legitimately change the producer's broad
source inventory. Never compare historical inventory to today's tools as proof of
authenticity. Receipt is bound by manifest/raw-input SHA but environment facts are
declared, not attested. Original raw scenario bytes are not in the bundle: their
SHA can only be matched across records, not recomputed from normalized INPUT.
Fully rehashed consistent fabricated records cannot be detected by this reader.

## View and publication

Generate portable VIEW.json and self-contained index.html. VIEW holds input's
scenario ID/raw SHA, four portable source file hashes, retained producer identity,
typed rows, final state, descriptive event counts, fixed closed gates and explicit
`CHECKSUM_AND_CROSS_RECORD_CONSISTENCY_NOT_MODEL_OR_ORIGIN_VALIDATION` claim.
Do not put path-specific producer receipt/manifest hashes into portable files.
Separate RECEIPT.json records actual input/output/tool/Python paths and all6
owned source hashes. Output SHA256SUMS.txt covers these3 files.

HTML: escaped text, no JS/network/fonts/external assets, restrictive CSP, clear
synthetic/non-authority badge. Two SVG graphs: original normalized request; integer
request/previous applied/limited/final (separate units). X is invocation index,
never seconds/10ms. Display-only SVG rounding3 decimals; exact hex/integers in
VIEW/table. Single sample centered; flat series get nonzero axis span. Full table
shows previous requested/applied, active, request bit, recorded fault condition,
before/after counter and command stages. Count limiter adjustment by inequality,
not driver-vs-rate attribution; suppression bit is not automatically zero torque.

Existing/dangling output, missing parent or output inside input tree rejects before
reading. All validation/rendering before creating output; exclusive writes, index
last. Preserve partial new output on IO fault, no overwrite/rollback/resume/crash
atomicity guarantee. Require successful CLI exit AND full output checksums.
CLI imports no model/native/NumPy/Controller/Runtime/F61, never reads producer paths
from receipt/identity. Cold private CLI cache prefix; in-process API not isolated.

## Evidence and limits

TDD strict reader/rehash/type/alias/state/caps/files and HTML/CLI tests; use preserved
R31 example portable bytes with constructed test-only receipt, no model invocation
to create unit fixtures. Separate subprocess import tripwire. Baseline/full pure
gates; fresh relocated reproduction twice using the SAME saved R31 bundle, four
source portable files unchanged, report portable2 identical, receipts retained.
Full suite may execute inherited synthetic model tests: report renderer zero-work
separately, never claim whole-task model0. Existing frozen source/native/wheel
guards checked; native regressions inspect retained R31 evidence without new
native execution because no old/native code changes. Fresh final whole-branch
review, feature push/exact-head pure CI/Draft PR2 and deterministic evidence seal.

R_BUDGET UNRESOLVED, Static Gate FAIL, actual r/T2/scale null, no actual activation,
F61/Controller/Runtime/CAN/actual-vehicle/r/dt/candidate execution. F70UH/V/F71
NOT_ALLOWED; no whole-product, physical safety, performance or deployment claim.
