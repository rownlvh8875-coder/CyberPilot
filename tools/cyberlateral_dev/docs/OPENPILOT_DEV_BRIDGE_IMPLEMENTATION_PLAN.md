# R12 Synthetic Development Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans (inline TDD and one fresh final review). This is a FUTURE plan, NOT executed as part of R11. Routine design questions were delegated; original execution/vehicle restrictions remain binding.

**Goal:** Implement only the R11 typed, fixed-fixture DEV bridge over unchanged CyberLateral0.3.0.
**Architecture:** Immutable source-shaped snapshot/session/result records; closed-registry factory and pure validating advance; separate installed-wheel synthetic probe in the existing verifier. No real-object reader or runtime hook.
**Tech Stack:** Existing pinned CPython3.12.13/uv0.12.23/dev lock and stdlib. No runtime/dependency additions.
**Spec:** OPENPILOT_DEV_BRIDGE_DESIGN.md and OPENPILOT_DEV_BRIDGE_SOURCE_MAP.json in this directory.

## Global Constraints

- No original Controller/Runtime/CAN/F61/schema import/execution or executable compile, no actual/raw inputs, r/dt/candidate evaluation or main merge.
- Preserve all77 imported bytes, src API/version0.3.0, wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c and existing156 tests.
- Actual r/T2/vehicle scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL; activation/F70UH/F70V/F71 NOT_ALLOWED.
- DEV bridge code is excluded from the wheel. No direct CC/CS/CI/CP object acceptance, dynamic profiles, file/log loaders, callbacks, timestamp/r parameters, clamp/coercion/default recovery.
- Contract/profile/source-set IDs, record fields, signatures, rejection ordering and fixed catalog SHA are exact in the spec; do not redesign them silently.
- Final evidence must distinguish new coverage/integration from independent arithmetic certification, physical or production equivalence. Use scoped skip-ci commits and dedicated explicit offline CI; preserve audit/worktree.

## Review Focus

- Unknown/subclass/side-effecting field objects must reject before their methods or new transition run (Tasks1/2).
- A same-index but wrong requested/applied/counter state must reject against the trusted prefix; never self-heal (Task2).
- Signed zero and schema-Float32-like alternative values must not bypass exact registered binary64 identity (Task2).
- history-scale starts at model index1 and may emit19.0; offset0 does not mean canonical index0 and no hidden clamp is permitted (Tasks1/2).
- Original immutable retry is deterministic, advanced-session duplicate rejects, and interleaved sessions cannot share hidden state (Task2).

## Task1 — immutable records and closed factory

Files create: integration_tools/dev_bridge_types.py, integration_tools/dev_bridge.py, project/test_dev_bridge.py.
Consumes: public Limits/LateralState/LateralOutput, fixed_catalog, pinned spec/source-map.
Produces: DevSourceSnapshotV1, DevBridgeSessionV1, DevBridgeResultV1, DevBridgeError(code), fixture_snapshot(fixture_id,offset,sequence_id), begin_sequence(fixture_id,sequence_id), with exact spec fields/signatures and no defaults.

- [ ] Write RED tests for exact frozen/slots records, factory fields from ramp, canonical vs registered history-scale initial states, ASCII sequence ID1..64, bool/negative/end offset rejection, unknown fixture/source profile and closed schema.
- [ ] Run new file via existing unittest discovery; expected FAIL missing DEV bridge symbols (not import typo). Read failures before implementation.
- [ ] Implement immutable types, exact metadata type checks and factories only. Registry source/profile labels are constants matching the source-map; fingerprint/version prerequisite uses the fixed trusted registry and0.3.0, not a runtime source scan. No original imports/global mutable sessions.
- [ ] Literal controls: ramp first snapshot request1.0/driver0.0/angle0.0/activeTrue/Limits(16,2,5,7,1,3), model index0; history-scale begin state(1,100,100,0). Existing modules perform no new transitions in factory construction.
- [ ] Full component suite PASS and unchanged imported/wheel identity; commit scoped DEV records/factory/tests with skip-ci.

## Task2 — exact pure advance and rejection contracts

Files modify: integration_tools/dev_bridge.py, project/test_dev_bridge.py.
Consumes Task1 records/registry; produces advance(snapshot,session)->DevBridgeResultV1 with explicit next_session, stable DevBridgeError.code and no partial result.

- [ ] RED tests for all ten rejection stages in the exact specified order. Include an arbitrary native-like object with raising properties (reject before property access), string/int subclasses, missing/wrong Limits/state, production scope, old ajouatom-like source label, unknown fixture, mismatched sequence/offset/model index, terminal or advanced-session duplicate, NaN/inf/non-dyadic values, allowance250, wrong integer bookkeeping/state.
- [ ] RED exact field/bit tests: signed-zero fixture negative-zero request changed to positive-zero rejects SNAPSHOT_MISMATCH;0.3 replaced by its distinct Float32-style numeric value rejects without hidden rounding; no changes to package validation.
- [ ] RED state tests: compare all previous fields against trusted prefix state; wrong applied integer, wrong previous-requested integer or counter rejects STATE_MISMATCH without correction. Unknown numeric scale does not fall back to409/CP/defaults. Unknown kwargs/r/time are absent from constructors, not accepted calculator policy.
- [ ] Implement validation steps1..8 before model work, trusted prefix simulation for offset>0 only, complete state comparison, then one NEW current step. Count prefix/current calls separately if reporting execution; prefix work is not independent oracle evidence.
- [ ] Literal result controls: ramp first command2/normalized0.125/steer_requestTrue/next state(1,16,2,0); history-scale command95/normalized19.0/next state(2,0,95,0), no clamp. Integer prior request is not normalized F61 previous native.
- [ ] Run all7 registered sequences; every diagnostic output/final state matches existing frozen golden results. Normalized expression and Float32 projections remain separate diagnostic values, not wire serialization.
- [ ] Original pair retry returns exactly the same result and leaves inputs untouched. Interleave distinct sequence IDs and fixtures; cross-session values reject at the specified stage. Frozen records do not implement persistence, ownership or anti-replay.
- [ ] Full unit/static/compile checks and wheel identity PASS; commit pure DEV transition/tests with skip-ci.

## Task3 — isolated synthetic probe, verifier and publication

Files create: integration_tools/dev_bridge_probe.py, project/test_dev_bridge_probe.py.
Files modify: integration_tools/verify.py and README/docs only; no runtime package/workflow/dependency edits.
Consumes Task2 API; produces closed fixed-fixture probe artifacts and verifier acceptance hashes/counts.

- [ ] RED tests: installed wheel in empty venv runs DEV probe under -I -B from unrelated cwd without NumPy/original modules/source selectors; two output directories byte match. Existing output/file/dangling link and unknown data/log modes reject before work. Missing/identically malformed artifacts or altered safety gates reject.
- [ ] Implement run_bridge_probe()->dict in the DEV probe, iterating all7 fixed fixtures via begin_sequence/fixture_snapshot/advance. Use explicit deterministic sequence labels, record fixture/source identities, complete diagnostic outputs/final session state and unchanged safety gates. No caller-supplied data/policy/time arguments.
- [ ] CLI accepts only --output NEW, stages complete files and publishes final RESULTS last after checksum success, consistent with existing harness. Probe does IO; core advance remains pure.
- [ ] Extend existing installed-wheel verification to run probe twice, validate full per-scenario output hashes against trusted existing golden records (not just PASS/counts), Manifest and all gates; record the actual new test count. All156 inherited tests remain discoverable.
- [ ] Verify before commit: full component suite, Ruff/Ty with explicit config/Codespell/own compile, exact wheel, report/numeric/harness/probe pairs, relocated checkout and no source/runtime activation changes. Top-level new verifier status may be F70UGZ_R12_SYNTHETIC_DEV_BRIDGE_REFERENCE_PASS; existing inner R9 harness/F61 contracts do not change.
- [ ] One fresh final whole-change review; fix only Critical/Important with RED->GREEN in one pass, ledger any Minor/declined scopes. Scoped skip-ci push, explicit dedicated final-HEAD CI, downloaded artifact checks, existing Draft PR update. No automatic merge or vehicle deployment.

## Plan self-review

Record/factory -> advance -> installed probe interfaces match the design. Domain,
registry fingerprint, state/offset distinction, ordering, failure-before-current
transition, float bits, full artifacts and unchanged operational gates each have
named tests above. Remaining choices are local helper factoring and test naming,
not new policy values or broader input modes. Do not execute this plan in R11.
