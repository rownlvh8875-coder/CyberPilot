# Controlled synthetic native adapter (R28)

Development-only API, not a production reader. Public0.3.0 is unchanged and
does not package this opt-in adapter. R19–R27 experiments remain unchanged.

## Qualified entry point

Run the fixed qualification separately from `dev.py verify`:

```bash
uv run --locked python -B native_qualification/adapter_run.py \
  --controlled-synthetic-adapter \
  --python /absolute/fresh-native-venv/bin/python \
  --wheel /absolute/pinned-pycapnp-wheel.whl \
  --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl \
  --output /absolute/new-output
```

It installs nothing and accepts no message/log/vehicle/policy inputs. The native
venv must contain the exact pinned wheel and public wheel, with no unexpected
package payload or bytecode. The worker uses `-I -B`, empty cwd and private cache
prefix; the schema/import closure and observed process files are recorded.

For synthetic developer use inside such an isolated worker:

```python
from native_qualification.adapter_runtime import qualified_adapter

with qualified_adapter(wheel, schema, public_wheel) as session:
    # Import these only after the qualified context has verified the backend.
    from integration_tools.native_adapter import SyntheticSpec
    from integration_tools.owned_message_boundary import (
        PreviousSnapshot, SettingsSnapshot, Stamp,
    )
    stamp = Stamp('EXAMPLE', 0, 'SYNTHETIC')
    spec = SyntheticSpec(
        stamp, SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
        PreviousSnapshot(stamp, None, 0, 0, 0, 0, None,
                         'ENTRY_BEFORE_CURRENT_LIMITER'),
        0.25, 1.5, -7.25, True,
    )
    handle = session.adapter.construct(spec)
    result = session.adapter.prepare(handle)
    sample, state = result.prepared.sample, result.prepared.state
# session.receipt now records the observed process. Retained handles reject.
```

One qualified context per fresh process. Use from a single thread; this is not a
concurrent streaming service. `_SyntheticAdapter` and private handles are not
alternate qualified entry points. Do not pass an arbitrary native backend.

## Accepted values and ownership

Builtin finite floats exactly representable as Float32, no coercion or rounding:
request [-1,1], driver [-1024,1024], angle [-180,180]. Driver/angle additionally
require a dyadic denominator<=256. Boolean active is required, even when false.
Signed zero and the smallest request Float32 subnormal survive. Binary64 `0.3`
rejects; explicitly promoted `float.fromhex('0x1.333334p-2')` is accepted for
request, not for the narrower driver/angle domain.

Existing R20 settings, stamp and declared prior-state rules apply. These facts
are synthetic declarations supplied together, not actual observed history.
The adapter explicitly writes all four message fields, holds immutable bytes,
reads them inside native contexts and retains no borrowed reader. Only its own
weak identity-bound live handle can retrieve those bytes. `inspect` returns a
frozen diagnostic frame, but that frame/its bytes cannot be passed to `prepare`.
Copied/foreign handles reject; context exit clears handles and closes the adapter.
Private-member access, monkeypatching and hostile same-process code are outside
this cooperative API boundary. No actual/native-custody Q05 promotion occurs.

## Stable rejection families

- `ADAPTER_SPEC_TYPE`, `ADAPTER_DOMAIN`, `ADAPTER_PRECISION`: invalid spec.
- `ADAPTER_ENVELOPE:<R20 code>`: stamp/settings/previous/payload mismatch.
- `ADAPTER_HANDLE_TYPE`, `ADAPTER_HANDLE_UNKNOWN`: unowned normal API input.
- `ADAPTER_CONTEXT_CLOSED`: all operations after context exit.
- `ADAPTER_NATIVE_SCHEMA`, `ADAPTER_NATIVE_CONSTRUCTION`, `ADAPTER_NATIVE_READ`,
  `ADAPTER_READBACK_MISMATCH`: backend does not deliver the expected exact data.
- `ADAPTER_SEMANTIC:<R21 code>`: conversion contract rejects; no fallback.

Identity/runtime/RECORD/origin failures retain the R19 verifier's exact codes.
Native allocation/reader errors produce no partial prepared output. Construction
is not a transaction across multiple calls; no actual sequence is inferred.

## Assurance boundary

Output is a development model input/state record, NOT F61 constructor arguments.
R28 does not call model step/simulate, Controller, Runtime, CAN or F61. R27
regression separately makes454 model calls per suite. Other pure unit/CI tests
also perform model work; zero R28 calls is not a whole-stage zero claim.

Invocation index means order, not elapsed time. No actual r, T2, vehicle scale,
hardware limit or deployment facts are supplied. R_BUDGET remains UNRESOLVED,
Static Gate FAIL, actual custody NOT_QUALIFIED, actual activation/F70UH/V/F71
NOT_ALLOWED. Process receipts are observations, not OS attestation.
