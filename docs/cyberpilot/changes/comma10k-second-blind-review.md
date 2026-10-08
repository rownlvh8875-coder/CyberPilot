# Independent second reviewer contract — IMPLEMENTED

## Identity and purpose

Cyber Validation; feature/cyber-autotune; baseline
e2decd536e16ccf27d900845665cb41c32a17d31. Define SECOND_REVIEWER_BLIND_V1 over
the unchanged29 frames. No actual second reviewer or annotations are generated.
The original AI-exposed person cannot become blind by repeating the images or
choosing another reviewer ID.

## Original references

Reuse CyberPilot lane_tail_review_contract and workflow at the baseline:
original twelve-label taxonomy, guide, UTC annotations and immutable no-follow/
atomic storage. Separate AI/provenance modules are not imported by the blind
store. No external implementation/dependency or changed attribution/license.

Future unweighted nominal Cohen's kappa uses the standard observed/chance
agreement definition described by the official scikit-learn documentation:
https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html
It is implemented with existing Python arithmetic; no scikit-learn dependency.
A constant-category perfect-agreement case has undefined kappa (null), not1.

## Changes and expected effect

Added lane_tail_second_review.py and its tests; inter_rater in the assisted
diagnostic module validates each store separately. No production/UI hooks added.

protocol(frozen_manifest) → register(opaque SHA256 ID, explicit attestations) →
new empty separate store → presentation whitelist → explicit human immutable
save → separate export → all29 admission → future human-only attribution and
separate inter-rater diagnostic.

Registration requires explicit human acknowledgement, not-original-reviewer,
no prior AI suggestion/assisted label/stratum hypothesis access. All fields must
be actual JSON booleans, not0/1. Opaque ID and self-attestation do not establish
external independence cryptographically. A new person with truthful nonexposure
is still an external evidence prerequisite. Software cannot certify it.

Visible: original image, category2 GT mask, detector prediction geometry, and
opaque frame/input hashes. Hidden: AI suggestions, assisted labels, metrics,
detector confidence and automatic stratum/selection hypotheses. The presentation
API returns only frame ID/image/mask/prediction hashes; it has no previous-store
path or import API. Do not feed the AI-assisted page/montage to a new reviewer:
use the clean image/GT/prediction views without hypothesis text.

BlindStore uses a new directory, immutable registration, separate rows and
exactly matched index with existing durable writer lease/fsync/atomic operations.
Unknown/duplicate/stale annotations, old store files, symlink/unsafe paths and
orphaned index state fail closed. Incomplete or corrupt stores do not finalize.
Rows cannot overwrite prior assisted evidence or vice versa. There is no silent
migration, automatic label copying, interpolation or synthetic human fallback.

Presentation time has no controller/physical delay significance. The protocol
and annotation sources/config hashes bind immutable evidence, with no mutable
runtime parameter state. Vehicle applicability: none.

Published protocol, zero-row pending and inter-rater-pending JSON receipts keep
statistical results null. All actual blind-store initialization remains NOT_RUN.
The synthetic temporary TEST_ONLY stores in tests are not human evidence.

## Regression risk and acceptance

Exact frozen29, new uninformed reviewer, same taxonomy, separate immutable store
and all29 completion are required. Assisted rows cannot satisfy this contract.
Acceptance for software is isolation/shape/hash/store validation, not reviewer
qualification or detector performance. Main risks: reuse of the first reviewer,
hidden prior exposure, leaking selection hints, accepting integer attestations,
and generating statistics from incomplete/synthetic rows as public evidence.

Rollback removes only the added protocol/store; original assisted/AI/human
annotations remain immutable. A future browser adapter must preserve the whitelist
and independently test access isolation; the existing assisted UI is not
rebranded as a blind UI.

## Validation method and actual results

### SYNTHETIC SCREENING

No controller or real human experiment. TEST_ONLY fixtures cover separate-store
restart, duplicate/unknown/stale input rejection, attestation typing,29-only
finalization, blinded presentation and no prior-label imports.

Future inter-rater analysis validates two aligned exports before computing:
exact agreement, assisted×blind confusion matrix, disagreement frame IDs and
nominal Cohen's kappa. Tests use an analytically checked29-row synthetic example
(19 agreements,10 disagreements, kappa13/42), undefined constant-label case,
and28-row/absent-reviewer cases with no statistics. These fixture numbers are
not measured human results.

| Check / stage | Method | Evidence | Result / limit |
| --- | --- | --- | --- |
| Unit/regression/build | TDD, focus, full AutoTune, lint/syntax/SCons | [comma10k-assisted-tail-validation-v1.json](comma10k-assisted-tail-validation-v1.json) | Executed checks recorded there |
| Actual reviewer | explicit independent human attestations | [comma10k-second-blind-review-pending-v1.json](comma10k-second-blind-review-pending-v1.json) | UNAVAILABLE;0 rows |
| Inter-rater | separate validated completed exports | [comma10k-inter-rater-pending-v1.json](comma10k-inter-rater-pending-v1.json) | statistics=null |
| Replay/simulation/shadow | no control change/actuation | prior results preserved | NOT_RUN |
| Browser | no UI changed | prior review UI intact | NOT_RERUN_NO_UI_CHANGE |

## Handoff — BLOCKED / REAL VEHICLE STATUS

INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE.
ASSISTED_HUMAN_REVIEW_COMPLETE is not INDEPENDENT_BLIND_HUMAN_REVIEW_COMPLETE.
A second reviewer cannot be automatically created, copied or inferred.
Independent tail attribution waits for actual new reviewer evidence.

Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
