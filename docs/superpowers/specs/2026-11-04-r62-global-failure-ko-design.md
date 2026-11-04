# R62 — Korean explanations for whole-run browser failures

Baseline e5b76678cff4d45a4915da0f9b26982711167b1d. The owner delegated normal
offline next-step choices and inline execution without repeated approval questions.
Resolve the preserved R61 review M1: whole-run failures currently show only raw
JSON, unlike the translated case table. The exact current producer emits
UNEXPECTED_BROWSER_REQUEST as a whole-run record after case observations.

Author's choice: retain each escaped raw failure record and append Korean
explanations for its codes using the existing REASONS/future-code label. Do not
replace raw JSON, change the upstream producer/classifier or add new semantics.
Unknown codes keep their original identifier. An empty code list keeps its raw
record, without inventing a reason or saying the failing record has no failure.
PASS output, individual table rows and fixed links must remain byte-identical.

This is an internal fresh-producer Markdown reading aid, not a new saved-input
reader. Keep escaping, validation, RESULT V1/stdout/exit0/1/2, exclusive publication,
closed checksum, and last RESULT marker unchanged. No model/app/probe/locks/
dependencies/workflows, F61/r/dt/vehicle policy, installs or prior evidence edits.

Alternatives considered: leaving raw English codes alone leaves M1 unresolved;
changing the JSON API or browser classifier is unnecessary. The selected small
presentation fix uses the existing translation authority, not new observation.

Verify missing explanation RED→GREEN, full cloud suite/static checks, two real
positive browser runs and a harness-induced real blocked loopback navigation
control: all ten case rows PASS but whole run FAIL with raw code/count and Korean
explanation. No CSP relaxation, renderer/DOM edits or fabricated observations.
Clearly label that negative control as test-induced, not a naturally failing page.
Reuse prior exact DEV883/main CI only as inherited evidence: do not claim a new
DEV gate or wheel build. Compare unchanged app/probe/workflow Git bytes instead.

One fresh whole-branch review, feature Draft PR/actual CI and independently verified
reproducible evidence. No main merge/HF writes in this feature task; preserve old
source/branches/workspaces/evidence. All vehicle/r/T2/scale gates remain closed.
