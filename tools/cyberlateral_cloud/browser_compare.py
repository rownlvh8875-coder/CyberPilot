"""Read-only exact saved-byte comparison, never a new browser or quality assessment."""

import argparse
import json
import sys
from pathlib import Path

from artifacts import sha
from browser_verify import load_saved_browser


def compare_saved_browser(baseline: Path, candidate: Path) -> dict:
    loaded = []
    for side, root in [('BASELINE', baseline), ('CANDIDATE', candidate)]:
        try:
            loaded.append(load_saved_browser(root))
        except ValueError as error:
            raise ValueError(side + '_' + str(error)) from None
    (baseline_receipt, before), (candidate_receipt, after) = loaded
    differences = [
        {'path': name,
         'baseline': {'sha256': sha(before[name]), 'byte_size': len(before[name])},
         'candidate': {'sha256': sha(after[name]), 'byte_size': len(after[name])}}
        for name in sorted(before) if before[name] != after[name]
    ]
    return {
        'schema_version': 1,
        'status': 'R66_SAVED_BROWSER_BYTES_DIFFERENT' if differences else 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH',
        'comparison': 'EXACT_SAVED_BYTES',
        'compared_files': len(before), 'changed_files': len(differences),
        'unchanged_files': len(before) - len(differences), 'differences': differences,
        'baseline_verification': baseline_receipt, 'candidate_verification': candidate_receipt,
        'quality_assessment': 'NOT_PERFORMED', 'source_identity_reauthenticated': False,
        'comparator_browser_model_F61_vehicle_executions': 0,
        'scope': 'SAVED_BYTES_COMPARISON_NOT_VISUAL_OR_ORIGIN_ATTESTATION',
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_saved_browser(args.baseline, args.candidate)
    except ValueError as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 1 if result['changed_files'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
