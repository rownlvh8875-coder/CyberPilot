# R19 — isolated synthetic native-message observations

Status: scoped qualification experiment, NOT a native reader or vehicle approval.
Baseline:06d33b6694681db598aa5a50cef02f7a1356972b.

## Authorization amendment and selected approach

The user requested the next stage after the proposed R19 offline synthetic
native/schema qualification. This permits pycapnp/schema loading ONLY in an
explicitly invoked isolated subprocess. Historical R13/R14 prohibitions remain
accurate for those stages. This document is the prospective narrow amendment.
Routine design/inline execution/feature-branch publication were delegated.

Choose a separate, pinned binary-wheel environment and an observation-only tool.
Do not import original structs/cereal/opendbc/openpilot modules. Directly load the
unchanged frozen car.capnp with an explicit include root copied from the verified
wheel. No native-to-model adapter is implemented. Default verification, component
lock, public API0.3.0, sealed wheel, source helpers and goldens stay unchanged.
Using the root environment or silently enabling native reads in CI was rejected:
neither isolates this authorization from existing pure synthetic work.

## Inputs, receipts and reports

Require CPython3.12.13/Linux x86_64 and pycapnp2.1.0's exact cp312 manylinux wheel
already recorded by the root lock. Verify the downloaded wheel SHA before import;
verify all installed wheel-member bytes, including extension/bundled libraries,
before import (installer-rewritten RECORD is checked for full coverage/hash/size
instead of byte equality; its actual hash and the three metadata additions plus
the exact generated capnpc-cython wrapper hash are retained; that wrapper is NOT
run). Reject symlinked/missing/mutated installed members. Preexisting .pyc caches
and extra files/symlinks in wheel-owned package/metadata directories reject BEFORE
native import. -B alone does not block bytecode reads. The tool never deletes
caches as a fallback. Resolve only car.capnp and wheel capnp/c++.capnp into a
private include tree, preserving bytes.
Record Python binary, imported file and Linux mapped-library hashes after loading.
This is an observed process receipt, not an authenticated OS image, portable ABI
promise, malicious-interpreter defense or complete system attestation.

Two fresh worker processes produce canonical observation bytes. Equality is
required. Environment/path-specific receipts are separate from portable semantic
observations. A relocated source/new environment run supplies an additional check.
Do not deserialize user/vehicle messages; all message bytes originate inside the
closed fixture routine. Output paths must be new, and output is data, not installer.

## Q01–Q06 coverage and honest limits

- Q01: exact wheel/installed/schema/include/process receipts; OS-image trust is
  explicitly outside qualification. No missing dependency fallback.
- Q02: observe actual builder/reader classes, schema IDs/fields, owned-buffer read
  context and exception for an invalid field. No unsafe use-after-close probe;
  general lifetime/concurrency behavior remains NOT_QUALIFIED.
- Q03: separately construct omitted vs explicitly written zero/False; retain
  construction ledgers, wire hashes, readback and observed presence behavior.
  Equal values or bytes do NOT establish explicit field supply.
- Q04: observe assignment, getter and owned serialization readback for0.3,-0.0,
  +/-1, smallest subnormal/normal, NaN, infinities and overflow. Keep literal
  independent IEEE reference values distinct from observations. No nonfinite
  JSON numbers, arbitrary tolerance, coercion, clamp or model invocation.
- Q05: no call-entry hook, six-setting/prior-state custody or concurrency proof
  is implemented. Mark NOT_QUALIFIED rather than inventing an atomic snapshot.
- Q06: native activation remains NOT_IMPLEMENTED; no profile is accepted by this
  observation tool. Existing pure exact-record rejection/domain tests remain
  required; observations cannot authorize a reader or widen its domain.

Overall success means OBSERVATIONS_REPRODUCED_READER_STILL_BLOCKED, never all-Q
PASS, native exact replay, actual deployment, complete state custody or safety.

## Boundaries

Controller/Runtime/CAN/F61 import/execution=0; actual/raw vehicle inputs=0;
model/calculator input generation by this tool=0; r/dt calculation=0.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
Candidate/Runtime=NO_GO; SOURCE_SCHEMA_UNQUALIFIED=6000;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
Feature Draft PR may be updated; no main merge, installation, observer or capture.

## Reproduction

See native_qualification/requirements.txt and the R19 implementation plan.
The opt-in command requires --python pointing to a separate clean environment,
--wheel pointing to the exact downloaded wheel, and --output to a NEW directory.
There is no default native backend, reader registration, raw-data input option,
network step or dependency installation in the observation command itself.
