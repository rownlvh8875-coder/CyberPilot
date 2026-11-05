# CORE20 saved input preflight CLI

Builder-selected small usability increment under delegated offline execution:
expose unchanged CORE19 through a standalone command, without a Python -c recipe.
Existing APIs, schemas, algorithms, readers, CORE18 CLI and frozen wheel stay unchanged.

## Approaches

Keeping only the manual Python recipe leaves path setup and exit classification
to callers. Reusing temporary-cache infrastructure adds writes/resource lifetime
this read-only command does not need. Chosen: one thin CLI with bytecode writes
suppressed throughout main, explicit source paths, no cache/temp allocation.

## Contract

`tools/core_sequence_input_preflight.py::main(argv=None) -> int` accepts exactly
one nonempty `--input-root PATH`. No abbreviations, duplicate roots, run/output/
format/rate/scale/time options or stdin input. Help exits0 without importing CORE19.
Syntax failures use fixed `INPUT_PREFLIGHT_USAGE_NO_MODEL_EXECUTION`, exit2, no
input metadata/read or project imports; no raw caller argv/data in diagnostics.

After parsing, temporarily prepend this component ROOT and ROOT/src, import
CORE19/canonical, call preflight_saved_sequence exactly once, serialize its unchanged
canonical JSON, and write stdout with a progress-checked short-write loop.

- INPUTS_COMPATIBLE -> exit0, including valid input with historical DIFFERENT or REJECTED.
- INPUTS_REJECTED -> exit1 and the full normal CORE19 receipt, not an exception.
- InputPreflightError -> exit2, empty stdout and fixed existing error.code on stderr.
- Unexpected import/API/serialization/output failures -> exit2 and fixed
  INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION. No false receipt on pre-output failure.
- Partial stdout already written cannot be retracted; callers must check exit status.

Save sys.dont_write_bytecode and sys.path before main work, suppress bytecode before
ArgumentParser/gettext cold imports, restore both on every path (including help,
syntax/import/API/stdout failures and BaseException propagation). Never alter
sys.pycache_prefix, tempfile.tempdir or temp environment configuration. Neither
implicit gettempdir probe nor temp/cache creation is used. From any cwd, source
selection is anchored to __file__, not caller cwd. Command guide uses -I -B.

Supported configured CPython3.12.13 Linux. No concurrency/repeated embedding,
interpreter/module import side effects before main, hostile objects/hooks/path
races/aliases, atime preservation, atomic snapshot, crash recovery or origin/math/
vehicle guarantees. stdout is explicitly caller-selected output, not a saved-file
publisher. Shell redirection into an input file is caller mutation and unsupported.

CORE19 remains closed CORE8 three-file intake with numeric validation NONZERO,
model/reference/F61/actualr-dt/Controller/Runtime/CAN0 in command operations.
Whole unit/gate fixture work is separately NONZERO_NOT_AGGREGATED. Actual r/T2/
vehicle_scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL; Candidate/Runtime=NO_GO;
F70UH/F70V/F71 and vehicle activation=NOT_ALLOWED. No merge/push/PR/CI/HF writes.

## Verification

Real CLI/API receipt parity for all three preserved outcomes, independent twice
subprocess runs with import/execution/read/mkdir/bytecode guards. Cold first-main
checks must avoid importing subprocess/locale in the child before the parser.
Test syntax before project import/path access, fixed diagnostics, error status,
short/zero/failing stdout writes, restoration and no temp discovery. Full DEV gate,
288 own compiles, frozen wheel unchanged; one final fresh whole-branch review.
