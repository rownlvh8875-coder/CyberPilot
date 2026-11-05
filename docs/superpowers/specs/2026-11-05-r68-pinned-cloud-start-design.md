# R68 — one-command pinned cloud development recovery

Base f562377abefdc5796f54b4f98c0c3ded9a5a4a3e. The owner delegated ordinary
offline next steps and inline execution without repeated approval questions.
R67 HF evidence efe2d37dfc9bf3b175d876434f8c6fcd9e39506bed436dfdbbc0954c34c0be34
proved the two archives below; current handoff needs an external helper and
several commands. This small feature puts that workflow in reviewed Git tools.

## Approach and scope

Author choice: compose existing read-only cloud_restore/hf_archive and passive
comparison APIs; add a bounded supplementary-tool recovery helper. Do not change
the established DEV archive/API, add upload behavior or execute downloaded
DRIVER code. Keeping the external script leaves a missing dependency; changing
the archive layout would invalidate existing pins. No UI/browser dependency.

Only the CLI's built-in R67_MAIN_V1 profile is exposed. No user profile file,
moving main/latest reference, environment override, numeric rate policy or fallback.
Python engine functions accept explicit records for independent fixtures/testing;
that is not a second CLI profile or an origin-attestation interface.

## Frozen profile

schema_version1, profile_id R67_MAIN_V1, HF repo jjuinho/cyberpilot-evidence.
source_commit f562377abefdc5796f54b4f98c0c3ded9a5a4a3e.
source_tree 6b42352b0ee2a2a5259837a4df779d47c7b7c54a.

- dev.sha256 adeaf66e4212ffa350c5b851c684153eac0f5953716f9e9449afd22d5c031c22
- dev.revision 5916191894529c579451b21c7f3f18b9f5eee2ed
- tools.sha256 c7ca0b6fd9ed46cd31d3456b39536b35203799070dfee0e89ed485eb7004723d
- tools.revision 9d41b3cccacc25fa7c4843b1a1a44f23a33ed16e

These are original archive/source identities, NOT the new R68 tool commit.
Keep historical R62/R64 guidance and its original pins unchanged.

## Supplement recovery boundary

`tooling_restore.recover_tooling(repo: Path, commit: str, archive: Path,
digest: str, destination: Path) -> dict` mirrors the existing DEV recovery API.
Use existing bounded archive verification/captured payloads. Independently derive
Git bytes/blob/mode/size/SHA for tools/cyberlateral_cloud plus the two R67 spec/
plan documents; require exact canonical SOURCE_IDENTITY (including the original
scope string) and exact SOURCE member set. Never trust dirty checkout bytes,
copy .git/untracked data, transform newlines or execute archive SOURCE/DRIVER.

Only restore SOURCE and SAVED/{one,two,fail}; ancillary archive members remain
unexecuted. Strict JSON metadata rejects duplicate keys/non-finite constants.
SAVED has exactly the fixed R64 38 names per alias. Validate metadata hash/size
types and ordinary permission bits, write fresh regular files, validate each
whole saved bundle with the existing reader and compare its computed receipt to
the saved identity. This is record consistency, not new visual/source authentication.
All source substitutions/identity/member errors fail before destination creation.
An invalid saved bundle may leave partial source/data after creation, never a
success return; caller keeps failure evidence. No repair/delete/overwrite.

Return EXACT_GIT_MATCHED_TOOLING_AND_SAVED_RECOVERED, source commit/tree/count/
identity, saved count114, original receipts, downloaded_driver_executions0.

## Entry point and engine

`cloud_start.py profile` returns deterministic JSON for the built-in frozen pins
without SDK/auth/network/Git lookup or app/browser imports.

`cloud_start.py run --hf-python EXISTING_SDK --output NEW_EXTERNAL
[--repo-root EXISTING_GIT_ROOT]` uses the existing repository by default.
Full option names only. `get_profile() -> dict` returns a detached profile.
`run_profile(repo: Path, sdk: Path, output: Path, profile: dict) -> dict` is the
testable engine. Validate all full SHA/revision/tree/repo/profile types before
invocation; reject unavailable Git commit/tree rather than fetch/relabel it.

Output must be new, outside the repository, with existing non-symlink parents.
Keep inherited auth/proxy/CA. Reuse existing SDK; no login, implicit Python
download, global install or old environment writes. Existing cloud_restore creates
the task-local app venv with locked dependencies and explicitly runs synthetic R41.

Run stages in order:

1. SDK_PREFLIGHT / pinned Git/profile checks.
2. DEV_RESTORE: existing cloud_restore worker with exact dev/source/revision;
   require successful durable RESTORE_RESULT plus DEV_START. Validate source/tree,
   unchanged gates, read-only/zero actual-work counters, R41 acceptance and scope.
3. TOOL_FETCH: existing hf_archive fetch with exact tools/source/revision;
   require matching private/read-only receipt, archive digest and namespace.
4. TOOL_SOURCE: recover_tooling and write TOOL_RECOVERY.json.
5. SAVED_COMPARISON: current trusted Git comparison code reads recovered data,
   never executes recovered SOURCE. Save one/two DIFFERENT and fail/fail MATCH
   JSON plus Korean summaries outside closed SAVED folders. Original FAIL remains.
6. Write START_KO.md with links to child results, then START_RESULT.json LAST.

Success R68_PINNED_CLOUD_START_PASS means recovery completed, NOT screen PASS or
vehicle qualification. Include pinned profile, source counts, comparison records,
relative child paths, unchanged GATES, remote_writes0, downloaded_driver_executions0,
new passive browser/F61/actual-r/dt/vehicle work0 and explicit synthetic R41 work.
Child DEV success alone is not overall completion. Output is not an atomically
sealed full filesystem/venv snapshot; no writer-race or publisher attestation.

On any post-creation failure retain children/logs, write FAILURE.json with stage,
safe code and outputs_preserved=true; no START_RESULT. CLI exit0 profile/success,
exit2 invalid/error (including transport failure). Normal saved DIFFERENT exit1
does not fail this orchestrator. No root success on partial/corrupt/public/wrong
owner/missing SDK/time/source/gate evidence. Never use r=0 or fill null policy.

## Changed files and preservation

Add cloud_start.py, tooling_restore.py, their two test files and
docs/PINNED_CLOUD_START_R68_KO.md; update cloud README; commit this spec/plan first.
No existing helper/producer/verifier/comparator/app/lock/workflow/rootREADME or
historical-guide edits. New local feature branch only; main/push/PR/CI/HF writes
NOT_RUN this task. Reuse existing linked worktree and app/SDK environments; keep
all old evidence and this task's ledger/workspace instead of skill scratch cleanup.

Acceptance: baseline179/25/static; TDD real local Git/archives/saved bundles and
only external SDK/network/venv worker boundary doubled in unit tests. Full cloud
suite/static/29owned compiles; actual default profile in TWO fresh external folders,
same restored bytes/saved comparisons, read-only HF metadata unchanged. One fresh
whole-branch review, one Critical/Important TDD fix pass if needed, deterministic
evidence/independent custody checks. New full DEV883/wheel/real browser not required:
inherit unchanged source proof, distinguish fresh R41 and unit synthetic work.

R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/scale null; Runtime/Candidate
NO_GO; F70UH/F70V/F71 and vehicle activation NOT_ALLOWED. Logical same-host
recovery only, not complete repo/native/physical-machine independence.
