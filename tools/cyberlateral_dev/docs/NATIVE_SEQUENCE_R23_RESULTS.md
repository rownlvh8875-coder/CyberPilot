# R23 — fixed synthetic native/model state continuity

Literal reference preregistered atc2d695b1086021492d712c9dfdfc5196b8614348,
BEFORE R23 implementation/tests/model execution. Reference SHA256:
221b04aae7a149409f5f91aa516e7f9fcefe090958e785d91bc6fd4153161e97.
Expectations come from sealed public0.3.0 source, not observed outputs. All four
matched on first R23 consumer execution, without modifying the reference.

## Results

One closed native sequence produces final commands2,-2,0,2. Its middle inactive
call retains limiter result2 in trace but stores final0; the following active
call consumes prior applied0, not previous requested4 or pre-gate limited2.
Each previous verified output.next_state is carried to the next native frame's
explicit previous snapshot. This demonstrates synthetic model state carry, NOT
real Controller history/custody, elapsed time, runtime or native exact replay.

The parent now requires exact coverage/full registered input/output/count types
before creating an output directory. Two equal but incomplete workers reject.
R22's M1 is fixed prospectively:both summaries derive counts from validated
worker observations, rather than asserting constants. Historical sealed evidence
is unchanged. New pure tests cover missing/duplicate/extra/reordered rows, bool
counts, wrong flags, incorrect previous state, changed complete output and failed
publication; native workers themselves are separately tested in the pinned env.

Primary full gate338 tests PASS (318 inherited +20 new),116 own compilations,
77 imported frozen checks and sealed public wheel unchanged. Explicit native
Ruff/Ty/Codespell/11 own compilations and7 independent literal output checks PASS.
Two designated R23 workers execute4 steps each/8 combined. Unit/reviewer/CI model
work is additional and NOT included in that figure. Projection words are schema
simulation, not native output/CAN wire; scalar kind strings are model trace labels.

Fresh archived source/new dev+native environment also passes338 tests/116 own
compilations. Native observations and SUMMARY match primary byte-for-byte; four
designated R23 workers total16 steps. The separate R22 control pair adds10;
unit/reviewer/CI activity remains outside these scoped counts. Environment receipts
and complete pure SUMMARY are not claimed equal or authenticated.

One fresh read-only whole-branch reviewer independently ran20 new pure tests and
7 observation checks:PASS, Critical0/Important0. Deferred Minor R23-M1:parent
coverage currently enforces numerical records/counts/selected gates, not every
auxiliary oracle/stamp/binding/identity/custody/module claim. Current actual
producer/observations are correct; mandatory recorded-output checks independently
verify key claims. Parent PASS alone is not full metadata validation/authentication.
This reporting-hardening item is distinct from the fixed R22 count issue. No
source correction/re-review pass was needed for this fixed synthetic head.

R23 OBSERVATIONS.json SHA256:
662a138f71ef6c065eebb6061ba71ab2e6c728250c57bef8a932e32e0c260441.
R19/R20/R21/R22 observation controls remain respectively:
b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74;
d88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af;
afbc84215769d23a8939828a28cc4c5507485bb8177a3e64e52fadad2c753ae2;
c802a6ecad9f0cae59b8d82598d9b6a58a171d7e8a826406b21e3c157d02c4a7.
Older R19/R20/R21 run no new model work; R22 still executes5 per worker. New
source hashes in summaries/receipts are expected, not historical-byte equality.

## Reproduction

Follow the separate CPython3.12.13/Linux x86_64 native environment procedure in
[R21 results](SEMANTIC_BRIDGE_R21_RESULTS.md); same pinned public/native wheels,
schema/RECORD/cache/import-origin guards. No new dependency or relaxed guard.
From tools/cyberlateral_dev:

```bash
uv run --locked python -B native_qualification/run.py --model-sequence --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r23-output
```

From that output directory run native_qualification/test_sequence_observations.py
by absolute path using the native interpreter -I -B -v and verify SHA256SUMS.txt.
Run in a fresh archived source/new dev+native environment; compare observations
and SUMMARY, not environment-specific process/install receipts. Preserve both
receipts without metadata normalization. Native GitHub CI NOT_RUN; pure workflow
continues to exclude capnp installation/import, while testing the new pure gates.

## Maintained boundaries

Public API/wheel/lock/default workflow and old77 frozen files unchanged. One new
DEV literal reference is independently SHA-pinned. Original trees read-only.
No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment/main merge.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
