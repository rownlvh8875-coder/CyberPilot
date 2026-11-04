# R61 — Korean browser observation summary

Baseline: b01ae91e9858772099622f3c6c81a03afbe5fc04. The owner delegated ordinary
offline next-step choices and inline execution without repeated questions.

R60 is now reproducible from cloud Git/HF, but its completed result is a long JSON
plus separate captures. Add SUMMARY_KO.md to each completed R60 command output so
the owner can read the ten recorded observations and find the relevant captures.

Author's choice: deterministic UTF8 Markdown beside the existing machine result.
Keeping JSON alone leaves manual inspection cumbersome. A new HTML dashboard or
browser CI would add an unrelated UI/dependency surface; neither is selected.

The summary shows recorded PASS/FAIL, actual browser/library versions, each
profile/width verdict, measured document width/pan, visible charts/minimum label
font, user table motion, failure-code explanations and available relative links.
Include any whole-run failure records even when all individual cases pass.
Unknown/missing observations are shown as unknown, not invented zero/false facts.
Keep the distinction between observed browser results, ordinary pure CI, source
integrity and numerical/origin/vehicle qualification explicit.

This is an internal presentation function over the fresh producer record, not a
new saved-input CLI or a general JSON reader. It must reject empty/duplicate/
missing selected cases and contradictory PASS/failure flags, rather than print
vacuous success. Do not re-run the browser, classifier, model, reference or F61.
Escape metadata as data. Links may target only fixed known relative report and
capture paths actually present in the owned file snapshot; no external/absolute/
traversal targets. Keep field values/types visible and raw RESULT authoritative.

Publish the summary exclusively before checksum and RESULT. Include it in the
closed checksum set; keep RESULT as the last completion marker. On a summary or
checksum write error, never leave a success RESULT. A leftover partial summary is
not completion and says so prominently. Preflight/runtime rejection remains exit2
with existing partial FAILURE semantics and does not gain a fabricated summary.
Completed PASS0/FAIL1, stdout, RESULT schema/version and browser verdicts stay as
R60. Existing outputs are never overwritten or automatically deleted.

Change only cloud summary/publication/tests and usage documentation. No app,
browser_probe, public wheel/model/API, lock/dependency/default workflow, r/T2/
scale or vehicle changes. Default tests must not require Playwright. Real runs
with the existing host browser must prove PASS and old-CSS FAIL summaries, valid
local links, closed manifests, unchanged HTML/VIEW and two-run summary equality.
One fresh whole-branch review, feature Draft PR and actual CI; main/HF integration
is a separate subsequent task. Retain external evidence and old environments.

Maintain R_BUDGET unresolved, Static Gate FAIL, actualr/T2/scale null,
Candidate/Runtime NO_GO, and F70UH/F70V/F71/vehicle activation NOT_ALLOWED.
