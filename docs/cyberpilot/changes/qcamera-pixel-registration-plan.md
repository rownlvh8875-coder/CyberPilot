# Qcamera pixel registration implementation plan

Goal: source-bound qcamera/native software registration with no invented scaler phase or physical calibration.
Baseline aed8b348c; user specification 2026-10-09. Existing frozen detector/60-frame annotations/metrics stay unchanged.

Architecture: a separate registration module and immutable source/evidence receipt, strict projection integration,
and a standalone offline schematic. Historical recording commit and current checkout are audited separately.
Tech: NumPy/Pillow/stdlib, existing browser harness; no dependency changes.

Global constraints: no detector inference/tuning; no new holdout opening; no model/path/candidate payload access;
no raw private data/coordinates/paths publication; no independent physical measurements or sealed reference.

Review focus: hardware scaler phase cannot be inferred from PC fallback; codec padding differs from optical crop;
recording source differs from current source; normalized detector output differs from resampler centers;
software round-trip does not prove physical pixel registration.

- [x] Audit actual historical recording source and whitelisted metadata of already selected development segments.
  Freeze exact source SHAs, sensor/role/dimensions and unresolved hardware/firmware phase/crop/distortion evidence.
- [x] TDD registration arithmetic: crop/anisotropic/half-pixel/center conventions, known points/grid/inverse,
  principal-point K transform, source/sensor/dimension identity and stale/fail-closed gates.
  Add qcamera_pixel_registration.py with explicit conditional hypotheses if exact hardware semantics remain unknown.
- [x] TDD preprocessing/restoration and human canvas coordinate mapping with real frozen sources;
  preserve historical coordinates and expose any semantic limitations, no corrective recomputation.
- [x] Tighten physical_projection_uncertainty.py to require source-bound VALIDATED registration,
  leave numeric results null while current registration pending. Legacy boolean-only mapping is rejected.
- [x] Offline schematic and actual browser tests: coordinate diagram, principal points, labels;
  existing assisted UI tested with synthetic images only, multiple CSS scales/DPR/pointer modes.
- [x] Document source pipeline, empirical availability, mapping residual and physical calibration separately;
  publish redacted immutable receipt and updated blocker dependencies.
- [x] Final focused, full AutoTune/controls, Ruff, syntax, publication/privacy/authority/diff, SCons, browser,
  independent review completed locally. Commit/push and final local/origin/CI verification follow this precommit record.

Native is defined here as the published VisionIPC/intrinsics image, not full raw sensor-array coordinates.
No execution-method question: user explicitly authorized autonomous implementation, verification, commit/push.
