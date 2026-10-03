# Offline promotion and rollback-advice rehearsal

## Identity and purpose

- Cyber Validation STEP10, component implemented/reviewed; overall qualification incomplete.
- feature/cyber-autotune base1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Pure gate/fault machinery for documentary rehearsal; not evidence qualification,
  approval, actual active-profile ownership or rollback execution. Vehicle-agnostic
  structural bindings; tests name HYUNDAI_SANTA_FE_2022 without physical claims.

## Original references

- CyberPilot repository https://github.com/rownlvh8875-coder/CyberPilot, current branch
  above; reuses existing cyber_autotune contracts.is_sha256, audit.REASON_CODE and
  native_protocol canonical/digest. No Carrot/Zoom/Sunny/private logic copied.
- No model/native control call; no additional dependency or submodule change.
- Caller frozen bindings/receipt -> full-history validation -> immutable next state
  -> diagnostic assessment and digest. No production control consumer.

## Changes and expected effect

- promotion.py: exact-type records, ordered four-gate history, terminal receipt/fault
  handling, explicit rollback advice based on supplied observations.
- tests/test_promotion.py: ordered completion without authority, negative bindings,
  forged history, terminality, every fault at each stage and rollback advice matrix.
- Four stages: simulation screening, replay, final calibrated simulation, shadow.
  Preserves user screening flow and repository final replay->simulation->shadow order.
- Receipt ordinal is immutable tuple index. All stages share exact fingerprints,
  software/configuration/profile/evaluator/policy binding; artifacts cannot be reused.
- Scope must cover lateral AND longitudinal to rehearse full CyberPilot promotion.
- No tunable physical parameters, limits or timing constants added. No clock/reset.
- Fault enum includes regression/saturation/corruption/exception/confidence/invalid
  state/rollback unavailable. Baseline explicitly still active -> quarantine candidate;
  candidate explicitly active with matching declared rollback -> request rollback;
  unknown active/bad rollback -> operator required. Never rollback_executed.
- No upstream integration; native control/safety/override unchanged. Easy rollback:
  stop calling standalone module. No files/Params/profile pointer are modified.

## Regression risk and acceptance

- Hashes and named PASS receipts are assertions, not authenticated physical evidence.
  No current diagnostics are converted into PASS or used to promote real candidates.
- Initial baseline==rollback required, candidate!=baseline; full history checked at
  every public entry. Failure remains terminal; fault may be appended without hiding it.
- Full structural chain still NOT_READY and AWAITING_SEPARATE_VEHICLE_APPROVAL;
  actual runtime integration absent, so no LIMITED/ACTIVE execution capability.
- No holdout/H1/H2/frozen evidence/measurement/threshold/test relaxation.
- Final independent reviewer required; runtime_accepted/promotable fixed false.

## Validation method and actual results

- TDD missing-module RED ->8 tests77subtests PASS.
- Final168 AutoTune tests527subtests PASS;300 affected controls+AutoTune PASS9.52s,
  exit0; Ruff/diff check PASS. FullPC1282 collected, extended1200s run in progress.
- Review0Critical/1Important/0Minor. Important fixed in one TDD pass: prior gate
  status remains visible after fault (new regression RED3subfailures->GREEN).
  assess now includes ordered gate_results with status/artifact/reasons, not only digest.
- No real replay/simulation/shadow/vehicle test performed for this module.
- Persistent authenticated profile/audit storage, qualified receipts and runtime
  rollback remain separate missing gates. STEP10 PARTIAL; vehicle NOT_READY.
