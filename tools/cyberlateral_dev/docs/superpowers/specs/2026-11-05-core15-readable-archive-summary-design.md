# CORE15 readable saved-ZIP summary

User approved progressing from CORE14 to a human-readable summary and delegated
ordinary builder decisions. Choose Korean Markdown, building on existing CORE10
Markdown conventions, not HTML/browser UI or new untrusted JSON intake. This needs
no new dependencies or execution. Full CORE14 JSON remains the complete comparison.

## Interface

New integration_tools/core_sequence_archive_report.py:
`report_suite_archives(left: Path, left_sha256: str, right: Path, right_sha256: str)
-> tuple[dict, bytes]`, plus `report_suite_archive_bytes` with byte inputs and same
digest arguments/return. Return the unchanged CORE14 comparator-owned dict and
UTF8 Markdown bytes. Each calls existing CORE14 comparison exactly once, capturing
each role once; no reopen/extraction. Private `_markdown` accepts owned results
only; no public raw-dict/JSON-file rendering API. Reject all inherited malformed
ZIP/SHA and4MiB diagnostic-budget errors before rendering, without fallback.

Separate tools/core_sequence_archive_report.py accepts required --left-archive,
--left-sha256, --right-archive, --right-sha256, no abbreviation. Markdown stdout
only, exit0 identical/1 validated difference/2 rejection, same as CORE14. No run,
extract, r, format or output-file flags. Cleanup, formatting and exit computation
precede output; fixed diagnostic ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION for
unexpected CLI errors, ARCHIVE_REPORT_CACHE_IO_NO_MODEL_EXECUTION for cache creation.
Preserve inherited ArchiveCompareError codes; ArchiveReportError for summary size.

## Readable projection, not a new decision

Title CORE15_ARCHIVE_SUMMARY_V1. Show byte comparison status, both whole SHA/byte
size, saved M/D/R counts/history steps, all three case IDs/order, full per-case and
aggregate INPUT/RESULT/IDENTITY totals, comparison detail count/truncation/budget,
zero new model/reference execution and unqualified source/arithmetic flags. Include
unchanged gates and explicitly label historical work vs new work. Saved D/R stays
data; equality is not a new numerical MATCH/qualification/vehicle approval.

Show first20 retained details per case,60 overall. Preserve full counts and
separately state CORE14 retained count vs CORE15 shown/omitted counts. Use case-relative
JSON pointers together with case labels. Presence columns distinguish missing/null;
typed JSON previews distinguish false/0 and strings. No tolerance or coercion.

Each untrusted cell's JSON representation uses ensure_ascii=True and escapes
backtick/pipe/HTML delimiters as literal Unicode JSON escapes within code spans.
Stream preview encoding; at most160 escaped ASCII payload characters per cell.
Append explicit PREVIEW_TRUNCATED marker when content omitted; previews need not
be parseable/full JSON and never replace originals. No raw controls/bidi/newlines,
active links/HTML, added table rows/columns or unescaped backticks from data.
Output cap65536bytes before any publication; ARCHIVE_REPORT_SIZE on overflow.
These are builder display/resource choices, not F61/r/Owner vehicle policy.

No timestamps, caller paths, current source hashes, model/vehicle work or network
publication. Markdown source/escaping checks do not establish every renderer's
visual behavior; no browser visual PASS claimed. Configured Python3.12/POSIX and
cooperative FS assumptions unchanged. No atomic snapshot, malicious path/alias
races, atime preservation, fsync or repeated CLI embedding guarantees.
Actual r/T2/vehicle_scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL;
actualinput/F61/Controller/Runtime/CAN/actualr0; activation/F70UH/F70V/F71 NOT_ALLOWED.
Keep local branch/evidence and previous refs; no merge/push/PR/CI/HF writes.
