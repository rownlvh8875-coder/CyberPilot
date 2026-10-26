# Qcamera pixel registration: source-defined infrastructure, actual mapping pending

## Identity and purpose

Cyber Validation / offline software coordinates. IMPLEMENTED, PARTIAL, physical validation BLOCKED.
Baseline aed8b348c30dc3601343c4f6fa8f16f8f27030f5, branch feature/cyber-autotune.
The frozen assisted holdout, detector, annotations, matching policy and historical metrics are unchanged.
The task is to establish the original526×330 image-to-native camera mapping before meter diagnostics.
No new holdout, image decode, inference, vehicle/device access or actual physical measurement occurred.

**Result: PIXEL_GEOMETRY_REGISTRATION_DEFINED_STRUCTURAL_ONLY /
PIXEL_GEOMETRY_REGISTRATION_PARTIAL. Actual exact transform is not yet established.**
No PIXEL_GEOMETRY_REGISTRATION_VALIDATED claim, actual K_q, transformed historical points or meter output.

## Original references and source pipeline

MIT recording source is [ajouatom/openpilot at5a970f1a](https://github.com/ajouatom/openpilot/tree/5a970f1ad25d9f07d055955d7a7c14603b6b7813),
traced separately from the current CyberPilot checkout.
All60 existing development initData.gitRemote values bind this public origin; GitHub's commit API
confirms the exact SHA there. The earlier audit's repo_url denotes the CyberPilot audit checkout,
not the recording repository; the separate origin-binding receipt makes this distinction explicit.
The recording commit is not an ancestor of this branch. Offline regression verifies the pinned
completed audit receipt rather than depending on an unreferenced local Git object or network fetch.
The original audit rehashed all16 recording files from that Git object.
The immutable source audit lists exact file SHA-256 identities; no external implementation/dependencies copied.
Submodules and licenses unchanged. Detector/source config identities and public results remain historical.

Metadata from the same60 previously opened DEVELOPMENT source segments reports:
mici60/60, clean recorded commit5a970f1ad25d9f07d055955d7a7c14603b6b7813, OS19.8-carrot-bt1.
There are180 narrow-road sensor observations, all os04c10.
This is log-observed identity/source probe correspondence, not independent hardware inspection.
Only initData and camera-state sensor metadata were accessed; model/candidate/live-calibration payloads were not read.
Each existing qcamera file was rechecked against its frozen source SHA before metadata inspection.
No paths, route names, timestamps, GPS, image bytes or human coordinates are published.

Recording-source trace:

1. openpilot/system/camerad/sensors/os04c10.cc and os04c10_registers.h:
   active output2688×1520, out_scale2. Sensor register trims precede the published image;
   they must not be counted as a qcamera-specific crop.
2. cameras/spectra.cc camera_open and camera_common.cc buffer construction:
   VisionIPC NV12 image1344×760. Stride/y-height/UV alignment are buffer-layout properties.
   **Native in this contract means this VisionIPC/static-K image, not the full raw sensor array.**
3. loggerd/loggerd.h chooses VISION_STREAM_ROAD, qRoadEncodeData, qcamera.ts, H264526×330.
   Current checkout names these VISION_STREAM_NARROW_ROAD / qNarrowRoadEncodeData.
   It would be incorrect to assume the current encoder implementation was the recording implementation.
4. loggerd/encoderd.cc obtains the actual VisionIPC dimensions and constructs V4LEncoder.
   The recording V4L encoder passes NV12 input1344×760 and H264 output526×330 through VIDIOC_S_FMT.
   Its explicit crop branch is for youtubeRoadEncodeData; the separate livestream override also does not apply to qcamera.
   No application qcamera crop, letterbox, rotation or mirror operation was found.
5. The hardware VIDC driver/firmware performs scaling. Effective hardware crop/defaults,
   interpolation phase, orientation defaults and ISP distortion geometry remain unverified.
   Absence of an application crop call is not proof of a particular firmware sampling convention.

The PC FfmpegEncoder/common/yuv.cc fallback uses floor(x×src_width/dst_width) point sampling.
**That PC rule is not evidence of comma4 hardware scaler behavior.**
File/segment encoder rotation is not image rotation.

Official kernel reference:
[commaai/agnos-kernel-sdm845](https://github.com/commaai/agnos-kernel-sdm845/tree/b53ae06564df3d34f6914c5d0699594913b16626).
msm_venc.c → msm_vidc_common.c → hfi_packetization.c passes input/output frame-size properties.
Exact file hashes and GPL-2.0 provenance are recorded; source was inspected outside the repo, not copied.
This reference is **not bound to the recorded19.8-carrot-bt1 runtime** and does not prove firmware phase.
No flashing or device execution was performed.

## Encode/decode geometry evidence

All60 existing development sources yielded4800 SPS observations:
coded528×336, progressive4:2:0, visible526×330, display crop left0/right2/top0/bottom6.
SPS parsing inspects bitstream metadata without invoking an image codec.
This crop removes codec padding, not a native optical crop.
All corresponding segments lack a native/high-resolution fcamera stream (0/60 paired sources).
EMPIRICAL_MAPPING_VALIDATION_UNAVAILABLE: no fabricated source pair, image residual or residual bound.
H264 RGB compression residual would not, by itself, be a pixel-position calibration.

## Software mapping and intrinsics transformation

qcamera_pixel_registration.py defines strict dimensions/receipts, conditional affine arithmetic,
inverse transforms, conditional K transformation, source identity checks, SPS geometry inspection
and a self-contained schematic. Forward q→native hypotheses use:

- ZERO_ORIGIN: x_n = left + x_q×crop_width/q_width.
- CENTER_ALIGNED: x_n = left + (x_q+0.5)×crop_width/q_width −0.5.
- CORNER_ALIGNED: x_n = left + x_q×(crop_width−1)/(q_width−1).

The analogous y mapping uses its own scale;1344/526 differs from760/330.
These are explicitly conditional examples, not an exhaustive hardware uncertainty envelope.
Actual crop rectangle, resize rule, affine coefficients and mapping residual remain null.
The full application input rectangle is recorded separately from effective hardware crop.

Coordinates use x=column to the right, y=row down, top-left pixel-center index0.
Source pixel-center/physical sensor phase applicability is still part of pending hardware evidence.
For an evidenced affine n=Aq+b, K_q=A_homogeneous_inverse K_native.
This preserves crop offsets, half-pixel offsets and anisotropic fx/fy/cx/cy transforms.
Conditional examples are STATIC_INTRINSICS_PRIOR_PLUS_CONDITIONAL_IMAGE_TRANSFORM,
not independently measured intrinsics. Actual SOURCE_DERIVED_QCAMERA_INTRINSICS is NOT_GENERATED.

For lateral error at fixed y, the x Jacobian is scale_x; offsets cancel in coordinate differences.
No scalar conversion of historical error statistics is published while actual mapping is pending.

## Detector restoration and annotation coordinates

Frozen CLRerNet input: source526×330 → OpenCV INTER_LINEAR1640×590 →
test crop[0,270,1640,590] → Albumentations resize800×320.
Model preprocessor mean0/std255/BGR, no test flip or letterbox; confidence threshold0.41 unchanged.
Head restores normalized y with (y×320+270)/590.
The frozen executor samples the normalized Lane spline at y=row/source_height and stores
x=x_normalized×source_width, y=row in original526×330 coordinates.

This normalized lane representation is **not an exact inverse of image resampling**.
OpenCV pixel-center sampling and normalized spline restoration are separate semantics.
The representation round-trip tests establish the existing stored-coordinate rule only;
no historical point was corrected, detector rerun, threshold changed or result invalidated.

The unchanged assisted annotation UI maps PointerEvent CSS client coordinates through the
actual canvas bounding rectangle into backing pixels, then inverses zoom/pan.
Device pixel ratio is not multiplied into CSS event coordinates.
Actual Chromium synthetic tests at viewport1200/DPR1/mouse and390/DPR2/touch verify this unchanged
handler, responsive canvas sizing, zoom/pan and draft save/reload.
Maximum original-coordinate numerical error:1.43e−13px. No private image/annotation was used.

## Distortion and physical calibration limits

No application rectification was found in the audited qcamera path.
Raw sensor geometry, BPS/IFE processing, static-K convention and firmware lens geometry are not
independently proven equivalent to an undistorted pinhole image.
DISTORTION_UNVERIFIED and NATIVE_INTRINSICS_APPLICABILITY_PENDING remain explicit.
Software arithmetic exactness does not create physical mapping residual0.

Actual physical measurements:0. Static hardware K remains a source prior.
The unchanged stationary target UI currently requires native1344×760 original-image input
and checks original dimensions/source;526×330 must not be relabeled native.
The wizard/target solver is not extended to accept qcamera by guessed scaling.
A future qcamera target path requires validated registration, transformed K and distortion accounting.
INTRINSICS_VALIDATION_PENDING and independent physical validation remain separate.

physical_projection_uncertainty.py now rejects the former boolean-only mapping declaration.
Both report and envelope require a validated source-bound registration.
The pinned audit cannot admit actual VALIDATED status while hardware proof is absent.
Explicit TEST_ONLY geometry controls continue to exercise synthetic numerical uncertainty tests,
and cannot bind an INDEPENDENT_PHYSICAL calibration receipt.
A partial registration returns PIXEL_GEOMETRY_REGISTRATION_PENDING with meter_results=null.
Registration alone cannot satisfy the independent calibration gate.

## Regression risk and acceptance

No metrology, qualification or residual threshold is invented.
Synthetic affine tolerance2e−13px is numerical round-trip tolerance, not physical uncertainty.
All99 fixed grid points round-trip with maximum≤5.69e−14px across the three hypotheses.
Known endpoints, crop offsets, half-pixel semantics, anisotropy, principal-point mapping,
wrong sensor/dimensions, stale/tampered receipts, scope firewall and meter blocking are tested.
Malformed/unsupported source metadata is rejected; missing proof has no heuristic fallback.

Only qcamera infrastructure, its new evidence/docs, the uncertainty mapping gate and tests change.
Existing physical admission, stationary solver, independent geometry, detector, UI, production
controller/comparator/candidate/A3 policies and source images remain unchanged.
Rollback is a normal revert of this isolated increment; it does not authorize the old boolean mapping.

## Immutable evidence and blockers

- qcamera-source-pipeline-audit-v1.json: source/metadata/kernel reference receipt.
- qcamera-recording-origin-binding-v1.json: separately binds the actual public recording repository.
- qcamera-display-geometry-audit-v1.json: metadata-only codec display geometry.
- qcamera-pixel-registration-v1.json: source-bound partial registration; no actual affine.
- qcamera-pixel-registration-readiness-v1.json: separate new blocker snapshot and conditional99-point tests.
- qcamera-pixel-registration-validation-v1.json: executed software checks and source identities.

The previous readiness snapshot remains immutable.
Software registration and physical calibration are parallel prerequisites for metric calibration;
actual physical evidence does not automatically prove encoder crop/phase.
Next priorities: bind recorded runtime/firmware; establish effective crop/sample phase;
obtain an authorized same-frame native/q pair if one becomes available; validate distortion and
intrinsics applicability; justify a residual bound; independently measure stationary calibration.

Historical60-frame assisted reference remains AI_ASSISTED_HUMAN_PIXEL_REFERENCE.
Ego-center median1.937923236290544px, p955.053136006631054px and unavailable11 remain526×330 metrics.
Native historical derivative NOT_GENERATED; actual meter diagnostic NOT_RUN.
The32 new tests and tightened old uncertainty fixture are synthetic, not measurement evidence.

## Validation method and actual results

Executed results are recorded in qcamera-pixel-registration-validation-v1.json.
Focused67/67 (32 new registration +35 existing calibration/uncertainty/UI), AutoTune1711/1711, controls142/142, replay16/16, Ruff, syntax, publication/privacy/authority,
git diff, SCons, Chromium and separate independent review PASS before commit.
Post-push CI is verified for the final commit; the precommit receipt does not claim a future run passed.
Replay and closed-loop tuning changes are not applicable: this increment changes no controller.
Shadow/vehicle execution is NOT_RUN and not authorized.

To generate the standalone offline schematic without private inputs:

~~~python
from pathlib import Path
from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q
Path('/tmp/qcamera-coordinate-map.html').write_text(q.visualizer(q.source_registration()))
~~~

Open the local HTML; all CSS/JS/SVG is inline. It shows native and qcamera rectangles,
source and conditional principal points, known synthetic points and selectable hypothetical conventions.
No external assets, server or private image is required.
If served, bind127.0.0.1 only. It is labeled SOFTWARE COORDINATE REGISTRATION / NOT PHYSICAL CALIBRATION.

## Handoff

Source/runtime evidence narrows the problem without inventing the final transform.
Exact hardware mapping and its residual are PENDING; physical measurement/validation remain PENDING.
CALIBRATION_MEASUREMENT_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE and INDEPENDENT_REFERENCE_UNAVAILABLE remain BLOCKED.
Independent blind-review, official CULane, ego association and desired-path blockers are not cleared.
Sealed reference NOT_GENERATED. NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No vehicle application, controller change, raw publication or new private access is authorized by this result.
