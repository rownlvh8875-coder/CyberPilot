# Device readiness closeout

Goal: finish the native review's deferred source-input and restart coverage,
then provide the next necessary step toward comma4 identification without
requiring CyberPilot to be installed first. User delegated routine design and
publication decisions and asked to continue without approval pauses.

Author choice: a portable standard-library Python observation tool, not a
vehicle installer. Alternatives are waiting for a device connection (does not
prepare the handoff) or requiring the full CyberPilot/native environment on the
device (unnecessary for public system facts). Existing runtime stays unchanged.

The observer reads only /sys/firmware/devicetree/base/model, /VERSION and /AGNOS
metadata, basic platform/Python information and optionally exact-root Git
HEAD/branch metadata. It never imports native/Cereal/Controller, reads Params,
VIN/serial/logs/secrets, starts processes other than read-only local Git, changes
system settings, installs software or opens network services. No broad search.

Missing/empty/unreadable/oversized/nonregular files produce explicit unavailable
values, never fabricated zero/false facts. Final file symlinks and FIFOs are not
read. Model-to-code derivation follows get_device_type in the preserved hardware
source, cited with exact baseline/path/SHA. The resulting code is a hint, not
attestation, installation or vehicle qualification. Source-root is optional;
existing Carrot checkout is acceptable as an observed source, not a CyberPilot
installation receipt. Refuse subdirectory/parent-repository attribution and
inherited Git selectors. Do not claim working-tree content or dirty status.

Any non-system filesystem root is explicitly a test fixture. Regardless of
apparent model/OS, device_installation_qualified and actual_activation_allowed
remain false. Real cloud execution must visibly report host/missing device facts.
The tool prints JSON only; no file writes. Its deterministic ZIP has probe,
Korean instructions, source authority and checksums; it is not a comma image.

Prior native source epoch case uses real IPC: old sample/store, close old
fixture, construct new store/collector, assert no old state, then accept a lower
source timestamp and different explicit value. Coverage of an existing behavior
is characterized and checked with an intentional old-store-reuse mutation; no
runtime change is required if it already passes. Add process.py to both event
filters; native workflow consumes the union of its own and basic-web inputs.

Host-only constraints remain: no device route, full comma4 build/install/boot/
update/restore/actual phone/vehicle verification; no Controller/CAN/F61/actual
r/dt. R_BUDGET unresolved, Static Gate FAIL, actual r/T2/scale null. Preserve prior
workspaces, old lateral/runtime/native safety sources and persistent Git config.
