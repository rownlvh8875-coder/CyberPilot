# R28 controlled synthetic native adapter

Intent: replace caller-asserted scalar readback with a common development
adapter that actually reads bytes it constructed. This is NOT an arbitrary
message reader, vehicle adapter, F61 adapter or deployment qualification.

## Approaches and executor decisions

Keep the existing pure semantic bridge and R19–R27 fixed experiments unchanged.
Add a qualified, context-managed native adapter and a separate R28 worker/runner.
A generic bytes decoder would widen the untrusted parser surface; editing old
demos would invalidate their sealed source pins. Neither belongs in this task.
The user delegated ordinary development decisions and opted out of repeated
design/permission menus; the executor selected this bounded additive approach.

## Contract

`SyntheticSpec(stamp, settings, previous, request, driver, angle_deg, lat_active)`
contains exact existing immutable envelope records, builtin floats and bool.
Existing R20 stamps/settings/previous-snapshot rules remain binding, including
adjacency and declared entry state. These are synthetic declarations, NOT proof
of actual previous execution, actual state history or elapsed time.

Request is finite [-1,1]; driver finite [-1024,1024] and angle finite [-180,180],
both with dyadic denominator <=256. All three must already be exactly binary32
representable, preserving signed zero. Binary64 0.3 is rejected; its explicitly
supplied promoted Float32 value is allowed. No coercion, normalization, rounding,
clamp, scale authority or fallback is introduced.

`qualified_adapter(wheel, schema, package_wheel)` verifies the exact R19 wheel,
schema, CPython3.12.13/Linux/x86_64 isolated fresh venv, installed RECORD/file set
and import origins before native import. Reuse existing verification functions,
closed schema imports, private empty pycache prefix and process receipt. One
context per fresh process; this does not attest the OS or every dependency.

Within that context `adapter.construct(spec)` internally writes all four fields,
serializes owned immutable bytes and returns an opaque identity-bound handle.
`adapter.prepare(handle)` accepts only its own live handles. It parses its own
bytes inside both reader contexts, copies scalars, creates its own readback and
uses the unchanged semantic bridge. `inspect(handle)` exposes a frozen data-only
frame for developer diagnostics, not a parser input. Foreign/copied handles,
caller bytes/frames/readbacks and closed contexts are rejected. Context exit
invalidates handles. No borrowed native objects escape. This is a cooperative
in-process API boundary, not protection against monkeypatching/private access.

Output is `PreparedSemanticInput` wrapped with an R28 controlled-read claim.
The inherited declared-readback custody claim remains unchanged; actual custody
Q05 is NOT_QUALIFIED. State/settings are synthetic caller declarations, not read
from messages. Invocation index is order only; no timestamps/dt are accepted.

## Verification and non-goals

Independent old ratio-based semantic oracle must not import the adapter.
Hand-derived literals additionally pin accepted scalar/state outputs. Native
tests exercise actual pycapnp, owned lifetime, sign/precision boundaries,
invalid specs, foreign handles and closed contexts. Pure tests cover preflight
without importing capnp. Two fresh workers must reproduce observations; repeat
from a committed relocated tree/new environments. Run full pure gate and the
unchanged R27 suite in both locations; R27 executes454 model calls/location,
separate from R28 adapter's zero model calls. Receipts/manifests are not portable.

Public0.3.0/model/wheel/lock and original10 source files stay unchanged. No
Controller, Runtime, CAN, F61, actual inputs, r/dt calculation or main merge.
R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual activation/F70UH/F70V/F71 prohibited.
Commit/push only delegated feature branch and update existing Draft PR2.
