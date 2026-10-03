# CyberPilot feature change record

Copy this template to `docs/cyberpilot/changes/<descriptive-name>.md` for each
feature or behavior change. Fill every section; use `not applicable` with a
reason where appropriate. Keep planned checks distinct from executed results.

## Identity and purpose

- Feature / area (Cyber Long, Lateral, AutoTune, Validation or UI):
- Status (proposed, implemented, validation pending, reviewed):
- Purpose and concrete scenario:
- Scope, exclusions and vehicle applicability:
- CyberPilot branch / baseline SHA / candidate SHA or uncommitted patch identity:

## Original references

- Source repository URL / verified branch / exact commit SHA:
- Source files, symbols and license / attribution requirements:
- Traced callers → input data / state → algorithm → outputs / consumers:
- Relevant submodule SHAs, model identity and external dependencies:
- Adoption decision (reuse, adapt/reimplement, reject) and rationale:

## Changes and expected effect

- Modified / added files and their responsibilities:
- Minimal upstream integration points and alternatives considered:
- Expected observable effect and evidence supporting the hypothesis:
- Constants / parameters: name, unit, source, range, vehicle applicability:
- State initialization, reset, delay assumptions and failure/fallback behavior:
- Safety boundaries affected or confirmed unaffected, with code references:
- Upstream synchronization conflicts and maintenance cost:

## Regression risk and acceptance

- Potential regressions, including vehicle variants and invalid/stale inputs:
- Baseline comparison and predeclared acceptance thresholds:
- Holdout / scenario coverage and input provenance:
- Rollback method and last validated configuration:
- Required reviewer / promotion authority and decision:

## Validation method and actual results

For each row, record planned method, actual command/environment, input and output
identity, exit code/counts, status and remaining limitations. Required stages
must be completed in order before vehicle application.

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | | | |
| Replay vs baseline | | | |
| Simulation / closed loop | | | |
| Shadow (candidate cannot actuate) | | | |

## Handoff

- Verified effect vs expected effect:
- Failed, blocked or not-run checks and missing inputs:
- Remaining regression risks and next verification:
- Commit / PR references when available:
- Vehicle application decision (not authorized unless explicitly approved):
