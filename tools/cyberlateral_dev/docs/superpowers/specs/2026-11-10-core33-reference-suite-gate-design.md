# CORE33 — fixed reference suite in the development gate

Builder decision under standing offline delegation, not a new user product requirement.
BASE eee243da8c21d6f50effc17ff13d5077c5bc9325; existing host-owned linked worktree.

## Intent and approaches

The CORE32 command exists but full DEV verification only discovers its unit tests.
Add an explicit cold command-level regression to dev.py verify without changing CLI,
auditors, formulas, vectors or frozen wheel. Considered direct API calls (cheaper but
not cold CLI), two subprocess CLI calls (selected: command boundary plus determinism),
and cloud publishing changes (unneeded and outside scope). Native inline TDD then one
fresh whole-branch review; no new package/network work or approval menu.

## Exact boundary

Use the development interpreter to run tools/core_reference_suite.py --run twice,
with -I -B. The child cwd is the caller-selected resolved output directory, which
may be inside or outside the component; an external cwd is not enforced. Recorded
CORE33 acceptance used external directories. This is development-tree CLI regression,
not installed-wheel isolation or a Python sandbox. Existing _run retains combined
stdout/stderr logs; separately preserve returned stdout as core_reference_one.json
and core_reference_two.json. Corresponding logs have .log names.

Preflight those four paths for collisions; xb writes remain authoritative against
races. Never overwrite or delete. First failed command or invalid stdout stops before
the second; second failure keeps the first receipt. BaseException propagates. No retry,
fallback or partial success; failure can follow nonzero synthetic work.

Each receipt must be exact built-in bytes of length10463 and SHA256
6dba6db52bbaf8a5e602a4c2266a2e29908629f894683c67bcdb11adaf32dead.
This is the complete canonical normal CORE32 receipt, including original child reports
and denial gates, not a new schema/numerical validator. Pin comes from CORE32 sealed
Evidence ZIP63fb38b5326ae689ff07fefa171557630b99b220337dc42c46718d33db525737,
member acceptance-1/direct-receipt.json. Do not regenerate or update the baseline
from current output. Invalid bytes, reformats, extra fields, noncanonical encodings,
forged counts/gates, ordinary suite differences and output errors cannot pass.

reference_suite_pair_summary(first: bytes, second: bytes)->dict validates identity and
byte equality without JSON parsing/model/reference/quantizer calls. It returns
CORE33_FIXED_REFERENCE_SUITE_GATE_PASS, invocation_count2, case_count_per_invocation6,
audit_counts_per_invocation6/0, observed_counts4/1/1, reported_model_steps19 per call/38
for this pair, runtime_attestation=false, numeric_preflight NONZERO_NOT_AGGREGATED,
receipt identity and two JSON file hashes, plus explicit development-tree-only scope.

verify_reference_suite(root,python,output,cwd)->dict in integration_tools/verify.py
uses the existing subprocess runner, validates each stdout before proceeding and
returns the pair summary. Errors use REFERENCE_SUITE_GATE_FAILED_WORK_MAY_BE_NONZERO.
Call after static checks/own compiles and before wheel work. Add summary under
synthetic_core_reference_suite before final SUMMARY.json/Manifest publication.
All four artifacts are covered by the existing final Manifest. Existing top-level
gate status and cloud consumer remain compatible; no cloud code/CI/network changes.

## Limits and success

Normal explicit pair: reported38 synthetic model calls, reference generation0;
unit/full-gate additional numeric work nonzero/unaggregated. Pins prove fixed bytes,
not current source authentication, general correctness, timing bounds or runtime
attestation. Capture is the existing trusted subprocess mechanism, not hostile
output-budget/deadline isolation. Existing stdout/stderr logging limitations stay.
Existing output precondition and imported/runtime checks remain before work.

Actual r/T2/vehicle_scale=null,R_BUDGET UNRESOLVED,Static Evidence Gate FAIL;
actual inputs/F61/Controller/Runtime/CAN/actual r/dt0,F70UH/V/F71 NOT_ALLOWED.
Preserve all prior source except verify.py and README/backlog/CORE32 guide navigation;
new files are validator,tests,CORE33 guide,spec,plan. No merge/push/PR/CI/HF writes.
Success requires TDD,full DEV/static/wheel,actual two-process independent checks,
failure preservation,source/ref custody,review and independently verified unsigned ZIP.
