# R67 — Korean saved-browser comparison summary

Base: ef90e61b719701096a982b96f3e2a24594c809da. The owner accepted the
recommended next step and previously delegated ordinary offline design and
inline execution without repeated approval questions.

## Intent and approach

Make R66 exact-byte comparisons readable without interpreting saved pixels or
rerunning anything. Author's choice: add `--format markdown` to the existing
comparison CLI and a pure renderer. Default JSON and explicit `--format json`
remain byte-identical to R66 for the same inputs. A separate JSON-file reader
would add a second untrusted input/parser; an HTML viewer would add unnecessary
assets and browser work. Neither is needed for this small change.

## Interfaces and behavior

`browser_compare_summary.render_comparison_summary(result: dict) -> bytes`
consumes a current R66 result, returning deterministic UTF-8 Korean Markdown
with LF and a final newline. It does not read paths, load JSON, write files,
compare images, reclassify recorded metrics or authenticate origins. Validate
the consumed schema/counts/difference rows/receipt fields before rendering;
malformed or contradictory data raises `ValueError('BROWSER_COMPARISON_SUMMARY_INVALID')`.
No fallback, coercion, sorting malformed rows into validity or partial report.
Only fixed owned relative paths and lowercase 64-hex hashes are rendered;
no active links, raw saved content, absolute paths, timestamps or user labels.
The renderer is a reading aid, not an independent validator of source bytes.

The report shows:

- R66 status, compared/changed/unchanged counts, and the 0/1/2 exit meanings;
- separate baseline/candidate recorded R60 status, case count, failed-case
  count, global failure-record count and RESULT SHA (including global FAIL
  with zero failed cases);
- sorted changed paths with full before/after SHA256 and byte size, or an
  explicit no-difference message;
- MATCH is not screen PASS; DIFFERENT is not a new visual regression; quality
  assessment NOT_PERFORMED and source_identity_reauthenticated=false;
- immutable policy boundaries and no new browser/model/F61/vehicle execution.

`browser_compare.py --baseline PATH --candidate PATH [--format json|markdown]`
calls `compare_saved_browser` once, then serializes that same result. Preserve
API result, default JSON spelling/newline, validation order, errors, and exit
0 MATCH / 1 DIFFERENT / 2 invalid. Markdown is written as UTF-8 bytes, independent
of terminal encoding. Invalid inputs/formats produce no stdout and no report.
The tool never creates an output file: shell redirection is caller-owned and
must target a NEW file outside both closed input folders. Invalid input is a
safe stderr error, not a Markdown failure artifact. Do not claim atomic reads,
concurrent-writer protection, pixel similarity or publisher authentication.

## Scope and constraints

Only add browser_compare_summary.py and its tests/guide; modify browser_compare.py,
focused comparison tests and cloud README; commit this spec/plan first. Keep
R64 verifier, producer, probe, existing browser_summary, artifacts, app, locks,
workflows, root README and historical recovery/compare guides unchanged.
Use existing CPython3.12.13/dev tools and stdlib, no installs or network needed.
Reuse the existing linked worktree on a new feature branch; preserve all older
sources, environments, branches, evidence and this task's verification records.
Do not merge main, publish HF, enable Runtime or run new browser/candidate/F61
work. Cloud full unit/gate synthetic work is NONZERO_NOT_AGGREGATED, separate
from passive comparison/summary consumers. No new full DEV/wheel qualification.

R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/scale=null;
Candidate/Runtime NO_GO; F70UH/F70V/F71 and vehicle activation NOT_ALLOWED.

## Acceptance

Baseline full cloud gate 161 tests / 23 owned compiles / static checks PASS.
TDD pins literal rendered facts, global and identical FAIL preservation, complete
hashes/sizes/direction/order, unchanged input, deterministic UTF-8, invalid schema
rejection, CLI default JSON compatibility, 0/1/2 exits and side-specific rejection.
Run actual retained saved bundles twice per case (same/copy, different, FAIL,
invalid sides) without modifying them; compare default JSON to R66 and rendered
facts to an independent raw-byte oracle. Full cloud suite/static/compile PASS,
one fresh whole-branch review and reproducible local evidence. Preserve evidence
even when skills normally clean scratch directories.
