# R25 — fixed negative-angle/driver results

## Preregistration and exact scope

Twenty full literal records were preregistered at
fbfb6a6fda765975490606f29c395c82f750964d BEFORE any R25 model execution.
Reference SHA21de9d95fa3e45dd03fe5ac8da0505a4ea94d233dc81d21ba65d741573ef1fa7.
No expected record was changed after execution. Unchanged public0.3.0 produced
the complete prepared-input/quantization/clip/state/projection records exactly.
This is one fixed synthetic sequence, not a general driver-domain qualification.

Fractional bounds11.5/-11.5 and float-kind hexadecimal clip results are retained;
nearest-even integer12/-12 is not post-round clamped. These are unchanged model
semantics, not physical limits or safety recommendations. Negative85 is inclusive,
negative84.5 clears the counter, and index16 enters inactive with nonzero counter1
and applied-12, clearing both to0. Index17 consumes actual verified final zeros.
This does not qualify negative-angle89-call suppression or actual elapsed time.

## Verified gates and reproduction

Core consumer RED8 (missing implementation) -> GREEN8. Opt-in/parent gate RED5
(missing mode) -> GREEN5. Reference-summary regression RED R24 stale identity ->
GREEN across R22/R23/R24. Complete pure gates373 tests (359 inherited +14 new),
127 own pure compilations,77 frozen files and unchanged public wheel PASS.
Explicit native Ruff/Ty/Codespell and16 own in-memory compilations PASS. Two
import-order lint findings were corrected before final native runs.

Source3571e5dea66f2612b14c55b487b53089b04cc540 was archived into a new directory
with the exact workflow and completely new dev/native environments. Both primary
and relocated full gates pass373/127/77; each native run also passes seven
independent literal output assertions. OBSERVATIONS and SUMMARY are byte-identical:

- OBSERVATIONS:2283bed92bafaacda57486fe109be213d5a1479a820cfc63074539f3d7ba3150.
- SUMMARY:84f0d4d2784bca738c8457e404ec5bb99a5119c5e35c9f77b85db27bc546c7ae.

Each pair uses2 workers/20 steps each; four designated R25 workers total80.
R22/R23/R24 control pairs10/8/198=216 are separate. Unit/reviewer/CI activity is
additional; these are not a stage-wide aggregate or zero-model-work claim.
All six R19–R24 observation hashes are unchanged. Environment receipts and their
manifests, and complete pure summaries, are preserved without byte-equality or
OS-image attestation claims. Both complete pure94-entry manifests are verified.

Public wheel stays46646 bytes/27 entries, SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
No public API/source/lock/default pure workflow changes. Native GitHub CI NOT_RUN.

## R24 historical metadata correction

R24 sealed ZIPec57d39799174f6cb9c04f797faa4c7753dbe97ec4908f90f96db2075088c052
is unchanged. Its numerical observations and consumer correctly used v2 reference
dfb150fc3f1348be6fae161bdb2d524dc1138c504410c8ef38bf874c27b4d8cd, but summary
label incorrectly named v1 SHA7d0d6ab9702318049752fc5312c6530f91822ed391a83863a56134d95df550e0.
The parent duplicated a stale file-path branch. Now it copies the already fully
numerical-and-claims-validated observation reference into the summary; it does
not change the calculator, expected output or old evidence. The R25 package
contains R25_R24_REFERENCE_CORRECTION.json and original archived summary and
observation members, plus a current R24 control with corrected summary identity.

## Reproduce the native experiment

One fresh whole-branch review plus supplemental results-document read found
Critical0/Important0/Minor0. Reviewer independently ran14 recorded-data assertions
and checked literals/manifests/frozen identities, but did not rerun the full373
suite/native workers/static tools or claim production readiness. Its exhaustive
review limits and executor rulings are retained in the external evidence. No
implementation fix or re-review was needed.

Use the pinned CPython3.12.13/Linux x86_64 separate pycapnp2.1.0 environment and
exact sealed public wheel as in [R21 results](SEMANTIC_BRIDGE_R21_RESULTS.md).
From tools/cyberlateral_dev:

```bash
uv run --locked python -B native_qualification/run.py --driver-boundaries --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --output /absolute/NEW-r25-output
```

From that new output directory, run native_qualification/test_driver_observations.py
by absolute path with native python -I -B -v, and verify SHA256SUMS.txt. There is
no generic external reader, actual history, timing inference or output activation.

## Maintained gates

No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment/main merge.
Kind strings are model trace labels, not live NumPy ABI observations.
R_BUDGET=UNRESOLVED; Static Gate=FAIL; r/T2/vehicle scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
Final review, exact-head pure CI and external evidence seal are recorded in the
handoff; documentation-only publication does not alter the qualified tool sources.
