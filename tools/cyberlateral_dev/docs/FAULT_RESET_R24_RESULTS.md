# R24 — fixed synthetic fault/reset trace and auxiliary claims

All96 literal rows were preregistered ate8cf2e0d2cebf7e10ff9f6b20206a95a273b7958
before R24 implementation/tests/model execution. Reference SHA256:
7d0d6ab9702318049752fc5312c6530f91822ed391a83863a56134d95df550e0.
They were expanded from the hand-derived source table, not observed outputs.
The first96-step consumer execution matched without changing any literal.

## Boundary behavior

At calls89/90/91/92 (indices88/89/90/91), next counters89/90/0/1 and request
bits true/false/false/true match unchanged public0.3.0. Both suppressed calls
retain integer command4; inventing command zeroing would violate this model.
No permission to transmit these synthetic commands or safety conclusion follows.
Below85 resets the counter. Inactive call94 (index93) retains limited4 but final0;
reactivation consumes prior final0 and limits the next command to2, not4.
All complete quantization/clip/flag/state/projection records are checked, not
only these boundary values. Indices are invocation order, not elapsed time.

## Metadata and numerical gates

R23-M1 is fixed prospectively. After numerical coverage/count/input/output/
adjacency checks and before mkdir, parent validates schema/version/scope/reference,
schema/native-wheel identity, forbidden-module/custody/oracle declarations,
payload-hash format, exact sequence stamps/state-binding/time labels; R22 also
requires its exact accepted precision/custody and rejected-oracle agreement,
algorithm declaration and non-F61 structure flag. Existing test doubles now
include the real complete claims. No old actual observation bytes were changed.
These are consistency checks, not external payload/history or OS authentication.

Primary final full gate358 tests PASS (338 inherited +20 new),122 own pure
compilations,77 frozen imports and unchanged public wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Explicit native Ruff/Ty/Codespell/14 own compilations and6 independent literal
output checks PASS. An earlier intermediate full run passed346 unit tests but
failed Ty on a next-task test's mixed kwargs; corrected and retained, not omitted.
Final full-tree verification covers both tasks, with no claim that the earlier
mutable tree had passed its entire gate.

Final R24 OBSERVATIONS.json SHA256:
799d302cd2d0fa45a57e81207d1a9f7c8f96af47851770aaa6c026537706312c.
Final primary SUMMARY SHA256:
d220621435862948fb123fad75ef73b317a360132c4d7b0b286c311b4786bba9.
Two designated primary workers execute96 each/192 combined. A preliminary pair
also executed192 before the last R22-only metadata tightening; its observations
match but its source-identity summary is retained separately, never rewritten.
R22/R23 control pairs add10/8 separately. Unit/reviewer/CI work is additional;
none of these scoped figures is a whole-stage aggregate.

R19–R23 observation controls remain respectively:
b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74;
d88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af;
afbc84215769d23a8939828a28cc4c5507485bb8177a3e64e52fadad2c753ae2;
c802a6ecad9f0cae59b8d82598d9b6a58a171d7e8a826406b21e3c157d02c4a7;
662a138f71ef6c065eebb6061ba71ab2e6c728250c57bef8a932e32e0c260441.
Source-hash summaries and environment receipts may differ legitimately.

## Reproduce

Follow the separate pinned CPython3.12.13/Linux x86_64 native env setup in
[R21 results](SEMANTIC_BRIDGE_R21_RESULTS.md); no dependency or identity guard
changes. From tools/cyberlateral_dev:

```bash
uv run --locked python -B native_qualification/run.py --fault-boundaries --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r24-output
```

From that output directory run native_qualification/test_fault_observations.py
by absolute path with the native interpreter -I -B -v, then verify SHA256SUMS.txt.
Fresh archived source/new dev+native env should reproduce observations/SUMMARY;
preserve environment receipts without normalizing or claiming equality. Native
GitHub CI NOT_RUN; default pure CI does not install/import capnp.

## Boundaries

Public source/API/wheel/lock/default pure workflow and old77 frozen files unchanged.
No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment/main merge.
Projection words are mathematical schema simulation, kind labels not live NumPy
ABI observations. R_BUDGET=UNRESOLVED; Static Gate=FAIL; r/T2/scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
