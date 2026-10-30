# CyberLateral — isolated offline development

CyberLateral0.3.0 is a pure synthetic command/state calculation package, imported
byte-for-byte from the verified R7 evidence. It is now maintained as a standalone
development project in CyberPilot. It is NOT an openpilot controller, vehicle
installation, physical simulator, F61 invocation or safety/performance approval.

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
[future implementation plan](docs/OPENPILOT_DEV_BRIDGE_IMPLEMENTATION_PLAN.md).
This proposes typed, fixed-fixture-only source-shaped records, not a live CC/CS
reader, runtime hook or F61 adapter. No bridge implementation is included yet;
state, binary64/Float32, time and vehicle-policy boundaries are kept explicit.

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
