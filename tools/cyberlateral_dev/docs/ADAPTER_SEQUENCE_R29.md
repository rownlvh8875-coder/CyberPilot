# R29 fixed synthetic native adapter→DEV model sequences

This opt-in development check connects the unchanged R28 owned-message reader
to the unchanged public0.3.0 model. It is NOT F61, Controller, vehicle Runtime,
CAN, a generic input reader or deployment qualification. Public wheel unchanged.

## Fixed profiles

- `SIGN_CHANGE_4`: existing sealed R23 four-step sequence. Promoted Float32 0.3,
  negative0.25, inactive positive0.25, reactivated positive0.25. Previous requested
  and applied states differ:5/2, -4/-2,4/0. The inactive limiter result2 is not
  the final applied0 carried into the next invocation.
- `NEGATIVE_CYCLE_99`: existing sealed R26 negative request/driver-limited sequence.
  Exact -85-degree boundary,89/90/0/1 counter behavior, -84.5 reset, inactive reset
  and reactivation. All99 complete input/output records remain pinned.

Synthetic limits16/2/5/7/1/3 are fixture data, NOT actual normalization authority,
vehicle configuration or rate policy. No new expected numbers are generated.
The literal source references are SHA-pinned by the existing reference loaders.
Input recipes are constructed independently of the expected-output assemblies.

Each profile starts explicit `State(0,None,0,0)`. Afterwards the actual preceding
verified output.next_state supplies all three history fields. The profiles reset
independently; their concatenation is not one continuous actual call history.

## Execute

Prepare a fresh pinned native venv and the exact public0.3.0 wheel as documented
in NATIVE_ADAPTER_R28.md. From this component root:

```bash
uv run --locked python -B native_qualification/adapter_sequence_run.py \
  --fixed-adapter-model-sequences \
  --python /absolute/fresh-native-venv/bin/python \
  --wheel /absolute/pinned-pycapnp-wheel.whl \
  --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl \
  --output /absolute/new-output
```

Runner installs nothing. No arbitrary profile/subset, messages, previous state,
timestamps, dataset, vehicle context, r or T2 options exist. Parent output
directory must exist; target must not exist. Output is canonical OBSERVATIONS,
SUMMARY, two separate process receipts and a four-entry SHA256 manifest.
The two workers use fresh -I -B interpreters, empty cwd/private cold prefix and
the unchanged R28 qualified context. Sources are hashed before/after execution.

## Closed model gate

`consume_prepared(profile_id,index,PreparedNativeInput)` checks exact R28/R21
record types, metadata and `R29_<profile>`/`entry_<index>` stamp. Existing consumers
then verify the entire registered input/state before one model step, and the
entire registered output afterwards. Invalid inputs do not call the model;
bad outputs throw without retry or next-state advancement. This gate accepts
only exact fixture values, but is NOT authentication of caller-created records.

`run_registered_sequence(adapter,profile_id)` uses the R28 adapter from a qualified
session. It writes fixed synthetic fields, owns and reads bytes through that
adapter, compares converted scalars/state with the independent ratio oracle,
then consumes the preparation and carries the verified output state. It does
not use R23/R26's older native frame constructors. No borrowed readers escape.

Native input reading does not promote output projections: output remains
`SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE`. No output message packing or CAN occurs.
History/settings/stamps remain controlled synthetic declarations, not actual
custody. Invocation ordering is not elapsed time; no dt is derived.

## Model accounting and checks

Each complete worker performs4+99=103 model calls; its wrapper counts actual
invocations separately from row counts. Two-worker qualification reports206
calls, scoped to those two workers. Two fresh locations report412 R29 calls.
Unchanged R27 regression separately reports454/location,908 for both. Pure/unit,
CI and exploratory executions are additional; this is not a whole-stage total.

The data-only export validator checks all103 full inputs/outputs, state adjacency,
stamps, exact profile coverage, byte-hash syntax and closed gates. Hash syntax
alone is not payload authentication. Separate data-only tests additionally pin
key hand-derived sign/inactive/fault/reset literals. No arbitrary tolerance.

M1 pre-allocation tests use a backend access tripwire. A controlled mutation
moving validation after allocation makes the tests RED; restoring exact original
R28 source makes them GREEN. No R28 executable changes are retained.

## Limits

Single-threaded/cooperative process only. No hostile private mutation protection,
OS attestation, untrusted parser qualification, arbitrary stream support,
transactional crash recovery or portable receipt guarantee. Exceptions stop the
run; successful final artifacts are not published on a worker rejection. A crash
during publication can leave a partial new directory; no atomicity is claimed.

R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/scale null. Actual inputs,
actual custody qualification, activation, F70UH/F70V/F71 remain prohibited.
This development result is not a main-merge, installation or safety approval.
