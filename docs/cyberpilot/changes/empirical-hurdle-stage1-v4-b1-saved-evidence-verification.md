# V4 B1 saved evidence integrity and alignment

이번 작업은 저장된 파일과 행 순서의 무결성 확인이다. 점수·정답·이전 변화량의
성능 통계를 계산하지 않으며, 새 prediction이나 rollout도 실행하지 않는다.
TRAIN score descriptor는 threshold와 head 정보가 섞인 carrier에 있으므로
이번 권한으로 열지 않는다. 나머지 여섯 필드만 제한적으로 검증한다.

## Identity and purpose

Cyber Validation, `feature/cyber-autotune`, baseline
`de418c9300c33b716609ba1e5c3415d13202974d` in
https://github.com/rownlvh8875-coder/CyberPilot. The containing publication commit
identifies the additive implementation; private execution records bind the exact
reader/test source bytes independently of the later report commit.

Scope: the frozen 32 jobs, seven requested TRAIN/DEV field slots per job.
No vehicle applicability or empirical efficacy claim is introduced.

## Original references and ordering proof

- [Field/authority contract](empirical-hurdle-stage1-v4-evidence-access-field-allowlist.json).
- [V4 job catalog](empirical-hurdle-stage1-v4-job-manifest.json),
  [V4 DEV bindings](empirical-hurdle-stage1-v4-development-results.json),
  [V1 results and counts](empirical-hurdle-fit-cv-results-v1.json), and
  [V1 population receipt pins](empirical-hurdle-fit-cv-job-manifest-v1.json).
- `empirical_hurdle_fit_cv_data.py:61`: ordered segment/count/index hashes;
  `design:76` and `empirical_s2_ri_reconstruction_math.py::context:52` preserve
  that blocks order. `empirical_s2_ri_schema.py:150` pins source ticks to int64.
- V1 `empirical_hurdle_fit_cv_execution.py::population/execute_job` and V4
  `empirical_hurdle_v4_execution.py::save_arrays/execute_job` bind saved fields.
  V4 DEV requires its authenticated finalized parent, since the DEV receipt
  itself lacks candidate/fold. The mixed TRAIN receipt is never opened or hashed.

All references above use the baseline bytes. Existing licensing and submodule
identities are preserved; no external implementation/dependency is adopted.
This proof concerns immutable recorded original-order provenance. It does not
reconstruct source rows, read row-ID arrays, or independently validate physical
or label semantics. Equal lengths or an anchor digest alone are insufficient.

## Changes and expected effect

Add `empirical_hurdle_v4_b1_evidence.py`, its synthetic tests and this bounded
public result record. Existing B0, scientific executors, models, normalizers,
selectors, projection, control paths and workflows remain unchanged.

The reader accepts exactly three trusted run manifests and the named safe
population/finalized receipts. Its finite allowlist contains at most 195 metadata
files and 256 requested arrays. It has no directory scan, fallback, model loader,
threshold operation, numeric array construction or scientific reducer.

Every file uses the unchanged B0 `openat2` guards below a mandatory bound mount:
no symlink/magiclink/nested mount traversal; single-link regular files and unique
file identities; one bounded read, stable held-fd stamps, no retries. Read-only
access may update atime; no whole-store fresh immutability claim is made.

Compressed bytes must match manifest and safe descriptor hashes before decoding.
One bounded gzip member must pass CRC/end/trailing checks. A bounded literal NPY
header must match full `[N]`, C order and exact `|b1`, `<f8` or `<i8` dtype.
Object/pickle/structured types, casts, truncation, reordering and repairs are
rejected. NPY and complete payload hashes must also match the safe descriptor.

Caps are fixed before live file inspection: public exact N (maximum 336941),
dtype width, 65536-byte header allowance, and compressed bound
`decoded + decoded//100 + 65536`, following existing V1 store reservation.
Safe metadata has a 65536-byte ceiling for at most 32 fixed descriptors plus
scalar fields; top manifests retain B0's frozen caps. Private outputs are
exclusive0600 in a disjoint0700 directory, at most9MiB receipts plus a fixed9MiB
reserve. No full arrays are persisted. Guards are not an OS-wide sandbox.

## Regression risk and acceptance

Risks are wrong job/role routing, aliasing, decompression expansion, malformed
headers, changed bytes, incomplete replica checks, unproved row provenance and
private publication. Conflicts stop the scope without substitution. V4 field
PASS requires both requested replicas and their equality check; a partial replica
cannot be promoted. Rollback is to stop this standalone reader, with no runtime
integration or changes to existing evidence.

Actual input access requires the current human B1 grant, B0/handoff seals, exact
public source/catalog pins, fresh host/volume/mount proof, output capacity and
permissions, synthetic PASS and both independent source reviews.

## Actual result and validation

Actual result: **B1_MIXED_CARRIER_ACCESS_BLOCKED**, with the authorized six-field
subset verified. [Technical field statuses](empirical-hurdle-stage1-v4-b1-saved-evidence-results.json)
account for all224 requested job/role/field slots:192 PASS and32 AUTHORITY_BLOCKED.
TRAIN has64 V1-reference field PASS and32 unopened V4-score fields; DEV has128
logical field PASS across32 jobs. All256 array payloads read passed compressed,
NPY and payload hashes, exact full-N shape, dtype and C-order checks against
authenticated manifest/descriptor bindings. The raw manifest pins came from the
existing B0 observation; this is not an independent pre-B0 raw-byte proof.

Exactly195 metadata and256 array files were opened once,451 total. No target
retry or substitution occurred. All32 DEV four-field populations have immutable
recorded-order provenance; no TRAIN three-field population is fully verified.
The64 V4 DEV field/job pairs match across both replicas at compressed/NPY/payload
hash, dtype, shape and anchor levels. This is field-scoped equality only.

The retained private result was reopened, its hash and seal checked, and resume
passed with all source/array recomputation entrypoints trapped:0 recompute calls
and0 source openings. Detailed receipts and byte totals remain private. Read-only
opens and stable same-fd stamps support source writes0; no entire-store post-run
rehash was authorized. Call-path audit recorded0 forbidden attempts, with all18
forbidden actual-scientific-operation counters0. Historical regression uses
synthetic fixtures and is accounted separately.

| Check | Actual result / limit |
| --- | --- |
| Reader synthetic | 45 PASS |
| Private caller synthetic | 9 PASS, including saved-result reload/corruption and output-directory replacement |
| Independent integrity and authority reviews | APPROVED for exact source snapshots; private review receipts retained |
| Full AutoTune/controls | 5252 PASS in606.27s; includes existing empirical regressions; real E masked |
| Attribution / lateral | 95 / 16 PASS, synthetic historical tests |
| Ruff / compileall / SCons | PASS |
| Replay/simulation/shadow/vehicle | Not applicable; no controller change or actuation authorized |

Both independent reviewers approved the exact reader, test and private caller
source snapshots before live access. Their restricted private receipts bind
those SHA256 identities. The public result identifies only public source hashes;
no private root, descriptor hash, manifest content, score, gate or tick row is
published. Publication/privacy/authority checks passed for the four additive
files; the containing commit's exact-head CI is verified separately after push.

## Handoff and authority

TRAIN `combined_probability`: `B1_MIXED_CARRIER_ACCESS_NOT_AUTHORIZED`; a separate
explicitly approved, provenance-bound minimal descriptor is needed. The current
scope never opens the mixed carrier, its coefficient arrays or the TRAIN score.
TRAIN rowwise gates remain `NOT_SAVED`, with no decision application.

Only the two V4 DEV fields may receive fresh field-scoped replica equality.
Whole-run equality remains `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`.
The replicas are retained and are never summed or averaged.

C requires its own predeclared processing/output protocol and human grant;
missing TRAIN inputs must first be resolved or explicitly excluded from that
future scope. B1 does not grant C/D/E/F. Existing
`HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`,
selected candidate null, HOLDOUT CLOSED, vehicle authority NONE/NOT_READY/
REAL_VEHICLE_UNVERIFIED/VEHICLE_ACTIVATION_BLOCKED are preserved. Hugging Face
is not used. Stop after integrity/alignment verification and publication.
