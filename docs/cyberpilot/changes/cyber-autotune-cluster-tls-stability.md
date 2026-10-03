# Cyber AutoTune route-cluster TLS stability — 2026-10-03

## Status

- Numerical cluster stability gate: **PASS**.
- Statistical confidence: **NOT QUALIFIED**.
- Parameter identification: **NOT QUALIFIED**.
- Candidate generation, replay acceptance, promotion and vehicle application: **BLOCKED**.

This stage evaluates a frozen Gram-matrix TLS diagnostic over the full clean development corpus. It does not change `torqued`, controller behavior, Params, safety limits, profiles, CAN output, or vehicle state.

## Frozen policy

The policy was written and SHA-bound before reading any real TLS estimate outcome.

- minimum nonempty route clusters: 20
- minimum source commits: 10
- maximum route point share: 25%
- maximum source-commit point share: 40%
- maximum route/source leave-one-out factor delta: 5%
- maximum route/source leave-one-out offset delta: 0.05 m/s²
- maximum route-jackknife factor relative SE: 5%
- maximum route-jackknife offset SE: 0.05 m/s²

Policy SHA-256: `f11c2a0c6bd325cd450e40f0403b10d8283eee52a58863cc4ab6b23c92c6f1ef`.

## Frozen inputs

- sufficient statistics: 85 declared routes / 37 nonempty routes / 216,356 accepted points
- distinct source commits represented by nonempty routes: 16
- pooled bucket counts: `[1036, 5252, 22088, 81691, 68439, 27084, 8307, 2459]`
- raw points were not reopened by the TLS runner; only frozen route-level Gram matrices were consumed
- structural Leave-One-Route-Out count gate was already PASS
- holdout opened: false

Sufficient-statistics SHA-256: `d10f031af2122948e63f5f6e06d979c604b8798385ade1cf1d38a2a130672315`.

## Pooled numerical estimate

| quantity | value |
|---|---:|
| `lat_accel_factor` | 4.024832798307419 |
| `lat_accel_offset_mps2` | -0.17960344075536194 |
| native residual-spread coefficient | 0.0923049940975453 |
| residual RMSE | 0.25520583374786665 m/s² |

The residual-spread coefficient is the native numerical diagnostic from `torqued`; it is not established here as physical friction. The estimate is not an approved vehicle parameter.

## Route/source omission stability

- route clusters: 37
- source-commit clusters: 16
- maximum route point share: 14.5482%
- maximum source-commit point share: 31.4722%

| stability metric | observed | frozen limit | result |
|---|---:|---:|---|
| max route factor relative delta | 1.3325% | 5% | PASS |
| max source factor relative delta | 1.7194% | 5% | PASS |
| max route offset delta | 0.010512 m/s² | 0.05 m/s² | PASS |
| max source offset delta | 0.010653 m/s² | 0.05 m/s² | PASS |
| route-jackknife factor relative SE | 2.2353% | 5% | PASS |
| route-jackknife offset SE | 0.014358 m/s² | 0.05 m/s² | PASS |

Every route omission and source-commit omission remained numerically identifiable. The complete result repeated byte-for-byte with SHA-256 `f333b58735c2e52ddfc7a5fb06443e56f09d4de7fe47081b003abafc27292bbc`.

## Remaining blockers

1. `CLUSTER_CONFIDENCE_NOT_QUALIFIED`
2. `CANDIDATE_GENERATION_NOT_AUTHORIZED`

A stability PASS means only that the numerical TLS estimate is not highly sensitive to removal of one route or one source commit under the predeclared limits. It does not prove route independence, unbiased sampling, physical correctness, predictive benefit, closed-loop improvement, or safety.

The next gate requires a separately frozen development/evaluation protocol and candidate-admission contract. The current development corpus cannot be silently repurposed as independent evaluation evidence.

## Implementation and verification

New modules:

- `openpilot/tools/cyber_autotune/torque_gram_tls.py`
- `openpilot/tools/cyber_autotune/torque_cluster_tls.py`

New tests:

- `test_torque_gram_tls.py`: 6 passed / 14 subtests
- `test_torque_cluster_tls.py`: 7 passed / 5 subtests
- affected AutoTune + controls: **456 passed**
- Ruff: PASS
- `git diff --check`: PASS
- result repeat: byte-identical PASS

Artifact SHA-256:

- Gram TLS module: `7cf03d8d56abf6d6212bd496ceab16e6f3b59a117570f744cd57181d3ea6d56c`
- Gram TLS tests: `ffe682dd00a96dbde33bb64406c1a0a4ad8a3ce0a7a88dae146f7a22db469109`
- cluster TLS module: `157aa3807d285f7beb11b2c68ad95ccb34b8e2af4ba33049e2380a46fb69dc80`
- cluster TLS tests: `75978fdf5b546cee20a24dabad822fb6727d5b7e5a43efc7c5fe5dbcb3ec711b`
- frozen runner: `51230e89053506af37461c62155fa82fb0723405eaae6dc7c4ee0e7474f2285f`
- result: `f333b58735c2e52ddfc7a5fb06443e56f09d4de7fe47081b003abafc27292bbc`

No commit, push, merge, reset or clean was performed.
