# CORE36: finite same-process partition/resume regression

## Intent and authority

Exercise the existing public `simulate(samples, state)` consumer with the two
nine-call CORE35 synthetic chains. No new runtime or persistent checkpoint API.
The unchanged CORE35 literal rows are the selected-field numeric authority;
they were already evaluated in CORE35, not newly blind holdouts.

## Required behavior

For each chain, enumerate every contiguous partition of its nine samples:
the eight possible internal cut positions give 256 partitions, 512 total.
Run each nonempty tuple chunk with the **actual returned** batch state, without
replacing it with expected state. Concatenated outputs and final state must
equal the uninterrupted run. Check each batch's returned state against the
literal prefix state. Recheck selected typed driver/rate/gate/projection/state
fields against the old literal rows, not only same-implementation parity.

Also run the two streams as interleaved singleton batches using separate
returned histories. Each stream must equal its uninterrupted result and the
selected old literals. Check the independently enumerated set of cut tuples.
No mandatory internal object-aliasing contract: equal immutable state copies
are valid. The harness itself feeds the actual returned state.

## Defects and validation

Target six in-memory mistakes in `simulate` only: reset incoming applied
history; replace it with previous request; save pre-inactive-gate limited
history inside a batch; return stale incoming applied history; drop the first
output; reverse batch output order. They keep valid state/index types. Each
must cause assertion failures, not harness/domain errors. Compile only the
function AST so existing result classes retain their identity. Restore the
original function and run GREEN. Do not modify source bytes for mutations.

Two repeat proofs count public simulate, public step and quantizer calls and
hash ordered observed inputs/outputs. Compare deterministic records, not log
elapsed times. Expected per focused run: 2 methods, 512 partitions, 2,582 batch
calls, 4,662 model/quantizer calls, 518 independent initializations, and 2,064
caller-to-next-batch returned-state links. Counts are for this focused run
only, not a whole-task work/performance measure. Each proof has two baselines
and six mutants: 37,296 model calls; two proofs 74,592. Additional unit/gate
and reviewer work is nonzero and separate.

## Boundaries

Only add a new test, this spec, plan and Korean guide; existing edits limited
to README/backlog navigation. Preserve old runtime/API/formulas/tests/literals,
CORE32 stdout pins, frozen wheel bytes and cloud gate behavior. No external
vehicle/production data, F61 import/compile/execution, Controller/Runtime/CAN,
actual r/dt, new input reader, cross-process resume or timing claims.
The finite two-chain result is not an exhaustive arbitrary-input theorem or
an independent full numerical oracle. Older fault/invalid-input coverage is
unchanged; angle zero means no new fault-threshold coverage here.

Actual r/T2/vehicle_scale stay null; R_BUDGET UNRESOLVED; Static Evidence Gate
FAIL; Candidate/Runtime NO_GO; F70UH/V/F71 and actual activation NOT_ALLOWED.
Local commits and external evidence only; no merge/push/PR/CI/HF publication.

## Completion

Focused GREEN and six assertion-RED/restored-GREEN mutations; two proof runs
byte-identical; full DEV gate and static checks PASS; prior source/ref/wheel
custody unchanged; fresh whole-branch review; independently verified unsigned
evidence ZIP. Preserve the host-owned worktree and evidence for future work.
