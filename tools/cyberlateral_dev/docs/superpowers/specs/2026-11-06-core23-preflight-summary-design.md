# CORE23 Korean input preflight summary

Builder-selected small offline increment under the user's delegation and opt-out
of repeated approval questions: present current portable input compatibility in
readable Korean without changing the original CORE21 machine receipt or CORE22 CLI.

## Approaches and choice

JSON-only CLI is precise but makes current versus historical fields harder to scan.
Chosen: add a bounded Korean Markdown API paired with the unchanged CORE21 receipt,
following CORE15's existing owned-result presentation pattern and safe cell helper.
HTML/UI or new CLI format options would add independent behavior and are not included.
The builder made this choice; it is not a new full-product requirement from the user.

## Interface and sequencing

New `integration_tools.core_sequence_preflight_report`:

- `report_preflight_archive_bytes(raw: bytes, expected_sha256: str)->tuple[dict,bytes]`
- `report_preflight_archive(input_archive: Path, expected_sha256: str)->tuple[dict,bytes]`
- `PreflightReportError.code` is `PREFLIGHT_REPORT_SIZE` if summary exceeds65536UTF8bytes.

Each public call invokes its corresponding unchanged CORE21 API exactly once and
only renders its owned successful receipt. First tuple element is unchanged CORE21
dict/canonical JSON, second UTF8 Markdown with trailing newline. No public arbitrary
dict/JSON-file renderer, extraction, extra capture, new CLI, state transition or r/dt.
All integrity/preflight exceptions propagate unchanged with no partial summary.
Unexpected semantic-helper or rendering exceptions propagate, never become success.

## Presentation contract

Title `# CORE23 ZIP 입력 사전 검증 요약`, summary contract
`CORE23_PORTABLE_INPUT_PREFLIGHT_SUMMARY_V1`. Show current aggregate status;
case/compatible/rejected counts and all-cases-processed; successful validation prefix
sum versus declared transitions; historical recorded model steps separate from new
model/reference0 and numeric validation NONZERO_NOT_AGGREGATED.

Show full archive SHA, byte size and member count, historical saved M/D/R counts.
Show all three case rows in CORE21 order with current status, current rejection,
validated prefix, declared transitions, saved status, saved rejection and historical
model steps. Null rejection is JSON null, not zero/empty string. State explicitly
that historical MATCH/DIFFERENT/REJECTED does not determine current compatibility,
and successful prefix validation is not a transition execution count.

Reuse unchanged CORE15 `_preview` for every dynamic table cell: typed JSON ASCII,
escape control/bidi/backtick/pipe/HTML delimiters,160-character escaped payload with
PREVIEW_TRUNCATED when clipped. Count clipped cells explicitly. Do not mutate or
truncate the returned original receipt. Full SHA fits; original JSON is exact authority
for displayed excerpts. No untrusted metadata is inserted into prose/headings.

Display all unchanged gates and all six false authority flags (source identity,
arithmetic recomputation,prehistory,V4,F61,actual activation). Explicit limitations:
input compatibility is not stored arithmetic/source/prehistory/vehicle qualification;
actualr/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,Candidate/Runtime=NO_GO,
F70UH/F70V/F71/actual activation NOT_ALLOWED. No fabricated numeric/time policy.

## Verification and scope

TDD: literal default counts2/1/8/9/6; all-valid with historical REJECTED; all-rejected
and early/float rejection rows; exact original JSON, no mutation, bytes/Path/deterministic
parity; every gate/false flag; safe typed cells/nulls/escaping/clipping and byte cap;
bad SHA/corrupt final member fail before rendering; unexpected helper/render error
propagation; single readonly capture/verifier and no file I/O for bytes/no extraction;
blocked producer/reference/F61 imports and model steps. Existing preflight/report
regressions unchanged, full DEV gate plus294 own compiles/static and frozen wheel.
Independent preserved original CORE17 ZIP twice, original CORE21 receipt equality,
bytes/Path Markdown equality, observed one verifier/three cases/eight quantizer calls,
Path capture1/bytes0 and original bytes/modes/layout unchanged. No new fixtures there.

Configured Linux CPython3.12.13/cooperative API only. Initial import infrastructure
caller-managed (-I -B); no atomic/atime/hostile hook/path-race/platform guarantee or
browser visual PASS. Summary work new model/reference0; numeric validation NONZERO,
whole unit/gate fixture work separately NONZERO. Retain branch/worktree/evidence;
no merge/push/PR/CI/HF writes or existing algorithm/API/CLI edits.
