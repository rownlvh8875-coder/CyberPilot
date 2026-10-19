# Canonical runtime feasibility and isolated native candidate

## Identity and purpose
Cyber Validation/AutoTune mission `STAGE1_V4_E2_CANONICAL_RUNTIME_FEASIBILITY_AND_NUMERICAL_ACCELERATION`; branch feature/cyber-autotune; baseline1608205ff68ae5fe3182c303726c51e3831595ed. Scope PUBLIC_SYNTHETIC_RUNTIME_FEASIBILITY_AND_NATIVE_CANDIDATE_ONLY. Implementation is standalone and not wired to any E2/controller/vehicle runtime. No private source/metadata/model/handoff was opened. Final exact-head CI and local/origin/clean state belong in final handoff, avoiding receipt self-reference.

## Original references and immutable sources
Repository https://github.com/rownlvh8875-coder/CyberPilot, exact baseline above; original V4 bd8045ef2a0da62a92603439f38e7740f5923622.220 frozen public source pins match, including original canonical kernel e8b77a9c4494484c2022ca6a9325a588751d8aa1661d69a28608b8860ab92ef8, bounded executor11e94639dbdc5a3a59a761fd3f87acaf868e0b8334f948d4ff99e869b1529cc7, selectors, acceptance, all three existing workflows and LFS pointers. No historical result or source was rewritten. MIT/comma.ai attribution and submodule gitlinks retained; native code is new MIT C11 source. No binary is committed.

Compiler13.3.0 flags follow [GCC13.3 optimization documentation](https://gcc.gnu.org/onlinedocs/gcc-13.3.0/gcc/Optimize-Options.html), especially contraction controls. Flags alone are not an arithmetic proof: generated scalar instructions and raw-byte tests provide separate evidence. Runtime ABI C11_LINUX_X86_64_DOUBLE_SIZE_T_INT64_V1; qualified only for tested Linux x86_64/CPython3.12.13/NumPy2.5.3/nearest ties-even/gradual underflow. No untested platform guarantee.

## Changes and execution architecture
Added runtime_model.py, separate native_candidate.c/.py, two focused test files, explicit build/benchmark runner, a dedicated runtime-lab workflow and three contract/result/lock JSONs plus this report. Original Python canonical kernel and bounded scientific caller are unchanged. New `NativeCandidate.predict` consumes only in-memory arrays and returns exact binary64 output; loading requires an explicit public build receipt and expected raw SHA. No implicit build/search/load or private grant. An optional callable is injected only into the lab recurrence; no global monkeypatch or executor substitution.

C arithmetic is intercept+1, positive-zero accumulator, original effective-column order, separately stored volatile double subtraction/division/product/addition, strict finite checks, signed-zero preservation and no clipping. Python validates exact dtype/shape/effective/constant/model fields; C checks declared extents/overflow/NULL/output capacity/environment. np.require may copy Fortran/unaligned input to aligned C layout without changing bytes. Normalized trace is diagnostic only. Raw ABI/argument-reuse timing assumes valid declared buffers and is not safety for arbitrary hostile pointers.

Explicit build uses an exclusive0700 external directory, immutable0400 source snapshot, source hash before/after compile, minimal compiler environment, GCC13.3.0 and frozen flags. Library0500 and receipt0600 are hashed, file/directory-fsynced. Rooted descriptor-relative no-follow/NONBLOCK/CLOEXEC traversal, uid/mode/nlink/caps and before/after stamps reject FIFO/symlink/hardlink/mutated artifacts. One verified inode/handle/CLOEXEC fd is retained per process behind a loader lock, preventing /proc/fd name reuse. This is artifact-drift detection, not a signed trusted issuer, malicious same-user/compromised-compiler proof or OS sandbox. Native code spawns no threads/heap scratch and cannot open files/network.

## Predeclared tests and repairs
Protocol declares seed20261021, N8192/65536/336941, P5/13/33/93, all effective columns, warmup1 then measured3, call sizes0/1/8/64/512/max, fixed three-arm/horizon/routing probes, equal/unique D2 and the frozen32-job caller. Python-first/native-second order is fixed; cache/thermal/order bias and three-sample uncertainty are disclosed. No adaptive seed/grid/repeat/subset search. CPU user/system and wall are separate; process high-water is cumulative across cases, not per-case peaks.

26 focused tests PASS: native/Python/frozen independent oracle,600 batch checks over60 reused configurations/12 input-model pairs,180 Original/Parity/Aligned controls, all32 native Q1/Q3 and64 original D2 context winners/guards, effective/intercept/constant handling, dtype/endian/model rejection, positive/negative zero, subnormal/underflow/nonfinite/overflow, FMA counterexample, ties-even/signed16, immutable inputs and ABI errors. These are not independent drives or private qualification. Empty-gate integrated/lab paths skip Stage2; standalone empty-batch API is tested separately.

Preliminary review confirmed an exported-C fenv gap (SSE rounding diverged from x87 while the Python wrapper rejected it), numeric /proc/fd dlopen reuse and FIFO blocking. Each was reproduced RED and repaired GREEN. Unsupported SSE modes now return environment failure; source arithmetic for qualified modes is unchanged. Initial candidate/source benchmark is preserved but superseded. Three development builds and two full fixed benchmark matrices occurred; the guarded candidate matrix is final. The added source-cost postprocessor/call-graph metadata correction came after timing; measured source hashes and raw benchmark bytes remain separately recorded and untouched.

Timed recursive scale0.125 has projected HOLD even when gateMOVE; it is not a state-switching throughput certificate. A separate predeclared unscaled8-anchor H200 test compares full path/history/context/gate/probability/delta bytes against frozen recursion and requires both contexts/nonzero projected movement. Stage1 timing separately covers1/8/64/512 rows, four P values and STATIC/MOVE/alternating prior contexts. These controls do not alter the original timing grid.

## Measured kernel and boundary cost
CPU medians in seconds, P=effective columns=93. Full12-condition measurements, raw user/system/wall samples, rates, build and environment identities are in the results JSON.

|N|Python CPU|Native wrapper CPU|Speedup|Native terms/CPU-second|
|---|---:|---:|---:|---:|
|8,192|0.168621|0.003534|47.71x|215.58M|
|65,536|1.417062|0.026943|52.59x|226.21M|
|336,941|7.067026|0.137941|51.23x|227.17M|

Microseconds/call, P93, fixed100-inner calls except maximum1. Raw checked-ABI reuse omits Python validation/copy/argument work and is not an authorized inference path. Empty real gates make zero Stage2 calls. Large-batch speedup cannot be assigned to tiny batches.

|Rows|Python|Native wrapper|Checked ABI reuse|
|---|---:|---:|---:|
|0|54.68|75.77|1.67|
|1|75.47|73.38|2.09|
|8|218.20|82.82|4.34|
|64|1563.54|99.03|22.47|
|512|10451.32|257.66|171.27|
|336,941|6972651.00|152889.00|120065.00|

Build wall 0.236283s; compiler child CPU/RSS NOT_MEASURED. Parent build-process resource snapshots are not compiler usage. Final native C SHA 1af1bfa0ce165b47104980ed917375de5fd1c2385c7c0d8429c6f8b7d0e7115e; binary SHA d9f2a5b8a36a19944ed75d2f334731790d6b474a63632930db9fff9397daa52d; compiler binary SHA 1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26; disassembly SHA c214773b39bcd7278e0dc30251532739891af5965a5e2cefa34463f487bb7522. Scalar subsd/divsd/mulsd/addsd observed, no fused multiply-add found in this artifact; no universal compiler/CPU proof.

## Full caller, phase accounting and Amdahl
Only the unchanged Python bounded executor runs the full32-job scientific pipeline. Warmup1, measured3 and profile1 all have identical train/result/complete payload bytes. Coverage D0=32,D1=64,D2=64,Q1=32,Q3=32,DEV=32. Global all32 barriers, whole-selected references, durable TRAIN seal, strict p>decision/equalitySTATIC, Canonical D0 guard reference, four guards/five priorities/fixed loss tree, same-anchor metrics, exact P95, four horizons and32 clauses/22 domains remain unchanged. No historical BLAS delta is inserted. Synthetic support failures are not empirical acceptance or policy admission.

Last unprofiled phase sample (not phase medians); provider creation/admission and final serialization are also in the full-run timer and separately visible in profiler data.

|Phase|CPU seconds|Wall seconds|
|---|---:|---:|
|B_ALL32_D0|0.012001|0.011739|
|COMPLETE_SYNTHETIC_REPEAT|0.000000|0.000001|
|C_ALL32_POTENTIALS|0.100012|0.100409|
|D_ALL32_Q1|0.079968|0.077575|
|E_ALL64_D1|0.007960|0.010943|
|F_ALL64_D2|0.135933|0.132485|
|G_ALL32_Q3|0.084002|0.084255|
|H_DURABLE_TRAIN|0.007059|0.015634|
|I_DEV_UNLOCK|0.027956|0.030301|
|J_THREE_ARM_DEV|6.741648|6.642382|
|K_FROZEN32_22|0.000000|0.000003|

cProfile uses process CPU timing and adds instrumentation cost. Exclusive times may be summed within that profile; cumulative values overlap and must not be summed. Clock/profiling overhead and tiny synthetic populations prevent scaling these times into a private completion guarantee.

|Function|Calls|Exclusive CPU|Cumulative CPU (overlaps)|
|---|---:|---:|---:|
|empirical_hurdle_v4_execution.py::probability|36128|0.855511|5.297955|
|empirical_hurdle_v4_e2_canonical_bridge.py::recursive|384|0.333759|16.351844|
|empirical_hurdle_v4_e2_canonical_stage2.py::canonical_predict_delta|18451|0.221308|7.104045|
|empirical_hurdle_v4_e_evaluation.py::drift_chunk|384|0.160982|0.442271|
|empirical_s2_ri_fit_cv_math.py::project|18387|0.107101|0.325800|
|empirical_hurdle_v4_e2_decision.py::select_context|64|0.080069|0.275496|
|empirical_s2_ri_fit_cv_math.py::metrics|288|0.017093|0.062717|

Profile total 22.150811s, Stage2 cumulative 7.104045s. Infinite Stage2 speedup leaves 15.046766s in this instrumented fixture, maximum 1.472x. This conditional Amdahl result is not a measured native full-caller speedup.

## Worst-case resource and runtime conclusion
Frozen upper workload remains12,129,876,000 row steps,1,128,078,468,000 Stage2 terms and23,724,000 recursive bridge/probability calls (up to47,448,000 head calls). All-MOVE allows one Stage2 call per step; all-STATIC skips Stage2 but not Stage1/history/metrics. High-switching retains both-head routing costs. MaxN Q1/Q3 remain whole-selected calls; D2 sorted-tree sweep stays O(N logN), tested equal/unique groups without per-threshold Stage2 inference.

Maximum-observed512-row sample extrapolations: Stage1 7415.885 CPU seconds, all-MOVE native wrapper 6367.284 CPU seconds before other work. These are sample-cost extrapolations, not upper time bounds or a sum proving6h. Source admission/hash, feature assembly, loss trees, loop/history, drift, exact P95, serialization and actual I/O remain.

Conditional source cost: horizon chunks253,056, at least two fast checks/chunk506,112. SourceBlock.check(fast=True) still hashes live original aliases; if all4×8byte fields for916,535 source rows/job remain alive this alone reads/hashes 14,843,819,581,440 source bytes, excluding outer checks/metadata. Actual retained alias bytes/segments are unknown. This is in-memory hashing, not new private file-reread authority. Drift full-history comparison is O(anchors×H×L), not merely O(anchors×H). The runnable postprocessor returns full CPU/wall upper bounds=None and never converts partial measured costs into PASS.

Existing logical memory scenario6,016,244,488 bytes remains conditional. Candidate adds output, possible full contiguous/alignment copy, model buffers, DSO/loader overhead; optional diagnostic trace may add another N×effective matrix. Native heap scratch0 by source, stack constant but not measured. Native/allocator retention and actual host/source/model counts are not bounded by del/refcount. Synthetic process high-water RSS643,872KiB / VM731,496KiB under AS8GiB; this is not full E2 peak proof.

Caps unchanged: CPU21,600s/wall43,200s per repeat, AS8GiB,input3,000opens/64GiB,output384MiB,reserve2GiB,worker1/BLAS1. Lab child uses AS8GiB/CPU1800s/external wall2400s. No actual private I/O/host capacity was inspected. Whole runtime, Stage1/caller and memory remain UNPROVEN.

## Regression risk, validation and CI
Regression risks: unsupported fenv/toolchain, artifact drift, ABI misuse, small-batch overhead and non-Stage2 bottlenecks. Failure is byte-exact-or-fail, no tolerance/fallback/rebatching. Rollback is simply not using this nonwired candidate. No existing implementation is replaced. Replay/closed-loop/shadow/vehicle validation is NOT_RUN and outside authority; lateral tests are public synthetic regression only.

Current local full regression: 5878 PASS / 604.10s. Current-task standalone91/readiness29/bounded30 preserved; attribution95 and lateral16 passed separately (not added to full count). Ruff/compileall/SCons and220 source pins pass. D/E scientific volumes are empty read-only mounts during full local regression; all permitted fixture operations are public synthetic. Private reads/refits/source writes/tolerance changes/HOLDOUT/vehicle/V5 and all forbidden actual operations0. Final publication audit and two exact-byte reviews are independent of CI.

New dedicated OFFLINE_CANONICAL_NATIVE_AND_RUNTIME_CI performs exact toolchain qualification, separate build, explicit receipt tests/benchmarks, caps, Ruff/syntax/pins/publication/clean checks. Existing Offline120, Bounded150 and Full workflows are untouched. Original full CI baseline failed setup on15 upstream LFS404 OIDs; downstream build/tests did not run. Offline/native/local success is not FULL_CI success. Native suite requires an explicit artifact; missing/unsupported builds fail rather than skip. Any future recovered Full CI environment must supply that explicitly under separately reviewed workflow scope, not silently auto-build or skip tests.

## Handoff and STOP
Standalone candidate is implemented, byte-exact synthetic-qualified and performance-measured. Whole caller runtime/memory remain UNPROVEN. Native integration and private E2 execution NOT_AUTHORIZED. Actual input capability/root/member/model/anchor binding remains pending, as do host capacity, Full CI recovery and future explicit grant/source amendment. Prospective integration must preserve canonical D0 reference, all32 Q1/Q3, TRAIN/DEV seal/barrier, frozen objective/guards/acceptance, two fresh repeats and source-free verify-only.

Historical D0/D1/E2/Q1 outcomes remain immutable; D2 PERFORMANCE_NOT_EVALUATED, selectionsnull, TRAIN gateNOT_SAVED, HOLDOUT CLOSED/FUTURE_UNTOUCHED_HOLDOUT_REQUIRED, vehicleNOT_READY/REAL_VEHICLE_UNVERIFIED/VEHICLE_ACTIVATION_BLOCKED/authorityNONE, V5/pooledrefit/composition NOT_AUTHORIZED. Source-grid ticks are not measured physical EPS movement; recorded normalized commands are not applied EPS torque. After publication, final exact-head four-workflow observations, source/local-origin/clean checks and final approvals: STOP.
