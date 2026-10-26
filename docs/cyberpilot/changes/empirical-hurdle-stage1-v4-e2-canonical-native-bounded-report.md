# Native bounded synthetic integration and caller profiling

## Identity and purpose
Cyber Validation/AutoTune mission STAGE1_V4_E2_CANONICAL_NATIVE_BOUNDED_SYNTHETIC_INTEGRATION_AND_CALLER_OPTIMIZATION; feature/cyber-autotune baseline 7cf1630773918dd560153517f45bfc75663c6f97. Scope PUBLIC_SYNTHETIC_NATIVE_BOUNDED_INTEGRATION_ONLY. Runnable A/B/C synthetic integration; no private scientific source, model, metadata or handoff opened. Final commit, exact-head five-workflow statuses, local/origin equality and clean state are separate final handoff evidence to avoid receipt self-reference.

## Original references
Repository https://github.com/rownlvh8875-coder/CyberPilot at the baseline above; original V4 bd8045ef2a0da62a92603439f38e7740f5923622. MIT/comma.ai attribution, Git history and submodule gitlinks preserved. All 231 public frozen source pins, including the Python kernel, Native C/wrapper, bounded caller, selectors, bridge, evaluator, acceptance, prior locks and four prior workflows remain unchanged. No model or LFS pointer replacement; no compiled binary committed. Source checkout, public Python wheels and compiler use network/filesystem as declared; this lab is not an OS sandbox.

## Changes and expected effect
Added an isolated Native bounded caller, explicit profiling/audit contexts, two focused test files, a fixed lab runner, one new workflow and contract/results/lock/report. No original runtime imports the new caller. MODE A invokes the frozen Python bounded reference directly. MODE B injects the verified Native candidate explicitly at TRAIN cache, Q1/Q3 whole-selected, DEV one-step and recursive Stage2 sites. MODE C differs only by reusing a C-contiguous recursive feature workspace. Intercept, feature order, Stage1 head routing/normalization/batch groups, full projected history, strict threshold, original projection and all metric/reduction order are preserved. No global monkeypatch, silent fallback or changed D2 winner.

The source -> immutable SourceBlock -> job-scoped features -> fixed512 cache -> global Q1 -> D1/D2 -> global Q3 -> durable TRAIN seal/readback -> DEV job/horizon/chunk -> same-anchor metrics -> frozen acceptance path is unchanged. Only source/policy recipes are reused, never historical BLAS deltas or metrics. New guard baseline remains NEW_CANONICAL_D0_TRAIN_REFERENCE. No actual private execution capability is generated; execute_private remains unconditionally blocked.

Native artifact qualification reuses the unchanged receipt verifier and compiler build. Explicit receipt digest and actual library SHA are required. The adapter keeps aligned input, effective indices, all normalizer fields, coefficients, model and original input strongly reachable until C returns; wrapper locals own output/trace. np.require copies are counted. Strong-reference entries are not unique owners or a process-memory census. C/F, unaligned/noncontiguous, copied model fields, diagnostic trace, GC pressure and repeated calls are tested. Error means fail closed; no fallback or arbitrary library discovery. Qualification is limited to tested Ubuntu24.04/Linuxx86_64/CPython3.12.13/NumPy2.5.3/GCC13.3.0/nearest-even/gradual-underflow environment and frozen flags.

## Regression risk and acceptance
Byte-exact equality includes signed zero for Stage1 probabilities, deltas, projected ticks, context/gate/history, cache, Q1/Q3 proofs, TRAIN seal and final files. Explicit sys.setprofile audit hashes actual returned arrays with dtype/shape/raw bits and ordered call counts; it never replaces functions or stores row arrays. Parent comparison requires complete nonempty witnesses, exact expected counts and digests. Missing/disabled witnesses fail. Identity, phase, source alias, model, winner, signed-zero corruption, early DEV, incomplete durable seal and private execution requests fail terminally. No tolerance, seed selection, second-best selection or altered policy grid.

Every original SourceBlock.check is retained. fast=True can still hash each live original alias. The profile records real fast/full calls, live/dead aliases, actual hashed arrays/bytes, metadata/spec work and CPU/wall. Reusable feature workspace is the only accepted optimization. SOURCE_INTEGRITY_OPTIMIZATION_UNPROVEN remains; checks_removed=0. Mutation-detection behavior is tested. No claim of a new immutable-source trust boundary or safe hash removal.

## Validation method and actual results
Primary fixture: 32 jobs, N=208, original single horizon anchor; warmup 1 then timing 3 per mode, fixed ABC order. CPU and wall seconds medians include artifact/provider/pipeline/seal work, excluding interpreter import/public-source qualification and process startup.

|Mode|CPU median|Wall median|CPU speedup A/mode|
|---|---:|---:|---:|
|PYTHON_REFERENCE|7.445277|7.183560|1.000x|
|NATIVE_BOUNDED|7.933034|7.771280|0.939x|
|NATIVE_BOUNDED_OPTIMIZED|7.864755|7.665802|0.947x|

Native does not accelerate the tiny primary end-to-end case. These three samples are not a significance or worst-case guarantee.

Two-segment full original 32 jobs,N832,416+416 segments; H anchor population2*(417-H), unchanged. Each mode has two fresh scientific observations with full intermediate witness, not a three-sample unprofiled timing qualification.

|Mode|CPU observations|Wall observations|
|---|---|---|
|PYTHON_REFERENCE|558.871, 558.632|544.240, 543.248|
|NATIVE_BOUNDED|49.110, 48.314|47.881, 47.083|
|NATIVE_BOUNDED_OPTIMIZED|48.529, 48.011|47.182, 46.319|

All six fresh scientific payloads and ordered raw-array witnesses match within each fixture:cache,Stage1 probabilities,delta,projected tick,realized movement,gate/context,entire projected history/path. TRAIN/result/complete file bytes match across modes. Primary witness infer36096/recursive384/cache32; two-segment infer52896/recursive672/cache32. No witness-free timing comparison substitutes for scientific audit. All 32 Q1/32 Q3,32 D0/64 D1/64 D2 decisions, five objectives/four guards/fixed loss tree, original metrics/P95, Frozen32/22-domain records match. Source-free verification has source rereads/inference/recomputation/writes = 0.

512-row L45 recursion:48controls across3arms,4routinglabels,4horizons;36unique input/policy cases because HIGH_SWITCH intentionally duplicates ALL_MOVE with an extra nonzero context-transition assertion. Warmup1 then3 timings permode. All raw trace bytes match, including All-STATIC zero Native calls. D0 H200 representative CPU medians:

|Routing|A|B|C|
|---|---:|---:|---:|
|ALL_STATIC|0.127770|0.125435|0.125988|
|ALL_MOVE|2.256324|0.203561|0.200892|
|MIXED|0.682709|0.145981|0.147148|
|HIGH_SWITCH|2.273181|0.203386|0.197490|

All 48 controls and timing samples are in results JSON; no favorable subset is used as global speedup.

Original v1 primary profile (instrumented cumulative CPU, overlapping, not additive; measured v1 source identities retained):

|Function|A CPU|B CPU|C CPU|
|---|---:|---:|---:|
|Stage1.probability|8.341609|8.791046|8.247163|
|transform|1.720527|1.756424|1.715063|
|SourceBlock.check|0.189733|0.189242|0.177438|
|digest|0.973314|0.890688|0.916018|
|assemble|0.095502|0.131679|0.111304|
|np.column_stack|0.694018|0.638785|0.028864|
|NativeWrapper._prepare|N/A|5.885785|6.016376|
|NativeWrapper.predict|N/A|6.091624|6.243035|
|NativeAdapter.predict|N/A|7.761617|7.904471|
|recursive|28.452900|29.217168|27.645725|
|drift_chunk|0.570541|0.642205|0.596909|
|metrics|0.078007|0.045356|0.086550|
|D2.select_context|0.415193|0.415311|0.438523|
|durable_serialization|0.180600|0.176312|0.179191|

Selected-target exclusive recursive CPU: A1.027068s/B1.114917s/C0.498716s. This remainder includes uninstrumented helper work and audit overhead; it is not a pure Python-bytecode timer. Native adapter and wrapper cumulative values overlap and must not be summed.

Stage1 probability 36,128 calls versus SourceBlock 1,856 calls (fast 768/full 1,088). Actual array hashing 48,707,200 bytes/28,896 arrays, including live original aliases 887,808 bytes; metadata JSON 5,961,683 bytes. Stage1 is larger than hashing in this primary profile; full two-segment hashing was not separately profiled and private alias lifetimes are unknown. np.column_stack calls B 37,472 -> C 1,472, exactly 36,000 recursive constructions removed without changing probabilities or results.

Each primary Native child executes 18,419 C calls: MODEL_VALIDATE32zero-row,TRAIN_CACHE32,Q1/Q3 32each,DEV_ONE_STEP96,DEV_RECURSIVE18195. Empty gates skip inference; model validation is separate. Native rows 42,327, fallback 0, strong-reference entries peak 10/end 0; this fixture needs no additional np.require input/model copy. Unit tests explicitly require copies for adverse layouts. Benchmark counters total 469,990 C calls across 18 Native full-pipeline children plus 21,000 recursive512 matrix calls (490,990 total). These are actual counters for the fixed benchmark; focused unit-test calls are outside this counter scope.

Observed across lab parent/27 children:maximum process high-water RSS 293,020 KiB/VM 412,044 KiB, maximum sealed repeat output 2,625,462 bytes. These are process measurements, not simultaneous E2 maximums. Feature/selected/trace/horizon tracked peaks 1 each; retained caches 32 before retirement. The allocator return is not claimed. The prior conditional 14.84TB live-alias hashing scenario remains an analytical scenario, not this lab's observed hash volume.


Current-task final-source fresh validation: 5900 full AutoTune/controls PASS; new focused 22, unchanged Native 26, Offline 91, readiness 29, bounded 30, attribution 95 and lateral 16 separately PASS (overlapping coverage, not added to full total). Max-shape original bounded stress, Ruff, compileall, SCons, 231 source pins and the public contract JSON checks are recorded separately in results. Final generated result/lock receipt and publication checks belong in the final handoff. D/E scientific mounts were empty read-only throughout the lab and local full regression. Full CI remains a separate GitHub result. All 33 forbidden actual operation categories are 0; synthetic materialization/inference/selection are separately measured and do not imply private execution.


Replay versus real driving baseline, closed-loop simulation and shadow/vehicle stages are NOT_RUN and outside this authorization. Lateral regression uses public synthetic fixtures only. Synthetic acceptance output is not empirical Frozen32 pass/admission; D2 real performance remains unevaluated.

## Final job/phase/chunk telemetry amendment
The original unprofiled timing matrix and both full two-segment scientific repeats above were measured on the retained v1 source identities. Final source changes add granular telemetry, validation and negative tests; Native caller, backend, arithmetic and scientific fixture bytes remain unchanged. The measured v1 source archive raw SHA256 is cc440227c24aa921a912899fd4c0205d31c89e14f6f6525bfe1097b3a7466138. Final CI reruns the entire fixed benchmark on the final commit.

Three predeclared additional primary profiles (one per A/B/C, warmup0) measured actual constructor admission per job/role and spec/digest costs by job/phase, plus horizon/chunk checks and setup work. Each has64 job/role admission records,384 chunk records and384 nonchunk setup records. Provider-wide admission is separately measured, never divided by32. Every original check remains. All scientific files and raw-array witnesses match v1, and source-free verify remains0 rereads/inference/recompute/writes.

|Final granular profile|A|B|C|
|---|---:|---:|---:|
|Instrumented end-to-end CPU s|39.456580|34.768226|33.708815|
|Instrumented end-to-end wall s|38.903585|34.119374|33.070683|
|Actual per-job constructor CPU sum s|0.056169|0.036843|0.049033|
|Chunk source-check CPU sum s|0.024811|0.035877|0.044915|
|Chunk spec-stamp CPU sum s|0.469934|0.456750|0.502140|

These instrumented times include profiling overhead and are not unprofiled speedup evidence. Each profile observes768 fast/1088 full checks,48707200 actual array-hash bytes and5961683 JSON bytes. Within the384 chunks,768 fast checks observe dead original aliases and0 array-hash bytes; this is an observation of this synthetic ownership lifetime, not an O(1) guarantee for fast checks with live aliases. Setup/other phases carry source and spec hash work. Generic digest costs mix array/source and spec hashes; named _spec_hash/_spec_stamp costs identify spec work. Inclusive nested costs and job/chunk alternative views must not be summed together.

Chunk and nonchunk costs reconcile all14 integer fields to independently accumulated event totals and key sets. Missing/duplicate setup/chunk records and calls/bytes/CPU/wall/alias-field corruption fail. The first generic frame-local implementation retained a stale feature alias and triggered the original lifetime guard; it was corrected by inspecting metadata-only frames, with the guard unchanged. Review then found a chunk-reconciliation gap; it was repaired and tested. The interrupted full regression before this repair is NOT_PASS and is excluded; final fresh regression is5900PASS. No failed or interrupted evidence is relabeled.

All per-job/per-phase/per-chunk records are published losslessly in results JSON, using named columns to fit the1MiB public-text limit. Decode each table by row_count: a column with constant repeats its observed identical value (never an imputed count); otherwise values[i] is row i and its list length must equal row_count. Missing/duplicate fields are invalid. keys reconstruct ordinary fields. cost_columns maps label to cost-field columns; cost_key=cost uses its single label directly, while cost_key=costs retains label nesting. Replace columnar_tables by the six reconstructed named record lists and remove table_encoding. Each decoded granularity object must match its decoded_granularity_canonical_sha256 under canonical sorted JSON. This is public synthetic telemetry, not private row data. The sealed final granular measurement raw SHA256 is c518800e3aa9d1d4bd2e18eea85faf7bc54827bf653696bf6d83b05025cf4c79.

The final additional profiles execute36838 Native calls; fixed v1 benchmark490990 plus this final-profile scope equals527828. Focused/full unit tests, superseded granular profiles and reviewer probes are outside that scoped total. Fallback0, original hash checks removed0, all forbidden actual operations0. Runtime/memory bounds remain UNPROVEN and private authority remains absent.

## Workload and resource assessment
Frozen worst case remains32jobs,3arms,H25/H50/H100/H200,Nmax336941,Pmax93;12,129,876,000recursive row-steps,1,128,078,468,000Stage2 terms,23,724,000recursive bridge calls and up to47,448,000head calls. Prior single-kernel speedup is not full-caller speedup. Reported medians and instrumented cumulative costs cannot prove worst-case completion or sum into a hard bound. Profile cumulative CPU overlaps; selected exclusive CPU includes only instrumented targets and overhead.

CPU 21,600s/wall 43,200s per repeat, AS8GiB,input 3,000 opens/64GiB,output384MiB,reserve2GiB,worker 1/BLAS 1 unchanged. Lab children use AS8GiB/CPU1800s and wall2400s; the recursive/D2 parent section also has a2400s timer. Actual private I/O, source/alias/model lifetimes, host capacity, allocator retention and full maximum D2/metric workload remain unknown. Previous logical scenario6,016,244,488bytes is not an OS address-space proof. Adapter contiguous copies/output/model buffers/library/loader/temporary serialization must also be included. del/refcount/GC do not guarantee RSS/VM release. Runtime and memory upper bounds remainNone/UNPROVEN, private execution NOT_AUTHORIZED.

## CI, authority and publication
New CyberPilot Native Bounded Integration CI independently builds the exact Native artifact, runs existing 26 plus new focused tests, fixed A/B/C matrix/fresh repeats, source-free verification, source/receipt/Ruff/syntax/publication/clean checks without LFS payloads, model download or setup. It uses pinned source actions, exact Python/public wheel hashes and GCC13.3.0. Child environment is a minimal explicit allowlist, with no inherited credentials or loader overrides. Child scientific reads follow externally held completion -> member SHA chains through rooted Store. Child logs retain a regular no-follow FD throughout execution/readback. Both wall timers and profile hooks are restored.

Existing Offline Numerical, Bounded Lifetime, Native Runtime Lab and Full workflows remain unchanged. Baseline Full CI failed setup on 15 upstream LFS404 OIDs; later build/tests did not run. New and prior Offline success is distinct from Full CI. Final exact-head status is reported only after actual completed runs. Two independent final-byte scientific and authority/resource reviews are separately recorded in the publication commit/handoff, not treated as CI evidence.

## Handoff
Remaining blockers: actual private capability/member/model/anchor binding; verified host and I/O capacity; whole-caller CPU/wall/AS proof; Full CI recovery; separate explicit private E2/source integration authorization. No policy admission or vehicle use is authorized. Rollback is to leave the new isolated caller unused; no existing scientific runtime is replaced.

Historical D0 HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE; D1 E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE; D2 PERFORMANCE_NOT_EVALUATED; E2 E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED; Q1 E2_V2_Q1_BATCH_LAYOUT_NUMERICAL_DIFFERENCE_CONFIRMED remain immutable. selectionsnull, historicalTRAINgateNOT_SAVED, HOLDOUTCLOSED/FUTURE_UNTOUCHED_HOLDOUT_REQUIRED, vehicleNOT_READY/REAL_VEHICLE_UNVERIFIED/VEHICLE_ACTIVATION_BLOCKED/authorityNONE. V5/pooledrefit/compositionNOT_AUTHORIZED. Source-grid ticks are not physical EPS movement and recorded normalized commands are not applied EPS torque.

After GitHub publication, five exact-head workflow observations, source/receipt checks, independent approvals and clean local/origin state: STOP.
