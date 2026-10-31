# R21 — declared-readback preparation and independent oracle

The pure bridge constructs public0.3.0 LateralInput/LateralState/Limits data
records ONLY. It does not call step, simulate, initial_state, R14 extraction,
quantization, a limiter, Controller/Runtime/CAN/F61 or calculate elapsed dt/r.
Readback-to-byte correspondence and prior history remain declarations, not actual
native custody. Its oracle requires an already valid R20 envelope.

Adapter precision validation uses binary32 struct roundtrip; oracle precision uses
independent integer significand/exponent analysis. Both preserve supplied Float32
readback exactly. Binary64-only0.3 rejects without rounding; the observed native
0.30000001192092896 request passes. That same value as driver/angle still rejects
the existing denominator<=256 synthetic subset. Inactive requests are not zeroed;
signed zero and the smallest binary32 subnormal request survive unchanged.

## Actual closed native experiment

Eight fixed cases; five accepted into data-only records, three rejected with exact
SEMANTIC_DOMAIN agreement:driver/angle precision and request range. Every result
matches the independent oracle exactly, including float.hex and full state/limits.
Six literal output assertions check coverage, fixed fields, signed zero/subnormal,
resumed declaration, rejections and no activation/model/F61 work. Separate pure
tests detect deliberately swapped fields and signed-zero-loss in the comparator.

R21 OBSERVATIONS.json SHA256:
afbc84215769d23a8939828a28cc4c5507485bb8177a3e64e52fadad2c753ae2.
R19 control stays b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74;
R20 control stays d88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af.

Primary and fresh relocated full gates:299 tests PASS (280 inherited +19 R21),
107 own component compilations,77 frozen imports and sealed wheel unchanged.
Explicit native Ruff/Ty/Codespell/7 own compilations and6 literal output checks
PASS. Native observation/SUMMARY bytes reproduce across relocated new environments;
environment-specific receipts are kept separately, not claimed identical.
One fresh final reviewer independently ran19 semantic tests,6 output assertions,
and a pure probe of4,108 exact signed binary32 plus4,108 adjacent binary64-only
values, all correct. No Critical/Important/Minor findings or fix/re-review pass.
This is bounded development verification, not exhaustive numeric or model qualification.

## Reproduction

From tools/cyberlateral_dev, build public wheel to a NEW directory using
python -B tools/build_wheel.py --output /absolute/NEW-package. Its SHA must be
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Create a separate CPython3.12.13/Linux x86_64 venv; install the existing hash-pinned
native_qualification/requirements.txt and this exact local wheel with --no-index
--no-deps (the qualifier itself never installs or downloads anything).

```bash
uv run --locked python -B native_qualification/run.py --semantic-bridge --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r21-output
```

From that output directory run native_qualification/test_semantic_observations.py
by absolute path with the native interpreter -I -B -v, then sha256sum -c SHA256SUMS.txt.
Two isolated workers must match before output publication. Compare a relocated
source/new-env run's observations/SUMMARY separately from environment receipts.

Both installed wheel payloads/RECORDs/namespaces/cache and import origins are
verified before importing native/public modules. The public install's exact
uv_cache.json is non-executable installer metadata, checked by RECORD hash/size,
not exempted payload code. Unknown extras/modified payload/cache still reject.
New repository imports use a private empty bytecode prefix and -B. Schema/include
identity and old native restrictions remain enforced. No arbitrary message mode.

No flag retains R19; --owned-boundary retains R20; --semantic-bridge requires
--package-wheel. Conflicting modes, malformed mode types, missing/wrong/unexpected
public wheel and existing output reject without fallback. Native GitHub CI NOT_RUN.

## Boundaries

Preparing model INPUT STRUCTURES is not model execution, an F61 constructor/input,
actual call-state validity, feasibility, performance or deployment readiness.
Public API/wheel/lock/frozen references/default workflow remain unchanged.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
