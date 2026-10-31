"""Static escaped view of internal validated records, never a model consumer."""

from html import escape

from .scenario_output import COLUMNS

TABLE = [*COLUMNS, 'fault_condition', 'limiter_adjusted', 'inactive_gate_changed', 'fault_request_suppressed']
STYLE = '''
:root{font-family:system-ui,sans-serif;color:#20304a;background:#eef2f7}*{box-sizing:border-box}
body{margin:0}main{max-width:1280px;margin:auto;padding:28px 18px 50px}
header,section{background:white;border:1px solid #d7e0ec;border-radius:14px;padding:22px;margin-bottom:20px}
h1{font-size:28px}h2{font-size:19px}p,footer{line-height:1.7}.badge{background:#fff0e8;color:#8a301b;padding:8px;border-radius:8px;font-weight:700}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:#f0f4fa;padding:10px;border-radius:8px}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;min-width:0}figcaption{font-weight:600}
svg{display:block;width:100%;height:auto}.axis{stroke:#9ba9bd}.zero{stroke:#d5ddeb;stroke-dasharray:4 4}
.series{fill:none;stroke-width:2.5}.legend{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.key{display:inline-block;width:16px;border-top:3px solid;margin:0 4px 0 10px}
.scroll{overflow:auto;max-height:600px}table{border-collapse:collapse;font:12px ui-monospace,monospace;width:100%}
th,td{white-space:nowrap;text-align:left;padding:8px;border-bottom:1px solid #e1e7f0}th{position:sticky;top:0;background:#eaf0f8}tr.event{background:#fff4e2}
code{overflow-wrap:anywhere}small,footer{color:#53647c}a{color:#225ab0}
@media(max-width:850px){.charts{grid-template-columns:1fr}main{padding:14px 8px}header,section{padding:16px}}
@media print{.scroll{max-height:none;overflow:visible}body{background:white}}
'''


def _text(value):
    text = 'null' if value is None else str(value).lower() if type(value) is bool else str(value)
    return escape(text, quote=True)


def _chart(rows, normalized):
    names = ['request_hex'] if normalized else ['integer_request', 'previous_applied', 'limited_command', 'final_command']
    series = [(name, [float.fromhex(row[name]) if normalized else row[name] for row in rows]) for name in names]
    low = min(0, *(min(values) for _, values in series))
    high = max(0, *(max(values) for _, values in series))
    if low == high:
        low, high = -1, 1
    first, last = rows[0]['index'], rows[-1]['index']
    def x(index):
        return 375.0 if first == last else 50 + 650 * (index - first) / (last - first)
    def y(value):
        return 200 - 170 * (value - low) / (high - low)
    name = 'normalized' if normalized else 'commands'
    title = '원본 정규화 요청 · binary64' if normalized else '정수 명령 단계 · 물리 torque 아님'
    parts = [f'<figure><figcaption>{title}</figcaption><svg viewBox="0 0 720 240" role="img" aria-labelledby="{name}-title">',
             f'<title id="{name}-title">{title}</title><desc>X축은 호출 index이며 초가 아닙니다. 좌표는 표시용 반올림입니다.</desc>',
             '<line class="axis" x1="50" y1="30" x2="50" y2="200"/><line class="axis" x1="50" y1="200" x2="700" y2="200"/>',
             f'<line class="zero" x1="50" y1="{y(0):.3f}" x2="700" y2="{y(0):.3f}"/>',
             f'<text x="4" y="35" font-size="11">{high:.6g}</text><text x="4" y="203" font-size="11">{low:.6g}</text>',
             f'<text x="50" y="218" font-size="11">{first}</text><text x="680" y="218" font-size="11">{last}</text>',
             '<text x="220" y="236" font-size="11">모델 호출 index · NOT seconds</text>']
    colors, legends = ['#2563eb', '#b26917', '#8d52b3', '#15805c'], []
    for i, (label, values) in enumerate(series):
        points = ' '.join(f'{x(row["index"]):.3f},{y(value):.3f}' for row, value in zip(rows, values, strict=True))
        parts.append(f'<polyline class="series" stroke="{colors[i]}" data-series="{label}" points="{points}"/>')
        if len(rows) == 1:
            parts.append(f'<circle cx="{x(first):.3f}" cy="{y(values[0]):.3f}" r="3" fill="{colors[i]}"/>')
        legends.append(f'<span><i class="key" style="border-color:{colors[i]}"></i>{label}</span>')
    return ''.join(parts) + '</svg><div class="legend">' + ' · '.join(legends) + '</div></figure>'


def _render_html(view: dict) -> bytes:
    """Internal view only: caller must use read_report first; no generic HTML API."""
    parts = ['<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>CyberLateral · 사용자 합성 기록</title><style>' + STYLE + '</style></head><body><main><header>',
             '<span class="badge">합성 선언 기록 · 실차 사용 금지</span><h1>' + _text(view['scenario_id']) + '</h1>',
             '<p>저장된 요청 → 정수화 → 제한 → 최종 출력 기록입니다. 이 리포트는 모델을 다시 실행하지 않습니다.</p>',
             '<p><strong>Static Gate = FAIL · R_BUDGET = UNRESOLVED · Candidate / Runtime = NO_GO</strong></p>',
             '<p>checksum과 기록 간 일관성만 검산했습니다. 출처 인증·계산식의 독립 검증·실차 안전 판정이 아닙니다.</p>',
             '<div class="stats">' + ''.join(f'<span class="stat">{_text(k)}: <b>{_text(v)}</b></span>' for k, v in view['summary'].items()) + '</div>',
             '<p>리포트의 새 모델 호출:0. 위 steps는 입력 기록의 호출 수입니다. X축은 호출 순서이며 실제 초·10ms·주기를 뜻하지 않습니다.</p>',
             '<p><a href="VIEW.json">정확한 투영 JSON</a> · <a href="SHA256SUMS.txt">출력 checksum</a></p>',
             '<small>선언된 원본 입력 SHA (원본 bytes는 이 묶음에 없으므로 재계산하지 못함)</small><br><code>' + _text(view['input_raw_sha256']) + '</code></header>',
             '<section><h2>호출별 명령</h2><div class="charts">', _chart(view['rows'], True), _chart(view['rows'], False),
             '</div><p>정규화 표현과 정수 명령은 서로 다른 단위입니다. 그래프 좌표는 표시용 소수3자리이며 아래 hex/정수가 기준입니다.</p></section>',
             ('<section><h2>상태·비활성화·요청 비트</h2><p>previous_requested와 previous_applied는 별도입니다. '
              '요청 비트 해제는 명령0과 같지 않습니다. limiter_adjusted는 결합 제한 변화이며 driver/rate 단독 원인 판정이 아닙니다.</p>'),
             '<div class="scroll"><table><thead><tr>' + ''.join('<th scope="col">' + _text(k) + '</th>' for k in TABLE) + '</tr></thead><tbody>']
    for row in view['rows']:
        event = row['inactive_gate_changed'] or row['fault_request_suppressed']
        parts.append('<tr data-row="true"' + (' class="event"' if event else '') + '>')
        parts.extend('<td>' + _text(row[key]) + '</td>' for key in TABLE)
        parts.append('</tr>')
    parts.extend(['</tbody></table></div></section><section><h2>입력 파일 검산 근거</h2>',
                  '<p>아래 hash는 소유한 portable 파일 bytes의 검산값입니다. 환경 receipt는 별도 보존하며 인증 사실로 승격하지 않습니다.</p>'])
    for name, digest in sorted(view['source_portable_hashes'].items()):
        parts.append('<p>' + _text(name) + '<br><code>' + _text(digest) + '</code></p>')
    parts.append('</section><footer>SYNTHETIC_ONLY는 사용자 선언입니다. 일관되게 위조·재봉인된 기록은 탐지하지 못합니다. '
                 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE · 실제 r/T2/차량 scale 미정 · F70UH/F70V/F71 NOT_ALLOWED. '
                 'F61/Controller/Runtime/CAN/실차 실행 없음 · 물리·성능·배포 승인 아님 · JavaScript/외부 자산 없음.</footer></main></body></html>\n')
    return ''.join(parts).encode()
