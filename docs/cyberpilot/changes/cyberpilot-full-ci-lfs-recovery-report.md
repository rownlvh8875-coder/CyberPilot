# Exact public LFS recovery and Full CI validation

## Identity and purpose

Cyber Validation; public supply-chain verification, baseline `a720b930fa63f1372019a1e696c1b63181da3e81` on `feature/cyber-autotune`. The original Full CI attempt1 failed in setup with 45 HTTP404 lines for 15 unique OIDs. No downstream build or tests ran in that attempt. This increment verifies exact original public bytes and observes an unchanged clean-runner workflow. It does not authorize private E2 or vehicle use.

## Original references and traced path

The current [official upstream configuration](https://github.com/commaai/openpilot/blob/9b899fdaa217533042affa43b566758b42bedac4/.lfsconfig) endorses `https://huggingface.co/commaai/openpilot-lfs.git/info/lfs`. The [official repository](https://huggingface.co/commaai/openpilot-lfs) identifies commaai as operator and MIT license. Each original pointer was retrieved from its immutable official upstream Git commit and matched byte-for-byte to this HEAD. The machine inventory contains all URLs, OIDs, sizes and digests.

Full CI → `tools/op.sh setup` → explicit `git lfs pull` (three attempts) → `op_check_git` → build/regressions. Its one existing exclusion is `big_driving_tinygrad.pkl`; none of the missing15 matches. All15 therefore remain required for the existing setup fetch. Both ONNX assets feed modeld's LLVM-conditioned SCons generation; dmonitoring additionally has a mandatory setup payload check. The other13 retain UNKNOWN downstream dependency classification. OPTIONAL_PROVEN=0; no exclusion was added.

## Changes and verified effect

All15 objects were freshly downloaded anonymously from the existing official HF LFS endpoint's returned CDN actions on 2026-10-19 UTC. Every actual SHA256 and size matched: **15/15, 95,348,970 bytes**. The 10 PNG signatures were recognized; updater is identified by `file` as a Python executable containing binary data. ONNX and pickle files remained uninterpreted binary bytes; no model deserialization or downloaded executable execution was performed during recovery verification. Exact content identity does not substitute for provenance; the official endpoint and upstream immutable pointer supply both parts of the evidence.

The older HF named Git tree is not the complete content-addressed object store. Its stale snapshot cannot establish object absence. The historical official GitLab batch returned nine object-level404 responses and six actions; 404 there is ambiguous between absence and permission. Current HF supplied all15, so no alternative source or mirror was needed. The cause and timestamp of upstream availability recovery are unknown; the earlier CI failure remains immutable.

`verify_full_ci_lfs.py` provides strict pointer parsing and a content-only verifier with bounded streaming, exclusive/no-follow staging, single-link regular-file checks, fsync/readback, partial cleanup and separate content/provenance claims. It has no network, upload, model loading or Git-cache installation API. The new synthetic tests cover wrong digest/size, truncation, pointer-as-payload, symlinks, hardlinks, FIFO, interruption, permissions, traversal, wrong HEAD/workflow, skipped required stages, and clean synthetic Git LFS checkout. The recovery observations and contract are additive JSON receipts; no provisioning workflow was necessary.

Local original `git lfs pull --include=<exact15> --exclude= origin` succeeded. All15 were already present in the local cache before that command: it is a checkout/cache test, not fresh-download evidence. Fresh independent HTTPS streaming supplies the latter. Every cache and checkout file matched again, and both `git lfs fsck --pointers` and `--objects` passed for HEAD. All252 pointers declare 895,134,701 bytes. Six pinned submodules report zero LFS pointers. No binary payload is committed or uploaded.

## Regression risk and acceptance

Acceptance requires original setup, SCons, Ruff, full AutoTune/controls, attribution, lateral, JSON/publication and clean tree all SUCCESS at the final exact HEAD. Setup SUCCESS alone and four independent numerical workflows do not establish FULL_CI_SUCCESS. The original 45-minute timeout and all five workflows are unchanged. There is no alternate required-asset skip or new success authority. Existing231 source pins remain exact.

Prepublication observation: baseline run39283519646 attempt2 job118296556193 passed setup and entered SCons. Full validation was pending at this document's observation; final exact-head outcomes are reported separately through GitHub Actions and the final handoff, avoiding a self-referential receipt. The historical attempt1 remains FAILURE. A later build, dependency, test, publication or timeout failure must be classified separately from LFS failure.

## Validation method and actual results

- New public synthetic suite: 27 PASS; Ruff scoped check PASS.
- Real official anonymous download: all15 SHA256/size PASS; immutable official pointer lineage15/15 PASS.
- Existing231 raw source pins PASS; pointer count252, missing15 reconciled; six submodule pointer counts0.
- Local full regression started with private drive mounts masked; final counts belong to the final handoff when the run completes.
- GitHub final exact-head Full CI and four numerical CI conclusions require completed run evidence. This file makes no premature Full CI success claim.

## Resource, privacy and promotion

Predeclared payload budget is three times the exact missing total (286,046,910 bytes); actual recovery downloads were one set (95,348,970). No bulk history fetch or `fetch --all`. The external plan recorded timeout30 seconds; metadata used30 and the payload socket timeout actually used45. This instrumentation difference is retained explicitly; byte/retry budgets and all user hard caps were unchanged. Staging is outside Git, directory0700/files0600. Signed download actions, credentials and payload bytes are excluded from public receipts. Standard Full CI performs its own original LFS fetch; no additional runner provisioning/disk requirement was introduced. Actual build space and 45-minute completion remain CI observations, not consequences of the payload budget.

Private TRAIN/DEV/metadata/model/handoff reads and real E2 calls remain zero. Public upstream ONNX bytes are separate from private scientific models. D0/D1/historical E2 states, D2 PERFORMANCE_NOT_EVALUATED, selections null, HOLDOUT CLOSED and vehicle authority NONE remain unchanged. Native production integration and private E2 require separate approval and exact capability/host/resource validation even if Full CI succeeds.

## Handoff

Independent supply-chain and CI/scientific reviews must approve final exact bytes before publication. Their hash receipts are recorded in the commit message/final handoff, outside the self-hashed file set. Rollback is removal of these additive diagnostics, not any source/model change. No original configuration was edited. After final fetch/origin/clean-state and exact-head CI observations, STOP.
