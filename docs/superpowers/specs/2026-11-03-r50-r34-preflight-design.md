# R50 — R34 public preflight error boundary

## Intent and observed cause

The user delegated routine offline next-step decisions and opted out of repeated
design questions. Close the R34 API boundary deferred by R45 without extending
the shared preflight implementation or vehicle scope. Base:
109bdbc1724f4a35e5329d145f23ee08551e95e9.

Real reproduction at that base: NUL in baseline/candidate/output raises raw
ValueError; output under mode000 raises raw PermissionError; isolated CLI NUL
prints a traceback and exits1. The public R34 entry calls shared `_preflight`
without an error boundary, unlike the already guarded R44/R46 entry points.

## Selected approach

Wrap only `run_comparison(baseline: Path, candidate: Path, output: Path)`'s call
to `_preflight`: re-raise existing CompareError unchanged, translate remaining
ordinary OSError/ValueError into CompareError('COMPARE_IO') chained to the original.
Existing CLI already catches CompareError, so it yields bounded rejection/exit2
without a CLI code change. Preserve the signature and every classified code.

Alternatives: changing shared `_preflight` broadens R44/R46 behavior; CLI-only
catching leaves the programmatic API inconsistent. No general exception wrapper,
new helper/framework or new result schema is needed.

## Boundaries and proof

- Reject before observing source hashes, reading batch bytes or creating output.
- Preserve specific output/encoding/runtime/input-file rejection codes and existing
  causes. Do not catch programmer TypeError, BaseException or later-stage defects.
- Exercise real NUL paths in all three arguments and a real unprivileged mode000
  probe. Deterministic filesystem fault injection covers otherwise unclassified
  OSError/ValueError across arguments; isolated CLI checks exact stderr/exit/output.
- Existing R34 guard tests remain active. Add scope tests showing preflight
  programmer/interrupt exceptions and downstream OSError/ValueError propagate.
- Compare baseline/fixed saved R34 MATCH/DIFFERENT output bytes on the same complete
  owned inputs. Re-run all R34/R44/R46 tests; verify shared preflight AST unchanged.
  Receipt source hashes may change; no arithmetic, verdict or presentation changes.
- Full DEV/cloud gates, one fresh final branch review, actual exact-head PR CI,
  deterministic evidence ZIPs and independent checksum/closure verification.

Public0.3.0 wheel/API, model/reference/generator/limiter, locks/dependencies, shared
preflight, R44/R46 implementations, cloud tools and CI unchanged. No main merge/HF
write in this feature stage. Preserve all old branches/envs/evidence.
R_BUDGET UNRESOLVED, StaticFAIL, actualr/T2/vehicle scale null; Candidate/Runtime NO_GO;
F70UH/F70V/F71 and activation NOT_ALLOWED. Comparator/probes new model/reference0;
fixture/unit/gate/CI work NONZERO/unaggregated. No F61/actualr/dt/vehicle/Controller/Runtime/CAN.
