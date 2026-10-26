# CyberPilot repository instructions

These instructions apply to the entire CyberPilot repository. Read any deeper
`AGENTS.md` in the directories you edit, including initialized submodules.
Follow the user's authorized task scope. Report conflicts between instructions;
do not resolve a conflict by weakening a safety requirement.

## Purpose and upstream contract

CyberPilot builds on comma.ai openpilot with selectively adapted longitudinal
and lateral improvements, vehicle-specific parameter optimization, and replay
and closed-loop validation. These are development objectives, not claims that
the features already exist or that the project is approved for road use.

- Preserve upstream layout, Git history, submodule gitlinks, LFS pointers,
  licenses, attribution, build tooling, and established interfaces.
- Read [upstream contributing rules](docs/CONTRIBUTING.md),
  [safety requirements](docs/SAFETY.md), [development setup](tools/README.md),
  and the relevant subsystem documentation before changing behavior.
- Preserve upstream's priority order: safety, stability, quality, then features.
  Upstream PR instructions referring to `master` apply to contributions to
  comma.ai; CyberPilot uses the branch workflow below.
- Do not wholesale merge sunnypilot or carrotpilot. Analyze one feature at a
  time, tracing actual callers, inputs, state, outputs, and actuator consumers.
  README labels and file diffs alone do not establish behavior.
- Record the source repository, actual branch, exact commit SHA, file paths,
  dependency/submodule SHAs where relevant, and license before adapting code.
- Keep necessary upstream edits small and focused. Prefer independent
  CyberPilot modules with explicit interfaces and tests; choose their location
  from the current package structure when implementing an approved feature.
  Do not add empty modules or speculative runtime hooks just to reserve names.
- Keep stock cereal field meanings and identifiers compatible. Follow
  [cereal's custom-fork guidance](openpilot/cereal/README.md) for extensions;
  preserve old-log readability and document any reserved-field allocation.

## Safety boundaries

- Do not bypass, remove, or weaken panda/opendbc safety enforcement, openpilot
  actuator limits, excessive-actuation checks, driver monitoring, engagement
  checks, brake/cancel takeover, or fault handling.
- AutoTune must never change safety limits, safety model selection, safety
  flags, CAN permissions, or the safety enforcement code. Its candidate control
  parameters must stay within separately reviewed bounds inside existing limits.
- Keep vehicle-specific parameters separate from global control algorithms.
  Reject invalid, non-finite, stale, or incompatible parameter candidates and
  retain the last validated configuration or documented upstream fallback.
- PC development does not authorize device flashing, live CAN/actuation,
  vehicle writes, road testing, or automatic deployment. Obtain explicit user
  authority for those operations and their exact targets.

## Development areas

These are ownership boundaries, not pre-existing CyberPilot implementations.

| Area | Responsibility | Current upstream reference locations |
| --- | --- | --- |
| Cyber Long | Lead handling, stop/start, cruise, acceleration/jerk targets, longitudinal delay and compensation within existing limits; Carrot concepts are evaluated feature by feature. | `openpilot/selfdrive/controls/plannerd.py`, `controls/lib/longitudinal_planner.py`, `controls/lib/longcontrol.py`, `openpilot/selfdrive/car/cruise.py` |
| Cyber Lateral | Path/curvature interpretation, torque/PID/angle/curvature control, delay, friction and curve smoothness; evaluate openpilot/Sunny/Carrot approaches individually. | `openpilot/selfdrive/controls/controlsd.py`, `controls/lib/latcontrol_*.py`, `openpilot/selfdrive/modeld/` |
| Cyber AutoTune | Vehicle-specific estimation, candidate bounds, confidence, persistence, rollback and offline evaluation; no safety-limit tuning. | `openpilot/selfdrive/locationd/paramsd.py`, `torqued.py`, `lagd.py`, vehicle interfaces in `opendbc_repo` |
| Cyber Validation | Baseline comparison, process replay, closed-loop scenarios, regression coverage and shadow evidence. | `openpilot/selfdrive/test/process_replay/`, `openpilot/selfdrive/test/longitudinal_maneuvers/`, `openpilot/tools/sim/`, `tools/test_runner.py` |
| Cyber UI | Explain settings, validation status, tuning provenance and rollback; preserve driver-monitoring and critical alerts. | `openpilot/selfdrive/ui/`, `openpilot/system/ui/` |

Paths abbreviated within a table cell are relative to the preceding directory.
Vehicle CAN translation is reached through `openpilot/selfdrive/car/card.py`
and opendbc interfaces. Inspect the pinned submodule code before claiming how
gas/brake, steering conversion, or safety enforcement works.

## Before each change

1. Inspect `git status --short --branch`, current HEAD, remotes, relevant diffs,
   and `git submodule status`. Preserve unrelated user changes.
2. Identify the smallest affected call path and tests. Read the applicable
   upstream instructions and initialized submodule instructions.
3. For every feature or behavior change, complete a record using
   [the feature-change template](docs/cyberpilot/FEATURE_CHANGE_TEMPLATE.md).
   Store completed records under `docs/cyberpilot/changes/` with a descriptive
   filename. Documentation-only edits describe purpose, scope and checks in
   the handoff or commit message without a separate feature record.
4. Define baseline, regression risks, acceptance criteria and validation inputs
   before implementation. Record gaps rather than inventing evidence.

## Code and configuration

- Follow `.editorconfig` and `pyproject.toml`: LF line endings, UTF-8, two-space
  Python indentation and the repository's configured lint rules.
- Do not introduce magic numbers. Use named constants/configuration with units,
  rationale/source, validity range and vehicle applicability. Explain any
  algorithmic literal whose meaning is not self-evident.
- Document state ownership, reset conditions, timestamps, units, failure paths
  and vehicle applicability at new control interfaces.
- Keep dependencies minimal. Do not rewrite schemas, package layout, build
  systems, submodule URLs/SHAs or LFS storage as an incidental feature change.
- The inherited `.lfsconfig` names comma.ai's Hugging Face storage for both read
  and write. Do not upload CyberPilot objects there. Inspect LFS requirements
  before pushing: the Step 1 Git-only push used `GIT_LFS_SKIP_PUSH=1` because
  it added no new LFS objects. New LFS content requires a reviewed storage plan;
  skipping upload must never be presented as complete asset publication.
- Keep private driving logs, CAN/GPS/video, credentials, local environment files
  and generated artifacts out of commits. Share only authorized evidence.

## Verification and promotion

- Use the supported environment in `tools/README.md` (Ubuntu 24.04; Windows
  development through WSL where needed). Check pinned submodules, LFS assets,
  Python constraints and build dependencies before runtime tests.
- For code changes, run affected tests and relevant regression/build checks.
  The current runner is `python tools/test_runner.py [targets]` in the prepared
  environment. Examples: `openpilot/selfdrive/controls/tests` and
  `openpilot/selfdrive/locationd/test`. `scons -u` builds native components.
- The runner's default discovery excludes process replay and simulator tests.
  Run those explicitly when required; unit-test success does not cover them.
  Follow [process replay instructions](openpilot/selfdrive/test/process_replay/README.md)
  and [simulation instructions](openpilot/tools/sim/README.md), verifying the
  available dependencies and command arguments against the current checkout.
- Before real-vehicle application, require ordered evidence:
  **replay → simulation (closed loop) → shadow validation**. Shadow candidates
  must not command actuators; document isolation, active controller, candidate
  identity and comparison data. Road-use approval remains a separate decision.
- Do not ignore failed tests, remove tests, expand ignores, or relax thresholds
  to obtain a PASS. Do not update replay references automatically. An intended
  behavior change requires reviewed output differences and recorded authority
  before updating its baseline.
- Bind results to code/submodule/model/configuration SHAs, input identity,
  environment, commands, exit codes, counts and output artifacts. Report passed,
  failed, blocked and not-run checks separately. Synthetic/CI evidence alone
  does not prove empirical improvement, vehicle safety or release readiness.
- For documentation-only edits, check diff whitespace, links, paths, scope and
  consistency; do not claim that runtime suites ran from document checks.

## Branches and completion

- `main`: intended destination for reviewed stable releases. Its initial
  openpilot-master baseline is not itself a validated CyberPilot road release.
- `develop`: integration branch; feature branches target it.
- `feature/cyber-long`, `feature/cyber-lateral`, `feature/cyber-autotune`,
  `feature/cyber-ui`, `feature/cyber-sim`: work in the corresponding domain.
  Choose the correct base deliberately; do not assume an existing branch is
  current or clean. Avoid unnecessary permanent integration branches.
- Fetch `openpilot` and verify its actual branch/SHA before syncing. Integrate
  upstream changes into `develop`, review differences and run required checks
  before promoting to `main`. Do not force-push shared branch history.
- Keep each change focused. A request for a commit-ready result means leave
  reviewable local files; commit/push when the user requests that action.
- Finish with purpose, references, changed files, verification and limitations,
  remaining risks, and the next needed check. Never label unrun work complete.
