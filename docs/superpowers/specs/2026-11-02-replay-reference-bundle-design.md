# Immutable compatible process-replay reference

The user authorized the next fix after the separate diagnosis and has explicitly
delegated implementation choices without repeated approval questions.

## Intent and approaches

Stop comparing the September production snapshot with a moving November upstream
reference. Keep existing numerical comparisons, tolerances and production behavior.

1. Pin only `ref_commit`: insufficient, because artifact downloads remain on a
   moving branch and no bytes/schema compatibility are checked.
2. Pin the compatible producer, immutable artifact revision, source fingerprint,
   opendbc/schema identity and each compressed artifact's size/hash: selected.
3. Upgrade production or regenerate goldens: broader changes, not authorized here.

The historical producer is `c8fb906815530460ed156f14e09e1f312bb0f851`, whose
openpilot production tree and opendbc pointer exactly match this fork. Its existing
artifact revision is `eab2cc2b1f6de3773617937868442520c7ef554c`. Verify that revision's
index and Git blobs, then record SHA256 of compressed bytes without decoding logs.

## Design

A stdlib-only `reference_bundle.py` validates a tracked JSON lock and exposes
immutable URLs, current-source compatibility checks, and compressed-byte checksum
verification. No moving URL or unverified local-cache fallback is allowed.

The protected source fingerprint covers tracked openpilot files except the replay
harness directory, root dependency/build inputs, root tools except the two
independent `tools/cyberlateral_dev` and `tools/cyberlateral_cloud` directories,
and all submodule pointers. The
harness is excluded so the checker can change without redefining its producer.
Compare the current HEAD projection with the producer projection, reject dirty
protected tracked files, and verify the checked-out opendbc revision/schema before
native imports. This is a conservative declared-source guard, not attestation of
the entire build, environment, LFS payload or actual deployment.

Verify all selected reference bytes before any input-log decode or replay, and
pass those verified bytes to workers instead of reopening paths. A corrupt local
cache is an error, not a reason to silently use remote bytes. `--update-refs` is
rejected explicitly: this fix does not grant baseline-generation authority.
Legacy local `ref_commit` overrides are rejected if they disagree with the lock.

## Boundaries

No production source/physical parameters/tolerances/workflow gates change. No local
Controller, Runtime, native decode, replay, F61, r/dt or candidate evaluation.
Compressed public CI references may be downloaded and hashed only. Run stdlib
fixture tests plus the existing isolated synthetic component gate. Root on-vehicle
and native replay suites are excluded by the user's execution constraints.

Keep changes local on `fix/pin-process-replay-reference` based on PR13 head. Do not
push, merge or trigger CI in this task. Request an independent final code review.
Keep R_BUDGET unresolved, Static Gate FAIL and actual vehicle activation prohibited.
