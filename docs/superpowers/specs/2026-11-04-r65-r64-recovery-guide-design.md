# R65 — pinned R64 cloud recovery and passive verification guide

Baseline af4523c05c24ea2c9368a869c0cf9f4df0f54590. Owner delegated ordinary
offline next-step design/inline work without repeated approval questions.

## Intent and approaches

The current recovery guide pins R62 tool1b244fe8, which lacks the now-merged R64
saved-browser verifier. Author chooses a new versioned RECOVERY_R64_KO.md and an
updated current README section. Rewriting the old pinned R62 guide would damage
historical reproducibility; a new orchestration CLI is unnecessary. Existing
Python/CLI/API/locks/workflows/app and old guide bytes stay unchanged.

## Fixed identities

- Tool commit af4523c05c24ea2c9368a869c0cf9f4df0f54590 / tree a2cab555bc0e74c633aa7d118c15f8f307d59dde.
- Archive source commit e5b76678cff4d45a4915da0f9b26982711167b1d / tree 5e890731b54b5534faf93c2a5a6d9b1f3762a72c.
- Existing archive SHA e1021b2d6c9f729402ab0f57805c8209d3cc3e06a94f7d0751c5ec71e82729d2 / revision aa393167a37fff42eef9ce8940faa8413c798f15.
- Existing private Dataset jjuinho/cyberpilot-evidence. No new HF writes/archive/guide.

Document revision, pinned tool and archive source are three separate identities.
The tool checkout can lack the new guide and show its historical README. Do not
substitute document/main/latest for fixed tool/source pins or relabel old archive.

## Literal workflow

One Bash block, set-eu, new /workspace/cyberpilot-r64-recovery-XXXXXX root, inherited
proxy/CA/auth; print WORKDIR immediately to locate partial failures. LFS skip,
Python-download-never, isolated cache. Fresh clone/fetch both full commits,
checkout pinned tool, verify HEAD/tree and DEV/context Git diff against old source.
Use existing uv0.12.23/CPython3.12.13 and hash-locked SDK2.4.0; SDK/app stay separate.
Call pinned cloud_restore with --commit OLD archive source, existing hash/revision.
Execute pinned browser_smoke with explicit already-prepared host Playwright/
Chromium and restored app; strict root checksum; then restored app Python -B
invokes pinned browser_verify on the same browser output.

Save reader stdout at ROOT/SAVED_BROWSER_VERIFY.json, OUTSIDE browser/, whose
38files/seven directories and closed checksums must not change. Reader exit0 is
required after actual browser PASS; a nonzero command stops and no completion
marker appears. Print R64_RECOVERY_ROOT only at successful end. No skip/fallback,
automatic browser/global installs, secret values, dependency redesign or repair.

R41 restore is nonzero synthetic model/reference work; browser/reader perform
no new model/F61/actual-r-dt/vehicle work. Reader checks consistency only and
source_identity_reauthenticated=false; restore's original Git/archive source
checks are a separate authority. No new numerical truth/physical timing claims.

## README and preservation

Keep the current section heading/anchor. Update only its body to the new R64
guide/pin, retain an explicitly historical R62 link. Keep all following README
bytes/anchors and old R48 records. Old RECOVERY_R62_KO.md SHA remains
23f9c7369479c32ca99a0df662e5c4a67ea73f66c98b5217367ebcaa02957964.

## Acceptance and limits

Run new document's literal block twice in fresh Git/SDK/app/cache roots on the
prepared shared host. Each441records/rawbytes/actual modes agrees with pinned
tool/source; original source identity remains old e5. Verify R41 portable26,
browser10PASS/38files/37root entries/18links, reader0/10cases/38files/recordedPASS/
zero failures/false source authentication. Reader and checksum calls leave every
browser file byte intact. Summary/four HTML+VIEW files match across runs and
canonical R64 feature proof. Do not claim physical-machine independence.

Full cloud141/21/static and unit repeat; all21Python fingerprints unchanged,
new permanent tests0/no artificial RED. DEV883/wheel inherited, not rerun/built.
One fresh whole-branch review, normal feature Draft PR/exact-head CI, deterministic
evidence and independent bounded parse. No main merge/HF writes in this task.
Preserve prior/new workspaces/branches/evidence. R_BUDGET UNRESOLVED, Static Gate
FAIL, actualr/T2/scale null, Candidate/Runtime NO_GO and all vehicle activation/
F70UH/F70V/F71 NOT_ALLOWED remain unchanged.
