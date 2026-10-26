# Stationary target calibration and uncertainty implementation plan

Goal: prepare actual independent stationary observations, never invent measurements.
Baseline: 6da307858; existing detector, assisted holdout, calibration admission unchanged.
Architecture: new local target capture/pose module, bounded projection diagnostics, separate loopback UI.
Spec: user request dated 2026-10-09. Existing authoritative camera_calibration_evidence remains the only admission validator.
Tech: Python/NumPy/Pillow and stdlib HTTP; no runtime dependency changes.

Constraints: no private log crawl, no detector tuning, no model-derived solver inputs, no sealed reference,
no calibration admission from convergence. Camera height and all physical bounds must be observed.
Static intrinsics and unknown distortion remain separate pending evidence.

Review focus: planar ambiguity; image resolution mismatch; missing physical survey; pixel quantiles are not absolute bounds;
road horizon crossing; local publication leakage.

- [x] TDD: measured target scaling, image/source binding, height repeats, known-pose/sign and degenerate solve.
- [x] Implement stationary_target_calibration.py: printable existing checkerboard, six observed labeled corners,
  normalized homography pose with numerical conditioning, immutable local capture/solve receipts.
  Unknown distortion permits explicitly nonqualifying pinhole diagnostics only; no automatic admission.
- [x] TDD: projection finite differences, interval domain bounds, unavailable coverage and historical pixel identity.
- [x] Implement physical_projection_uncertainty.py: admitted calibration only for numeric meter diagnostics;
  first-order terms, deterministic nonlinear perturbation check, interval envelope; p95 remains a quantile, not bound.
- [x] TDD and actual browser: separate stationary_target_ui.py with raw-image import/corner marking,
  blank measured fields, draft/reload, solve preview, mobile responsive local assets, host/origin/nonce guard.
- [x] Field guide and readiness-only publication, all actual measurement/solve/meter results NOT_RUN.
- [x] Focused/Ruff/syntax/publication/privacy/authority/diff/SCons/browser and independent review.
- [x] Full AutoTune1679/controls142:1821 PASS.
- [ ] Commit/push and latest CI SUCCESS; verified after publication without creating a self-referential commit receipt.

Execution is authorized by the user's instruction to implement/verify/push autonomously.
