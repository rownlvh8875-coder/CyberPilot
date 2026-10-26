# Independent reference blocker dependency plan — IMPLEMENTED

## Identity and purpose

Cyber Validation; feature/cyber-autotune; baseline
e2decd536e16ccf27d900845665cb41c32a17d31. Update the evidence DAG after assisted29
aggregation while preserving every older blocker/history receipt.
This orders engineering work; it does not resolve missing evidence.

## Original references

CyberPilot's sealed curvature_yaw_reference_input/admission remains unchanged.
Reuse the exact prior comma10k-assisted-review-blockers-v1.json receipt
e10ac47cb038ff1d767f02dba2d1387beed3e102e6702ea034196b167a0281cb and reverify
its referenced evidence-file hashes. Existing physical calibration protocol,
Jacobian, public dataset/detector audits and full-run reports are inherited.
No new dataset, mirror, model, dependency or private input was acquired.

## Changes and expected effect

Added lane_tail_blocker_plan.py/tests, NEXT_BLOCKER_PLAN_V1 and a proposed
PRIVATE_PIXEL_DIAGNOSTIC_ONLY_V1 receipt. Consumers must validate the complete
assisted diagnostic, its exact public inputs and frozen original pooled metric
summary; scope cannot be promoted by merely resealing TEST_ONLY metadata.
Typed nodes distinguish supporting PASS, pending/BLOCKED and diagnostic history.
Every node has evidence SHA/kind, resolution condition and dependencies.
Deterministic topological ordering rejects duplicate/unknown nodes or cycles.

Current nodes include official CULane reproduction, full evaluation COMPLETE,
assisted human COMPLETE (supporting diagnostic only), blind reviewer unavailable,
ego-lane identity, metric calibration, independent extrinsics, physical
measurements, road registration, desired-path reference, confidence/public
threshold prerequisites and private-domain validation NOT_RUN.
The root remains BLOCKED. Completed diagnostic nodes cannot satisfy independent
geometry/qualification gates.

Dependency answers:

1. Yes, software calibration admission, registration/provenance contracts and
   clean second-review tooling can progress without a blind reviewer.
2. More public localization data cannot manufacture ego-left/right identity:
   comma10k masks label all markings. Independently validated ego association
   remains a separate gate.
3. Independent measured camera pose/height and uncertainty are a critical path
   for meter projection. Existing static intrinsics do not certify independently
   observed mount extrinsics or road-plane assumptions. Model-derived live
   extrinsics cannot substitute for missing measurements.
4. Road-frame registration must precede a coordinate-bound desired-path reference.
   Defining an independent desired-path source/provenance contract can proceed
   in parallel; a path origin alone is not registered metric truth.
5. Frozen-detector private pixel-domain gap diagnostics may be worth preparing,
   but the proposed contract is DESIGN_ONLY/NOT_RUN. This increment opens no
   private inputs and gives no execution exception to existing gates.

Priority: admit actual measurements under the existing physical calibration
protocol without inventing measurements; develop independent ego association and
road registration with desired-path provenance; prepare a separately declared
metadata-first private diagnostic manifest/privacy contract; await a genuinely
new blind reviewer and official CULane access.

Private proposed constraints: pixels only, no meter conversion, qualification,
sealed reference, detector reselection/config mutation, confidence optimization,
modelV2 path/lane, candidate outputs, training/selection or raw-data publication.
Any future diagnostic exception must be separately declared with exactly frozen
source/weight/config/environment and sample manifest frozen before image/output
opening. It never makes official reproduction or PUBLIC_GT qualification PASS.

## Regression risk and acceptance

Risks are stale blocker evidence, treating diagnostic completion as independent
truth, hiding geometry prerequisites, synthetic scope masquerading as public,
and allowing private acquisition from a design receipt. Acceptance: deterministic
acyclic known dependencies, authentic prior evidence, complete nonqualifying
diagnostic admission, and all private/sealed/promotion flags false.
No performance threshold or comparator policy is added/changed.
Rollback removes only the new snapshot/plan; immutable prior reports remain.

## Validation method and actual results

### SYNTHETIC SCREENING

No new detector/controller/private experiment. Synthetic fixtures test malformed
receipts, source/scope mismatch, missing categories, count/metric/provenance
corruption, forged public scope, DAG ordering and cycle failure.
The actual public29 plan is generated from admitted current evidence and
recomputes exactly.

| Check / stage | Method | Evidence | Result / limit |
| --- | --- | --- | --- |
| Unit/regression/build | TDD, focused/full AutoTune, Ruff/syntax/SCons | [comma10k-assisted-tail-validation-v1.json](comma10k-assisted-tail-validation-v1.json) | Executed checks recorded there |
| Evidence admission | exact old/new receipt and original vector bindings | [comma10k-next-blocker-plan-v1.json](comma10k-next-blocker-plan-v1.json) | Supporting diagnostics only |
| Public official CULane | existing legal source availability prerequisite | unchanged audit receipts | BLOCKED |
| Controller replay/sim/shadow | no control changes | prior results preserved | NOT_RUN |
| Private diagnostic | proposed nonqualifying contract | [comma10k-private-pixel-diagnostic-design-v1.json](comma10k-private-pixel-diagnostic-design-v1.json) | NOT_RUN; no execution permission |

## Handoff — BLOCKED / REAL VEHICLE STATUS

CLRerNet PUBLIC_DIAGNOSTIC_RETAINED; DETECTOR_QUALIFICATION_BLOCKED.
No acceptance threshold is inferred from assisted review.
CLRNet REJECTED, V2 REJECTED/stress TRADEOFF_ONLY, A3 rejection unchanged.
Full metrics and29 selection remain historical, with no outlier removal.

Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
