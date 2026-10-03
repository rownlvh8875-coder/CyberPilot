# Cyber AutoTune classification and proposal profiles

## Identity and purpose

- Area: AutoTune STEP8 offline structural contracts; implemented and reviewed.
- Branch/base: feature/cyber-autotune at 1ee1eb07f6cc48526f4d61265abe317fe67cc23b.
  These additions are uncommitted; no vehicle qualification or candidate promotion.
- Scenario: reject forbidden parameters or malformed/unbounded proposals before
  building a deterministic review-only single-parameter identity.
- No real corpus read, new learner, controller adapter, live loader or apply path.
  No vehicle-specific calibrated bounds supplied. All test values synthetic.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot at base above, unchanged upstream
  c8fb906815530460ed156f14e09e1f312bb0f851 and opendbc
  4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
- Registry references existing torqued/lagd/paramsd, controlsd, torque controller,
  Cyber Long read-only PARAMETER_METADATA and Hyundai CarControllerParams.
  Source symbols indicate ownership, not empirical calibration or live values.
- New independent validation code; no copied Carrot/Sunny/Zoom logic, no new
  dependencies or license obligations beyond repository license.
- Offline call path: ProposalInput -> authoritative policy -> shape/identity/
  physical-domain/range/delta/sample/confidence/interval/rate guards -> digest.
  No runtime consumers; old admission code still denies all proposals.

## Changes and expected effect

- policy.py: immutable six-class registry, unknown names fail closed. Only factor
  and friction support initial offline representation, not evaluation permission.
- profiles.py: frozen proposal/history/review data and pure structural assessment;
  evidence validation pending even when contracts_ready=true. Authority outputs
  default false and excluded from constructor/replace arguments.
- tests/test_policy.py and test_profiles.py: immutable registry and numerical,
  provenance, history, physical-domain and repeatability boundary coverage.
- Canonical units: factor (m/s^2)/normalized_command, friction normalized_command.
  No implicit Nm conversion. Bounds/delta/rate/minima have no production defaults.
- Rate unit is parameter-unit per elapsed second. Input elapsed time is offline
  metadata, not a wall-clock timer. Shortest decimal rational arithmetic avoids
  floating-point epsilon exceptions at hard bounds. 2 and 2.0 share identity.
- Profile schema cyber-autotune-proposal-v1 includes all supplied values/reviews
  and source/config/evidence/metric/adapter/history bindings; SHA256 is content
  identity, not authenticated approval. No persistence or mutable state/reset.
- No edits to model, planning, controls, safety, CAN, override, limits, metrics or
  evidence modules. No additional delay. Sync risk confined to offline package.

## Regression risk and acceptance

- Caller review digests/confidence/sample counts are unverified assertions. A
  digest cannot authenticate bounds or prove temporal/statistical independence.
- Initial history requires previous==rollback==baseline. This is not a rollback
  store, history authentication, versioned runtime profile or update authority.
- Exact types required; NaN/Inf/bool/huge unrepresentable numerics blocked. Factor
  reviewed minimum must be positive, friction minimum nonnegative. Malformed
  candidates return blocked with no profile hash. Unreviewed boundaries block.
- Local structural success must keep offline_evaluable/runtime_accepted false.
- No holdout access, no new real candidate search, no threshold/reference changes.
- Rollback for this change is to stop using standalone offline tools; active
  controller unchanged. Independent code review required; no deployment authority.

## Validation method and actual results

| Check | Method / identity | Result and limit |
| --- | --- | --- |
| Baseline | Ubuntu24.04/Python3.12.13 existing venv, unittest discover | 56 passed, exit0 before additions |
| TDD | policy then profiles unittest modules | each RED missing module exit1 -> GREEN7 and16 respectively |
| AutoTune suite | .venv/bin/python -m unittest discover -s openpilot/tools/cyber_autotune/tests | 82 passed, exit0 after review fixes |
| Ruff / whitespace | .venv/bin/ruff check openpilot/tools/cyber_autotune; git diff --check | PASS, exit0; StrEnum used for UP042 |
| Controls + AutoTune | prepared tools/test_runner.py -j2 | 214 passed in12.03s, exit0 after fixes |
| Default PC | 300s bounded prepared tools/test_runner.py | 1193 collected, timeout exit124; no final counts, not full PASS |
| Review | one independent final review | 2Important fixed with3RED regression tests -> GREEN; no Critical/Minor |
| Real replay / calibrated simulation / shadow | not invoked | NOT RUN; scientific prerequisites still missing |

## Handoff

Verified to date: synthetic contract/guard behavior, not physical identification,
comfort improvement or statistical confidence. Finite-grid search, native
evaluation, audit persistence and full versioned profiles remain separate tasks.
STEP8 overall PARTIAL. Vehicle use NOT_READY. No commits, PR, device or CAN access.
Review fixes unify range/interval/confidence comparisons with decimal semantics and
require positive minimum confidence as existing preflight does. The full-suite
timeout did not produce named test assertion failures or final counts; do not infer
the earlier fixture-download cause for this run from an interrupted worker trace.
Protected7prior AutoTune source/test hashes unchanged. Existing2trackedSTEP7docs and
empty index preserved. Reviewer exclusions: no authenticity/real-data/firmware,
live history rollback or persistence qualification; no serialized-input parser,
route collection or defense against arbitrary Python execution in this local API.

## 2026-10-02 wheelbase provenance correction

Read-only source audit found the STATIC wheelbase metadata referenced the removed
controls/lib/vehicle_model.py. Actual controlsd imports opendbc.car.vehicle_model;
VehicleModel consumes CP.wheelbase. Correct only the registry source_symbol to
opendbc_repo/opendbc/car/vehicle_model.py:VehicleModel. Classification, unit, owner,
proposal permissions, physical value and all controller/safety code remain unchanged.

Regression test resolves the referenced file/module/symbol and verifies consumer
identity, STATIC classification and denied proposal permission. It failed on the
missing file before the one-line fix, then passed. Policy8tests34subtests0.16s;
package234tests748subtests29.96s;controls+AutoTune366tests14.81s,exit0. Ruff PASS.
Whole-PC remains unqualified pending prior locationd setup-error diagnosis. No
new physical evidence, data access, runtime authority, commit or deployment.
