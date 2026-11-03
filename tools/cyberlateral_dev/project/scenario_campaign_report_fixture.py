"""Real complete saved comparisons for R46 tests; never imported by the reader."""

import atexit
import shutil
import tempfile
from functools import cache
from pathlib import Path

from scenario_campaign_compare_fixture import change_saved_trace, copy_campaign, real_campaign

_scratch = tempfile.TemporaryDirectory(prefix='r46-comparisons-')
atexit.register(_scratch.cleanup)


@cache
def _real_comparison(kind):
    from integration_tools.scenario_campaign_compare_run import run_campaign_comparison

    home = Path(_scratch.name) / kind
    home.mkdir()
    if kind == 'truncated':
        old = real_campaign(seeds=(42,), cases=2, steps=256)
        new = copy_campaign(home / 'candidate', seeds=(42,), cases=2, steps=256)
        change_saved_trace(new, many=True)
    elif kind == 'difference':
        old = real_campaign()
        new = copy_campaign(home / 'candidate')
        change_saved_trace(new)
    elif kind in {'error', 'source_different'}:
        old = new = real_campaign(seeds=(42,), status='ERROR' if kind == 'error' else 'DIFFERENT')
    elif kind == 'added':
        old, new = real_campaign(seeds=(42,)), real_campaign()
    else:
        old = new = real_campaign()
    output = home / 'comparison'
    run_campaign_comparison(old, new, output)
    return output


def real_comparison(kind='match'):
    return _real_comparison(kind)


def copy_comparison(target, kind='match'):
    shutil.copytree(real_comparison(kind), target)
    return target
