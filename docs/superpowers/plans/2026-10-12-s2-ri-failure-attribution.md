# S2-RI failure attribution input audit

Baseline: a50d008e76b651d02ced30dbfcd810a141850170.
Specification: user's S2_RI_FAILURE_ATTRIBUTION_V1 request, especially STEP 2.

1. Verify exact remote/CI, public receipt chain and private result manifest.
2. Test then implement additive, read-only input completeness gate. Hash every
   manifest-listed file; inspect sealed job metadata, never decode private arrays.
3. If required stored target/current/path/context evidence is absent, stop at
   ATTRIBUTION_INPUT_INSUFFICIENT. No algebraic target recovery from errors,
   prediction regeneration, raw/causal access, ranking or gate reevaluation.
4. Run input audit twice independently, verify input bytes before/after and
   verify-only resume. Publish all requested evidence slots with explicit null
   analyses and NOT_RUN states, never a successful numerical attribution claim.
5. Independent review, focused/empirical/full regression, lint/syntax/JSON,
   publication/privacy, replay/SCons, documentation, additive commit/push and
   exact-HEAD CI.

Pre-flight finding: the frozen writer persisted one-step prediction, projected,
error and comparator_error; rollout persisted projected endpoint, error and
comparator_error. It did not persist current/target ticks, observed/projected
paths, command/speed/rail/prior-motion context. STEP 2 requires fail closed.
No numeric attribution implementation is justified for these unavailable inputs.
