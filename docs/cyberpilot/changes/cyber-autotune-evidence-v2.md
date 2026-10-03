# Cyber AutoTune evidence integrity / coverage v2

## Identity and purpose

- Area: offline AutoTune STEP 8.3 infrastructure implemented and reviewed;
  real-corpus/provenance qualification remains pending.
- Baseline: feature/cyber-autotune at 1ee1eb07f6cc48526f4d61265abe317fe67cc23b;
  uncommitted additions, no revision or vehicle qualification promotion.
- Scope: explicit reviewed manifest binding, bounded local artifact hashing and
  development fit/evaluation coverage. Synthetic tests only; no actual logs opened.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot, baseline above.
- Existing STEP 8 design sections7–8/12–13 and package preflight.CoveragePolicy
  are reused. This is independently written validation code, not fork control code.
- Call flow: trusted EvidencePolicy + EvidenceManifest -> whole-manifest preflight
  -> per-role coverage -> bounded descriptor hashing -> aggregate EvidenceReport.
- Source/submodule/dirty overlay/CP/firmware/model/schema/runtime/configuration,
  signal/time/plant/metric/mask/classifier/reset identities are mandatory digest
  bindings. This module does NOT verify their semantic contents or authenticate
  the reviewer. Expected manifest digest/allowlist must come from trusted review,
  never be manufactured from incoming data by a loader.
- No new dependencies, model or submodule versions; no code copied from Carrot,
  Sunny or ZoomPilot. Existing repository license applies.

## Changes and expected effect

- Added evidence.py: frozen manifest/policy/report and explicit POSIX read-only
  integrity validation. Added coverage.py: reviewed corpus-group counts.
- Added tests/test_evidence.py: synthetic files, split/coverage/privacy failures.
- No upstream integration point, runtime importer or controller callback added.
- Roles limited to development_fit/development_evaluation; validation, holdout,
  H1/H2 and unknown roles blocked before any artifact is opened.
- Exact canonical absolute allowlisted paths only; pre-resolve and no-follow
  descriptor traversal reject symlinks. Nonregular files/hardlinks are not read.
  Bounded length/hash checks and stable descriptor metadata detect mutations.
- Coverage minima are caller-reviewed distinct-group counts. No production
  minima or speed bins inferred. Repeated windows/runs within a group count once.
- Route overlap OR same-vehicle/day overlap across fit/evaluation blocks loading;
  coverage is union across windows per role, not every condition in each window.
- Within a role too, identical file path OR content hash cannot be rebound to a
  different vehicle/route/day group to inflate coverage. Same-group repeats count once.
- Missing/malformed contracts or filesystem failures => BLOCKED. Unsupported
  platforms block. No raw bytes/paths in returned report. No persistent state.
- No panda/opendbc/actuator/override/longitudinal/model/metric-v1 changes.
- Sync risk limited to isolated offline package; no delay or control behavior.

## Regression risk and acceptance

- A forged trusted policy defeats any digest-based approval; policy is the trust
  boundary, not a capability acquired by supplying a matching digest.
- Labels, independence, firmware truth, mask derivation and plant domain still
  require producer-specific review/integration. Hash matches prove bytes only.
- A hostile privileged filesystem/mount namespace is outside this loader contract.
- Previously seen data remains development-only; never reclassified as validation.
- Synthetic coverage minimum1 is a test fixture, not scientific sufficiency.
- All offline_evaluable/candidate_generation_allowed/runtime_accepted flags remain
  false even on INTEGRITY_AND_COVERAGE_PASS. Existing admission stays unchanged.
- Rollback: stop importing these offline tools; no runtime configuration changed.
- Independent review required before handoff; no commit, merge or vehicle approval.

## Validation method and actual results

| Check | Actual result and limit |
| --- | --- |
| Initial RED | unittest import fails for missing new coverage module, exit1 |
| AutoTune unit tests | python -m unittest discover -s openpilot/tools/cyber_autotune/tests: 56 passed, exit0 (24 new,32 existing) |
| Ruff/diff-check | PASS, exit0 |
| Controls + AutoTune | python tools/test_runner.py openpilot/selfdrive/controls/tests openpilot/tools/cyber_autotune/tests -j 2: 188 passed in18.56s, exit0 |
| Independent review | One Important duplicate-artifact/group-label inflation defect; repeated path and copied-byte cases RED (2 failures,exit1), fixed and GREEN |
| Default PC runner | Not rerun here; prior8.2 bounded run timed out on public fixture fetching |
| Real evidence/replay/simulation/shadow | NOT RUN; no physical qualification |

## Handoff

Verified effect: synthetic privacy/integrity/split/coverage contract checks only.
Remaining: independent producer provenance verification, reviewed real manifest,
coverage thresholds, identity/plant/primary truth gaps, reviewed search bounds,
native adapters and v2 A/A. STEP8 overall PARTIAL; search still blocked.
No commit/PR. No device/network/raw personal input access in this implementation.
Tests ran in Ubuntu24.04/Python3.12.13 with child PATH including existing .venv/bin.
Review exclusions: semantic authenticity/statistical independence and actual corpus
qualification remain deferred; no privileged mount-adversary guarantee or broad PC
suite claim. These exclusions do not authorize real-data evaluation or deployment.
