# Process replay

Process replay is a regression test designed to identify any changes in the output of a process. This test replays a segment through individual processes and compares the output to a known good replay. Each make is represented in the test with a segment.

If the test fails, make sure that you didn't unintentionally change anything. If there are intentional changes, the reference logs will be updated.

Use `test_processes.py` to run the test locally.
Log files are cached by default. Use `DISABLE_FILEREADER_CACHE='1' test_processes.py` to disable caching.

### Pinned reference bundle (this fork)

`reference_bundle.json` binds producer `c8fb906815530460ed156f14e09e1f312bb0f851`
to existing `commaai/ci-artifacts` revision
`eab2cc2b1f6de3773617937868442520c7ef554c`. All66 compressed references were checked
against that revision's Git blobs and recorded size/SHA256; none were regenerated.
There is no latest-upstream fallback.

Before native imports, the runner checks its protected tracked-source projection,
root build/dependency inputs, submodule pointers, checked-out opendbc and schema.
The replay harness and independent `tools/cyberlateral_dev` / `cyberlateral_cloud`
directories are excluded from the producer projection. A shallow checkout is
supported: the historical producer object need not exist locally.

Before downloading input segments or decoding/replaying anything, all selected
reference names and compressed bytes must match the lock. Downloads use the
immutable artifact revision. Existing local fakedata references must also match;
a corrupt cache is rejected, not silently replaced. Workers consume the verified
bytes, not a reopened path. Decode failures do not create unreferenced replay runs.

Preflight failures exit2 with a diagnostic code. A legacy `ref_commit` may agree
with the lock but cannot override it. `--update-refs` is explicitly rejected and
argument abbreviation is disabled. Changing producer/source/schema requires a
separate reviewed baseline update; widening numerical tolerances is not a fix.
These checks establish declared source/reference consistency, not complete build,
runtime-environment, actual deployment or vehicle qualification.

Run the stdlib-only fixture tests without importing the eager replay package:

```sh
python -B openpilot/selfdrive/test/process_replay/test_reference_bundle.py -v
```

This command performs no native log decode, replay, Controller or Runtime work.
The tests and compressed-byte checks do not establish end-to-end replay PASS.

Currently the following processes are tested:

* controlsd
* radard
* plannerd
* calibrationd
* dmonitoringd
* locationd
* paramsd
* ubloxd
* torqued

### Usage
```
Usage: test_processes.py [-h] [--whitelist-procs PROCS] [--whitelist-cars CARS] [--blacklist-procs PROCS]
                         [--blacklist-cars CARS] [--ignore-fields FIELDS] [--ignore-msgs MSGS] [--update-refs]
Regression test to identify changes in a process's output
optional arguments:
  -h, --help            show this help message and exit
  --whitelist-procs PROCS               Whitelist given processes from the test (e.g. controlsd)
  --whitelist-cars WHITELIST_CARS       Whitelist given cars from the test (e.g. HONDA)
  --blacklist-procs BLACKLIST_PROCS     Blacklist given processes from the test (e.g. controlsd)
  --blacklist-cars BLACKLIST_CARS       Blacklist given cars from the test (e.g. HONDA)
  --ignore-fields IGNORE_FIELDS         Extra fields or msgs to ignore (e.g. driverMonitoringState.events)
  --ignore-msgs IGNORE_MSGS             Msgs to ignore (e.g. onroadEvents)
  --update-refs                         Rejected; requires a separate approved reference-generation workflow
```

## Forks

This fork uses the reviewed bundle above. Ordinary comparison runs save current
outputs but never approve or adopt them as goldens. Baseline generation, review
and publication are separate work: a changed producer requires a compatible
source/schema inventory, immutable artifact revision and independently checked
byte hashes. Merely editing `ref_commit` is insufficient.

## API

Process replay test suite exposes programmatic APIs for simultaneously running processes or groups of processes on provided logs.

```py
def replay_process_with_name(name: Union[str, Iterable[str]], lr: LogIterable, *args, **kwargs) -> List[capnp._DynamicStructReader]:

def replay_process(
  cfg: Union[ProcessConfig, Iterable[ProcessConfig]], lr: LogIterable, frs: Optional[Dict[str, Any]] = None,
  fingerprint: Optional[str] = None, return_all_logs: bool = False, custom_params: Optional[Dict[str, Any]] = None, disable_progress: bool = False
) -> List[capnp._DynamicStructReader]:
```

Example usage:
```py
from openpilot.selfdrive.test.process_replay import replay_process_with_name
from openpilot.tools.lib.logreader import LogReader

lr = LogReader(...)

# provide a name of the process to replay
output_logs = replay_process_with_name('locationd', lr)

# or list of names
output_logs = replay_process_with_name(['ubloxd', 'locationd'], lr)
```

Supported processes:
* controlsd
* radard
* plannerd
* calibrationd
* dmonitoringd
* locationd
* paramsd
* ubloxd
* torqued
* modeld
* dmonitoringmodeld

Certain processes may require an initial state, which is usually supplied within `Params` and persists from segment to segment (for example `CalibrationParams` or the learner cache keys like `LiveParametersV2`). The `custom_params` is a dictionary used to prepopulate `Params` with arbitrary values. The `get_custom_params_from_lr` helper is provided to fetch meaningful values from log files.

```py
from openpilot.selfdrive.test.process_replay import get_custom_params_from_lr

previous_segment_lr = LogReader(...)
current_segment_lr = LogReader(...)

custom_params = get_custom_params_from_lr(previous_segment_lr, 'last')

output_logs = replay_process_with_name('calibrationd', lr, custom_params=custom_params)
```

Replaying processes that use VisionIPC (e.g. modeld, dmonitoringmodeld) require additional `frs` dictionary with camera states as keys and `FrameReader` objects as values.

```py
from openpilot.tools.lib.framereader import FrameReader

frs = {
  'narrowRoadCameraState': FrameReader(...),
  'wideRoadCameraState': FrameReader(...),
  'cabinCameraState': FrameReader(...),
}

output_logs = replay_process_with_name(['modeld', 'dmonitoringmodeld'], lr, frs=frs)
```

To capture stdout/stderr of the replayed process, `captured_output_store` can be provided.

```py
output_store = dict()
# pass dictionary by reference, it will be filled with standard outputs - even if process replay fails
output_logs = replay_process_with_name(['radard', 'plannerd'], lr, captured_output_store=output_store)

# entries with captured output in format { 'out': '...', 'err': '...' } will be added to provided dictionary for each replayed process
print(output_store['radard']['out']) # radard stdout
print(output_store['radard']['err']) # radard stderr
```
