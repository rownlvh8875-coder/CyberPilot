# CyberPilot retrospective untouched evaluation — 2026-10-03

Status: **all three predeclared models pass the frozen absolute residual gates.**
This remains a retrospective evaluation, not a prospective independent holdout.
CyberPilot remains **NOT_READY** for candidate generation or vehicle application.

## Scope and chronology

1. The complete development intake was frozen first: 3,665 files / 152 routes.
2. Filesystem metadata identified 17 routes / 897 segments whose route labels never
   appeared in that development intake. Existing-route extra segments were excluded.
3. The 17-route universe was hashed before any log content or performance was read.
4. The evaluation policy and all three model values were hashed before pilot decoding.
5. One earliest segment per route was decoded only for source/vehicle/tuning compatibility.
6. Eleven technically eligible routes / 728 segments were frozen before performance scan.
7. The full route scan excluded two routes with later source-identity drift.
8. Compact sufficient statistics were regenerated from exact schemas and native torqued
   acceptance; raw point rows were not exported.

The route selection did not use speed, bucket coverage, residuals, fitted values or
candidate performance. The corpus predates this evaluation, so it is not a newly
collected prospective holdout.

## Frozen inputs and technical admission

| Stage | Routes | Segments | SHA-256 |
|---|---:|---:|---|
| metadata-only untouched universe | 17 | 897 | `5f9bff61fe256fe3956e4ccc96ae25d3e0b2c06b250969a35130778179e3e0d7` |
| technical pilot result | 17 | 17 pilot files | `e4a5ca6063e511edc6d0a9ceae10e04bbe1e8658d77b58396bd15478cdc5c9bb` |
| technically eligible universe | 11 | 728 | `192de15edcb86113b0bd58ea6be566457a19b19343077d706d6d1ac9c3fe55f7` |
| full evaluation scan | 11 | 728 | `ec279c384ee746ee7b08636bd3e3807e5b95348d97fc72a3d4030bb1e8829a2c` |
| compact sufficient statistics | 9 consistent | 65 epochs | `8028dc71ad0e979703b25d5bb4deb389080b9a56767313721542e328c22e003d` |
| fixed-model result | 8 evaluated | 8 source commits | `2510eadb5959f062e783f0c76713fd8ceee967fbd477546759dff959a75fddad` |

Pilot technical exclusions were based only on decode success, one clean source commit,
target vehicle identity, torque tuning and source-A-identical torqued/helper/replay logic.
During the full scan, two additional routes were excluded after source identity changed
inside the route. One technically consistent route had zero accepted points and was
excluded by the predeclared minimum of 100 points.

Final evaluation corpus:

- nonempty route clusters: **8**
- distinct source commits: **8**
- accepted points: **76,001**
- native bucket counts: `[242,1570,7671,23524,26908,12282,2959,845]`
- cross-route duplicate sample IDs: **0**
- within-epoch duplicate IDs/times/non-increasing times: **0 / 0 / 0**
- raw points/CAN/GPS/video/unhashed route labels exported: **false**

## Predeclared absolute gates

Policy SHA-256:
`bc0673033a65a149376e67ea9e19d75407255cd1e62e3f50e4aa34e47cae8673`

- minimum eligible routes: **5**
- minimum distinct source commits: **4**
- minimum total points: **4,000**
- bucket minima: `[100,300,500,500,500,500,300,100]`
- model weighting for metrics: **equal route weight**
- maximum route-balanced residual RMSE: **0.30 m/s²**
- maximum absolute route-balanced mean residual: **0.10 m/s²**
- model selection from evaluation: **false**

## Fixed-model evaluation

| Frozen development model | Factor | Offset (m/s²) | Evaluation RMSE (m/s²) | Mean residual (m/s²) | Absolute gate |
|---|---:|---:|---:|---:|---|
| point-weighted development | 4.0248327983 | -0.1796034408 | **0.2454603669** | 0.0318597971 | PASS |
| route-balanced development | 4.0218395909 | -0.1767872624 | **0.2449451873** | 0.0291343635 | PASS |
| source-balanced development | 4.1430647659 | -0.1685707974 | **0.2512116301** | 0.0172427283 | PASS |

The route-balanced development model has the lowest observed evaluation RMSE by about
`0.000515 m/s²` versus the point-weighted model. The source-balanced model has the
smallest absolute mean residual but the highest RMSE. These differences are reported
only as diagnostics: `selected_model` remains `null`, and no evaluation-driven ranking
is converted into a candidate or profile.

## What this evidence supports

This result supports the narrow statement that all three frozen development estimates
remain below the predeclared route-balanced residual gates on a disjoint set of route
labels that was absent from the development intake.

It does **not** establish:

- a prospective independently collected holdout;
- calibrated steering plant fidelity or closed-loop lane-centering improvement;
- physical friction identification;
- confidence qualification, candidate superiority or safe update magnitude;
- qualified replay, runtime shadow isolation, rollback or vehicle safety;
- permission to apply any factor or offset to comma4 or an active vehicle profile.

Current authority remains:

```text
selected_model                    null
model_selection_executed          false
fit_executed                      false
confidence_qualified              false
candidate_generation_allowed      false
qualified_replay                  false
runtime_accepted                  false
promotable                        false
vehicle_or_can_write              false
```

## Verification

- fixed-evaluation module tests: **5 passed / 3 subtests**
- local bound-runner tests: **2 passed**
- native-cleanup race regression: **5 repeated runs / 40 subtests passed**
- final AutoTune + controls regression: **475 passed**
- Ruff: **PASS**
- `git diff --check`: **PASS**
- result repeat: **byte-identical PASS**

The `/proc` cleanup test was also corrected to treat `ProcessLookupError` as the same
expected ABSENT state as `FileNotFoundError`; production cleanup already handled both.

## Next gate

The next legitimate evidence increment is prospective: freeze a future route collection
before it exists or before any content is inspected, keep it unavailable to fitting and
policy changes, then run the same fixed-model evaluation. Until such a dataset and
qualified replay/closed-loop/shadow evidence exist, CyberPilot remains **NOT_READY**.
