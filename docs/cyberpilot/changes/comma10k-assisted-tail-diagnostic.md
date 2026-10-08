# Assisted comma10k tail diagnostic — IMPLEMENTED

## Identity and purpose

Cyber Validation; feature/cyber-autotune; baseline
e2decd536e16ccf27d900845665cb41c32a17d31. Fetch verified local/origin equality
and a clean tree before implementation. Preserve the frozen29 manifest, all
human/AI/exposure records, full-run metrics and rejected candidates.

This increment aggregates the actual assisted review. It cannot establish an
independent blind-human cause adjudication or detector qualification.

## Original references

CyberPilot repository https://github.com/rownlvh8875-coder/CyberPilot at the above
baseline. Reuse lane_tail_review_contract, lane_tail_review_workflow,
lane_tail_ai_review, lane_tail_diagnostics and lane_public_storage. No adoption
of external detector/controller code, new dependency or changed upstream license.
Original detector/config/weight/environment/submodule identities remain inherited
from the completed public run.

Original fixed manifest SHA:
82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10.
Selection policy SHA:
ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54.
Human export SHA:
311a5940a8bccd2c2c6be9acafea8bb189c57b3460bc01670d8a7e7b07735453.
The AI export remains 2ad2ca1d3b88c208831b467215bca1329c8963065db37d5423bcc835720e314c.

## Changes and expected effect

Added lane_tail_assisted_diagnostic.py and its tests; no runtime integration.
Flow: frozen manifest + original human/AI/exposure metadata → validate all29
relationships and chronology → unchanged bound_metric_loader → original
point vectors → separate diagnostic and concordance receipts → blocker plan.

Each relation preserves original row/AI/exposure hashes and explicitly records
exposed-before-decision=true, blind=false, assisted=true. No annotation is merged,
relabelled or overwritten. UTC chronology requires suggestion creation ≤ first
exposure ≤ human decision; equal recorded seconds are permitted by durable
first-exposure ordering, not proof of external nonexposure.

Metrics are original point-pooled linear quantiles in pixels. No averaging of
frame percentiles, inference rerun, outlier filtering or imputation. Empty vectors
produce null quantiles, not zeros; unreviewable frames would remain accounted.
Existing normalized image thirds and detector-score bins are reused. Three
representative frame IDs per label follow the existing diagnostic convention,
sorted by frame ID; they are not new selected review frames.

A strict result validator checks full schema, accounting, nested receipts and
scope; public admission also revalidates exact historical manifest/human/AI
inputs. A separately published original metric summary binds the exact twice
replayed original vectors' summaries/trace receipts. Its SHA is fixed for this
historical V1, not an acceptance threshold. Rehashed metric edits cannot pass.
Different inputs/metric definitions require a new declared experiment/version.

Artifacts (all metadata, no images/weights/raw logs):

- comma10k-assisted-tail-diagnostic-v1.json
- comma10k-assisted-row-provenance-v1.json
- comma10k-assisted-review-concordance-v1.json
- comma10k-assisted-original-metric-summary-v1.json

## Regression risk and acceptance

Predeclared exact29 accounting, immutable history, original-vector summary
agreement, deterministic receipts and no blind/private/qualification promotion.
There is no newly invented detector acceptance threshold. Risks: averaged
percentiles, hidden empty frames, AI/human confidence confusion, stale identities,
fabricated public scope, and treating assisted concordance as independent accuracy.
Fail closed before opening metric inputs if review/provenance is incomplete.
There is no fallback to AI labels. Rollback removes only this new diagnostic
layer; historical receipts and production paths remain unchanged.

The first reviewer had prior AI exposure. Same-person rereview cannot restore
blindness. Selected diagnostic strata cannot estimate causal population shares.

## Validation method and actual results

### SYNTHETIC SCREENING / public diagnostic

No new controller screening, replay or shadow experiment was run. This is public
image diagnostic aggregation, not scientific vehicle performance qualification.
29/29 assisted rows are reviewable; independent blind rows remain 0/29.

| Primary assisted label | Count | Selected29 percentage | Metric-available frames |
| --- | ---: | ---: | ---: |
| DETECTOR_MISS | 12 | 41.38% | 9 |
| REPRESENTATION_MISMATCH | 8 | 27.59% | 8 |
| DETECTOR_FALSE_POSITIVE | 3 | 10.34% | 3 |
| INTERSECTION_OR_MERGE | 3 | 10.34% | 1 |
| DETECTOR_LOCALIZATION_ERROR | 1 | 3.45% | 1 |
| OTHER | 2 | 6.90% | 2 |
| Remaining six frozen labels | 0 | 0% | 0 |
| Total | 29 | 100% | 24 |

OTHER contains affirmative correct-detection observations, not failure evidence.
One primary label cannot encode every additional miss in the original comments.
Five empty metric frames are explicit: three MISS and two INTERSECTION_OR_MERGE.
The small intersection pooled median/p95 covers only one frame and is not
evidence of uniformly good junction performance.

| Original selected29 pooled metric | Samples | Median px | p95 px |
| --- | ---: | ---: | ---: |
| prediction → GT marking | 16,244 | 64.36 | 1451.35 |
| same-point 2D | 16,244 | 14.46 | 447.74 |
| GT marking → prediction | 12,163 | 13.29 | 909.51 |

These are selected29 statistics, not revised full-run results. Full-run history
remains 11,888/11,888; directional median4.96px/p95 666.97px; same-point2D p95
154.37px. The 9,472 reused receipts, restart recovery and earlier temporary-cache
loss remain documented in the unchanged full-run records.

Association groups: detector-related primary labels16/29; representation8/29;
far-field/multilane group3/29 (all intersection/merge); OTHER/unresolved2/29.
Explicit component-matching and GT-ambiguity primary-label groups have zero rows;
that does not prove those mechanisms absent. These counts neither allocate each
tail point nor measure causal error magnitudes. The smaller same-point p95 shows
a different geometry comparison; subtracting p95s does not isolate matching error.
No dominance or causal population verdict is issued.

Existing y-region pred→GT sample counts are far0, mid8,766, near7,478.
Far0 means no samples in that frozen image third, not proof of reliable distant
geometry. Detector frame-median score bins: 0.4–0.6:8; 0.6–0.8:16;
unavailable:5. Per-label counts are in the JSON, not optimized confidence gates.

ASSISTED_REVIEW_CONCORDANCE:18/29 (62.07%). AI confidence HIGH3/3,
MEDIUM14/21, LOW1/5. No HIGH-confidence disagreement; AI UNRESOLVED4,
human UNRESOLVED0. Matrix orientation is assisted-human rows × AI columns.
The person already saw AI/assistant explanations; these are not independent AI
accuracy, confidence calibration, or evidence that AI can replace human review.

| Check / stage | Method | Evidence | Result / limit |
| --- | --- | --- | --- |
| Unit/regression/build | TDD, focused, full AutoTune, Ruff, syntax, SCons | [comma10k-assisted-tail-validation-v1.json](comma10k-assisted-tail-validation-v1.json) | Executed counts/commands and logs recorded there |
| Public metric replay | unchanged bound loader, two exact executions | [comma10k-assisted-original-metric-summary-v1.json](comma10k-assisted-original-metric-summary-v1.json) | Exact pooled input identity, no images/inference |
| Controller replay/simulation | not applicable, no controller change | prior results unchanged | NOT_RUN this increment |
| Shadow/vehicle | no actuation authority | blocked readiness | NOT_RUN |
| Browser | no UI files changed | prior validated UI preserved | NOT_RERUN_NO_UI_CHANGE |

Independent review found and repaired missing creation-time chronology,
stripped/test scope admission, stale public relation hashes and resealed metric
values. New regression tests cover each attack. The first full regression ran
while source was still changing; A1 correctly failed its during-run source-binding
guard (1296 passed,1 failed,1 error). Source was frozen before the final full
rerun. Both runs remain in validation history; no policy was weakened.

## Handoff — BLOCKED / REAL VEHICLE STATUS

ASSISTED_TAIL_DIAGNOSTIC_COMPLETE; PUBLIC_DIAGNOSTIC_RETAINED for diagnostic
use only; DETECTOR_QUALIFICATION_BLOCKED. No justified new threshold exists to
declare detector acceptance/rejection from these assisted strata.
Independent blind attribution remains pending; canonical finalizer unchanged.
CLRNet REJECTED, controller V2 REJECTED, stress TRADEOFF_ONLY and A3 rejection
remain historical. Production controller/comparator are unchanged.

Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Next steps follow comma10k-next-blocker-plan-v1.json; independent reviewer and
physical geometry remain missing evidence, not values software can invent.

## Reproducing this metadata-only diagnostic

Requires the unchanged persistent public receipts/cache, not private logs or
new detector inference. Run from the repository with its prepared .venv.
Set public_root to the existing external recovery-v2 directory. The following
Python API calls validate completed index/input/source identities before pooling.
Do not replace missing metric vectors with estimates.

    from pathlib import Path
    from openpilot.tools.cyber_autotune import lane_public_storage as s
    from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
    from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d
    docs = Path("docs/cyberpilot/changes")
    m = s.read_json(docs / "comma10k-completed-full-human-review-manifest.json")
    h = s.read_json(docs / "comma10k-assisted-human-review-v1.json")
    ai = s.read_json(docs / "comma10k-ai-prereview-results-v1.json")
    loader = w.bound_metric_loader(public_root / "full-run-persistent-v3",
                                   public_root / "comma10k-full-cache", m)
    result = d.aggregate(m, h, ai["experiment"], ai["suggestions"], loader)
    d.validate_result(result)
    assert result == s.read_json(docs / "comma10k-assisted-tail-diagnostic-v1.json")

Cached source/config/input drift intentionally fails closed. A later producer
revision must create a new declared artifact/version; historical V1 is immutable.
