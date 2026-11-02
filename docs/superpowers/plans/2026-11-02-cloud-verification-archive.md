# Cloud Verification Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one fresh reviewer at the end. User opted out of repeated approval questions.

**Goal:** A single explicit command runs committed-source offline verification and a verified private HF archive.

**Architecture:** Stdlib source/artifact module, orchestration CLI, isolated optional HF worker. Existing calculation package, wheel and lock remain unchanged.

**Tech Stack:** CPython3.12.13; existing uv0.12.23 project tools; isolated huggingface-hub2.4.0.

**Spec:** docs/superpowers/specs/2026-11-02-cloud-verification-archive-design.md

## Global Constraints

- No Controller/Runtime/CAN/F61/vehicle data/actual r/dt, GPU or paid jobs.
- Existing private Dataset jjuinho/cyberpilot-evidence; no visibility changes/public fallback.
- Export committed component only; new external outputs; no app API/dependency/lock change.
- Separate local acceptance and remote download-verified acceptance; preserve failure evidence.
- No GitHub merge/push/CI or environment publish; local feature commit after review only.

## Review Focus

- Existing/broken-link output and zip traversal/alias/member/size attacks: artifact tests.
- Public/wrong-identity/missing-credential storage: HF tests, no write side effects.
- Retry after upload or download failure: HF tests, exact content, no model rerun.
- Truncated gate ledger or forged PASS/changed gates: pipeline acceptance tests.
- Portable/private scope confusion or late source changes: pipeline export/selection tests.

### Task 1: Source and sealed artifact boundary

**Files:** tools/cyberlateral_cloud/artifacts.py, tests/test_artifacts.py.
**Interfaces:** export_source(repo: Path, commit: str, destination: Path) -> dict;
seal(output: Path, members: dict[str, bytes]) -> dict;
verify_archive(path: Path, expected_sha: str | None = None) -> dict.

- [ ] Write tests for exact committed Git bytes despite worktree dirt, invalid commit,
  symlink source, deterministic ZIP, checksum closure, unsafe names/modes/aliases,
  output collision, corruption, missing/extra entries, bounded members and secrets.
- [ ] Run `python -B -m unittest discover -s tools/cyberlateral_cloud/tests -v`; observe RED.
- [ ] Implement minimal artifact functions, rerun the same command to GREEN.

### Task 2: Private storage and integrated command

**Files:** tools/cyberlateral_cloud/hf_archive.py, cloud_run.py,
tests/test_hf_archive.py, tests/test_pipeline.py, README_KO.md.
**Consumes:** Task1 dict provenance/seal with archive_sha256 and member hashes.
**Produces:** one-command run, explicit local-only run, retry-backup without model work;
LOCAL_VERIFIED.json before remote acceptance, FINAL_RESULT.json only after exact download.

- [ ] Write HF behavioral tests against an in-memory external transport: public/wrong
  account refusal, success, existing identical content/no commit, collision, failed
  upload, mutated/failed download, privacy recheck; observe RED before implementation.
- [ ] Write pipeline tests for real output/CLI rejection, gate log/count validation,
  closed safety gates, portable selection, failure state and backup retry; observe RED.
- [ ] Implement HF boundary and pipeline, keeping full gate and fixture APIs unchanged.
- [ ] Run all new tests and static checks. Baseline component gate is a separate fresh
  full run. Do not replace it with metadata checks or zero-test success.
- [ ] One fresh read-only review of all new files/spec/plan/ledger; fix Important/Critical
  with RED→GREEN tests and a green full new suite. Keep Minor findings in the ledger.
- [ ] Local feature commit of only new tooling/docs, then real one-command full cloud
  run and private-HF download verification, followed by backup retry without new commit.
- [ ] Record evidence, commands and limits; report actual counts and pending publication.
