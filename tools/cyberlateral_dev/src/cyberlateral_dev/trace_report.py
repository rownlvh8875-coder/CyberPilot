"""Fixed offline bundle bytes; no filesystem, network, clock or arbitrary data."""
import hashlib

from .report_csv import render_csv
from .report_html import render_html
from .reporting import canonical_report, catalog_report
from .trace_analysis import analyze_trace


def build_report_bundle() -> dict[str, bytes]:
    source = catalog_report()
    analysis = analyze_trace(source)
    files = {'simulation.json': canonical_report(source), 'analysis.json': canonical_report(analysis),
             'trace.csv': render_csv(analysis), 'index.html': render_html(analysis)}
    files['REPORT_SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()
    return files
