# R39 saved-batch independent reference check

## Intent and scope

The user approved implementing the recommended next step: expose R38 independent
selected-source checks over an entire complete saved R33 batch in one command.
This is an offline DEV tool, not a wheel API, vehicle deployment, generic numerical
proof, source-origin authentication, or rate/time policy resolution.

Build on main dc3cf32dc7d566c5f24420985f99a092e5b71dae. Preserve imported source,
public0.3.0 API/wheel, R31/R33/R34/R38 contracts and hand-authored R35 literals.
CPython3.12.13/Linux/binary64 and existing locked development dependencies remain.
No new dependencies. New public model executions0; independent reference/helper
calculations are NONZERO. Actual r/T2/vehicle scale remain null, R_BUDGET UNRESOLVED,
Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.

## Approaches and decision

1. Shell loop over case paths: short, but skips complete-batch consistency,
   rejection reconciliation and a single durable result. Not selected.
2. Make R33 execute references automatically: mixes generation with inspection and
   changes existing execution/accounting. Not selected.
3. Separate R39 read-only batch checker using R34 snapshot validation and R38
   independent checks: selected by the implementer as the approved recommendation's
   implementation detail. Keeps existing tools and arithmetic unchanged.

The user previously delegated routine implementation choices and opted out of
repeated approval questions. This document records implementer decisions, not
new owner rate-policy approvals. No remote push/merge is included in this task.

## Interface and owned input

`tools/scenario_batch_reference_check.py --input COMPLETE_R33_DIR --output NEW_DIR`.
No raw JSON, portable subset, multiple inputs, r/dt options, overwrite or fallback.
Output parent must exist; output must be outside input/component and not exist.
Validate output guards before input reads. Resolve loops/encoding failures to a
bounded diagnostic. Never traverse paths stored in receipts or BATCH metadata.

Read the original batch once with R34's bounded no-follow `_owned_files`; copy
only those owned bytes into a private temporary snapshot. Run existing `read_batch`
over that snapshot, validating every case/schema/checksum/typed/raw/report binding
before any independent worker. R38 consumes only complete6-file data directories
inside the validated private snapshot. No post-validation reopening of original
input paths. Existing R34 limits apply:32cases/8192samples/512files/128MiB.
This is cooperative filesystem observation, not an atomic/OS-attested snapshot.

## Case classification and aggregate result

Complete cases use unmodified R38. Preserve each successful R38 report and sums,
including DIFFERENT reports. Each case starts from its own declared initial state.
Rejected cases with raw bytes re-run only `parse_scenario`; exact rejection-code
equality is INPUT_REJECTION_CONFIRMED. Valid raw input or a different rejection code
is REJECTION_MISMATCH. Missing raw bytes are INPUT_REJECTION_UNVERIFIED, never green.
These are parser confirmations, not claims about why original file I/O failed.

Overall precedence and CLI exit:

| Condition | Status | exit |
|---|---|---|
| any failed R38 case | ERROR | 2 |
| numerical differences or rejection mismatch | DIFFERENT | 1 |
| any unverifiable rejection | INCOMPLETE | 1 |
| no completed numerical cases | NO_COMPLETED_CASES | 1 |
| all completed match plus confirmed rejections | MATCH_WITH_INPUT_REJECTIONS | 0 |
| all completed match, no rejections | MATCH | 0 |

Malformed batch, runtime/source identity/change, snapshot or publication failure
are request failures/exit2, not numerical differences. Preflight failures publish
no result. A case worker failure may still publish an explicitly ERROR aggregate
with no fabricated successful child report, while other cases remain inspectable.
Failure work may be NONZERO: reference-step/helper totals cover successful reports
only and failed-case counts must not be represented as proven zero work.

## Output and reproducibility

Root `BATCH_REFERENCE_CHECK.json`, `SUMMARY_KO.md`, `SHA256SUMS.txt`, plus
`case-NNN/REFERENCE_CHECK.json` and `case-NNN/SHA256SUMS.txt` for successful R38
checks. Root sums cover every other output file, including child sums. Canonical
JSON, generated relative case paths, explicit cases/counts/statuses/gates, summed
successful reference/helper work, total numerical differences, first difference,
input root/portable manifest hashes and current checker/reference source hashes.
No private paths, input labels, raw logs or source receipt contents in the summary.
Child R38 details retain its256 cap; aggregate does not duplicate unbounded detail.

Source identity before/after includes R38 imported/reference identity plus every
new orchestration/decoder/CLI/summary source. Source changes abort final publication.
New directory creation and exclusive writes only; interrupted partial outputs stay.
Same complete input bytes/current source/runtime produce identical outputs. Different
private input receipts may change full hashes; do not claim full equality across them.

## Acceptance

Tests cover complete/mixed/all-rejected/unverifiable/mislabelled cases; coherent
wrong arithmetic; late corrupt batch before worker; owned snapshot versus original
mutation; child worker error distinct from DIFFERENT; guards, symlinks/FIFO/limits,
source/runtime failure, cold import barrier, no public model, all manifests, moved
input determinism and path-free reports. Real R35 acceptance:6checks/38reference
steps/3confirmed rejections, plus a coherent changed copy that reports DIFFERENT.
Run full development gate, static checks, wheel byte equality, independent final
review and two explicit reference rehearsals before completion claims.
