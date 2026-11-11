"""Print a fixed synthetic call recording; no external input, capture or runtime."""

import argparse
import sys
from pathlib import Path
from typing import NoReturn


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, 'REJECTED: RECORDER_DEMO_ARGUMENTS\n')


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
    from integration_tools.offline_call_recorder import SyntheticCallRecorderV1
    from integration_tools.offline_recording_codec import encode_recording
    from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1

    context = SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
        'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'fixture-capture', 'fixture-controller', 'fixture-config',
        'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
    settings = SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
    recorder = SyntheticCallRecorderV1(2)
    for sequence, timestamp, word, active, reset, entry, saved, counter, next_counter in (
        (7, -9, '80000000', True, True, 12, -2, 3, 4),
        (8, -8, '00000001', False, False, -2, 4, 4, 5),
    ):
        request = SyntheticRequestSnapshotV1(context, sequence, timestamp, bytes.fromhex(word), active, False, reset)
        frame = SyntheticLimiterSnapshotV1(request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, next_counter, True)
        recorder.begin(request)
        recorder.complete(frame)
    sys.stdout.buffer.write(encode_recording(recorder.finish()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
