"""Read-only report frontend with exclusive last-marker publication."""

import hashlib
import os
import platform
import sys
import tempfile
import warnings
from pathlib import Path

from .scenario_campaign_compare_run import _source_hashes as _comparison_sources
from .scenario_campaign_evidence import capture_tree
from .scenario_campaign_report_data import MAX_BYTES, MAX_FILES, read_comparison
from .scenario_campaign_report_html import _render_html
from .scenario_campaign_report_schema import CampaignReportError, need
from .scenario_compare_input import CompareError, _manifest
from .scenario_compare_run import FORBIDDEN, _preflight
from .scenario_output import canonical

ROOT = Path(__file__).resolve().parents[1]


def _source_hashes():
    try:
        sources = _comparison_sources()
        sources['tools/scenario_campaign_compare_report.py'] = hashlib.sha256(
            (ROOT / 'tools/scenario_campaign_compare_report.py').read_bytes()).hexdigest()
        return sources
    except (ValueError, OSError) as error:
        raise CampaignReportError('CAMPAIGN_REPORT_SOURCE_IDENTITY') from error


def _write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def _warn_after_result(message: str) -> None:
    """Best-effort diagnostic only; never replace a determined result."""
    try:
        warnings.warn(message, RuntimeWarning, stacklevel=2)
    except Exception:
        # Caller warning filters/hooks may raise. Keep their policy unchanged.
        try:
            print(f'WARNING: {message}', file=sys.stderr)
        except Exception:
            # A closed/broken diagnostic sink cannot undo publication either.
            pass


def _publish(output, files, check):
    committed = False
    try:
        output.mkdir(exist_ok=False)
        for name in ['VIEW.json', 'RECEIPT.json', 'SHA256SUMS.txt']:
            _write(output / name, files[name])
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r46-publish-', dir=output.parent) as scratch:
            pending = Path(scratch) / 'pending_html'
            _write(pending, files['index.html'])
            check()
            os.link(pending, output / 'index.html')
            committed = True
    except OSError as error:
        if not committed:
            raise CampaignReportError('CAMPAIGN_REPORT_PUBLICATION_FAILED') from error
        _warn_after_result('CAMPAIGN_REPORT_CLEANUP_FAILED_AFTER_COMMIT')


def run_report(input_path: Path, output_path: Path) -> dict:
    try:
        _preflight(input_path, input_path, output_path)
        need(not any(p.is_symlink() for p in output_path.absolute().parents), 'CAMPAIGN_REPORT_OUTPUT_LOCATION')
    except CompareError as error:
        raise CampaignReportError(error.code.replace('COMPARE_', 'CAMPAIGN_REPORT_', 1)) from error
    except CampaignReportError:
        raise
    except (ValueError, OSError) as error:
        raise CampaignReportError('CAMPAIGN_REPORT_IO') from error
    sources = _source_hashes()
    snapshot = read_comparison(input_path)

    def unchanged():
        try:
            current = capture_tree(input_path, max_files=MAX_FILES, max_bytes=MAX_BYTES)
        except (ValueError, OSError) as error:
            raise CampaignReportError('CAMPAIGN_REPORT_INPUT_CHANGED') from error
        need(current == snapshot['hashes'], 'CAMPAIGN_REPORT_INPUT_CHANGED')
        need(_source_hashes() == sources, 'CAMPAIGN_REPORT_SOURCE_CHANGED')

    html = _render_html(snapshot['view'])
    unchanged()
    try:
        receipt = {
            'schema_version': 1, 'input_directory': str(input_path.absolute()), 'output_directory': str(output_path.absolute()),
            'source_root': str(ROOT), 'source_file_hashes': snapshot['hashes'], 'renderer_source_hashes': sources,
            'python_executable': sys.executable, 'python_version': platform.python_version(),
            'python_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            'renderer_model_executions': 0, 'renderer_reference_executions': 0,
            'forbidden_modules_loaded': sorted({n.split('.')[0] for n in sys.modules} & FORBIDDEN),
            'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API',
            'scope': 'OWNED_BYTES_COOPERATIVE_NOT_ATOMIC_OS_OR_ORIGIN_AUTHENTICATION',
        }
        files = {'index.html': html, 'VIEW.json': canonical(snapshot['view']), 'RECEIPT.json': canonical(receipt)}
        files['SHA256SUMS.txt'] = _manifest(files)
        _publish(output_path, files, unchanged)
    except OSError as error:
        raise CampaignReportError('CAMPAIGN_REPORT_IO') from error
    record = snapshot['view']['comparison']
    return {'status': 'REPORT_COMPLETE', 'recorded_status': record['status'], 'recorded_regression_status': record['regression_status'],
            'renderer_model_executions': 0, 'renderer_reference_executions': 0}
