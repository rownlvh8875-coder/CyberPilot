# R30 scoped offline development acceptance

User approved goal/code inventory, fresh-environment usage verification and Draft
integration preparation. This is documentation/evidence work, not a new runtime
feature. Standing delegation permits ordinary feature commits/push/Draft updates,
not main merge or installation. No further permission menus are needed.

## Goal and selected approach

Close the bounded R8–R29 offline development milestone with source-backed facts,
an executable Korean quickstart and an explicit distinction between developer
acceptance and actual CyberPilot product/vehicle readiness.

The root README currently declares an isolated offline synthetic module and then
retains upstream openpilot's README. Relevant component design/docs declare pure
calculation, exact wheel, standalone verification, fixed synthetic/native paths
and closed production gates. They are authority for this milestone, NOT a
complete custom CyberPilot product requirements baseline. Do not invent AI,
perception, autonomous-driving or physical safety requirements from the name.

Chosen approach: documentation-only acceptance over existing code. A runtime API
rewrite, a new test wrapper layer or enabling vehicle inputs would exceed the
approved task. Existing programmatic synthetic simulate API is distinct from
the fixed-catalog CLI and closed native profiles.

## Outputs

- `docs/OFFLINE_CAPABILITY_INVENTORY_R30.json`: baseline cc8d294a0312e1cc3316aafacb7a76ac1fe54024,
  exact source filenames/SHA/symbol citations, supported scopes, missing CLI
  conveniences, unestablished whole-product requirements, closed production gates.
- `docs/OFFLINE_ACCEPTANCE_R30_KO.md`: acceptance criteria and concrete fresh-use
  commands from repository root, pure/runtime report first; native explicitly
  opt-in and Linux x86_64 CPython3.12.13 only. No root uv sync or submodule/LFS setup.
- Component README: link current R28/R29 and acceptance guide, preserve historical
  stage descriptions and all upstream/root README content.
- `docs/OFFLINE_ACCEPTANCE_R30_RESULTS.md`: actual source/verification results and
  scope. External evidence retains full logs/receipts, exact-final-head CI and Draft
  state. Do not predict remote success in a pre-CI document.

## Acceptance criteria

A01 All existing Python/reference JSON/build/lock files byte-identical to baseline.
A02 Fresh relocated committed snapshot, fresh dev env, full pure440 tests/static
    and141 own compile checks pass. Exact public wheel stays46,646 bytes/27 entries/
    SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
A03 Documented separate runtime install/report commands work without dev/native
    dependencies; complete report bytes match the pure-gate report.
A04 Fresh optional native env runs unchanged R27/R28/R29. Portable observations/
    summaries match historical pins. No receipt/path normalization. One-location
    formal native model count R27=454,R28=0,R29=206,total660; pure/unit/CI/report
    calls are additional, not a whole-stage total or time claim.
A05 Native static/in-memory compile checks pass; every manifest and data check passes.
A06 Independent final reviewer finds no unresolved Important/Critical acceptance defect.
A07 Exact-final-head dedicated pure CI succeeds; actual artifact verified, Draft PR
    updated preserving old body; runtime/legacy CI remains unexecuted.
A08 Original10 source guards and original checkout/submodule clean observations
    preserved; no main merge/deployment/settings/credential changes.

Only this bounded offline milestone can be marked ACCEPTED. Whole-product goal
completion, physical behavior, generic message custody and merge authorization
remain NOT_ESTABLISHED/NOT_ALLOWED as applicable. A missing vehicle receipt is
not an offline-development blocker, and offline acceptance cannot waive it.

## Next implementation recommendation

Select a prospective developer convenience, not an invented product requirement:
explicit user-defined SYNTHETIC-only scenario file/CLI contract over the existing
pure programmatic API. The current CLI accepts only its fixed catalog. This is a
proposal for a later scoped design, not approval to implement it here or to admit
real logs/native messages. Whole-product requirements still need a real baseline.

## Constraints

No new package/adapter/model/controller/observer implementation, F61 execution,
actual input, Controller/Runtime/CAN, r/dt or performance evaluation. Actual r/T2/
vehicle scale null, R_BUDGET UNRESOLVED, Static Gate FAIL, actual activation and
F70UH/F70V/F71 NOT_ALLOWED. Public0.3.0/wheel/dependencies/workflow unchanged.
External evidence workspace and active feature worktree retained for user custody.
