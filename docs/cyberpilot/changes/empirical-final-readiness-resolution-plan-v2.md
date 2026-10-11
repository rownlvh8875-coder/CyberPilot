# Empirical final readiness resolution V2 plan

Purpose: implement the user's EMPIRICAL_FINAL_READINESS_RESOLUTION_V2 on
ba84b61fee7f3a2c0c2e2815c1b3a6ebdfb06eeb. This is a bounded, additive
consumer of existing immutable receipts, not extraction or model development.

1. Freeze exact public receipt pins and required precedence:
   AUTHORITATIVE_FINAL_ASSESSMENT > EXECUTION_READINESS > INTERMEDIATE_EXTRACTION_STATE.
   A missing, stale, untrusted or contradictory final assessment fails closed;
   there is no fallback to execution READY.
2. Resolve final causal completeness PARTIAL, historical reproduction PASS,
   qlog reconciliation COMPLETE as three separate states. Preserve every old
   JSON, source file and private store without opening raw logs or arrays.
3. Publish route/stream support partitions: 154 rlogs / 916535 base rows are a
   retrospective causal-rich subset; 2 qlogs / 11989 rows are accounting only
   with zero causal runs/design support. Count accounting is not fitting support.
4. Implement a reusable future-consumer gate. It validates the resolved receipt,
   the pinned historical rlog manifest and exact member segment receipt before
   any array use. Qlog/unknown/zero-support-route/role/source drift is rejected.
   In-memory arrays must match sealed dtype/shape/order/content identities.
   Eligibility preserves required availability/validity/age/gap/run boundaries.
   A history window must stay in one route, segment, causal run and exact grid.
   This guard grants no fitting, selection, CV, candidate or holdout authority.
5. Define nonexecuting S1/S2/S3 development-data admission prerequisites.
   Actual steering-rate values exist; physical rate unit/sign remains unresolved.
   No family/config choice, history length, solver, model or score is generated.
6. Test first: precedence conflicts and missing final evidence; qlog rejection
   before arrays; forged stream kind and segment/source/profile drift; null/stale/
   invalid/gap rows; exact age boundary; histories; immutability; publication.
7. Generate additive aggregate artifacts twice and verify exact receipt equality.
   Run focused and combined empirical tests, full AutoTune and controls, lateral
   replay, Ruff, compileall, JSON, publication/privacy, diff and SCons. Freeze
   code before the full suite because historical source-binding tests hash it.
   Request independent review, fix important issues and rerun affected checks.
8. Commit/push; fetch and confirm local/origin equality and clean tree/index;
   wait for exact-HEAD GitHub Actions completed/success before reporting done.

Acceptance: final resolution cannot be READY from the historical execution
receipt; qlog accounting rows cannot pass the new future model-support gate;
no historical mutation, data reopening, policy relaxation or model operation.
