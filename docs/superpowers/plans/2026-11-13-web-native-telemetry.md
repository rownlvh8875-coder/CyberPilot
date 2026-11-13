# Native Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reproducibly qualify the read-only monitor against actual host-native Cereal/IPC with synthetic inputs.
**Architecture:** Isolated exact dependency checkout/minimal build; guarded private IPC namespaces; actual production collector and CLI process; native tests and browser integration; dedicated CI.
**Tech Stack:** Python 3.12.13, pycapnp 2.1.0, pinned Cython/SCons, g++, Playwright.
**Spec:** docs/superpowers/specs/2026-11-13-web-native-telemetry-design.md

## Global Constraints

- Baseline 93563c0fdd6f7ca6ce5058c5a3bdcd197d403048; reuse host-owned linked checkout, preserve prior evidence.
- Linux x86_64 host-native qualification only; no physical-device/vehicle/full native build claims.
- No Controller/vehicle Runtime/CAN/F61/actual r/dt/actual vehicle inputs. Synthetic status publishers only.
- External new build/output directories; root native submodules and root dependencies unchanged.
- Production monitor stays read-only; test-only publishing outside runtime package.
- R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/vehicle scale null.
- No routine approval pauses; existing user authorization covers normal feature backup/main FF publication.

## Review Focus

- Namespace escape/symlink/ownership changes: reject before native socket/publisher creation and before cleanup.
- Cold IPC readiness and independent topic outages: bounded retries, never phantom default values or false PASS.
- Source/build drift: exact dependency commits, root gitlink agreement, hashes and explicit host scope.
- Error cleanup: native sockets/processes stop before removing only owned queues; no unrelated queues touched.
- CI/source triggers and truthful receipts: actual native tests execute; skipped/failed work never labelled PASS.

### Task 1: Isolated build and namespace boundary

**Files:** tools/cyberpilot_web_native/{prepare.py,isolation.py,dependencies.json,pyproject.toml,uv.lock,tests/test_boundary.py}.
**Interfaces:** prepare(root,out) -> build receipt and dependency paths; namespace() -> private OPENPILOT_PREFIX context.
- [ ] Write tests: reject absent/unsafe namespace, symlink/public/foreign namespace; cleanup only owned run directory; reject in-checkout/used build output and mismatched root gitlinks. Expected RED missing boundary.
- [ ] Implement guard/context and minimal exact Git fetch/build tooling; fetch/compile only pinned msgq IPC target, preserve tracked source hashes. Record SDK/compiler/binary identity.
- [ ] Run boundary suite (Expected all PASS), install locked native SDK in local venv and build external dependencies (Expected ipc_pyx.so exists; source bytes unchanged).
- [ ] Commit task deliverable and ledger gate.

### Task 2: Actual native collector and web integration

**Files:** tools/cyberpilot_web_native/{fixtures.py,native_check.py,tests/test_native.py}.
**Interfaces:** consumes Task1 owned namespace/dependency receipt; exercises unchanged CerealCollector/Store, actual SubMaster, actual CLI subprocess and authenticated HTTP/browser.
- [ ] Write guarded fixture tests and real native tests first; observe expected failure without fixture runner.
- [ ] Implement only four explicitly synthetic topic builders and bounded IPC receive helper; no control channels or factory mock.
- [ ] Validate native types/validity/timestamps/staleness and source restart. Two separate processes must carry synthetic bytes into actual CLI source=openpilot.
- [ ] Run desktop/mobile browser integration, per-topic stop/recovery and invalid data checks. Expected PASS with actual native imports and no default IPC prefix.
- [ ] Commit with actual test counts and source provenance; if runtime bug is found, add failing regression before minimal fix and document protected-source deviation.

### Task 3: CI, documentation and final qualification

**Files:** tools/cyberpilot_web_native/verify.py, .github/workflows/cyberpilot-web-native.yaml, existing web workflow filters, docs/CYBERPILOT_WEB_NATIVE_KO.md and current product/target guides.
- [ ] Add full gate: boundary/native/basic-web/static/compile/browser, dependency/source manifests; output only external directories.
- [ ] Document exact commands and host-only limits; connect actual source inputs to CI triggers, resolving prior Minor.
- [ ] Run full new gate (Expected PASS); one fresh whole-branch reviewer per executing-plans, explicit strongest model; Important findings RED/GREEN plus full suite, no repeat reviewer.
- [ ] Normal feature backup/main FF/push; verify exact-head CI and artifact hashes/manifests. Seal external evidence and report remaining physical-device work.
