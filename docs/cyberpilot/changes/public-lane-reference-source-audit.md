# Public lane-reference feasibility, detector freeze and blocked promotion

## Identity and purpose
- Cyber Validation / AutoTune; IMPLEMENTED audit and blocker contract, independently reviewed source/code consistency.
- Scope: test whether existing public lane GT can support an independently sourced estimator without new driving-data collection. No private frame semantic open, detector inference, training, selection or reference emission in this increment.
- Branch feature/cyber-autotune; baseline0673adeeea973986efc404ac86c021b94a3c9459. Source/config protocol SHA113d5bc94b11fb11aee24986cf1ef2b78d4c0f9a26742959382d2df3274cdb3c; source and weight identities in public_lane_reference_policy.json and public-lane-reference-source-audit.json.
- A metadata/source/config declaration freeze is not a complete execution freeze or selected qualified detector. No actual performance qualification.

## Original references
- [comma10k](https://github.com/commaai/comma10k/tree/6c205fe4c43cc53b2b1befafb1060d0606555027), master, MIT. Full Git tree metadata SHA e34b96b6bfcdf8c660fa5d907471828b5e52b9822c10e4f7dd26f6d77f0529e3. README, size-check and palette scripts are individually hashed in the audit.
- [CLRerNet](https://github.com/hirotomusiker/CLRerNet/tree/dae038f67da57e292e5293a68c9c1c2922de13c2), main, Apache-2.0 code; [CLRNet](https://github.com/Turoad/CLRNet/tree/7269e9d1c1c650343b6c7febb8e764be538b1aed), main, Apache-2.0 code; [UFLDv2](https://github.com/cfzd/Ultra-Fast-Lane-Detection-v2/tree/c903880678454dfd9b55a63022368db05c00bc6d), master, MIT code. Fixed three-member roster before any public GT pixel decode or private frame open.
- Official CLRerNet non-EMA CULane DLA34 release weight downloaded63,464,485 bytes; SHA424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa. Primary reproduction target only, no selected detector.
- CLRNet official DLA34 ZIP SHA4e753261408cbf8f329523699d82d83cc596a581415aa1b6b9df692084046095; contained weight SHA3750c1b1a93a4c77c1e159c0f76d60a1b17c7960f1a60f8dd6b4c8ea11917c7c. UFLDv2 official Drive request returned HTML; weight SHA remains null.
- Config bundles/root, training dataset, preprocessing/output/confidence semantics, requested dependency recipe and absent executable environment SHA are separate fields. Source license alone does not authenticate weight/data rights; CULane derivative restrictions still apply.
- Traced pipeline: public GT/explicit detector samples → pixel diagnostic; independently calibrated camera → projection diagnostics; reviewed reports/provenance → future separately sealed manifest → unchanged strict reference admission. Missing prerequisites stop before private inference.
- Existing opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged. No upstream/detector code copied into CyberPilot.

## Changes and expected effect
- New lane_reference_qualification.py and public_lane_reference_policy.json pin this audit-only v1, source/config/weight roster and null qualification thresholds. Protocol canonical digest and literal frozen SHA reject edits, unknown fields, boolean-version substitution or caller-selected detector. Report has12 deliverable entries and child blockers, deterministic receipt, producer-source SHA and audit file SHA bindings.
- No STATE PASS/READY transition implementation in this version. Enum names are the future protocol vocabulary; actual detector state stays DETECTOR_UNVERIFIED, reference state REFERENCE_UNAVAILABLE.
- Audit JSON records source inventory, official reported scores separately from null measured scores, metric-capable dataset limitations and scoped environment probe. BLOCKED report is rejected by existing exact-key reference admission.
- Architecture alternatives: a full detector producer now would require inventing acceptance/calibration facts; a documentation-only warning would not protect later integrations. Chosen structural blocker contract plus separately tested pixel/projection kernels preserves the evidence boundary.
- State/delay: pure report construction, no persistent controller state, physical queue, profile or runtime integration. No fallback, interpolation or private raw loader.
- Rollback removes the new offline modules/records. Existing production controller, comparator, A3 rejection and original frozen reference memfd/no-follow admission are untouched.

## Public data inventory and capability
| Source | Verified or declared role | Limit |
| --- | --- | --- |
| comma10k imgs |9,888 image/mask filename pairs | Full tree pairing; no semantic mask completeness/quality check |
| comma10k imgs2 |2,000 image/mask pairs,1,000 exact e/f capture pairs | Paired fisheye domain; no authenticated per-frame road device/sensor generation |
| comma10k imgsd |741 interior images,511 masks,230 missing | Driver camera, excluded from road benchmark |
| comma10k geometry | Nominal1164x874 old;1928x1208 new/interior from official size checker;7 deterministic PNG header samples match | Header samples do not prove all files' dimensions. No pixels decoded |
| comma10k labels/split |Category2 red marks all lane markings; no ego identity. files_trainable:10,863 eligibility entries; README informal filename-suffix validation | No dedicated full train/validation split; eligibility is not a held-out split. Initial segnet/human-touch-up provenance needs label quality review |
| CULane |Official88,880 train /9,675 validation /34,680 test; pixel splines, ordered four marking existence bits | Context-inferred occluded markings; no audited camera metric calibration. Non-commercial/personal research, citation/no redistribution |
| TuSimple |Official3,626 train /2,782 test; x/h_samples pixels; unknown points-2 | No official calibration in inspected contract.358 validation is an external split convention, not established as official here. Code license does not establish separate raw-data terms |
| LLAMAS |1276x717, automatic LiDAR-map/image-optimized labels | Download login; dataset non-commercial, code MIT.3D/calibration release and uncertainty not verified |
| Pandar128 |Pinned code f3bc4f9e7c2f7e6b06b6b1db521c11f3cbb56663 and HF3366842fa701e4e5ec313f9124acb84b502f11ee; both MIT notices; matching Configuration SHAec511a4259daa41578f88c4c60054c85d8fc3569da6e2e6c187280b4b907213a | Metadata specifies calibration/distortion/odometry/XYZ polylines; archives and GT alignment unopened. Published frame counts disagree. Candidate metric benchmark, not validated metrology |

[Official CULane terms](https://xingangpan.github.io/projects/CULane.html), [TuSimple contract](https://github.com/TuSimple/tusimple-benchmark/tree/d1f5ef1b6fff78c92c61864abcc07a9714900360/doc/lane_detection), [LLAMAS labeling](https://unsupervised-llamas.com/llamas/), [Pandar128 distribution](https://huggingface.co/datasets/filipberanek/pandar128-lane-line-detection/tree/3366842fa701e4e5ec313f9124acb84b502f11ee).

CLRerNet official test config crops CULane1640x590 to800x320, BGR/255, conf0.41, extend_bottom=True. Original benchmark reproduction would keep that official configuration; arbitrary comma10k/comma4 geometry requires an explicitly frozen adapter and unavailable support mask. Demo interpolation/bottom extrapolation cannot manufacture missing reference points. Class confidence is not calibrated localization probability.
Official published F1 values (CLRerNet81.11/non-EMA; EMA81.55; CLRNet80.47; UFLDv2Res34 76.0) are source claims, never measurements from this work or CyberPilot qualification thresholds.
The prepared .venv lacks torch/cv2/scipy/mmcv/mmdet/mmengine; audited CULane archive/list/GT inventory is not available in this track cache. No dependency installation or partial benchmark masquerading as official reproduction. CLRerNet backbone pretrained=True can also fetch ImageNet weights during initialization; exact initialization asset and offline execution recipe still require freeze.
All public/private measured accuracy, coverage, confidence reliability and domain-gap statistics remain null / NOT_RUN. No training or detector selection occurred.

## Regression risk and acceptance
- Undefined median/p95/failure/coverage/confidence/total-uncertainty promotion thresholds are BLOCKED_UNJUSTIFIED. Published F1 matching tolerance and existing synthetic .01 fixtures cannot substitute for a justified downstream meter error budget.
- No result-dependent threshold editing, new detector addition, private selection, easier-frame selection, interpolation, prior-frame carry or modelV2/candidate fallback.
- Future human holdout protocol is declared before outputs: independent frame manifest, straight/curve/speed/lighting/marking/road/day/night/weather strata, ego left/right/unavailable/ambiguous/visibility labels, no detector overlays or fine-tuning. Actual sample list and human review SHA are unavailable; no human labels manufactured.
- Digests prove consistency only. Timing/source/license/independence claims need external review; no promotion authorization can be obtained by editing/re-hashing a receipt.
- Independent reviewers inspect source counts, sensor/calibration chain, derived units and missing-evidence semantics; actual qualification remains separate authority.

## Validation method and actual results
| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | TDD RED module absence and malformed-result regressions → focused pytest; tools/test_runner.py -j2 openpilot/tools/cyber_autotune/tests; export PATH=$PWD/.venv/bin:$PATH; .venv/bin/scons -j2 | WSL Ubuntu24.04 Python3.12.13; source/config protocol and JSON receipts | Focused27/27 PASS; full1009/1009 PASS281.87s; SCons100% PASS; Ruff/py_compile/publication/authority/privacy/diff PASS |
| Public GT replay | Official intended python tools/test.py config weight; metadata/source/download probes | All exact source/weight identities in JSON, no deserialization | NOT_RUN/BLOCKED: execution environment, dataset identity and promotion budget missing |
| Simulation / closed loop | Pure synthetic analytical pixel/ray fixtures only | No native candidate modification/execution for this track | No measured detector performance or lane truth |
| Shadow | Not applicable: offline no actuation | No CAN/Params/CarController/device/profile/runtime network integration | No vehicle application |

## Handoff
IMPLEMENTED: reproducible official-source audit, pinned detector declaration and machine-readable12-deliverable blocker report; pure metrics/projection groundwork.
SYNTHETIC SCREENING: analytical unit fixtures only; public benchmark reproduction, detector selection, private inference, human cross-validation and metric uncertainty are NOT_RUN.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE, with explicit thresholds/public reproduction/environment/geometry/holdout/confidence/calibration/error-budget/road-registration/desired-path/producer child reasons.
The public route is a viable research direction, but this audit cannot remove the blocker. Next independently review the downstream metrical uncertainty/coverage requirements and complete the official frozen public execution environment/data inventory before any promotion or private opening. Separately validate mount geometry, pose/road registration and independent desired path. No new driving collection demanded.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No raw public datasets/weights, private frames/logs, credentials or binary artifacts committed; all downloads stay in an external local cache. Commit/push follow the completed final gates; validation identities in public-lane-reference-validation-results.json.
