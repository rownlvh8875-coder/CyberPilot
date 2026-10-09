# Completed private assisted-human pixel holdout

## Summary and applicability

IMPLEMENTED: completed frozen60 assisted review, immutable final analysis binding,
unchanged/modified groups, observed-support ego center, 11-frame geometry-unavailable
ledger and confidence diagnostics. Frozen selection is unchanged.
This is AI_ASSISTED_HUMAN_PIXEL_REFERENCE, not independent blind GT or vehicle
qualification. Forty-four original drafts were accepted; sixteen AI-assisted
revision drafts were explicitly human verified. "Modified" does not mean a
human manually drew every replacement point.

Branch: feature/cyber-autotune. Baseline:
7a09d3d2ab35878bf05835c54df5c88f2d9ba8e6.
Scope: read-only post-freeze analysis of existing receipts. Original AI, human
first-decision, detector, authorization and evaluation artifacts are unchanged.
No controller, comparator, A3 rejection, calibration admission or detector
configuration changes.

## Original references and data flow

Existing private_holdout_assisted.py admission/freeze/evaluate and
private_holdout_pixel_metrics.py assignment/distribution are reused. No
external algorithm or new dependencies. Frozen CLRerNet identity remains
in its original authorization and per-frame receipts; existing license applies.

Validated materialization + assisted authorization + original AI rows +
immutable human rows + frozen detector receipts + historical evaluation
→ authoritative evaluation recomputation and exact equality check
→ immutable private final analysis receipt
→ strict nested numeric aggregate publication allowlist.

The new private_holdout_assisted_analysis.py source SHA and analysis-policy SHA
are bound in the report. Local bindings cover all60 image/manifest/AI/human/
prediction receipts and historical evaluation. Observed-support center pixels
and the failure ledger remain local. Publication contains whole-set hashes and
aggregates only. No native submodule changes, network executor or live authority.
Stale/incomplete inputs fail closed; historical evidence is never overwritten.

## Actual pixel diagnostics

Pooling: common observed integer image-y rows, point weighted. No extrapolation.
Errors are conditional on matched geometry, not a score for unavailable frames.
Matching is unchanged: maximum observed-overlap match count, then pixel cost,
then lane index; no acceptance-distance threshold.

| Group | Frames | Left median / p95 px | Right median / p95 px | Both match / both visible |
| --- | ---: | ---: | ---: | ---: |
| Original draft accepted | 44 | 3.22 / 7.74 | 3.97 / 11.61 | 37/39 (94.87%) |
| Modified draft accepted | 16 | 1.91 / 5.09 | 1.97 / 8.76 | 7/16 (43.75%) |
| All | 60 | 2.92 / 7.54 | 3.65 / 11.49 | 44/55 (80%) |

The modified group's smaller conditional errors cannot hide its nine unmatched
frames. Its largest right error is 121.83px; unchanged right maximum is 24.52px.
These are observed discrepancies, not posthoc acceptance/rejection thresholds.

Human pixel ego center: left/right midpoint on common visible image-y support
only, original pixel coordinates, no meter conversion.
Median1.94px, p90 4.59px, p95 5.05px, maximum15.05px.
Available44 / both-visible55; unavailable11. Five other frames have no
two-boundary center denominator: two right-only, two intersections, one
no-clear-markings. There are57 frames with any visible boundary reference.

### Draft modification diagnostics

Geometry partition: left-only1, right-only1, both14, state-only0.
State changes15 overlap the geometry partition; do not sum them as extra frames.
Twenty-eight previously absent boundaries were added, none removed.
Only changed boundaries with an original AND final observed shared span have a
distance sample:141 rows, median15.78px, p90 27.80px, p95 28.90px, max30px.
Added boundaries have no distance to an absent original boundary; they are not
zero-distance samples. These describe AI draft correction, NOT detector error.

### Geometry-unavailable ledger

All11 both-visible-but-not-both-matched frames are bound privately:
LEFT_MISS2, RIGHT_MISS5, BOTH_MISS4.
These names mean no eligible observed-y overlap assignment for the human side;
they are not independently adjudicated semantic detector misses.

WRONG_LANE_ASSOCIATION, EXTRA_FALSE_POSITIVE, INTERSECTION_OR_MERGE,
HUMAN_AMBIGUOUS, OTHER and UNRESOLVED slots remain in the taxonomy.
Their zero automatic ledger counts do not establish absence of semantic
failures. Wrong association / extra false-positive truth are NOT_ADJUDICATED.
The11-frame ledger covers only both-visible frames; other states stay in the
full60 accounting.

### Confidence diagnostic, not calibration

Buckets were fixed before the actual group report. Frame-mean frozen lane score
is not probability of correctness. Unknown confidence is separate from NO_OUTPUT.

| Score bucket | Frames | Both matched / both visible | Left / right unavailable |
| --- | ---: | ---: | ---: |
| [0, .50) | 6 | 1/5 | 1 / 3 |
| [.50, .75) | 40 | 37/39 | 1 / 1 |
| [.75, .90) | 7 | 6/7 | 0 / 1 |
| [.90, 1] | 0 | no denominator | 0 / 0 |
| NO_OUTPUT | 7 | 0/4 | 4 / 5 |
| UNKNOWN_CONFIDENCE | 0 | no denominator | 0 / 0 |

Low-score right p95 is108.95px, including the121.83px maximum. Higher confidence
does not guarantee both-boundary availability. Frozen60 remains evaluation-only:
no confidence optimization, filtering, fine-tuning or detector reselection.

## Public/private comparison

Separate published comparison binds the existing completed public report.
Public all-marking masks versus private assisted ego-boundaries are different
semantic targets. Their localization medians/p95 are NOT one accuracy benchmark.

Only prediction-only diagnostics are comparable:
public no-output3285/11888 (27.63%), private holdout7/60 (11.67%).
Frame-mean score median .6327 versus .6613; per-lane score median .6495 versus
.6671; normalized vertical extent median .3730 versus .4939.
Full-public versus selected-private60 sampling, resolution/FOV and road domain
are confounders. These shifts are not accuracy improvement evidence.
Historical development240 and public11888 results remain unchanged.

## Decision and remaining critical path

PRIVATE_ASSISTED_HUMAN_HOLDOUT_COMPLETE
PRIVATE_PIXEL_HOLDOUT_EVALUATION_COMPLETE
PRIVATE_REFERENCE_CANDIDATE_DIAGNOSTIC_ONLY

No justified qualification threshold exists; no new PASS/FAIL qualification.
Conditional errors support continuing engineering, while80% geometry availability
and the121.83px tail remain concerns. Do not tune on this evaluation holdout.

Next priority: CALIBRATION_MEASUREMENT_PENDING
→ INDEPENDENT_CALIBRATION_VALIDATION_PENDING
→ METRIC_CALIBRATION_UNAVAILABLE
→ validated road-frame registration and uncertainty accounting.
EGO_ASSOCIATION_VALIDATION_PENDING remains parallel; geometry matching is not
ego-association qualification. Existing physical wizard/Jacobian infrastructure
must receive actual measurements; do not invent height/orientation uncertainties.

Still BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
CULane official reproduction, second blind reviewer, road registration,
desired-path provenance and all other reference blockers remain.
Assisted pixel evidence cannot enter sealed independent-reference admission.
Actual measurements NONE; sealed reference NOT_GENERATED.

## Verification and review

TDD: new analysis failed first; empty support, nested publication, provenance
type, unknown confidence and cross-accounting defects were reproduced and covered
before fixes. Independent review rechecked all findings with no remaining issues.
No UI changes; existing assisted/blind UI and first-decision history preserved.
Synthetic fixtures cover known5/10px offsets, group changes, missing sides,
unavailable centers, exact historical evaluation binding and redaction.

Prepared Ubuntu24.04/WSL commands:
- .venv/bin/python -m unittest -q openpilot.tools.cyber_autotune.tests.test_private_holdout_assisted_analysis
- .venv/bin/python tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j 1
- Workflow-equivalent Ruff, compileall, publication audit and whitespace checks.
- export PATH="$PWD/.venv/bin:$PATH" followed by .venv/bin/scons -j2

Actual counts/status and privacy/authority audit are in the separate validation
receipt. No real-vehicle replay/simulation/shadow qualification is claimed.
Rollback: remove additive analysis module, retaining immutable original inputs.

## Vehicle status

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No CAN/Params/CarController/device writes or activation authority.
Private raw images, human coordinates, route names, paths and timestamps were
not published.
