# Frozen public lane detector execution and pixel diagnostics

## Identity and purpose

Cyber Validation; IMPLEMENTED, public diagnostic execution complete, qualification BLOCKED. Baseline b885a914adeb5cd5b2332ffb6a18a5a546f8aa99 on feature/cyber-autotune. Run a real external lane detector against public masks with reproducible identities, without admitting its predictions as independent lane truth. No private frames/logs opened and no controller tuning performed.

This increment does **not** complete the requested official full benchmark reproduction: CULane images and annotations are unavailable through the official supplier download endpoint. Official F1/local metric are NOT_RUN. The separately declared comma10k subset is a diagnostic experiment, not a replacement qualification benchmark.

## Original references

- [CLRerNet pinned official source](https://github.com/hirotomusiker/CLRerNet/tree/dae038f67da57e292e5293a68c9c1c2922de13c2): code Apache-2.0; weight license not separately declared, binary not redistributed.
- Non-EMA release clrernet_culane_dla34.pth, SHA-256 424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa, 63,464,485 bytes. [Official reported non-EMA F1](https://github.com/hirotomusiker/CLRerNet/blob/dae038f67da57e292e5293a68c9c1c2922de13c2/README.md) is 81.11%; EMA/paper averages are different models/results.
- [Official dataset procedure](https://github.com/hirotomusiker/CLRerNet/blob/dae038f67da57e292e5293a68c9c1c2922de13c2/docs/DATASETS.md) names three test image archives, annotations_new.tar.gz and list.tar.gz. All four image/annotation downloads returned supplier quota errors; only list archive acquired. No unofficial mirror accepted as an authenticated substitute.
- comma10k source 6c205fe4c43cc53b2b1befafb1060d0606555027; [prior source audit](public-lane-reference-source-audit.md) remains unchanged. Category 2 is lane marking segmentation; no ego-left/right GT.
- CLRNet secondary source/weight declaration remains frozen; no secondary execution or winner selection while primary official reproduction is blocked.
- Original call path: BGR image → official validation Compose/crop/resize → DetDataPreprocessor /255 → DLA/FPN/CLRerHead.predict → softmax/.41/CUDA NMS → normalized Lane spline → original-image row samples → category-2 row-run distances. No modelV2/CyberPilot controller output supplies reference.
- Production/submodule identity and behavior remain untouched. Exact external dependency/toolchain details are in [environment](public-lane-detector-environment.json), [package manifest](public-lane-detector-packages.lock), [toolchain](public-lane-detector-toolchain.json) and [execution details](public-lane-detector-execution-details.json).

## Changes and expected effect

- lane_detector_execution.py: exact source/weight/runtime declaration freeze, official full-split receipt and rounded-release fidelity rule, extended pixel distributions, fail-closed private gate.
- lane_detector_runner.py: external CUDA inference only; no-follow verified public input buffers; canonical pair identities and identical image/mask geometry; exact consumed protocol/manifest binding; immutable sealed memfd checkpoint; retained original protocol/prior result verification.
- lane_public_protocol.py: spatial sampling, near/mid/far thirds, exact metadata-only holdout selection, missing metric-data provenance report. No private reader or annotation generation.
- Existing pixel/projection/reference-admission modules unchanged. No production integration, network acquisition inside runner, model/config search, missing-frame fill or temporal state.
- Environment: Python3.11.9, torch2.1.0+cu121, torchvision0.16.0+cu121, mmcv2.1.0, mmdet3.3.0, mmengine0.10.5, CUDA12.1, GCC11.4, RTX3050 Laptop4GB; full 65-package manifest frozen. Official CUDA NMS built without source edits. GCC12 initial build failed; GCC11 resolved pybind/NVCC incompatibility.
- Inference network isolation: Linux user/network namespace with only unconfigured loopback; no external interface. Check /proc/self/net/dev, because inherited /sys view incorrectly lists host interfaces.
- All inference state keys load from official weight. Exactly three missing segmentation training-only keys are allowed; predict() does not call loss()/forward_seg(). Any other missing/unexpected key fails. init_detector palette='random' skips eager absent CULane dataset metadata loading; palette is not consumed by lane inference.
- Physical actuator delay/reset/state ownership: not applicable; detector inference only. Controller/plant pipeline unchanged.
- Maintenance: optional external environment/native build; no production requirements changes. Snapshots are declared/bound evidence, not cryptographic authentication of accuracy.

## Regression risk and acceptance

Official reproduction criterion was declared before outputs: full 34,680 test frames and F1 rounded to two decimal percent equal non-EMA release 81.11. A numerical mismatch fails; missing inputs/NOT_RUN stays BLOCKED with null metric/difference/exit code. No arbitrary tolerance added.

CyberPilot pixel promotion thresholds remain undefined: the earlier audit found no justified median/p95/coverage/confidence requirement linked to independent calibration/downstream error budget. F1 fidelity alone cannot grant PUBLIC_GT_PASS_PIXEL_ONLY or private access. Confidence softmax is not calibrated probability; calibration NOT_RUN.

Subset selection was frozen from metadata before semantic GT/output opening: lexicographic road image paths, indices 0,100,200,… across 11,888 pairs → 119 pairs. Every PNG blob and SHA-256 verified. Original immutable manifest retained. This is neither the full comma10k benchmark nor an independent capture-level holdout (imgs2 has paired camera views).

Geometry adapter stretches original images to CULane1640x590 then applies official crop/800x320. Aspect ratio/FOV/domain differences limit interpretation. Spatial Lane spline sampling uses original rows; -2 excludes unsupported y, finite off-canvas points counted/excluded, malformed/nonfinite outputs make frame unavailable. No GT or unavailable frame is interpolated.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Actual detector inference | unshare --user --map-root-user --net env CUBLAS_WORKSPACE_CONFIG=:4096:8 TORCH_HOME=external-cache PYTHONPATH=repository detector-env/bin/python -m openpilot.tools.cyber_autotune.lane_detector_runner; exact public paths in run manifest/details | [run receipt](public-lane-detector-diagnostic-result.json), [protocol](public-lane-detector-diagnostic-protocol.json), [input manifest](public-lane-detector-input-manifest.json) | 119 frames ×2, exact points/status/lane count/sampling/geometry equality; exit0; 0 malformed geometry frames |
| Official reproduction | Planned official tools/test.py command recorded; batch1/workers0 | [official receipt](public-lane-detector-official-reproduction.json), [acquisition errors](public-lane-detector-culane-acquisition-blocked.json) | NOT_RUN/BLOCKED; evaluated0/34680; local F1/difference/exit code null |
| Public marking diagnostic | Fixed existing row-run-midpoint bidirectional kernel; original widths; thirds; median/p90/p95/p99/max | [actual result](public-lane-detector-diagnostic-result.json) | Quantitative subset result below; no meter/ego qualification |
| Unit / regression / build | TDD + focused/full AutoTune, Ruff, syntax, publication/privacy/authority/diff, SCons | Final validation receipt | See final receipt for executed counts; no native controller edits |
| Replay vs baseline | Not applicable: detector track | Prior controller ledger preserved | V1/V2/A3 unchanged |
| Simulation / closed loop | No new controller screening | Existing candidate history unchanged | V2 REJECTED, stress TRADEOFF_ONLY, FAMILY_REDESIGN retained |
| Shadow | No private/runtime path | [private gate](public-lane-detector-private-gate.json) | NOT_RUN; cannot actuate or open private input |

Actual pixel results, conditional on supported row pairs:

| Direction | Samples | Median px | p90 px | p95 px | p99 px | Maximum px |
| --- | --- | --- | --- | --- | --- | --- |
| predicted → marking run center | 42,296 | 3.884612 | 409.889217 | 608.405860 | 818.508466 | 1137.649348 |
| marking run center → prediction | 36,991 | 2.715234 | 178.647916 | 343.351548 | 711.153958 | 1092.550494 |

GT eligible94/119; usable79; unavailable40 (includes25 no-GT frames and15 eligible frames without prediction). Failure rate15/94=15.9574%; available ratio79/119=66.3866%. Marking row-run support coverage56.6621%; off-marking predicted-point ratio68.0469%; unmatched exact-mask-run ratio43.3379%. Pred→GT width-normalized p95=.522685. These are exact paint-mask support conventions, **not** official F1 or ego-boundary accuracy. The detector's continuous inferred lane and visible/dashed-paint masks have different semantics; the cause of every large tail is unresolved. Do not infer real lane quality from small median or discard the tails.

Near/mid/far distributions are in the receipt. Far field has no supported GT/pred pairs; errors remain null rather than zero. Runtime median/p95 around22/34ms per image excludes preprocessing/mask evaluation and includes CUDA synchronization; hardware-specific diagnostic only.

### Discarded adapter run and review

[Original adapter run](public-lane-detector-adapter-v1-discarded.json) remains byte-identical. It had82 whole-frame geometry exclusions because the adapter mistakenly treated legitimate off-canvas spline samples as invalidating all lanes. It is DISCARDED_ADAPTER_ERROR_NOT_DETECTOR_VERDICT.

V2 protocol was frozen before rerun with explicit prior semantic GT/output inspection and prior result SHA. Same sample selection/source/config/weight/confidence/scenario; no threshold relaxation. Evidence tier: POST_RESULT_ADAPTER_CORRECTION_DIAGNOSTIC_NOT_QUALIFICATION. Subsequent integrity fixes changed runner source/environment identities, not model/selection/metric parameters.

Independent review found three Important defects: unchecked metadata/weight reread, possible swapped/duplicated masks and unequal geometry, and unverified prior protocol/result lineage. Fixed with RED→GREEN regression tests; canonical path aliases also reject. Portable CPython omissions required glibc memfd_create and documented Linux UAPI seal constants. Final rerun consumes sealed weight, verified exact buffers and verified prior lineage; reviewer confirmed result/source/environment/protocol/manifest/prediction binding.

## Handoff

IMPLEMENTED: reproducible real GPU execution and public subset error distributions, exact repeatability, strict consumed-input bindings, unavailable counts and closed private gate.

BLOCKED: official CULane reproduction, full comma10k/CULane custom benchmark, justified pixel thresholds/confidence calibration, metric-capable GT/calibration, private human/domain validation, ego association, road registration and desired-path provenance. [Machine-readable report](public-lane-detector-blocked-report.json). Private inference/human manifest/sealed reference NOT_RUN. No PUBLIC_GT_PASS, qualified winner or estimator-ready state emitted.

Remaining risks: post-result adapter correction is diagnostic only; full benchmark supplier access and justified protocol are required before qualification. External /tmp cache is reproducible from pinned identities but may be ephemeral; no binaries/datasets/raw images added to Git. Checkpoints/source/dependencies must be reverified after reacquisition.

REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Actual performance qualification: BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
Rollback: remove new offline modules/records, retaining prior audited baseline; no production configuration changed. Commit references recorded in Git/handoff.

### Re-execution notes

Keep all acquisitions/environment/cache outside Git. Clone the pinned detector, acquire the exact official weight and DLA initialization checkpoint (recorded toolchain/cache SHA), then recreate Python3.11.9/CUDA12.1/GCC11.4. Install the exact package manifest with the cu121 torch and cu121/torch2.1 mmcv wheels; nms==0.0.0 is a **local build from pinned source**, not a PyPI download. Build its original setup.py with TORCH_CUDA_ARCH_LIST=8.6 and compiler identities in the toolchain manifest.

The .lock files are exact resolved manifests/explicit toolchain URLs, not a portable cross-platform environment guarantee. Recollect/review the runtime receipt on another OS/GPU/driver; changed identity cannot masquerade as this run. Do not skip SHA verification after cache expiry.

The complete executed invocation is in execution-details.json. The runner rechecks installed versions/source/config/kernels, verifies immutable initial manifest/protocol and prior discarded result, seals the public weight and runs twice before aggregating. The legacy initial protocol is retained byte-for-byte for the diagnostic correction chain; do not edit it retrospectively. This does not enable private file reading or change public qualification status.
