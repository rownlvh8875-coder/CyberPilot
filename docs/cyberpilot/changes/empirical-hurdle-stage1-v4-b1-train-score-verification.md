# V4 B1 TRAIN score provenance and completion

이번 작업은 이전 B1에서 남은 TRAIN 점수32개 필드만 확인한다.
threshold와 head 정보가 섞인 `train/receipt.json`은 열지 않는다.
root manifest → TRAIN submanifest → finalized receipt → 저장 점수의 연결과
기존 V1 TRAIN 정답의 저장 순서 provenance를 검사한다.
새 점수·판단·통계·prediction·rollout은 만들지 않는다.

## Identity and purpose

Cyber Validation, https://github.com/rownlvh8875-coder/CyberPilot,
`feature/cyber-autotune`, baseline
`5d226bf8c4fbfab6c57a0a256352264f61d06bd3`.
The containing publication commit identifies this additive implementation;
the private execution binding pins exact reviewed source/test/caller bytes.

The scenario is completion of32 blocked TRAIN/V4/combined_probability fields.
The previous192 PASS are inherited from their authenticated B1 receipts, never
recorded as newly reread. No vehicle applicability or efficacy is established.

## Original references and source contract

- [Previous B1 result](empirical-hurdle-stage1-v4-b1-saved-evidence-results.json)
  and [bounded reader record](empirical-hurdle-stage1-v4-b1-saved-evidence-verification.md).
- [V4 job bindings](empirical-hurdle-stage1-v4-job-manifest.json),
  [V1 population bindings](empirical-hurdle-fit-cv-results-v1.json).
- [Historical V4 source authorization](empirical-hurdle-stage1-v4-retrospective-execution-authorization.json)
  and [historical V1 source authorization](empirical-hurdle-fit-cv-authorization-v1.json).
  These authenticate old execution identities; the current human grant supplies
  this limited read authority.
- `empirical_hurdle_v4_execution.py::probability` writes each head's scores into
  `result[mask]` at original TRAIN positions. `train` identifies ORIGINAL_TRAIN;
  `save_train` saves that complete array, then its submanifest and finalized
  receipt. These functions are inspected as source and never executed here.
- `empirical_hurdle_v3_store.py::finish` defines the historical member map.
  Its broad traversal/verifier is never called. The new reader uses exact names.
- V1 `empirical_hurdle_fit_cv_data.py::binding/design`,
  `empirical_hurdle_fit_cv_execution.py::population/execute_job` and
  `empirical_s2_ri_reconstruction_math.py::context` supply the ordered source
  population contract carried by the earlier B1 proof.

All references use frozen baseline bytes, checked against the appropriate V1
or V4 authorization source map. Existing upstream licenses, attribution,
submodule identities and layout are unchanged; no external code is adopted.

## Changes and expected effect

Add `empirical_hurdle_v4_b1_train_score.py`, its synthetic tests and a public
technical result. Existing B0/B1, scientific executors, fitting, normalization,
threshold, selector, projection, controller and workflows remain unchanged.

Two root manifests bind64 exact TRAIN submanifests,64 exact finalized receipts
and64 exact score payloads: at most130 metadata opens and64 array opens.
There is no discovery, fallback, directory scan or old reference payload read.

For each replica/job the root-declared raw SHA binds both safe metadata files.
The TRAIN submanifest's canonical receipt must match the finalized receipt and
public job pin. Its train_receipt_sha256 must match the opaque model receipt
identity in the finalized record. The unopened mixed receipt's declared raw hash
must agree between root and submanifest. Candidate/fold/anchor/authorization and
TRAIN_COMPLETE are independently checked. The score's raw compressed SHA must
agree in root, submanifest and current bytes.

The unchanged B1 GuardedReader inherits B0 openat2 constraints: exact allowlist,
no symlink/magiclink/nested-mount escape, no aliases, regular single-link files,
bounded one-fd reads and stable stamps, no retry. A stdlib-only bounded parser
checks one complete gzip member including CRC/end/trailing conditions and literal
NPY v1/v2 header: full[N], float64 `<f8`, C order. No numeric array is created.
Object/pickle/structured data, repairs, reordering and truncation are rejected.

Caps precede actual reads: public exact TRAIN N (max336941), inherited65536-byte
header allowance, compressed bound decoded+decoded//100+65536, safe metadata
65536 bytes, and B0's frozen root-manifest bound. Private outputs are exclusive
0600 in a disjoint0700 directory, binding4MiB+result4MiB+resume1MiB and a fixed
9MiB reserve for one equally bounded receipt set. No array copies are stored.
The call-path audit is not an OS-wide sandbox.

## Proof levels and limitations

- MANIFEST_BOUND_COMPRESSED_FILE_VERIFIED: current compressed bytes match the
  previously trusted root member and authenticated submanifest declaration.
- LIVE_NPY_AND_PAYLOAD_HASH_OBSERVED: inner hashes are current observations.
  They are not compared to any unread descriptor or independent historical pin.
- CROSS_REPLICA_PAYLOAD_EQUALITY_VERIFIED: both approved score replicas agree
  at compressed/NPY/payload hashes, shape, dtype and anchor.
- ORIGINAL_MIXED_DESCRIPTOR_NOT_OPENED: neither contents nor current bytes of
  the mixed receipt or coefficient payloads are independently reverified.
- RECORDED_ORIGINAL_ORDER_PROVENANCE_VERIFIED: frozen writer source, exact job,
  TRAIN anchor/count, finalized/submanifest/score identities and the prior B1 V1
  population proof align. Equal length or an anchor alone is insufficient.
  No original rows or row IDs are reconstructed, and no source-log lookup occurs.

Whole-run replica equality remains
REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED. Other fields are outside this fresh
verification. TRAIN rowwise gates remain NOT_SAVED; no threshold is applied.

## Regression risk and acceptance

Principal risks are broken parent/child identity links, incorrect candidate/fold
or ordered population, decompression expansion, malformed headers, aliasing,
premature one-replica PASS and accidental disclosure. Each conflict stops the
scope without replacement files or policy changes. Full completion requires all32
new fields and their exact prior192 lineage. Rollback is stopping this standalone
reader; there is no runtime integration.

Before actual access: exact B0/B1 controls, host/volume/mount, public source pins,
scope and output identity/capacity, synthetic tests and two independent reviews
must pass. After one run the receipt is sealed and reopened for verify-only
resume with all source/recomputation entrypoints trapped.

## Validation method and actual results

Actual result: **B1_TRAIN_SCORE_INTEGRITY_AND_RECORDED_ALIGNMENT_VERIFIED**.
[Public technical result](empirical-hurdle-stage1-v4-b1-train-score-results.json)
records32/32 new TRAIN logical field PASS. Both replicas'32 score files passed
the expected compressed hashes and complete NPY format/N/shape/dtype/C-order
checks; all32 field pairs matched observed NPY/payload hashes and anchor identity.

The authenticated root → TRAIN submanifest → finalized → score chain passed
for both replicas. Its frozen source semantics and previous V1 TRAIN population
proof establish recorded original-order alignment for all32 jobs. The prior192
PASS are carried forward through their exact retained B1 binding/result/resume
lineage; none of their array files was reread. Cumulative approved field scope is
224/224, with this distinction between inherited and fresh proof retained.

Fresh access was exactly130 metadata files and64 score files,194 total, each
once without retry or substitution. Mixed carrier opens0, source writes0 and
all19 forbidden actual-scientific-operation counters0; call-path forbidden
attempts0. Detailed byte totals and source event identities remain private.
The output binding/result/resume receipts are exclusive0600.

The saved result was reopened and its raw hash/seal checked before verify-only
resume. Source reader, score decoder, chain/catalog and run entrypoints were
trapped; resume passed with source openings0 and recompute calls0. No scientific
aggregation, model execution, threshold reading/application or gate reconstruction
occurred. Synthetic historical regression runs hid actual E and used fixtures.

| Check / stage | Method | Actual result / limit |
| --- | --- | --- |
| New reader / caller | Synthetic bytes and exact-protocol guards | 38 / 9 PASS |
| Prior B0/B1 / prior caller | Existing synthetic suites | 86 / 9 PASS |
| Attribution / lateral | Existing synthetic suites | 95 / 16 PASS |
| Full AutoTune/controls / empirical | Existing runner; actual E masked | 5290 PASS in600.84s, includes combined empirical regressions |
| Ruff / compileall / SCons | Existing checks | PASS |
| Publication / JSON / authority | Four additive files and retained technical proof | PASS |
| Replay / simulation / shadow / vehicle | Not applicable | No control-path or actuation change |

Two independent agents approved integrity/provenance and authority/privacy for
the exact source/test/private-caller snapshots before any target read. Both
independently ran38 public reader and9 private caller synthetic tests. Their
review receipts are retained privately; they neither accessed E nor executed
prepare/run. Exact publication-head CI is checked after push, separately from
the execution's source-byte binding.

## Handoff and authority

Only public technical statuses/source references are published. Private roots,
manifest contents, sensitive hashes, score values, gate/tick/path rows, threshold
and coefficients remain private. Detailed read counts/bytes and proof receipts
are retained privately. Read-only opens may affect atime; no whole-store fresh
immutability proof is claimed.

C requires a separate predeclared aggregation protocol and explicit grant;
completing input integrity does not authorize aggregation or policy experiments.
C/D/E/F stay unapproved. Preserve HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE,
MODEL_SELECTION_FAILED_CLOSED, selected candidate null; HOLDOUT CLOSED,
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED, NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT,
FINAL_POOLED_REFIT_NOT_AUTHORIZED, COMPOSITION_NOT_AUTHORIZED; vehicle NOT_READY,
REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED, authority NONE.
Hugging Face is NOT_REQUIRED/NOT_USED. Stop after verification and publication.
