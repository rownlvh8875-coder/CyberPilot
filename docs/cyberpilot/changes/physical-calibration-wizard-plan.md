# Physical calibration wizard implementation plan

Baseline 926b86e0de1120fe195a1648fc02eb1a3a985e21 fetched; equal origin; clean.
User specification supplies complete design and autonomous execution authority.

New isolated wizard maps explicit observed inputs into unchanged authoritative
camera_calibration_evidence.py; existing contracts/results remain byte-identical.
No actual measurements, private comma4 reads, controller writes or external network.

1. TDD session/model: blank draft, strict explicit units/provenance/uncertainty,
   degrees converted to radians with original input frozen in local package,
   physical/static/phone tiers distinct, evidence opaque content hashes,
   atomic editable draft and versioned immutable admitted package, recovery marker.
2. TDD loopback frontend/server: staged device/position/angles/target/ground/
   distortion/evidence/preview; no defaults, no model importer, all-local assets,
   Host+Origin+nonce checks, CSP, request bounds, private root outside repository.
3. Actual browser via existing bundled Playwright: blank workflow, all stages,
   invalid inputs, save/reload, local attachment, preview/admit TEST_ONLY fixture,
   no external requests, no JS errors, shutdown. No real measurements.
4. User field guide + feature record/pending readiness + validation receipt.
5. Independent read-only review; regressions for defects; freeze source;
   focused/full AutoTune >1359; Ruff/syntax/publication/authority/privacy/diff/SCons.
6. Logical commits and normal push; verify local/origin equal and clean.

No target pattern solver/detector/calibration fit is introduced. Survey geometry
and independent metrology must be provided; wizard cannot certify them. Generic
printable measurement sheet may contain blanks and size-control instructions,
never a nominal physical dimension accepted as observed truth. Phone/informal
tier is not admitted. Ground/distortion unknown blocks admission. No real actor
completed a submission this increment: CALIBRATION_MEASUREMENT_PENDING.
