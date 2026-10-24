# Approximate geometry diagnostic plan

Baseline 4190c7c65ad5ee1c58cae37a62846fc06bc22e6e fetched/equal origin/clean.
User gives bounded implementation scope and autonomous execution authority.

Separate APPROX_GEOMETRY_DIAGNOSTIC_V1, never an independent calibration receipt.
User-reported original degrees and rounded radians preserved. Explicit matrix
adapter: device-from-calib rotation E, optical-to-device V, FRD-to-FLU F;
optical-to-diagnostic-road R = F E^T V. Relative physical Euler rotation A =
F E^T F. Extraction is coupled, not a naive sign-flip/reuse. Model calibration
is a motion/model-derived prior, and assumed road alignment remains diagnostic.

1. TDD exact diagnostic prior/firewall, independent admission rejection, known
   ray height scaling, convention direction/inverse, deterministic bounded
   parameter enumeration, future physical consistency (never validation).
2. Vehicle owner identity not established by fixed replay/test CarParams.
   No official spec/height invented. Future declared official spec can constrain
   hypothetical geometry only; source validity is not certified by a hash.
3. No camera height default, no assumed measurement uncertainty. Normalized ray
   symbolic result gives affine height relation. Positive explicit height
   parameters can evaluate5/10/20/30m in camera-footpoint road axes with all
   source/assumption/policy bindings. Parameters are not plausible intervals or
   physical bounds. No pixel data/calibration inference.
4. TDD all-local loopback visualizer: blank heights, prior labels, parameter
   table/schematic, safe fixed routes, no network/CDN/telemetry beyond127.0.0.1.
5. Freeze current diagnostic artifacts + additive blocker snapshot, docs,
   focused/full AutoTune>1399, Ruff/syntax/publication/authority/privacy/diff,
   SCons, actual browser and independent read-only review.
6. Logical normal commits/push; SHA equality/clean tree.

Actual camera/unit/sensor identity, height, mount_x and physical uncertainty
remain unavailable. Private comma4 inputs never opened. Existing independent
calibration/wizard/geometry/blocker/comparator/history/A3 files unchanged.
