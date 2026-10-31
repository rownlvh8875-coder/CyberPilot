# R16 — fixed synthetic message handoff lifecycle

## Intent and delegated choice

R15 proves one contiguous fixed synthetic message-to-model chain. R16 checks
that the same extraction boundary still preserves owned state when a caller
pauses/resumes at every interior cut and alternates independent streams.
Routine next-step choices and inline execution were delegated by the user;
this bounded DEV choice is the implementer's, not a new vehicle approval.

## Approaches

1. Add only more contiguous-chain faults: smallest, but leaves segmented and
   alternating message callers unexercised.
2. Add a closed lifecycle runner over the existing frozen catalog: selected;
   tests the complete extraction-to-model path without opening data intake.
3. Add an arbitrary message/session reader: rejected; needs a separate source,
   custody, ABI and replay design and is not licensed by synthetic success.

## Contract

Use CPython 3.12.13, unchanged package/API 0.3.0 and all seven frozen fixtures
(112 samples). Refactor the existing R15 encode/extract/whole-prepared-check/
one-step operation into `_advance_owned(sample, state, sequence)` in its DEV
module. R15's complete installed RESULTS bytes must remain unchanged.
R14 extractor/types/probe, src, references, goldens, dependencies and workflows
are unchanged. The new runner takes no input other than a NEW output directory.

First run the existing R15 full chain. Recheck the catalog before lifecycle
work. For each scenario, execute both chunks at every cut in range(1,n),
passing the actual first chunk's final state to the second. Compare complete
frames, prepared values and combined output/final state with the full chain.
There are 105 interior cuts; history-scale has none and remains a declared
index1 seed, not observed prehistory. Preserve sign bits through canonical
binary64 JSON and explicit prior-request/prior-applied/counter/index values.

Then round-robin all seven streams in catalog order, one sample per live
stream per round, maintaining a distinct actual owned state for each stream.
Record each event's scenario, offset, frame, prepared input and output. The
whole interleaved event trace must equal the corresponding full-chain rows.
No simulate/prefix replay is substituted for message extraction plus step.

Counts per fixed lifecycle process (not aggregate tests): full112 + all split
chunk transitions8786 + round-robin112 = 9010 extractions and model steps;
prefix validation calculations0. Counts describe synthetic invocation work,
not time, performance, r, dt or physical behavior.

## Artifacts and acceptance

RESULTS includes the complete baseline R15 trace, all105 split certificates
(cut, prefix final state, first resumed prepared state, combined frame/
prepared/result hashes), and the full112-event interleaved trace. A stdlib-only
validator first validates the embedded baseline against the old input/result
hash authorities and independently reconstructs each cut and event's expected
record from that frozen trace. It rejects omissions, duplicate/reordered cuts
or events, identical poisoned pairs with rewritten checksums, noncanonical
JSON, changed gates/claims/environment and promoted seed custody.

Run in two empty installed-wheel environments with -I/-B and no NumPy; record
actual isolation/package/module facts. Publish RESULTS.json last, after both
payload and checksum writes. Existing file/dir/dangling links and unknown
input/native/r/dt flags reject before work. Failure does not produce a
designated successful result. Concurrency and crash durability are not promised.

## Boundaries

This is a closed same-process synthetic lifecycle regression, not a public
checkpoint format, persistent restart service, independent numerical oracle,
native custody proof or hostile-authority authentication. An underscore
helper accepting owned objects is not authorization for arbitrary log intake.
No native Q01-Q06/schema/Controller/Runtime/CAN/F61 execution, actual vehicle
input, r/dt calculation, capture, policy selection, install/deploy or main
merge. Prior two extracted helper bodies remain authorized only in inherited
synthetic DEV reference checks. Actual r/T2/scale remain null; R_BUDGET
UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.

## Completion

Named RED-to-GREEN tests, full component regression/static/wheel gate, fresh
archive/new venv reproduction, one independent whole-branch review, then push
the existing feature branch and update its existing Draft PR. Every commit
uses [skip ci]; dispatch only the dedicated offline workflow, verify exact
HEAD/artifact hashes and keep main unmerged. Do not claim full log/install
Manifest identity across environments or browser visual quality.
