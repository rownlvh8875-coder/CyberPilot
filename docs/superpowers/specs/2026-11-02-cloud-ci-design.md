# Credential-free cloud tooling CI

## Intent and agent decision

The merged restore tools have70 locally tested cases but the existing DEV workflow
filters out cloud-tool-only changes and runs the separate700-test app suite. Make
cloud changes automatically verifiable without HF credentials or a laptop.
The user delegated scoped offline work and opted out of repeated design questions.

Approaches: append everything to the existing app job (unnecessarily couples app700
and modifies archived CI context); inline all commands in new YAML (harder to verify
local/CI agreement); use one small local verifier plus a thin separate workflow
(selected by agent). Keep the existing app workflow, calculator/API/locks unchanged.

## Contract

- `tools/cyberlateral_cloud/ci_verify.py --hf-python SDK --output NEW` runs the full
  cloud unittest suite, Ruff/Ty/Codespell and compiles cloud-owned Python only.
  Reuse existing safe command/output/JSON/Manifest helpers, no new numerical code.
- CPython3.12.13, existing app DEV lock/pins, separate huggingface-hub2.4.0 SDK.
  Reject SDK-in-app or shared environment. SDK is queried for version/type analysis,
  not account/auth/API use. Set HF_HUB_OFFLINE=1 for verifier children. No HF secret
  is provided to the workflow; live HF backup/restore integration remains separate.
- Successful unittest ledger must contain exactly one complete run, at least the
  preserved baseline70 tests, final OK, no failures/errors/skips. Do not hardcode
  the new total. Failed/truncated/small/duplicate ledgers cannot create SUMMARY.
- Emit SUMMARY.json plus closed sorted SHA256SUMS and command logs only after all
  commands pass. SUMMARY preserves closed GATES and records dynamic test/compile
  counts. Failures retain logs and FAILURE.json stage/code without success summary.
  Existing output/symlink/source-root destinations are rejected without overwriting.
- Existing project env and new SDK paths stay separate. Source bytes are rehashed
  after verification; only cloud-owned code is compiled, never a downloaded DRIVER,
  original Controller or F61. This is worktree verification, not origin attestation.
- New `.github/workflows/cyberlateral-cloud.yaml`: push main, PR main, manual dispatch;
  paths cover cloud tools, app component, both offline workflow files, root README.
  Read-only contents permission, no secrets, pinned existing action SHAs, no submodule/
  LFS/credential persistence, ubuntu24.04, pinned Python/uv, always upload bounded logs.
  Explicit setup-python interpreter and only-system/never-download uv selection.
- No vehicle/F61/actualr/dt/controller deployment, HF uploads, new secrets, policy
  values, paid HF jobs or configuration publication. Existing physical gates stay
  closed. Unit fixtures do synthetic model/reference work, NONZERO/unaggregated.

## Deliverable and verification

Two implementation tasks, RED→GREEN focused tests, full cloud suite and local verifier,
fresh whole-branch review. Publish a feature PR to verify the actual GitHub workflow
with zero HF credentials. Stop at the verified PR; this stage does not merge main or
refresh the stable6bd1 HF backup. Existing worktree/branches/evidence are preserved.
The workflow contract tests parse semantics and execute its real verification step
against controlled error cases, rather than merely grepping YAML text. The actual
GitHub job provides end-to-end bootstrap/permission/artifact evidence.
