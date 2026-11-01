# R32.1 — close looping-input error handling and bounded visual check

User approved the proposed follow-up: fix R32-M1, add regression, check existing
graphs/Korean/table/scroll in an available browser, then full tests/CI/Draft update.
No new model, renderer, controller, vehicle data or policy feature is requested.

Bug cause: run_report resolves input for output-location comparison before the
bounded nofollow reader. A looping input symlink raises pathlib RuntimeError,
outside the CLI's ReportError/OSError handling, producing traceback/exit1.
Resolve input in a narrow try/except(OSError,RuntimeError), translate to
ReportError('REPORT_INPUT_FILE') with chained cause. Do not catch arbitrary
RuntimeError from renderer/publication; keep output existence/parent guards first,
then output-inside-input rule, runtime check, read/render/exclusive publication.

Regression: isolated CLI self-loop and ancestor-loop both exit2 with exactly
REJECTED: REPORT_INPUT_FILE, no traceback/stdout/output. Direct API preserves
RuntimeError cause. Existing-output/missing-parent guards retain precedence.
No valid-data portable byte change, no model/native import/execution in reader.

Browser check uses existing saved synthetic HTML only, owned temporary browser
profile and loopback CDP with25s total/4s request limits. Blank-page readiness
separates environment failures from report failures; inspect2SVG/4rows/Korean,
horizontal scroll and desktop/mobile screenshots if supported. No dependency/
system/browser policy changes, no external browser/debug endpoint exposure or
access to user laptop. If blocked, record exact stage as NOT_ESTABLISHED and
provide a concise local read-only check rather than repeat unchanged attempts.
Screenshots/DOM are a scoped sample, not full accessibility/browser qualification.

Preserve public0.3.0 wheel/model, R31 producer/R32 validator/HTML/native/workflow/
build/lock. Only run_report and its CLI tests need runtime/test edits. Keep old
R32 reports immutable; add R32.1 results and guide follow-up. Existing r/Static
Gate/activation/F61/Controller/Runtime/CAN/actual-input restrictions stay closed.
Full baseline/local/relocated gates, saved-bundle portable equality/import
tripwire/source guards, one fresh whole-branch review, existing feature/Draft PR2
and exact-head pure CI, deterministic evidence. No main merge. Final publication
receipts external to avoid recursive HEAD/CI/seal rewriting.
