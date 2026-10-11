# Fixed source-grid observation diagnostic

User supplies the design and authorizes implementation through delivery.
This bounded extension preserves all historical files and private inputs.

1. Add failing numerical tests for int16 source codes, binary64 quotient
   half-to-even ties, Float32 emission, range rejection, shared support and
   six-scope exact directional gate. Implement empirical_grid_analysis.py.
2. Add failing store/identity tests. Implement empirical_grid_emission.py:
   freeze aggregate/hash policy before any NPY deserialization; bind V3 selected
   arrays and recovered origins; hash four historical input stores; read only
   six selected one-step arrays plus exact origin/receipt proofs; save projected
   codes/emissions privately, atomically, without overwrite. Run twice under
   forced raw-reader and raw-path exceptions. Compare all receipt/array bytes.
3. Publish only policy/results/readiness/repeatability aggregates; add pinned
   publication-chain tests. All six gates required for a nonexecuting V4
   observation contract; otherwise disclose tradeoff/rejection and close only
   the named simple-observation track. No refit/rollout/selector/holdout.
4. Independent review, focused/full AutoTune/controls/lateral replay, Ruff,
   syntax, publication/privacy/authority, whitespace and SCons. Complete feature
   record with actual six-scope numbers. Commit/push, wait exact-HEAD CI success,
   fetch, assert local/origin equality and clean tree.

Review focus: wrong Float32 multiplication order; tie semantics; silent range
clipping; substituted target/support/origin; hidden model/holdout promotion;
aggregate count weighting; old store mutation; raw logs accidentally reopened.
