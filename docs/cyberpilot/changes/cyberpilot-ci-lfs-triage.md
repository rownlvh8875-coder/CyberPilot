# CyberPilot CI LFS triage and recovery design

Status: `CI_LFS_REMEDIATION_PLAN_READY_NOT_APPLIED`.
Required asset: `CI_LFS_REQUIRED_ASSET_UNAVAILABLE`.
Dependency closure: `CI_LFS_DEPENDENCY_CLASSIFICATION_INCOMPLETE`.
No setup/workflow/LFS configuration, pointer or asset payload was changed or transferred.

## Confirmed failure and identity

Baseline `602855e53fe1f66bbb8c4a99e6d8841b4a6c2afc`, branch
`feature/cyber-autotune`: [run 39196436306 attempt 2](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39196436306/attempts/2),
job `117880505991`, `build and validate offline branch`, completed/FAILURE.
`Set up openpilot development environment` invoked `./tools/op.sh setup`.
Its explicit `git lfs pull` returned HTTP 404 `Object does not exist` for
15 distinct OIDs, across three setup pull attempts. Build, Ruff, AutoTune,
attribution and lateral validation did not execute. This is an external setup
failure, not a test failure; exact-head FULL_CI SUCCESS was not obtained.

The earlier [pre-execution run 39193687093](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39193687093)
was SUCCESS at `7676d761e47654e3c86665a3166dfe88d87b39e0`. It is a different
HEAD and cannot substitute for baseline or final CI. The final new-head result
is reported separately in the handoff; this inventory freezes the observed
baseline failure rather than rewriting it.

Both LFS read and push endpoints in `.lfsconfig` are
`https://huggingface.co/commaai/openpilot-lfs.git/info/lfs`.
The evidence establishes the configured endpoint's response at that attempt.
It does not establish permanent deletion, another mirror's availability,
authorization correctness or a particular server-side cause. No credentials
from another task were used; no asset was fetched, uploaded or substituted.

## Public pointer inventory

The companion JSON enumerates all 252 baseline index LFS pointers and their
Git blob/pointer SHA256, declared OID and size. For each failing OID it also
records the last pointer-change commit and whether its pointer matches original
V4 head `bd8045ef2a0da62a92603439f38e7740f5923622`. These are metadata checks,
not proof that the corresponding binary content is currently available.
All 15 log OIDs map 1:1 to tracked pointers, declared total 95,348,970 bytes.

| Missing SHA256 OID | Tracked path | Declared bytes |
| --- | --- | ---: |
| `f92c0a9b41613e063b6a1cd086729f5555d9df6482249e171ed1e276272cad7d` | `openpilot/common/hardware/comma/updater` | 24,709,520 |
| `dfb645e59636687d61d20283bae65b68ddda6f7b2d4fda01a6e613a842e3b41f` | `openpilot/selfdrive/assets/icons_mici/settings/device/apple.png` | 823 |
| `df07383a6ddfe8cd7eeb2f22271cbd13068327ca0978873f8d10368860562e40` | `openpilot/selfdrive/assets/icons_mici/settings/device/commacare.png` | 111,083 |
| `f7518f3409e2ff8f7e99fb7f0c06afa8bdf0b0a506147b5cf9d4931b820a1a75` | `openpilot/selfdrive/assets/icons_mici/settings/device/github.png` | 1,107 |
| `8a18e3de5f455b4089a824da8d5d78d5d532ef71facb05cc75c178b24d5beeb7` | `openpilot/selfdrive/assets/icons_mici/settings/device/google.png` | 920 |
| `710e74b526adb5bbac15cd8915a828dd673dd8ce15b2fd694c64c182eef6f56f` | `openpilot/selfdrive/assets/icons_mici/settings/device/green_cell.png` | 13,744 |
| `25db08a9038b5faa3b200ef5625cb216d7f4b31ea3d49fb0395f9b726bfaf8e6` | `openpilot/selfdrive/assets/icons_mici/settings/device/green_settings.png` | 13,135 |
| `547f466cc59d29647f3bf131d8444d7f22b63b186bcea55ceb8109c68ca74fe8` | `openpilot/selfdrive/assets/icons_mici/settings/device/paired_apple.png` | 2,345 |
| `55050096cd98e7f4ea3e843d927c18815e458dfbd5e7d100b503db92075d061b` | `openpilot/selfdrive/assets/icons_mici/settings/device/paired_github.png` | 2,373 |
| `f9c439ed89bc0357e86c005d5dbb6f1ad2b8d72cdc0890e3201d842d8c3928f1` | `openpilot/selfdrive/assets/icons_mici/settings/device/paired_google.png` | 2,443 |
| `7aeccd3e0d8517f74eb34f7d73632c0b29b0ad5df5b9686c0f509bb6b136561e` | `openpilot/selfdrive/assets/icons_mici/settings/device/phone.png` | 1,728 |
| `6334d6b92a2cc095bfb1430a252aa2ede1902605d0f9ba89224aa5a87c7dc7c0` | `openpilot/selfdrive/modeld/models/big_driving_warp_1344x760_tinygrad.pkl` | 863,472 |
| `bda11a9c2e87636db364862ca68ebe4ff9d7baeeb39c0c7e2010b702ed543283` | `openpilot/selfdrive/modeld/models/big_driving_warp_1928x1208_tinygrad.pkl` | 863,216 |
| `dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04` | `openpilot/selfdrive/modeld/models/dmonitoring_model.onnx` | 7,844,499 |
| `65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce` | `openpilot/selfdrive/modeld/models/driving_supercombo.onnx` | 60,918,562 |

## Requirements and unresolved dependency coverage

`tools/op.sh::op_setup` runs setup dependencies, configures LFS and retries the
whole pull before `op_check`. `op_check_git` explicitly requires
`dmonitoring_model.onnx` to be real binary data. Thus this object is
REQUIRED_FOR_VALIDATION, and a blanket exclusion of all 404 objects cannot
produce a valid full setup. When the LLVM model build branch is enabled,
`modeld/SConscript` additionally consumes both `dmonitoring_model.onnx` and
`driving_supercombo.onnx`. Actual LLVM availability in the failed runner was
not verified because build was never reached. Treat the second ONNX as
required when planning a conservative fetch, not optional by assumption.

The ten device/settings PNGs have identified UI runtime consumers. The two
`big_driving_warp_*` files have Chestnut/release consumers, and updater has
AGNOS update/startup consumers. Static review finds these outside the current
PC build and selected workflow tests, making them candidates for
OPTIONAL_FOR_THIS_WORKFLOW. However, clean-build dynamic coverage is not
established; the authoritative inventory retains UNKNOWN_DEPENDENCY for these
13 files. This is deliberate: absence of a static hit and a cached local build
are insufficient to prove an asset may safely be omitted. The other 237 index
pointers are enumerated but their full dependency closure remains UNKNOWN.
No UNKNOWN item is approved for exclusion.

The current workflow sets `lfs.fetchexclude` to exactly
`openpilot/selfdrive/modeld/models/big_driving_tinygrad.pkl` via Git configuration
environment entries. None of the 15 missing paths matches that exclusion;
in particular it does not exclude similarly named big warp files. Local
fetchinclude/fetchexclude overrides were unset at inventory time.

Git LFS pull supports path include/exclude filters, while skip-smudge controls
smudge/filter-process behavior. Setting `GIT_LFS_SKIP_SMUDGE=1` alone does not
remove this explicit pull. [Git LFS pull](https://github.com/git-lfs/git-lfs/blob/v3.6.1/docs/man/git-lfs-pull.adoc),
[Git LFS configuration](https://github.com/git-lfs/git-lfs/blob/v3.6.1/docs/man/git-lfs-config.adoc)

## Safe recovery options and recommendation

| Option | Required evidence | Present disposition |
| --- | --- | --- |
| A: verified upstream recovery | Official/authorized exact OID and size, actual content SHA256, license and redistribution authority | Recommended first for required ONNX assets; no alternate verified source is established |
| B: minimal required fetch | Complete exact asset allowlist, LLVM/build branches, clean build and every validation target; explicit pull filters and actual binary integrity | Design only; two ONNX paths are conservative seeds, NOT a complete fetch allowlist; blocked by required 404 and incomplete closure |
| C: separate offline/static numerical CI | Explicit dependency/import closure, synthetic-only tests and clear reporting label | Useful independently; requires separate workflow approval and cannot certify full build/model validation |
| D: retain full-CI blocker | Required asset unavailable | Current safe full-CI status; do not skip required assets or fabricate SUCCESS |

First ask the legitimate upstream asset owner to recover or identify an
already-authorized immutable source for the exact required OIDs. Do not upload
to inherited comma.ai LFS storage or use a private model as replacement.
If only the static/synthetic work needs an independent green signal, a separately
approved workflow can report `OFFLINE_STATIC_NUMERICAL_CI`. That label must
remain distinct from `FULL_CI` and `LOCAL_FULL_REGRESSION`.

No safe minimal-fetch list is finalized by this task. A future CI change must
resolve UNKNOWN dependencies, preserve required checks and verify actual
content hash/size after authorized fetching. Existing source, original failed
run and pointers remain immutable. No fake pointer, alternate model or
credential injection is a remedy.

## Future implementation and validation approval

A CI-only grant must identify exact workflow/setup/filter edits and asset
access/storage authority. Then verify OID/path/size, every required asset,
clean SCons build, Ruff, full AutoTune/controls, attribution, lateral replay,
JSON/source/privacy checks, clean tree and exact-head full Actions result.
An offline-only job requires separate naming and a restricted dependency plan.
Neither grant authorizes scientific private data, Stage2 replacement or E2.

Local results, final reviews and final-head CI are kept separate below. Local
success does not establish a clean GitHub asset fetch. The original 404 run
remains FAILURE even if a future run passes.

- New focused tests: 21 PASS (`python -B -m unittest ...deterministic_numerics_design`).
- Fifteen focused public/synthetic modules: 520 PASS, 24.875 seconds, with E/D mounts masked read-only.
- Lateral closed-loop/gate/plant/scenarios synthetic modules: 40 PASS.
- Ruff on AutoTune: PASS; compileall: PASS; local `scons -u -j4`: PASS (prepared workspace, not a fresh LFS fetch).
- JSON parse: 833 files PASS; canonical receipts/source/index-pointer pins are asserted by the new tests.
- Full local AutoTune/controls: 5,737 PASS at `bbb7ee02e61fd394a817ef6d69ef4a776cfc5b12`, with four workers and E/D mounts masked read-only. This is `LOCAL_FULL_REGRESSION`, not GitHub FULL_CI.
- Final independent approvals bind the five final file digests in the publication commit and final handoff. Final exact-head Actions outcome is observed after push and reported there; no success is inferred in advance.
- All actual private/scientific forbidden-operation counters in the numerical contract are zero.


## Stop boundary

No private arrays/models/handoff/E-drive, raw/qlog, HOLDOUT or vehicle access.
No numerical runtime replacement, policy search or E2 execution. No LFS payload
transfer, pointer rewrite, workflow bypass or fake full-CI success. This task
ends with design/inventory publication and truthful final CI observation.
