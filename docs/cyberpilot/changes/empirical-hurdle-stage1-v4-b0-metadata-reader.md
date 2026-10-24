# V4 B0: four-file metadata reader

## Identity and purpose

Cyber Validation, `feature/cyber-autotune`; baseline
`3e1be13c09710f924704f8d2ff89a76f166dbd88`. Add a metadata reader for the
explicit human-authorized `STAGE1_V4_B0_METADATA_VERIFICATION_EXECUTION`.
This change introduces no scientific evaluation or vehicle functionality.
The containing commit identifies the reviewed implementation.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot, same branch/baseline.
The [public request](empirical-hurdle-stage1-v4-evidence-access-scope-request.json)
binds exactly four record IDs and historical canonical receipt identities.
Saved schemas come from `empirical_hurdle_v4_execution.py::run` and
`empirical_hurdle_execution.py::run/repeated` at that baseline. Existing receipt
canonicalization is retained. Historical authorizations identify evidence;
they do not authorize this access. No external code or dependencies are adopted;
repository licensing is unchanged, with no relevant submodule change.

## Changes and expected effect

- `empirical_hurdle_v4_b0_metadata.py`: stdlib-only, caller-bound four-file
  read; exact schemas/fields, canonical receipt and identity-link checks.
- `tests/test_empirical_hurdle_v4_b0_metadata.py`: synthetic behavior and
  privacy tests, with no private paths or data.
- The trusted handoff, human-grant binding, host/root/volume checks, reviewed
  caller, private output and actual results remain outside Git.

The API accepts exactly the approved four ordered paths. Linux `openat2` uses
`BENEATH`, `NO_SYMLINKS`, `NO_MAGICLINKS` and `NO_XDEV`; no fallback, enumeration
or retry exists. A held root fd can be checked against the caller's prior
device/inode proof. Regular single-link targets and distinct file identities are
required. File size is bounded before reads; metadata stamps must remain stable.
Any conflict stops remaining reads. Actual successful target opens and bytes
are counted even when subsequent validation fails.

Caps are frozen from public schemas before inspecting target sizes:
V4 member ceiling = `32*(train6 + one-step6 + rollout16 + job2)+top3 = 963`;
V1 = the published `files_per_replica=5250`. ASCII member names are bounded by
Linux `PATH_MAX-1=4095`; each declaration allows a 64-byte digest and 64 bytes
of syntax/indent overhead, plus 4096 bytes fixed metadata. Thus V4 caps are
4,070,845 bytes each, V1 manifest 22,174,846, and repeatability receipt 4096.
These input bounds are not scientific parameters.

No member names are dereferenced, even for stat/header access. Observed raw file
SHA256 is distinct from canonical receipt SHA256. Without a trusted expected
raw digest the comparison remains `INPUT_INSUFFICIENT_NO_TRUSTED_EXPECTED_RAW_HASH`.
Canonical manifest equality does not reverify replica payloads.

## Regression risk and acceptance

Risks: malformed/oversize metadata, path aliases, mutation during a read,
schema drift, caller authorization errors and accidental private publication.
Tests reject these cases without weakening existing contracts. Caller trust and
Linux path-open guards are not an OS-wide process sandbox or protection against
every privileged mount mutation. Read-only access can update filesystem atime;
no whole-store fresh immutability proof is claimed.

Acceptance requires synthetic checks, two independent caller/reader reviews,
exact host/root/volume/reference binding, private output permissions and clean
exact-head CI before actual metadata reads. No automatic broad-verifier fallback
is allowed. Rollback is to stop this reader; no existing executor is changed.

## Validation method and actual results

Local validation results are recorded below before publication. Actual B0 result
receipts are private and are deliberately absent from this change record.

| Check | Actual result / limits |
| --- | --- |
| Reader synthetic tests | 41 PASS; four files, bounds, schemas, hashes, aliases, mutation, counters, privacy |
| Private caller synthetic tests | 5 PASS; permissions, held-directory race, exclusive output, verified source buffer |
| Windows junction fixture | New reader rejects the explicit synthetic junction; no E evidence involved |
| Independent reviews | Data integrity and authority/privacy review; exact byte identities retained privately |
| AutoTune/controls regression | 5207 PASS, 595.77s; real E masked by an empty read-only mount in the test namespace |
| Lateral synthetic replay | 16 PASS; isolated fixtures, no vehicle operation |
| SCons | PASS with existing venv activated; first attempt lacked venv build tools in PATH, no dependencies changed |
| Ruff / compileall / whitespace | PASS for the changed sources and existing CyberPilot validation scope |
| Public JSON / privacy | 808 existing JSON files parse; publication audit: 3 changed files, 0 findings; sealed tracked sources unchanged |
| Replay / simulation / shadow / vehicle | Not applicable; no control change, not executed or authorized |

## Handoff

No member payload equality is reverified: `REPLICA_PAYLOAD_EQUALITY_NOT_REVERIFIED`.
TRAIN rowwise gates remain `NOT_SAVED`. Existing V4
`HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED` and
`selected_candidate=null` are unchanged. B1/C/D/E/F remain unauthorized; no
threshold, coefficients, private path or manifest payload is published.
HOLDOUT remains CLOSED; vehicle authority NONE, NOT_READY,
REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED. Hugging Face is not used.
After the explicit four-file B0 operation, stop; subsequent access requires its
own approval.
