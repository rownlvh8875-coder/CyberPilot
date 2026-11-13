# CyberPilot product web integration

User goal: a branch installable on a supported comma device, with a mobile live
status page. This increment completes the cloud-implementable monitoring path;
it does not certify a vehicle installation or enable custom control.

## Contract

A standard-library package at `openpilot/system/cyberpilot_web` supplies real host
telemetry and an explicitly selected, lazy, read-only Cereal subscriber. Four
independent topics (deviceState, selfdriveState, carState, managerState) retain
validity, source timestamps and monotonic receipt age. A repeated/out-of-order
message cannot renew freshness. Invalid/stale/missing records expose null data.
Source timestamps cross JSON as decimal strings. No control publishers or Params
writes. No F61 import/execution or rate-policy calculation.

The mobile page polls a same-origin authenticated GET API every second. Five
seconds is a display freshness policy, not vehicle timing. A browser watchdog
clears live claims on network loss. Host metrics and observed openpilot state
are labelled separately. Unavailable vehicle values are never fabricated.

Default bind is loopback. A private random token file is mandatory; bearer auth,
constant-time comparison, fixed static routes, CSP, no CORS, no query credentials,
no request logs, bounded connections. Optional TLS; LAN binding is explicit.
There are no remote control/config endpoints. Assets have no external resources.

Manager registration is opt-in (`CYBERPILOT_WEB=1`); normal boot behavior stays
unchanged. Source bundle works standalone for host monitoring, with a deterministic
manifest. Safe readiness inspection checks launcher resources without executing
launch scripts. Fix the confirmed misplaced AGNOS manifest reference after a
failing static test. Uninitialized native submodules and absent actual target
qualification remain visible blockers. A mobile monitor is not a control Adapter.

## Completion

Pure tests, real host HTTP/browser checks at desktop/mobile sizes, disconnect and
stale behavior, deterministic extracted bundle smoke test, static checks, fresh
whole-branch review, normal Git backup/main publication and dedicated CI evidence.
Actual comma boot/network/vehicle tests require the identified physical target.
R_BUDGET remains UNRESOLVED, Static Gate FAIL, actual r/T2/scale null.
