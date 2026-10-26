# Recorded Carrot runtime camera-stack audit

## Identity and purpose

Cyber Validation, additive offline audit, baseline
d32d5b65dbcfb8e5cabe9c0c54f93b4a4bf9adb5 on feature/cyber-autotune.
Implementation is complete; actual hardware registration remains PARTIAL.
The purpose is to narrow the 1344×760 VisionIPC → 526×330 qcamera mapping
without inventing a crop, sampling phase, intrinsics or physical residual.
Detector, assisted 60-frame holdout, historical registration and height artifacts
are unchanged. No images were decoded, no holdout accessed, and no inference run.

## Original references and source trace

The author [19.8-carrot-bt1 release](https://github.com/ajouatom/agnos-builder/releases/tag/agnos-19.8-carrot-bt1)
provides VERSION, PROVENANCE, SHA256SUMS, the C3X/C4 OTA manifest and boot image.
Their downloaded bytes/digests are bound in recorded-runtime-camera-stack-v1.json.
The boot XZ was SHA-verified, bounded-decompressed, raw-SHA verified and inspected
for its embedded kernel banner; it was never executed or flashed.

The release builder is
[f5b3f77e59f1917f95e0752630ca08050463eede](https://github.com/ajouatom/agnos-builder/tree/f5b3f77e59f1917f95e0752630ca08050463eede).
Its kernel gitlink and release provenance identify commaai/agnos-kernel-sdm845
[eccd146599f2e2f159d951092642689bede91632](https://github.com/commaai/agnos-kernel-sdm845/tree/eccd146599f2e2f159d951092642689bede91632).
The C3X/C4 workflow additionally applies c4-usbpd-v2.patch,
c4-usbpd-v3.patch and bluetooth-wcn3990.patch before building tici_defconfig.
Their hashes are bound separately: kernel_base alone omits these working-tree
patches. Their touched files concern USB/PD/DWC3/Bluetooth/DTS/defconfig;
no camera/VIDC source diff was found in these three patches.
The older b53ae065… kernel remains an exploratory reference.

Only the exact 60 previously opened DEVELOPMENT rlog sources were reread.
Each rlog SHA was checked against the prior immutable metadata cache. Access
was limited to initData OS/kernel/device and the whitelisted BUILD command.
No Params, model, liveCalibration, candidate, controller or image payloads were
read. All 60 BUILD commits match the release builder. All 60 complete normalized
kernel strings match the SHA-verified release boot banner: Linux 4.9.103, including
compiler/build identity. Normalization removes only the first two tokens
(Linux plus hostname/version) and outer whitespace. Publication includes hashes
and counts, not device hostnames, private paths, route names or raw timestamps.

This binds the recorded **build identity**, not cryptographic equality of the
device's boot/system partitions. Recorded logger source explicitly lacks
boot/system hashes; it does not populate an Android build fingerprint.
Loaded Venus firmware identity is also absent. A matching label/banner cannot
exclude a modified binary that retains that label.

The exact recorded application is ajouatom/openpilot
[5a970f1ad25d9f07d055955d7a7c14603b6b7813](https://github.com/ajouatom/openpilot/tree/5a970f1ad25d9f07d055955d7a7c14603b6b7813).
Every claim in qcamera-hardware-scaler-evidence-v1.json binds its source URL,
commit, file SHA and line locations. Kernel files retain GPL-2.0 attribution;
openpilot files retain their upstream MIT attribution. No external source,
firmware, boot binary or dataset is copied into Git. Existing submodule/model/
detector identities are unchanged; no new dependency or adopted control code.

## Source pipeline and limits

OS04C10 RAW12 2688×1520 → custom camerad IFE → NV12 VisionIPC 1344×760
→ MSM VIDC/HFI firmware scaler → H264 coded 528×336, visible 526×330.

Road-camera hw.h selects ISP_IFE_PROCESSED; BPS/CAMERA_ICP evidence belongs to
a different path and cannot prove narrow-road distortion behavior. OS04C10
out_scale is 2; spectra.cc derives output geometry and supplies IFE rectangles.
IFE contains crop/scaler register writes and vignetting/color processing.
Lens shading/roll-off is not evidence of geometric undistortion. Applicable
geometric register semantics and actual stage behavior remain unverified.

The recorded V4LEncoder submits NV12 input and encoded output dimensions through
separate V4L2 S_FMT queues. Explicit application crop is conditional on the
YouTube stream, not qcamera. The bound kernel maps sizes to HAL_PARAM_FRAME_SIZE,
then HFI_PROPERTY_PARAM_FRAME_SIZE containing buffer type/width/height.
Venus sends that packet to its firmware command queue. Q16 scaling capability
checks limit dimension ratios, not sample-center phase. No applicable public
phase/tap/crop-default specification was found at this firmware boundary.

Rotation/flip default to NONE in the bound kernel, and no qcamera override was
found in the application. This supports a SOURCE_DEFAULT_ONLY observation,
not an independently measured orientation matrix or proof of sensor mounting.
Conditional rotation arithmetic is explicitly separate from the actual mapping.

Codec display crop L0/R2/T0/B6 removes coded padding. It provides no optical
native crop rectangle. For 1344×760, the recorded NV12 helper gives stride 1408 bytes, Y scanlines
768 and UV scanlines 384. These are source-derived storage alignment values,
not an optical crop or proof of firmware sampling semantics. Actual effective crop and phase remain null.

Recorded camera.py maps OS04C10/mici fcam to 1344×760 with nominal
fx=fy=1141.5, cx=672, cy=380. This binds the **post-IFE VisionIPC source prior**
rather than the 2688×1520 raw sensor. It is not independently measured intrinsics,
unit-specific validation, or proof that distortion is preserved/corrected.
No actual Kq is generated.

## Empirical validation and conditional envelope

Existing inventory reports no paired native road stream in the 60 DEVELOPMENT
sources. No filesystem rescan or new image access was performed. No authorized
same-frame pair, known hardware calibration-grid pair, encoder conformance
vector or vendor positional residual bound is available.

Qualcomm's public SDM845 overview identifies the SoC but supplies no sampling
phase specification. The 2025 public Video Guide and other-generation scaler
documents do not establish this recorded SDM845 firmware's phase. Mainline
Venus documentation is context, not substitution for the bound downstream tree.
No restricted/unattributed debug document or unknown binary/mirror was used.

ZERO_ORIGIN, CENTER_ALIGNED and CORNER_ALIGNED all remain conditional.
The envelope assumes a full native crop and identity orientation and spans
only these three hypotheses. It is NON-EXHAUSTIVE, not a physical uncertainty
bound. Proprietary/polyphase behavior or a different effective crop can lie
outside it. No hypothesis is pruned and no residual bound is inferred from the
synthetic arithmetic.

## Changes, state and regression risk

A new pure offline module parses/redacts kernel identity, rejects mismatched
recorded/public builds, separates crop layers, computes conditional orientation/
envelopes and reproduces a pinned readiness DAG. It opens only checked-in
evidence; private metadata acquisition was a bounded local audit, not a runtime
hook. New JSON receipts preserve old receipts and give per-blocker outcomes.

| Existing blocker | Outcome | Remaining child evidence |
| --- | --- | --- |
| RECORDED_OS_KERNEL_BINDING_PENDING | PARTIAL | Boot/system binary attestation and loaded Venus firmware |
| HARDWARE_EFFECTIVE_CROP_PENDING | BLOCKED | Actual effective input crop/defaults |
| HARDWARE_RESIZE_PHASE_PENDING | BLOCKED | Firmware-opaque phase or independent position registration |
| DISTORTION_STAGE_ORDERING_PENDING | BLOCKED | IFE geometric semantics and observed ordering |
| NATIVE_INTRINSICS_APPLICABILITY_PENDING | PARTIAL | Unit/distortion validation; static source contract is bound |
| MAPPING_RESIDUAL_BOUND_PENDING | BLOCKED | Actual positional residual evidence |

No numeric tolerance or acceptance threshold was relaxed. The principal risks
are confusing build labels with binary attestation, padding with optical crop,
source defaults with observations, or conditional arithmetic with physical
bounds. Tests exercise these rejection paths. All actual forward/inverse
mapping, Kq, mapping residual and meter results remain null. Existing strict
registration/calibration admission is untouched; rollback is removal of this
additive increment, without replacing historical evidence.

The 1.385 m physical observation is bound only as context; formal uncertainty
remains pending. It is never an input for crop/phase inference. The 1.40 m coarse
prior, height sweep, model-derived orientation and 526×330 historical metrics
remain unchanged.

## Future target capture and next evidence

Native 1344×760 stationary target input remains the current supported path.
A future qcamera target path needs independently validated registration,
source-derived Kq, applicable intrinsics/distortion and physical target evidence
before execution. This increment grants no qcamera-target execution authority.

Next useful evidence is exact loaded firmware/boot/system identity plus either
applicable scaler semantics or an independently captured known-point/native–
qcamera pair. Physical pose/uncertainty measurement proceeds in parallel.
Height cannot substitute for either mapping or full physical calibration.

## Validation method and actual results

See recorded-runtime-camera-stack-validation-v1.json for final commands,
counts, exit codes and SHA-bound output logs. TDD first demonstrated the absent
binding API, then passed the focused audit cases. Full AutoTune/controls, focused
calibration/registration, explicit replay, Ruff, syntax, publication/privacy/
authority, diff and SCons are required before commit. Independent review is
required. Final local results: focused 104/104; AutoTune 1757 + controls 142 = 1899/1899;
explicit replay 16/16; privacy/authority 58/58. Ruff, syntax, publication (0 findings),
whitespace and SCons passed. Independent review found and then verified the fix
for a forged matching-banner API claim; its new regression passed. No remaining
review findings. No visualizer/UI changes; browser test is NOT_RUN / NOT_APPLICABLE.

Replay and simulation/controller behavior are unchanged. New simulation,
shadow, physical capture, device writes and vehicle application are NOT_RUN
and not authorized by this audit.

## Handoff and vehicle status

PIXEL_GEOMETRY_REGISTRATION_PARTIAL remains. CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE remain blocked. Sealed reference NOT_GENERATED.

Vehicle: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
