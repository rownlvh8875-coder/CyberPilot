# CyberLateral — isolated offline development

For the fixed R56 implementation baseline, see the separate
[Korean path/cache troubleshooting supplement](docs/OFFLINE_HARDENING_R56_KO.md).
It complements, not replaces, the historical guide and source inventory below.

CyberLateral0.3.0 is a pure synthetic command/state calculation package, imported
byte-for-byte from the verified R7 evidence. It is now maintained as a standalone
development project in CyberPilot. It is NOT an openpilot controller, vehicle
installation, physical simulator, F61 invocation or safety/performance approval.

Start with the [current Korean offline workflow guide](docs/OFFLINE_QUICKSTART_CURRENT_KO.md)
and [reviewed source capability map](docs/OFFLINE_CAPABILITY_INVENTORY_CURRENT.json).
They distinguish the installed fixed-catalog wheel CLI from the separate custom
scenario tools below. Static availability is not a fresh execution or vehicle verdict.

The [R37 validation-only mode](docs/SCENARIO_VALIDATION_R37_KO.md) checks declared
synthetic input without model imports/execution or result files. Input acceptance
is not model/source/runtime qualification or authenticated origin.

The separate [R38 saved-scenario reference checker](docs/SCENARIO_REFERENCE_R38_KO.md)
compares complete R31 records with the existing independent selected-source
reference in a fresh worker. It does not rerun the public model; reference/helper
arithmetic is explicitly NONZERO. Exact agreement is bounded synthetic parity,
not whole-controller, input-origin or vehicle qualification. Portable subsets
are not complete inputs for this checker.

The separate [R39 saved-batch reference checker](docs/SCENARIO_BATCH_REFERENCE_R39_KO.md)
applies existing R38 references to every complete case in a validated owned R33
snapshot. It distinguishes confirmed input rejections, unavailable raw inputs,
numerical differences and reference errors in one JSON/Korean summary. It does
not rerun the public model; reference/helper work is NONZERO. Rejected-only or
unverifiable batches never become vacuous numerical MATCH results.

Custom declared-synthetic JSON files can now be run with the separate
[R31 developer scenario CLI](docs/SYNTHETIC_SCENARIO_CLI_R31_KO.md) for full JSON/CSV
traces. It preserves the public0.3.0 model/wheel; it is not a vehicle/log reader.

Multiple explicitly named JSON files can be run independently with the
[R33 synthetic batch CLI](docs/SCENARIO_BATCH_R33_KO.md), producing one static
index of per-file results, input rejections and existing individual reports.
State never crosses files; completion is not numerical or vehicle approval.
Its [bounded local visual acceptance](docs/SCENARIO_BATCH_R33_RESULTS.md) covers
the success/mixed/rejected lists and two linked reports at desktop/mobile sizes;
[receipts and screenshot hashes](docs/evidence/r33-visual-acceptance/README_KO.md)
preserve the scope. This does not qualify arbitrary scenarios or vehicle use.

Two complete saved R33 batches can be checked with the separate
[R34 exact regression comparison CLI](docs/SCENARIO_REGRESSION_R34_KO.md).
It reports changed inputs, command/state/trace fields, rejection outcomes and
producer identity changes without rerunning the model. MATCH is recorded-value
equivalence, not an independent numerical oracle or vehicle approval. Portable
sharing subsets are not complete input bundles; no baseline auto-update exists.

The [R35 fixed synthetic regression pack](docs/SYNTHETIC_REGRESSION_PACK_R35_KO.md)
adds six hand-authored scenarios/38 samples and three expected input rejections.
Separate literal checks cover selected numerical/state boundaries before saved-byte
comparison; no new CLI, public-model change or vehicle qualification is implied.

Saved R31 outputs can be checked and viewed with the separate
[R32 read-only HTML scenario report](docs/SCENARIO_REPORT_R32_KO.md).
It displays graphs/state tables without importing or rerunning the model;
checksum consistency is not origin authentication or independent numerical proof.
The [R32.2 mobile readability correction](docs/SCENARIO_REPORT_R322_RESULTS.md)
passed the two-report desktop/mobile visual check; [evidence receipts and hashes](
docs/evidence/r322-visual-acceptance/README_KO.md) preserve its bounded scope.
This is not vehicle, arithmetic, performance or deployment approval.

The separate [R70 recorded trace summary](docs/RECORDED_TRACE_SUMMARY_R70_KO.md)
prints JSON or Korean Markdown from complete saved R31 records. Exact numeric
changes stay separate from scalar-kind/signed-zero representation changes; events
can overlap and first indices are declared sample indices, not elapsed time.
It validates captured record consistency without model/reference execution,
limiter arithmetic replay, source-origin authentication or vehicle/policy approval.

The [DEV F61 signal Adapter V4](docs/F61_SIGNAL_ADAPTER_V4_KO.md) integrates the
previously sealed synthetic request-to-request projection, with its independent
test-only IEEE oracle. It preserves exact values and explicit pair-local times;
it does not accept vehicle input, construct F61 requests, select a rate policy or
invoke the calculator. The [core development backlog](docs/CORE_DEVELOPMENT_BACKLOG_KO.md)
maps current code to confirmed requirements and separates the remaining binding,
rate-policy and vehicle gates from offline development work.

The [CORE2 observation-to-V4 reconciliation](docs/F61_OBSERVATION_BINDING_CORE2_KO.md)
covers all41 V4 leaf fields and35 observation roles. It records incompatible source
profiles and missing request-stage flags/reset/context explicitly; this static
draft does not implement a bridge, relabel observations, change V4 source pins or
authorize actual inputs. Its design obligations are not executed runtime tests.

The [CORE3 counterfactual request snapshot boundary](docs/REQUEST_SNAPSHOT_CORE3_KO.md)
preserves explicit raw binary32 requests, flags and context in immutable carriers.
Its pair factory checks exact types, context, adjacent sequence, time order and
declared reset without model/native/time-delta computation. This is not real source
capture, state/settings binding, a V4 bridge or calculator/vehicle authorization.

The [CORE4 declared limiter snapshot boundary](docs/LIMITER_SNAPSHOT_CORE4_KO.md)
adds separate integer limited-state/counter and consumed-settings declarations to
CORE3 requests. It checks prior-saved/current-entry links, stable settings and a
separate inactive-gate flag without running limiter arithmetic. Its result is not
model input, source-consumption proof or V4/F61/vehicle authorization.

The [CORE5 current synthetic model input](docs/SYNTHETIC_MODEL_INPUT_CORE5_KO.md)
adds required driver/angle/model-index/previous-integer-request declarations and
maps an explicitly compatible CORE4 pair into the unchanged public model types.
It checks previous request quantization and rejects incompatible active reads or
overrides. It does not execute transitions, validate declared saved outputs,
authenticate actual settings or authorize V4/F61/vehicle input.

The [CORE6 current synthetic transition check](docs/SYNTHETIC_TRANSITION_CORE6_KO.md)
runs CORE5 preflight and exactly one public synthetic step, then compares the
current declared post-gate saved command and angle counter. It returns MATCH or
explicit DIFFERENT fields without overwriting declarations. This is not previous
transition/prehistory/full-output parity or actual-source/V4/F61/vehicle approval.

The [CORE7 declared synthetic sequence check](docs/SYNTHETIC_SEQUENCE_CORE7_KO.md)
preflights all adjacent inputs and explicit model indices before any public step,
then retains every CORE6 diagnostic, including those after a difference. It uses
declared entry states without repair or computed-state rollout. Empty or malformed
sequences cannot pass; the anchor/prehistory and actual-source/vehicle gates remain unqualified.

The [CORE8 closed sequence CLI](docs/CORE_SEQUENCE_CLI_CORE8_KO.md) runs the named
sign-cycle, declared-difference and late-invalid examples through CORE7 and saves
canonical input/results/checksums to a new outside-checkout folder. Exit0/1/2
distinguishes MATCH/DIFFERENT/input rejection; operational failures are not zero-work
success. It accepts no external vehicle/log/JSON/rate input and grants no vehicle authority.

Historical R30 snapshot: [original acceptance guide](docs/OFFLINE_ACCEPTANCE_R30_KO.md)
and [original source inventory](docs/OFFLINE_CAPABILITY_INVENTORY_R30.json).
Their recorded counts and prospective features describe R30, not current DEV-tool
availability. These files and the historical stage descriptions retain their
original scope; the current guide above covers R31–R48, including cloud-only
recovery, two-seed campaigns, saved comparison and the read-only comparison report.
Its inventory hashes describe a pinned reviewed commit, not a fresh execution verdict.

The separate [R40 integrated synthetic workflow](docs/SCENARIO_WORKFLOW_R40_KO.md)
connects input validation, batch execution and existing graphs, independent batch
reference checking, and optional saved-batch regression in one DEV command.
It snapshots readable inputs and an optional complete baseline before model work,
keeps mixed input rejection visible as exit1, and never treats rejected-only input
as numerical success. Model/reference work is NONZERO and reported separately;
the unchanged public wheel and all closed vehicle gates remain unchanged.

The [R41 combined-boundary and longer-sequence pack](docs/SYNTHETIC_REGRESSION_PACK_R41_KO.md)
adds three fixed synthetic scenarios/324 invocations through this same workflow.
Hand-derived selected literals and full selected-source parity cover interacting
driver/rounding/sign/inactive boundaries and repeated state/fault-counter cycles.
Coherent wrong saved histories must be detected; no new model/API, elapsed-time
claim, actual rate policy or vehicle activation is introduced.

The separate [R42 deterministic synthetic boundary explorer](docs/SCENARIO_EXPLORATION_R42_KO.md)
generates bounded seed-based R31 inputs, runs the existing R40 independent checks,
and preserves complete inputs for every nonmatching case. Input feature counts
are not exhaustive branch coverage; this does not alter the public0.3.0 model,
select a vehicle rate policy or authorize actual vehicle inputs/activation.

The separate [R43 multi-seed synthetic campaign](docs/SCENARIO_CAMPAIGN_R43_KO.md)
runs one to four explicit unique R42 seeds in order, validates every complete child
record/manifest, and retains all numerical differences and reference errors with
whole reproducers. State never crosses seeds/cases. A completed ERROR outranks a
numerical DIFFERENT; fatal/changed/incomplete evidence never gets a final campaign
marker. No new model/oracle, minimization, rate policy, upload or vehicle authority.

The separate [R44 saved-campaign comparator](docs/SCENARIO_CAMPAIGN_COMPARISON_R44_KO.md)
compares two complete R43 V1 campaigns in saved seed/case order, reusing R34 exact
recorded-value checks without new model/reference execution. Source ERROR and
DIFFERENT remain visible even when identical failed records compare equal. Identity
changes are separate from value changes; this is not a new numerical oracle,
automatic baseline update, upload or vehicle qualification.

The separate [R46 saved comparison report](docs/SCENARIO_CAMPAIGN_REPORT_R46_KO.md)
opens complete R44 V1 results as escaped, responsive Korean HTML. It checks closed
hashes and saved-record consistency, not the original comparison truth. Overall
source ERROR/DIFFERENT and equal-record regression MATCH stay separate. No new
model/reference work, original campaign reads or policy/vehicle authorization.

R28 provides a [controlled internally constructed synthetic native adapter](docs/NATIVE_ADAPTER_R28.md).
R29 connects it to the unchanged model for [two fixed state-carry profiles](docs/ADAPTER_SEQUENCE_R29.md).
Neither is a generic external message reader, authenticated vehicle history or
F61/production activation. Native work remains separate opt-in; default CI is pure.

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

R21 adds a [declared-readback semantic bridge and independent oracle](docs/SEMANTIC_BRIDGE_R21.md).
It prepares unchanged0.3.0 synthetic input/state records without running the model
or F61. Its explicitly selected native experiment also requires the exact public
wheel in a separate environment; default R19/R20 and pure CI remain unchanged.
See [R21 results](docs/SEMANTIC_BRIDGE_R21_RESULTS.md).

R22 adds [five preregistered fixed single-step consumptions](docs/MODEL_CONSUMPTION_R22.md)
of the unchanged public model, explicitly selected with --model-consumption.
Complete input and output must match independent SHA-pinned literals; it is not
a general native adapter, sequence replay, F61 invocation or vehicle activation.
R19/R20/R21 retain their original zero-new-model-work behavior.
See [R22 results and reproduction](docs/MODEL_CONSUMPTION_R22_RESULTS.md).

R23 adds [one fixed native/model sequence](docs/NATIVE_SEQUENCE_R23.md), explicitly
selected with --model-sequence. Four synthetic steps carry the preceding verified
model output state; complete preregistered literals check sign changes and inactive
gating. Parent coverage/count validation also closes R22's deferred M1 without
changing old observation bytes. See [R23 results](docs/NATIVE_SEQUENCE_R23_RESULTS.md).

R24 adds [fixed fault/reset boundaries](docs/FAULT_RESET_R24.md), explicitly selected
with --fault-boundaries:99 preregistered synthetic native/model steps across the
request-suppression window, below85 reset and inactive reactivation. Auxiliary
claim validation also closes R23-M1 without changing old observations. A separately
preregistered v2 preserves the original96-call prefix and adds nonzero-counter
deactivation/reactivation coverage identified by review. This is
model behavior, not a physical safety recommendation. See [R24 results](docs/FAULT_RESET_R24_RESULTS.md).

R25 adds [fixed negative-angle/driver interactions](docs/NEGATIVE_DRIVER_R25.md),
explicitly selected with --driver-boundaries:20 preregistered steps retain
fractional driver bounds, direction-sensitive rate limits, nearest-even rounding
and nonzero inactive state reset. Summary reference labels now come from validated
observations; a correction receipt preserves the known R24 summary-label error
without rewriting old evidence or changing numerical results. Public0.3.0 is
unchanged; this is neither a general driver sweep nor physical safety validation.
See [R25 results and correction scope](docs/NEGATIVE_DRIVER_R25_RESULTS.md).

R26 adds [one fixed negative-angle full cycle](docs/NEGATIVE_CYCLE_R26.md),
explicitly selected with --negative-cycle:99 preregistered steps qualify the
89/90/91/92-call request boundary, below-negative85 reset and nonzero inactive
reset/reactivation while retaining fractional driver trace kinds. It does not
broaden accepted external inputs, infer elapsed time or authorize vehicle use.
See [R26 results and reproduction](docs/NEGATIVE_CYCLE_R26_RESULTS.md).

R27 adds a separate [complete fixed native suite](docs/NATIVE_SUITE_R27.md).
It runs all eight R19–R26 profiles, checks exact retained observation identities,
numerical contracts, source hashes and manifests, and publishes one bounded
Korean/JSON report only after all pass. Missing/contradictory records, late
corruption and output collisions fail closed; SUITE_SUMMARY.json is published last.
The default pure command/CI below still does NOT run native qualification.

From tools/cyberlateral_dev, after preparing the existing separate pinned native
environment and the exact native/public wheels:

```bash
uv run --locked python -B native_qualification/suite.py --fixed-native-suite --python /absolute/native-env/bin/python --wheel /absolute/pycapnp.whl --package-wheel /absolute/cyberlateral_dev-0.3.0-py3-none-any.whl --output /absolute/NEW-suite-output
```

The output parent must exist. This command neither installs dependencies nor
accepts stage subsets, external data, r or dt. Its8 profiles/16 workers/454 model
calls are scoped to this one fixed synthetic suite, not an aggregate stage count,
general reader, actual-history proof or vehicle/production approval. Environment
receipts/manifests are retained separately from portable summary equality.
See [R27 results and reproduction](docs/NATIVE_SUITE_R27_RESULTS.md).

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

The [CORE9 saved sequence inspector](docs/CORE_SEQUENCE_INSPECT_CORE9_KO.md) reads
the three CORE8 files without importing/running the model or reference. It checks
captured-byte checksums and stored record relationships, not arithmetic or origin.
Inspection exit0 covers intact saved MATCH, DIFFERENT and REJECTED alike;
`saved_status` is historical, never a fresh numerical verdict. Errors exit2.
The stdout-only JSON/Markdown view neither alters inputs nor approves vehicle use.

The [CORE10 saved sequence comparator](docs/CORE_SEQUENCE_COMPARE_CORE10_KO.md)
checks both CORE8 packages through CORE9, then locates full INPUT/RESULTS field
differences, including opaque identity metadata, without model/reference execution.
JSON/Markdown stdout reports the first256 details plus exact total/section counts.
Arrays compare positionally; false differs from0, and absent differs from null.
Exit0 means identical saved records, exit1 different, exit2 invalid/operational;
saved MATCH/DIFFERENT/REJECTED remains separate from this comparison status.
No arithmetic, source authenticity, improvement or vehicle approval is inferred.

The [CORE11 closed sequence workflow](docs/CORE_SEQUENCE_WORKFLOW_CORE11_KO.md)
integrates explicit `check` (saved-only, no producer/model import) and `run` (one
named closed synthetic case, NEW external package) with optional saved baseline
comparison. Each role is captured once; run validates/captures baseline before
new model work. JSON stdout distinguishes recorded steps, new steps, saved status
and comparison. Workflow exit0 is valid orchestration, exit1 baseline differs,
exit2 error: even run's saved DIFFERENT/REJECTED can exit0. No baseline means no
regression comparison, and source identity changes are not silently ignored.
Run errors may retain partial output/nonzero work; no overwrite, deletion or retry.

The [CORE12 closed three-case suite](docs/CORE_SEQUENCE_SUITE_CORE12_KO.md) applies
CORE11 in fixed case order. `check --input-root` reads exactly three saved case
directories with no producer/model import; `run --output-root` explicitly creates
a NEW external suite (six new synthetic steps across3/3/0). Optional baseline roots
are fully captured before ANY new work. JSON stdout separates saved outcomes,
comparison counts, recorded history and new steps, retaining every per-case report.
Without a baseline, difference totals are null, not regression PASS. Errors retain
partial output/prefix work; no subset/manifest/fallback/retry or vehicle activation.

The [CORE13 portable saved-suite archive](docs/CORE_SEQUENCE_PORTABLE_CORE13_KO.md)
exports the exact nine saved files plus a check-only report and root Manifest.
`export --input-root --output` creates one NEW external ZIP; `verify --archive
--sha256` requires a full external digest before file access. Both execute zero
new model/reference steps, never extract, preserve stored M/D/R outcomes and keep
source identity unqualified. Fixed ZIP metadata makes identical inputs portable
byte-identically. Bounded CRC/schema/Manifest/report checks are custody, not origin
or arithmetic proof. Publication failures retain files; no overwrite/cleanup/retry.

The [CORE14 saved ZIP comparison](docs/CORE_SEQUENCE_ARCHIVE_COMPARE_CORE14_KO.md)
accepts two archives and two explicit full digests, preflighting BOTH digests before
file access. Each role is captured/verified once, with no extraction or new model
work. It preserves CORE13 receipts and CORE10 per-case exact INPUT/RESULT/IDENTITY
differences, counts all differences and caps details at256 per case. Exit0 means
identical validated archive bytes,1 a validated difference,2 rejection; saved M/D/R
outcomes stay data, never a numerical or provenance qualification.
An aggregate4MiB canonical-detail byte budget is checked before materializing
reports; oversized diagnostics reject explicitly, without silently shortened paths.

The [CORE15 readable archive summary](docs/CORE_SEQUENCE_ARCHIVE_REPORT_CORE15_KO.md)
adds a separate Korean Markdown CLI/API over unchanged CORE14 comparison. It shows
full/retained/displayed counts distinctly, first20 details per case, safe typed
cell previews (160escaped ASCII characters) and an explicit truncation marker.
The original JSON result is returned unchanged alongside at-most65536bytes of
Markdown. No JSON intake, extraction, new execution, hidden omission or weakened
CORE14 budget; no browser/all-renderer visual-quality claim. Exit0/1/2 unchanged.

The [CORE16 archive workflow](docs/CORE_SEQUENCE_ARCHIVE_WORKFLOW_CORE16_KO.md)
validates and compares two saved ZIPs once, then publishes unchanged comparison JSON,
Korean Markdown and a checksum to a NEW external folder. Exclusive writes and bounded
readback precede a path-independent receipt. Exit0/1 means identical/different saved
archives, both successfully published; exit2 can leave partial output for inspection.
No overwrite, extraction, replay, new model work or vehicle qualification is added.

The [CORE17 explicit offline run](docs/CORE_SEQUENCE_ARCHIVE_RUN_CORE17_KO.md)
requires literal `run`, a saved baseline ZIP/full SHA and a NEW external folder.
It validates and retains the baseline before executing the fixed three-case suite
(6 new synthetic model steps), exports CURRENT.zip, then uses CORE16 for comparison
and Korean summary. Original baseline is captured once; errors retain partial work.
Exit0/1 compares ZIP bytes, not stored M/D/R. No arbitrary/vehicle input or F61 work.

The [CORE18 saved run inspector](docs/CORE_SEQUENCE_RUN_INSPECT_CORE18_KO.md)
checks the exact14-file CORE17 layout read-only with both external archive digests.
It rebuilds the suite ZIP and comparison from captured bytes, accepting only exact
cross-artifact equality. Each file is captured once; no model/reference/extraction.
Exit0 is inspection consistency even when the saved comparison differs; recorded
steps and comparison0/1 remain data. No execution, arithmetic or origin proof.

The separate [CORE19 saved input preflight](docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md)
revalidates captured CORE8 synthetic input through the existing CORE3–5 rules.
It separates current input compatibility from recorded MATCH/DIFFERENT/REJECTED,
checks exact float decoding and quantization constraints, and never invokes a
model step or reference. Numeric validation is nonzero; compatible inputs do not
authenticate saved arithmetic, authorize replay or produce V4/F61 constructor args.

The [CORE20 preflight CLI](docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CLI_CORE20_KO.md)
exposes that unchanged CORE19 receipt with exit0/1 for current compatible/rejected
inputs and exit2 for fixed operational errors. It suppresses bytecode throughout
the command, creates no temporary cache, and does not add replay or vehicle authority.

The separate [CORE21 archive input preflight](docs/CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md)
accepts a complete CORE13 ZIP and external SHA, verifies it once, then reuses owned
CORE19 records for all three semantic verdicts without extraction or replay.
Historical statuses, archive integrity and current input compatibility stay separate;
the existing folder API and CLI keep their receipts and behavior.

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
