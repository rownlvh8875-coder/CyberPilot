# CORE18-R1 cache isolation hardening

The CORE18 CLI must not create its private Python cache inside the saved input,
even when TMPDIR/TEMP/TMP or cached tempfile.tempdir points there. The inspection
API, fourteen-file capture, canonical receipt, comparison rules and exit0/2 stay
unchanged. No new calculator, model, reference or vehicle work is authorized.

For the configured CPython3.12.13 Linux environment, the CLI uses an explicit
`CACHE_PARENT = Path('/tmp')`. It never calls implicit tempfile directory discovery
or changes the process's temp configuration. Validate both external SHA formats
before input metadata or cache allocation. Require an existing, non-symlink input
directory and an existing, non-symlink cache parent outside that input. A parent
of the input is allowed: exclusive random cache creation cannot reuse an existing
input directory. Equal/descendant cache parent rejects with
`RUN_INSPECT_CACHE_INPUT_OVERLAP_NO_MODEL_EXECUTION`; unusable cache parent rejects
with `RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION`. No fallback.

Bootstrap own-source imports with bytecode writes disabled. Only the private
cache may receive subsequent bytecode writes. Restore `sys.pycache_prefix` and
`sys.dont_write_bytecode` on success, import failure, inspection failure, cleanup
failure and stdout failure. Cleanup completes before stdout receipt emission.

Input bytes, layout and filesystem modes remain unchanged. Atime, hostile path
races/aliases, atomic snapshots, crash durability, concurrent/repeated CLI
embedding, other OS/Python versions and origin/arithmetic/vehicle qualification
remain outside the guarantee. Existing whole DEV gate is mandatory; fixture
work in that gate is NONZERO_NOT_AGGREGATED, not inspection work.

Actual r/T2/vehicle_scale stay null; R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/F70V/F71 and vehicle activation=NOT_ALLOWED.
