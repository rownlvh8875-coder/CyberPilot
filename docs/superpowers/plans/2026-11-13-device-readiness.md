# Device Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline execution with one final fresh review.

**Goal:** Close deferred native gaps and deliver a portable read-only device observation handoff.
**Architecture:** Existing native tests/config first; standalone bounded observer and source-only ZIP; compose with existing locked native gate and CI.
**Tech Stack:** Python standard library, existing Python3.12 native SDK, real private msgq IPC.
**Spec:** docs/superpowers/specs/2026-11-13-device-readiness-design.md

## Global Constraints

- Baseline13d6929d95d2b600a234a29d9d68b59fa04b2d9a; use existing linked checkout/new branch.
- No runtime safety-source modifications, source submodule initialization, actual device or vehicle execution.
- No routine approvals; standing normal feature backup/main FF/push authority applies.
- Facts do not qualify a device/vehicle; no r/T2/scale defaults, F61 or control calls.
- External evidence output only; preserve prior workspaces/config/registered source bytes.

## Review Focus

- Incorrect filesystem/model observations must stay unavailable or fixture-labelled, never certified device identity.
- FIFO/symlink/oversized/unreadable public files must not block or expose unrelated bytes.
- Git environment/parent roots must not impersonate the requested source checkout.
- Restart case must use real native IPC and a genuinely new Store; mutation must be detected.
- Portable execution must not depend on repo/native imports; CI/accounting must execute the new cases and bundle smoke.

### Task 1 — Close deferred coverage

Files: native tests/test_native.py, test_worker.py and both web workflows.
- [ ] Add actual native source-restart/new-store characterization case, confirm expected values/missing state.
- [ ] Witness deliberate old-store reuse mutation failing; keep real production classes/IPC in normal run.
- [ ] Add process.py to basic push/PR filters and union direct basic inputs into native filters; focused changed-path selection probe before/after.
- [ ] Raise required actual-native coverage to9, run complete native suite and static checks, commit.

### Task 2 — Portable device observer

Files: tools/cyberpilot_web_native/{device_probe.py,device_probe_bundle.py,tests/test_device_probe.py}, docs/CYBERPILOT_DEVICE_PROBE_KO.md.
- [ ] Tests first RED missing observer: bounded fixed-file status, missing/no invented values, symlink/FIFO rejection, fixture scope, never-qualified output, exact-root Git and inherited selector isolation.
- [ ] Implement collect(root=Path('/'),source_root=None) and stdout-only CLI, no native imports/network/install.
- [ ] Add deterministic ZIP and extracted stdlib-only real-host CLI smoke, with source/SHA provenance.
- [ ] Run full project tests/static/compile and actual host probe, commit.

### Task 3 — Qualification and publication

- [ ] Existing full native gate discovers all new tests; run it, record device probe/ZIP verification separately (no protected verifier edits unless needed).
- [ ] One fresh whole-branch review using strongest model, fix Important findings RED/GREEN plus full gate; no repeated reviewer.
- [ ] Normal feature backup/main FF/push; exact-head basic/native CI and artifacts, source custody, sealed external package.
- [ ] Report actual result and physical-device limitations without claiming install completion.
