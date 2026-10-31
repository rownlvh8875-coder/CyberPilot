# R19 — actual synthetic native observations

Status: F70UGZ_R19_OBSERVATIONS_REPRODUCED_READER_STILL_BLOCKED.
This is NOT all-Q qualification or permission for a native/vehicle reader.

## Observed facts

Exact pycapnp2.1.0 cp312 manylinux x86_64 wheel SHA256:
48938e0436ab1be615fc0a41434119a2065490a6212b9a5e56949e89b0588b76.
Exact extension SHA256:
d68adee01debfc7324ca057374fa3100e3575f43268c848ad46e92be3da67815.
Exact car.capnp SHA256:
098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788.
Explicitly copied wheel c++.capnp SHA256:
52ead0eaa560b21e692d6f3d9966a52dfc99e19f53ae2d7c7bd2944a240d86de.
These are development artifacts, NOT installed-vehicle source authority.

- Builder class: capnp.lib.capnp._DynamicStructBuilder; reader:
  capnp.lib.capnp._DynamicStructReader. Both CarControl and CarState share these
  generic classes, but schema IDs differ:17836551423953212591 and
  11359479080460390460. Class name alone cannot identify an admissible schema.
- Assigned0.3:0x1.3333333333333p-2. Builder/owned-reader:
  0x1.3333340000000p-2 (0.30000001192092896), exact builtin float.
  This is observed rounding, not lossless binary64 identity. The independent
  IEEE logical word3e99999a remains a reference, not direct wire-bit extraction.
- Negative zero remains -0x0.0p+0. +/-1,2^-149 and2^-126 survive assignment and
  owned serialization in this pinned environment.
- NaN/+inf/-inf survive; finite1e39 becomes +inf at assignment. These observations
  do NOT make such values admissible to the pure model or F61.
- With an actuators pointer allocated in both cases, omitting torque/latActive
  vs explicitly writing0.0/False yields identical bytes and readback. _has on
  latActive returns True for BOTH. Independent construction ledgers differ.
  Therefore neither value/default nor this presence method proves explicit supply.
- Accessing a nonexistent field inside the live owned context raises builtin
  AttributeError. No use-after-context/native-memory-lifetime experiment is run.

Ten Float32 fixtures, two default-construction cases and one paired CC/CS schema
observation form the fixed experiment. No model or original source module runs.
The CS message is a bare CarState, NOT an actual CS.out wrapper/call snapshot.

OBSERVATIONS.json SHA256:
b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74.
Process-specific paths/runtime receipts are separate; only observations are
claimed byte-identical. Receipts identify observed loaded files, not OS trust.

## Qualification limits and next work

Q01 artifact/process identities observed; Q02 generic schema types/owned read
observed, general lifetime NOT_QUALIFIED. Q03 default ambiguity established;
Q04 fixed synthetic readback observed. Q05 coherent entry snapshot/settings/prior
state/concurrency custody NOT_QUALIFIED. Q06 native reader NOT_IMPLEMENTED and
activation NOT_ALLOWED. No native profile or acceptance API is created.

Next bounded development work: specify an owned-message/explicit-field-ledger
boundary and same-synthetic-frame settings/prior-state contract; fail closed on
wrong schemas or missing ledger. This is not an observer, actual-input adapter,
runtime installation, vehicle custody or automatic domain widening.

## Opt-in reproduction (separate environment only)

From tools/cyberlateral_dev, use NEW task paths. Network is only for bootstrap;
the qualifier itself has no network/install/data-input mode.

```bash
r19_workspace=$(mktemp -d /tmp/cyberlateral-r19-XXXXXX)
uv venv --python 3.12.13 "$r19_workspace/native-env"
uv pip install --python "$r19_workspace/native-env/bin/python" --require-hashes --no-deps --only-binary :all: -r native_qualification/requirements.txt
curl --fail --location https://files.pythonhosted.org/packages/63/9d/18e978500d5f6bd8d152f4d6919e3cfb83ead8a71c14613bbb54322df8b9/pycapnp-2.1.0-cp312-cp312-manylinux_2_28_x86_64.whl --output "$r19_workspace/pycapnp.whl"
uv run --locked python -B native_qualification/run.py --python "$r19_workspace/native-env/bin/python" --wheel "$r19_workspace/pycapnp.whl" --output "$r19_workspace/result"
```

From the result directory, run the absolute path to
native_qualification/test_observations.py with the native interpreter -I -B -v;
then sha256sum -c SHA256SUMS.txt. The qualifier runs two fresh workers internally.
Wrong runtime/hash/installed bytes fail before native import. Existing output
or dangling output symlink rejects without spawning. A failed run is not evidence.

Ruff/Ty/Codespell must also be run explicitly on native_qualification; the default
pure CI intentionally does not execute or install this opt-in dependency.

## Unchanged gates

Public0.3.0 wheel SHA256 remains
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
Controller/Runtime/CAN/F61 execution=0; actual input/model work/r/dt by this tool=0.
Candidate/Runtime=NO_GO; SOURCE_SCHEMA_UNQUALIFIED=6000;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
Native GitHub CI=NOT_RUN. Existing pure regression CI is a separate gate.
