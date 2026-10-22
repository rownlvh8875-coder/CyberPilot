# Track F9: versioned F8 evidence adapter v1

This is a diagnostic-only adapter for the **exact previously audited local F8
delivery**, not a new controller or a performance qualification procedure.

- Evidence source HEAD: `03cffd30998551b56ad7774223b8bdd0b790d228`.
- ZIP SHA256: `2bca346bd8af0bdf1278fc65b6dca0f2cf9a5facdf32d6a1cb5cd399ed0e75c0`.
- Manifest SHA256: `c40ec405a12a37adcee0bb25e09684c30091c6af764069959130dcbb7653ea62`.
- F8 receipt: `7cd794d1ba3bb0235f5c24f95df8764696bcd7061bf7f4aea1d8b03fd0d739d9`.
- Namespace: `CYBERPILOT_F9_F8_DIAGNOSTIC_SIDECAR_V1`.
- Contract: [track-f9-f8-evidence-contract-v1.json](track-f9-f8-evidence-contract-v1.json).

The manifest lists 472 files, excluding itself; the ZIP contains 473 regular
entries. Both distinctions are checked. A local content hash establishes
consistency with the audited delivery, **not an independent external signer or
proof that arbitrary self-consistent data came from an authentic experiment**.
No raw archive, original trace, or experiment script is included in this change.

## Execution

Use the Linux/POSIX development environment and an explicit authorized local
read capability. The output parent must already exist. The output directory
must be new and outside both the source repository and the read root.

```bash
python3 -B -m tools.cyberpilot.offline_f8_evidence_v1 \
  --archive /authorized/f8/cyberpilot-track-f8-20261022-final.zip \
  --read-root /authorized/f8 \
  --output /isolated-output/f9-run-1

python3 -B -m unittest \
  openpilot.tools.cyberpilot_tests.test_f8_evidence_adapter_v1 \
  openpilot.tools.cyberpilot_tests.test_f8_evidence_trace_v1 \
  openpilot.tools.cyberpilot_tests.test_f8_evidence_diagnostics_v1
```

There is no pin override, untrusted source import, archive extraction, network
operation, controller call, CAN/Params access, runtime apply, candidate ranking,
selection, or performance pass operation. Archive path strings in historical
locks are inert identities. They map only to pinned repository sources or
verified members; they are never executable paths.

## Boundary and mapping

The path is:

`Pinned ZIP -> bounded reader -> private strict JSON -> checked F8 records
-> immutable F7 Frame values -> unchanged F7 pure metric calculator
-> separate F8 diagnostic sidecars`.

F7 files, its original trusted evidence inventory, 28 metric definitions and
10 hard-gate definitions are unchanged. The F7 historical gate validator is
**not run on a different F8 raw schema**. Each output says
`NOT_RUN_DIFFERENT_SCHEMA`; inherited HG05/HG06 labels inside F7 metric values
are references, not claims that F7 gates passed. F8 source, time, state, command,
measurement and arithmetic checks are identified separately.

Each derived trace retains 22 computed and six unavailable F7 metric statuses.
F8 evidence status is reported separately:

| Item | F8 sidecar status | Limit |
| --- | --- | --- |
| frequency_response | ADDITIONAL_EXCITATION_REQUIRED | 72 local tone/window estimates; no full nonlinear response |
| settling_time | DEFINITION_APPROVAL_REQUIRED | 909 explanatory grid combinations, not acceptance rules |
| transition_and_s_curve | EVIDENCE_OBTAINED_DIAGNOSTIC_ONLY | 24 executed arm conditions |
| speed_and_disturbance | EVIDENCE_OBTAINED_DIAGNOSTIC_ONLY | 29 executed, three A2 preflight blocks |
| initial_state_coverage | EVIDENCE_OBTAINED_DIAGNOSTIC_ONLY | 28 initial conditions; reset supplement separate |
| measurement_robustness | MEASUREMENT_CONTRACT_UNVERIFIED | 28 synthetic conditions, not real sensors |

Mapped physical outputs are post-step values at `(sequence+1)*0.01 s`.
Reference and actual pose use metres/radians. Positive normalized command maps
to negative Plant input and negative curvature; yaw has the declared opposite
curvature sign. Measurement curvature is reconstructed from acquisition history,
including declared priming, noise and bias. Truth curvature is used for metrics,
not substituted for recorded controller feedback.

F7 derivative arithmetic prepends zero. This convention is preserved, even for
the F8 nonzero-history case. A separate initial-aware derivative uses the actual
declared previous physical applied command. Initial heading is retained
explicitly; integrated yaw error describes heading **change**, not an assumed
zero initial heading. Auxiliary F7 reference-polyline distance remains a
full-record diagnostic and is never supplied to a controller.

## Reset and feasibility

`RESET_MODE_A` is the original SG-A explicit reset: the Stock controller is
fresh, while the governor owns and retains its prior state.
`RESET_MODE_B` is the separately identified reset supplement: Stock controller
and candidate are reconstructed; physical Plant, pose and delay queue continue.
A0/A2/A3 original optimizer event resets have their own label. These historical
conditions are not rewritten or blended.

The adapter checks event ordering, fresh reset state, previous/next state
continuity, measured feedback binding, candidate arithmetic, the one physical
delay queue, curvature/yaw recurrence, heading and pose integration. It does
**not** independently rerun Stock PID/filter/reference-buffer updates. Historical
profile/call records and sealed producer sources support the recorded execution
claim; they do not prove hardware performance or external authenticity.

Mathematical Plant validity, development envelope admission and dynamic
tracking quality are separate fields. A2 speed/envelope preflight blocks remain
blocks. The named 30 m/s A0 observation is bound to its exact trace hash:
normal RMS 134.18535449526564 m and rail occupancy 0.777. Its
`SEVERE_TRACKING_DEVIATION_OBSERVED` label describes that observation only;
it introduces no numerical classifier or vehicle safety threshold.
All results remain `DYNAMIC_FEASIBILITY_UNQUALIFIED` and
`PERFORMANCE_NOT_QUALIFIED`.

## Resource and output contract

POSIX directory descriptors and no-follow opens reject symlinks in both the
input and output paths. ZIP central-directory records are bounded before
`ZipFile` allocation. Duplicate/path-traversal/special/encrypted/ZIP64 entries
and unlisted files are rejected. SHA mismatch, duplicate JSON keys,
NaN/Infinity, invalid frame sequences and measurement signs fail closed.

Resource bounds are independent of performance criteria:

- ZIP: 320 MiB; entry: 4 MiB; 512 entries; outer inventory: 384 MiB.
- Cumulative member reads: 768 MiB, including rereads.
- Decoded trace: 40 MiB; cumulative decoded data: 5 GiB; compression ratio: 200.
- At most 4,000 frames per trace; one decoded raw trace at a time.
- Output: 8 MiB per file, 128 MiB total; only new exclusive files.
- The small frozen SG-A reset comparison is retained alongside the current trace.

The reader pins an open descriptor, hashes each buffer, checks file metadata
before/after processing and hashes the entire archive again before completion.
This is a trusted local immutable-file assumption, not synchronization with an
arbitrary concurrent writer. A new output starts with `INCOMPLETE.json`.
Only after all checks and the final archive hash does it receive a sealed
`summary.json`; successful completion removes the incomplete marker. Partial
outputs are evidence of an incomplete attempt and must not be qualified.

The declared cohort is 145 main repeated execution pairs, three blocked pairs,
and four reset supplement pairs: 298 historical executions, 740,000 total
historical frames, 370,000 unique frames and 149 identical repeated traces.
The adapter verifies recorded evidence; it performs zero new controller
executions. Repeating it checks diagnostic determinism, not new closed-loop
repeatability.

## Integrity, CI and further authorization

New tests live under `openpilot/tools/cyberpilot_tests`, outside the fixed
AutoTune/Controls ID scope. They are targeted independently and are discoverable
by the existing Upstream Unit runner. The 5,960 Legacy/Full CI V2 IDs, historical
5,927 baseline, fixture groups, workflows, Frozen manifest and native receipt
contracts must remain unchanged.

F8's 28 historical Ruff findings are preserved with the sealed source. They are
not adapter findings, and do not refer to the upstream ty diagnostic total.
Adapter quality and regression checks are separate.

This contract remains `effective=false`, `diagnostic_only=true`,
`performance_qualified=false`, `runtime_authorized=false`, vehicle authority
NONE and selections null. D2 is PERFORMANCE_NOT_EVALUATED; Private E2 is
NOT_AUTHORIZED; HOLDOUT is CLOSED. No source, policy, measurement threshold,
required check, PR readiness or vehicle authority is granted by a valid report.

Any additional evidence inventory, different source, measurement/freshness
contract, full-response excitation, settling acceptance rule or changed adapter
definition requires a new reviewed contract/source identity. Do not overwrite
historical receipts. Rollback is removal/revert of this additive adapter commit;
all historical sources/evidence and existing F7/Legacy/Native paths remain intact.
