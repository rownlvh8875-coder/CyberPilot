# R22 — fixed synthetic single-step consumption

The literal reference was committed in147a6454137da3c4d5c844517d15c5d9f55d0514
BEFORE consumer implementation/tests and the first R22 model execution. SHA256:
55e07d229fadd5cbe96130670b3a16812ef0ef9ebf20a389408cd5ca9cf0fff1.
Independent expectations were derived from sealed public0.3.0 source; no observed
outputs were adopted or tuned. All five matched on the first R22 execution.

The closed consumer checks the entire registered input, including Float32-origin
hex, signed zero, six explicit synthetic settings, prior declaration and provenance.
Only then does it call public step ONCE. Complete quantization/driver/rate/fault/
request/state/projection output must equal the independent literal assembly.
Unknown/changed inputs reject before work; model mismatch fails without returning
a successful output. No retries, automatic initialization, simulation or chaining.

## Actual closed native observations

Eight fixed native frames:five accepted into one step each, three domain rejects
before step. Final integer outputs in zero/rounded_request/signed_zero/resumed/
smallest_subnormal order:0,2,0,4,0. Negative-zero input/product traces and the
smallest subnormal are preserved. Active zero command can still have request=true.
These are synthetic DEV-model semantics, NOT steering performance evidence.

Primary and fresh relocated full gates:318 tests PASS (299 inherited +19 new),
111 own component compilations,77 frozen imports and sealed wheel unchanged.
Native Ruff/Ty/Codespell/8 own compilations and7 literal output checks PASS.
Native observation/SUMMARY bytes reproduce in the fresh source/new environment.
Environment-specific receipts/manifests are NOT equal. Complete pure SUMMARY
also differs only in numeric execution identity:NumPy installer RECORD and its
aggregate payload digest vary; both unmodified receipts are retained. Within
each full gate, numeric/report pairs remain byte-identical.

One fresh read-only whole-branch reviewer independently ran19 new unit tests and
7 observation assertions:PASS, Critical0/Important0. Deferred minor M1:the native
runner currently writes fixed5/10 summary counts; separate mandatory observation
tests validate exact current coverage/counts, but the runner should eventually
enforce those internally against a future shared worker regression. No second
review or code-fix pass was needed at this fixed head. This is bounded synthetic
verification, not exhaustive correctness or safety certification.

OBSERVATIONS.json SHA256:
c802a6ecad9f0cae59b8d82598d9b6a58a171d7e8a826406b21e3c157d02c4a7.
Two worker observation bytes match; their model executions are5 each/10 combined.
Counts cover these sealed processes, NOT aggregate unit-test/full-stage activity.
Projection bit words remain mathematical schema simulations, not native output
message/CAN byte observations. Resumed state is declared, not proven history.

R19/R20/R21 observation SHA controls remain respectively:
b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74;
d88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af;
afbc84215769d23a8939828a28cc4c5507485bb8177a3e64e52fadad2c753ae2.

## Reproduction

Follow the separate pinned native environment setup in
[R21 results](SEMANTIC_BRIDGE_R21_RESULTS.md). Require exactly the same public
wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c
and pycapnp wheel/schema/installed-payload/origin/cache guards; no weakened checks.
From tools/cyberlateral_dev:

```bash
uv run --locked python -B native_qualification/run.py --model-consumption --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r22-output
```

From that output directory run native_qualification/test_model_observations.py
by absolute path with the native interpreter -I -B -v; seven independent literal
checks must pass. Check sha256sum -c SHA256SUMS.txt. Reproduce observations/SUMMARY
in a fresh relocated source/new environment; receipts remain environment-specific.
Do not use another mode together with --model-consumption. Without this flag,
older modes do not consume the model. Native GitHub CI remains NOT_RUN.

## Maintained boundaries

Public package/API/wheel/lock/default pure workflow and original77 frozen files
are unchanged; one separate DEV reference has its own SHA pin. Original trees
are read-only. No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment.
R_BUDGET=UNRESOLVED, Static Gate=FAIL; actual r/T2/vehicle scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
