# CyberPilot D-drive data curation

Status: **COMPLETED — protected evidence and retrospective evaluation preserved.**

## Scope

- Roots: local D-drive log directories; private absolute paths are intentionally withheld
- Original inventory: 20,372 files / 70.847 GiB
- Existing development evidence was protected before deletion.
- A late-locked retrospective evaluation set was frozen before semantic parsing.
- No holdout/H1/H2, vehicle/CAN write, parameter update, candidate promotion, commit or push occurred.

## Frozen retrospective evaluation set

- 17 routes / 897 unique `rlog.zst` segments
- `rlog` size: 10.626 GiB
- associated camera size: 1.676 GiB
- total bound files: 1,687 / 12.303 GiB
- 16 routes are contiguous; one route is retained with an explicit segment gap.
- selection used metadata only: route absent from the prior development manifest and at least one unprotected `rlog.zst` present.
- speed, bucket coverage, fit result and candidate outcome were not used for selection.

## Deleted data

| Class | Files | Bytes | Rationale |
|---|---:|---:|---|
| paired unreferenced `qlog.zst` | 4,713 | 3.322 GiB | same segment has a non-zero full `rlog`; no explicit `qlog.zst` path reference found |
| exact duplicate copy | 33 | 0.012 GiB | identical SHA-256; retained counterpart verified |
| zero-byte lock file | 306 | 0 | no payload |
| **Total** | **5,052** | **3.334 GiB** | |

Filesystem free-space increase was 3.343 GiB; the small difference from logical file size is filesystem allocation accounting.

The 33 duplicate-copy removals comprised one non-zero duplicate `rlog.zst` plus zero-byte log/camera copies. No source-code file was deleted.

## Preserved data

- 3,665 prior-development files remained present at their original sizes.
- All 1,687 retrospective-evaluation files were rehashed after deletion and matched their frozen SHA-256 values.
- 63 explicitly referenced paired `qlog` paths were preserved.
- 839 `qlog`-only files (0.507 GiB) were preserved because they are the only log copy for those segments.
- All non-zero camera files and all unique `rlog` files were preserved.
- Twelve zero-length qlog/rlog pairs were excluded from the paired-qlog deletion rule; they consume no meaningful space.

## Post-cleanup inventory

- Remaining files: 15,320
- Remaining total: 67.513 GiB
- `rlog.zst`: 4,694 files / 53.630 GiB
- `qlog.zst`: 908 files / 0.555 GiB
- `.ts` camera/log-related files: 4,380 / 9.246 GiB
- `.hevc`: 96 / 3.307 GiB
- Current D-drive free space: 267.225 GiB

## Retrospective fixed-model evaluation

The frozen 17-route set is exactly the existing untouched-evaluation universe: same 17 route hashes and same 897 segment identities. Technical filtering yielded 8 eligible routes, 8 source commits and 76,001 accepted points.

| Development-fixed model | factor | offset (m/s²) | route-balanced RMSE (m/s²) | mean residual (m/s²) |
|---|---:|---:|---:|---:|
| point-weighted | 4.0248327983 | -0.1796034408 | 0.2454603669 | 0.0318597971 |
| route-balanced | 4.0218395909 | -0.1767872624 | **0.2449451873** | 0.0291343635 |
| source-balanced | 4.1430647659 | -0.1685707974 | 0.2512116301 | **0.0172427283** |

All three passed the frozen absolute diagnostic gate. No model was selected, refitted or promoted. The result remains retrospective, not a prospective independent holdout.

## Reproducibility after cleanup

The fixed-model evaluation runner was executed again after deletion:

- runner tests: 2 passed
- post-cleanup result: byte-identical to the pre-cleanup result
- result SHA-256: `2510eadb5959f062e783f0c76713fd8ceee967fbd477546759dff959a75fddad`

Authority remains blocked:

- confidence qualification: false
- candidate generation: false
- qualified replay: false
- runtime acceptance: false
- promotion: false
- vehicle/CAN write: false

## Integrity

- original metadata inventory: `1f75915437e927b53568e82ac6082ffb0f50a139098d2d2190207e7a5a1f6cf8`
- frozen evaluation metadata: `a7570e43e57128e19461bda1c2a69a299a079618d8ad7535bf8ec95b16254ac9`
- frozen evaluation content manifest: `75d08169ef360a8a3b73572f774be26a72a0aead7c4d46e3e31c1d56b0605cd4`
- deletion plan: `ad27b322e81f65c8986b04c541d3f27e9f5a376db735e5e580ee7dba37367657`
- deletion receipt: `b04ff19d07e45bec0c275735b72f8652dd26bee087f8b769813f286b1d41725b`
- post-cleanup inventory: `34cbcd9f4e08198296643b29bb5e584b5c831589c06810e93cd9df86ed21d25e`
