# CyberLateral development module V1 — offline trace report0.3.0

Distribution cyberlateral-dev0.3.0 provides a pure, reusable synthetic calculation
API. No NumPy, original helper loader, vehicle runtime or network dependency ships
in the wheel. Tested/supported CPython3.12.13 only. This is not vehicle deployment.

## Build and use

From the delivered workspace root, using CPython3.12.13:

```bash
python -B tools/build_wheel.py --output new-dist
uv venv --python 3.12.13 new-dev-env
uv pip install --offline --no-deps --python new-dev-env/bin/python new-dist/cyberlateral_dev-0.3.0-py3-none-any.whl
```

```python
from cyberlateral_dev import LateralInput, Limits, initial_state, step

sample = LateralInput(0, 0.3, 0.0, 0.0, True, Limits(5, 5, 5, 0, 1, 1), "SYNTHETIC_ONLY")
result = step(sample, initial_state())
assert result.projection.integer_command == 2
assert result.projection.normalized_expression_hex == "0x1.999999999999ap-2"
assert result.projection.torque_float32.bits_hex == "3ecccccd"
state_for_next_call = result.next_state
```

## Run the installed offline consumer

```bash
new-dev-env/bin/python -I -B -m cyberlateral_dev --output new-simulation-results
```

This runs a CLOSED catalog of7 synthetic scenarios/112 model steps and writes
new-simulation-results/simulation.json. Without --output, stdout is canonical JSON.
An existing file/directory/dangling link is rejected before model work. Ordinary
no-overwrite guards are not race-free or atomic snapshot protection. The CLI has
no data/log/source-root/runtime/install/capture mode. It needs no original sources,
NumPy, external fixture files, network or hardware. Scenario constants are explicitly
DEVELOPMENT_FIXTURE_NOT_POLICY, never actual scale/r/T2.

For a reusable pure batch, call simulate(samples_tuple, explicit_state), exported
alongside step. Return fields are outputs (immutable tuple) and next_state. Resume
by supplying next_state and adjacent-index samples; no implicit reset. Exact tuple
length1..4096 required. A later invalid sample raises without a partial returned
result or mutation of supplied input/state. It is command-state calculation, not
a vehicle-dynamics, closed-loop perception, F61-feasibility or safety simulation.
Invocation indices are not elapsed time or a policy conversion period.

The scope label is not a certificate of arbitrary input origin. The supplied API
is bounded synthetic development software; no production/actual-data context mode.
Input/state/explicit scale rules remain those of R4; no defaults, clamp or r/T2
fallback. Call step(sample,state), then pass returned next_state to the next sample.

## View the offline trace report

```bash
new-dev-env/bin/python -I -B -m cyberlateral_dev --report --output new-trace-report
```

Open new-trace-report/index.html locally. No server, JavaScript, external assets,
network, or original source files needed. --report requires a NEW output directory.
The5-file bundle includes simulation.json, analysis.json, trace.csv, index.html,
and REPORT_SHA256SUMS.txt. The plain CLI mode above remains compatible.

The Korean page shows7 synthetic scenarios,14 SVG figures and112 invocation rows.
Command plots compare integer request, previous applied, limited and final command;
normalization plots show requested and returned expressions. Summary counts separate
combined limiter adjustment19, inactive calls2/changed commands2 and active fault
request suppression2. These are descriptive events, not performance/feasibility
scores. Fault suppression does not zero active torque. No driver-versus-rate cause
is inferred from the combined adjustment flag.

X=model invocation index, NOT seconds or10ms. Y=synthetic command units, NOT physical
torque. Integer command differences are NOT per-second rates or policy budgets.
History normalization19.0 is retained and autoscaled, not clipped to[-1,1].
SVG pixel coordinates use3 display decimals only; CSV19 columns and JSON retain
exact hex/word values. Table cells also show readable normalized values. Spreadsheet
CSV type inference is not controlled; JSON/hex is authoritative. Internal analysis/
render helpers consume package-built fixed catalog, not a general file intake or
input-authentication API. Synthetic labels never certify arbitrary provenance.

## Output layers

- projection.integer_command: final post-inactive integer command, NOT CAN bytes.
- normalized_expression: builtin binary64 command/explicit current scale, before
  actual actuator assignment. It may exceed[-1,1] with mismatched history/scale.
- torque_float32 and torque_output_can_float32: IEEE754 binary32 numeric-word
  simulations for BOTH declared Float32 schema fields. bits_hex is canonical
  big-endian numeric notation, NOT actual Cap'n Proto or CAN serialization.
- steer_request/next_state/trace: retain inactive versus fault semantics and
  integer history. Normalization does not undo lossy input quantization.

Actual schema builder/accessor/ABI/wire and mutable production snapshot behavior
are not established. Source comments are not runtime range validation. Controller
or schema is never imported/compiled/executed by this package. No actual vehicle,
Runtime/CAN/F61/Adapter integration or safety/performance certification is claimed.
Original-derived notices ship in wheel dist-info/licenses; no license-policy change.
The prior0.1.0 License-File path-prefix error is fixed; each declaration resolves
to the corresponding preserved notice in the wheel and installed metadata.

## Development verification

The external project/ tree retains30 R4 source/test files unchanged plus new
development reference/tests. Seven private package modules differ only in relative
imports, with AST/provenance proof. Original-helper comparisons use the old pinned
NumPy2.5.3 development environment, not a package runtime dependency:

```bash
/workspace/cyberpilot-helper-arithmetic-85zkPB/.venv/bin/python -B -m unittest discover -s project -v
```

For another machine use an equivalent pinned CPython3.12.13/NumPy2.5.3 DEV environment
for the reference suite; an empty runtime venv is sufficient for the installed API.
The complete fixed-catalog validation runner (new output directory only) is:

```bash
python -B project/run_module_v1.py --controller reference/carcontroller.py --helper reference/lateral.py --schema reference/car.capnp --output new-results
```

It compares150 direct output ratios,19 standalone codec vectors and224 independent
state trajectories (2802 calls). Only the old two helper definitions run in this
development reference; the package calls them zero times. No user dataset mode.
No old environment/repository/evidence changes, Git/Push/CI or publishing performed.
Actual r/T2/vehicle scale remain null, R_BUDGET UNRESOLVED, Static Gate FAIL,
Candidate/Runtime NO_GO and actual activation/F70UH/F70V/F71 NOT_ALLOWED.
