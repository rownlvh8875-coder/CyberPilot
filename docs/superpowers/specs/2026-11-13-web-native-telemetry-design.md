# Host-native telemetry integration

User goal: continue toward comma4 / 2021 Santa Fe TM diesel installation and a
live mobile monitor. The next cloud-implementable uncertainty is native Cereal
interoperability; physical-device access is not configured. This increment
qualifies synthetic host-native telemetry only, never actual vehicle use.

Author choice under standing autonomous execution: use exact pinned msgq and
opendbc gitlinks, compile only msgq/ipc_pyx.so on Linux x86_64, and load actual
Cereal schemas through pycapnp 2.1.0. No full openpilot build, Controller, CAN,
F61, actual r/dt, or actual vehicle data. Existing runtime package stays read-only.
The full device build remains a separate target-architecture task.

Alternative: wait for physical device; this leaves native protocol gaps open.
Alternative: initialize/build the entire root project; this adds unrelated
hardware/model requirements. A minimal native telemetry qualification exercises
the monitor's real boundary with a smaller, reproducible build.

## Isolation and identity

Dependencies: msgq 0e266c1dbcf7328beee3e57b4a8688555387c877 and opendbc
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76, copied by exact Git fetch into an
external new build workspace. Never initialize source-checkout submodules or
change root dependencies. Record tracked-source hashes before/after and compiled
binary SHA, compiler/SDK/platform metadata. Native binary reproducibility is not
claimed; dependency and source identity are.

Every synthetic publisher/consumer runs with a freshly created private 0700
/dev/shm/msgq_cyberpilot_web_native_<32 lowercase hex> directory and matching
OPENPILOT_PREFIX, before native imports/sockets. CEREAL_FAKE must be absent:
fake-event prefix alone does not isolate IPC. Refuse missing/unsafe/existing
namespaces; never clean any unrelated/default queue. Only the four status topics
are publishable by test fixtures. No can/sendcan/carControl/carOutput endpoints.
Cleanup occurs only after test publishers/consumers exit; ownership/containment
checks precede removal of this run's newly created namespace.

## Qualification

Actual SubMaster plus production CerealCollector must handle explicit valid
fields, finite/null conversion, invalid messages, independent staleness,
duplicate/backward times, missing samples, exact UInt64-to-string timestamps,
and source restart via a new store. Fixtures are synthetic and prospective.

A separate production CLI process with source=openpilot must consume actual IPC
from the synthetic publisher. Authenticated HTTP and real PC/mobile Chromium
must show those values, invalid/stale values, disconnect/recovery and clear
synthetic provenance in alerts. Tests publish no vehicle commands. Source stop
is distinguished from web-server connection failure. Unit/mock results are not
substitutes for the native checks.

CI repeats the locked native build and tests in a separate workflow. Basic web
suite stays independent of native dependencies. Include direct source inputs in
workflow triggers (resolve the previous deferred filter gap). Ship Korean run
instructions and honest qualification boundaries. Preserve old lateral sources,
web runtime bytes, prior evidence/worktrees and persistent Git configuration.
