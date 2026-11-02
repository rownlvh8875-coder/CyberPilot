# R43 bounded multi-seed synthetic campaign

## Intent and author decisions

R42 already generates one seed's bounded synthetic cases and runs the unchanged
R40/R39 selected-source reference checks. Add one explicitly requested multi-seed
campaign, keeping complete results for every seed and numerical/error findings.
The user delegated routine offline choices and opted out of repeated approvals;
the limits/CLI below are the author's choices, not vehicle/rate-policy approval.
Base main97191972cc72ed9dfa9048ed8f0c3c7134321b84. Deliver reviewed feature PR only;
no main merge or HF refresh in this implementation stage.

Approaches: manual shell loop lacks one validated overall verdict; a new generator/
oracle changes trusted math unnecessarily; selected sequential composition of R42
preserves existing input/state semantics and independent reference authority.
Counterexample minimization waits for an independently reproducible numerical issue;
the full history remains necessary and is never truncated or renumbered here.

## Interfaces and bounds

- `integration_tools/scenario_campaign_evidence.py`: `CampaignError(ValueError)`
  with `.code`, `capture_tree(root:Path, *, max_files:int=2048,
  max_bytes:int=134217728)->dict[str,str]`, `verify_manifests(root:Path, hashes:dict)->None`.
  Hash only regular no-follow/nonblocking files, reject directory/file symlinks,
  nonregular files, unsafe names, depth>16, >16MiB/file and bounded total/count.
  Verify root/nested closed SHA256SUMS; portable manifests are checked subsets.
- `integration_tools/scenario_campaign_run.py`:
  `run_campaign(seeds:list[int], cases:int, steps:int, output:Path)->dict`,
  `exit_code(record:dict)->int`. Seeds must be a builtin list of1..4 unique builtin
  uint32 ints in explicit order. Cases1..16, steps16..256 use R42 exact validation.
  At most16384 declared samples. Reject all bad parameters before output/model work.
- `tools/scenario_campaign.py`: required repeated `--seed`, `--cases`, `--steps`,
  `--output`, allow_abbrev=False. No defaults/input/baseline/r/dt/vehicle options.
  Follow existing private-pycache/stdlib frontend pattern; no model/NumPy/native import.

## Execution and evidence

Use R42's new-output/runtime/location checks with CAMPAIGN-prefixed error codes.
Run each seed sequentially under `runs/seed-001` etc.; state never crosses seeds.
Retain child R42 trees unchanged, including full original reproducer JSON and reports.
Read bounded canonical child EXPLORATION.json and compare its exact bytes with the
returned object, its requested parameters/source identity/gates, consumed counters
and finding paths/hash bindings. Validate every child Manifest before aggregation.
Snapshot relevant R42 identity plus the three R43 sources before/after; recheck each
child tree after all runs. Cooperative before/after observation, not origin/atomic proof.

Completed MATCH/DIFFERENT/ERROR children all remain visible and later seeds still run.
Any ERROR outranks DIFFERENT, which outranks MATCH. MATCH requires every seed/case,
exact declared model/reference counts and zero differences/findings. DIFFERENT needs
positive actual reference differences, not worker failure. ERROR preserves known
nonnegative counters; failed reference work may be additional NONZERO/unaggregated.
Malformed/contradictory child evidence or thrown worker/source/IO failure aborts:
stable REJECTED/exit2, preserve completed/partial children, no campaign completion marker.
No retry/resume/overwrite, no silently missing seed and no0-case vacuous MATCH.

Root CAMPAIGN.json contract `R43_DECLARED_SYNTHETIC_SEED_CAMPAIGN_V1` contains schema1,
ordered parameters, per-seed status/record SHA/counts/report/reproducer links,
reported model/reference/difference totals, status counts, source identity, unchanged
gates, explicit state/time/accounting/claim scopes. SUMMARY_KO.md links existing child
graphs/reports/whole reproducers, not a new HTML renderer. Root closed Manifest covers
all actual files; CAMPAIGN.json publishes last. Root capture caps8192 files/512MiB.
Private receipt/log bytes are not automatically shareable or repeat-identical.
Path-free CAMPAIGN/SUMMARY, child EXPLORATION/GENERATION and generated/portable bytes
are deterministic for the same ordered parameters/source/runtime.

## Safety and non-goals

Unchanged public0.3.0 model/API/wheel, selected-source oracle, R42 generator, app/HF
locks and dependencies. No log/vehicle/native input, F61/actualr/dt/Controller/Runtime/
CAN/candidate evaluation or deployment. No numeric rate/scale policy, tuning, tolerance,
baseline auto-update, upload, Git operation, exhaustiveness or physical safety claim.
Existing R_BUDGET unresolved, Static Gate FAIL, actualr/T2/scale null and all closed
Candidate/Runtime/F70UH/V/F71 gates remain exact. Invocation order is not elapsed time.

## Verification

TDD: strict bounds/order, real two-seed MATCH/repeat, coherent stored numerical mutation
under the real reference checker, completed reference ERROR plus later seed, fatal
worker interruption, bad/extra/corrupt/symlink child bytes, malformed child record,
late child/source mutation, complete reproducer links and source/hash/count bindings,
output collisions and real CLI errors/import boundaries/exit counts. Reuse one real
fixture only for expensive worker boundaries; never replace the numerical oracle
with a PASS stub. Full component gate and cloud suite/static/wheel preservation,
two explicit small campaigns + saved R34 comparison, fresh independent review and
actual PR CI. No HF upload/main merge at this stage; preserve all evidence/worktrees.
