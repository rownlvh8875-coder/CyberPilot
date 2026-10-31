# CyberLateral — isolated offline development

CyberLateral0.3.0 is a pure synthetic command/state calculation package, imported
byte-for-byte from the verified R7 evidence. It is now maintained as a standalone
development project in CyberPilot. It is NOT an openpilot controller, vehicle
installation, physical simulator, F61 invocation or safety/performance approval.

R19 adds an explicitly opt-in [native-message observation experiment](
docs/NATIVE_MESSAGE_QUALIFICATION_R19.md), not a native adapter. It uses a separate
pycapnp environment and only internally constructed synthetic messages. The
default command below remains pure; the package/lock/wheel remain unchanged.
See [observations and reproduction](docs/NATIVE_MESSAGE_QUALIFICATION_R19_RESULTS.md).

R20 adds a [pure owned-message envelope boundary](docs/OWNED_MESSAGE_BOUNDARY_R20.md)
and an explicit --owned-boundary native demonstration. It preserves immutable
bytes/field ledgers/settings/prior declarations, but does NOT parse arbitrary
messages, authenticate call custody or create model/F61 inputs. See
[R20 results and reproduction](docs/OWNED_MESSAGE_BOUNDARY_R20_RESULTS.md).

## One-command verification

Install [uv](https://docs.astral.sh/uv/)0.12.23. From the repository root:

```bash
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/dev.py verify --output tools/cyberlateral_dev/out/verify-1
```

The output must be a NEW path. Use verify-2 for a later run; existing files,
directories and dangling links are rejected without numerical work or overwrite.
Bootstrap downloads the pinned CPython3.12.13 and DEV dependencies if necessary;
the installed-wheel/report comparisons themselves are offline. No root openpilot
dependencies, submodules, LFS models, Docker or hardware are needed.

Verification runs the full component test suite, static checks and own-code
in-memory compilation; checks exact imported identities; builds the wheel twice;
installs the local wheel into an empty temporary environment without dependencies;
compares two isolated report runs and two fixed numerical reference runs. Output
contains logs, wheel, reports, checksums and SUMMARY.json. No environment/cache
payload is included. Do not interpret descriptive counts or CI PASS as vehicle safety.

The R9 gate also runs a DEV caller harness twice against the installed wheel:
seven fixed scenarios/112 model invocations,105 internal two-chunk splits,
single-step chaining, round-robin independent caller states and11 exact rejection
cases. `harness_one/RESULTS.json` records every output/state and acceptance check;
the harness directories and their checksums must match byte-for-byte. Golden
hashes come from the validated R8 report: regression snapshots, NOT a new
independent numerical oracle. Existing independent arithmetic tests still run.
There is no external data/log input mode, state persistence protocol or production
adapter. Invocation order is not elapsed time; actual r/T2/vehicle scale stay null.
The acceptance gate verifies full result hashes, fixture identity, exact rejection
records and unchanged safety gates, not just PASS labels/counts. `RESULTS.json` is
published last after complete staged writes; failed output directories are not
successful evidence. Ty uses explicit component `ty.toml`, without inheriting
openpilot's generated-ABI import/attribute suppressions.

R10 closes the targeted caller-state test gap: split-only history resets and
round-robin-only cross-caller history leakage preserve all whole-batch/isolated
step golden controls, yet must fail at their dedicated harness comparisons.
Each test was also run with just its comparison temporarily bypassed: it failed
as intended, then passed after exact source restoration. See
[state mutation coverage](docs/STATE_MUTATION_COVERAGE.md). This is tests-only;
the package, wheel, fixed fixtures and R9 harness contract remain unchanged.

R11 adds a [source-backed DEV bridge design](docs/OPENPILOT_DEV_BRIDGE_DESIGN.md),
[pinned source map](docs/OPENPILOT_DEV_BRIDGE_SOURCE_MAP.json) and
[implementation plan](docs/OPENPILOT_DEV_BRIDGE_IMPLEMENTATION_PLAN.md).
Those documents preserve the historical R11 design-only state; R12 implements
that design below, without making it a live CC/CS reader, runtime hook or F61 adapter.

R12 adds the [fixed-fixture DEV bridge](docs/DEV_BRIDGE_R12.md) in
`integration_tools/dev_bridge.py`. Frozen snapshot/session/result records preserve
source-shaped names, exact builtin binary64 bits and explicit caller state.
`fixture_snapshot(id, offset, sequence_id)` and `begin_sequence(id, sequence_id)`
only select existing fixed fixtures; `advance(snapshot, session)` rejects arbitrary
objects/metadata/domains, out-of-order calls, payload changes and incorrect state.
Trusted-prefix validation is additional model work, NOT an independent oracle.
No source/message reader, arbitrary-input mode, timestamp, dt, r or policy input
exists. A deterministic retry of the original immutable pair is allowed; replay
prevention, persistence and concurrency management are not provided.

The one-command gate now also runs `dev_bridge_probe.py` twice under -I/-B in the
empty installed-wheel environment. `bridge_one/RESULTS.json` and `bridge_two`
contain all7 scenarios/112 NEW current transitions, complete diagnostics, final
sessions, source-profile labels and unchanged gates. Both outputs must byte-match;
the verifier separately validates every frozen full-result hash, session, gate and
checksum. Profiles/labels are not input provenance authentication. The runtime
wheel remains the sealed0.3.0 artifact with no DEV bridge code or dependencies.

R13 adds an [offline message-boundary design](docs/OPENPILOT_MESSAGE_BOUNDARY_DESIGN.md),
[machine-readable contract](docs/OPENPILOT_MESSAGE_BOUNDARY_CONTRACT.json),
[future test specification](docs/OPENPILOT_MESSAGE_BOUNDARY_TEST_SPEC.md) and
[future extraction plan](docs/OPENPILOT_MESSAGE_BOUNDARY_IMPLEMENTATION_PLAN.md).
Those documents preserve R13's design-only history. They separate source-backed
fields/declared synthetic custody from unverified native Float32/default/presence/
lifetime behavior. Native qualification stays closed; R12 remains unchanged.

R14 implements the [pure synthetic extractor](docs/MESSAGE_BOUNDARY_R14.md): seven
immutable nested carriers and `extract_synthetic_message(frame)`, which validates
then copies public sample/state without model transitions or state repair. The28
synthetic cases B01-B28 now run, giving215 tests with the existing187. Native Q01-Q06
are still NOT_AUTHORIZED/NOT_RUN, not passing tests. No actual CC/CS reader exists.

The gate additionally runs `message_boundary_probe.py` twice under -I/-B with the
installed unchanged wheel. `message_boundary_one/RESULTS.json` contains four fixed
prepared inputs and exact float.hex/state/claim/gate records, checked in full
against hand-authored literal expectations, not just matching checksums/counts.
Previous integer candidate is model bookkeeping/declaration-only, not history
proof; supplied signed-zero/binary64 bits remain intact. No F61/r/time API is added.

R15 adds a separate [fixed handoff runner](docs/MESSAGE_HANDOFF_R15_DESIGN.md) and
[implementation plan](docs/MESSAGE_HANDOFF_R15_PLAN.md): nested synthetic frames ->
unchanged R14 extraction -> exact prepared-input/state check -> pure model step ->
owned continuation. It covers7 scenarios/112 synthetic steps per process, with0
prefix recomputation. R14 itself remains copy-only with0 model transitions.
`handoff_one/RESULTS.json` records complete source/frame/prepared/result traces.
The acceptance gate anchors input identity and results to the existing frozen
catalog/goldens, then reconstructs every expected frame/prepared state from them.
The history-scale seed is declared, NOT observed prehistory; later state ownership
only describes this synthetic run. No native/vehicle/rate-policy qualification.

R16 adds a [closed lifecycle runner](docs/MESSAGE_HANDOFF_LIFECYCLE_R16_DESIGN.md)
and [plan](docs/MESSAGE_HANDOFF_LIFECYCLE_R16_PLAN.md) over the same message-to-model
advance: all105 interior split/resume points and112 round-robin stream events.
Complete frames/prepared values/results must match the existing frozen baseline;
the installed `lifecycle_one/RESULTS.json` and `lifecycle_two` include all split
certificates and interleaved events, independently checked against that baseline.
Each lifecycle process uses9010 synthetic extractions/model steps including the
baseline and all splits, with0 prefix validation calculations; this is not an
aggregate test count or elapsed-time/rate/performance claim. R15 output bytes,
R14's copy-only behavior, package0.3.0, goldens and gates remain unchanged. This
does not add arbitrary input, persistent checkpoint/replay or native qualification.

R17 adds [read-only audit tables](docs/HANDOFF_AUDIT_R17_DESIGN.md) from the exact
validated R16 pair: `audit_one/audit.csv` has112 rows/37 scalar columns spanning
request, explicit settings, owned previous state, separate limiting stages and
next state. `AUDIT.json` retains typed values/source hashes/gates, and
`SUMMARY_KO.md` summarizes the seven synthetic scenarios in Korean. Signed zero
and binary64 hex/null are explicit; spreadsheet display may coerce numbers.
Two isolated report processes load no model/native/NumPy modules and perform0
extractions/model steps/F61/r/dt calculations. The source's9010 calls are labeled
separately. This is a fixed-evidence projection, not arbitrary log intake, a new
model run or an independent mapping/numerical oracle. Complete table mappings
are tested against raw source fields; paired artifacts are checked in full.
`AUDIT.json` is published last, after all report/checksum writes succeed.

R18 adds a [portable data-only bundle](docs/AUDIT_BUNDLE_R18_DESIGN.md):
`bundle_one/F70UGZ_R18_AUDIT_BUNDLE.zip` contains exactly17 files (R16/R17 pair
data14 plus metadata/Korean README/16-entry Manifest). No executable code/wheel
or installer is included. Keep the ZIP and its external .sha256 for notebook
storage. Validation needs this repository's trusted tools, not a bundled signature:

```bash
python -I -B tools/cyberlateral_dev/integration_tools/audit_bundle.py verify --bundle YOUR_ZIP_PATH
```

The verifier checks exact names/CRC/hashes/frozen contracts and canonical ZIP
bytes, with8MiB archive/total and4MiB member limits. It never uses extractall or
runs archive members; only hardcoded data enters private validation temps. Stored
ZIP/sorted paths/regular modes/fixed1980 format time make full ZIP bytes repeatable;
that time is not an observed sample/creation/vehicle time. Two isolated exports
and two isolated read-only verifications add0 model/extractor/F61/r/dt work.
The final ZIP is published last after receipts. Source/goldens/runtime/gates
remain unchanged; this is consistency, not origin authentication or activation.

The dev environment intentionally does not install the wheel-only project as an
editable package (`tool.uv.package=false`). Test source selectors are DEV-only.
The actual package installation is verified in an isolated child environment.

## Build and use separately

```bash
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/build_wheel.py --output new-dist
uv venv --python 3.12.13 new-runtime-env
uv pip install --offline --no-deps --python new-runtime-env/bin/python new-dist/cyberlateral_dev-0.3.0-py3-none-any.whl
new-runtime-env/bin/python -I -B -m cyberlateral_dev --report --output new-trace-report
```

Open new-trace-report/index.html locally. The five-file report has7 scenarios,
112 rows,14 SVG figures, exact19-column CSV and canonical source/analysis JSON.
Without --report the module CLI emits only canonical simulation JSON. No arbitrary
data/log/source-root/runtime/capture/install mode exists. The runtime wheel has
ZERO third-party dependencies; NumPy is only for DEV original-helper comparisons.

```python
from cyberlateral_dev import LateralInput, Limits, initial_state, step

sample = LateralInput(0, 0.3, 0.0, 0.0, True, Limits(5, 5, 5, 0, 1, 1), "SYNTHETIC_ONLY")
result = step(sample, initial_state())
assert result.projection.integer_command == 2
```

`simulate(samples_tuple, explicit_state)` supports bounded1..4096 synthetic calls,
immutable output/state and explicit resume. The label is NOT input attestation.
No state/r/T2/vehicle-scale fallback is introduced. Command normalization may
exceed[-1,1] with mismatched synthetic history/scale (95/5=19.0); no hidden clamp
or inverse-quantization claim. Binary64 quotient and Float32 numeric projections
remain separate; neither is actual Cap'n Proto or CAN wire bytes.

## Source/provenance boundary

IMPORTED_ARTIFACT.json records the original R7 ZIP identity, each unchanged imported
source/test/license/fixture hash and the expected wheel hash. No historical evidence
ZIP, personal logs or old virtual environments are committed. The three reference
fixtures are DATA/AST authority only. Original Controller/schema are never imported,
compiled as executable code or run; only two exact helper function bodies execute
in development reference comparisons, not in the installed package.

X-axis is model invocation order, NOT seconds,10ms or actual control timing. Delta
is an integer difference, NOT rate_budget_per_s. Limiter/inactive/fault-request
events are separate. No physical dynamics, actual r calculation, candidate ranking
or F61 feasibility result is provided. Browser visual verification was not
established in the source evidence; data/DOM/SVG checks do not prove visual quality.
Original inherited documentation is retained as reference/r7_README.md; its old
workspace-specific paths are historical and not required by this project.

## CI and pull requests

The dedicated workflow `.github/workflows/cyberlateral-dev.yaml` only checks this
standalone project, with no vehicle/native setup. It bootstraps pinned development
tools, then runs the same command above. Existing repository PR workflows can
build/replay openpilot; they are NOT the offline gate and are not modified here.

For this integration, the implementation branch is push-tested before PR creation.
A tree-identical `[skip ci]` guard commit suppresses legacy PR/push tests, then a
DRAFT PR is opened. Tested code SHA/tree and guarded head SHA are reported separately.
An explicit dispatch of the new safe workflow is attempted on the guarded head;
GitHub may require workflow registration/default-branch availability. Never claim
a head check passed merely because the previous identical tree passed. Do not
merge automatically or enable legacy runtime CI to satisfy this offline gate.

## Unchanged production gates

Actual r/T2/vehicle scale=null. R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL;
Candidate/Runtime=NO_GO; actual activation/F70UH/F70V/F71=NOT_ALLOWED;
SOURCE_SCHEMA_UNQUALIFIED=6000; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN.
No vehicle deployment or policy approval follows from repository integration.
