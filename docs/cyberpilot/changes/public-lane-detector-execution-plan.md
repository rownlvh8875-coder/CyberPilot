# Public lane detector execution plan

Baseline: b885a914adeb5cd5b2332ffb6a18a5a546f8aa99, feature/cyber-autotune.
Implementer: current session; whole-increment independent review at completion.
Scope: external CLRerNet DLA34 non-EMA CUDA environment; public-only reproduction and lane-marking pixel diagnostics. No controller changes or private input access.

## Ordered tasks and interfaces

1. Freeze source/config/weight, exact executable environment and public protocol before semantic GT/output inspection. External Python 3.11.9, torch 2.1.0 CUDA 12.1, torchvision 0.16.0, mmcv 2.1.0, mmdet 3.3.0, mmengine 0.10.5, original CUDA NMS. Resolved packages/compiler/binary identities are collected after installation, before inference. Package acquisition may use network; inference must not.
2. TDD execution receipts and public reproduction validator: exact source/environment/config/weight/artifact bindings, complete official split and rounded published F1 fidelity. Official non-EMA F1=81.11 percent, compare rounded-to-two-decimal reported metric without post-result tolerance adjustment. Batch size 1/workers 0 for available 4GB GPU; record resolved configuration.
3. TDD public pixel protocol/aggregate and deterministic representation adapter. Existing pixel kernel remains unchanged. Original-image row samples, exact category-2 masks, median/p90/p95/p99/max, unsupported/off-marking/missing denominators, width-normalized distributions, near/mid/far image thirds; no ego identity/meters. CULane custom raster/row convention is explicitly separate from official IoU.
4. Reproduce official full CULane first. A missing/failed reproduction blocks normal comma10k qualification and secondary selection. Any separately declared diagnostic subset is labelled incomplete, never full benchmark/PASS. Public pixel thresholds remain undefined until literature/downstream requirements justify them; official F1 matching alone never grants private access.
5. TDD known-camera geometry forward/backprojection and analytic-vs-central-difference Jacobian validation at 5/10/20/30m. Record sensitivities, not measured comma4 calibration. Split calibration blockers; stationary physical protocol and symbolic uncertainty.
6. TDD fail-closed private promotion guard before any input opening, metadata-only human holdout selection freeze. Do not emit sealed reference or open private frames unless all required public conditions pass.
7. Focused/full AutoTune, Ruff/syntax/publication/authority/privacy/diff, SCons; fresh-context review/fixes; feature record and text-only receipts; commit/push/equality/clean.

Pre-flight: execution identity feeds reproduction, reproduction feeds promotion. Public pixel diagnostics feed symbolic budget only, not a metric qualification. Private holdout stays inaccessible while justified public thresholds/reproduction are absent.
Ruling: external acquisition/build probes precede implementation tests; they are environment preparation, not repository behavior changes.
Ruling: preserve old audit/protocol/report identities. Introduce separately versioned execution receipts rather than retrospectively turning NOT_RUN into PASS.
Ruling: user explicitly authorized commit/push and continuous work; no additional approval pause.
Vehicle status: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Qualification: BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.

## Execution ledger

- Task1 complete: external65-package Python/CUDA/GCC environment, pinned official CUDA NMS and checkpoint/cache identities. No production dependency changes.
- Task2 complete software contract; actual official execution BLOCKED supplier quota. Numeric metric/difference/exit code remain null,0/34680.
- Task3 complete: metadata-prefrozen119-pair diagnostic, explicit original-geometry/row/width conventions. Existing metric/admission source not changed.
- Task4 partial by evidence: actual119x2 CUDA inference and pixel errors; full official/CyberPilot benchmark NOT_RUN. No qualified detector selected.
- Task5 complete software: known-camera forward/backprojection/Jacobian checks, independent physical protocol and unknown-budget children; actual independent calibration NOT_RUN.
- Task6 complete fail-closed software; private metadata/images/human labels/sealed reference NOT_RUN. Pure holdout helper only, no reader.
- Task7 verification/review/commit: final validation receipt and Git history contain actual checks/results.

Ruling: supplier download failure is missing official input, not a measured detector mismatch. Preserve full-reproduction blocker and execute a separately declared public diagnostic to test software; never substitute it for official/public qualification.
Ruling: adapter-v1 rejected legitimate off-canvas spline samples at frame level. Retain original run/protocol and freeze explicit post-result V2 correction; unchanged detector/config/threshold/sample set. No pretense of untouched holdout or preregistered qualification.
Ruling: independent review corrected consumed-file TOCTOU, pairing/geometry and prior-lineage checks with regression tests; final source/env rerun required and completed.
Ruling: physical calibration needs observations; stationary protocol supplied without inventing measurements or requesting new driving data. All unknown bounds remain null.
