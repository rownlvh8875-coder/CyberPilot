# R15 — fixed synthetic extraction-to-model handoff

Small DEV integration extension over unchanged R14 extraction and pure0.3.0 model.
User delegated routine next-step choices; the following design choices are the
author's, not native/vehicle permission or rate-policy approval.

## Intent and alternatives

R14 prepares inputs but does not execute a transition. Verify that an independent
fixed runner passes those exact prepared values into the already authorized pure
synthetic step and carries its own immediate prior output to the next invocation.
Alternatives: modifying R14 to compute would break its copy-only contract; a native
reader would open the still-prohibited Q01-Q06 scope. Selected: separate fixed DEV
runner. Neither existing component changes, and no live hook or new data mode exists.

## Interface and sequence

integration_tools/message_handoff.py exposes run_handoff_chain()->dict and CLI
main(argv=None), only --output NEW. No caller data, context/seed, timestamp, policy,
source-root or native argument. HandoffError(RuntimeError) rejects an incomplete
chain; no repair/default or partial PASS. Helper _encode(sample,state,sequence)
builds only R14 SyntheticBoundaryFrameV1 from trusted fixed synthetic values.

Use exactly the existing fixed_catalog:7 scenarios/112 samples, catalog SHA
74095144882ff3977679ce92ec7dad0e7bf3f532a0cacae2cfa26f4aab0fd287. Check package0.3.0,
catalog and expected scenario IDs/counts before model work. Expected result hashes
are existing synthetic_harness_expected_v1.json regression values, not a new oracle.

For each scenario start with its explicit registered initial_state. For each sample:
encode nested frame -> unchanged R14 extract -> check the complete prepared record
against original fixture sample and owned state/claims -> one public p.step -> retain
output.next_state for the next iteration. Never use p.simulate or prefix recomputation.
Require exact PreparedLateralInputV1/public nested types, canonical full sample/state/
metadata equality (including signed zero), before the current model call. A mismatch
is HANDOFF_PREPARED_MISMATCH; extraction ValueError becomes HANDOFF_EXTRACTION_REJECTED
and model ValueError becomes HANDOFF_MODEL_REJECTED with original cause chained.
Unexpected output type is HANDOFF_MODEL_OUTPUT; complete result hash must match the
frozen golden or HANDOFF_GOLDEN_MISMATCH. No source/controller or F61 invocation.

Records contain id/steps/initial_state/source_samples, all source frames and prepared
records, full SimulationResult and result_sha256. Sequence label is handoff_ + id.
Canonical seed label: DECLARED_CANONICAL_SYNTHETIC_INITIAL_STATE; history-scale seed:
REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY. The latter's index1 does not prove
an observed invocation0. All subsequent state is OWNED_IMMEDIATE_PRIOR_MODEL_OUTPUT
inside this fixed run, NOT actual native custody. R14's declaration-only claim stays.

Report extractor_calls=112/model_steps=112/prefix_validation_steps=0 per fixed
handoff process, not aggregate unit/reference activity. Package0.3.0/wheel and
R9/R12/R14 code, catalogs/goldens/contracts remain unchanged. Counts are synthetic
invocations, NOT seconds, physical rates, candidate performance or r/dt calculation.

## Artifact acceptance and checks

integration_tools/handoff_validation.py contains stdlib-only
handoff_pair_summary(first:Path,second:Path)->dict, imported by verify.py.
The verifier's verify_installed_handoff(root,python,output,cwd)->dict runs the new
script twice under -I/-B with unchanged installed wheel, empty venv, unrelated cwd,
no NumPy or original modules. Validate canonical full paired bytes and Manifest.

Accept top contract F70UGZ_R15_FIXED_SYNTHETIC_HANDOFF_V1, status
F70UGZ_R15_SYNTHETIC_HANDOFF_CHAIN_PASS and exact unchanged gates/metadata/counts.
Rebuild the fixture catalog digest from each record's source_samples/initial_state;
match the existing catalog hash. Check every full result hash against frozen golden.
For each position independently reconstruct expected frame and prepared dictionaries
from the sealed input sample and initial/previous frozen output state; require exact
canonical equality. Thus recomputed checksums, altered traces/seed claims or two
identically corrupted outputs cannot pass. This is consistency against trusted
reviewed fixtures/results, not adversarial authentication or new arithmetic proof.
CLI rejects existing files/dirs/dangling links/unknown modes before work, stages the
payload and checksum, publishes RESULTS.json last. Failure directories are not PASS.

## Unchanged boundaries

No original/native/schema/Controller/Runtime/CAN/F61 execution/compile/import, actual
data, capture, deploy or main merge. Native Q01-Q06 remain NOT_AUTHORIZED/NOT_RUN.
R14 extractor/probe still perform zero transitions; only the separate R15 runner
adds112 explicit pure model steps per process. Existing2 exact helper bodies remain
authorized only in inherited DEV reference tests, never this installed runner.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
Candidate/Runtime=NO_GO; actual activation/F70UH/F70V/F71=NOT_ALLOWED;
SOURCE_SCHEMA_UNQUALIFIED=6000; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN. No concurrency/persistence,
physical safety, native presence/ABI, actual snapshot or vehicle approval claim.
