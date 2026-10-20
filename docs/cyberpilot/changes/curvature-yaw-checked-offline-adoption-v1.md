# Checked diagnostic offline adoption V1

This additive offline interface preserves the four original self-hashing modules and all historical records. It does not modify a controller, planner, Native kernel, model, scientific source pin, workflow, replay reference or acceptance rule.

The publication, diagnostics, rejection investigation, exporter and renderer have separate source identities. Each execution entry requires the keyword `offline_publication_v1=True` (exact built-in boolean). Its default is `False`; invalid or omitted values fail before worker execution or input/output work. The three versioned command-line modules also require `--offline-publication-v1`. Existing callers import the original modules and retain their original behavior.

The qualified flow is immutable canonical request bytes → exclusive private producer state → complete source-bound publication → private decode and original runtime validation → frozen scalar records → one archive → exporter and run-directory renderer. The producer exposes no mutable request/native/result object or callback. Channel writers and readers share a lock, generations are monotonic, and failed updates retain the previous complete publication. The renderer requires both run and evaluation directories and reads the checked export projection. It never consumes the original mutable diagnostic files after validation.

The archive uses `CHECKED_DIAGNOSTIC_ARCHIVE_BUNDLE_V1`; each packet uses `CHECKED_DIAGNOSTIC_OWNED_PUBLICATION_V1`. Both verify the exact six source filenames and SHA256 values, canonical bytes, receipt and cross-field bindings. The externally supplied `evaluation-envelope.json` is a single canonical JSON object containing `evaluation`, `selection` and `evaluation_freeze`; these are the complete corresponding original evaluation records. Its authority is independent of the archive and must match exactly. A source version string is not sufficient authority, and these hashes establish consistency rather than authentication.

Legacy receipts must be verified with the unchanged original verifier. New receipts bind to the actual new source bytes. Neither verifier accepts the other source's diagnostic receipt. Historical receipts are never migrated, resealed or relabeled. The original JavaScript renderer is reused by its explicit unchanged filename and its actual digest.

Helper functions for pure reconstruction, metadata inspection or basic file reading do not start an owned run and are not all gated. Mutable standalone diagnostic adapters do not gain a concurrency guarantee. The guarantee applies to the immutable publication/archive path. Ordinary frozen records and supported ownership APIs are not a security sandbox against arbitrary Python reflection.

## Validation and expected limits

Run the original diagnostic and archive tests plus `test_curvature_yaw_owned_publication` using the prepared public environment. Existing Unit and Full CI V2 collect the additional six test IDs automatically. V2 preserves its original 5,927-ID subset requirement. No workflow, assertion, baseline-ID manifest or static policy is changed.

Before publication, also repeat the deterministic 37-case producer/consumer and 32-case boundary races twice, the 107+75 outcome comparisons, 300 guard checks, 401-frame binary64 and signed-zero comparison, fresh-process repeats, eight-case investigation/export/render, source and receipt rejection checks, complete local regression, and both independent reviews. External diagnostic evidence and generated binaries are not committed.

Keeping the original source bytes also keeps its 49 type diagnostics. The measured full ty result must be reported honestly; this change does not claim to restore all Static checks. New source files must add no diagnostics. Runtime, concurrency, provenance, Static and exact-HEAD CI are separate validation axes.

## Rollback

Omit the opt-in keyword/flag to retain the original API and workflow behavior. Preserve new archives separately with their exact source identity. If removal is needed, inspect affected consumers and revert the adoption commit normally; do not rewrite history or historical receipts. Rerun Unit, V2, Numerical and Native checks on the revert HEAD. Turning the option off alone does not transform a new receipt into a legacy receipt.

D2 remains PERFORMANCE_NOT_EVALUATED; Private E2 is NOT_AUTHORIZED; HOLDOUT remains CLOSED; vehicle authority remains NONE. Candidate and policy selections remain null. This offline change grants no PR merge, policy-enforcement or vehicle authority.

## Feature change record

### Identity and purpose

- Area: Cyber Validation, implemented opt-in offline interface; exact-HEAD validation pending until publication.
- Scenario: consume one consistent synthetic diagnostic publication in export/render without mutable raw aliases.
- Scope: offline public synthetic only; no vehicle applicability or activation.
- Branch/baseline: `feature/cyber-autotune`, `bb06771140feac9926b72e9a7e144a7d6806728f`; added source identities are in the companion JSON.

### Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot, verified feature baseline above.
- Sources: original `curvature_yaw_diagnostics`, `curvature_yaw_rejection`, `curvature_yaw_rejection_export`, `curvature_yaw_rejection_visualizer`; adapted B7 local six-file patch SHA256 `bedf686f83bd9682d35878916e9e391e4098d9d51bf4adad3f829ab3544df6a0`.
- License: repository MIT-style license, copyright comma.ai; original source attribution retained. No external code or model acquisition.
- Call path: `produce_diagnostics` / `DiagnosticChannel.publish_request` → immutable packet → `seal_bundle` → `export_results` → `render_html`. Original APIs remain separate.
- Dependencies: pinned opendbc `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`; all six Gitlinks unchanged. Public prepared Python 3.12.13 / NumPy 2.5.3 / Cap'n Proto 2.1.0; no model used by this diagnostic flow.
- Decision: adapt the checked B7 ownership flow into parallel versioned names; reject in-place changes that would invalidate legacy self-source identities.

### Changes and expected effect

- Six added Python files: four versioned legacy counterparts, publication boundary and six-test module. Two additive contract/documentation files. No upstream integration or automatic activation point.
- Expected effect: equal functional outputs and binary64 values; explicitly different source/receipt metadata. Keep legacy type diagnostics visible and add none.
- Constants: the inherited 128 MiB archive limit bounds this public offline interface; no private runtime limit changes. Timeout and numeric constants remain inherited, unchanged.
- State: private decode per producer run; complete publication only; channel generation starts at one, stale expected generation rejects and failed updates preserve prior state. No silent fallback.
- Safety: no imports or changes in `selfdrive/controls`, car interfaces, controller/planner or Native kernel. Existing standalone raw APIs retain their previous scope.
- Maintenance: duplicated versioned offline code requires explicit future review; changing a source in the exact tuple invalidates its new receipts and requires a new source identity rather than compatibility relaxation.

### Regression risk and acceptance

- Risks: missing opt-in propagation, cross-source receipt confusion, raw consumer rereads, shared aliases and numeric or exception drift.
- Acceptance: original bytes preserved; no new ty diagnostic; exact normal/error outcomes, binary64 and signed zero; original source pins and IDs retained; deterministic race tests; no tolerance or skip added.
- Inputs: frozen public synthetic fixtures only. HOLDOUT, private E2, real replay and vehicle execution are not part of this change.
- Rollback: retain originals as the last validated default; remove explicit opt-in; normal commit revert if necessary, retaining versioned archives and receipts.
- Review: independent concurrency/type and provenance/source reviews before commit; user adoption authority does not grant vehicle authority.

### Validation method and actual results

| Stage | Method | Actual evidence and limits |
| --- | --- | --- |
| Unit/regression | Existing diagnostic/archive tests plus added publication tests; complete V2 collection using original runner | Focused 19 PASS; complete regression and GitHub exact-HEAD status recorded in final handoff, not inferred here |
| Static | Same pinned ty/Ruff/codespell and original fast lint script | ty 1,156 unchanged including original 49; new files zero diagnostics; Ruff/codespell/eight fast checks pass locally |
| Functional | Original vs versioned public synthetic 401-frame outcomes | 107+75 outcomes equal, 300 guards, 24,898 binary64 and 252 negative-zero values equal; provenance fields separated |
| Replay | Existing reference unchanged | Not run for this change; automatic upstream CI conclusion reported independently |
| Simulation/closed loop | No new model or vehicle simulation | Not applicable: isolated diagnostic ownership only; no performance qualification |
| Shadow | Candidate cannot actuate | Not applicable: no runtime/controller integration or actuation path |

### Handoff

- Effect: controlled additive source adoption with separate archive/source identities; does not restore all Static diagnostics or repair official replay drift.
- Remaining checks: complete local regression, pipeline/race evidence, independent exact-byte reviews and new-HEAD CI must be read before any success declaration.
- PR: https://github.com/rownlvh8875-coder/CyberPilot/pull/1 remains Draft/Open/Unmerged. Final commit/run references are in the final handoff.
- Vehicle application: NOT_AUTHORIZED. D2 remains unevaluated and all research authority boundaries remain unchanged.
