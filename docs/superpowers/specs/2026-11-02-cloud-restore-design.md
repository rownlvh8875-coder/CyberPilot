# Cloud-only DEV restoration

## Intent and decision

Turn the verified external main-be266bb4 recovery procedure into a reusable
explicit command. The user delegated subsequent offline development choices and
opted out of repeated approval questions. Reuse the existing isolated worktree on
`feat/cloud-only-restore`, starting at main be266bb4. No push/merge/publication is
part of this change.

Approaches considered: leave the many manual snippets outside Git (hard to reuse
or regression-test); add a read-only restore command beside the archive command
(selected, reuses its proven boundaries); automatic startup/CI/HF execution
service (extra authority and lifecycle, excluded). This is the agent's scoped
implementation choice, not a new vehicle or policy approval.

## Contract

- `cloud_restore.py` takes a trusted local Git root with an exact full source
  commit, full archive SHA256, exact HF revision, own private Dataset, separate
  SDK Python, and NEW external output. It restores the DEV component only, NOT a
  complete Git repository/native/vehicle installation. GitHub remains whole-source
  authority; users clone it before invoking this command.
- A new `hf_archive.py fetch` worker is read-only. Verify own namespace, current
  and pinned private state, full revisions, bounded ZIP and exact checksum at
  `runs/<source>/<archive>/`. Verify CRC/Manifest/hash/source commit before success.
  SDK stays out of the app environment. No fallback, upload, repo creation or
  visibility change. Errors expose bounded codes rather than upstream text.
- Before executing anything restored, compare the complete SOURCE member set and
  SOURCE_IDENTITY (blob/mode/size/SHA/tree) to a fresh committed Git-object export.
  Dirty and untracked local bytes do not participate. Only verified SOURCE files
  are materialized; downloaded DRIVER is never executed. No blind ZIP extraction.
- Use existing uv0.12.23 and CPython3.12.13 (no implicit Python downloads), a NEW
  app venv and dedicated cache, unchanged app lockfile. Check dependency versions,
  module origin and absence of HF SDK in app env. No global installs/config.
- Run existing R41 workflows one/two/baseline, existing saved-literal/reference/
  Manifest acceptance, then compare all26 portable files exactly to HF R41 bytes.
  Nominal/basic restore is not a fresh700-test rerun or physical-machine proof.
  Explicit972model/972reference steps plus any unit work are synthetic only.
- Completion requires source bytes unchanged, all gates unchanged, and local
  RESTORE_RESULT.json/DEV_START.json. Failure records stage/code, preserves partial
  outputs, and never generates those success receipts. Existing paths/symlinks
  (including ancestors) or output inside the Git root are rejected.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL, actualr/T2/scale=null, Candidate/Runtime
  NO_GO, F70UH/V/F71 NOT_ALLOWED. No F61/actualr/dt/Controller/vehicle Runtime/CAN/
  vehicle input/deployment. Synthetic model/reference work is NONZERO.

## Verification

RED→GREEN tests for read-only fetch, exact source reconstruction, path/error
boundaries and actual saved-result comparisons. Existing cloud suite and unchanged
DEV gate remain green. Run the new command against pinned private be266 archive
in a fresh external folder; corrupt/conflicting inputs must not become success.
One fresh whole-branch review, local feature commit only, preserve evidence.
