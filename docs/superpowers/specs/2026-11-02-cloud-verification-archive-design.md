# Cloud verification and private archive

## Intent and approach

One explicitly invoked Python command replaces repeated notebook handoffs. Reuse
the unchanged CyberLateral full gate and R41 workflow; do not implement a new
calculator, CI service, GPU job or public model. GitHub stays source authority;
Hugging Face is private artifact storage, not an execution service.

Use stdlib orchestration in tools/cyberlateral_cloud, plus an isolated HF worker
under the already configured SDK interpreter. A GitHub Actions upload integration
would require extra secret/publication policy and is outside this task. Keeping
manual commands only would not meet the requested one-command workflow.

## Contract

- Explicit Git root and full commit SHA. Export only committed
  tools/cyberlateral_dev blobs and required root README/offline workflow context,
  retaining SHA256, Git blob and mode provenance.
  Worktree dirt is neither executed nor included; do not mutate/reset user files.
- Explicit pinned project Python and separate HF SDK Python. Project gate remains
  Python3.12.13/uv0.12.23 and existing lockfile; no app dependency/lock changes.
- New external output only; reject existing paths and symlinks. Preserve failures.
- Run the full component gate, R41 twice, then R41 against the first complete
  batch baseline. Check actual exits, gate counts versus logs, typed hand-derived
  saved rows/views, complete Manifest closure, reference parity and exact portable
  repetition. Never use a portable subset as a complete baseline.
- Deterministic EVIDENCE.zip contains committed component source, provenance,
  path-free acceptance metadata and allowlisted portable workflow payloads only.
  Exclude private receipts/logs/cache/venv and never upload a directory recursively.
  Bound ZIP member counts/bytes, validate paths/modes/root manifest closure, and
  reject obvious credential-shaped payloads (not a universal secret-free proof).
- Existing authenticated own-namespace private Dataset only. Default target is
  jjuinho/cyberpilot-evidence; never create/change visibility or fall back to public.
  Immutable content-addressed runs/<source-SHA>/<archive-SHA>/ targets. Same bytes
  may be retried without new model work or an unnecessary remote commit. Conflicts
  are rejected, not overwritten. Require parent-commit optimistic concurrency.
- Upload ZIP plus sidecar, force-download both at exact remote commit, compare
  every byte/hash and recheck ZIP. Completion is published locally only afterward.
  Authentication/upload/download errors retain local verified output and expose
  stage/error code, not credentials or arbitrary SDK exception text.
- Explicit local-only mode and backup retry are distinct from remote success.
  Checksums establish consistency, not authenticity of an untrusted local receipt.
- All actual vehicle/F61/r/dt work remains0; R_BUDGET unresolved, Static Gate FAIL,
  actual r/T2/scale null, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.

## Completion

New unit tests RED then GREEN, unchanged component full gate, static checks,
one fresh review, then a real end-to-end cloud/private-HF run and idempotent backup
retry. No GitHub merge/push/CI or environment publication is implied by this task.
Keep a local feature commit and the evidence outside the checkout for review.
