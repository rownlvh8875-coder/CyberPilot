# Frozen secondary detector comparison

## Identity and purpose

IMPLEMENTED public diagnostic comparison, not detector selection/qualification.
Branch feature/cyber-autotune, baseline41cfd0c1f. Test whether the tail is unique to
CLRerNet using the previously declared CLRNet, same119public image/mask pairs.
No private inputs, ensemble, retraining or thresholds changed.

## Original references

[Turoad/CLRNet](https://github.com/Turoad/CLRNet/tree/7269e9d1c1c650343b6c7febb8e764be538b1aed),
Apache2, pinned7269e9d1c1c650343b6c7febb8e764be538b1aed; NMS BSD3 retained.
Official DLA34 CULane weight3750c1b1a93a4c77c1e159c0f76d60a1b17c7960f1a60f8dd6b4c8ea11917c7c,
configs/clrnet/clr_dla34_culane.py. Source unchanged, dependency resolution external.
No production/submodule synchronization.

## Changes and expected effect

lane_secondary_capture.py checks actual source HEAD/bundle/config/kernel/weight,
freezes all installed package/platform/device/pre/post settings before inputs.
Separate environment: Python3.11.9, torch2.1.0+cu121, torchvision0.16.0+cu121,
mmcv1.7.2, NumPy1.23.5, SciPy1.10.1. Full exact package manifest is embedded in
comma10k-tail-clrnet-environment.json. The primary environment was not mutated.
Original CUDA NMS built with retained CUDA12.1/GCC11 toolchain; no source patch.

Input: same BGR original→1640x590→crop270→official imgaug Resize800x320,/255.
Output: official confidence.4,NMS50,top4,Lane spline, same original row sampler.
Same mask/metric/component graph/y/confidence bins. Raw Lane.metadata.conf is
positive-class LOGIT, not calibrated confidence: capture uses softmax on the
retained proposal logits, matching official thresholding. Official first2logits
remain unmodified by geometric decode.

Exactly four missing release keys are accepted: heads.sample_x_indexs,
heads.prior_feat_ys,heads.prior_ys are deterministic config-derived buffers;
heads.criterion.weight is training-only. Their initialized hashes are recorded;
other missing/unexpected keys fail. No permissive wildcard or random inference
weight substitution.

## Regression risk and acceptance

The initial strict-load attempt failed on these omitted keys and is recorded as
NO_INFERENCE, not a successful reproduction. Exact two-pass SAME-INSTANCE
repeatability then failed: official predictions_to_pred changes prior_ys from
float32 to float64, consumed by subsequent forward curvature coordinate algebra.
Only firstframe differed between passes. Failed repetition artifacts were captured externally
with their SHA in the public capture receipt; no rounding to manufacture equality.

Fresh-process first-pass output SHA matched another fresh process after validation
instrumentation changes, supporting the state-mutation attribution. This does not
overturn SAME-INSTANCE rejection or grant the currently frozen repeat protocol
PASS. Any future reset-protocol qualification requires a new explicitly frozen
experiment. No state/threshold workaround was silently applied here.

## Validation method and actual results

| Stage | Evidence | Actual result |
| --- | --- | --- |
| Inference |comma10k-tail-clrnet-capture.json |119x2 executed; SAME-INSTANCE exact FAIL on firstframe; REJECTED_FOR_EXACT_REPEATABILITY |
| Environment |comma10k-tail-clrnet-environment.json |source/config/weight/pre/post/compiled kernel/full packages bound |
| Directional diagnostics |comma10k-tail-clrnet-report.json |median4.055733,p95611.626766px; GT→pred p95323.074228px |
| Same-population spatial counterfactual |same report |p95136.991520px; original directional tail retained |
| Ledger / review |comma10k-tail-clrnet-ledger.json /human-review.json |all119, no images; human semantic review PENDING |
| Unit / regression / build |comma10k-tail-validation.json when finalized |actual checks separate from GPU repeat failure |
| Official reproduction |original planned CULane procedure |NOT_RUN, images/annotations inaccessible via accepted source |
| Replay / simulation / shadow |not applicable |controller untouched; private NOT_RUN |

Similar tails in two related CULane-trained architectures support a shared
representation/domain contribution, not proof of no detector error. CLRNet is
not an independent benchmark control for all architectural/training biases.
Both remain unqualified; no winner declared.

## Handoff

DIAGNOSTIC PUBLIC GT only. Secondary repeatability REJECTED, official benchmark
BLOCKED. No meter/ego/reference promotion. Public binaries/raw frames/weights
were external and subsequently lost with the volatile public cache; only
provenance/numerical reports survive in Git. See the full-attempt availability receipt. Remove new offline
files to roll back; production path unchanged.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Actual inference-only timings (exclude decode, localization and acquisition):
CLRerNet median22.675ms,p9527.157ms; CLRNet median23.729ms,p9532.223ms.
End-to-end throughput is separately measured in the full resource report.
Primary/secondary usable79/78 of119; no-prediction32/31 including GT-unavailable
frames. Exact row-paint coverage0.566621/0.561432; these are not ego-lane recall.
Confidence bins remain diagnostic, and CLRNet exact-repeat failure prevents
selection or promotion irrespective of its other distributions.
