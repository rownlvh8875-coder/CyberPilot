# F70UGZ-R8 — CyberPilot repository integration and isolated offline CI

User approved the explicitly proposed development-branch integration, one-command
verification, CI, commit/push/PR. This lifts repository-writes0 ONLY for scoped
development changes. No main merge, vehicle/runtime/Controller/CAN/F61/schema run,
actual data/r/dt/candidate evaluation, settings or credentials changes. Old evidence
folders immutable. Existing main checkout remains byte/status/HEAD unchanged.

Base origin/main c8fb906815530460ed156f14e09e1f312bb0f851, confirmed remote/main
equals local; fork target rownlvh8875-coder/CyberPilot, not commaai. Main GH default
branch confirmed main (upstream CONTRIBUTING's master applies upstream, not fork).
Isolated external Git worktree, feature/cyberlateral-dev-offline-ci, no submodule
init/LFS downloads. No native worktree tool exists; git fallback authorized.

## Choices and imports

Chosen standalone project tools/cyberlateral_dev: src/, project/ (127 old tests and
references), licenses/, reference/ (only3 hash-pinned source/schema data fixtures),
build_backend.py, pyproject.toml, tools/build_wheel.py. Keep package0.3.0/code bytes
exact from sealed R7 ZIP SHA
c2f9c240aba8d181a4a341cf5e7edce3d74210759ee2b43ed2ed7bdfadbec83a.
Expected wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Root project dependencies/uv.lock/runtime/SCons untouched. No historical ZIP or
results/venv/cache/private logs imported. Source fixtures are data; only2 exact
inherited helper bodies execute in DEV test comparison. Package runtime deps[].

IMPORTED_ARTIFACT.json records sealed-parent identity and every unchanged imported
file hash, including src/project/licenses/reference/build backend/build tool.
Store original R7 pyproject as reference/r7_pyproject.toml; live pyproject retains
same [project]/build metadata, adds isolated dev dependency pins/config only.
No generic sys.path mutation in shipped library. README root gets concise link;
new component README supplies setup/verify/report/gates and provenance boundaries.

Alternative root-project dependency integration would pull vehicle/native packages;
reject it. Merely storing wheel/ZIP would not provide editable/testable code; reject.
Large imported subsystem is justified against upstream's500-line preference by
sealed identical bytes +127 regression tests +isolated path, not a new controller.

## Environment and single command

Component dev group pinned numpy2.5.3, ruff0.16.7, ty0.0.80, codespell2.4.3,
PyYAML6.0.3. Component uv.lock generated/used with uv0.12.23, CPython3.12.13.
No root uv sync. Bootstrap may download pinned dependencies; verification uses
local sources/wheel only and installed-wheel uv --offline --no-deps.

From repo root:
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/dev.py verify --output NEW_DIR

dev.py has main(argv=None), parser verify --output required, refuses existing
file/dir/dangling symlink BEFORE prerequisite/numerical work. Validates pinned
runtime/deps and imported hashes before reference compilation. New output dir only;
no deletions/overwrite. Ordinary guard, not race-free/atomic guarantee.
Uses integration_tools/verify.py for orchestration/helpers:
verify_imports(root)->dict; verify_new_output(path)->None; build_wheels(root,out)->dict;
verify_project(root,out)->summary. Runtime/library behavior unchanged.

Run all project/ tests (old127 plus new integration tests), Ruff/Ty/Codespell on
OWN code excluding original reference fixtures; compile own Python in memory, not
original Controller/schema. Log commands/results. Build wheel twice and verify
RECORD/no deps/expected sealed wheel identity. Install local wheel into temporary
empty venv using uv offline/no-deps, invoke -I -B installed --report twice from
unrelated cwd, exact5-file/Manifest comparison and source/report gates. Run existing
fixed numeric reference CLI twice with exact3 fixtures, compare all7 result bytes.
Persist SUMMARY.json, SHA256SUMS.txt, logs, wheels and reports, no venv/pycache.
Summary labels per-process helper counts, calculator/runtime/r/dt0 separately,
R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
No browser visual PASS; inherited NOT_ESTABLISHED remains explicit.

TDD tests guard/no-work, imported-hash tamper detection (test-only temp copies),
actual wheel/RECORD/report determinism helpers. Avoid recursive full-verifier test
inside suite; full dev.py invocation is the independent end-to-end completion gate.

## Workflow and PR safety

New .github/workflows/cyberlateral-dev.yaml, Ubuntu24.04, permissions contents:read,
no secrets/hardware/self-hosted/Docker/root tools/op.sh/SCons/runtime actions.
Pin official checkout/setup-python/setup-uv/upload-artifact action SHAs resolved
from current tags; checkout submodules:false,lfs:false,persist-credentials:false.
Python3.12.13/uv0.12.23; run single component command, upload only controlled output.
Triggers scoped push(main,feature/cyberlateral-dev-offline-ci), PR(main) path filter
component/new workflow/root README, and manual workflow_dispatch. Lockfile/dev
dependencies only; no modification to legacy workflow behavior or repository policy.

Existing tests.yaml runs original openpilot build/replay on PRs; must not trigger
that scope. First push tested implementation commit BEFORE creating PR; existing
push workflows target master, so only new isolated workflow runs on this branch.
After dedicated CI proof, create a tree-identical empty [skip ci] guard commit,
push, then create DRAFT PR against main. Exact git tree equality proves tested code
unchanged; report tested SHA vs PR-head SHA separately. Try explicit dispatch of
new safe workflow on guarded head (workflow_dispatch isn't skip-ci suppressed);
if GitHub registration/default-branch rules prevent dispatch, report actual status,
retain green tested-tree CI proof and do not claim head-check success. No automatic
merge, no disabling legacy workflows/actions settings, no token/login escalation.
Harmless existing PR-target metadata automation may still run, not vehicle code.

## Validation/handoff

Baseline127 tests before edits, new tests RED->GREEN, isolated local full verify,
one fresh whole-change review, one Important/Critical TDD fix pass if needed,
green final suite, scoped commits. Push normal named branch, monitor ONLY dedicated
CI with bounded waits, fix in-scope issues before PR (no existing PR yet), then PR
guard/dispatch as above. Attach created PR through codex_app tool. Preserve worktree
for user. Final report includes PR/commits/CI URLs and any blockers/deferred minors,
main/runtime preservation and remaining real-world gates. No new evidence ZIP churn
required; Git+CI artifacts now provide versioned development handoff.
