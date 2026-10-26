"""Pure local comparison reports. No parser, artifact loader or persistent writer."""
from dataclasses import asdict

from openpilot.tools.cyber_autotune.comparison import ComparisonPolicy, RunReceipt, compare_receipts


def build_report(policy: ComparisonPolicy, receipts: tuple[RunReceipt, ...]) -> dict:
  """Recompute assessment instead of accepting externally forged success flags."""
  result = compare_receipts(policy, receipts)
  return {
    'schema': 'cyber-validation-local-v1',
    'scope': 'ASSERTED_RECEIPTS_ONLY',
    'status': result.status,
    'runs': {'expected': result.expected_runs, 'received': result.received_runs, 'repeatable_groups': result.repeatable_groups},
    'identities': {'review_sha256': result.review_sha256, 'group_sha256s': list(result.group_sha256s),
                   'source_sha256s': list(result.source_sha256s)},
    'checks': {'local_nonregression_pass': result.local_nonregression_pass, 'primary_improvement_pass': result.primary_improvement_pass},
    'issues': [asdict(issue) for issue in result.issues],
    'authority': {'offline_evaluable': result.offline_evaluable, 'runtime_accepted': result.runtime_accepted, 'promotable': result.promotable},
  }


def render_markdown(policy: ComparisonPolicy, receipts: tuple[RunReceipt, ...]) -> str:
  """Render only validated hashes and generated codes; no raw paths or payloads."""
  report = build_report(policy, receipts)
  lines = [
    '# Cyber validation comparison', '',
    f'Status: {report["status"]}', '',
    'Scope: ASSERTED_RECEIPTS_ONLY — not native replay or vehicle qualification.', '',
    f'Runs received / expected: {report["runs"]["received"]} / {report["runs"]["expected"]}',
    f'Repeatable groups: {report["runs"]["repeatable_groups"]}', '',
    '## Local checks', '',
    *(f'- {name}: {str(value).lower()}' for name, value in report['checks'].items()), '',
    '## Authority', '',
    *(f'- {name}: {str(value).lower()}' for name, value in report['authority'].items()), '',
    '## Issues', '',
  ]
  for issue in report['issues']:
    context = ' / '.join(value for value in (issue['group_sha256'], issue['arm'], issue['detail']) if value is not None)
    lines.append(f'- {issue["code"]}' + (f': {context}' if context else ''))
  lines.extend(('', '## Identities (asserted, not authenticated)', '',
                f'- review_sha256: {report["identities"]["review_sha256"] or "unavailable"}'))
  lines.extend(f'- group_sha256: {digest}' for digest in report['identities']['group_sha256s'])
  lines.extend(f'- source_sha256: {digest}' for digest in report['identities']['source_sha256s'])
  return '\n'.join(lines) + '\n'
