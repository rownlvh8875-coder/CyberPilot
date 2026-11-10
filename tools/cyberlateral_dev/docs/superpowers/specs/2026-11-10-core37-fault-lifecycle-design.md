# CORE37 — mixed fault-counter lifecycle across batch boundaries

## Intent and approaches

Existing lower-level tests already cover a 94-call positive constant-angle fault
cycle and isolated reset conditions. CORE31 starts from a declared counter88;
CORE36 covers driver/gate/history mixtures but uses angle0. Add two **new fixed
100-call canonical public API chains** combining those concerns without changing
runtime behavior. Standalone fault tests alone would duplicate existing coverage;
a new checkpoint/runtime feature is unnecessary. The author's delegated choice
is mixed-chain batch regression with manual expectations, not a new product API.

## Fixture and expected behavior

Both chains start with initial_state(),no injected nonzero seed. Use synthetic
scale16,UP2/DOWN5,allowance7/factor1/multiplier3. The first88 calls request +1
or -1 with angle +85 or -85 and active true. Applied ramps are explicitly
2/4/6/8/10/12/14 then sixteen through call87,with negative counterparts.
Declared warmup counters are1..88. These fixed progressions are manually authored,
not produced by the model,quantizer,oracle or source execution.

Calls88..99 (zero-based) use the following declared counter/flag sequence:
89/T,90/F,0/F,1/T,0/F,1/T,0/T,1/T,2/T,0/F,1/T,2/T.
Calls89/90 remain active with nonzero commands despite request suppression.
Call92 is inactive;93 resumes at opposite-sign exact85;94 drops just below the
threshold (84.99609375 magnitude);95 returns to85;96 adds opposing driver12.5;
97 is inactive again;98 is active with UP/DOWN0;99 restores2/5 and reverses request.
Separate declared limited/final vectors distinguish inactive pre-gate values
from zero applied history. Original source is inspected,not executed to build
the expected values;local preregistration is not a blind or external approval.

## Batch schedules and assertions

Per chain use sixteen two-chunk cuts after sample counts
1,7,8,87,88,89,90,91,92,93,94,95,96,97,98,99;
one multi-cut schedule at7,88,89,90,91,92,93,94,96,97,98,99;
and all100 singleton chunks. Exactly18 schedules per chain/36 total,not every
partition of100 samples. Also interleave both100-call streams as singleton
batches,keeping independent actual returned histories.

Compare every counter/fault/request flag,limited/final/projected integer,
quantized command,limiter previous and returned state with fixed expectations.
Compare complete outputs/final state with uninterrupted execution separately;
this full parity is same-implementation,not a full independent numerical oracle.
Check intermediate returned states at each chunk edge. Feed actual returned
state objects,never expected states;equal immutable internal copies are valid.

Two methods: per focused run4200 model/quantizer calls,494simulate calls,
42initializations and452caller-to-next-batch state links. Per proof8modes
(normal before/after+6mutants),33600model/quantizer;two proofs67200 each.
Additional unit/gate/reviewer work is nonzero and separately scoped.

## Mutation sensitivity and completion

Six valid-domain in-memory function-only mutants: zero incoming batch counter;
return incoming stale counter;zero active torque when fault suppresses request;
exclusive85 threshold;count inactive calls as active;retain counter when the
fault condition/active predicate clears. Each must cause assertion failures,
not domain/harness errors. Restore normal callables/source and verify GREEN.
Two proofs compare ordered event rolling hashes,counters and failure IDs;
retain failure logs,not repeated full traces;elapsed logs are not byte targets.

Full DEV1922PASS/static checks/331own compiles,frozen wheel and CORE32 pins
unchanged;source692/prior686/ref41 custody;fresh review and independent unsigned
ZIP CRC/Manifest/rebuild checks. Old changes limited to README/backlog links;
new test,Korean guide,this spec and plan only. Preserve all prior evidence.

## Exclusions and gates

No runtime/API/formula/oldtests/vectors/CORE32..36/cloud changes,no new reader,
persistence,concurrency,actual data,F61 import/compile/calculation,Controller,
Runtime,CAN,actual r/dt,remote publication or vehicle authority. This configured
environment/two fixed chains are not arbitrary-domain/native replay proof.
Actual r/T2/vehicle_scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL,
Candidate/RuntimeNO_GO,F70UH/V/F71/actual activationNOT_ALLOWED. Offline model
request suppression is not a physical steering-safety assertion.
