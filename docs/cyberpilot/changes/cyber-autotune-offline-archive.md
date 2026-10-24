# Durable offline proposal and job-audit archive

## Identity and purpose

- Cyber AutoTune STEP8/Validation STEP10; two components implemented and independently reviewed.
- feature/cyber-autotune base1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Preserve proposal version/baseline/previous/rollback/evidence identities and job
  history across process restart, without any active-profile/Params writer.
- Linux local filesystem only; no vehicle specificity beyond existing proposal
  binding. Tests use synthetic values and explicit temporary directories only.

## Original references

- Existing CyberPilot profiles.py/audit.py contracts and native_protocol canonical
  helpers reused unchanged. Official repository https://github.com/rownlvh8875-coder/CyberPilot,
  branch/SHA above. No fork/private code, model data or dependency/submodule changes.
- New original archive codec/filesystem implementation; existing repo license retained.
- Caller ProposalInput/audit chain -> existing contract checks -> strict canonical
  envelope -> owned-directory lock -> temporary fsync -> no-replace publication ->
  directory fsync. Reopen -> bounded read/integrity check -> existing contract checks.
- No controller/estimator/vehicle consumer, live source, network or raw-log loader.

## Changes and expected effect

- archive_codec.py: exact known schema/fields,1MiB byte cap, duplicate/nonfinite JSON
  rejection, separate content/profile identities, proposal and audit reconstruction.
- archive.py: explicit canonical root, descriptor-relative nofollow operations, root
  owner/mode checks, nonblocking directory flock, regular single-link bounded reads,
  Linux renameat2(RENAME_NOREPLACE) and fsync. Unsupported primitive fails closed.
- tests/test_archive_codec.py and test_archive.py: corruption/admission, roundtrip,
  conflict/race/no-overwrite, fsync failures, concurrent terminal writers and restart.
- Generated names only: proposal-hash.json and job-runhash-0/1.json. No active alias.
- STARTED-only is incomplete; terminal means job outcome, never physical PASS. Audit
  terminal requires exact stored prefix and cannot replace another terminal outcome.
- Existing committed/corrupt files never deleted/repaired. Cleanup only operation's
  own temporary inode; crash orphan temps ignored, not scanned or auto-removed.
- Canonically equal numeric profile spellings can have different archive bytes and
  conflict at same profile ID; no silent normalization or overwrite.
- No physical parameter range/rate/limit changed.1MiB/64KiB are serialization/read
  resource limits,0600 private creation mode, flag1 Linux no-replace syscall constant.
- Rollback: stop calling standalone archive; it cannot change the active controller.

## Regression risk and acceptance

- Local filesystem fsync semantics only, not physical power-loss/disk-controller proof.
  Directory must already exist, belong to caller and disallow group/other writes.
  No mkdir/chmod tree or non-Linux fallback. BUSY explicit, caller chooses retry.
- Content hashes are not authority or protection against entire-history rewriting.
  Same-UID hostile mutation/mount namespace/privileged attacker outside trust boundary.
- Wrong units/bounds/safety-locked proposal cannot be saved as valid. Stored evidence,
  confidence and reviewed bounds remain declarations, not physical validation.
- No public upload/private log copying, holdout/H1/H2/acceptance/reference changes.

## Validation method and actual results

- Task1 missing-module RED ->7tests41subtests PASS; package175tests568subtests PASS.
- Task2 missing-module RED ->12tests12subtests PASS; Ruff PASS.
- Final package187tests580subtests PASS;319affectedcontrols+AutoTune PASS9.08s exit0;
  Ruff/diff whitespace PASS. Previous full-PC1282 run remains pre-archive scope.
- Independent review0Critical/0Important/0Minor; focused19tests PASS and additional
  fsync/retry/native publication race/unsupported-syscall probes PASS. No fix pass.
- Actual replay/closed-loop/device shadow/real profile application NOT RUN.

## Handoff

Storage integrity component only; entire STEP8/STEP10 PARTIAL, vehicle NOT_READY.
Remaining trusted evidence, actual usable fit/evaluation corpus, producer contracts,
continuous shadow and executed runtime rollback. No commit/push/merge.
