# R20 — owned synthetic envelope results

The pure boundary validates exact immutable records, source/stamp/schema labels,
owned-byte digests, explicit field ledgers, bounded synthetic settings and prior
declarations. It does NOT decode or establish native validity, authentic call
custody, atomicity or a verified previous transition. Deliberately opaque fixtures
can pass structural checks; this is documented behavior, not a native reader.

## Closed native demonstration

Four cases:explicit_zero,rounded_point_three,negative_zero,resumed_declaration.
Their original local CC and CS builders are mutated AFTER to_bytes. Owned payload
digests and owned-context readback stay unchanged. No reader/builder escapes.
The resumed case explicitly declares prior applied3/counter1/prior candidate5;
these are not inferred, computed by the limiter, or replay/history validated.
The CS builder is a bare synthetic CarState; ledger CS.out paths denote source
roles, not an actual Interface wrapper or installed capture hook.

An independently constructed omitted-zero CC has the same bytes as explicit
zero/False. Removing the explicit ledger rejects OWNED_FIELD_LEDGER despite this
equality. Nine negative cases reject with exact structural codes:missing ledger,
wrong schema, crossed settings/prior stamps, mutated/mutable payload, wrong prior
index, source/model prior mismatch and wrong stage.

Two isolated workers produce byte-identical observations. Six independent literal
assertions verify fixed case coverage, exact Float32/signed-zero values, builder
mutation isolation, default ambiguity, rejection map and blocked actual-reader/
model gates. R19's original observation bytes remain unchanged at:
b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74.

R20 OBSERVATIONS.json SHA256:
d88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af.

Primary and relocated full gates:280 tests PASS (263 inherited +17 R20).
Each separate native observation check:6 PASS. Component/static checks and
102 own-code compilations PASS; explicit native Ruff/Ty/Codespell and5 own-code
compilations PASS.77 frozen imports and sealed public wheel unchanged.
Fresh relocated sources/new environments reproduce observation and SUMMARY bytes;
process/environment receipts are retained separately, not claimed identical.
One fresh final reviewer independently ran17 tests,40 hostile probes and6 output
checks, finding no Critical/Important/Minor defect. No fix pass/re-review needed.

## Reproduction

Use the same separate binary-only native environment/wheel requirements as R19.
From tools/cyberlateral_dev, supply explicit absolute task paths and NEW output:

```bash
uv run --locked python -B native_qualification/run.py --owned-boundary --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r20-output
```

From that output directory, invoke the absolute path of
native_qualification/test_owned_observations.py with the native interpreter
-I -B -v, then sha256sum -c SHA256SUMS.txt. Omitting --owned-boundary retains R19.
The flag is not automatic native backend selection or actual-message permission.
R19 characterization controls also run before the closed R20 demo in its verified
schema context. New repository imports use a private empty bytecode prefix with
-B; existing .pyc cannot substitute for the demo's source. Original installed
package cache/extra-file rejection remains intact.

Default dev.py verification stays pure. Run Ruff/Ty/Codespell and own compilation
explicitly on native_qualification as well. Native GitHub CI=NOT_RUN. Environment
receipts retain actual installed/process paths/hashes separately from deterministic
observations. Receipt equality/portable ABI/OS attestation is not claimed.

## Remaining boundary

Next meaningful development work is a deliberately synthetic-only semantic bridge
from this envelope to prepared scalar/state fields, with explicit precision/domain
rules and an independent oracle. It must not feed arbitrary bytes to a native
parser or auto-route native observations through R14's binary64-only profile.
No such bridge or model work is implemented by R20.

Public API/wheel0.3.0, component lock, frozen goldens and default workflow unchanged.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
New boundary/demo Controller/Runtime/CAN/F61/actual-input/model/r/dt work=0.
