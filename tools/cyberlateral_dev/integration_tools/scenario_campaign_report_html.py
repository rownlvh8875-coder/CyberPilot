"""Escaped static Korean view. Internal renderer accepts validated R46 views only."""

import json
from html import escape


def _text(value):
    return escape(str(value), quote=True)


def _json(value):
    return _text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))


def _typed(value, present=True):
    if not present:
        return '<span class="missing">없음 (missing)</span>'
    kind = 'null' if value is None else type(value).__name__
    return f'<span class="kind">존재 · {_text(kind)}</span><code>{_json(value)}</code>'


def _table(headers, rows):
    return ('<div class="scroll" tabindex="0" role="region" aria-label="가로 스크롤 표"><table><thead><tr>'
            + ''.join('<th scope="col">' + _text(h) + '</th>' for h in headers) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join('<td>' + cell + '</td>' for cell in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def _details(record):
    details = record['differences']
    text = (f'<p>전체 {_text(record["difference_count"])} · 보존 {len(details)} · '
            f'미보존 {record["difference_count"] - len(details)}</p>')
    if record['details_truncated']:
        text += '<p class="notice">미보존 상세는 검증하거나 복원하지 않았습니다. VIEW.json도 보존된 상세만 담습니다.</p>'
    if not details:
        return text + '<p>보존된 차이 없음.</p>'
    for number, detail in enumerate(details, 1):
        context = ' / '.join(str(detail.get(n)) for n in ['run_id', 'case_id', 'sample_index'] if n in detail)
        text += (f'<details><summary>차이 {number} · {_text(context)} · <code>{_text(detail["field"])}</code></summary>'
                 + _table(['위치 / 호출 index', '이전 값', '이후 값'], [[_text(context),
                         _typed(detail['before'], detail['before_present']),
                         _typed(detail['after'], detail['after_present'])]]) + '</details>')
    return text


def _render_html(view: dict) -> bytes:
    record = view['comparison']
    status = record['status']
    tone = 'good' if status == 'MATCH' else 'bad'
    runs = _table(['명시적 위치', '이전 → 이후 seed', '원본 판정', '분류', '회귀 / 차이'], [
        ['<a href="#run-' + str(number) + '">' + _text(row['run_id']) + '</a>',
         _text(row['baseline_seed']) + ' → ' + _text(row['candidate_seed']),
         _text(row['baseline_status']) + ' → ' + _text(row['candidate_status']), _text(row['classification']),
         _text(row['regression_status']) + ' / ' + str(row['difference_count'])]
        for number, row in enumerate(record['runs'], 1)])
    alerts = ''
    for name in ['source_error_runs', 'source_difference_runs']:
        for alert in record[name]:
            alerts += (f'<article class="finding"><h3>{_text(alert["side"])} · {_text(alert["run_id"])} · '
                       f'원본 판정 {_text(alert["status"])}</h3>')
            for finding in alert['findings']:
                alerts += f'<h4>{_text(finding["case_id"])} · {_text(finding["case_status"])}</h4><code>{_json(finding)}</code>'
            alerts += '</article>'
    children = ''
    for number, row in enumerate(record['runs'], 1):
        children += f'<section id="run-{number}"><h2>{_text(row["run_id"])} · {_text(row["classification"])}</h2>'
        child = view['children'].get(row['run_id'])
        if child is None:
            children += '<p>짝이 없는 run: 하위 비교 결과를 만들지 않았습니다.</p></section>'
            continue
        children += (f'<p>저장된 하위 판정: {_text(child["status"])} · sample {child["compared_sample_count"]} · '
                     f'identity 전체 일치: {_text(child["all_observed_producer_identities_match"])}</p>')
        children += _table(['case 위치', '분류', '차이', 'producer identity 변경'], [
            [_text(c['case_id']), _text(c['classification']), str(c['difference_count']), _text(c['producer_identity_changed'])]
            for c in child['cases']])
        children += '<h3>하위 보존 상세</h3>' + _details(child) + '</section>'
    hashes = _table(['고정 상대 파일명', 'SHA256 (출처 인증 아님)'], [
        [_text(name), '<code>' + _text(value) + '</code>'] for name, value in sorted(view['source_file_hashes'].items())])
    return ('''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>R46 저장 캠페인 비교 리포트</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef2f7;color:#172637;font:16px/1.65 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:24px}header,section{background:white;border:1px solid #d4dce6;border-radius:14px;padding:24px;margin-bottom:20px;min-width:0}
h1{font-size:28px;line-height:1.3}h2{font-size:22px}h3{font-size:18px}h4{font-size:16px}p{margin:12px 0}
h1,h2,h3,h4,p,code,summary,td,th,a{overflow-wrap:anywhere}code{font:14px/1.65 ui-monospace,monospace;white-space:pre-wrap;display:block}
a{color:#185c9a;text-underline-offset:3px}.status{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.verdict{border:2px solid;padding:16px;border-radius:10px;font-weight:700;font-size:20px}.good{border-color:#247253;background:#f0faf5}.bad{border-color:#a13535;background:#fff4f3}
.neutral{border-color:#66778b;background:#f4f7fb}.notice,.finding{border-left:4px solid #a13535;padding:12px 16px;background:#fff6ef}
.scroll{overflow-x:auto;max-width:100%;margin:12px 0}table{border-collapse:collapse;width:100%;font-size:14px;text-align:left}
th,td{border-bottom:1px solid #dbe2eb;padding:12px;vertical-align:top;min-width:120px}th{background:#f3f6fa}td code{min-width:180px;max-width:660px}
details{border:1px solid #dbe2eb;border-radius:8px;padding:12px;margin:10px 0}summary{cursor:pointer;font-size:15px}summary code{display:inline}
.kind{display:block;font-size:14px;color:#42546b}.missing{color:#7a3840}nav{display:flex;gap:18px;flex-wrap:wrap}
@media(max-width:600px){main{padding:12px}header,section{padding:16px;margin-bottom:14px}h1{font-size:24px}h2{font-size:20px}.status{grid-template-columns:1fr}.verdict{font-size:18px}th,td{padding:10px}}
</style></head><body><main><header><p>R46 · 계산하지 않는 저장 기록 뷰</p><h1>캠페인 비교 리포트</h1>
''' + f'<div class="status"><div class="verdict {tone}">전체 판정: {_text(status)}</div>'
            f'<div class="verdict neutral">저장 기록 회귀: {_text(record["regression_status"])}</div></div>'
            '<p class="notice">원본 ERROR·DIFFERENT는 회귀 MATCH여도 정상으로 승격하지 않습니다. 리포트 생성 성공은 원본 검증 통과가 아닙니다.</p>'
            f'<p>원본 판정: {_text(record["baseline_campaign_status"])} → {_text(record["candidate_campaign_status"])}</p>'
            f'<p>비교 sample: {record["compared_sample_count"]} · 차이: {record["difference_count"]} · '
            f'producer identity 전체 일치: {_text(record["all_observed_producer_identities_match"])}</p>'
            '<p>새 모델/참조 실행: 0/0. 호출 index는 호출 순서이며 초나 100Hz가 아닙니다.</p>'
            '<nav><a href="VIEW.json">정확한 보존 VIEW JSON</a><a href="SHA256SUMS.txt">출력 checksum</a><a href="#differences">보존 차이</a><a href="#sources">원본 findings</a></nav></header>'
            '<section><h2>명시적 위치별 run</h2>' + runs + '<h3>이전 조건</h3><code>' + _json(record['baseline_parameters'])
            + '</code><h3>이후 조건</h3><code>' + _json(record['candidate_parameters']) + '</code></section>'
            '<section id="differences"><h2>전체 비교의 보존 차이</h2>' + _details(record) + '</section>'
            '<section id="sources"><h2>원본 판정과 findings</h2>' + (alerts or '<p>보존된 원본 ERROR·DIFFERENT findings 없음.</p>') + '</section>'
            + children + '<section><h2>입력 파일 검산 근거</h2>' + hashes + '</section>'
            '<section><h2>검증 범위와 제한</h2><p>완전한 R44 V1 결과의 hash·구조·보존 기록 일관성만 확인했습니다. '
            '원래 캠페인으로 비교를 재계산하지 않았으며 수치의 진실·출처·현재 소스 identity를 인증하지 않습니다. '
            'Markdown 의미 동등성·미보존 상세·원자적 OS snapshot은 검증하지 않았습니다. private receipt 경로는 열거나 표시하지 않습니다.</p>'
            '<p>R_BUDGET=UNRESOLVED · Static Gate=FAIL · 실제 r/T2/scale=null. Candidate/Runtime NO_GO. '
            'F61·실제 r/dt·차량 실행 0. 실차 활성화·F70UH/V/F71 NOT_ALLOWED.</p></section></main></body></html>\n').encode()
