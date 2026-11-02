# R42 deterministic synthetic boundary exploration

## Intent, scope and authority

Extend the offline DEV tools beyond hand-authored scenarios: generate bounded reproducible R31 JSON inputs, run the unchanged R40 workflow, compare the unchanged public0.3.0 model with the existing independent selected-source reference, and retain complete reproducible failing inputs. The user chose this recommended next step and previously delegated routine choices without repeated approval questions. The exact parameters below are the author's engineering choices, not vehicle/Owner rate-policy approvals.

Base: CyberPilot main `491965b8be2861df8b3933bb70487093df37e302`. This is DEV orchestration only; no public model/API/wheel/lock/source authority change and no new dependencies. No native, vehicle/log input, F61, actualr/dt, rate-policy selection, Controller/Runtime/CAN, performance tuning or vehicle activation.

## Approaches

1. Add more hand-authored fixtures: cheap but no reusable automatic exploration.
2. Unbounded random fuzzing/new oracle: hard to reproduce, changes too many trusted boundaries, unnecessary.
3. Selected: a deterministic bounded generator feeding the existing isolated R40/R39 workers. Tradeoff: finite input coverage and selected-source parity only, not exhaustive fuzzing or physical safety.

## New interfaces

- `integration_tools/scenario_explore_generate.py`: `generate_cases(seed: int, cases: int, steps: int) -> dict[str, bytes]` and `generation_record(seed, cases, steps, payloads) -> dict`. Pure stdlib plus existing parser/canonical serializer; no model/reference/NumPy/native import. Reject non-builtin integer parameters (including bool), seed outside0..2**32-1, cases outside1..16, steps outside16..256. Total at most4096samples.
- `integration_tools/scenario_explore_run.py`: `run_exploration(seed: int, cases: int, steps: int, output: Path) -> dict`, `exit_code(record) -> int`, `ExplorationError(ValueError)` with `.code`.
- `tools/scenario_explore.py`: required `--seed`, `--cases`, `--steps`, `--output`; no defaults, input files, r/dt/vehicle/context options. CLI does not import model/NumPy/native in the frontend. Keep private temporary pycache pattern and existing isolated workers.

## Generator version1

Contract `R42_DETERMINISTIC_BOUNDARY_GENERATOR_V1`. Filenames `case-001.json` etc.; IDs `R42_<seed>_<ordinal>`. Canonical JSON, exact builtin floats (including signed zero) for samples and builtin ints for integer fields. Validate every generated payload with the existing R31 parser before any model work.

Deterministic discrete selection uses SHA256 over a documented ASCII generator-id/seed/case/offset/channel key, not process-global randomness or wall-clock time. Publish the algorithm and bind generator source identity. A fixed16-sample prefix combines request±1/signed zero, half-step rounding requests and their binary64 neighbors, driver fractional/opposing torque, abs-angle85 and adjacent dyadic values, and inactive/reset transitions. Remaining samples use seeded choices from bounded request/driver/angle/active catalogs. At least one prefix driver choice varies with seed. No rejection sampling or hidden state.

Four synthetic parameter/state profiles cycle by case ordinal: scales16/8/32/5; UP2/DOWN5 except an explicit zero-UP profile, driver allowance0/factor1/multiplier1. Case0 is canonical state index0; others declare resumed index5 with distinct previous_requested4/previous_applied-3 and counter88/89/90. These are synthetic stress seeds, not actual vehicle history or scale authority. Index remains below4096.

Generation metadata contains seed/case/step bounds, per-file raw SHA, synthetic profile/initial-state description and actual input feature counts: positive/negative/zero/signed-zero requests, request sign transitions, fractional drivers, inactive samples, abs-angle>=85 samples, resumed cases. These are input feature counts, not claims of exhaustive executed branch coverage.

## Execution, evidence and failure semantics

Check parameter, output path/UTF-8/runtime/source prerequisites before creating outputs or model work. Output must be a new path outside the component with an existing parent; reject existing/dangling symlink/nonexistent-parent/in-component paths. Never delete, resume or overwrite partial outputs. Snapshot relevant R42+R40 source hashes before and after computation; compare generated files to original owned bytes before publication. This is cooperative observation, not atomic source attestation.

Save generated input JSON under `generated/` and `GENERATION.json`, then run unchanged `run_workflow` into `workflow/`. Preserve all existing complete data, reports, input validation, worker errors and reference work accounting. No baseline argument or tolerance is added. For any non-MATCH reference case save a byte-identical **whole original sequence** under `reproducers/`, with its initial state, hash, case status, first difference/error and reference-report path. Do not truncate at the failing index or claim minimization; failure may depend on the prefix. Copy all flagged cases, not only the first.

Root `EXPLORATION.json` and Korean `SUMMARY_KO.md` link existing per-case HTML graphs/tables and reference reports. No new browser UI is required. Root Manifest covers every actual file including nested private receipts/logs; final completion JSON is written last. A marker alone is never success without full checksum validation. No upload, Git operation or automatic public sharing occurs inside this CLI.

Verdicts: `MATCH`/exit0 only if every generated case completed, workflow VERIFIED/reference MATCH and counts equal requested cases*steps. `DIFFERENT`/exit1 for actual reference numerical differences without higher-priority errors. `ERROR`/exit2 for reference ERROR, incomplete/rejected/unexpected statuses or contradictory counts. Preflight/worker/source/input changes/IO exceptions return REJECTED stable code/exit2 without root completion record; partial artifacts remain. Reference work counted only from successful reports; errors may have uncounted NONZERO work. Never turn0 matched cases into PASS.

Preserve unchanged gates in every top-level record: R_BUDGET=UNRESOLVED, Static Gate=FAIL, actualr/T2/vehicle scale=null, Candidate/Runtime=NO_GO, F70UH/V/F71=NOT_ALLOWED. Invocation order is not elapsed time or100Hz. No actual candidate/vehicle performance claim.

## Verification and completion

TDD for deterministic valid generation, strict builtin/bounds, prefix/seed diversity and domain checks, fresh real CLI run, exact repeatable portable outputs, unchanged gates, source/input tamper rejection, output guards, no forbidden frontend imports, independent-reference numerical negative control, preserved complete reproducer JSON, reference error distinct from differences, partial worker failure and root Manifest closure. Negative controls must exercise real R40/R39 arithmetic; only inject a targeted saved-field mutation or actual worker failure below the real checker.

Run the full component gate, cloud-tool tests, Ruff/Ty/Codespell/own compilation, unchanged wheel identity, two explicit generated runs with existing R34 same-input regression, and private Hugging Face evidence verification. Record explicit model/reference work separately from additional unit/gate work. Publish a feature PR only after independent review and fresh validation; do not assume main merge from implementation approval.
