"""Self-contained escaped HTML/SVG view, display coordinates are not authority."""
from html import escape

from .report_csv import COLUMNS

STYLE = """
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#17263c;background:#edf2f7}
*{box-sizing:border-box}body{margin:0}main{max-width:1220px;margin:auto;padding:32px 20px 56px}
header,.scenario{background:white;border:1px solid #d5dfeb;border-radius:16px;padding:24px;margin:0 0 24px}
h1{font-size:30px;margin:12px 0}h2{font-size:22px}h3{font-size:15px;margin:0 0 12px}
p{line-height:1.65}.muted,small{color:#52647b}code{overflow-wrap:anywhere;font-size:12px}
.badge{display:inline-block;padding:6px 10px;border-radius:8px;background:#fff0eb;color:#8d2b17;font-weight:700}
.summary{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}.stat{padding:10px 12px;background:#f1f5fa;border-radius:8px}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;min-width:0;border:1px solid #e1e7ef;border-radius:10px;padding:12px}
svg{display:block;width:100%;height:auto}.axis{stroke:#92a2b8;stroke-width:1}.zero{stroke:#cbd4e0;stroke-dasharray:4 4}
.line{fill:none;stroke-width:2.5}.s0{stroke:#2563eb}.s1{stroke:#b56810;stroke-dasharray:5 3}.s2{stroke:#9253bf}.s3{stroke:#13795b}
circle.s0{fill:#2563eb}circle.s1{fill:#b56810}circle.s2{fill:#9253bf}circle.s3{fill:#13795b}
.legend{font-size:11px;line-height:1.7;overflow-wrap:anywhere}.key{display:inline-block;width:18px;border-top:3px solid;margin-right:4px}
.table-scroll{overflow:auto;max-height:520px;border:1px solid #d5dfeb;border-radius:8px;margin-top:16px}
table{border-collapse:collapse;font:11px ui-monospace,monospace;min-width:1800px;width:100%}th,td{padding:8px;border-bottom:1px solid #e4eaf1;text-align:left;white-space:nowrap}
th{background:#f0f4f8;position:sticky;top:0}tr.event{background:#fff7e7}td small{display:block}
a{color:#205ca9}.notes{font-size:13px}footer{font-size:12px;line-height:1.8;color:#52647b}
@media(max-width:800px){.charts{grid-template-columns:1fr}main{padding:16px 10px}header,.scenario{padding:16px}h1{font-size:24px}}
@media print{body{background:white}.table-scroll{max-height:none;overflow:visible}.scenario{break-inside:avoid}.charts{grid-template-columns:1fr}}
"""


def _text(value):
    return escape(str(value), quote=True)


def _chart(scenario, kind, ordinal):
    rows = scenario['rows']
    if kind == 'command':
        series = [(key, [r[key] for r in rows]) for key in ('integer_requested', 'previous_applied', 'limited_command', 'final_command')]
        label, unit = '정수 명령 단계 비교', '합성 command 단위 · 물리 torque 아님'
    else:
        series = [('requested_normalized', [float.fromhex(r['request_hex']) for r in rows]),
                  ('returned_normalized', [float.fromhex(r['normalized_expression_hex']) for r in rows])]
        label, unit = '요청 정규화 / 반환 나눗셈 표현', '정규화 표현 · F61 입력/역변환 아님'
    low = min(0, *(min(values) for _, values in series))
    high = max(0, *(max(values) for _, values in series))
    if low == high:
        low, high = -1, 1
    indices = [r['invocation_index'] for r in rows]
    xmin, xmax = min(indices), max(indices)
    def xcoord(index):
        return 375.0 if xmin == xmax else 50 + 650 * (index - xmin) / (xmax - xmin)
    def ycoord(value):
        return 200 - 170 * (value - low) / (high - low)
    title_id = f'chart-{ordinal}-{kind}'
    parts = [(f'<figure><h3>{label}</h3><svg viewBox="0 0 720 240" role="img" aria-labelledby="{title_id}" '
              f'data-chart="{_text(scenario["id"])}:{kind}" data-ymin="{low}" data-ymax="{high}">'),
             f'<title id="{title_id}">{_text(scenario["id"])} — {label}</title>',
             f'<desc>{unit}. X: 모델 호출 순서, 초가 아님. 좌표 반올림은 표시 전용.</desc>',
             '<line class="axis" x1="50" y1="30" x2="50" y2="200"/><line class="axis" x1="50" y1="200" x2="700" y2="200"/>',
             f'<line class="zero" x1="50" y1="{ycoord(0):.3f}" x2="700" y2="{ycoord(0):.3f}"/>',
             f'<text x="4" y="35" font-size="11">{high:.6g}</text><text x="4" y="203" font-size="11">{low:.6g}</text>',
             f'<text x="50" y="218" font-size="11">{xmin}</text><text x="680" y="218" font-size="11">{xmax}</text>',
             '<text x="240" y="236" font-size="11">모델 호출 순서 · NOT seconds</text>']
    colors = ['#2563eb', '#b56810', '#9253bf', '#13795b']
    legends = []
    for i, (name, values) in enumerate(series):
        points = ' '.join(f'{xcoord(index):.3f},{ycoord(value):.3f}' for index, value in zip(indices, values, strict=True))
        parts.append(f'<polyline class="line s{i}" data-series="{name}" points="{points}"/>')
        if len(rows) == 1:
            parts.append(f'<circle class="s{i}" cx="{xcoord(indices[0]):.3f}" cy="{ycoord(values[0]):.3f}" r="3"/>')
        legends.append(f'<span><i class="key" style="border-color:{colors[i]}"></i>{name}</span>')
    parts.append('</svg><div class="legend">' + ' · '.join(legends) + '</div><small>' + unit + '</small></figure>')
    return ''.join(parts)


def render_html(analysis: dict) -> bytes:
    summary = analysis['summary']
    parts = ['<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>CyberLateral · 오프라인 합성 trace</title><style>' + STYLE + '</style></head><body><main><header>',
             '<span class="badge">SYNTHETIC_DEVELOPMENT_ONLY · 실차 사용 금지</span><h1>명령이 어떻게 달라졌는지 확인하세요</h1>',
             '<p>요청 → 정수화 → 제한 → 비활성화 gate → 반환 표현을 비교합니다. 실제 차량·물리 동역학·F61 feasibility 결과가 아닙니다.</p>',
             '<p><strong>Static Gate = FAIL · R_BUDGET = UNRESOLVED · Candidate / Runtime = NO_GO</strong></p>',
             '<div class="summary">' + ''.join(f'<span class="stat">{_text(k)}: <b>{_text(v)}</b></span>' for k, v in summary.items()) + '</div>',
             ('<p class="notes">X축은 모델 호출 순서이며 초·10ms·실제 주기가 아닙니다. Δ는 호출 사이 정수 차이이며 /s 또는 rate budget이 아닙니다. '
              'limiter_adjusted는 결합 제한 효과로, driver/rate 단독 원인을 판정하지 않습니다. fault 요청 비트 해제 ≠ 명령 0.</p>'),
             '<p><a href="simulation.json">원본 합성 JSON</a> · <a href="analysis.json">분석 JSON</a> · <a href="trace.csv">정확한 CSV</a></p>',
             '<p class="muted">source_report_sha256<br><code>' + _text(analysis['source_report_sha256']) + '</code></p></header>']
    for i, scenario in enumerate(analysis['scenarios']):
        parts.extend([f'<section class="scenario" id="scenario-{i}"><h2>{_text(scenario["id"])}</h2>',
                      '<p class="notes">' + ' · '.join(f'{_text(k)}={_text(v)}' for k, v in scenario['summary'].items()) + '</p>',
                      '<div class="charts">', _chart(scenario, 'command', i), _chart(scenario, 'normalized', i), '</div>',
                      '<div class="table-scroll"><table><thead><tr>' + ''.join('<th scope="col">' + key + '</th>' for key in COLUMNS) + '</tr></thead><tbody>'])
        for row in scenario['rows']:
            record = dict(row, scenario_id=scenario['id'])
            event = row['inactive_gate_changed'] or row['fault_request_suppressed']
            parts.append('<tr data-row="true"' + (' class="event"' if event else '') + '>')
            for key in COLUMNS:
                value = record[key]
                text = str(value).lower() if type(value) is bool else str(value)
                extra = '<small>' + _text(float.fromhex(value)) + '</small>' if key == 'normalized_expression_hex' else ''
                parts.append('<td>' + _text(text) + extra + '</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div></section>')
    parts.append('<footer>정확한 값은 JSON / CSV / hex를 기준으로 보세요. SVG 좌표는 표시용 소수 3자리이며, 숫자 모의 Float32 word는 CAN/Cap’n Proto bytes가 아닙니다. '
                 '실제 r/T2/차량 scale 미확정 · F70UH/F70V/F71 NOT_ALLOWED · 네트워크/JavaScript 없음.</footer></main></body></html>\n')
    return ''.join(parts).encode('utf-8')
